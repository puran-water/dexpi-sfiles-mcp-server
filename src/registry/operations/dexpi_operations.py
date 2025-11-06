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

async def add_equipment_handler(model: Any, params: Dict[str, Any]) -> OperationResult:
    """
    Handler for add_equipment operation.

    Note: This is a placeholder that will be connected to actual
    DexpiTools._add_equipment implementation.
    """
    # TODO: Import and call DexpiTools._add_equipment
    return OperationResult(
        success=True,
        message=f"Equipment {params.get('tag_name')} added",
        data={"tag": params.get("tag_name"), "type": params.get("equipment_type")}
    )


async def add_valve_handler(model: Any, params: Dict[str, Any]) -> OperationResult:
    """
    Handler for add_valve_between_components operation.

    Note: This is a placeholder that will be connected to actual
    DexpiTools._add_valve_between_components implementation.
    """
    # TODO: Import and call DexpiTools._add_valve_between_components
    return OperationResult(
        success=True,
        message=f"Valve {params.get('valve_tag')} added",
        data={"tag": params.get("valve_tag")}
    )


async def connect_components_handler(model: Any, params: Dict[str, Any]) -> OperationResult:
    """
    Handler for connect_components operation.

    Note: This is a placeholder that will be connected to actual
    DexpiTools._connect_components implementation.
    """
    # TODO: Import and call DexpiTools._connect_components
    return OperationResult(
        success=True,
        message=f"Connected {params.get('from_component')} to {params.get('to_component')}",
        data={
            "from": params.get("from_component"),
            "to": params.get("to_component"),
            "line": params.get("line_number")
        }
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
