#!/usr/bin/env python3
"""
Generate equipment registration data for all 159 pyDEXPI equipment classes.

This script uses DexpiIntrospector to enumerate all equipment classes and generates:
1. CSV file with registration metadata
2. Python code for EquipmentDefinition entries
3. 1:Many SFILES mapping definitions
"""

import sys
import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from tools.dexpi_introspector import DexpiIntrospector
from core.symbols import get_registry as get_symbol_registry


class EquipmentCategorizer:
    """Categorize equipment into EquipmentCategory types."""

    # Category mapping rules (keyword → category)
    CATEGORY_RULES = {
        # ROTATING
        'pump': 'ROTATING',
        'compressor': 'ROTATING',
        'blower': 'ROTATING',
        'fan': 'ROTATING',
        'turbine': 'ROTATING',
        'motor': 'ROTATING',
        'rotor': 'ROTATING',
        'engine': 'ROTATING',
        'generator': 'ROTATING',

        # HEAT_TRANSFER
        'heat': 'HEAT_TRANSFER',
        'heater': 'HEAT_TRANSFER',
        'exchanger': 'HEAT_TRANSFER',
        'cooler': 'HEAT_TRANSFER',
        'cooling': 'HEAT_TRANSFER',
        'boiler': 'HEAT_TRANSFER',
        'furnace': 'HEAT_TRANSFER',
        'burner': 'HEAT_TRANSFER',
        'steam': 'HEAT_TRANSFER',

        # SEPARATION
        'separator': 'SEPARATION',
        'centrifuge': 'SEPARATION',
        'filter': 'SEPARATION',
        'sieve': 'SEPARATION',
        'column': 'SEPARATION',

        # STORAGE
        'tank': 'STORAGE',
        'vessel': 'STORAGE',
        'silo': 'STORAGE',
        'chamber': 'STORAGE',
        'container': 'STORAGE',

        # TREATMENT
        'dryer': 'TREATMENT',
        'drying': 'TREATMENT',
        'treatment': 'TREATMENT',
        'evaporator': 'TREATMENT',

        # REACTION
        'mixer': 'REACTION',
        'agitator': 'REACTION',
        'kneader': 'REACTION',

        # TRANSPORT
        'conveyor': 'TRANSPORT',
        'screw': 'TRANSPORT',
        'lift': 'TRANSPORT',
        'truck': 'TRANSPORT',
        'ship': 'TRANSPORT',
        'waggon': 'TRANSPORT',
        'forklift': 'TRANSPORT',
        'transport': 'TRANSPORT',
        'loading': 'TRANSPORT',
        'unloading': 'TRANSPORT',

        # Processing/Handling
        'crusher': 'TREATMENT',
        'mill': 'TREATMENT',
        'grinder': 'TREATMENT',
        'extruder': 'TREATMENT',
        'agglomerator': 'TREATMENT',
        'pelletizer': 'TREATMENT',
        'briquetting': 'TREATMENT',
        'weigher': 'TREATMENT',
        'feeder': 'TREATMENT',
        'packaging': 'TREATMENT',

        # Emissions/Safety
        'flare': 'TREATMENT',
        'chimney': 'TREATMENT',
        'waste': 'TREATMENT',
    }

    @classmethod
    def categorize(cls, class_name: str) -> str:
        """Determine category based on class name."""
        name_lower = class_name.lower()

        # Check each rule
        for keyword, category in cls.CATEGORY_RULES.items():
            if keyword in name_lower:
                return category

        # Default to CUSTOM
        return 'CUSTOM'


class SFILESAliasGenerator:
    """Generate SFILES aliases from DEXPI class names."""

    # Known 1:Many mappings (SFILES alias → primary class)
    PRIMARY_MAPPINGS = {
        'pump': 'CentrifugalPump',
        'compressor': 'Compressor',
        'blower': 'Blower',
        'fan': 'Fan',
        'heat_exchanger': 'HeatExchanger',
        'heater': 'Heater',
        'separator': 'Separator',
        'centrifuge': 'Centrifuge',
        'filter': 'Filter',
        'mixer': 'Mixer',
        'agitator': 'Agitator',
        'tank': 'Tank',
        'vessel': 'Vessel',
        'column': 'ProcessColumn',
        'turbine': 'Turbine',
        'dryer': 'Dryer',
        'furnace': 'Furnace',
    }

    # Family groupings (base alias → [variant classes])
    FAMILIES = {
        'pump': ['Pump', 'CentrifugalPump', 'ReciprocatingPump', 'RotaryPump', 'EjectorPump', 'CustomPump'],
        'compressor': ['Compressor', 'CentrifugalCompressor', 'AxialCompressor', 'ReciprocatingCompressor', 'RotaryCompressor', 'CustomCompressor'],
        'blower': ['Blower', 'CentrifugalBlower', 'AxialBlower', 'CustomBlower'],
        'fan': ['Fan', 'AxialFan', 'RadialFan', 'CustomFan'],
        'heat_exchanger': ['HeatExchanger', 'PlateHeatExchanger', 'SpiralHeatExchanger', 'TubularHeatExchanger', 'CustomHeatExchanger'],
        'heater': ['Heater', 'ElectricHeater', 'CustomHeater'],
        'separator': ['Separator', 'GravitationalSeparator', 'MechanicalSeparator', 'ElectricalSeparator', 'ScrubbingSeparator', 'CustomSeparator'],
        'centrifuge': ['Centrifuge', 'FilteringCentrifuge', 'SedimentalCentrifuge', 'CustomCentrifuge'],
        'filter': ['Filter', 'GasFilter', 'LiquidFilter', 'CustomFilter'],
        'turbine': ['Turbine', 'SteamTurbine', 'GasTurbine', 'CustomTurbine'],
        'motor': ['Motor', 'AlternatingCurrentMotor', 'DirectCurrentMotor', 'CustomMotor'],
        'generator': ['ElectricGenerator', 'AlternatingCurrentGenerator', 'DirectCurrentGenerator', 'CustomElectricGenerator'],
        'sieve': ['Sieve', 'StationarySieve', 'RevolvingSieve', 'VibratingSieve', 'CustomSieve'],
        'weigher': ['Weigher', 'BatchWeigher', 'ContinuousWeigher', 'CustomWeigher'],
        'cooling_tower': ['CoolingTower', 'WetCoolingTower', 'DryCoolingTower', 'CustomCoolingTower'],
        'dryer': ['Dryer', 'ConvectionDryer', 'HeatedSurfaceDryer', 'CustomDryer'],
    }

    @classmethod
    def to_snake_case(cls, name: str) -> str:
        """Convert CamelCase to snake_case."""
        # Insert underscore before uppercase letters
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        # Insert underscore before uppercase letters preceded by lowercase
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    @classmethod
    def generate_alias(cls, class_name: str) -> Tuple[str, bool]:
        """
        Generate SFILES alias for a class name.

        Returns:
            Tuple of (alias, is_primary)
            is_primary = True if this is the primary class for a family
        """
        # Check if this is a primary class
        for alias, primary_class in cls.PRIMARY_MAPPINGS.items():
            if class_name == primary_class:
                return (alias, True)

        # Check if this is a variant in a family
        for family_alias, members in cls.FAMILIES.items():
            if class_name in members:
                # Generate variant alias
                # Remove the base word and convert to snake_case
                base_word = family_alias.replace('_', '')
                variant_part = class_name.replace(members[0], '')
                if variant_part:
                    variant_alias = f"{family_alias}_{cls.to_snake_case(variant_part)}"
                else:
                    variant_alias = family_alias
                return (variant_alias, False)

        # Default: simple snake_case conversion
        return (cls.to_snake_case(class_name), False)

    @classmethod
    def get_family(cls, class_name: str) -> Optional[str]:
        """Get the family alias if this class belongs to one."""
        for family_alias, members in cls.FAMILIES.items():
            if class_name in members:
                return family_alias
        return None


class SymbolMapper:
    """Map component classes to NOAKADEXPI symbols.

    Phase 3 Pass 1: Extended to support equipment, piping, and instrumentation.
    """

    # Known symbol mappings from validation script and Phase 3 Pass 1
    KNOWN_MAPPINGS = {
        # Equipment (existing)
        'CentrifugalPump': 'PP001A',
        'Pump': 'PP001A',  # Generic pump
        'ReciprocatingPump': 'PP010A',
        'Tank': 'PE025A',
        'Vessel': 'PT002A',
        'HeatExchanger': 'PE037A',
        'Separator': 'PE012A',
        'Centrifuge': 'PE030A',
        'Filter': 'PS014A',

        # Phase 3 Pass 1: Rotating Equipment
        'Turbine': 'PE021A_Origo',
        'CentrifugalCompressor': 'PP011A_Origo',
        'Agitator': 'PP017A_Origo',

        # Phase 3 Pass 1: Valves
        'BallValve': 'PV019A',
        'GateValve': 'PV005A_Option1',
        'GlobeValve': 'PV007A_Origo',
        'ButterflyValve': 'PV018A',
        'CheckValve': 'PV013A_Detail',
        'NeedleValve': 'PV016A_Origo',
        'PlugValve': 'PV023A_Origo',

        # Phase 3 Pass 1: Instrumentation
        'FlowDetector': 'PF002A',
        'ProcessControlFunction': 'ND0006',

        # Phase 3 Pass 2: Remaining Pass 1 targets (valves)
        'AngleBallValve': 'PV019A',  # Use BallValve symbol (same base type)
        'AngleGlobeValve': 'PV007A_Origo',  # Use GlobeValve symbol (same base type)
        'AnglePlugValve': 'PV023A_Origo',  # Use PlugValve symbol (same base type)
        'AngleValve': 'PV008A',  # Generic angle valve
        'BreatherValve': 'PV011A',  # Generic valve
        'GlobeCheckValve': 'PV013A_Detail',  # Use CheckValve symbol (check valve variant)
        'OperatedValve': 'PV021A',  # Generic operated valve
        'SafetyValveOrFitting': 'PV002A',  # Blind flange (safety fitting)
        'SpringLoadedGlobeSafetyValve': 'PV008B',  # Generic safety valve
        'SpringLoadedAngleGlobeSafetyValve': 'PV008B',  # Generic safety valve
        'SwingCheckValve': 'PV013A_Detail',  # Use CheckValve symbol (check valve variant)

        # Phase 3 Pass 2: Remaining Pass 1 targets (rotating equipment)
        'AlternatingCurrentMotor': 'PP013A',  # Generic motor
        'DirectCurrentMotor': 'PP013A',  # Generic motor
        'AxialCompressor': 'PP011A_Origo',  # Use CentrifugalCompressor (compressor family)
        'ReciprocatingCompressor': 'PP011A_Origo',  # Use CentrifugalCompressor (compressor family)
        'RotaryCompressor': 'PP011A_Origo',  # Use CentrifugalCompressor (compressor family)
        'AxialBlower': 'PP013A_Detail',  # Generic blower/fan
        'CentrifugalBlower': 'PP013A_Detail',  # Generic blower/fan
        'AxialFan': 'PP013A_Detail',  # Generic blower/fan
        'CentrifugalFan': 'PP013A_Detail',  # Generic blower/fan
        'RadialFan': 'PP013A_Detail',  # Generic blower/fan
        'GasTurbine': 'PE021A_Origo',  # Use Turbine symbol (turbine family)
        'SteamTurbine': 'PE021A_Origo',  # Use Turbine symbol (turbine family)

        # Phase 3 Pass 2: Remaining Pass 1 targets (instrumentation)
        'ActuatingFunction': 'IM005B_Option1',  # Actuating device
        'ActuatingSystem': 'IM005B_Option1',  # Actuating device
        'ControlledActuator': 'IM005B_Option1',  # Actuating device
        'Positioner': 'IM017A',  # Instrument component
        'Transmitter': 'IM017B',  # Transmitter device
        'SensingLocation': 'IM017C',  # Sensor/detector

        # Phase 3 Pass 2: Common equipment (long tail)
        'Heater': 'PE037A',  # Use HeatExchanger symbol
        'ElectricHeater': 'PE037A',  # Use HeatExchanger symbol
        'Boiler': 'PE037A',  # Use HeatExchanger symbol
        'SteamGenerator': 'PE037A',  # Use HeatExchanger symbol
        'Furnace': 'PE037A',  # Use HeatExchanger symbol
        'Dryer': 'PE037A',  # Heat treatment equipment
        'ConvectionDryer': 'PE037A',  # Heat treatment equipment
        'Mixer': 'PP017A_Origo',  # Use Agitator symbol (mixing equipment)
        'RotaryMixer': 'PP017A_Origo',  # Use Agitator symbol
        'InLineMixer': 'PP017A_Origo',  # Use Agitator symbol
        'StaticMixer': 'PP017A_Origo',  # Use Agitator symbol
        'LiquidFilter': 'PS014A',  # Use Filter symbol
        'GasFilter': 'PS014A',  # Use Filter symbol
        'Silo': 'PE025A',  # Use Tank symbol
        'Blower': 'PP013A_Detail',  # Generic blower
        'Compressor': 'PP011A_Origo',  # Generic compressor
        'Fan': 'PP013A_Detail',  # Generic fan
        'Motor': 'PP013A',  # Generic motor
        'Pump': 'PP001A',  # Generic pump (already exists)
        'RotaryPump': 'PP001A',  # Use generic pump
        'EjectorPump': 'PP001A',  # Use generic pump
        'Crusher': 'PS014A',  # Mechanical processing
        'Grinder': 'PS014A',  # Mechanical processing
        'Mill': 'PS014A',  # Mechanical processing
        'Sieve': 'PS014A',  # Separation equipment
        'Conveyor': 'PC023A',  # Transport equipment
        'Feeder': 'PC023A',  # Transport equipment
        'Weigher': 'PC023A',  # Transport/measurement
        'Extruder': 'PC023A',  # Transport/forming
        'ProcessColumn': 'PT002A',  # Use Vessel symbol
        'PressureVessel': 'PT002A',  # Use Vessel symbol
        'Vessel': 'PT002A',  # Already mapped

        # Phase 3 Pass 2: Custom* variants (use base class symbols)
        'CustomPump': 'PP001A',  # Use Pump symbol
        'CustomCompressor': 'PP011A_Origo',  # Use Compressor symbol
        'CustomMotor': 'PP013A',  # Use Motor symbol
        'CustomFan': 'PP013A_Detail',  # Use Fan symbol
        'CustomHeatExchanger': 'PE037A',  # Use HeatExchanger symbol
        'CustomHeater': 'PE037A',  # Use HeatExchanger symbol
        'CustomDryer': 'PE037A',  # Use HeatExchanger symbol
        'CustomMixer': 'PP017A_Origo',  # Use Agitator symbol
        'CustomFilter': 'PS014A',  # Use Filter symbol
        'CustomCentrifuge': 'PE030A',  # Use Centrifuge symbol
        'CustomSeparator': 'PE012A',  # Use Separator symbol
        'CustomSieve': 'PS014A',  # Use Filter symbol
        'CustomVessel': 'PT002A',  # Use Vessel symbol
        'CustomEquipment': 'PE037A',  # Generic equipment

        # Phase 3 Pass 2: Common piping components
        'Hose': 'PP001A',  # Flexible piping (use pump symbol as generic)
        'Strainer': 'PS014A',  # Use Filter symbol
        'ConicalStrainer': 'PS014A',  # Use Filter symbol
        'Silencer': 'PE037A',  # Process equipment
        'SteamTrap': 'PV013A_Detail',  # Valve-like device
        'RuptureDisc': 'PV002A',  # Safety device (use blind flange)
        'FlameArrestor': 'PS014A',  # Safety/filtration device
        'SightGlass': 'PE037A',  # Observation device
        'Compensator': 'PC023A',  # Piping component
        'PipeReducer': 'PC023A',  # Piping fitting
        'PipeTee': 'PC023A',  # Piping fitting
        'PipeFitting': 'PC023A',  # Generic fitting
        'FlangedConnection': 'PC023A',  # Connection
        'PipingConnection': 'PC023A',  # Connection
        'Funnel': 'PE025A',  # Use Tank symbol (tank-like)

        # Phase 3 Pass 2: Additional instrumentation
        'InlinePrimaryElement': 'PF002A',  # Use FlowDetector symbol
        'OfflinePrimaryElement': 'PF002A',  # Use FlowDetector symbol
        'PrimaryElement': 'PF002A',  # Use FlowDetector symbol
        'SignalLineFunction': 'ND0006',  # Signal/control
        'MeasuringLineFunction': 'PF002A',  # Measurement
        'InstrumentationLoopFunction': 'ND0006',  # Control loop
        'ProcessInstrumentationFunction': 'ND0006',  # Generic instrumentation
        'ProcessSignalGeneratingFunction': 'PF002A',  # Signal generation
        'SignalConveyingFunction': 'ND0006',  # Signal transmission
        'ActuatingElectricalFunction': 'IM005B_Option1',  # Electrical actuator
        'ActuatingElectricalSystem': 'IM005B_Option1',  # Electrical actuator system
        'ActuatingElectricalLocation': 'IM005B_Option1',  # Electrical actuator location
        'SignalOffPageConnector': 'ND0006',  # Signal connector
        'SignalOffPageConnectorReference': 'ND0006',  # Signal connector reference
        'SignalOffPageConnectorObjectReference': 'ND0006',  # Signal object reference
        'SignalOffPageConnectorReferenceByNumber': 'ND0006',  # Signal number reference
        'SignalConveyingFunctionSource': 'ND0006',  # Signal source
        'SignalConveyingFunctionTarget': 'ND0006',  # Signal target
        'FlowInSignalOffPageConnector': 'ND0006',  # Flow signal in
        'FlowOutSignalOffPageConnector': 'ND0006',  # Flow signal out
        'InlinePrimaryElementReference': 'PF002A',  # Inline element reference
        'OperatedValveReference': 'PV021A',  # Valve reference (use OperatedValve)
        'ElectronicFrequencyConverter': 'IM017A',  # Electronic converter

        # Phase 3 Pass 2: Remaining Custom* variants
        'CustomAgglomerator': 'PS014A',  # Use Filter/processing symbol
        'CustomCoolingTower': 'PE037A',  # Use HeatExchanger symbol
        'CustomElectricGenerator': 'PP013A',  # Use Motor symbol
        'CustomExtruder': 'PC023A',  # Use Extruder/Conveyor symbol
        'CustomMill': 'PS014A',  # Use Mill/Crusher symbol
        'CustomMobileTransportSystem': 'PC023A',  # Use transport symbol
        'CustomStationaryTransportSystem': 'PC023A',  # Use transport symbol
        'CustomWasteGasEmitter': 'PE037A',  # Process equipment
        'CustomWeigher': 'PC023A',  # Use Weigher/Transport symbol
        'CustomPipingComponent': 'PC023A',  # Generic piping
        'CustomPipeFitting': 'PC023A',  # Piping fitting
        'CustomOperatedValve': 'PV021A',  # Use OperatedValve symbol
        'CustomInlinePrimaryElement': 'PF002A',  # Flow measurement
        'CustomActuatingSystemComponent': 'IM005B_Option1',  # Actuator
        'CustomActuatingElectricalSystemComponent': 'IM005B_Option1',  # Electrical actuator
        'CustomProcessSignalGeneratingSystemComponent': 'PF002A',  # Signal generation

        # Phase 3 Pass 2: Cooling equipment
        'CoolingTower': 'PE037A',  # Heat transfer equipment
        'CoolingTowerRotor': 'PE037A',  # Cooling tower component
        'AirCoolingSystem': 'PE037A',  # Cooling system
        'DryCoolingTower': 'PE037A',  # Cooling tower variant
        'WetCoolingTower': 'PE037A',  # Cooling tower variant

        # Phase 3 Pass 2: Basic piping components
        'Pipe': 'PC023A',  # Basic pipe
        'PipeCoupling': 'PC023A',  # Pipe coupling
        'PipeOffPageConnector': 'PC023A',  # Off-page connector
        'PipeOffPageConnectorReference': 'PC023A',  # Connector reference
        'PipeOffPageConnectorObjectReference': 'PC023A',  # Object reference
        'PipeOffPageConnectorReferenceByNumber': 'PC023A',  # Number reference
        'FlowInPipeOffPageConnector': 'PC023A',  # Flow in connector
        'FlowOutPipeOffPageConnector': 'PC023A',  # Flow out connector
        'DirectPipingConnection': 'PC023A',  # Direct connection
        'LineBlind': 'PV002A',  # Use blind flange
        'PipeFlangeSpacer': 'PC023A',  # Flange spacer
        'PipeFlangeSpade': 'PV002A',  # Flange spade (blind)
        'ClampedFlangeCoupling': 'PC023A',  # Flange coupling
        'Penetration': 'PC023A',  # Pipe penetration

        # Phase 3 Pass 2: Flow measurement
        'FlowMeasuringElement': 'PF002A',  # Flow measurement
        'FlowNozzle': 'PF002A',  # Flow nozzle
        'MassFlowMeasuringElement': 'PF002A',  # Mass flow meter
        'ElectromagneticFlowMeter': 'PF002A',  # EM flow meter
        'PositiveDisplacementFlowMeter': 'PF002A',  # PD flow meter
        'TurbineFlowMeter': 'PF002A',  # Turbine flow meter
        'VariableAreaFlowMeter': 'PF002A',  # Variable area meter
        'VenturiTube': 'PF002A',  # Venturi meter
        'RestrictionOrifice': 'PF002A',  # Orifice plate
        'VolumeFlowMeasuringElement': 'PF002A',  # Volume flow meter
    }

    def __init__(self):
        """Initialize symbol mapper with registry."""
        try:
            self.symbol_registry = get_symbol_registry()
        except Exception as e:
            print(f"Warning: Could not load symbol registry: {e}")
            self.symbol_registry = None

    def map_symbol(self, class_name: str, category: str, component_type: str = 'equipment') -> str:
        """
        Map component class to symbol ID.

        Args:
            class_name: DEXPI class name (e.g., 'CentrifugalPump')
            category: Component category (e.g., 'ROTATING', 'VALVE')
            component_type: Type of component ('equipment', 'piping', 'instrumentation')

        Returns:
            Symbol ID or placeholder (with 'Z' suffix if no real symbol found)
        """
        # Check known mappings first
        if class_name in self.KNOWN_MAPPINGS:
            return self.KNOWN_MAPPINGS[class_name]

        # Try symbol registry
        if self.symbol_registry:
            try:
                symbol = self.symbol_registry.get_by_dexpi_class(class_name)
                if symbol:
                    return symbol.symbol_id
            except:
                pass

        # Generate placeholder based on component type and category
        if component_type == 'equipment':
            prefix_map = {
                'ROTATING': 'PP',  # Pumps/Prime movers
                'HEAT_TRANSFER': 'PE',  # Process equipment
                'SEPARATION': 'PS',  # Separation
                'STORAGE': 'PT',  # Tanks/Vessels
                'TREATMENT': 'PD',  # Dryers/Treatment
                'REACTION': 'PE',  # Process equipment
                'TRANSPORT': 'PM',  # Material handling
                'CUSTOM': 'PX',  # Custom
            }
            prefix = prefix_map.get(category, 'PX')
        elif component_type == 'piping':
            prefix_map = {
                'VALVE': 'PV',  # Valves
                'PIPE': 'PP',  # Pipes
                'CONNECTION': 'PC',  # Connections/Flanges
                'FLOW_MEASUREMENT': 'PF',  # Flow meters
                'FILTRATION': 'PS',  # Strainers/Filters
                'SAFETY': 'PV',  # Safety devices
                'STRUCTURE': 'PN',  # Network/Structure
                'OTHER_PIPING': 'PL',  # Other piping
            }
            prefix = prefix_map.get(category, 'PL')
        elif component_type == 'instrumentation':
            prefix_map = {
                'ACTUATING': 'IM',  # Actuators
                'TRANSMITTER': 'IM',  # Transmitters
                'SIGNAL': 'IM',  # Signal functions
                'SENSING': 'IM',  # Sensors
                'DETECTOR': 'IM',  # Detectors
                'CONTROL': 'IM',  # Control functions
                'MEASUREMENT': 'IM',  # Measurement
                'CONTROL_LOOP': 'IM',  # Control loops
            }
            prefix = prefix_map.get(category, 'IN')
        else:
            prefix = 'PX'  # Unknown

        # Generate placeholder with class name hash
        hash_suffix = str(abs(hash(class_name)) % 1000).zfill(3)
        return f"{prefix}{hash_suffix}Z"  # Z suffix indicates placeholder


class NozzleDefaults:
    """Determine nozzle defaults for equipment."""

    DEFAULT_COUNTS = {
        'Pump': 2,
        'CentrifugalPump': 2,
        'ReciprocatingPump': 2,
        'Tank': 4,
        'Vessel': 4,
        'HeatExchanger': 4,
        'Separator': 3,
        'Mixer': 3,
        'ProcessColumn': 6,
        'Centrifuge': 2,
        'Filter': 2,
        'Compressor': 2,
        'Turbine': 2,
    }

    @classmethod
    def get_nozzle_count(cls, class_name: str, category: str) -> int:
        """Determine default nozzle count."""
        # Check specific mappings
        if class_name in cls.DEFAULT_COUNTS:
            return cls.DEFAULT_COUNTS[class_name]

        # Category-based defaults
        if category == 'ROTATING':
            return 2  # Inlet/outlet
        elif category == 'STORAGE':
            return 4  # Multiple connections
        elif category == 'HEAT_TRANSFER':
            return 4  # Hot/cold in/out
        elif category == 'SEPARATION':
            return 3  # Feed, overhead, bottoms
        elif category == 'REACTION':
            return 4  # Multiple feeds/products
        else:
            return 2  # Default


def generate_registration_data():
    """Generate complete registration data for all equipment."""
    introspector = DexpiIntrospector()
    symbol_mapper = SymbolMapper()

    equipment_classes = introspector.get_available_types()['equipment']

    registrations = []

    for class_name in sorted(equipment_classes):
        # Generate alias
        sfiles_alias, is_primary = SFILESAliasGenerator.generate_alias(class_name)

        # Determine category
        category = EquipmentCategorizer.categorize(class_name)

        # Map symbol
        symbol_id = symbol_mapper.map_symbol(class_name, category)

        # Get nozzle defaults
        nozzle_count = NozzleDefaults.get_nozzle_count(class_name, category)

        # Get family (if any)
        family = SFILESAliasGenerator.get_family(class_name)

        # Display name
        display_name = re.sub('([A-Z])', r' \1', class_name).strip()

        registrations.append({
            'class_name': class_name,
            'sfiles_alias': sfiles_alias,
            'is_primary': is_primary,
            'family': family or '',
            'category': category,
            'symbol_id': symbol_id,
            'nozzle_count': nozzle_count,
            'display_name': display_name,
        })

    return registrations


def write_csv(registrations: List[Dict], output_path: Path):
    """Write registrations to CSV file."""
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'class_name', 'sfiles_alias', 'is_primary', 'family', 'category',
            'symbol_id', 'nozzle_count', 'display_name'
        ])
        writer.writeheader()
        writer.writerows(registrations)

    print(f"✓ CSV written to {output_path}")


def write_python_code(registrations: List[Dict], output_path: Path):
    """Generate Python registration code."""

    lines = [
        '"""Auto-generated equipment registrations.',
        'Generated by scripts/generate_equipment_registrations.py',
        '"""',
        '',
        '# Import all equipment classes from pyDEXPI',
        'from pydexpi.dexpi_classes.equipment import (',
    ]

    # Add imports (sorted alphabetically)
    class_names = sorted(set(r['class_name'] for r in registrations))
    for i, class_name in enumerate(class_names):
        comma = ',' if i < len(class_names) - 1 else ''
        lines.append(f'    {class_name}{comma}')

    lines.extend([
        ')',
        '',
        '# Equipment definitions',
        'def register_all_equipment(registry):',
        '    """Register all 159 equipment types."""',
        '',
    ])

    # Group by family for better organization
    families = {}
    no_family = []

    for reg in registrations:
        if reg['family']:
            if reg['family'] not in families:
                families[reg['family']] = []
            families[reg['family']].append(reg)
        else:
            no_family.append(reg)

    # Write family groups
    for family, members in sorted(families.items()):
        lines.append(f'    # {family.upper()} family')
        for reg in members:
            lines.append(f"    registry._register(EquipmentDefinition(")
            lines.append(f"        sfiles_type='{reg['sfiles_alias']}',")
            lines.append(f"        dexpi_class={reg['class_name']},")
            if reg['is_primary']:
                lines.append(f"        # PRIMARY for {family}")
            lines.append(f"        category=EquipmentCategory.{reg['category']},")
            lines.append(f"        display_name='{reg['display_name']}',")
            lines.append(f"        symbol_id='{reg['symbol_id']}',")
            lines.append(f"        nozzle_count_default={reg['nozzle_count']}")
            lines.append(f"    ))")
        lines.append('')

    # Write standalone equipment
    if no_family:
        lines.append('    # Standalone equipment')
        for reg in no_family:
            lines.append(f"    registry._register(EquipmentDefinition(")
            lines.append(f"        sfiles_type='{reg['sfiles_alias']}',")
            lines.append(f"        dexpi_class={reg['class_name']},")
            lines.append(f"        category=EquipmentCategory.{reg['category']},")
            lines.append(f"        display_name='{reg['display_name']}',")
            lines.append(f"        symbol_id='{reg['symbol_id']}',")
            lines.append(f"        nozzle_count_default={reg['nozzle_count']}")
            lines.append(f"    ))")

    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))

    print(f"✓ Python code written to {output_path}")


def print_summary(registrations: List[Dict]):
    """Print summary statistics."""
    print("\n" + "="*60)
    print("EQUIPMENT REGISTRATION SUMMARY")
    print("="*60)

    print(f"\nTotal equipment classes: {len(registrations)}")

    # Count by category
    categories = {}
    for reg in registrations:
        cat = reg['category']
        categories[cat] = categories.get(cat, 0) + 1

    print("\nBy category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")

    # Count families
    families = {}
    for reg in registrations:
        if reg['family']:
            families[reg['family']] = families.get(reg['family'], 0) + 1

    print(f"\n1:Many families defined: {len(families)}")
    print("Top families by size:")
    for family, count in sorted(families.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {family}: {count} variants")

    # Count symbols
    real_symbols = sum(1 for r in registrations if not r['symbol_id'].endswith('Z'))
    placeholders = len(registrations) - real_symbols

    print(f"\nSymbol mapping:")
    print(f"  Real symbols: {real_symbols}")
    print(f"  Placeholders: {placeholders}")
    print(f"  Coverage: {real_symbols / len(registrations) * 100:.1f}%")


if __name__ == '__main__':
    print("Generating equipment registration data...")
    print("="*60)

    # Generate data
    registrations = generate_registration_data()

    # Output files
    output_dir = Path(__file__).parent.parent / 'docs' / 'generated'
    output_dir.mkdir(exist_ok=True)

    csv_path = output_dir / 'equipment_registrations.csv'
    py_path = output_dir / 'equipment_registrations.py'

    # Write outputs
    write_csv(registrations, csv_path)
    write_python_code(registrations, py_path)

    # Print summary
    print_summary(registrations)

    print("\n" + "="*60)
    print("✓ Generation complete!")
    print("="*60)
    print(f"\nNext steps:")
    print(f"1. Review generated files:")
    print(f"   - {csv_path}")
    print(f"   - {py_path}")
    print(f"2. Validate SFILES aliases and categories")
    print(f"3. Update symbol mappings for placeholders")
    print(f"4. Integrate into src/core/equipment.py")
