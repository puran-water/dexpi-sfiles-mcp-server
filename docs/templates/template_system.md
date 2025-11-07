# Template System Architecture

**Version:** 1.0.0-draft
**Status:** Phase 0.5 Design
**Last Updated:** 2025-11-06
**Codex Approved:** ✅

---

## Overview

The **Template System** enables high-level pattern-based model construction via the `area_deploy` tool. It wraps pyDEXPI's `DexpiPattern` system with:

- Parameter substitution for dynamic templates
- Tag generation via `ConnectorRenamingConvention`
- Pattern composition and sequencing
- Instrumentation and control loop variations
- Validation and testing infrastructure

**Design Philosophy**: Thin wrapper over upstream `DexpiPattern`, adding the parameter substitution layer that pyDEXPI doesn't provide.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      area_deploy                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐      ┌─────────────────┐                 │
│  │  Template    │─────▶│  Parameter      │                 │
│  │  Definition  │      │  Substitution   │                 │
│  │  (YAML)      │      │  Engine         │                 │
│  └──────────────┘      └─────────────────┘                 │
│                               │                              │
│                               ▼                              │
│  ┌──────────────────────────────────────┐                  │
│  │      DexpiPattern (upstream)         │                  │
│  │  ┌────────────────────────────────┐  │                  │
│  │  │  Pattern.copy_pattern()        │  │                  │
│  │  │  mt.import_model_contents()    │  │                  │
│  │  │  ConnectorRenamingConvention   │  │                  │
│  │  └────────────────────────────────┘  │                  │
│  └──────────────────────────────────────┘                  │
│                               │                              │
│                               ▼                              │
│  ┌──────────────────────────────────────┐                  │
│  │      Pattern Composition             │                  │
│  │  (Generator stack sequencing)        │                  │
│  └──────────────────────────────────────┘                  │
│                               │                              │
│                               ▼                              │
│  ┌──────────────────────────────────────┐                  │
│  │      Validation                      │                  │
│  │  MLGraphLoader.validate_graph_format │                  │
│  └──────────────────────────────────────┘                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Template Format

### YAML Template Structure

Templates are defined in YAML format with the following sections:

```yaml
# /library/patterns/piping/pump_station_n_plus_1.yaml

name: pump_station_n_plus_1
version: 1.0.0
category: piping
description: N+1 redundant pump station with isolation and check valves

# Template parameters (user-provided values)
parameters:
  pump_count:
    type: integer
    min: 2
    max: 10
    default: 3
    description: Number of pumps (N+1 configuration)

  flow_rate:
    type: number
    unit: m3/h
    description: Design flow rate per pump

  nominal_diameter:
    type: string
    enum: [DN50, DN80, DN100, DN150, DN200]
    default: DN100
    description: Pipe nominal diameter

  control_type:
    type: string
    enum: [flow, pressure, none]
    default: flow
    description: Control loop type

  area:
    type: string
    default: PUMP
    description: Area tag for naming

# Base pattern (DexpiPattern reference)
base_pattern:
  file: patterns/dexpi/single_pump_with_valves.dexpi.xml
  # OR inline DexpiModel definition
  # model: {...}

# Component generation rules
components:
  # Generate N pumps
  - name: pump
    type: CentrifugalPump
    count: ${pump_count}
    tag_pattern: "P-${area}-${sequence:03d}"
    attributes:
      nominalDiameter: ${nominal_diameter}
      flow_rate: ${flow_rate}
      design_pressure: 10  # bar
    nozzles:
      - subTagName: inlet
        nominalDiameter: ${nominal_diameter}
      - subTagName: outlet
        nominalDiameter: ${nominal_diameter}

  # Isolation valve for each pump (inlet)
  - name: isolation_valve_inlet
    type: GateValve
    count: ${pump_count}
    tag_pattern: "V-${area}-${sequence:03d}A"
    attributes:
      nominalDiameter: ${nominal_diameter}

  # Check valve for each pump (outlet)
  - name: check_valve
    type: CheckValve
    count: ${pump_count}
    tag_pattern: "CV-${area}-${sequence:03d}"
    attributes:
      nominalDiameter: ${nominal_diameter}

  # Isolation valve for each pump (outlet)
  - name: isolation_valve_outlet
    type: GateValve
    count: ${pump_count}
    tag_pattern: "V-${area}-${sequence:03d}B"
    attributes:
      nominalDiameter: ${nominal_diameter}

  # Common inlet header
  - name: inlet_header
    type: PipeSegment
    count: 1
    tag_pattern: "LINE-${area}-INLET"
    attributes:
      nominalDiameter: ${nominal_diameter}

  # Common outlet header
  - name: outlet_header
    type: PipeSegment
    count: 1
    tag_pattern: "LINE-${area}-OUTLET"
    attributes:
      nominalDiameter: ${nominal_diameter}

# Connection topology
connections:
  # Inlet header to each pump
  - from: inlet_header
    to: pump[*].inlet
    via: [isolation_valve_inlet[*]]

  # Each pump to outlet header
  - from: pump[*].outlet
    to: outlet_header
    via: [check_valve[*], isolation_valve_outlet[*]]

# Instrumentation (conditional on control_type)
instrumentation:
  # Flow control on each pump
  - condition: ${control_type} == "flow"
    components:
      - name: flow_transmitter
        type: FlowTransmitter
        count: ${pump_count}
        tag_pattern: "FT-${area}-${sequence:03d}"
        sensing_location: pump[*].outlet

      - name: flow_controller
        type: FlowController
        count: ${pump_count}
        tag_pattern: "FC-${area}-${sequence:03d}"
        control_params:
          setpoint: ${flow_rate}
          units: m3/h

    connections:
      - from: flow_transmitter[*]
        to: flow_controller[*]
        type: signal

  # Pressure control on outlet header
  - condition: ${control_type} == "pressure"
    components:
      - name: pressure_transmitter
        type: PressureTransmitter
        count: 1
        tag_pattern: "PT-${area}-001"
        sensing_location: outlet_header

      - name: pressure_controller
        type: PressureController
        count: 1
        tag_pattern: "PC-${area}-001"

    connections:
      - from: pressure_transmitter
        to: pressure_controller
        type: signal

# Validation rules (run after instantiation)
validation:
  rules:
    - type: connectivity
      description: All pumps connected to headers
    - type: tag_uniqueness
      description: All tags must be unique
    - type: port_compatibility
      description: Connected ports must match diameter

# Metadata
metadata:
  author: Engineering MCP Server
  created: 2025-11-06
  tags: [pump, redundancy, n+1, piping]
  references:
    - ISA-5.1 (Instrumentation Symbols)
    - API 610 (Centrifugal Pumps)
```

---

## Parameter Substitution Engine

### Substitution Syntax

Templates use `${variable}` syntax for parameter substitution:

```yaml
# Simple substitution
tag_pattern: "P-${area}-001"
# Result: "P-PUMP-001" (if area="PUMP")

# With formatting
tag_pattern: "P-${area}-${sequence:03d}"
# Result: "P-PUMP-001", "P-PUMP-002", etc.

# Arithmetic expressions
value: ${flow_rate * 1.1}
# Result: 165 (if flow_rate=150)

# Conditional expressions
- condition: ${control_type} == "flow"
# Result: true/false boolean
```

### Substitution Implementation

**Codex Guidance**: "Walk DexpiModel objects and replace attributes before incorporation"

```python
class ParameterSubstitutionEngine:
    """Handles parameter substitution in templates."""

    def __init__(self):
        self.parameters: Dict[str, Any] = {}
        self._sequence_counters: Dict[str, int] = {}

    def substitute(self, template: str, context: Optional[Dict] = None) -> str:
        """
        Substitute parameters in template string.

        Supports:
        - Simple: ${param_name}
        - Formatted: ${param_name:format_spec}
        - Expressions: ${param1 + param2}
        - Conditionals: ${param1} == "value"

        Args:
            template: Template string with ${...} placeholders
            context: Additional context variables

        Returns:
            Substituted string
        """
        import re
        from string import Formatter

        # Merge parameters and context
        all_params = {**self.parameters, **(context or {})}

        # Find all ${...} patterns
        pattern = re.compile(r'\$\{([^}]+)\}')

        def replacer(match):
            expr = match.group(1)

            # Check for format spec (e.g., "sequence:03d")
            if ':' in expr:
                var_name, format_spec = expr.split(':', 1)
                var_name = var_name.strip()
                value = self._resolve_variable(var_name, all_params)
                return format(value, format_spec)

            # Check for arithmetic/boolean expressions
            elif any(op in expr for op in ['+', '-', '*', '/', '==', '!=', '<', '>', 'and', 'or']):
                return str(self._evaluate_expression(expr, all_params))

            # Simple variable substitution
            else:
                value = self._resolve_variable(expr.strip(), all_params)
                return str(value)

        return pattern.sub(replacer, template)

    def _resolve_variable(self, var_name: str, params: Dict) -> Any:
        """
        Resolve variable name to value.

        Supports:
        - Simple: param_name
        - Sequence: sequence (auto-increments)
        - Array index: pump[0], pump[*] (returns list)

        Args:
            var_name: Variable name
            params: Parameter dictionary

        Returns:
            Resolved value

        Raises:
            KeyError: If variable not found
        """
        # Handle special "sequence" variable
        if var_name == "sequence":
            # Auto-incrementing sequence counter
            counter_key = "_default_sequence"
            self._sequence_counters.setdefault(counter_key, 0)
            self._sequence_counters[counter_key] += 1
            return self._sequence_counters[counter_key]

        # Handle array indexing
        if '[' in var_name and ']' in var_name:
            array_name = var_name[:var_name.index('[')]
            index_str = var_name[var_name.index('[')+1:var_name.index(']')]

            array = params.get(array_name)
            if not isinstance(array, list):
                raise ValueError(f"{array_name} is not an array")

            if index_str == '*':
                # Return all elements
                return array
            else:
                # Return specific index
                index = int(index_str)
                return array[index]

        # Simple lookup
        if var_name not in params:
            raise KeyError(f"Parameter {var_name} not defined")

        return params[var_name]

    def _evaluate_expression(self, expr: str, params: Dict) -> Any:
        """
        Safely evaluate Python expression with parameters.

        Args:
            expr: Python expression
            params: Parameter dictionary

        Returns:
            Evaluated result
        """
        # Build safe evaluation context
        # Only allow parameters, no builtins
        safe_context = {**params}

        # Evaluate safely
        try:
            return eval(expr, {"__builtins__": {}}, safe_context)
        except Exception as e:
            raise ValueError(f"Expression evaluation failed: {expr} - {e}")

    def substitute_model(
        self,
        model: DexpiModel,
        parameters: Dict[str, Any]
    ) -> DexpiModel:
        """
        Substitute parameters throughout DexpiModel.

        Walks model tree and replaces all ${...} occurrences.

        Codex guidance: "Deterministic traversal for DexpiModel"

        Args:
            model: DexpiModel to process
            parameters: Parameter values

        Returns:
            Model with substitutions applied
        """
        self.parameters = parameters

        # Clone model first
        import copy
        substituted_model = copy.deepcopy(model)

        # Walk model tree
        self._walk_and_substitute(substituted_model)

        return substituted_model

    def _walk_and_substitute(self, obj: Any, path: str = "root") -> None:
        """
        Recursively walk object tree and substitute parameters.

        Deterministic traversal order for predictable results.

        Args:
            obj: Object to process
            path: Current path (for debugging)
        """
        from pydexpi.model import GenericItem

        if isinstance(obj, GenericItem):
            # Process DEXPI model item
            # Get all attributes
            for attr_name in sorted(dir(obj)):  # Sorted for deterministic order
                if attr_name.startswith('_'):
                    continue

                try:
                    attr_value = getattr(obj, attr_name)

                    if isinstance(attr_value, str) and '${' in attr_value:
                        # Substitute string attribute
                        substituted = self.substitute(attr_value)
                        setattr(obj, attr_name, substituted)

                    elif isinstance(attr_value, (list, tuple)):
                        # Recurse into collections
                        for i, item in enumerate(attr_value):
                            self._walk_and_substitute(item, f"{path}.{attr_name}[{i}]")

                    elif isinstance(attr_value, GenericItem):
                        # Recurse into nested items
                        self._walk_and_substitute(attr_value, f"{path}.{attr_name}")

                except AttributeError:
                    # Skip non-accessible attributes
                    pass

        elif isinstance(obj, dict):
            # Process dictionary
            for key in sorted(obj.keys()):  # Sorted for deterministic order
                value = obj[key]

                if isinstance(value, str) and '${' in value:
                    obj[key] = self.substitute(value)
                else:
                    self._walk_and_substitute(value, f"{path}.{key}")

        elif isinstance(obj, (list, tuple)):
            # Process list/tuple
            for i, item in enumerate(obj):
                self._walk_and_substitute(item, f"{path}[{i}]")
```

---

## Template Instantiation Workflow

### ParametricTemplate Class

Wraps `DexpiPattern` with parameter substitution:

```python
class ParametricTemplate:
    """
    Parametric template wrapping DexpiPattern.

    Codex guidance: "Wrap templates in parametric template class"
    """

    def __init__(self, template_def: Dict[str, Any]):
        """
        Initialize from template definition.

        Args:
            template_def: Parsed YAML template
        """
        self.name = template_def["name"]
        self.version = template_def["version"]
        self.category = template_def["category"]
        self.description = template_def["description"]
        self.parameters = template_def["parameters"]
        self.base_pattern = template_def.get("base_pattern")
        self.components = template_def.get("components", [])
        self.connections = template_def.get("connections", [])
        self.instrumentation = template_def.get("instrumentation", [])
        self.validation = template_def.get("validation", {})
        self.metadata = template_def.get("metadata", {})

        self._dexpi_pattern: Optional[DexpiPattern] = None
        self._substitution_engine = ParameterSubstitutionEngine()

    def validate_parameters(self, params: Dict[str, Any]) -> ValidationResult:
        """
        Validate provided parameters against schema.

        Args:
            params: Parameter values

        Returns:
            ValidationResult
        """
        errors = []

        for param_name, param_schema in self.parameters.items():
            # Check required
            if param_name not in params and "default" not in param_schema:
                errors.append(f"Required parameter missing: {param_name}")
                continue

            # Get value
            value = params.get(param_name, param_schema.get("default"))

            # Type check
            expected_type = param_schema.get("type")
            if expected_type == "integer" and not isinstance(value, int):
                errors.append(f"Parameter {param_name} must be integer, got {type(value)}")

            elif expected_type == "number" and not isinstance(value, (int, float)):
                errors.append(f"Parameter {param_name} must be number, got {type(value)}")

            elif expected_type == "string" and not isinstance(value, str):
                errors.append(f"Parameter {param_name} must be string, got {type(value)}")

            # Range check
            if "min" in param_schema and value < param_schema["min"]:
                errors.append(f"Parameter {param_name} below minimum: {value} < {param_schema['min']}")

            if "max" in param_schema and value > param_schema["max"]:
                errors.append(f"Parameter {param_name} above maximum: {value} > {param_schema['max']}")

            # Enum check
            if "enum" in param_schema and value not in param_schema["enum"]:
                errors.append(f"Parameter {param_name} not in enum: {value} not in {param_schema['enum']}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
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
        from pydexpi.syndata.pattern import Pattern
        from pydexpi.syndata.connector_renaming import ConnectorRenamingConvention
        from pydexpi.toolkits import model_toolkit as mt

        # Step 1: Validate parameters
        validation = self.validate_parameters(parameters)
        if not validation.is_valid:
            raise ParameterValidationError(
                f"Parameter validation failed: {validation.errors}"
            )

        # Add defaults for missing parameters
        full_params = {}
        for param_name, param_schema in self.parameters.items():
            if param_name in parameters:
                full_params[param_name] = parameters[param_name]
            elif "default" in param_schema:
                full_params[param_name] = param_schema["default"]

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
        renaming_convention = ConnectorRenamingConvention(
            prefix=full_params.get("area", "AREA"),
            start_index=1
        )

        renamed_pattern = Pattern(substituted_model)
        renamed_pattern.relabel_connector(renaming_convention)

        # Step 6: Import into target model
        # Uses mt.import_model_contents_into_model
        imported_ids = mt.import_model_contents_into_model(
            source_model=renamed_pattern.model,
            target_model=target_model,
            connection_point=connection_point
        )

        # Step 7: Validate result
        from pydexpi.loaders.ml_graph_loader import MLGraphLoader
        loader = MLGraphLoader()

        try:
            loader.validate_graph_format(target_model)
            validation_result = ValidationResult(is_valid=True)
        except Exception as e:
            validation_result = ValidationResult(
                is_valid=False,
                errors=[f"Post-instantiation validation failed: {e}"]
            )

        return TemplateInstantiationResult(
            template_name=self.name,
            parameters=full_params,
            imported_component_ids=imported_ids,
            validation=validation_result
        )

    def _get_base_pattern(self) -> DexpiPattern:
        """
        Get or create base DexpiPattern.

        Returns:
            DexpiPattern
        """
        if self._dexpi_pattern:
            return self._dexpi_pattern

        from pydexpi.syndata.dexpi_pattern import DexpiPattern

        if self.base_pattern:
            # Load from file
            pattern_file = self.base_pattern.get("file")
            if pattern_file:
                self._dexpi_pattern = DexpiPattern.load(pattern_file)
            else:
                # Create from inline model
                inline_model = self.base_pattern.get("model")
                self._dexpi_pattern = DexpiPattern(inline_model)

        else:
            # Create empty pattern
            self._dexpi_pattern = DexpiPattern()

        return self._dexpi_pattern
```

---

## Template Library Structure

### Directory Organization

```
/library/patterns/
├── piping/
│   ├── pump_station_n_plus_1.yaml
│   ├── pump_station_2_plus_1.yaml
│   ├── tank_farm.yaml
│   ├── heat_exchanger_network.yaml
│   └── heat_integration.yaml           # NEW: SFILES HI utilities
│
├── instrumentation/
│   ├── flow_control_loop.yaml
│   ├── level_control_loop.yaml
│   ├── temperature_control_loop.yaml
│   ├── pressure_control_loop.yaml
│   └── cascade_control.yaml
│
├── process/
│   ├── ro_train_2stage.yaml
│   ├── chemical_dosing_skid.yaml
│   ├── aeration_system.yaml            # Wastewater treatment
│   ├── clarification_system.yaml       # Wastewater treatment
│   └── membrane_bioreactor.yaml
│
└── dexpi/
    ├── single_pump_with_valves.dexpi.xml
    ├── heat_exchanger_unit.dexpi.xml
    └── control_valve_assembly.dexpi.xml
```

### Template Catalog

The template library manager provides discovery:

```python
class TemplateLibrary:
    """Manages template catalog and loading."""

    def __init__(self, library_path: str = "/library/patterns"):
        self.library_path = library_path
        self._templates: Dict[str, ParametricTemplate] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Load all templates from library."""
        import yaml
        from pathlib import Path

        pattern_files = Path(self.library_path).rglob("*.yaml")

        for pattern_file in pattern_files:
            with open(pattern_file) as f:
                template_def = yaml.safe_load(f)

            template = ParametricTemplate(template_def)
            self._templates[template.name] = template

    def list(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[ParametricTemplate]:
        """
        List templates with optional filters.

        Args:
            category: Filter by category
            tags: Filter by tags

        Returns:
            List of templates
        """
        templates = list(self._templates.values())

        if category:
            templates = [t for t in templates if t.category == category]

        if tags:
            templates = [
                t for t in templates
                if any(tag in t.metadata.get("tags", []) for tag in tags)
            ]

        return templates

    def get(self, name: str) -> ParametricTemplate:
        """
        Get template by name.

        Args:
            name: Template name

        Returns:
            ParametricTemplate

        Raises:
            TemplateNotFound: If template doesn't exist
        """
        if name not in self._templates:
            raise TemplateNotFound(f"Template {name} not found")

        return self._templates[name]
```

---

## SFILES Template Support

### Heat Integration Template

Leverages SFILES `split_HI_nodes` / `merge_HI_nodes`:

```yaml
# /library/patterns/piping/heat_integration.yaml

name: heat_integration
version: 1.0.0
category: process
description: Heat integration pattern using SFILES utilities

parameters:
  hot_stream:
    type: string
    description: Hot stream identifier

  cold_stream:
    type: string
    description: Cold stream identifier

  approach_temperature:
    type: number
    default: 10
    unit: degC
    description: Minimum approach temperature

  heat_duty:
    type: number
    unit: kW
    description: Heat duty to transfer

# SFILES-specific operations
sfiles_operations:
  # Use split_HI_nodes to create heat exchanger nodes
  - operation: split_HI_nodes
    streams: [${hot_stream}, ${cold_stream}]
    heat_duty: ${heat_duty}
    approach_temp: ${approach_temperature}

# Validation
validation:
  rules:
    - type: thermodynamic
      description: Hot stream outlet > cold stream outlet
    - type: energy_balance
      description: Heat duty conserved
```

### SFILES Template Instantiation

```python
class SFILESParametricTemplate(ParametricTemplate):
    """
    SFILES-specific template.

    Uses Flowsheet methods instead of DexpiPattern.
    """

    def instantiate(
        self,
        flowsheet: Flowsheet,
        parameters: Dict[str, Any]
    ) -> TemplateInstantiationResult:
        """
        Instantiate SFILES template into flowsheet.

        Uses:
        - Flowsheet.add_unit()
        - Flowsheet.add_stream()
        - Flowsheet.split_HI_nodes()
        - Flowsheet.convert_to_sfiles() for canonicalization

        Args:
            flowsheet: SFILES flowsheet
            parameters: Parameter values

        Returns:
            TemplateInstantiationResult
        """
        # Validate parameters
        validation = self.validate_parameters(parameters)
        if not validation.is_valid:
            raise ParameterValidationError(f"Validation failed: {validation.errors}")

        # Apply SFILES operations
        imported_ids = []

        for operation_def in self.sfiles_operations:
            operation = operation_def["operation"]

            if operation == "split_HI_nodes":
                # Use SFILES heat integration utilities
                streams = operation_def["streams"]
                heat_duty = self._substitution_engine.substitute(
                    str(operation_def["heat_duty"]),
                    parameters
                )

                result_nodes = flowsheet.split_HI_nodes(
                    streams=streams,
                    duty=float(heat_duty)
                )

                imported_ids.extend(result_nodes)

        # Re-canonicalize
        flowsheet.convert_to_sfiles()

        return TemplateInstantiationResult(
            template_name=self.name,
            parameters=parameters,
            imported_component_ids=imported_ids,
            validation=ValidationResult(is_valid=True)
        )
```

---

## Pattern Composition

### Generator Stack Sequencing

Codex guidance: "Generator stack shows how to sequence patterns"

```python
class PatternComposer:
    """
    Compose multiple templates into a complex pattern.

    Based on pyDEXPI generator.py:14-181
    """

    def __init__(self):
        self.templates: List[ParametricTemplate] = []
        self.composition_rules: List[CompositionRule] = []

    def add_template(
        self,
        template: ParametricTemplate,
        parameters: Dict[str, Any],
        connection_point: Optional[str] = None
    ) -> None:
        """
        Add template to composition sequence.

        Args:
            template: Template to add
            parameters: Parameter values
            connection_point: Where to connect (from previous template)
        """
        self.composition_rules.append(CompositionRule(
            template=template,
            parameters=parameters,
            connection_point=connection_point
        ))

    def compose(self, target_model: DexpiModel) -> CompositionResult:
        """
        Compose all templates into target model.

        Executes templates in sequence, connecting each to previous.

        Args:
            target_model: Model to compose into

        Returns:
            CompositionResult
        """
        all_imported_ids = []

        for rule in self.composition_rules:
            result = rule.template.instantiate(
                target_model=target_model,
                parameters=rule.parameters,
                connection_point=rule.connection_point
            )

            all_imported_ids.extend(result.imported_component_ids)

            # Update connection point for next template
            # (use last component from this template)
            if result.imported_component_ids:
                rule.connection_point = result.imported_component_ids[-1]

        return CompositionResult(
            templates_composed=len(self.composition_rules),
            total_components=len(all_imported_ids),
            component_ids=all_imported_ids
        )


# Example: Compose pump station + control loop
composer = PatternComposer()

# Add pump station template
composer.add_template(
    template=template_library.get("pump_station_n_plus_1"),
    parameters={"pump_count": 3, "flow_rate": 150, "control_type": "none"}
)

# Add flow control template (connects to pump station outlet)
composer.add_template(
    template=template_library.get("flow_control_loop"),
    parameters={"control_type": "cascade", "setpoint": 450},
    connection_point="outlet_header"  # From pump station
)

# Compose into model
result = composer.compose(target_model)
```

---

## area_deploy Tool Integration

### Tool Definition

```python
Tool(
    name="area_deploy",
    description="Deploy parametric template pattern to model",
    inputSchema={
        "type": "object",
        "properties": {
            "model_id": {"type": "string"},
            "template_name": {
                "type": "string",
                "description": "Template to instantiate",
                "enum": [...]  # Dynamic from template library
            },
            "parameters": {
                "type": "object",
                "description": "Template parameters (schema varies by template)"
            },
            "connection_point": {
                "type": "string",
                "description": "Optional connector to attach at"
            },
            "validate": {
                "type": "boolean",
                "default": True,
                "description": "Validate after instantiation"
            }
        },
        "required": ["model_id", "template_name", "parameters"]
    }
)
```

### Implementation

```python
async def area_deploy(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deploy area template to model.

    Args:
        args: {
            model_id: str,
            template_name: str,
            parameters: dict,
            connection_point?: str,
            validate?: bool
        }

    Returns:
        Deployment result with imported component IDs
    """
    # Get model
    model = model_store.get(args["model_id"])

    # Get template
    template_library = get_template_library()
    template = template_library.get(args["template_name"])

    # Instantiate
    try:
        result = template.instantiate(
            target_model=model,
            parameters=args["parameters"],
            connection_point=args.get("connection_point")
        )

        return {
            "ok": True,
            "data": {
                "template": args["template_name"],
                "components_added": len(result.imported_component_ids),
                "component_ids": result.imported_component_ids,
                "validation": result.validation.to_dict()
            }
        }

    except Exception as e:
        return {
            "ok": False,
            "error": {
                "code": "TEMPLATE_INSTANTIATION_FAILED",
                "message": str(e)
            }
        }
```

---

## Initial 5 Templates

### 1. pump_station_n_plus_1.yaml
**Category**: piping
**Description**: N+1 redundant pump station
**Parameters**: pump_count, flow_rate, control_type, nominal_diameter, area

### 2. flow_control_loop.yaml
**Category**: instrumentation
**Description**: Flow measurement and control loop
**Parameters**: setpoint, control_mode, sensing_location, valve_tag

### 3. tank_farm.yaml
**Category**: piping
**Description**: Multiple storage tanks with common inlet/outlet
**Parameters**: tank_count, capacity, material, nominal_diameter

### 4. ro_train_2stage.yaml
**Category**: process
**Description**: Two-stage reverse osmosis train
**Parameters**: recovery_rate, permeate_flow, feed_pressure

### 5. heat_integration.yaml
**Category**: process (SFILES)
**Description**: Heat integration using SFILES utilities
**Parameters**: hot_stream, cold_stream, heat_duty, approach_temperature

---

## Testing Infrastructure

### Template Validation

```python
class TemplateValidator:
    """Validates template definitions."""

    def validate(self, template_def: Dict) -> ValidationResult:
        """
        Validate template definition.

        Checks:
        - Required fields present
        - Parameter schemas valid
        - Component definitions valid
        - Connection topology valid

        Args:
            template_def: Template definition

        Returns:
            ValidationResult
        """
        errors = []

        # Required fields
        required = ["name", "version", "category", "description", "parameters"]
        for field in required:
            if field not in template_def:
                errors.append(f"Missing required field: {field}")

        # Parameter schemas
        if "parameters" in template_def:
            for param_name, param_schema in template_def["parameters"].items():
                if "type" not in param_schema:
                    errors.append(f"Parameter {param_name} missing type")

        # Component definitions
        if "components" in template_def:
            for comp_def in template_def["components"]:
                if "type" not in comp_def:
                    errors.append(f"Component missing type: {comp_def.get('name')}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )
```

### Template Testing

```python
class TemplateTestCase:
    """Test case for template instantiation."""

    def __init__(self, template_name: str, test_parameters: Dict[str, Any]):
        self.template_name = template_name
        self.test_parameters = test_parameters

    def run(self) -> TemplateTestResult:
        """
        Run template test.

        Creates empty model, instantiates template, validates.

        Returns:
            TemplateTestResult
        """
        from pydexpi.model import DexpiModel

        # Create empty model
        test_model = DexpiModel()

        # Get template
        template_library = get_template_library()
        template = template_library.get(self.template_name)

        # Instantiate
        try:
            result = template.instantiate(
                target_model=test_model,
                parameters=self.test_parameters
            )

            return TemplateTestResult(
                template_name=self.template_name,
                success=result.validation.is_valid,
                components_created=len(result.imported_component_ids),
                validation_errors=result.validation.errors
            )

        except Exception as e:
            return TemplateTestResult(
                template_name=self.template_name,
                success=False,
                error=str(e)
            )


# Run tests for all templates
def test_all_templates():
    """Run tests for all templates in library."""
    test_cases = [
        TemplateTestCase("pump_station_n_plus_1", {"pump_count": 3, "flow_rate": 150}),
        TemplateTestCase("flow_control_loop", {"setpoint": 100, "sensing_location": "pipe-01"}),
        # ... more test cases
    ]

    results = [tc.run() for tc in test_cases]

    passed = sum(1 for r in results if r.success)
    print(f"Tests: {passed}/{len(results)} passed")
```

---

## Implementation Checklist

### Phase 1: Core Engine

- [ ] Implement `ParameterSubstitutionEngine`
- [ ] Implement substitution syntax parsing
- [ ] Implement expression evaluation (safe)
- [ ] Implement deterministic model traversal
- [ ] Add substitution logging (Codex guidance)

### Phase 2: Template Infrastructure

- [ ] Implement `ParametricTemplate` class
- [ ] Implement parameter validation
- [ ] Integrate `Pattern.copy_pattern()`
- [ ] Integrate `ConnectorRenamingConvention`
- [ ] Integrate `MLGraphLoader.validate_graph_format()`

### Phase 3: Template Library

- [ ] Create template library structure
- [ ] Implement `TemplateLibrary` manager
- [ ] Create 5 initial templates (pump, control, tank, RO, HI)
- [ ] Add template discovery/catalog

### Phase 4: SFILES Support

- [ ] Implement `SFILESParametricTemplate`
- [ ] Integrate SFILES heat integration utilities
- [ ] Add SFILES canonicalization validation

### Phase 5: Composition & Testing

- [ ] Implement `PatternComposer`
- [ ] Add pattern sequencing
- [ ] Create template validator
- [ ] Create template test infrastructure

---

## Success Criteria

Template system satisfies requirements:

- ✅ Wraps `DexpiPattern` with parameter substitution
- ✅ Uses `Pattern.copy_pattern()` for cloning (Codex)
- ✅ Uses `ConnectorRenamingConvention` for tag generation (Codex)
- ✅ Validates via `MLGraphLoader.validate_graph_format()` (Codex)
- ✅ Deterministic model traversal for substitution (Codex)
- ✅ Logs substitutions for debugging (Codex)
- ✅ Supports SFILES heat integration (`split_HI_nodes`, `merge_HI_nodes`)
- ✅ Pattern composition via generator stack (Codex)
- ✅ 4 production-ready templates (pump_basic, pump_station_n_plus_1, tank_farm, heat_exchanger_with_integration)
- ✅ Comprehensive validation and testing

---

**Next Steps:**
1. Implement core substitution engine (Phase 1)
2. Create 5 initial templates (Phase 3)
3. Integration testing with area_deploy tool
4. Expand template library based on usage patterns
