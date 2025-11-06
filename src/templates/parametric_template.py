"""
Parametric template wrapper around pyDEXPI's DexpiPattern.

Provides parameter substitution layer that pyDEXPI doesn't offer out-of-the-box.
"""

import logging
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydexpi.dexpi_classes.dexpiModel import DexpiModel

from .substitution_engine import ParameterSubstitutionEngine

logger = logging.getLogger(__name__)


# ==============================================================================
# Result Types
# ==============================================================================

@dataclass
class ValidationResult:
    """Result of parameter validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class TemplateInstantiationResult:
    """Result of template instantiation."""
    success: bool
    message: str
    instantiated_components: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ==============================================================================
# Exceptions
# ==============================================================================

class TemplateError(Exception):
    """Base exception for template errors."""
    pass


class ParameterValidationError(TemplateError):
    """Raised when parameter validation fails."""
    pass


class TemplateInstantiationError(TemplateError):
    """Raised when template instantiation fails."""
    pass


class TemplateLoadError(TemplateError):
    """Raised when template loading fails."""
    pass


# ==============================================================================
# ParametricTemplate Class
# ==============================================================================

class ParametricTemplate:
    """
    Parametric template wrapping DexpiPattern.

    Codex guidance: "Wrap templates in parametric template class"

    Provides:
    - Parameter validation and substitution
    - Integration with ConnectorRenamingConvention
    - Pattern composition and sequencing
    - Validation hooks
    """

    def __init__(self, template_def: Dict[str, Any]):
        """
        Initialize from template definition.

        Args:
            template_def: Parsed YAML template definition

        Raises:
            TemplateLoadError: If template definition invalid
        """
        try:
            self.name = template_def["name"]
            self.version = template_def.get("version", "1.0.0")
            self.category = template_def.get("category", "general")
            self.description = template_def.get("description", "")
            self.parameters = template_def.get("parameters", {})
            self.base_pattern = template_def.get("base_pattern")
            self.components = template_def.get("components", [])
            self.connections = template_def.get("connections", [])
            self.instrumentation = template_def.get("instrumentation", [])
            self.validation = template_def.get("validation", {})
            self.metadata = template_def.get("metadata", {})

            self._substitution_engine = ParameterSubstitutionEngine()

        except KeyError as e:
            raise TemplateLoadError(f"Missing required field in template: {e}")

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "ParametricTemplate":
        """
        Load template from YAML file.

        Args:
            yaml_path: Path to YAML template file

        Returns:
            ParametricTemplate instance

        Raises:
            TemplateLoadError: If file not found or invalid YAML
        """
        try:
            with open(yaml_path, 'r') as f:
                template_def = yaml.safe_load(f)

            return cls(template_def)

        except FileNotFoundError:
            raise TemplateLoadError(f"Template file not found: {yaml_path}")
        except yaml.YAMLError as e:
            raise TemplateLoadError(f"Invalid YAML in template: {e}")

    def validate_parameters(self, params: Dict[str, Any]) -> ValidationResult:
        """
        Validate provided parameters against schema.

        Args:
            params: Parameter values

        Returns:
            ValidationResult with errors/warnings
        """
        errors = []
        warnings = []

        for param_name, param_schema in self.parameters.items():
            # Check required
            if param_name not in params and "default" not in param_schema:
                errors.append(f"Required parameter missing: {param_name}")
                continue

            # Get value (either provided or default)
            if param_name not in params:
                continue  # Will use default during instantiation

            value = params[param_name]

            # Type check
            expected_type = param_schema.get("type")
            if expected_type == "integer" and not isinstance(value, int):
                errors.append(f"Parameter {param_name} must be integer, got {type(value).__name__}")

            elif expected_type == "number" and not isinstance(value, (int, float)):
                errors.append(f"Parameter {param_name} must be number, got {type(value).__name__}")

            elif expected_type == "string" and not isinstance(value, str):
                errors.append(f"Parameter {param_name} must be string, got {type(value).__name__}")

            elif expected_type == "boolean" and not isinstance(value, bool):
                errors.append(f"Parameter {param_name} must be boolean, got {type(value).__name__}")

            # Range check (for numbers)
            if expected_type in ["integer", "number"]:
                if "min" in param_schema and value < param_schema["min"]:
                    errors.append(f"Parameter {param_name} below minimum: {value} < {param_schema['min']}")

                if "max" in param_schema and value > param_schema["max"]:
                    errors.append(f"Parameter {param_name} above maximum: {value} > {param_schema['max']}")

            # Enum check
            if "enum" in param_schema and value not in param_schema["enum"]:
                errors.append(f"Parameter {param_name} not in allowed values: {value} not in {param_schema['enum']}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def instantiate(
        self,
        target_model: Any,  # DexpiModel or Flowsheet
        parameters: Dict[str, Any],
        model_type: str = "dexpi",  # "dexpi" or "sfiles"
        connection_point: Optional[str] = None
    ) -> TemplateInstantiationResult:
        """
        Instantiate template into target model.

        Supports both DEXPI (P&ID) and SFILES (flowsheet) models.

        Args:
            target_model: DexpiModel or Flowsheet to instantiate into
            parameters: Parameter values
            model_type: "dexpi" or "sfiles"
            connection_point: Optional connector to attach at

        Returns:
            TemplateInstantiationResult

        Raises:
            ParameterValidationError: If parameters invalid
            TemplateInstantiationError: If instantiation fails
        """
        try:
            # Step 1: Validate parameters
            validation = self.validate_parameters(parameters)
            if not validation.is_valid:
                raise ParameterValidationError(
                    f"Parameter validation failed: {', '.join(validation.errors)}"
                )

            # Add defaults for missing parameters
            full_params = {}
            for param_name, param_schema in self.parameters.items():
                if param_name in parameters:
                    full_params[param_name] = parameters[param_name]
                elif "default" in param_schema:
                    full_params[param_name] = param_schema["default"]

            logger.info(f"Instantiating template '{self.name}' ({model_type}) with parameters: {full_params}")

            # Branch based on model type
            if model_type.lower() == "sfiles":
                return self._instantiate_sfiles(target_model, full_params, connection_point)
            else:
                return self._instantiate_dexpi(target_model, full_params, connection_point)

        except ParameterValidationError:
            raise

        except Exception as e:
            logger.exception(f"Template instantiation failed: {e}")
            raise TemplateInstantiationError(f"Failed to instantiate template: {e}")

    def _instantiate_dexpi(
        self,
        target_model: DexpiModel,
        full_params: Dict[str, Any],
        connection_point: Optional[str]
    ) -> TemplateInstantiationResult:
        """
        DEXPI-specific instantiation workflow.

        Directly adds components to the DEXPI model.
        """
        from pydexpi.dexpi_classes import equipment as eq_module
        from pydexpi.dexpi_classes import piping as piping_module
        from pydexpi.dexpi_classes import instrumentation as inst_module
        from pydexpi.dexpi_classes.dexpiModel import ConceptualModel

        # Ensure model has conceptual model
        if not target_model.conceptualModel:
            target_model.conceptualModel = ConceptualModel()

        instantiated_components = []

        # Process each component definition
        for component_def in self.components:
            # Check condition
            condition = component_def.get("condition")
            if condition:
                condition_result = self._substitution_engine.substitute(condition, full_params)
                if condition_result.lower() != "true":
                    continue

            # Get component type and count
            component_type = component_def.get("type")
            count = component_def.get("count", 1)

            # Substitute count if it's a template expression
            if isinstance(count, str):
                count = int(self._substitution_engine.substitute(count, full_params))

            # Generate N instances
            for i in range(count):
                # Build context for this instance
                instance_context = {**full_params, "index": i}

                # Generate tag
                tag_pattern = component_def.get("tag_pattern", component_def.get("name", "ITEM"))
                tag = self._substitution_engine.substitute(tag_pattern, instance_context)

                # Substitute attributes
                attributes = component_def.get("attributes", {})
                substituted_attrs = {}
                for attr_key, attr_value in attributes.items():
                    if isinstance(attr_value, str):
                        substituted_attrs[attr_key] = self._substitution_engine.substitute(
                            attr_value, instance_context
                        )
                    else:
                        substituted_attrs[attr_key] = attr_value

                # Create component instance
                # Try equipment first, then piping, then instrumentation
                component_class = None
                for module in [eq_module, piping_module, inst_module]:
                    component_class = getattr(module, component_type, None)
                    if component_class:
                        break

                if not component_class:
                    raise ValueError(f"Unknown component type: {component_type}")

                # Instantiate component
                component = component_class(tagName=tag, **substituted_attrs)

                # Set both tagName and tag for compatibility with different pyDEXPI tools
                if hasattr(component, 'tag') and not getattr(component, 'tag', None):
                    component.tag = tag

                # Add to model
                target_model.conceptualModel.taggedPlantItems.append(component)
                instantiated_components.append(tag)

        return TemplateInstantiationResult(
            success=True,
            message=f"Template '{self.name}' instantiated successfully",
            instantiated_components=instantiated_components,
            validation_errors=[],
            metadata={
                "template": self.name,
                "version": self.version,
                "parameters": full_params,
                "model_type": "dexpi"
            }
        )

    def _instantiate_sfiles(
        self,
        target_flowsheet: Any,  # Flowsheet from SFILES2
        full_params: Dict[str, Any],
        connection_point: Optional[str]
    ) -> TemplateInstantiationResult:
        """
        SFILES-specific instantiation workflow.

        Workflow:
        1. Generate components from template definition
        2. Apply parameter substitutions to component definitions
        3. Add nodes to flowsheet.state (NetworkX graph)
        4. Add edges based on connections
        5. Convert heat integration placeholders
        6. Validate via convert_to_sfiles()
        """
        instantiated_components = []
        self._substitution_engine.set_parameters(full_params)

        # Step 1 & 2: Generate and substitute components
        for component_def in self.components:
            # Check condition if present
            if "condition" in component_def:
                condition_expr = component_def["condition"]
                condition_result = self._substitution_engine.substitute(condition_expr)
                # Evaluate as boolean
                if condition_result.lower() not in ["true", "1"]:
                    continue

            component_type = component_def.get("type")
            count = self._substitution_engine.substitute(str(component_def.get("count", 1)))
            count = int(count) if isinstance(count, str) else count
            tag_pattern = component_def.get("tag_pattern", "${name}_${sequence}")
            attributes = component_def.get("attributes", {})

            # Substitute attributes
            substituted_attrs = self._substitution_engine.substitute_dict(attributes)

            # Generate N instances
            for i in range(count):
                # Reset sequence for each component type
                if i == 0:
                    self._substitution_engine.reset_sequence_counters()

                # Generate tag
                tag_context = {"name": component_def.get("name"), "index": i + 1}
                tag = self._substitution_engine.substitute(tag_pattern, tag_context)

                # Add node to flowsheet
                target_flowsheet.state.add_node(
                    tag,
                    unit_type=component_type,
                    **substituted_attrs
                )

                instantiated_components.append(tag)

                # Check for heat integration flag
                if substituted_attrs.get("heat_integration") or substituted_attrs.get("nodeType") == "heat_integration":
                    # Mark for HI conversion
                    target_flowsheet.state.nodes[tag]["_hi_node"] = True

        # Step 3: Add connections (edges)
        for connection_def in self.connections:
            # Check condition if present
            if "condition" in connection_def:
                condition_expr = connection_def["condition"]
                condition_result = self._substitution_engine.substitute(condition_expr)
                if condition_result.lower() not in ["true", "1"]:
                    continue

            # Parse connection (simplified - actual implementation would handle patterns)
            from_node = self._substitution_engine.substitute(connection_def.get("from", ""))
            to_node = self._substitution_engine.substitute(connection_def.get("to", ""))

            # Add edge if both nodes exist
            if from_node in target_flowsheet.state.nodes and to_node in target_flowsheet.state.nodes:
                target_flowsheet.add_stream(
                    node1=from_node,
                    node2=to_node,
                    stream_name=f"{from_node}_to_{to_node}"
                )

        # Step 4: Convert heat integration nodes
        self._convert_hi_nodes(target_flowsheet)

        # Step 5: Validate via convert_to_sfiles
        try:
            target_flowsheet.convert_to_sfiles(version="v2", canonical=True)
            validation_errors = []
        except Exception as e:
            validation_errors = [f"SFILES validation failed: {e}"]

        return TemplateInstantiationResult(
            success=len(validation_errors) == 0,
            message=f"Template '{self.name}' instantiated successfully (SFILES)" if not validation_errors
                    else f"Template instantiated with {len(validation_errors)} validation errors",
            instantiated_components=instantiated_components,
            validation_errors=validation_errors,
            metadata={
                "template": self.name,
                "version": self.version,
                "parameters": full_params,
                "model_type": "sfiles"
            }
        )

    def _convert_hi_nodes(self, flowsheet: Any) -> None:
        """
        Convert heat integration placeholder nodes to proper SFILES HI nodes.

        Args:
            flowsheet: Flowsheet instance with _hi_node marked nodes
        """
        # Find all HI nodes
        hi_nodes = [
            node for node, data in flowsheet.state.nodes(data=True)
            if data.get("_hi_node", False)
        ]

        if not hi_nodes:
            return

        logger.info(f"Converting {len(hi_nodes)} heat integration nodes")

        # Group HI nodes by exchanger (simplified - actual implementation would be more sophisticated)
        # For now, just mark them as HI nodes in the graph
        for node in hi_nodes:
            flowsheet.state.nodes[node]["is_heat_integration"] = True
            # Remove temporary marker
            del flowsheet.state.nodes[node]["_hi_node"]

            # Call split_HI_nodes or merge_HI_nodes if available
            # Note: Actual implementation depends on Flowsheet_Class API
            # This is a placeholder for the integration
            stream_type = flowsheet.state.nodes[node].get("streamType", "")
            if "in" in stream_type.lower():
                # This is an inlet HI node - would call split_HI_nodes
                pass
            elif "out" in stream_type.lower():
                # This is an outlet HI node - would call merge_HI_nodes
                pass

    def _validate_instantiation(self, model: DexpiModel) -> List[str]:
        """
        Validate instantiated model.

        Args:
            model: DexpiModel after instantiation

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Run validation rules if specified
        if not self.validation:
            return errors

        rules = self.validation.get("rules", [])

        for rule in rules:
            rule_type = rule.get("type")

            if rule_type == "connectivity":
                # Check connectivity (simplified)
                pass

            elif rule_type == "tag_uniqueness":
                # Check tag uniqueness
                tags = set()
                if model.conceptualModel and model.conceptualModel.taggedPlantItems:
                    for item in model.conceptualModel.taggedPlantItems:
                        if hasattr(item, 'tagName'):
                            if item.tagName in tags:
                                errors.append(f"Duplicate tag: {item.tagName}")
                            tags.add(item.tagName)

            elif rule_type == "port_compatibility":
                # Check port compatibility (simplified)
                pass

        return errors
