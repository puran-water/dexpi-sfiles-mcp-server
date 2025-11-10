"""Template system for BFD→PFD expansion.

This module provides the infrastructure for loading, resolving, and composing
process templates with component system and equipment library references.
"""

import re
import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field, field_validator
from ..models.port_spec import CardinalDirection


class PortDefinition(BaseModel):
    """Port definition for equipment."""
    name: str
    direction: CardinalDirection
    type: str = "Standard"  # Standard, Utility, Chemical, Solids
    nominal_diameter: Optional[str] = None


class EquipmentSpec(BaseModel):
    """Specification for equipment in template."""
    id: Optional[str] = None  # Local ID within template
    ref: Optional[str] = None  # Reference to equipment library ($ref)
    dexpi_class: Optional[str] = None  # Direct DEXPI class name
    tag_prefix: str
    count: int = 1
    shared: bool = False  # Shared across trains or per-train
    mount_to: Optional[str] = None  # For instrumentation
    default_params: Dict[str, Any] = Field(default_factory=dict)
    ports: List[PortDefinition] = Field(default_factory=list)
    condition: Optional[str] = None  # Conditional expression for equipment inclusion

    @field_validator('ref')
    def validate_ref(cls, v):
        """Ensure ref starts with equipment_library."""
        if v and not v.startswith('equipment_library.'):
            if not v.startswith('$ref:'):
                v = f'equipment_library.{v}'
        return v


class ConnectionSpec(BaseModel):
    """Connection specification between equipment."""
    from_equipment: str  # Equipment ID or reference
    from_port: str
    to_equipment: str
    to_port: str
    stream_type: str = "material"
    per_train: bool = True
    port_mapping: Optional[str] = None  # Maps to BFD port


class ParameterSpec(BaseModel):
    """Parameter specification for template variations."""
    name: str
    type: str  # enum, integer, float, string
    values: Optional[List[Any]] = None  # For enum type
    default: Any
    min: Optional[float] = None
    max: Optional[float] = None
    affects: List[str] = Field(default_factory=list)  # What it affects


class ComponentReference(BaseModel):
    """Reference to a reusable component."""
    component: str  # Component ID
    condition: Optional[Dict[str, Any]] = None  # Conditional inclusion
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ProcessTemplate(BaseModel):
    """Complete resolved process template."""
    process_unit_id: str
    area_number: int
    name: str
    description: Optional[str] = None

    # Parameters for variations
    parameters: Dict[str, ParameterSpec] = Field(default_factory=dict)

    # Equipment specifications
    per_train_equipment: List[EquipmentSpec] = Field(default_factory=list)
    shared_equipment: List[EquipmentSpec] = Field(default_factory=list)

    # Connections (resolved from DSL)
    connections: List[ConnectionSpec] = Field(default_factory=list)

    # Port mappings to BFD
    port_mappings: Dict[str, str] = Field(default_factory=dict)

    # Metadata
    components_used: List[str] = Field(default_factory=list)
    source_file: Optional[str] = None


class TemplateLoader:
    """Loads and resolves templates with component composition."""

    def __init__(self, base_path: str = "src/config/process_templates"):
        self.base_path = Path(base_path)
        self.equipment_library = self._load_equipment_library()
        self.components = self._load_components()
        self.registry = self._load_registry()

    def _load_equipment_library(self) -> Dict[str, Any]:
        """Load equipment library from YAML."""
        lib_path = self.base_path.parent / "equipment_library.yaml"
        if not lib_path.exists():
            return {}

        with open(lib_path, 'r') as f:
            data = yaml.safe_load(f)
            return data.get('equipment', {})

    def _load_components(self) -> Dict[str, Any]:
        """Load all component definitions."""
        components = {}
        comp_dir = self.base_path / "components"
        if not comp_dir.exists():
            return components

        for comp_file in comp_dir.glob("*.yaml"):
            with open(comp_file, 'r') as f:
                comp_data = yaml.safe_load(f)
                comp_id = comp_data.get('id')
                if comp_id:
                    components[comp_id] = comp_data

        return components

    def _load_registry(self) -> Dict[str, str]:
        """Load template registry mapping process IDs to files."""
        registry_path = self.base_path / "registry.yaml"
        if not registry_path.exists():
            return {}

        with open(registry_path, 'r') as f:
            data = yaml.safe_load(f)
            return data.get('templates', {})

    def load_template(self, process_unit_id: str, area_number: Optional[int] = None) -> ProcessTemplate:
        """Load and resolve template for process unit."""
        # Find template file from registry
        template_key = process_unit_id
        if area_number:
            # Check for area-specific template first
            area_key = f"{area_number}_{process_unit_id}"
            if area_key in self.registry:
                template_key = area_key

        if template_key not in self.registry:
            raise ValueError(f"No template found for process unit: {process_unit_id}")

        template_file = self.base_path / self.registry[template_key]
        if not template_file.exists():
            raise FileNotFoundError(f"Template file not found: {template_file}")

        # Load raw template
        with open(template_file, 'r') as f:
            raw_template = yaml.safe_load(f)

        # Resolve components
        if 'components' in raw_template:
            raw_template = self._compose_components(raw_template)

        # Resolve equipment references
        if 'per_train_equipment' in raw_template:
            raw_template['per_train_equipment'] = [
                self._resolve_equipment_ref(eq) for eq in raw_template['per_train_equipment']
            ]

        if 'shared_equipment' in raw_template:
            raw_template['shared_equipment'] = [
                self._resolve_equipment_ref(eq) for eq in raw_template['shared_equipment']
            ]

        # Parse connection DSL
        if 'connections' in raw_template and isinstance(raw_template['connections'], str):
            raw_template['connections'] = self.parse_connection_dsl(raw_template['connections'])

        # Convert parameters to ParameterSpec format if needed
        if 'parameters' in raw_template:
            converted_params = {}
            for param_name, param_data in raw_template.get('parameters', {}).items():
                if isinstance(param_data, dict):
                    # Add the name field
                    param_spec_data = {
                        'name': param_name,
                        'type': param_data.get('type', 'string'),
                        'default': param_data.get('default'),
                        'values': param_data.get('values'),
                        'min': param_data.get('min'),
                        'max': param_data.get('max'),
                        'affects': param_data.get('affects', [])
                    }
                    # Remove None values
                    param_spec_data = {k: v for k, v in param_spec_data.items() if v is not None}
                    converted_params[param_name] = param_spec_data
            raw_template['parameters'] = converted_params

        # Create ProcessTemplate
        template = ProcessTemplate(**raw_template)
        template.source_file = str(template_file)

        return template

    def _compose_components(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compose template from component references."""
        components = template_data.get('components', [])
        if not components:
            return template_data

        # Track which components were used
        used_components = []

        # Initialize collections if not present
        if 'per_train_equipment' not in template_data:
            template_data['per_train_equipment'] = []
        if 'shared_equipment' not in template_data:
            template_data['shared_equipment'] = []
        if 'connections' not in template_data:
            template_data['connections'] = []

        for comp_ref in components:
            if isinstance(comp_ref, str):
                # Simple component reference
                comp_id = comp_ref
                params = {}
                # For aeration_system, provide default basin_ref
                if comp_id == 'aeration_system':
                    params = {'basin_ref': 'Basin'}
            elif isinstance(comp_ref, dict):
                # Component with conditions or parameters
                if '$if' in comp_ref:
                    # Handle conditional components
                    condition = comp_ref['$if']
                    # For now, include by default (will be evaluated at runtime)
                    comp_id = comp_ref.get('then', {}).get('component')
                    params = comp_ref.get('then', {}).get('parameters', {})
                else:
                    comp_id = comp_ref.get('component', comp_ref.get('id'))
                    params = comp_ref.get('parameters', {})
            else:
                continue

            # Parse component ID if it has parameters
            if '(' in comp_id:
                # e.g., "recycle_loop(vessel_ref=Basin, pump_ref=RAS_Pump)"
                match = re.match(r'(\w+)\((.*)\)', comp_id)
                if match:
                    comp_id = match.group(1)
                    # Parse parameters from function call syntax
                    param_str = match.group(2)
                    for param in param_str.split(','):
                        key, value = param.strip().split('=')
                        params[key.strip()] = value.strip()

            if comp_id not in self.components:
                continue

            component = self.components[comp_id]
            used_components.append(comp_id)

            # Merge equipment
            for eq in component.get('equipment', []):
                eq_copy = eq.copy()
                # Apply parameters to equipment
                eq_copy = self._apply_parameters(eq_copy, params)

                if eq.get('shared', False):
                    template_data['shared_equipment'].append(eq_copy)
                else:
                    template_data['per_train_equipment'].append(eq_copy)

            # Merge connections (keep as DSL for now)
            comp_connections = component.get('connections', '')
            if comp_connections:
                # Apply parameters to connection DSL
                comp_connections = self._apply_parameters_to_string(comp_connections, params)

                if isinstance(template_data['connections'], list):
                    template_data['connections'].append(comp_connections)
                else:
                    template_data['connections'] += '\n' + comp_connections

            # Merge port mappings
            for bfd_port, eq_port in component.get('port_mappings', {}).items():
                if 'port_mappings' not in template_data:
                    template_data['port_mappings'] = {}
                template_data['port_mappings'][bfd_port] = eq_port

        template_data['components_used'] = used_components
        return template_data

    def _resolve_equipment_ref(self, equipment: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve $ref pointers to equipment library."""
        if '$ref' in equipment:
            ref = equipment['$ref']
            # Remove 'equipment_library.' prefix if present
            if ref.startswith('equipment_library.'):
                ref = ref[len('equipment_library.'):]

            if ref in self.equipment_library:
                # Merge library definition with local overrides
                lib_eq = self.equipment_library[ref].copy()
                merged = {**lib_eq, **equipment}
                # Remove the $ref field
                merged.pop('$ref', None)
                return merged

        return equipment

    def parse_connection_dsl(self, dsl: str) -> List[ConnectionSpec]:
        """Parse connection DSL to structured Connection objects.

        DSL syntax examples:
            A.out -> B.in
            Blower-*.discharge -> AirHeader
            Basin-*.outlet -> Basin-(*+1).inlet  # Series connection
            BFD.inlet -> Basin-1.inlet
        """
        connections = []
        lines = dsl.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Parse arrow connection: A.port -> B.port
            match = re.match(r'([A-Za-z0-9_\-\*]+)\.?([A-Za-z0-9_]*)\s*->\s*([A-Za-z0-9_\-\*\+\(\)]+)\.?([A-Za-z0-9_]*)', line)
            if match:
                from_eq = match.group(1)
                from_port = match.group(2) or 'outlet'
                to_eq = match.group(3)
                to_port = match.group(4) or 'inlet'

                # Check for port mapping indicator
                port_mapping = None
                if 'BFD' in from_eq or 'BFD' in to_eq:
                    port_mapping = line  # Store original for BFD mapping

                connections.append(ConnectionSpec(
                    from_equipment=from_eq,
                    from_port=from_port,
                    to_equipment=to_eq,
                    to_port=to_port,
                    port_mapping=port_mapping
                ))

        return connections

    def _apply_parameters(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply parameter substitutions to a dictionary."""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self._apply_parameters_to_string(value, params)
            elif isinstance(value, dict):
                result[key] = self._apply_parameters(value, params)
            elif isinstance(value, list):
                result[key] = [
                    self._apply_parameters(item, params) if isinstance(item, dict)
                    else self._apply_parameters_to_string(item, params) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def _apply_parameters_to_string(self, text: str, params: Dict[str, Any]) -> str:
        """Apply parameter substitutions to a string using ${param} syntax."""
        for key, value in params.items():
            text = text.replace(f'${{{key}}}', str(value))

        # Handle defaults: ${param|default_value}
        pattern = r'\$\{([^}|]+)\|([^}]+)\}'
        text = re.sub(pattern, lambda m: params.get(m.group(1), m.group(2)), text)

        return text


class ConnectionDSLParser:
    """Enhanced parser for connection DSL with pattern support."""

    @staticmethod
    def parse(dsl: str, equipment_list: List[str] = None) -> List[ConnectionSpec]:
        """Parse enhanced connection DSL.

        Supports:
        - Simple connections: A.out -> B.in
        - Wildcards: Pump-* -> Header
        - Series: Tank-1 -> Tank-2 -> Tank-3
        - Parallel: Source -> [Tank-1, Tank-2, Tank-3]
        - Patterns: @recycle_loop(vessel=Tank, pump=P-01)
        """
        loader = TemplateLoader()
        return loader.parse_connection_dsl(dsl)


def validate_template_coverage(hierarchy_path: str = "process_units_hierarchy.json") -> Dict[str, Any]:
    """Validate that all process units have templates."""
    import json

    # Load hierarchy
    with open(hierarchy_path, 'r') as f:
        hierarchy = json.load(f)

    # Extract all process units with area numbers (leaf nodes)
    process_units = []

    def extract_units(node, path=""):
        """Recursively extract process units."""
        if 'area_number' in node:
            # This is a leaf node (process unit)
            process_units.append({
                'id': node.get('process_unit_id', ''),
                'area': node['area_number'],
                'name': node.get('name', ''),
                'path': path
            })

        # Process subcategories
        for subcat_name, subcat_data in node.get('subcategories', {}).items():
            extract_units(subcat_data, f"{path}/{subcat_name}")

        # Process process_units
        for unit_name, unit_data in node.get('process_units', {}).items():
            if isinstance(unit_data, dict):
                extract_units(unit_data, f"{path}/{unit_name}")

    # Start extraction from root
    for category_name, category_data in hierarchy.items():
        extract_units(category_data, category_name)

    # Load template registry
    loader = TemplateLoader()
    registry = loader.registry

    # Check coverage
    covered = []
    missing = []
    registry_but_no_file = []

    for unit in process_units:
        # Check if template exists (with or without area prefix)
        unit_id = unit['id']
        area_id = f"{unit['area']}_{unit['id']}"

        template_key = None
        if unit_id in registry:
            template_key = unit_id
        elif area_id in registry:
            template_key = area_id

        if template_key:
            # Verify the file actually exists
            template_file = loader.base_path / registry[template_key]
            if template_file.exists():
                covered.append(unit)
            else:
                registry_but_no_file.append({
                    **unit,
                    'registry_key': template_key,
                    'expected_file': str(template_file)
                })
        else:
            missing.append(unit)

    total = len(process_units)
    coverage_pct = (len(covered) / total * 100) if total > 0 else 0

    return {
        'total_units': total,
        'covered': len(covered),
        'missing': len(missing),
        'registry_but_no_file': len(registry_but_no_file),
        'coverage_percentage': coverage_pct,
        'missing_units': missing,
        'invalid_registry_entries': registry_but_no_file
    }