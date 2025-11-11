"""
Unified Component Registry for ALL 272 pyDEXPI Classes

This module consolidates registration and factory methods for:
- Equipment (159 classes)
- Piping (79 classes)
- Instrumentation (34 classes)

Replaces the partial equipment.py registry and provides comprehensive coverage.
"""

from typing import Dict, List, Optional, Any, Type, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import csv
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================================
# Exception Classes
# ============================================================================

class UnknownComponentTypeError(ValueError):
    """Raised when component type is not registered."""
    pass


class ComponentInstantiationError(RuntimeError):
    """Raised when component cannot be instantiated."""
    pass


# ============================================================================
# Import ALL 272 pyDEXPI Classes
# ============================================================================

# Equipment classes (159)
from pydexpi.dexpi_classes.equipment import (
    # Import ALL equipment classes from CSV
    Equipment,
    # A
    Agglomerator, Agitator, AgitatorRotor, AirCoolingSystem, AirEjector,
    AlternatingCurrentGenerator, AlternatingCurrentMotor, AlternatingCurrentMotorAsComponent,
    AxialBlower, AxialCompressor, AxialFan,
    # B
    BatchWeigher, Blower, Boiler, BriquettingRoller, Burner,
    # C
    CentrifugalBlower, CentrifugalCompressor, CentrifugalPump, Centrifuge,
    Chamber, ChamberOwner, Chimney,
    ColumnInternalsArrangement, ColumnPackingsArrangement, ColumnSection, ColumnTraysArrangement,
    CombustionEngine, CombustionEngineAsComponent, Compressor, ContinuousWeigher,
    ConvectionDryer, Conveyor, CoolingTower, CoolingTowerRotor,
    Crusher, CrusherElement,
    CustomAgglomerator, CustomBlower, CustomCentrifuge, CustomCompressor, CustomCoolingTower,
    CustomDryer, CustomElectricGenerator, CustomEquipment, CustomExtruder, CustomFan,
    CustomFilter, CustomHeatExchanger, CustomHeater, CustomMill, CustomMixer,
    CustomMobileTransportSystem, CustomMotor, CustomPump, CustomSeparator, CustomSieve,
    CustomStationaryTransportSystem, CustomTurbine, CustomVessel, CustomWasteGasEmitter, CustomWeigher,
    # D
    DirectCurrentGenerator, DirectCurrentMotor, DirectCurrentMotorAsComponent,
    Displacer, DryCoolingTower, Dryer, DryingChamber,
    # E
    EjectorPump, ElectricGenerator, ElectricHeater, ElectricalSeparator,
    Extruder,
    # F
    Fan, Feeder, Filter, FilterUnit, FilteringCentrifuge, FilteringCentrifugeDrum,
    Flare, ForkliftTruck, Furnace,
    # G
    GasFilter, GasTurbine, GearBox, GravitationalSeparator, Grinder, GrindingElement,
    # H
    HeatExchanger, HeatExchangerRotor, HeatedSurfaceDryer, Heater,
    # I
    Impeller,
    # K
    Kneader,
    # L
    Lift, LiquidFilter, LoadingUnloadingSystem,
    # M
    MechanicalSeparator, Mill, Mixer, MixingElementAssembly, MobileTransportSystem,
    Motor, MotorAsComponent,
    # N
    Nozzle, NozzleOwner,
    # P
    PackagingSystem, PelletizerDisc, PlateHeatExchanger, PressureVessel, ProcessColumn, Pump,
    # R
    RadialFan, RailWaggon, ReciprocatingCompressor, ReciprocatingExtruder,
    ReciprocatingPressureAgglomerator, ReciprocatingPump,
    RevolvingSieve, RotaryCompressor, RotaryMixer, RotaryPump,
    RotatingExtruder, RotatingGrowthAgglomerator, RotatingPressureAgglomerator,
    # S
    Screw, ScrubbingSeparator, SedimentalCentrifuge, SedimentalCentrifugeDrum,
    Separator, Ship, Sieve, SieveElement, Silo,
    SpiralHeatExchanger, SprayCooler, SprayNozzle, StaticMixer,
    StationarySieve, StationaryTransportSystem, SteamGenerator, SteamTurbine,
    SubTaggedColumnSection,
    # T
    TaggedColumnSection, TaggedPlantItem, Tank, ThinFilmEvaporator,
    TransportableContainer, Truck, TubeBundle, TubularHeatExchanger, Turbine,
    # V
    Vessel, VibratingSieve,
    # W
    WasteGasEmitter, Weigher, WetCoolingTower
)

# Piping classes (79)
from pydexpi.dexpi_classes.piping import (
    # Valves (22)
    AngleBallValve, AngleGlobeValve, AnglePlugValve, AngleValve,
    BallValve, BreatherValve, ButterflyValve, CheckValve,
    CustomCheckValve, CustomOperatedValve, CustomSafetyValveOrFitting,
    GateValve, GlobeCheckValve, GlobeValve, NeedleValve, OperatedValve,
    PlugValve, SafetyValveOrFitting,
    SpringLoadedAngleGlobeSafetyValve, SpringLoadedGlobeSafetyValve,
    StraightwayValve, SwingCheckValve,
    # Connections (6)
    BlindFlange, ClampedFlangeCoupling, DirectPipingConnection,
    Flange, FlangedConnection, PipingConnection,
    # Filtration (2)
    ConicalStrainer, Strainer,
    # Flow Measurement (10)
    ElectromagneticFlowMeter, FlowMeasuringElement, FlowNozzle,
    MassFlowMeasuringElement, PositiveDisplacementFlowMeter, RestrictionOrifice,
    TurbineFlowMeter, VariableAreaFlowMeter, VenturiTube, VolumeFlowMeasuringElement,
    # Pipes and Fittings (14)
    CustomPipeFitting, FlowInPipeOffPageConnector, FlowOutPipeOffPageConnector,
    Pipe, PipeCoupling, PipeFitting, PipeFlangeSpacer, PipeFlangeSpade,
    PipeOffPageConnector, PipeOffPageConnectorObjectReference,
    PipeOffPageConnectorReference, PipeOffPageConnectorReferenceByNumber,
    PipeReducer, PipeTee,
    # Safety (2)
    FlameArrestor, RuptureDisc,
    # Structure (3)
    PipingNetworkSegment, PipingNetworkSegmentItem, PipingNetworkSystem,
    # Other (20)
    Compensator, CustomInlinePrimaryElement, CustomPipingComponent,
    Funnel, Hose, IlluminatedSightGlass, InLineMixer, InlinePrimaryElement,
    LineBlind, Penetration, PipingComponent, PipingNode, PipingNodeOwner,
    PipingSourceItem, PipingTargetItem, PropertyBreak,
    SightGlass, Silencer, SteamTrap, VentilationDevice
)

# Instrumentation classes (34)
from pydexpi.dexpi_classes.instrumentation import (
    # Actuating (9)
    ActuatingElectricalFunction, ActuatingElectricalLocation, ActuatingElectricalSystem,
    ActuatingFunction, ActuatingSystem, ControlledActuator,
    CustomActuatingElectricalSystemComponent, CustomActuatingSystemComponent,
    Positioner,
    # Signal (13)
    CustomProcessSignalGeneratingSystemComponent,
    FlowInSignalOffPageConnector, FlowOutSignalOffPageConnector,
    SignalConveyingFunction, SignalConveyingFunctionSource, SignalConveyingFunctionTarget,
    SignalLineFunction, MeasuringLineFunction,
    SignalOffPageConnector, SignalOffPageConnectorObjectReference,
    SignalOffPageConnectorReference, SignalOffPageConnectorReferenceByNumber,
    ProcessSignalGeneratingSystem,
    # Measurement (4)
    InlinePrimaryElementReference, OfflinePrimaryElement, PrimaryElement,
    # Control (3)
    InstrumentationLoopFunction, ProcessControlFunction, ProcessInstrumentationFunction,
    # Signal Generating (1)
    ProcessSignalGeneratingFunction,
    # Sensing (1)
    SensingLocation,
    # Detectors/Transmitters (3)
    ElectronicFrequencyConverter, FlowDetector, Transmitter,
    # References (1)
    OperatedValveReference
)

from pydexpi.dexpi_classes.pydantic_classes import PipingNode


# ============================================================================
# Category Enums
# ============================================================================

class ComponentCategory(Enum):
    """Component categories across all types."""
    # Equipment
    ROTATING = "rotating"
    HEAT_TRANSFER = "heat_transfer"
    SEPARATION = "separation"
    STORAGE = "storage"
    REACTION = "reaction"
    TREATMENT = "treatment"
    TRANSPORT = "transport"
    CUSTOM = "custom"  # Generic/abstract equipment
    # Piping
    VALVE = "valve"
    PIPE = "pipe"
    CONNECTION = "connection"
    FLOW_MEASUREMENT = "flow_measurement"
    FILTRATION = "filtration"
    SAFETY = "safety"
    STRUCTURE = "structure"  # Piping network structures
    OTHER_PIPING = "other_piping"  # Other piping components
    # Instrumentation
    ACTUATING = "actuating"
    SIGNAL = "signal"
    MEASUREMENT = "measurement"
    CONTROL = "control"
    CONTROL_LOOP = "control_loop"
    SENSING = "sensing"
    DETECTOR = "detector"
    TRANSMITTER = "transmitter"
    CONVERTER = "converter"
    OTHER_INSTRUMENTATION = "other_instrumentation"  # Other instrumentation


class ComponentType(Enum):
    """Top-level component type."""
    EQUIPMENT = "equipment"
    PIPING = "piping"
    INSTRUMENTATION = "instrumentation"


# ============================================================================
# Component Definition
# ============================================================================

@dataclass
class ComponentDefinition:
    """Complete definition of a component (equipment/piping/instrumentation)."""
    # Identifiers
    sfiles_alias: str  # SFILES notation (e.g., "pump", "valve_ball", "transmitter")
    dexpi_class: Type  # pyDEXPI class
    component_type: ComponentType  # Equipment, Piping, or Instrumentation

    # Classification
    category: ComponentCategory
    display_name: str = ""
    description: str = ""

    # Family relationships (for 1:Many mappings)
    is_primary: bool = False  # Is this the primary class for a family?
    family: Optional[str] = None  # Family name (e.g., "pump", "ball_valve")

    # Symbol mapping
    symbol_id: Optional[str] = None  # Symbol ID (real or placeholder)
    symbol_variants: List[str] = field(default_factory=list)

    # Connection/Nozzle defaults
    connection_count: int = 2  # For piping/instrumentation
    nozzle_count_default: int = 2  # For equipment
    nozzle_count_min: int = 0
    nozzle_count_max: Optional[int] = None

    # Attributes
    required_attributes: List[str] = field(default_factory=list)
    optional_attributes: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Unified Component Registry
# ============================================================================

class ComponentRegistry:
    """
    Unified registry for ALL 272 pyDEXPI components.

    Manages equipment, piping, and instrumentation with consistent interface.
    """

    def __init__(self):
        """Initialize registry and load all registrations."""
        self._definitions: Dict[str, ComponentDefinition] = {}
        self._alias_map: Dict[str, str] = {}  # SFILES alias → canonical ID
        self._class_map: Dict[Type, str] = {}  # pyDEXPI class → canonical ID
        self._family_map: Dict[str, List[str]] = {}  # Family → list of member IDs

        self._load_all_registrations()

    def _load_all_registrations(self):
        """Load registrations from CSV files."""
        # CSVs are now packaged with the module in src/core/data/
        data_dir = Path(__file__).parent / "data"

        # Load equipment
        self._load_category_registrations(
            data_dir / "equipment_registrations.csv",
            ComponentType.EQUIPMENT
        )

        # Load piping
        self._load_category_registrations(
            data_dir / "piping_registrations.csv",
            ComponentType.PIPING
        )

        # Load instrumentation
        self._load_category_registrations(
            data_dir / "instrumentation_registrations.csv",
            ComponentType.INSTRUMENTATION
        )

        logger.info(f"Loaded {len(self._definitions)} component definitions")
        logger.info(f"  Equipment: {self._count_by_type(ComponentType.EQUIPMENT)}")
        logger.info(f"  Piping: {self._count_by_type(ComponentType.PIPING)}")
        logger.info(f"  Instrumentation: {self._count_by_type(ComponentType.INSTRUMENTATION)}")
        logger.info(f"  Families: {len(self._family_map)}")

    def _load_category_registrations(self, csv_path: Path, component_type: ComponentType):
        """Load registrations from a CSV file."""
        if not csv_path.exists():
            raise RuntimeError(
                f"Required registration file not found: {csv_path}. "
                f"This indicates a packaging or installation issue. "
                f"Expected location: {csv_path.parent}"
            )

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self._register_from_csv(row, component_type)

    def _register_from_csv(self, row: Dict[str, str], component_type: ComponentType):
        """Register a component from CSV row."""
        class_name = row['class_name']
        sfiles_alias = row['sfiles_alias']
        is_primary = row['is_primary'].lower() == 'true'
        family = row['family'] if row['family'] else None
        category_str = row['category']
        symbol_id = row['symbol_id']
        display_name = row['display_name']

        # Get connection/nozzle count
        if component_type == ComponentType.EQUIPMENT:
            connection_count = 0
            nozzle_count = int(row['nozzle_count'])
        else:
            connection_count = int(row['connection_count'])
            nozzle_count = 0

        # Map category string to enum
        try:
            category = ComponentCategory[category_str.upper()]
        except KeyError:
            logger.warning(f"Unknown category '{category_str}' for {class_name}, using fallback")
            # Fallback to generic categories
            if component_type == ComponentType.EQUIPMENT:
                category = ComponentCategory.CUSTOM
            elif component_type == ComponentType.PIPING:
                category = ComponentCategory.OTHER_PIPING
            else:
                category = ComponentCategory.OTHER_INSTRUMENTATION

        # Get pyDEXPI class
        dexpi_class = self._get_class_by_name(class_name, component_type)
        if not dexpi_class:
            logger.error(f"Could not find pyDEXPI class: {class_name}")
            return

        # Create definition
        definition = ComponentDefinition(
            sfiles_alias=sfiles_alias,
            dexpi_class=dexpi_class,
            component_type=component_type,
            category=category,
            display_name=display_name,
            is_primary=is_primary,
            family=family,
            symbol_id=symbol_id,
            connection_count=connection_count,
            nozzle_count_default=nozzle_count,
            required_attributes=["tagName"]
        )

        # Register
        canonical_id = f"{component_type.value}_{class_name}"
        self._definitions[canonical_id] = definition

        # Only register PRIMARY classes in alias map to avoid overwriting
        # Non-primary classes are still accessible via class lookup and family lookup
        if is_primary or sfiles_alias not in self._alias_map:
            self._alias_map[sfiles_alias] = canonical_id

        self._class_map[dexpi_class] = canonical_id

        # Track family
        if family:
            if family not in self._family_map:
                self._family_map[family] = []
            self._family_map[family].append(canonical_id)

    def _get_class_by_name(self, class_name: str, component_type: ComponentType) -> Optional[Type]:
        """Get pyDEXPI class by name."""
        # Import the appropriate module
        if component_type == ComponentType.EQUIPMENT:
            import pydexpi.dexpi_classes.equipment as module
        elif component_type == ComponentType.PIPING:
            import pydexpi.dexpi_classes.piping as module
        else:  # INSTRUMENTATION
            import pydexpi.dexpi_classes.instrumentation as module

        return getattr(module, class_name, None)

    def _count_by_type(self, component_type: ComponentType) -> int:
        """Count components by type."""
        return sum(1 for d in self._definitions.values() if d.component_type == component_type)

    # ========================================================================
    # Query Methods
    # ========================================================================

    def get_by_alias(self, sfiles_alias: str) -> Optional[ComponentDefinition]:
        """Get component definition by SFILES alias."""
        canonical_id = self._alias_map.get(sfiles_alias.lower())
        return self._definitions.get(canonical_id) if canonical_id else None

    def get_by_class(self, dexpi_class: Type) -> Optional[ComponentDefinition]:
        """Get component definition by pyDEXPI class."""
        canonical_id = self._class_map.get(dexpi_class)
        return self._definitions.get(canonical_id) if canonical_id else None

    def get_family_members(self, family: str) -> List[ComponentDefinition]:
        """Get all component definitions in a family."""
        member_ids = self._family_map.get(family, [])
        return [self._definitions[mid] for mid in member_ids if mid in self._definitions]

    def get_all_by_type(self, component_type: ComponentType) -> List[ComponentDefinition]:
        """Get all components of a specific type."""
        return [d for d in self._definitions.values() if d.component_type == component_type]

    def get_all_by_category(self, category: ComponentCategory) -> List[ComponentDefinition]:
        """Get all components in a category."""
        return [d for d in self._definitions.values() if d.category == category]

    def list_all_aliases(self, component_type: Optional[ComponentType] = None) -> List[str]:
        """List all SFILES aliases, optionally filtered by type."""
        if component_type:
            return [
                d.sfiles_alias for d in self._definitions.values()
                if d.component_type == component_type
            ]
        return list(self._alias_map.keys())

    def get_dexpi_class(self, type_str: str) -> Type:
        """
        Get pyDEXPI class for any type string (SFILES alias or class name).
        Raises UnknownComponentTypeError if not found.
        """
        # Try as alias first
        definition = self.get_by_alias(type_str)
        if definition:
            return definition.dexpi_class

        # Try as class name
        for defn in self._definitions.values():
            if defn.dexpi_class.__name__ == type_str:
                return defn.dexpi_class

        # Not found
        available = sorted(self._alias_map.keys())[:20]
        raise UnknownComponentTypeError(
            f"Unknown component type: '{type_str}'. "
            f"Available aliases (first 20): {available}"
        )


# ============================================================================
# Singleton Instance
# ============================================================================

_registry_instance: Optional[ComponentRegistry] = None

def get_registry() -> ComponentRegistry:
    """Get singleton component registry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ComponentRegistry()
    return _registry_instance


# ============================================================================
# Factory Functions
# ============================================================================

def create_component(
    type_str: str,
    tag: str,
    params: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Any:
    """
    Create a component of any type (equipment/piping/instrumentation).

    Args:
        type_str: SFILES alias or pyDEXPI class name
        tag: Tag name for the component
        params: Optional parameters dictionary
        **kwargs: Additional keyword arguments

    Returns:
        Instantiated pyDEXPI component

    Raises:
        UnknownComponentTypeError: If type not found
        ComponentInstantiationError: If instantiation fails
    """
    registry = get_registry()

    # Get definition
    definition = registry.get_by_alias(type_str)
    if not definition:
        # Try as class name
        dexpi_class = registry.get_dexpi_class(type_str)
        definition = registry.get_by_class(dexpi_class)

    if not definition:
        raise UnknownComponentTypeError(f"Unknown component type: '{type_str}'")

    # Merge params and kwargs
    all_params = params.copy() if params else {}
    all_params.update(kwargs)
    all_params['tagName'] = tag

    # Instantiate
    try:
        component = definition.dexpi_class(**all_params)
        return component
    except Exception as e:
        raise ComponentInstantiationError(
            f"Failed to instantiate {definition.dexpi_class.__name__}: {e}"
        ) from e
