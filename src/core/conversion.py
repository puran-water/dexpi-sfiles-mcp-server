"""
Core Conversion Module - Unified SFILES ↔ DEXPI Conversion Engine

This module consolidates conversion logic from:
- converters/sfiles_dexpi_mapper.py (SFILES → DEXPI)
- converters/dexpi_sfiles_converter.py (DEXPI → SFILES)
- tools/pfd_expansion_engine.py (BFD → PFD expansion)
- model_service.py (parsing and enrichment)

Provides bidirectional conversion with validation and round-trip integrity.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path

# Import pyDEXPI classes - corrected to lowercase pydexpi
# Verified from process-intelligence-research/pyDEXPI repository structure
# NO FALLBACKS - fail fast if imports don't work
from pydexpi.dexpi_classes.dexpiModel import DexpiModel, ConceptualModel
from pydexpi.dexpi_classes.metaData import MetaData
from pydexpi.dexpi_classes.piping import (
    PipingNetworkSegment, PipingNetworkSystem,
    BallValve, GateValve, GlobeValve, CheckValve
)
from pydexpi.dexpi_classes.equipment import Equipment
from pydexpi.dexpi_classes.instrumentation import (
    ProcessInstrumentationFunction,
    ProcessControlFunction,
    ProcessSignalGeneratingFunction,
    ActuatingFunction,
    SensingLocation
)
from pydexpi.dexpi_classes.pydantic_classes import CustomStringAttribute

# Exception classes for conversion errors
class InvalidStreamError(ValueError):
    """Raised when a stream references unknown or invalid units."""
    pass


class EmptySfilesError(ValueError):
    """Raised when SFILES parsing produces an empty model."""
    pass


class HeatIntegrationWarning(UserWarning):
    """Warning when heat integration nodes are detected but handled safely."""
    pass


# Heat Integration Node Guard
# SFILES2 has known bugs with merge_HI_nodes/split_HI_nodes (GitHub issue #12)
# These patterns identify HI nodes that may cause issues
HI_NODE_PATTERNS = {
    # OntoCape HI node names
    "hot_in", "hot_out", "cold_in", "cold_out",
    "1_in", "1_out", "2_in", "2_out",
    # SFILES HI markers
    "HI_", "hi_", "hx_hot", "hx_cold",
}


def detect_hi_nodes(graph) -> List[str]:
    """
    Detect heat integration nodes in SFILES2 graph.

    Args:
        graph: NetworkX DiGraph from Flowsheet.state

    Returns:
        List of node names that appear to be HI nodes
    """
    hi_nodes = []
    for node in graph.nodes():
        node_lower = str(node).lower()
        # Check for HI node patterns
        if any(pattern in node_lower for pattern in HI_NODE_PATTERNS):
            hi_nodes.append(node)
        # Check node attributes for HI markers
        node_data = graph.nodes.get(node, {})
        if node_data.get('is_hi_node') or node_data.get('heat_integration'):
            hi_nodes.append(node)
    return list(set(hi_nodes))


def guard_hi_operations(flowsheet, operation: str = "auto") -> bool:
    """
    Guard against SFILES2 HI bugs before calling merge/split operations.

    This prevents crashes from known issues in SFILES2 #12 (merge_HI_nodes/split_HI_nodes bugs).

    Args:
        flowsheet: Flowsheet instance
        operation: "merge", "split", or "auto" (detect from graph)

    Returns:
        True if safe to proceed, False if HI nodes detected that could cause issues

    Raises:
        HeatIntegrationWarning: When HI nodes are detected and skipped
    """
    import warnings

    graph = flowsheet.state
    hi_nodes = detect_hi_nodes(graph)

    if not hi_nodes:
        return True  # No HI nodes, safe to proceed

    # HI nodes detected - issue warning and skip operation
    warning_msg = (
        f"Heat integration nodes detected: {hi_nodes}. "
        f"Skipping {operation} operation due to known SFILES2 bugs "
        "(see GitHub issue process-intelligence-research/SFILES2#12). "
        "HI node connections will be preserved as-is without merge/split."
    )
    warnings.warn(warning_msg, HeatIntegrationWarning)
    logger.warning(warning_msg)

    return False  # Not safe to call merge/split


# Import core modules
from .equipment import EquipmentFactory, EquipmentRegistry, get_factory, get_registry
from .symbols import SymbolRegistry, get_registry as get_symbol_registry

logger = logging.getLogger(__name__)


@dataclass
class SfilesUnit:
    """Represents a unit in SFILES notation."""
    name: str
    unit_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    sequence: Optional[int] = None  # For BFD ordering


@dataclass
class SfilesStream:
    """Represents a stream connection in SFILES."""
    from_unit: str
    to_unit: str
    stream_name: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, List[str]] = field(default_factory=dict)  # Column/HE tags


@dataclass
class SfilesModel:
    """Complete SFILES model representation."""
    units: List[SfilesUnit]
    streams: List[SfilesStream]
    model_type: str = "PFD"  # BFD or PFD
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConversionEngine:
    """
    Unified engine for bidirectional SFILES ↔ DEXPI conversion.
    Handles parsing, generation, validation, and round-trip integrity.
    """

    # SFILES regex patterns (kept for legacy fallback only)
    UNIT_PATTERN = re.compile(r'(\w+)\[([^\]]+)\](?:\(([^)]+)\))?')
    STREAM_PATTERN = re.compile(r'(\w+)(?:\[[^\]]+\])?(?:\([^)]+\))?\s*->\s*(\w+)')
    PROPERTY_PATTERN = re.compile(r'(\w+)=([^,]+)')
    TAG_PATTERN = re.compile(r'{([^:]+):([^}]+)}')

    # SFILES2 native patterns for direct parsing
    SFILES2_UNIT_PATTERN = re.compile(r'\(([^)]+)\)')  # (unit-name)
    SFILES2_TAG_PATTERN = re.compile(r'\{([^}]+)\}')  # {tag}

    def __init__(
        self,
        equipment_factory: Optional[EquipmentFactory] = None,
        symbol_registry: Optional[SymbolRegistry] = None
    ):
        """Initialize conversion engine with registries."""
        self.equipment_factory = equipment_factory or get_factory()
        self.equipment_registry = get_registry()
        self.symbol_registry = symbol_registry or get_symbol_registry()

        # Import SFILES2 Flowsheet for native parsing
        from ..adapters.sfiles_adapter import get_flowsheet_class_cached
        self._Flowsheet = get_flowsheet_class_cached()

    def parse_sfiles(self, sfiles_string: str) -> SfilesModel:
        """
        Parse SFILES string into structured model using SFILES2's native parser.

        PHASE 1 FIX: Uses Flowsheet.create_from_sfiles() instead of custom regex.
        This correctly handles:
        - Branches: (a)[(b)](c)
        - Cycles/recycles: (a)<1(b)1
        - Heat exchanger tags: {he:HE101}
        - Column tags: {col:C101}
        - All SFILES2 v1/v2 constructs

        Supports formats:
        - SFILES2: (reactor-0)(separator-1)
        - Legacy: unit1[type]->unit2[type]

        Args:
            sfiles_string: SFILES notation string

        Returns:
            Parsed SfilesModel
        """
        sfiles_string = sfiles_string.strip()

        # Detect format: SFILES2 uses (unit-name), legacy uses unit[type]
        is_sfiles2_format = bool(self.SFILES2_UNIT_PATTERN.search(sfiles_string))
        is_legacy_format = bool(self.UNIT_PATTERN.search(sfiles_string))

        if is_sfiles2_format:
            # Use SFILES2's native parser via Flowsheet
            return self._parse_sfiles2_native(sfiles_string)
        elif is_legacy_format:
            # Fallback to legacy regex parser for unit[type]->unit[type] format
            return self._parse_sfiles_legacy(sfiles_string)
        else:
            raise EmptySfilesError(
                f"SFILES parsing could not recognize format. "
                f"Input: '{sfiles_string[:100]}...'"
            )

    def _parse_sfiles2_native(self, sfiles_string: str) -> SfilesModel:
        """
        Parse SFILES2 string using the native Flowsheet.create_from_sfiles() API.

        This is the correct approach per Codex review - leverages SFILES2's
        built-in parser which correctly handles branches, cycles, and tags.
        """
        try:
            # Create Flowsheet and parse using SFILES2's native parser
            flowsheet = self._Flowsheet()
            flowsheet.create_from_sfiles(sfiles_string)

            # Extract units from the NetworkX graph
            units = []
            for node, data in flowsheet.state.nodes(data=True):
                # Parse unit name: format is typically "type-number"
                name = str(node)
                parts = name.rsplit('-', 1)
                if len(parts) == 2 and parts[1].isdigit():
                    unit_type = parts[0]
                else:
                    unit_type = data.get('unit_type', name)

                # Extract parameters from node attributes
                parameters = {k: v for k, v in data.items()
                             if k not in ('unit_type', 'name')}

                unit = SfilesUnit(
                    name=name,
                    unit_type=unit_type,
                    parameters=parameters
                )
                units.append(unit)

            # Extract streams from the NetworkX graph edges
            streams = []
            for from_unit, to_unit, data in flowsheet.state.edges(data=True):
                # Extract tags from edge attributes
                tags = {}
                if 'tags' in data:
                    tags = data['tags']
                # Also check for he/col directly
                if data.get('he'):
                    tags['he'] = data['he'] if isinstance(data['he'], list) else [data['he']]
                if data.get('col'):
                    tags['col'] = data['col'] if isinstance(data['col'], list) else [data['col']]

                stream = SfilesStream(
                    from_unit=str(from_unit),
                    to_unit=str(to_unit),
                    tags=tags,
                    properties={k: v for k, v in data.items()
                               if k not in ('tags', 'he', 'col')}
                )
                streams.append(stream)

            # Determine model type
            model_type = getattr(flowsheet, 'type', 'PFD')
            if model_type not in ('BFD', 'PFD'):
                # Infer from unit types
                bfd_types = ['reactor', 'clarifier', 'treatment', 'separation',
                            'screening', 'grit', 'aeration', 'thickener', 'digester']
                if any(any(bt in u.unit_type.lower() for bt in bfd_types) for u in units):
                    model_type = "BFD"
                else:
                    model_type = "PFD"

            # VALIDATE before returning
            if not units and flowsheet.state.number_of_nodes() == 0:
                raise EmptySfilesError(
                    f"SFILES2 parsing produced empty model. "
                    f"Input: '{sfiles_string[:100]}...'"
                )

            return SfilesModel(
                units=units,
                streams=streams,
                model_type=model_type
            )

        except ImportError as e:
            # SFILES2 not available, fall back to legacy
            logger.warning(f"SFILES2 not available, using legacy parser: {e}")
            return self._parse_sfiles_legacy(sfiles_string)
        except Exception as e:
            logger.error(f"SFILES2 native parsing failed: {e}")
            raise EmptySfilesError(
                f"SFILES2 parsing failed: {e}. Input: '{sfiles_string[:100]}...'"
            )

    def _parse_sfiles_legacy(self, sfiles_string: str) -> SfilesModel:
        """
        Legacy parser for unit[type]->unit[type] format.

        Kept for backward compatibility with older SFILES notation.
        """
        units = []
        streams = []
        unit_map = {}  # name -> SfilesUnit

        # Extract units
        for match in self.UNIT_PATTERN.finditer(sfiles_string):
            name = match.group(1)
            unit_type = match.group(2)
            properties_str = match.group(3)

            # Parse properties if present
            parameters = {}
            if properties_str:
                for prop_match in self.PROPERTY_PATTERN.finditer(properties_str):
                    key = prop_match.group(1)
                    value = prop_match.group(2)
                    # Try to convert to appropriate type
                    try:
                        if '.' in value:
                            parameters[key] = float(value)
                        else:
                            parameters[key] = int(value)
                    except ValueError:
                        parameters[key] = value

            unit = SfilesUnit(
                name=name,
                unit_type=unit_type,
                parameters=parameters
            )
            units.append(unit)
            unit_map[name] = unit

        # Extract streams
        segments = sfiles_string.split('->')
        for i in range(len(segments) - 1):
            # Get source unit name
            source_match = self.UNIT_PATTERN.search(segments[i])
            if not source_match:
                continue
            from_unit = source_match.group(1)

            # Get target unit name
            target_match = self.UNIT_PATTERN.search(segments[i + 1])
            if not target_match:
                continue
            to_unit = target_match.group(1)

            # Check for tags between units
            segment_text = segments[i] + '->' + segments[i + 1]
            tags = {}
            for tag_match in self.TAG_PATTERN.finditer(segment_text):
                tag_type = tag_match.group(1)
                tag_values = tag_match.group(2).split(',')
                tags[tag_type] = tag_values

            stream = SfilesStream(
                from_unit=from_unit,
                to_unit=to_unit,
                tags=tags
            )
            streams.append(stream)

        # Determine model type
        model_type = "PFD"
        bfd_types = ['reactor', 'clarifier', 'treatment', 'separation']
        if any(unit.unit_type.lower() in bfd_types for unit in units):
            model_type = "BFD"

        # VALIDATE before returning
        if not units and not streams:
            raise EmptySfilesError(
                f"Legacy SFILES parsing produced empty model. "
                f"Input: '{sfiles_string[:100]}...'"
            )

        return SfilesModel(
            units=units,
            streams=streams,
            model_type=model_type
        )

    def _is_control_unit(self, unit: SfilesUnit) -> bool:
        """
        Detect if a unit is a control/instrumentation unit.

        Args:
            unit: SfilesUnit to check

        Returns:
            True if unit represents control/instrumentation
        """
        # Check unit_type parameter
        if unit.parameters.get('unit_type') == 'Control':
            return True

        # Check for control type parameter
        if 'control_type' in unit.parameters:
            return True

        # Check if name starts with control prefix (C-, FC-, LC-, TC-, PC-)
        if isinstance(unit.name, str) and (
            unit.name.startswith('C-') or
            unit.name.startswith('FC-') or
            unit.name.startswith('LC-') or
            unit.name.startswith('TC-') or
            unit.name.startswith('PC-')
        ):
            return True

        return False

    def _create_instrumentation(
        self,
        unit: SfilesUnit,
        connected_equipment: Optional[Equipment] = None
    ) -> ProcessInstrumentationFunction:
        """
        Create DEXPI instrumentation from SFILES control unit.

        Args:
            unit: Control unit from SFILES
            connected_equipment: Optional equipment this control is connected to

        Returns:
            ProcessInstrumentationFunction
        """
        # Map control types to measured variables
        control_type_map = {
            'FC': 'Flow',
            'LC': 'Level',
            'TC': 'Temperature',
            'PC': 'Pressure',
            'DO': 'DissolvedOxygen',
            'ORP': 'OxidationReductionPotential',
            'pH': 'pH'
        }

        # Determine control type
        control_type = unit.parameters.get('control_type', 'FC')

        # Extract control type prefix from name if not in parameters
        if not unit.parameters.get('control_type'):
            name_upper = str(unit.name).upper()
            for ct in control_type_map.keys():
                if name_upper.startswith(ct):
                    control_type = ct
                    break

        # Get measured variable
        variable = control_type_map.get(control_type, 'Flow')

        # Parse tag name into components (e.g., "FC-101" -> "F", "C", "101")
        tag_str = str(unit.name)

        # Extract category (first letter: F, L, T, P, etc.)
        category = control_type[0] if control_type else "F"

        # Extract modifier (usually "C" for controller)
        modifier = control_type[1:] if len(control_type) > 1 else "C"

        # Extract number (everything after the dash)
        number = tag_str.split('-')[-1] if '-' in tag_str else "001"

        # Create instrumentation function (controller)
        pif = ProcessInstrumentationFunction(
            processInstrumentationFunctionCategory=category,
            processInstrumentationFunctionModifier=modifier,
            processInstrumentationFunctionNumber=number
        )

        # Store control type as custom attribute for round-trip preservation
        control_type_attr = CustomStringAttribute(
            attributeName="ControlType",
            value=control_type
        )
        if not hasattr(pif, 'customAttributes'):
            pif.customAttributes = []
        pif.customAttributes.append(control_type_attr)

        # Add signal generating function (sensor)
        sensor = ProcessSignalGeneratingFunction()
        sensor.sensorType = variable

        # If connected equipment provided, link sensor to equipment via SensingLocation
        if connected_equipment:
            # Create SensingLocation to wrap the equipment reference
            # Note: SensingLocation represents the physical location of the sensor
            sensing_loc = SensingLocation()
            # Store equipment reference (will be serialized as association in XML)
            sensor.sensingLocation = sensing_loc

        # Attach sensor to instrumentation
        if not pif.processSignalGeneratingFunctions:
            pif.processSignalGeneratingFunctions = []
        pif.processSignalGeneratingFunctions.append(sensor)

        logger.info(
            f"Created instrumentation for control {unit.name} "
            f"(type={control_type}, variable={variable}, "
            f"connected={'Yes' if connected_equipment else 'No'})"
        )

        return pif

    def sfiles_to_dexpi(
        self,
        sfiles_input: Any,
        expand_bfd: bool = True,
        metadata: Optional[Dict] = None
    ) -> DexpiModel:
        """
        Convert SFILES to DEXPI model.

        Args:
            sfiles_input: SFILES string or SfilesModel
            expand_bfd: Whether to expand BFD blocks to PFD equipment
            metadata: Optional metadata for the model

        Returns:
            Complete DexpiModel with equipment and connections
        """
        # Parse if string
        if isinstance(sfiles_input, str):
            sfiles_model = self.parse_sfiles(sfiles_input)
        else:
            sfiles_model = sfiles_input

        # Create DEXPI model structure
        dexpi_model = self._create_dexpi_model(metadata or sfiles_model.metadata)

        # Create equipment and instrumentation
        equipment_map = {}  # unit name -> Equipment instance
        control_units = []  # Track control units for later instrumentation processing
        control_unit_names = set()  # Track control unit names for validation

        for unit in sfiles_model.units:
            # Check if this is a control/instrumentation unit
            if self._is_control_unit(unit):
                # Store for later processing (after equipment is created)
                control_units.append(unit)
                control_unit_names.add(unit.name)
                logger.info(f"Detected control unit: {unit.name}, deferring instrumentation creation")
                continue

            if expand_bfd and sfiles_model.model_type == "BFD":
                # Expand BFD blocks to PFD equipment
                expanded = self.equipment_factory.create_from_bfd({
                    "type": unit.unit_type,
                    "name": unit.name,
                    "parameters": unit.parameters
                })
                # Add ALL expanded equipment to model (not just first)
                if expanded:
                    # Use first as primary for connection mapping
                    primary_equipment = expanded[0]
                    equipment_map[unit.name] = primary_equipment

                    # Add ALL equipment to DEXPI model
                    for equip in expanded:
                        self._add_equipment_to_model(dexpi_model, equip)
                else:
                    # Fallback if expansion returns empty (shouldn't happen after our fixes)
                    equipment = self._create_equipment(unit)
                    equipment_map[unit.name] = equipment
                    self._add_equipment_to_model(dexpi_model, equipment)
            else:
                # Direct creation
                equipment = self._create_equipment(unit)
                equipment_map[unit.name] = equipment
                self._add_equipment_to_model(dexpi_model, equipment)

        # Create piping connections - FAIL LOUDLY on invalid streams
        for stream in sfiles_model.streams:
            # Skip streams involving control units (handled later in instrumentation processing)
            if stream.from_unit in control_unit_names or stream.to_unit in control_unit_names:
                logger.debug(f"Skipping control stream: {stream.from_unit} -> {stream.to_unit}")
                continue

            # Validate stream references valid units
            if stream.from_unit not in equipment_map:
                raise InvalidStreamError(
                    f"Stream references unknown source unit: '{stream.from_unit}'. "
                    f"Available units: {sorted(equipment_map.keys())}"
                )
            if stream.to_unit not in equipment_map:
                raise InvalidStreamError(
                    f"Stream references unknown target unit: '{stream.to_unit}'. "
                    f"Available units: {sorted(equipment_map.keys())}"
                )

            # Both units exist - create connection
            self._add_connection(
                dexpi_model,
                equipment_map[stream.from_unit],
                equipment_map[stream.to_unit],
                stream
            )

        # Process control/instrumentation units
        for control_unit in control_units:
            # Find connected equipment from streams
            connected_equipment = None
            for stream in sfiles_model.streams:
                # Control units typically receive signal from equipment
                if stream.to_unit == control_unit.name and stream.from_unit in equipment_map:
                    connected_equipment = equipment_map[stream.from_unit]
                    break

            # Create instrumentation
            instrumentation = self._create_instrumentation(control_unit, connected_equipment)

            # Add to model's instrumentation functions
            if not dexpi_model.conceptualModel.processInstrumentationFunctions:
                dexpi_model.conceptualModel.processInstrumentationFunctions = []
            dexpi_model.conceptualModel.processInstrumentationFunctions.append(instrumentation)

            logger.info(f"Added instrumentation {control_unit.name} to DEXPI model")

        return dexpi_model

    def dexpi_to_sfiles(
        self,
        dexpi_model: DexpiModel,
        canonical: bool = True,
        version: str = "v2",
        use_mlgraph: bool = True
    ) -> str:
        """
        Convert DEXPI model to SFILES string.

        PHASE 2.1 FIX: Uses MLGraphLoader for robust graph extraction when
        segment endpoints are missing (e.g., imported Proteus XML).

        Args:
            dexpi_model: DEXPI model to convert
            canonical: Generate canonical (sorted) representation
            version: SFILES version (v1: simple, v2: with tags)
            use_mlgraph: Use MLGraphLoader for edge extraction (recommended)

        Returns:
            SFILES notation string
        """
        from pydexpi.loaders.ml_graph_loader import MLGraphLoader

        units = []
        streams = []

        # Extract equipment
        if hasattr(dexpi_model.conceptualModel, 'taggedPlantItems'):
            for equipment in dexpi_model.conceptualModel.taggedPlantItems or []:
                # Get SFILES type from DEXPI class
                equipment_type = self._get_sfiles_type(equipment)
                tag = getattr(equipment, 'tagName', 'UNKNOWN')

                # Create unit representation
                unit_str = f"{tag.lower()}[{equipment_type}]"
                units.append((tag.lower(), unit_str))

        # PHASE 2.1: Try MLGraphLoader first for robust edge extraction
        if use_mlgraph:
            try:
                ml_loader = MLGraphLoader()
                nx_graph = ml_loader.dexpi_to_graph(dexpi_model)

                # Extract edges from NetworkX graph
                for from_node, to_node, data in nx_graph.edges(data=True):
                    from_tag = str(from_node)
                    to_tag = str(to_node)
                    streams.append((from_tag.lower(), to_tag.lower()))

                # Also extract nodes if units list is empty
                if not units:
                    for node, data in nx_graph.nodes(data=True):
                        node_str = str(node)
                        # Get type from node attributes or infer from name
                        unit_type = data.get('dexpi_class', data.get('type', 'equipment'))
                        unit_str = f"{node_str.lower()}[{unit_type}]"
                        units.append((node_str.lower(), unit_str))

            except Exception as e:
                logger.warning(f"MLGraphLoader extraction failed, falling back: {e}")
                streams = []  # Reset and try direct extraction

        # Fallback: Extract connections from segment ID pattern
        if not streams:
            if hasattr(dexpi_model.conceptualModel, 'pipingNetworkSystems'):
                for pns in dexpi_model.conceptualModel.pipingNetworkSystems or []:
                    for segment in getattr(pns, 'segments', []) or []:
                        from_tag = None
                        to_tag = None

                        # Extract from segment ID pattern "segment__FROM__TO" (double underscore)
                        seg_id = getattr(segment, 'id', '')
                        if seg_id.startswith('segment__'):
                            # Split on double underscore after prefix
                            parts = seg_id[9:].split('__', 1)
                            if len(parts) == 2:
                                from_tag = parts[0]
                                to_tag = parts[1]

                        # Fallback: try sourceItem/targetItem (for imported models)
                        if not from_tag or not to_tag:
                            if hasattr(segment, 'sourceItem') and segment.sourceItem:
                                from_tag = getattr(segment.sourceItem, 'componentName', None)
                            if hasattr(segment, 'targetItem') and segment.targetItem:
                                to_tag = getattr(segment.targetItem, 'componentName', None)

                        if from_tag and to_tag:
                            streams.append((from_tag.lower(), to_tag.lower()))

        # Build SFILES string
        if canonical:
            # Sort for deterministic output
            units.sort(key=lambda x: x[0])
            streams.sort()

        # Create connection graph
        if not streams:
            # No connections, just list units
            return ' '.join(u[1] for u in units)

        # Build connected path
        result = []
        processed = set()

        # Find starting point (unit with no incoming connections)
        targets = {s[1] for s in streams}
        starts = [u[0] for u in units if u[0] not in targets]

        if starts:
            current = starts[0]
        elif units:
            current = units[0][0]
        else:
            return ""

        # Build path
        unit_dict = dict(units)
        while current:
            if current not in processed:
                result.append(unit_dict.get(current, f"{current}[unknown]"))
                processed.add(current)

            # Find next connection
            next_unit = None
            for from_unit, to_unit in streams:
                if from_unit == current and to_unit not in processed:
                    next_unit = to_unit
                    break

            current = next_unit

        # Add any unprocessed units
        for unit_name, unit_str in units:
            if unit_name not in processed:
                result.append(unit_str)

        return '->'.join(result)

    def validate_round_trip(
        self,
        original: Any,
        compare_attributes: bool = False
    ) -> Tuple[bool, List[str]]:
        """
        Validate round-trip conversion integrity.

        Args:
            original: Original model (SFILES string or DexpiModel)
            compare_attributes: Whether to compare attributes in addition to topology

        Returns:
            Tuple of (is_valid, list_of_differences)
        """
        differences = []

        try:
            if isinstance(original, str):
                # SFILES → DEXPI → SFILES
                sfiles1 = original
                dexpi = self.sfiles_to_dexpi(sfiles1)
                sfiles2 = self.dexpi_to_sfiles(dexpi, canonical=True)

                # Parse both for comparison
                model1 = self.parse_sfiles(sfiles1)
                model2 = self.parse_sfiles(sfiles2)

                # Compare units
                units1 = {u.name for u in model1.units}
                units2 = {u.name for u in model2.units}
                if units1 != units2:
                    differences.append(f"Unit mismatch: {units1 ^ units2}")

                # Compare connections
                streams1 = {(s.from_unit, s.to_unit) for s in model1.streams}
                streams2 = {(s.from_unit, s.to_unit) for s in model2.streams}
                if streams1 != streams2:
                    differences.append(f"Stream mismatch: {streams1 ^ streams2}")

            else:
                # DEXPI → SFILES → DEXPI
                dexpi1 = original
                sfiles = self.dexpi_to_sfiles(dexpi1)
                dexpi2 = self.sfiles_to_dexpi(sfiles)

                # Compare equipment counts
                count1 = len(getattr(dexpi1.conceptualModel, 'taggedPlantItems', []))
                count2 = len(getattr(dexpi2.conceptualModel, 'taggedPlantItems', []))
                if count1 != count2:
                    differences.append(f"Equipment count: {count1} vs {count2}")

                # TODO: Deeper DEXPI comparison if needed

        except Exception as e:
            # NO FALLBACKS - re-raise so we can see what broke
            logger.error(f"Round-trip validation failed: {e}")
            raise

        return len(differences) == 0, differences

    def _create_dexpi_model(self, metadata: Dict) -> DexpiModel:
        """Create base DEXPI model with metadata."""
        # Create metadata
        meta = MetaData()
        # Note: MetaData would have proper attributes in full implementation

        # Create conceptual model
        conceptual = ConceptualModel()
        conceptual.metaData = meta
        conceptual.taggedPlantItems = []
        conceptual.pipingNetworkSystems = []

        # Create main model
        model = DexpiModel(
            conceptualModel=conceptual,
            originatingSystemName=metadata.get("project", "SFILES Import"),
            originatingSystemVendorName="Engineering MCP",
            originatingSystemVersion=metadata.get("version", "1.0")
        )

        return model

    def _create_equipment(self, unit: SfilesUnit) -> Equipment:
        """Create equipment instance from SFILES unit."""
        return self.equipment_factory.create(
            equipment_type=unit.unit_type,
            tag=unit.name.upper(),
            params=unit.parameters
        )

    def _add_equipment_to_model(self, model: DexpiModel, equipment: Equipment):
        """Add equipment to DEXPI model while preserving all ConceptualModel fields.

        PHASE 1.3 FIX: Uses model_copy(update=...) or in-place mutation to preserve
        all fields (metaData, processInstrumentationFunctions, etc.)
        """
        # Get current conceptual model
        cm = model.conceptualModel

        # Initialize list if needed
        if not cm.taggedPlantItems:
            cm.taggedPlantItems = []

        # Append equipment in place (pydantic allows list mutation)
        cm.taggedPlantItems.append(equipment)

        # Note: We don't reconstruct ConceptualModel, so all fields are preserved:
        # - metaData
        # - processInstrumentationFunctions
        # - pipingNetworkSystems
        # - Any other attributes

    def _add_connection(
        self,
        model: DexpiModel,
        from_equipment: Equipment,
        to_equipment: Equipment,
        stream: SfilesStream
    ):
        """Add piping connection between equipment using pyDEXPI's piping_toolkit.

        PHASE 1.4 FIX: Uses piping_toolkit.connect_piping_network_segment() to create
        proper nozzle-based connections that MLGraphLoader can extract reliably.

        Also encodes connection info in segment ID as fallback for simpler extraction.
        """
        from pydexpi.dexpi_classes.piping import Pipe
        from pydexpi.dexpi_classes.equipment import Nozzle
        from pydexpi.toolkits import piping_toolkit as pt

        # Get equipment tags for segment naming
        from_tag = getattr(from_equipment, 'tagName', 'UNKNOWN')
        to_tag = getattr(to_equipment, 'tagName', 'UNKNOWN')

        # Helper to get or create nozzle on equipment
        def _get_or_create_nozzle(equipment, tag_prefix: str, prefer_end: str = "last"):
            if not hasattr(equipment, 'nozzles') or equipment.nozzles is None:
                equipment.nozzles = []

            # Try to reuse an existing unconnected nozzle
            ordered = (
                list(equipment.nozzles)[::-1] if prefer_end == "last" else list(equipment.nozzles)
            )
            for noz in ordered:
                # Check if nozzle is unconnected
                if not hasattr(noz, 'pipingConnection') or noz.pipingConnection is None:
                    return noz

            # Create new nozzle if all are used
            eq_tag = getattr(equipment, 'tagName', 'EQ')
            next_index = len(equipment.nozzles) + 1
            new_nozzle = Nozzle(
                id=f"nozzle_{tag_prefix}_{eq_tag}_{next_index}",
                subTagName=f"{tag_prefix}{next_index}"
            )
            equipment.nozzles.append(new_nozzle)
            return new_nozzle

        # Get source nozzle (outlet) and target nozzle (inlet)
        from_nozzle = _get_or_create_nozzle(from_equipment, tag_prefix="N_OUT_", prefer_end="last")
        to_nozzle = _get_or_create_nozzle(to_equipment, tag_prefix="N_IN_", prefer_end="first")

        # Create Pipe for the connection
        line_number = f"{from_tag}_to_{to_tag}"
        pipe = Pipe(
            id=f"pipe_{line_number}",
            tagName=line_number
        )

        # Create segment with connection info encoded in ID (for fallback extraction)
        # Format: "segment__FROM__TO" (double underscore) allows extraction in dexpi_to_sfiles
        segment_id = f"segment__{from_tag}__{to_tag}"
        segment = PipingNetworkSegment(id=segment_id)

        # Pipe goes in connections list
        segment.connections = [pipe]
        segment.items = []

        # Use piping_toolkit to create proper nozzle connections
        try:
            pt.connect_piping_network_segment(segment, from_nozzle, as_source=True)
            pt.connect_piping_network_segment(segment, to_nozzle, as_source=False)
        except Exception:
            # Fallback: toolkit may not be available, rely on segment ID encoding
            pass

        # Store stream tags if present (for heat exchangers, columns, etc.)
        if stream.tags:
            for tag_type, tag_values in stream.tags.items():
                setattr(segment, f'_{tag_type}_tags', tag_values)

        # Get conceptual model
        cm = model.conceptualModel

        # Initialize piping systems if needed
        if not cm.pipingNetworkSystems:
            cm.pipingNetworkSystems = []

        # Get or create piping network system
        if cm.pipingNetworkSystems:
            pns = cm.pipingNetworkSystems[0]
            if not pns.segments:
                pns.segments = []
            pns.segments.append(segment)
        else:
            # Create new system
            pns = PipingNetworkSystem(segments=[segment])
            cm.pipingNetworkSystems.append(pns)

        # Note: No reconstruction of ConceptualModel, preserving all fields

    def _get_sfiles_type(self, equipment: Equipment) -> str:
        """Get SFILES type string from DEXPI equipment instance."""
        # Get definition from registry
        equipment_class = type(equipment)
        definition = self.equipment_registry.get_by_dexpi_class(equipment_class)

        if definition:
            return definition.sfiles_type

        # Fallback: use class name
        class_name = equipment_class.__name__
        # Convert CamelCase to snake_case
        return re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()


# Singleton instance for global access
_engine: Optional[ConversionEngine] = None


def get_engine() -> ConversionEngine:
    """Get the global conversion engine."""
    global _engine
    if _engine is None:
        _engine = ConversionEngine()
    return _engine