"""
Frozen Legacy Equipment Creation Logic for Baseline Comparison

This module contains exact copies of legacy equipment creation logic
from BEFORE Phase 1 migration. These frozen implementations are used
to capture baseline fixtures for equivalence testing.

DO NOT MODIFY THIS FILE - It represents the "before" state.

Usage:
    from tests.fixtures.legacy_equipment import legacy_create_equipment

    # Capture baseline behavior
    equipment = legacy_create_equipment("Tank", "TK-101")
    # Compare against new core layer
"""

from pydexpi.dexpi_classes.equipment import (
    Tank, Pump, Compressor, HeatExchanger,
    Equipment, Nozzle
)
from pydexpi.dexpi_classes.piping import PipingNode


def legacy_create_equipment(equipment_type: str, tag_name: str, specs: dict = None, nozzle_configs: list = None):
    """
    Frozen copy of dexpi_tools._add_equipment equipment creation logic.

    Original source: src/tools/dexpi_tools.py lines 383-445 (before migration)

    Args:
        equipment_type: Type of equipment (Tank, Pump, etc.)
        tag_name: Equipment tag name
        specs: Equipment specifications
        nozzle_configs: Nozzle configurations

    Returns:
        Equipment instance with nozzles
    """
    if specs is None:
        specs = {}
    if nozzle_configs is None:
        nozzle_configs = []

    # Create equipment based on type (lines 383-414)
    if equipment_type == "Tank":
        equipment = Tank(tagName=tag_name, **specs)
    elif equipment_type == "Pump":
        equipment = Pump(tagName=tag_name, **specs)
    elif equipment_type == "Compressor":
        equipment = Compressor(tagName=tag_name, **specs)
    elif equipment_type == "HeatExchanger":
        equipment = HeatExchanger(tagName=tag_name, **specs)
    else:
        # Try to get the class dynamically from the introspector
        try:
            from pydexpi.dexpi_classes import equipment as eq_module
            equipment_class = getattr(eq_module, equipment_type, None)
            if equipment_class is None:
                raise ValueError(
                    f"Invalid equipment type '{equipment_type}'. "
                    f"Class not found in pydexpi.dexpi_classes.equipment. "
                    f"Use schema_query(operation='list_classes', schema_type='dexpi', category='equipment') "
                    f"to see available equipment types."
                )
            equipment = equipment_class(tagName=tag_name, **specs)
        except ImportError as e:
            raise ImportError(
                f"Failed to import pydexpi equipment module. "
                f"Ensure pydexpi is installed correctly. Original error: {e}"
            ) from e
        except AttributeError as e:
            raise AttributeError(
                f"Failed to instantiate equipment type '{equipment_type}'. "
                f"Check that the class constructor accepts tagName and specifications. "
                f"Original error: {e}"
            ) from e

    # Always create nozzles for equipment (lines 417-445)
    if not nozzle_configs:
        # Default nozzles if none specified
        nozzle_configs = [
            {"subTagName": "N1", "nominalPressure": "PN16", "nominalDiameter": "DN50"},
            {"subTagName": "N2", "nominalPressure": "PN16", "nominalDiameter": "DN50"}
        ]

    # Create nozzles
    nozzles = []
    for idx, nozzle_config in enumerate(nozzle_configs):
        nozzle = Nozzle(
            id=f"nozzle_{idx}_{tag_name}",
            subTagName=nozzle_config.get("subTagName", f"N{idx+1}"),
            nominalPressureRepresentation=nozzle_config.get("nominalPressure", "PN16"),
            nominalPressureNumericalValueRepresentation=nozzle_config.get("nominalPressure", "16").replace("PN", "")
        )

        # Add piping node to nozzle if diameter specified
        if "nominalDiameter" in nozzle_config:
            node = PipingNode(
                nominalDiameterRepresentation=nozzle_config["nominalDiameter"],
                nominalDiameterNumericalValueRepresentation=nozzle_config["nominalDiameter"].replace("DN", "")
            )
            nozzle.nodes = [node]

        nozzles.append(nozzle)

    # Assign nozzles to equipment
    equipment.nozzles = nozzles

    return equipment


def legacy_sfiles_to_dexpi_partial(flowsheet):
    """
    Frozen copy of key logic from SfilesDexpiMapper.sfiles_to_dexpi.

    Original source: src/converters/sfiles_dexpi_mapper.py lines 71-177

    NOTE: This is a simplified version that captures the equipment creation
    pattern. Full SFILES parsing is delegated to the core layer.

    Args:
        flowsheet: SFILES flowsheet object

    Returns:
        Equipment creation pattern for comparison
    """
    from pydexpi.dexpi_classes.model import DexpiModel, ConceptualModel
    from pydexpi.dexpi_classes.piping import PipingNetworkSystem

    # Create new DEXPI model (lines 81-85)
    model = DexpiModel()
    model.conceptualModel = ConceptualModel()
    model.conceptualModel.taggedPlantItems = []
    model.conceptualModel.pipingNetworkSystems = []
    model.conceptualModel.processInstrumentationFunctions = []

    # Track equipment for connection mapping (line 88)
    equipment_map = {}

    # Create piping system (lines 121-125)
    piping_system = PipingNetworkSystem(
        id="main_piping_system",
        segments=[]
    )
    model.conceptualModel.pipingNetworkSystems.append(piping_system)

    return model, equipment_map


def get_legacy_equipment_specs():
    """
    Return specifications for capturing baseline fixtures.

    Returns:
        List of (equipment_type, tag, specs, nozzles) tuples for testing
    """
    return [
        # Basic equipment
        ("Tank", "TK-101", {}, None),
        ("Pump", "P-201", {}, None),
        ("Compressor", "C-301", {}, None),
        ("HeatExchanger", "HE-401", {}, None),

        # Additional pyDEXPI types
        ("CentrifugalPump", "P-202", {}, None),
        ("ReciprocatingPump", "P-203", {}, None),
        ("Vessel", "V-501", {}, None),
        ("PressureVessel", "V-502", {}, None),

        # Custom nozzle configs
        ("Tank", "TK-102", {}, [
            {"subTagName": "INLET", "nominalPressure": "PN25", "nominalDiameter": "DN100"},
            {"subTagName": "OUTLET", "nominalPressure": "PN25", "nominalDiameter": "DN80"}
        ]),
    ]
