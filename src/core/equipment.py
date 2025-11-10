"""
Core Equipment Module - Single Source of Truth for Equipment Types and Creation

This module consolidates all equipment-related logic from:
- sfiles_dexpi_mapper.py (type mappings)
- pfd_expansion_engine.py (BFD to PFD mappings)
- model_service.py (equipment creation)
- dexpi_tools.py (DEXPI class instantiation)

Provides a unified, clean API for equipment handling across the system.
"""

from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass, field
from enum import Enum
import logging


# Exception classes for fail-loud error handling
class UnknownEquipmentTypeError(ValueError):
    """Raised when equipment type is not registered in the equipment registry."""
    pass


class TemplateNotFoundError(ValueError):
    """Raised when BFD template is not found for the specified process type."""
    pass

# Import pyDEXPI classes - VERIFIED against actual installed package
# NO FALLBACKS - fail fast if imports don't work
# Imports verified via: python -c "from pydexpi.dexpi_classes import equipment; inspect.getmembers(equipment)"
from pydexpi.dexpi_classes.equipment import (
    # Core base classes
    Equipment,
    Nozzle,
    # Vessels and tanks
    Tank,
    Vessel,
    ProcessColumn,
    # Pumps and compressors
    Pump,
    CentrifugalPump,
    Compressor,
    CentrifugalCompressor,
    # Heat transfer
    HeatExchanger,
    Heater,
    CustomHeater,
    # Separation
    Separator,
    Centrifuge,
    Filter,
    # Mixing
    Mixer,
    Agitator,
    # Rotating equipment
    Turbine,
    Blower,
    Fan,
    # Drying
    Dryer,
    # Other
    CustomEquipment,
    Furnace
)

# Import PipingNode from pydantic classes for nozzle connection points
from pydexpi.dexpi_classes.pydantic_classes import PipingNode

logger = logging.getLogger(__name__)


class EquipmentCategory(Enum):
    """Equipment categories for organization and filtering."""
    ROTATING = "rotating"
    STATIC = "static"
    HEAT_TRANSFER = "heat_transfer"
    SEPARATION = "separation"
    REACTION = "reaction"
    STORAGE = "storage"
    TRANSPORT = "transport"
    TREATMENT = "treatment"
    CUSTOM = "custom"


@dataclass
class EquipmentDefinition:
    """Complete definition of an equipment type."""
    # Identifiers
    sfiles_type: str  # SFILES notation (e.g., "pump", "reactor")
    dexpi_class: Type[Equipment]  # pyDEXPI class
    bfd_type: Optional[str] = None  # BFD block type if applicable

    # Metadata
    category: EquipmentCategory = EquipmentCategory.CUSTOM
    display_name: str = ""
    description: str = ""

    # Symbol mapping
    symbol_id: Optional[str] = None  # Default symbol ID
    symbol_variants: List[str] = field(default_factory=list)  # Alternative symbols

    # Attributes and validation
    required_attributes: List[str] = field(default_factory=list)
    optional_attributes: Dict[str, Any] = field(default_factory=dict)
    nozzle_count_default: int = 2
    nozzle_count_min: int = 0
    nozzle_count_max: Optional[int] = None

    # Template expansion (for BFD → PFD)
    expansion_template: Optional[str] = None
    expansion_params: Dict[str, Any] = field(default_factory=dict)


class EquipmentRegistry:
    """
    Central registry for all equipment types and mappings.
    Consolidates mappings from multiple sources into single source of truth.
    """

    def __init__(self):
        """Initialize the registry with all known equipment types."""
        self._definitions: Dict[str, EquipmentDefinition] = {}
        self._sfiles_map: Dict[str, str] = {}  # SFILES type → canonical ID
        self._dexpi_map: Dict[Type[Equipment], str] = {}  # DEXPI class → canonical ID
        self._bfd_map: Dict[str, str] = {}  # BFD type → canonical ID

        self._register_all_equipment()

    def _register_all_equipment(self):
        """Register all known equipment types."""

        # Pumps (from multiple sources) - Updated to PP001A format
        self._register(EquipmentDefinition(
            sfiles_type="pump",
            dexpi_class=CentrifugalPump,
            bfd_type="pumping",
            category=EquipmentCategory.ROTATING,
            display_name="Centrifugal Pump",
            description="Rotodynamic pump for liquid transfer",
            symbol_id="PP001A",  # NOAKADEXPI standard format
            required_attributes=["tagName"],
            optional_attributes={"flowRate": None, "head": None, "power": None},
            nozzle_count_default=2
        ))

        self._register(EquipmentDefinition(
            sfiles_type="pump_centrifugal",
            dexpi_class=CentrifugalPump,
            category=EquipmentCategory.ROTATING,
            display_name="Centrifugal Pump",
            symbol_id="PP001A"
        ))

        self._register(EquipmentDefinition(
            sfiles_type="pump_reciprocating",
            dexpi_class=Pump,  # Generic pump class
            category=EquipmentCategory.ROTATING,
            display_name="Reciprocating Pump",
            symbol_id="PP010A"
        ))

        # Tanks and Vessels - Updated to PP001A format
        self._register(EquipmentDefinition(
            sfiles_type="tank",
            dexpi_class=Tank,
            bfd_type="storage",
            category=EquipmentCategory.STORAGE,
            display_name="Storage Tank",
            description="Atmospheric storage vessel",
            symbol_id="PE025A",  # Verified in merged catalog
            required_attributes=["tagName"],
            optional_attributes={"volume": None, "diameter": None, "height": None},
            nozzle_count_default=4
        ))

        self._register(EquipmentDefinition(
            sfiles_type="vessel",
            dexpi_class=Vessel,
            category=EquipmentCategory.STORAGE,
            display_name="Pressure Vessel",
            symbol_id="PT002A",  # Verified in XLSM catalog
            nozzle_count_default=4
        ))

        self._register(EquipmentDefinition(
            sfiles_type="reactor",
            dexpi_class=Vessel,  # Note: pydexpi has no Reactor class, use Vessel
            bfd_type="reaction",
            category=EquipmentCategory.REACTION,
            display_name="Reactor",
            description="Chemical reactor vessel",
            symbol_id="PE003A",  # Placeholder
            expansion_template="cstr_reactor",
            nozzle_count_default=4
        ))

        # Heat Transfer Equipment - Updated to PP001A format
        self._register(EquipmentDefinition(
            sfiles_type="heat_exchanger",
            dexpi_class=HeatExchanger,
            bfd_type="heat_exchange",
            category=EquipmentCategory.HEAT_TRANSFER,
            display_name="Heat Exchanger",
            symbol_id="PE037A",  # Verified in merged catalog
            nozzle_count_default=4
        ))

        self._register(EquipmentDefinition(
            sfiles_type="heater",
            dexpi_class=Heater,
            category=EquipmentCategory.HEAT_TRANSFER,
            display_name="Heater",
            symbol_id="PE001A"  # Placeholder
        ))

        self._register(EquipmentDefinition(
            sfiles_type="cooler",
            dexpi_class=HeatExchanger,  # Note: pydexpi has no Cooler class, use HeatExchanger
            category=EquipmentCategory.HEAT_TRANSFER,
            display_name="Cooler",
            symbol_id="PE002A"  # Placeholder
        ))

        # Separation Equipment - Updated to PP001A format
        self._register(EquipmentDefinition(
            sfiles_type="separator",
            dexpi_class=Separator,
            bfd_type="separation",
            category=EquipmentCategory.SEPARATION,
            display_name="Separator",
            symbol_id="PE012A"  # Verified in merged catalog
        ))

        self._register(EquipmentDefinition(
            sfiles_type="centrifuge",
            dexpi_class=Centrifuge,
            category=EquipmentCategory.SEPARATION,
            display_name="Centrifuge",
            symbol_id="PE030A"  # Verified in merged catalog
        ))

        self._register(EquipmentDefinition(
            sfiles_type="filter",
            dexpi_class=Filter,
            bfd_type="filtration",
            category=EquipmentCategory.SEPARATION,
            display_name="Filter",
            symbol_id="PS014A"  # Verified in merged catalog
        ))

        self._register(EquipmentDefinition(
            sfiles_type="column",
            dexpi_class=ProcessColumn,
            bfd_type="distillation",
            category=EquipmentCategory.SEPARATION,
            display_name="Process Column",
            symbol_id="PE004A",  # Placeholder
            nozzle_count_default=6
        ))

        # Mixing Equipment - Updated to PP001A format
        self._register(EquipmentDefinition(
            sfiles_type="mixer",
            dexpi_class=Mixer,
            bfd_type="mixing",
            category=EquipmentCategory.REACTION,
            display_name="Mixer",
            symbol_id="PE005A"  # Placeholder
        ))

        self._register(EquipmentDefinition(
            sfiles_type="agitator",
            dexpi_class=Agitator,
            category=EquipmentCategory.REACTION,
            display_name="Agitator",
            symbol_id="PE006A"  # Placeholder
        ))

        # Compressors and Blowers - Updated to PP001A format
        self._register(EquipmentDefinition(
            sfiles_type="compressor",
            dexpi_class=Compressor,
            bfd_type="compression",
            category=EquipmentCategory.ROTATING,
            display_name="Compressor",
            symbol_id="PA001A"  # Placeholder (using PA for compressors)
        ))

        self._register(EquipmentDefinition(
            sfiles_type="blower",
            dexpi_class=Blower,
            category=EquipmentCategory.ROTATING,
            display_name="Blower",
            symbol_id="PA002A"  # Placeholder
        ))

        self._register(EquipmentDefinition(
            sfiles_type="fan",
            dexpi_class=Fan,
            category=EquipmentCategory.ROTATING,
            display_name="Fan",
            symbol_id="PA003A"  # Placeholder
        ))

        # Special Equipment - Updated to PP001A format
        self._register(EquipmentDefinition(
            sfiles_type="dryer",
            dexpi_class=Dryer,
            bfd_type="drying",
            category=EquipmentCategory.TREATMENT,
            display_name="Dryer",
            symbol_id="PD001A"  # Placeholder (using PD for dryers)
        ))

        self._register(EquipmentDefinition(
            sfiles_type="furnace",
            dexpi_class=Furnace,
            category=EquipmentCategory.HEAT_TRANSFER,
            display_name="Furnace",
            symbol_id="PE007A"  # Placeholder
        ))

        self._register(EquipmentDefinition(
            sfiles_type="turbine",
            dexpi_class=Turbine,
            category=EquipmentCategory.ROTATING,
            display_name="Turbine",
            symbol_id="PT011A"  # Placeholder
        ))

        # BFD-specific blocks (from pfd_expansion_engine)
        self._register(EquipmentDefinition(
            sfiles_type="clarifier",
            dexpi_class=Separator,
            bfd_type="clarification",
            category=EquipmentCategory.SEPARATION,
            display_name="Clarifier",
            expansion_template="primary_clarification"
        ))

        self._register(EquipmentDefinition(
            sfiles_type="treatment",
            dexpi_class=CustomEquipment,
            bfd_type="treatment",
            category=EquipmentCategory.TREATMENT,
            display_name="Treatment System"
        ))

        # Fallback for unknown types
        self._register(EquipmentDefinition(
            sfiles_type="custom",
            dexpi_class=CustomEquipment,
            category=EquipmentCategory.CUSTOM,
            display_name="Custom Equipment"
        ))

    def _register(self, definition: EquipmentDefinition):
        """Register an equipment definition."""
        # Generate canonical ID
        canonical_id = f"{definition.category.value}_{definition.sfiles_type}"

        # Store definition
        self._definitions[canonical_id] = definition

        # Update lookup maps
        self._sfiles_map[definition.sfiles_type] = canonical_id
        self._dexpi_map[definition.dexpi_class] = canonical_id

        if definition.bfd_type:
            self._bfd_map[definition.bfd_type] = canonical_id

        # Set display name if not provided
        if not definition.display_name:
            definition.display_name = definition.sfiles_type.replace("_", " ").title()

    def get_by_sfiles_type(self, sfiles_type: str) -> Optional[EquipmentDefinition]:
        """Get equipment definition by SFILES type."""
        canonical_id = self._sfiles_map.get(sfiles_type.lower())
        return self._definitions.get(canonical_id) if canonical_id else None

    def get_by_dexpi_class(self, dexpi_class: Type[Equipment]) -> Optional[EquipmentDefinition]:
        """Get equipment definition by DEXPI class."""
        canonical_id = self._dexpi_map.get(dexpi_class)
        return self._definitions.get(canonical_id) if canonical_id else None

    def get_by_bfd_type(self, bfd_type: str) -> Optional[EquipmentDefinition]:
        """Get equipment definition by BFD block type."""
        canonical_id = self._bfd_map.get(bfd_type.lower())
        return self._definitions.get(canonical_id) if canonical_id else None

    def get_all_by_category(self, category: EquipmentCategory) -> List[EquipmentDefinition]:
        """Get all equipment definitions in a category."""
        return [d for d in self._definitions.values() if d.category == category]

    def get_dexpi_class(self, type_str: str) -> Type[Equipment]:
        """
        Get DEXPI class for any type string (SFILES, BFD, or canonical).
        Raises UnknownEquipmentTypeError if not found.
        """
        # Try SFILES type
        definition = self.get_by_sfiles_type(type_str)
        if definition:
            return definition.dexpi_class

        # Try BFD type
        definition = self.get_by_bfd_type(type_str)
        if definition:
            return definition.dexpi_class

        # FAIL LOUDLY - no silent fallbacks
        available_types = list(self._sfiles_map.keys()) + list(self._bfd_map.keys())
        raise UnknownEquipmentTypeError(
            f"Unknown equipment type: '{type_str}'. "
            f"Available types: {sorted(set(available_types))}"
        )

    def list_all_types(self) -> Dict[str, List[str]]:
        """List all registered types organized by category."""
        result = {}
        for definition in self._definitions.values():
            category_name = definition.category.value
            if category_name not in result:
                result[category_name] = []
            result[category_name].append(definition.sfiles_type)
        return result


class EquipmentFactory:
    """
    Factory for creating equipment instances.
    Consolidates creation logic from multiple sources.
    """

    def __init__(self, registry: Optional[EquipmentRegistry] = None):
        """Initialize factory with registry."""
        self.registry = registry or EquipmentRegistry()

    def create(
        self,
        equipment_type: str,
        tag: str,
        params: Optional[Dict[str, Any]] = None,
        nozzles: Optional[List] = None
    ) -> Equipment:
        """
        Create equipment instance with proper initialization.

        Args:
            equipment_type: SFILES type, BFD type, or DEXPI class name
            tag: Equipment tag/ID
            params: Optional equipment-specific parameters
            nozzles: Optional nozzle configuration

        Returns:
            Initialized pyDEXPI equipment instance
        """
        params = params or {}

        # Get equipment definition
        definition = (
            self.registry.get_by_sfiles_type(equipment_type) or
            self.registry.get_by_bfd_type(equipment_type)
        )

        if not definition:
            # FAIL LOUDLY - no silent fallbacks
            available = sorted(set(
                list(self.registry._sfiles_map.keys()) +
                list(self.registry._bfd_map.keys())
            ))
            raise UnknownEquipmentTypeError(
                f"Unknown equipment type: '{equipment_type}'. "
                f"Available types: {available}"
            )

        # Prepare nozzles
        if nozzles is None:
            nozzles = self._create_default_nozzles(definition)

        # Create instance
        try:
            # Get the class
            equipment_class = definition.dexpi_class

            # Prepare constructor arguments
            kwargs = {
                "tagName": tag.upper(),
                "nozzles": nozzles
            }

            # Add optional attributes if provided
            for attr, default in definition.optional_attributes.items():
                if attr in params:
                    kwargs[attr] = params[attr]

            # Special handling for CustomEquipment
            if equipment_class == CustomEquipment:
                kwargs["typeName"] = definition.display_name

            # Create instance
            equipment = equipment_class(**kwargs)

            # Set additional attributes not in constructor
            for key, value in params.items():
                if hasattr(equipment, key) and key not in kwargs:
                    setattr(equipment, key, value)

            # Attach metadata for later use
            equipment._definition = definition
            equipment._symbol_id = definition.symbol_id

            logger.debug(f"Created {equipment_class.__name__} with tag {tag}")
            return equipment

        except Exception as e:
            logger.error(f"Failed to create equipment {tag} of type {equipment_type}: {e}")
            # NO FALLBACKS - re-raise the exception so we know what broke
            raise

    def _create_default_nozzles(self, definition: EquipmentDefinition) -> List[Nozzle]:
        """
        Create default nozzles based on equipment definition.

        Creates nozzles with piping nodes that specify connection properties
        (nominal diameter and pressure) following DEXPI standard.

        Args:
            definition: Equipment definition with nozzle count

        Returns:
            List of Nozzle instances with default naming (N1, N2, N3, etc.)
            and standard connection properties (DN50, PN16)
        """
        nozzles = []
        for i in range(definition.nozzle_count_default):
            # Create piping node with connection properties
            # Per DEXPI standard, diameter and pressure info lives in PipingNode
            piping_node = PipingNode(
                nominalDiameterRepresentation="DN50",
                nominalDiameterNumericalValueRepresentation="50",
            )

            # Create nozzle with sequential naming and piping node
            nozzle = Nozzle(
                subTagName=f"N{i+1}",
                nominalPressureRepresentation="PN16",
                nodes=[piping_node]
            )
            nozzles.append(nozzle)
        return nozzles

    def create_from_bfd(
        self,
        bfd_block: Dict[str, Any],
        area_code: str = "100"
    ) -> List[Equipment]:
        """
        Create PFD equipment from BFD block using expansion templates.

        Args:
            bfd_block: BFD block definition with type and parameters
            area_code: Area code for context (not used in tag generation)

        Returns:
            List of equipment instances (expanded from BFD)

        Note:
            The area_code parameter is kept for future expansion template use,
            but is NOT added as a suffix to equipment tags. Equipment tags
            should match the original block names from SFILES.
        """
        block_type = bfd_block.get("type", "").lower()
        block_name = bfd_block.get("name", "UNKNOWN")

        # Get definition for BFD type
        definition = self.registry.get_by_bfd_type(block_type)
        if not definition:
            # FAIL LOUDLY - no silent fallbacks
            available_bfd = sorted(self.registry._bfd_map.keys())
            raise TemplateNotFoundError(
                f"No BFD template found for type: '{block_type}'. "
                f"Available BFD types: {available_bfd}"
            )

        # Check for expansion template
        if definition.expansion_template:
            # This would integrate with template expansion engine
            # For now, create single equipment with original block name
            return [self.create(
                equipment_type=definition.sfiles_type,
                tag=block_name,
                params=bfd_block.get("parameters", {})
            )]
        else:
            # Direct mapping, single equipment with original block name
            return [self.create(
                equipment_type=definition.sfiles_type,
                tag=block_name,
                params=bfd_block.get("parameters", {})
            )]


# Singleton instances for global access
_registry = EquipmentRegistry()
_factory = EquipmentFactory(_registry)


def get_registry() -> EquipmentRegistry:
    """Get the global equipment registry."""
    return _registry


def get_factory() -> EquipmentFactory:
    """Get the global equipment factory."""
    return _factory