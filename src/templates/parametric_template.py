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
from pydexpi.syndata.pattern import Pattern as DexpiPattern
from pydexpi.syndata.connector_renaming import ConnectorRenamingConvention
from pydexpi.toolkits import model_toolkit as mt

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

            self._dexpi_pattern: Optional[DexpiPattern] = None
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
        target_model: DexpiModel,
        parameters: Dict[str, Any],
        connection_point: Optional[str] = None
    ) -> TemplateInstantiationResult:
        """
        Instantiate template into target model.

        Workflow (Codex-recommended):
        1. Validate parameters
        2. Load/create base DexpiPattern
        3. Clone via Pattern.copy_pattern()
        4. Apply parameter substitutions
        5. Feed to ConnectorRenamingConvention
        6. Import into target model
        7. Validate result

        Args:
            target_model: Model to instantiate into
            parameters: Parameter values
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

            logger.info(f"Instantiating template '{self.name}' with parameters: {full_params}")

            # Step 2: Get base pattern
            base_pattern = self._get_base_pattern()

            # Step 3: Clone pattern (Codex: "Clone via Pattern.copy_pattern")
            cloned_pattern = base_pattern.copy_pattern()

            # Step 4: Apply parameter substitutions
            substituted_model = self._substitution_engine.substitute_model(
                cloned_pattern.model,
                full_params
            )

            # Step 5: Apply connector renaming convention
            # This generates unique tags based on sequence
            prefix = full_params.get("area", self.category.upper())
            renaming_convention = ConnectorRenamingConvention(
                prefix=prefix,
                start_index=1
            )

            # Apply renaming to connectors
            for connector in cloned_pattern.connectors:
                connector.apply_renaming_convention(renaming_convention)

            # Step 6: Import into target model
            # Use pyDEXPI's model_toolkit.import_model_contents
            instantiated_components = mt.import_model_contents(
                source_model=substituted_model,
                target_model=target_model,
                preserve_ids=False  # Generate new IDs
            )

            # Step 7: Validate result
            validation_errors = self._validate_instantiation(target_model)

            return TemplateInstantiationResult(
                success=len(validation_errors) == 0,
                message=f"Template '{self.name}' instantiated successfully" if not validation_errors
                        else f"Template instantiated with {len(validation_errors)} validation errors",
                instantiated_components=[comp.tagName for comp in instantiated_components if hasattr(comp, 'tagName')],
                validation_errors=validation_errors,
                metadata={
                    "template": self.name,
                    "version": self.version,
                    "parameters": full_params
                }
            )

        except ParameterValidationError:
            raise

        except Exception as e:
            logger.exception(f"Template instantiation failed: {e}")
            raise TemplateInstantiationError(f"Failed to instantiate template: {e}")

    def _get_base_pattern(self) -> DexpiPattern:
        """
        Load or create base DexpiPattern.

        Returns:
            DexpiPattern instance

        Raises:
            TemplateLoadError: If pattern cannot be loaded
        """
        if self._dexpi_pattern is not None:
            return self._dexpi_pattern

        if self.base_pattern is None:
            # Create empty pattern
            empty_model = DexpiModel()
            self._dexpi_pattern = DexpiPattern(model=empty_model)
            return self._dexpi_pattern

        # Load from file
        if "file" in self.base_pattern:
            pattern_file = Path(self.base_pattern["file"])

            if not pattern_file.exists():
                raise TemplateLoadError(f"Pattern file not found: {pattern_file}")

            # Load DEXPI XML and wrap in Pattern
            from pydexpi.loaders import ProteusSerializer
            serializer = ProteusSerializer()

            with open(pattern_file, 'r') as f:
                model = serializer.loads(f.read())

            self._dexpi_pattern = DexpiPattern(model=model)
            return self._dexpi_pattern

        # Inline model definition
        elif "model" in self.base_pattern:
            # Convert dict to DexpiModel (simplified - actual implementation would use proper deserialization)
            model = DexpiModel()
            self._dexpi_pattern = DexpiPattern(model=model)
            return self._dexpi_pattern

        else:
            raise TemplateLoadError("base_pattern must have either 'file' or 'model' key")

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
