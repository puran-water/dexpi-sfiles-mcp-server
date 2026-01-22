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
#
# Note: These handlers work directly with the Flowsheet object passed by
# TransactionManager. The flowsheet is already in the working state and handlers
# should modify it in-place using Flowsheet_Class APIs directly.
# ============================================================================

async def add_unit_handler(model: Any, params: Dict[str, Any]) -> OperationResult:
    """
    Handler for add_unit operation.

    Works directly with Flowsheet object using Flowsheet_Class APIs.
    """
    unit_type = params.get("unit_type")
    unit_name = params.get("unit_name")
    sequence_number = params.get("sequence_number")
    parameters = params.get("parameters", {})

    try:
        # Use Flowsheet's add_unit method directly
        # The unit_name will be auto-generated if not provided
        if unit_name:
            # Add node with explicit name
            model.state.add_node(unit_name, unit_type=unit_type, **parameters)
            actual_unit_name = unit_name
        else:
            # Let flowsheet generate semantic ID based on unit_type
            # For BFD/PFD, this would use the process hierarchy
            if hasattr(model, 'type') and model.type == "BFD":
                # BFD mode: use semantic IDs
                from ...utils.process_resolver import resolve_process_type
                process_info = resolve_process_type(unit_type, allow_custom=params.get("allow_custom", False))

                if process_info:
                    # Generate semantic ID
                    semantic_id = f"{process_info['process_class']}.{process_info['name']}"
                    if sequence_number:
                        semantic_id = f"{semantic_id}.{sequence_number}"
                    model.state.add_node(semantic_id, unit_type=unit_type, **parameters)
                    actual_unit_name = semantic_id
                else:
                    # Fallback to simple naming
                    actual_unit_name = f"{unit_type}_{len(model.state.nodes) + 1}"
                    model.state.add_node(actual_unit_name, unit_type=unit_type, **parameters)
            else:
                # PFD mode: simple equipment names
                actual_unit_name = unit_name or f"{unit_type}_{len(model.state.nodes) + 1}"
                model.state.add_node(actual_unit_name, unit_type=unit_type, **parameters)

        return OperationResult(
            success=True,
            message=f"Unit {actual_unit_name} ({unit_type}) added",
            data={"name": actual_unit_name, "type": unit_type}
        )
    except Exception as e:
        return OperationResult(
            success=False,
            message=f"Failed to add unit: {str(e)}"
        )


async def add_stream_handler(model: Any, params: Dict[str, Any]) -> OperationResult:
    """
    Handler for add_stream operation.

    Works directly with Flowsheet object using Flowsheet_Class APIs.
    """
    from_unit = params.get("from_unit")
    to_unit = params.get("to_unit")
    stream_name = params.get("stream_name", f"{from_unit}_to_{to_unit}")
    tags = params.get("tags", {"he": [], "col": []})
    properties = params.get("properties", {})

    try:
        # Verify units exist
        if from_unit not in model.state.nodes:
            return OperationResult(
                success=False,
                message=f"Source unit {from_unit} not found in flowsheet"
            )

        if to_unit not in model.state.nodes:
            return OperationResult(
                success=False,
                message=f"Target unit {to_unit} not found in flowsheet"
            )

        # Add stream using Flowsheet's add_stream method
        model.add_stream(
            node1=from_unit,
            node2=to_unit,
            tags=tags,
            stream_name=stream_name,
            **properties
        )

        return OperationResult(
            success=True,
            message=f"Stream {stream_name} added from {from_unit} to {to_unit}",
            data={
                "name": stream_name,
                "from": from_unit,
                "to": to_unit
            }
        )
    except Exception as e:
        return OperationResult(
            success=False,
            message=f"Failed to add stream: {str(e)}"
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
