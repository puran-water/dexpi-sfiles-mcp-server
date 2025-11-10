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

    # SFILES regex patterns (consolidated from multiple sources)
    UNIT_PATTERN = re.compile(r'(\w+)\[([^\]]+)\](?:\(([^)]+)\))?')
    STREAM_PATTERN = re.compile(r'(\w+)(?:\[[^\]]+\])?(?:\([^)]+\))?\s*->\s*(\w+)')
    PROPERTY_PATTERN = re.compile(r'(\w+)=([^,]+)')
    TAG_PATTERN = re.compile(r'{([^:]+):([^}]+)}')

    def __init__(
        self,
        equipment_factory: Optional[EquipmentFactory] = None,
        symbol_registry: Optional[SymbolRegistry] = None
    ):
        """Initialize conversion engine with registries."""
        self.equipment_factory = equipment_factory or get_factory()
        self.equipment_registry = get_registry()
        self.symbol_registry = symbol_registry or get_symbol_registry()

    def parse_sfiles(self, sfiles_string: str) -> SfilesModel:
        """
        Parse SFILES string into structured model.

        Supports formats:
        - Simple: unit1[type]->unit2[type]
        - With properties: unit1[type](prop=val)->unit2[type]
        - With tags: unit1[type]->unit2[type]{col:C101,he:HE101}

        Args:
            sfiles_string: SFILES notation string

        Returns:
            Parsed SfilesModel
        """
        units = []
        streams = []
        unit_map = {}  # name -> SfilesUnit

        # Clean and normalize string
        sfiles_string = sfiles_string.strip()

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

        # Determine model type (BFD if any BFD-specific types found)
        model_type = "PFD"
        bfd_types = ['reactor', 'clarifier', 'treatment', 'separation']
        if any(unit.unit_type.lower() in bfd_types for unit in units):
            model_type = "BFD"

        return SfilesModel(
            units=units,
            streams=streams,
            model_type=model_type
        )

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

        # Create equipment
        equipment_map = {}  # unit name -> Equipment instance

        for unit in sfiles_model.units:
            if expand_bfd and sfiles_model.model_type == "BFD":
                # Expand BFD blocks to PFD equipment
                expanded = self.equipment_factory.create_from_bfd({
                    "type": unit.unit_type,
                    "name": unit.name,
                    "parameters": unit.parameters
                })
                # Use first equipment as primary (for now)
                if expanded:
                    equipment = expanded[0]
                else:
                    equipment = self._create_equipment(unit)
            else:
                # Direct creation
                equipment = self._create_equipment(unit)

            equipment_map[unit.name] = equipment
            self._add_equipment_to_model(dexpi_model, equipment)

        # Create piping connections
        for stream in sfiles_model.streams:
            if stream.from_unit in equipment_map and stream.to_unit in equipment_map:
                self._add_connection(
                    dexpi_model,
                    equipment_map[stream.from_unit],
                    equipment_map[stream.to_unit],
                    stream
                )

        return dexpi_model

    def dexpi_to_sfiles(
        self,
        dexpi_model: DexpiModel,
        canonical: bool = True,
        version: str = "v2"
    ) -> str:
        """
        Convert DEXPI model to SFILES string.

        Args:
            dexpi_model: DEXPI model to convert
            canonical: Generate canonical (sorted) representation
            version: SFILES version (v1: simple, v2: with tags)

        Returns:
            SFILES notation string
        """
        units = []
        streams = []

        # Extract equipment
        if hasattr(dexpi_model.conceptualModel, 'taggedPlantItems'):
            for equipment in dexpi_model.conceptualModel.taggedPlantItems:
                # Get SFILES type from DEXPI class
                equipment_type = self._get_sfiles_type(equipment)
                tag = getattr(equipment, 'tagName', 'UNKNOWN')

                # Create unit representation
                unit_str = f"{tag.lower()}[{equipment_type}]"
                units.append((tag.lower(), unit_str))

        # Extract connections
        if hasattr(dexpi_model.conceptualModel, 'pipingNetworkSystems'):
            for pns in dexpi_model.conceptualModel.pipingNetworkSystems:
                if hasattr(pns, 'pipingNetworkSegments'):
                    for segment in pns.pipingNetworkSegments:
                        from_tag = getattr(segment, 'from_tag', None)
                        to_tag = getattr(segment, 'to_tag', None)
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
        """Add equipment to DEXPI model."""
        # Correct attribute name from DeepWiki: taggedPlantItems (not taggedPlantItems assignment)
        # pydexpi uses pydantic - must use model_copy or pass to constructor
        if not model.conceptualModel.taggedPlantItems:
            # Initialize with current equipment
            current_items = []
        else:
            current_items = list(model.conceptualModel.taggedPlantItems)

        current_items.append(equipment)
        # Reassign the whole list (pydantic requirement)
        model.conceptualModel = ConceptualModel(
            taggedPlantItems=current_items,
            pipingNetworkSystems=model.conceptualModel.pipingNetworkSystems or []
        )

    def _add_connection(
        self,
        model: DexpiModel,
        from_equipment: Equipment,
        to_equipment: Equipment,
        stream: SfilesStream
    ):
        """Add piping connection between equipment."""
        # Correct API from DeepWiki:
        # - PipingNetworkSystem uses 'segments' not 'pipingNetworkSegments'
        # - ConceptualModel uses 'pipingNetworkSystems'
        # - pydantic requires proper initialization, not attribute assignment

        # Create segment
        segment = PipingNetworkSegment()
        # Note: These attributes may not exist, this is a simplified implementation
        # Full implementation should use piping_toolkit.connect_piping_network_segment

        # Get or create piping network system
        current_systems = list(model.conceptualModel.pipingNetworkSystems) if model.conceptualModel.pipingNetworkSystems else []

        if current_systems:
            # Add to existing system
            existing_segments = list(current_systems[0].segments) if current_systems[0].segments else []
            existing_segments.append(segment)
            current_systems[0] = PipingNetworkSystem(
                segments=existing_segments
            )
        else:
            # Create new system
            current_systems = [PipingNetworkSystem(segments=[segment])]

        # Update model
        model.conceptualModel = ConceptualModel(
            taggedPlantItems=model.conceptualModel.taggedPlantItems or [],
            pipingNetworkSystems=current_systems
        )

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