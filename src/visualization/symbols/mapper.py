"""
DEXPI Class to NOAKADEXPI Symbol Mapper
Based on official Symbols.xlsm mappings
"""

from typing import Dict, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class SymbolMapping:
    """Symbol mapping entry."""
    symbol_id: str
    description: str
    grouping: str
    dexpi_class: Optional[str] = None
    variants: List[str] = None


class DexpiSymbolMapper:
    """
    Maps DEXPI classes to NOAKADEXPI symbols.
    Based on official mappings from Symbols.xlsm
    """

    # Official mappings from NOAKADEXPI Symbols.xlsm
    SYMBOL_MAPPINGS = {
        # Pumps (PP prefix)
        "CentrifugalPump": SymbolMapping("PP001A", "Pump Centrifugal", "Pump"),
        "DiaphragmPump": SymbolMapping("PP002A", "Pump Diaphragm", "Pump"),
        "GearPump": SymbolMapping("PP003A", "Pump Gear", "Pump"),
        "HandPump": SymbolMapping("PP004A", "Pump Hand", "Pump"),
        "SlidingVanePump": SymbolMapping("PP005A", "Pump Sliding Vane", "Pump"),
        "LiquidRingPump": SymbolMapping("PP006A", "Pump Liquid Ring", "Pump"),
        "ProportioningPump": SymbolMapping("PP008A", "Pump Proportioning", "Pump"),
        "TriplexPump": SymbolMapping("PP009A", "Pump Triplex", "Pump"),
        "ReciprocatingPump": SymbolMapping("PP010A", "Pump Reciprocating", "Pump"),
        "ScrewPump": SymbolMapping("PP014A", "Pump Screw", "ConnectedEquipment"),
        "LiftPump": SymbolMapping("PP015A", "Pump Lift", "ConnectedEquipment"),
        "SumpPump": SymbolMapping("PP016A", "Pump Sump", "ConnectedEquipment"),
        "SubmersiblePump": SymbolMapping("PE032A", "Pump Submerged Motor", "Pump"),

        # Alternative pump mappings
        "RotaryPump": SymbolMapping("PP003A", "Pump Gear", "Pump"),  # Use gear pump for rotary

        # Blowers/Compressors
        "Blower": SymbolMapping("PP007A", "Blower", "Equipment"),
        "CentrifugalBlower": SymbolMapping("PP007A", "Blower", "Equipment"),
        "RotaryBlower": SymbolMapping("PP007A", "Blower", "Equipment"),
        "CentrifugalCompressor": SymbolMapping("PP011A", "Compressor Centrifugal", "ConnectedEquipment"),
        "ScrewCompressor": SymbolMapping("PP012A", "Compressor Screw", "ConnectedEquipment"),

        # Valves (PV prefix) - Manual versions
        "GateValve": SymbolMapping("PV005A", "Valve Gate (Manual Valve)", "Valve"),
        "GlobeValve": SymbolMapping("PV007A", "Valve Globe (Manual Valve)", "Valve"),
        "ButterflyValve": SymbolMapping("PV018A", "Valve Butterfly (Manual Valve)", "Valve"),
        "BallValve": SymbolMapping("PV019A", "Valve Ball (Manual Valve)", "Valve"),
        "CheckValve": SymbolMapping("PV013A", "Valve Check", "Valve"),
        "PlugValve": SymbolMapping("PV023A", "Valve Plug (Manual Valve)", "Valve"),
        "NeedleValve": SymbolMapping("PV016A", "Valve Needle (Manual Valve)", "Valve"),
        "DiaphragmValve": SymbolMapping("PV015A", "Valve Diaphragm (Manual Valve)", "Valve"),
        "PinchValve": SymbolMapping("PV014A", "Valve Pinch (Manual Valve)", "Valve"),
        "ChokeValve": SymbolMapping("PV010A", "Valve Choke", "Valve"),
        "ThreeWayValve": SymbolMapping("PV003A", "Valve Three Way (Manual Valve)", "Valve"),
        "FourWayValve": SymbolMapping("PV004A", "Valve Four Way (Manual Valve)", "Valve"),

        # Actuated valve versions (B suffix)
        "OperatedGateValve": SymbolMapping("PV005B", "Valve Gate (Actuated Valve)", "Valve"),
        "OperatedGlobeValve": SymbolMapping("PV007B", "Valve Globe (Actuated Valve)", "Valve"),
        "OperatedButterflyValve": SymbolMapping("PV018B", "Valve Butterfly (Actuated Valve)", "Valve"),
        "OperatedBallValve": SymbolMapping("PV019B", "Valve Ball (Actuated Valve)", "Valve"),
        "OperatedValve": SymbolMapping("PV019B", "Valve Ball (Actuated Valve)", "Valve"),

        # Special valves
        "SafetyValveOrFitting": SymbolMapping("PV012A", "Valve Vacuum Release", "Valve"),
        "MinFlowCheckValve": SymbolMapping("PV009A", "Valve Min. Flow And Check", "Valve"),
        "FlowControlCheckValve": SymbolMapping("PV022A", "Flow Control Check Valve", "Valve"),

        # Tanks/Vessels (PT prefix)
        "Tank": SymbolMapping("PE025A", "Tank Atmospheric Storage", "Vessel"),
        "AtmosphericTank": SymbolMapping("PE025A", "Tank Atmospheric Storage", "Vessel"),
        "PressureVessel": SymbolMapping("PT002A", "Pressure Vessel", "Vessel"),
        "Tower": SymbolMapping("PT003A", "Tank Tower", "Vessel"),
        "QuickOpenLidTank": SymbolMapping("PT004A", "Tank Pressure Quick Open Lid", "Vessel"),
        "DomeRoofTank": SymbolMapping("PT005A", "Tank Dome Roof", "Vessel"),
        "Silo": SymbolMapping("PT006A", "Tank Cone Roof Silo", "Vessel"),
        "GasBottle": SymbolMapping("PT007A", "Tank Gas Bottle", "Vessel"),
        "ToteTank": SymbolMapping("PT008A", "Tank Tote", "Vessel"),
        "OpenPit": SymbolMapping("PT009A", "Tank Open Pit", "Vessel"),
        "Hopper": SymbolMapping("PT011A", "Tank Hopper", "Vessel"),

        # Heat Exchangers (PE prefix)
        "HeatExchanger": SymbolMapping("PE037A", "Exch. Shell and Fuced Tube", "Equipment"),
        "TubularHeatExchanger": SymbolMapping("PE037A", "Exch. Shell and Fuced Tube", "Equipment"),
        "ShellAndTubeHeatExchanger": SymbolMapping("PE038A", "Exch. Shell and Tube H$V", "Equipment"),
        "PlateHeatExchanger": SymbolMapping("PE010A", "Exch. Plate", "Equipment"),
        "CompactHeatExchanger": SymbolMapping("PE009A", "Exch. Compact Heat", "Equipment"),
        "FinHeatExchanger": SymbolMapping("PE011A", "Exch. Fin", "Equipment"),
        "AirCooledForced": SymbolMapping("PE028A", "Air Cooled Forced", "Equipment"),
        "AirCooledInduced": SymbolMapping("PE029A", "Air Cooled Induced", "Equipment"),
        "Reboiler": SymbolMapping("PE036A", "Reboiler", "Equipment"),

        # Mixers/Agitators (PP/PE prefix)
        "Agitator": SymbolMapping("PP017A", "Agitator", "Equipment"),
        "Mixer": SymbolMapping("PP017A", "Agitator", "Equipment"),
        "StaticMixer": SymbolMapping("PE003A", "Inline Mixer", "In-line component"),
        "InlineMixer": SymbolMapping("PE003A", "Inline Mixer", "In-line component"),

        # Filters (PF/PS prefix)
        "Filter": SymbolMapping("PS014A", "Strainer", "In-line component"),
        "LiquidFilter": SymbolMapping("PS014A", "Strainer", "In-line component"),
        "Strainer": SymbolMapping("PS014A", "Strainer", "In-line component"),
        "YStrainer": SymbolMapping("PS015A", "Strainer Y Type", "In-line component"),
        "TStrainer": SymbolMapping("PS016A", "Strainer T Type", "In-line component"),
        "DuplexStrainer": SymbolMapping("PS013A", "Strainer Duplex", "In-line component"),
        "BagFilter": SymbolMapping("PE023A", "Bag Filter", "Equipment"),

        # Separators/Centrifuges
        "Separator": SymbolMapping("PE012A", "Hydrocyclon", "equipment"),
        "Hydrocyclone": SymbolMapping("PE012A", "Hydrocyclon", "equipment"),
        "Centrifuge": SymbolMapping("PE030A", "Centrifuge", "Equipment"),
        "DrillingCentrifuge": SymbolMapping("PE014A", "Centrifuge Drilling", "Equipment"),

        # Other Equipment
        "Eductor": SymbolMapping("PE006A", "Eductor", "Equipment"),
        "Ejector": SymbolMapping("PE006B", "Ejector", "Equipment"),
        "Burner": SymbolMapping("PE026A", "Burner", "Equipment"),
        "Crusher": SymbolMapping("PE022A", "Crusher", "Equipment"),
        "ConveyorScrew": SymbolMapping("PE015A", "Conveyor Screw", "Equipment"),
        "WeighFeeder": SymbolMapping("PE019A", "Weigh Feeder", "ConnectedEquipment"),
        "ElectricMotor": SymbolMapping("PE018A", "Drive Electric Motor", "ConnectedEquipment"),
        "Turbine": SymbolMapping("PE021A", "Turbine Type by XX", "ConnectedEquipment"),

        # Piping Components (PE/PS prefix)
        "ConcentricReducer": SymbolMapping("PE001A", "Concentric Reducer", "In-line component"),
        "EccentricReducer": SymbolMapping("PE002A", "Eccentric Reducer", "In-line component"),
        "MixingTee": SymbolMapping("PE004A", "Mixing Or Barred Tee", "In-line component"),
        "UnionCoupling": SymbolMapping("PE005A", "Union Coupling", "In-line component"),
        "Flange": SymbolMapping("PV001A", "Flange", "In-line component"),
        "BlindFlange": SymbolMapping("PV002A", "Blind Flange", "In-line component"),
        "SpectacleBlind": SymbolMapping("PS001A", "Spectacle Blind NO", "In-line component"),
        "Spade": SymbolMapping("PS003A", "Spade", "In-line component"),
        "Spacer": SymbolMapping("PS004A", "Spacer", "In-line component"),
        "WeldedCap": SymbolMapping("PS005A", "Welded Cap", "In-line component"),
        "ScrewedCap": SymbolMapping("PS006A", "Screwed Cap", "In-line component"),

        # Instrumentation (Generic mapping for now)
        "ProcessSignalGeneratingSystem": SymbolMapping("IM005A", "Field Instrument", "Off-line Instrument"),
        "ProcessControlFunction": SymbolMapping("ND0006", "Function available on VDU", "Off-line Instrument"),
        "Transmitter": SymbolMapping("IM005A", "Field Instrument", "Off-line Instrument"),

        # Flow elements (PF prefix)
        "OrificePlate": SymbolMapping("PF015A", "Flow T. Orifice Plate", "In-Line Instrument"),
        "FlowElement": SymbolMapping("PF001A", "Flow T. Turbine", "In-Line Instrument"),
        "FlowDetector": SymbolMapping("PF002A", "Flow T. Vortex", "In-Line Instrument"),
    }

    # Alternative mappings for common variations
    ALTERNATIVE_MAPPINGS = {
        "Pump": "PP001A",  # Default to centrifugal
        "Valve": "PV019A",  # Default to ball valve
        "Vessel": "PT002A",  # Default to pressure vessel
        "Compressor": "PP011A",  # Default to centrifugal
        "CustomEquipment": "LZ009A",  # Special item
    }

    def __init__(self):
        """Initialize mapper."""
        self.mappings = self.SYMBOL_MAPPINGS
        self.alternatives = self.ALTERNATIVE_MAPPINGS

    def get_symbol_for_dexpi_class(self, dexpi_class: str) -> Optional[str]:
        """
        Get NOAKADEXPI symbol ID for DEXPI class.

        Args:
            dexpi_class: DEXPI class name

        Returns:
            Symbol ID or None
        """
        # Direct mapping
        if dexpi_class in self.mappings:
            return self.mappings[dexpi_class].symbol_id

        # Check alternatives
        if dexpi_class in self.alternatives:
            return self.alternatives[dexpi_class]

        # Try fuzzy match
        for key, mapping in self.mappings.items():
            if dexpi_class.lower() in key.lower():
                return mapping.symbol_id

        # Try base class
        for base in ["Pump", "Valve", "Tank", "Vessel", "Equipment"]:
            if base in dexpi_class:
                if base in self.alternatives:
                    return self.alternatives[base]

        logger.warning(f"No symbol mapping found for DEXPI class: {dexpi_class}")
        return None

    def get_symbol_info(self, symbol_id: str) -> Optional[SymbolMapping]:
        """
        Get symbol information.

        Args:
            symbol_id: NOAKADEXPI symbol ID

        Returns:
            SymbolMapping or None
        """
        for mapping in self.mappings.values():
            if mapping.symbol_id == symbol_id:
                return mapping
        return None

    def get_actuated_variant(self, symbol_id: str) -> Optional[str]:
        """
        Get actuated variant of valve symbol.

        Args:
            symbol_id: Base symbol ID

        Returns:
            Actuated variant ID or None
        """
        # Manual to actuated mapping
        actuated_map = {
            "PV003A": "PV003B",  # Three way
            "PV004A": "PV004B",  # Four way
            "PV005A": "PV005B",  # Gate
            "PV007A": "PV007B",  # Globe
            "PV008A": "PV008B",  # Float
            "PV014A": "PV014B",  # Pinch
            "PV015A": "PV015B",  # Diaphragm
            "PV016A": "PV016B",  # Needle
            "PV018A": "PV018B",  # Butterfly
            "PV019A": "PV019B",  # Ball
            "PV023A": "PV023B",  # Plug
        }

        return actuated_map.get(symbol_id)

    def list_categories(self) -> List[str]:
        """Get list of all categories."""
        categories = set()
        for mapping in self.mappings.values():
            categories.add(mapping.grouping)
        return sorted(list(categories))

    def get_symbols_by_category(self, category: str) -> List[SymbolMapping]:
        """Get all symbols in a category."""
        symbols = []
        for mapping in self.mappings.values():
            if mapping.grouping == category:
                symbols.append(mapping)
        return symbols

    def validate_mapping(self, dexpi_class: str, symbol_id: str) -> bool:
        """
        Validate if a symbol is appropriate for a DEXPI class.

        Args:
            dexpi_class: DEXPI class name
            symbol_id: Symbol ID to validate

        Returns:
            True if valid
        """
        expected = self.get_symbol_for_dexpi_class(dexpi_class)
        if expected == symbol_id:
            return True

        # Check if it's an actuated variant
        if expected and self.get_actuated_variant(expected) == symbol_id:
            return True

        # Check alternatives
        return False