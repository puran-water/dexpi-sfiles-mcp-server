"""
Template operation registrations (STRATEGIC category).

Registers parametric template instantiation operations for DEXPI and SFILES.
"""

import logging
from typing import Any, Dict
from pathlib import Path

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
# Operation Handlers
# ============================================================================

async def template_instantiate_dexpi_handler(model: Any, params: Dict[str, Any]) -> OperationResult:
    """
    Handler for DEXPI template instantiation.

    Works with DexpiModel objects and ParametricTemplate.
    """
    from ...templates import ParametricTemplate

    template_path = params.get("template_path")
    template_params = params.get("parameters", {})

    try:
        # Load template
        template = ParametricTemplate.from_yaml(Path(template_path))

        # Instantiate into model
        result = template.instantiate(
            target_model=model,
            parameters=template_params,
            model_type="dexpi"
        )

        return OperationResult(
            success=result.success,
            message=result.message,
            data={
                "template": template.name,
                "version": template.version,
                "components": result.instantiated_components,
                "validation_errors": result.validation_errors
            }
        )

    except Exception as e:
        return OperationResult(
            success=False,
            message=f"Template instantiation failed: {str(e)}"
        )


async def template_instantiate_sfiles_handler(model: Any, params: Dict[str, Any]) -> OperationResult:
    """
    Handler for SFILES template instantiation.

    Works with Flowsheet objects and ParametricTemplate.
    """
    from ...templates import ParametricTemplate

    template_path = params.get("template_path")
    template_params = params.get("parameters", {})

    try:
        # Load template
        template = ParametricTemplate.from_yaml(Path(template_path))

        # Instantiate into flowsheet
        result = template.instantiate(
            target_model=model,
            parameters=template_params,
            model_type="sfiles"
        )

        return OperationResult(
            success=result.success,
            message=result.message,
            data={
                "template": template.name,
                "version": template.version,
                "components": result.instantiated_components,
                "validation_errors": result.validation_errors
            }
        )

    except Exception as e:
        return OperationResult(
            success=False,
            message=f"Template instantiation failed: {str(e)}"
        )


# ============================================================================
# Operation Descriptors
# ============================================================================

TEMPLATE_INSTANTIATE_DEXPI = OperationDescriptor(
    name="template_instantiate_dexpi",
    version="1.0.0",
    category=OperationCategory.STRATEGIC,
    description="Instantiate parametric template into DEXPI P&ID model",
    input_schema={
        "type": "object",
        "properties": {
            "template_path": {
                "type": "string",
                "description": "Path to YAML template file"
            },
            "parameters": {
                "type": "object",
                "description": "Template parameters (validated against template schema)"
            }
        },
        "required": ["template_path", "parameters"]
    },
    handler=template_instantiate_dexpi_handler,
    metadata=OperationMetadata(
        introduced="1.0.0",
        tags=["template", "dexpi", "strategic", "pattern"],
        diff_metadata=DiffMetadata(
            tracks_additions=True,
            tracks_removals=False,
            tracks_modifications=False,
            affected_types=["Equipment", "Valve", "Instrumentation", "Pattern"]
        )
    )
)

TEMPLATE_INSTANTIATE_SFILES = OperationDescriptor(
    name="template_instantiate_sfiles",
    version="1.0.0",
    category=OperationCategory.STRATEGIC,
    description="Instantiate parametric template into SFILES flowsheet",
    input_schema={
        "type": "object",
        "properties": {
            "template_path": {
                "type": "string",
                "description": "Path to YAML template file"
            },
            "parameters": {
                "type": "object",
                "description": "Template parameters (validated against template schema)"
            }
        },
        "required": ["template_path", "parameters"]
    },
    handler=template_instantiate_sfiles_handler,
    metadata=OperationMetadata(
        introduced="1.0.0",
        tags=["template", "sfiles", "strategic", "pattern", "heat_integration"],
        diff_metadata=DiffMetadata(
            tracks_additions=True,
            tracks_removals=False,
            tracks_modifications=False,
            affected_types=["Unit", "Stream", "HeatIntegrationNode"]
        )
    )
)


# ============================================================================
# Registration Function
# ============================================================================

def register_template_operations():
    """Register all template operations with the registry."""
    registry = get_operation_registry()

    operations = [
        TEMPLATE_INSTANTIATE_DEXPI,
        TEMPLATE_INSTANTIATE_SFILES,
    ]

    for operation in operations:
        try:
            registry.register(operation)
            logger.info(f"Registered template operation: {operation.name}")
        except Exception as e:
            logger.warning(f"Failed to register {operation.name}: {e}")

    logger.info(f"Registered {len(operations)} template operations (STRATEGIC)")
