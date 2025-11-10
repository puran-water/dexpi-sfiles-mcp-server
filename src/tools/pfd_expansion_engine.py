"""PFD Expansion Engine for BFD→PFD conversion.

This module implements the expansion of BFD blocks into PFD equipment groups
using the template system defined in Sprint 3.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

CONDITION_TOKEN_PATTERN = re.compile(r"\$\{([^}|]+)(?:\|([^}]+))?\}")
TRUTHY_CONDITION_VALUES = {"true", "yes", "1", "on"}

# Import pyDEXPI equipment classes - REQUIRED dependency
try:
    from pydexpi.dexpi_classes.equipment import (
        Tank, CentrifugalPump, Mixer, Filter, ProcessColumn,
        CustomEquipment, Centrifuge, PressureVessel,
        HeatExchanger, Pump, Vessel, Equipment,
        AlternatingCurrentMotor, Motor, CustomMotor,
        DirectCurrentMotor
    )
    from pydexpi.dexpi_classes.piping import (
        ButterflyValve, GateValve, CheckValve, OperatedValve,
        BallValve, GlobeValve, PlugValve
    )
    from pydexpi.dexpi_classes.instrumentation import (
        ProcessSignalGeneratingSystem, ProcessInstrumentationFunction, ProcessControlFunction
    )
    # Try to import additional equipment types (may not exist in all pyDEXPI versions)
    try:
        from pydexpi.dexpi_classes.equipment import CentrifugalBlower
    except ImportError:
        raise ImportError(
            "CentrifugalBlower class not found in pydexpi.dexpi_classes.equipment. "
            "This equipment type may not be available in your version of pyDEXPI. "
            "Check available equipment types with schema_query(operation='list_classes', schema_type='dexpi', category='equipment')"
        )

    try:
        from pydexpi.dexpi_classes.equipment import GearBox
    except ImportError:
        raise ImportError(
            "GearBox class not found in pydexpi.dexpi_classes.equipment. "
            "This equipment type may not be available in your version of pyDEXPI. "
            "Check available equipment types with schema_query(operation='list_classes', schema_type='dexpi', category='equipment')"
        )
except ImportError as e:
    raise ImportError(
        "pyDEXPI is required for PFD expansion engine. "
        "Please install it with: pip install pyDEXPI\n"
        f"Original error: {e}"
    )

from src.models.template_system import (
    ProcessTemplate, TemplateLoader, EquipmentSpec, ConnectionSpec
)
from src.utils.process_resolver import generate_user_facing_tag, get_next_sequence_number


@dataclass
class EquipmentInstance:
    """Represents an instantiated equipment from template."""
    id: str  # Unique equipment ID
    tag: str  # User-facing tag (e.g., "230-T-01")
    dexpi_class: str  # DEXPI class name
    dexpi_object: Any  # Actual pyDEXPI object instance
    train_number: Optional[int] = None
    parameters: Dict[str, Any] = None
    ports: List[Dict[str, str]] = None
    metadata: Dict[str, Any] = None


@dataclass
class ConnectionInstance:
    """Represents an instantiated connection between equipment."""
    from_equipment: str
    from_port: str
    to_equipment: str
    to_port: str
    stream_type: str = "material"
    metadata: Dict[str, Any] = None


@dataclass
class ExpansionResult:
    """Result of BFD→PFD expansion."""
    pfd_flowsheet_id: str
    source_bfd_block: str
    equipment: List[EquipmentInstance]
    connections: List[ConnectionInstance]
    expansion_metadata: Dict[str, Any]


class PfdExpansionEngine:
    """Engine for expanding BFD blocks using templates."""

    def __init__(self, template_base_path: str = "src/config/process_templates"):
        """Initialize expansion engine with template loader."""
        self.loader = TemplateLoader(template_base_path)
        self.dexpi_class_map = self._build_dexpi_class_map()

    def _build_dexpi_class_map(self) -> Dict[str, Any]:
        """Build mapping of DEXPI class names to actual classes."""
        return {
            'Tank': Tank,
            'CentrifugalPump': CentrifugalPump,
            'CentrifugalBlower': CentrifugalBlower,
            'Mixer': Mixer,
            'Filter': Filter,
            'ProcessColumn': ProcessColumn,
            'CustomEquipment': CustomEquipment,
            'ProcessSignalGeneratingSystem': ProcessSignalGeneratingSystem,
            'ProcessControlFunction': ProcessControlFunction,
            'Centrifuge': Centrifuge,
            'ButterflyValve': ButterflyValve,
            'GateValve': GateValve,
            'CheckValve': CheckValve,
            'OperatedValve': OperatedValve,
            'AlternatingCurrentMotor': AlternatingCurrentMotor,
            'Motor': Motor,
            'CustomMotor': CustomMotor,
            'DirectCurrentMotor': DirectCurrentMotor,
            'GearBox': GearBox,
            'PressureVessel': PressureVessel,
            'HeatExchanger': HeatExchanger,
            'Pump': Pump,
            'Vessel': Vessel,
            'Equipment': Equipment,
            'BallValve': BallValve,
            'GlobeValve': GlobeValve,
            'PlugValve': PlugValve,
            'ProcessInstrumentationFunction': ProcessInstrumentationFunction,
        }

    def expand_bfd_block(
        self,
        bfd_block: str,
        process_unit_id: str,
        area_number: int,
        train_count: int = 1,
        parameters: Optional[Dict[str, Any]] = None,
        pfd_flowsheet_id: Optional[str] = None
    ) -> ExpansionResult:
        """
        Expand a BFD block into PFD equipment based on template.

        Args:
            bfd_block: BFD block ID/tag (e.g., "230-AerationTank")
            process_unit_id: Process unit ID from hierarchy (e.g., "TK")
            area_number: Process area number (e.g., 230)
            train_count: Number of parallel trains to create
            parameters: Template parameters (e.g., aeration_type)
            pfd_flowsheet_id: Target PFD flowsheet ID

        Returns:
            ExpansionResult with created equipment and connections
        """
        # Load and resolve template
        template = self.loader.load_template(process_unit_id, area_number)

        runtime_parameters = parameters or {}
        resolved_parameters = self._resolve_parameter_values(template, runtime_parameters)

        # Apply parameters including train count (always apply to handle defaults)
        template = self._apply_template_parameters(template, resolved_parameters)

        # Instantiate equipment
        equipment = []
        equipment_map = {}  # Map template IDs to instances

        # Create per-train equipment
        for train_num in range(1, train_count + 1):
            for eq_spec in template.per_train_equipment:
                # Check condition
                if not self._evaluate_condition(eq_spec.condition, resolved_parameters):
                    continue

                instances = self._instantiate_equipment(
                    eq_spec, area_number, train_num, train_count
                )
                for i, inst in enumerate(instances, 1):
                    equipment.append(inst)
                    # Store mapping for connection resolution
                    # Fix: Handle multiple instances per train properly
                    if eq_spec.count > 1:
                        eq_id = f"{eq_spec.id or eq_spec.tag_prefix}-{train_num}-{i}"
                    else:
                        eq_id = f"{eq_spec.id or eq_spec.tag_prefix}-{train_num}"
                    equipment_map[eq_id] = inst

        # Create shared equipment
        for eq_spec in template.shared_equipment:
            # Check condition
            if not self._evaluate_condition(eq_spec.condition, resolved_parameters):
                continue

            instances = self._instantiate_equipment(
                eq_spec, area_number, None, None
            )
            for i, inst in enumerate(instances, 1):
                equipment.append(inst)
                eq_id = eq_spec.id or eq_spec.tag_prefix
                if eq_spec.count > 1:
                    # Multiple shared equipment
                    equipment_map[f"{eq_id}-{i}"] = inst
                else:
                    equipment_map[eq_id] = inst

        # Wire connections
        connections = self._wire_connections(
            template.connections, equipment_map, train_count
        )

        # Build expansion metadata
        metadata = {
            'source_bfd_block': bfd_block,
            'process_unit_id': process_unit_id,
            'area_number': area_number,
            'train_count': train_count,
            'template_used': template.source_file,
            'components_used': template.components_used,
            'equipment_count': len(equipment),
            'connection_count': len(connections),
            'parameters': resolved_parameters
        }

        return ExpansionResult(
            pfd_flowsheet_id=pfd_flowsheet_id or f"PFD_{area_number}",
            source_bfd_block=bfd_block,
            equipment=equipment,
            connections=connections,
            expansion_metadata=metadata
        )

    def _instantiate_equipment(
        self,
        spec: EquipmentSpec,
        area_number: int,
        train_number: Optional[int] = None,
        total_trains: Optional[int] = None
    ) -> List[EquipmentInstance]:
        """
        Create equipment instances from specification.

        Args:
            spec: Equipment specification from template
            area_number: Process area number
            train_number: Train number (for per-train equipment)
            total_trains: Total number of trains

        Returns:
            List of equipment instances (usually 1, but can be multiple)
        """
        instances = []

        # Determine how many instances to create
        count = spec.count

        # Generate tags
        for i in range(1, count + 1):
            # Generate unique tag
            if train_number:
                # Per-train equipment: area-prefix-train.instance
                if count > 1:
                    tag = f"{area_number}-{spec.tag_prefix}-{train_number:02d}.{i:02d}"
                else:
                    tag = f"{area_number}-{spec.tag_prefix}-{train_number:02d}"
            else:
                # Shared equipment: area-prefix-instance
                if count > 1:
                    tag = f"{area_number}-{spec.tag_prefix}-{i:02d}"
                else:
                    tag = f"{area_number}-{spec.tag_prefix}-01"

            # Get DEXPI class
            dexpi_class_name = spec.dexpi_class or 'CustomEquipment'
            dexpi_class = self.dexpi_class_map.get(dexpi_class_name)

            if not dexpi_class:
                raise ValueError(
                    f"Unknown DEXPI class: {dexpi_class_name}. "
                    f"Available classes: {', '.join(self.dexpi_class_map.keys())}"
                )

            # Create DEXPI instance
            try:
                # CustomEquipment requires typeName parameter
                if dexpi_class_name == 'CustomEquipment':
                    dexpi_obj = dexpi_class(typeName=spec.id or spec.tag_prefix)
                else:
                    # Most other DEXPI classes don't take constructor arguments
                    dexpi_obj = dexpi_class()

                # Set parameters as attributes
                for key, value in spec.default_params.items():
                    if hasattr(dexpi_obj, key):
                        setattr(dexpi_obj, key, value)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to instantiate DEXPI class {dexpi_class_name}: {e}"
                )

            # Create equipment instance
            eq_id = f"{spec.id or spec.tag_prefix}"
            if train_number:
                eq_id = f"{eq_id}-{train_number}"
            if count > 1:
                eq_id = f"{eq_id}-{i}"

            instance = EquipmentInstance(
                id=eq_id,
                tag=tag,
                dexpi_class=dexpi_class_name,
                dexpi_object=dexpi_obj,
                train_number=train_number,
                parameters=spec.default_params.copy(),
                ports=[p.model_dump() if hasattr(p, 'model_dump') else p
                       for p in spec.ports],
                metadata={
                    'area': area_number,
                    'shared': spec.shared,
                    'mount_to': spec.mount_to
                }
            )
            instances.append(instance)

        return instances

    def _wire_connections(
        self,
        connection_specs: List[ConnectionSpec],
        equipment_map: Dict[str, EquipmentInstance],
        train_count: int
    ) -> List[ConnectionInstance]:
        """
        Create connection instances from specifications.

        Args:
            connection_specs: Connection specifications from template
            equipment_map: Map of equipment IDs to instances
            train_count: Number of trains for wildcard expansion

        Returns:
            List of connection instances
        """
        connections = []

        for spec in connection_specs:
            # Expand wildcards and patterns
            from_patterns = self._expand_equipment_pattern(
                spec.from_equipment, train_count, equipment_map
            )
            to_patterns = self._expand_equipment_pattern(
                spec.to_equipment, train_count, equipment_map
            )

            # Create connections for all combinations
            for from_eq in from_patterns:
                for to_eq in to_patterns:
                    # Skip if equipment not found
                    if from_eq not in equipment_map and not from_eq.startswith('BFD'):
                        continue
                    if to_eq not in equipment_map and not to_eq.startswith('BFD'):
                        continue

                    conn = ConnectionInstance(
                        from_equipment=from_eq,
                        from_port=spec.from_port,
                        to_equipment=to_eq,
                        to_port=spec.to_port,
                        stream_type=spec.stream_type,
                        metadata={
                            'per_train': spec.per_train,
                            'port_mapping': spec.port_mapping
                        }
                    )
                    connections.append(conn)

        return connections

    def _apply_template_parameters(
        self,
        template: ProcessTemplate,
        parameters: Dict[str, Any]
    ) -> ProcessTemplate:
        """
        Apply runtime parameters to template.

        Args:
            template: Template to modify
            parameters: Runtime parameter values

        Returns:
            Modified template with parameters applied
        """
        # Apply parameters to equipment default_params
        for eq_list in [template.per_train_equipment, template.shared_equipment]:
            for eq in eq_list:
                # Substitute parameters in default_params
                for key, value in eq.default_params.items():
                    if isinstance(value, str) and '${' in value:
                        # Handle ${param|default} syntax
                        import re
                        pattern = r'\$\{([^}|]+)(?:\|([^}]+))?\}'

                        def replace_param(match):
                            param_name = match.group(1)
                            default_val = match.group(2) if match.group(2) else ''
                            return str(parameters.get(param_name, default_val))

                        eq.default_params[key] = re.sub(pattern, replace_param, value)

        # Apply parameters to connection DSL strings
        for conn in template.connections:
            # Handle ${param|default} syntax in connections
            import re
            pattern = r'\$\{([^}|]+)(?:\|([^}]+))?\}'

            def replace_param(match):
                param_name = match.group(1)
                default_val = match.group(2) if match.group(2) else ''
                return str(parameters.get(param_name, default_val))

            conn.from_equipment = re.sub(pattern, replace_param, conn.from_equipment)
            conn.to_equipment = re.sub(pattern, replace_param, conn.to_equipment)

        return template

    def _resolve_parameter_values(
        self,
        template: ProcessTemplate,
        runtime_parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge template defaults with runtime overrides.

        Args:
            template: Process template that defines parameter defaults
            runtime_parameters: Parameters provided at runtime

        Returns:
            Dictionary containing effective parameter values
        """
        resolved: Dict[str, Any] = {}

        for name, spec in template.parameters.items():
            resolved[name] = spec.default

        # Runtime parameters override defaults and may introduce extra keys
        resolved.update(runtime_parameters)
        return resolved

    def _evaluate_condition(
        self,
        condition: Optional[str],
        parameters: Dict[str, Any]
    ) -> bool:
        """
        Evaluate conditional expression for equipment inclusion.

        Args:
            condition: Condition string like "${do_control|true}" or "aeration_type == 'fine_bubble'"
            parameters: Parameter values

        Returns:
            True if equipment should be included
        """
        if not condition:
            return True
        original_condition = condition
        condition = condition.strip()

        token_only = CONDITION_TOKEN_PATTERN.fullmatch(condition)
        if token_only:
            value = self._resolve_condition_token(token_only, parameters, original_condition)
            return self._condition_value_to_bool(value)

        def _token_replacer(match) -> str:
            value = self._resolve_condition_token(match, parameters, original_condition)
            return repr(value)

        resolved_condition = CONDITION_TOKEN_PATTERN.sub(_token_replacer, condition)

        # Handle comparison expressions
        if '==' in resolved_condition or '!=' in resolved_condition:
            try:
                result = eval(
                    resolved_condition,
                    {"__builtins__": {}},
                    {k: v for k, v in parameters.items()}
                )
                return bool(result)
            except (SyntaxError, NameError, TypeError) as e:
                raise ValueError(
                    f"Invalid condition expression: '{original_condition}'. "
                    f"Resolved expression: '{resolved_condition}'. "
                    f"Conditions must be simple comparisons (==, !=) with valid parameter references. "
                    f"Error: {e}"
                ) from e

        # No condition operators found - fail loudly
        raise ValueError(
            f"Unsupported condition format: '{original_condition}'. "
            f"Supported formats: '${{param|default}}', 'param == value', 'param != value'"
        )

    def _resolve_condition_token(
        self,
        match: re.Match,
        parameters: Dict[str, Any],
        condition: str
    ) -> Any:
        param_name = match.group(1).strip()
        if not param_name:
            raise ValueError(f"Invalid parameter placeholder in condition '{condition}' (missing name)")

        if param_name in parameters:
            return parameters[param_name]

        default_raw = match.group(2)
        if default_raw is None:
            raise ValueError(
                f"Condition '{condition}' references parameter '{param_name}' without a default "
                "and it was not provided."
            )

        return self._coerce_literal_value(default_raw)

    @staticmethod
    def _coerce_literal_value(raw_value: str) -> Any:
        value = raw_value.strip()
        if not value:
            return ""

        if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
            return value[1:-1]

        lowered = value.lower()
        if lowered in {"true", "false"}:
            return lowered == "true"

        if re.fullmatch(r"-?\d+", value):
            try:
                return int(value)
            except ValueError:
                # Fall through to float parsing if int conversion somehow fails
                pass

        try:
            return float(value)
        except ValueError:
            return value

    @staticmethod
    def _condition_value_to_bool(value: Any) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in TRUTHY_CONDITION_VALUES
        return bool(value)

    def _expand_equipment_pattern(
        self,
        pattern: str,
        train_count: int,
        equipment_map: Dict[str, EquipmentInstance]
    ) -> List[str]:
        """
        Expand equipment pattern with wildcards.

        Patterns:
        - "Basin-*" -> ["Basin-1", "Basin-2", ...]
        - "Basin-(*+1)" -> ["Basin-2", "Basin-3", ...]
        - "Pump-1" -> ["Pump-1"]
        - "BFD.inlet" -> ["BFD.inlet"]

        Args:
            pattern: Equipment pattern from connection spec
            train_count: Number of trains
            equipment_map: Available equipment

        Returns:
            List of expanded equipment IDs
        """
        # Handle BFD ports
        if pattern.startswith('BFD'):
            return [pattern]

        # Handle wildcards
        if '*' in pattern:
            if '(*+1)' in pattern:
                # Series connection to next train
                base = pattern.replace('(*+1)', '')
                return [f"{base}{i+1}" for i in range(1, train_count)]
            else:
                # All trains
                base = pattern.replace('*', '')
                return [f"{base}{i}" for i in range(1, train_count + 1)]

        # Handle specific references
        if '-N' in pattern:
            # Last in series
            base = pattern.replace('-N', '')
            return [f"{base}{train_count}"]

        # Direct reference
        return [pattern]

    def populate_canonical_ports(
        self,
        equipment: List[EquipmentInstance],
        bfd_port_specs: Optional[List[Any]] = None
    ) -> None:
        """
        Populate canonical DEXPI port specifications.

        This is where BfdPortSpec.canonical gets populated for
        future PFD→P&ID expansion.

        Args:
            equipment: Equipment instances to populate ports for
            bfd_port_specs: Original BFD port specifications
        """
        # TODO: Implement canonical port population
        # This will map BFD port types to DEXPI NumberOfPortsClassification
        pass


def create_pfd_from_bfd(
    bfd_flowsheet_id: str,
    bfd_block: str,
    train_count: int = 1,
    parameters: Optional[Dict[str, Any]] = None
) -> ExpansionResult:
    """
    Convenience function to expand BFD block to PFD.

    Args:
        bfd_flowsheet_id: Source BFD flowsheet ID
        bfd_block: BFD block to expand
        train_count: Number of parallel trains
        parameters: Template parameters

    Returns:
        ExpansionResult with PFD equipment and connections
    """
    # TODO: Load BFD flowsheet and extract block metadata
    # For now, use hardcoded values
    process_unit_id = "TK"
    area_number = 230

    engine = PfdExpansionEngine()
    return engine.expand_bfd_block(
        bfd_block=bfd_block,
        process_unit_id=process_unit_id,
        area_number=area_number,
        train_count=train_count,
        parameters=parameters
    )
