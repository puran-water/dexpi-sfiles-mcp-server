"""
SFILES operation registrations.

Registers core SFILES operations with typed descriptors and metadata.
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

async def add_unit_handler(model: Any, params: Dict[str, Any]) -> OperationResult:
    """
    Handler for add_unit operation.

    Note: This is a placeholder that will be connected to actual
    SfilesTools._add_unit implementation.
    """
    # TODO: Import and call SfilesTools._add_unit
    return OperationResult(
        success=True,
        message=f"Unit {params.get('unit_name')} added",
        data={"name": params.get("unit_name"), "type": params.get("unit_type")}
    )


async def add_stream_handler(model: Any, params: Dict[str, Any]) -> OperationResult:
    """
    Handler for add_stream operation.

    Note: This is a placeholder that will be connected to actual
    SfilesTools._add_stream implementation.
    """
    # TODO: Import and call SfilesTools._add_stream
    return OperationResult(
        success=True,
        message=f"Stream {params.get('stream_name')} added",
        data={
            "name": params.get("stream_name"),
            "from": params.get("from_unit"),
            "to": params.get("to_unit")
        }
    )


# ============================================================================
# Operation Descriptors
# ============================================================================

SFILES_ADD_UNIT = OperationDescriptor(
    name="sfiles_add_unit",
    version="1.0.0",
    category=OperationCategory.SFILES,
    description="Add process unit to SFILES flowsheet",
    input_schema={
        "type": "object",
        "properties": {
            "unit_type": {"type": "string"},
            "unit_name": {"type": "string"},
            "sequence_number": {"type": "integer"},
            "parameters": {"type": "object"}
        },
        "required": ["unit_type"]
    },
    handler=add_unit_handler,
    metadata=OperationMetadata(
        introduced="1.0.0",
        tags=["sfiles", "unit", "creation"],
        diff_metadata=DiffMetadata(
            tracks_additions=True,
            tracks_removals=False,
            tracks_modifications=False,
            affected_types=["Unit", "Node"]
        )
    )
)

SFILES_ADD_STREAM = OperationDescriptor(
    name="sfiles_add_stream",
    version="1.0.0",
    category=OperationCategory.SFILES,
    description="Add stream connecting two units in SFILES flowsheet",
    input_schema={
        "type": "object",
        "properties": {
            "from_unit": {"type": "string"},
            "to_unit": {"type": "string"},
            "stream_name": {"type": "string"},
            "properties": {"type": "object"}
        },
        "required": ["from_unit", "to_unit"]
    },
    handler=add_stream_handler,
    metadata=OperationMetadata(
        introduced="1.0.0",
        tags=["sfiles", "stream", "connection"],
        diff_metadata=DiffMetadata(
            tracks_additions=True,  # Adds edge
            tracks_removals=False,
            tracks_modifications=False,
            affected_types=["Stream", "Edge"]
        )
    )
)


# ============================================================================
# Registration Function
# ============================================================================

def register_sfiles_operations():
    """Register all SFILES operations with the registry."""
    registry = get_operation_registry()

    operations = [
        SFILES_ADD_UNIT,
        SFILES_ADD_STREAM,
    ]

    for operation in operations:
        try:
            registry.register(operation)
            logger.info(f"Registered SFILES operation: {operation.name}")
        except Exception as e:
            logger.warning(f"Failed to register {operation.name}: {e}")

    logger.info(f"Registered {len(operations)} SFILES operations")
