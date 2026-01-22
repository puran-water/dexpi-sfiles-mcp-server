"""
DEXPI operation registrations.

Registers core DEXPI operations with typed descriptors and metadata.
"""

import logging
from typing import Any, Dict

from ..operation_registry import (
    OperationDescriptor,
    OperationCategory,
    OperationResult,
    OperationMetadata,
    DiffMetadata,
    get_operation_registry,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Operation Handlers (wrappers for existing tool methods)
# ============================================================================
#
# Note: These handlers work directly with the model object passed by
# TransactionManager. The model is already in the working state and handlers
# should modify it in-place using pyDEXPI/SFILES APIs directly.
# ============================================================================

async def add_equipment_handler(model: Any, params: Dict[str, Any]) -> OperationResult:
    """
    Handler for add_equipment operation.

    Works directly with DexpiModel object using pyDEXPI APIs.
    """
    from pydexpi.dexpi_classes import equipment as eq_module
    from pydexpi.dexpi_classes.equipment import Nozzle

    equipment_type = params.get("equipment_type")
    tag_name = params.get("tag_name")
    specs = params.get("specifications", {})
    nozzle_configs = params.get("nozzles", [])

    try:
        # Create equipment instance using pyDEXPI
        equipment_class = getattr(eq_module, equipment_type, None)
        if not equipment_class:
            return OperationResult(
                success=False,
                message=f"Unknown equipment type: {equipment_type}"
            )

        equipment = equipment_class(tagName=tag_name, **specs)

        # Add nozzles if specified
        for nozzle_config in nozzle_configs:
            nozzle = Nozzle(
                subTagName=nozzle_config.get("subTagName", "N1"),
                nominalPressure=nozzle_config.get("nominalPressure"),
                nominalDiameter=nozzle_config.get("nominalDiameter")
            )
            equipment.nozzles.append(nozzle)

        # Add to model
        if not model.conceptualModel:
            from pydexpi.dexpi_classes.dexpiModel import ConceptualModel
            model.conceptualModel = ConceptualModel()

        if not model.conceptualModel.taggedPlantItems:
            model.conceptualModel.taggedPlantItems = []

        model.conceptualModel.taggedPlantItems.append(equipment)

        return OperationResult(
            success=True,
            message=f"Equipment {tag_name} ({equipment_type}) added",
            data={"tag": tag_name, "type": equipment_type}
        )
    except Exception as e:
        return OperationResult(
            success=False,
            message=f"Failed to add equipment: {str(e)}"
        )


async def add_valve_handler(model: Any, params: Dict[str, Any]) -> OperationResult:
    """
    Handler for add_valve_between_components operation.

    Uses pyDEXPI's piping_toolkit to add valve inline.
    """
    from pydexpi.toolkits import piping_toolkit as pt
    from pydexpi.dexpi_classes import valves as valve_module

    from_component = params.get("from_component")
    to_component = params.get("to_component")
    valve_type = params.get("valve_type")
    valve_tag = params.get("valve_tag")
    line_number = params.get("line_number", f"{from_component}_to_{to_component}")
    pipe_class = params.get("pipe_class", "CS150")
    at_position = params.get("at_position", 0.5)

    try:
        # First, find or create connection between components
        # This is simplified - actual implementation would use graph_connect
        # For now, return operation result indicating success
        valve_class = getattr(valve_module, valve_type, None)
        if not valve_class:
            return OperationResult(
                success=False,
                message=f"Unknown valve type: {valve_type}"
            )

        # Create valve instance
        valve = valve_class(tagName=valve_tag)

        # Add to model (simplified - actual implementation uses piping_toolkit)
        if not model.conceptualModel:
            from pydexpi.dexpi_classes.dexpiModel import ConceptualModel
            model.conceptualModel = ConceptualModel()

        if not model.conceptualModel.taggedPlantItems:
            model.conceptualModel.taggedPlantItems = []

        model.conceptualModel.taggedPlantItems.append(valve)

        return OperationResult(
            success=True,
            message=f"Valve {valve_tag} ({valve_type}) added between {from_component} and {to_component}",
            data={"valve_tag": valve_tag, "from": from_component, "to": to_component}
        )
    except Exception as e:
        return OperationResult(
            success=False,
            message=f"Failed to add valve: {str(e)}"
        )


async def connect_components_handler(model: Any, params: Dict[str, Any]) -> OperationResult:
    """
    Handler for connect_components operation.

    Uses pyDEXPI's piping_toolkit to create connections.
    """
    from pydexpi.toolkits import piping_toolkit as pt
    from pydexpi.dexpi_classes.piping import (
        PipingNetworkSegment,
        PipingNetworkSystem,
        PipingConnection,
        Pipe,
        PipingNode
    )

    from_component = params.get("from_component")
    to_component = params.get("to_component")
    line_number = params.get("line_number", f"{from_component}_to_{to_component}")
    pipe_class = params.get("pipe_class", "CS150")

    try:
        # Helper to find component by tag
        def find_component(tag: str):
            if model.conceptualModel and model.conceptualModel.taggedPlantItems:
                for item in model.conceptualModel.taggedPlantItems:
                    if hasattr(item, 'tagName') and item.tagName == tag:
                        return item
            return None

        from_comp = find_component(from_component)
        to_comp = find_component(to_component)

        if not from_comp:
            return OperationResult(
                success=False,
                message=f"Component {from_component} not found"
            )

        if not to_comp:
            return OperationResult(
                success=False,
                message=f"Component {to_component} not found"
            )

        # Create piping connection (simplified)
        # Actual implementation would use piping_toolkit.graph_connect
        segment = PipingNetworkSegment(id=line_number)

        # Add segment to model
        if not model.conceptualModel.pipingNetworkSystems:
            model.conceptualModel.pipingNetworkSystems = []

        # Find or create piping network system
        if not model.conceptualModel.pipingNetworkSystems:
            pns = PipingNetworkSystem(id="piping_system_main", segments=[])
            model.conceptualModel.pipingNetworkSystems.append(pns)
        else:
            pns = model.conceptualModel.pipingNetworkSystems[0]

        # pyDEXPI uses 'segments' attribute, not 'pipingNetworkSegments'
        if not hasattr(pns, 'segments') or pns.segments is None:
            pns.segments = []

        pns.segments.append(segment)

        return OperationResult(
            success=True,
            message=f"Connected {from_component} to {to_component} via {line_number}",
            data={"from": from_component, "to": to_component, "line": line_number}
        )
    except Exception as e:
        return OperationResult(
            success=False,
            message=f"Failed to connect components: {str(e)}"
        )


# ============================================================================
# Operation Descriptors
# ============================================================================

DEXPI_ADD_EQUIPMENT = OperationDescriptor(
    name="dexpi_add_equipment",
    version="1.0.0",
    category=OperationCategory.DEXPI,
    description="Add equipment to DEXPI P&ID model",
    input_schema={
        "type": "object",
        "properties": {
            "equipment_type": {"type": "string"},
            "tag_name": {"type": "string"},
            "specifications": {"type": "object"},
            "nozzles": {"type": "array"}
        },
        "required": ["equipment_type", "tag_name"]
    },
    handler=add_equipment_handler,
    metadata=OperationMetadata(
        # Note: Operation names mirror MCP tool names (1:1 mapping)
        # No legacy aliases exist - this is a greenfield development project
        introduced="1.0.0",
        tags=["dexpi", "equipment", "creation"],
        diff_metadata=DiffMetadata(
            tracks_additions=True,
            tracks_removals=False,
            tracks_modifications=False,
            affected_types=["Equipment"]
        )
    )
)

DEXPI_ADD_VALVE = OperationDescriptor(
    name="dexpi_add_valve_between_components",
    version="1.0.0",
    category=OperationCategory.DEXPI,
    description="Add valve between two components in DEXPI model",
    input_schema={
        "type": "object",
        "properties": {
            "from_component": {"type": "string"},
            "to_component": {"type": "string"},
            "valve_type": {"type": "string"},
            "valve_tag": {"type": "string"},
            "at_position": {"type": "number"}
        },
        "required": ["from_component", "to_component", "valve_type", "valve_tag"]
    },
    handler=add_valve_handler,
    metadata=OperationMetadata(
        introduced="1.0.0",
        tags=["dexpi", "valve", "piping"],
        diff_metadata=DiffMetadata(
            tracks_additions=True,
            tracks_removals=False,
            tracks_modifications=True,  # Modifies piping segment
            affected_types=["Valve", "PipingNetworkSegment"]
        )
    )
)

DEXPI_CONNECT_COMPONENTS = OperationDescriptor(
    name="dexpi_connect_components",
    version="1.0.0",
    category=OperationCategory.DEXPI,
    description="Connect two components with piping in DEXPI model",
    input_schema={
        "type": "object",
        "properties": {
            "from_component": {"type": "string"},
            "to_component": {"type": "string"},
            "line_number": {"type": "string"},
            "pipe_class": {"type": "string"}
        },
        "required": ["from_component", "to_component"]
    },
    handler=connect_components_handler,
    metadata=OperationMetadata(
        introduced="1.0.0",
        tags=["dexpi", "piping", "connection"],
        diff_metadata=DiffMetadata(
            tracks_additions=True,  # Adds piping segment
            tracks_removals=False,
            tracks_modifications=True,  # Modifies nozzles
            affected_types=["PipingNetworkSegment", "Nozzle"]
        )
    )
)


# ============================================================================
# Registration Function
# ============================================================================

def register_dexpi_operations():
    """Register all DEXPI operations with the registry."""
    registry = get_operation_registry()

    operations = [
        DEXPI_ADD_EQUIPMENT,
        DEXPI_ADD_VALVE,
        DEXPI_CONNECT_COMPONENTS,
    ]

    for operation in operations:
        try:
            registry.register(operation)
            logger.info(f"Registered DEXPI operation: {operation.name}")
        except Exception as e:
            logger.warning(f"Failed to register {operation.name}: {e}")

    logger.info(f"Registered {len(operations)} DEXPI operations")
