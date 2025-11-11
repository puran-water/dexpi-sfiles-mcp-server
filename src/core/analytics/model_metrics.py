"""
Model metrics and analytics for DEXPI models.

Extracted from visualization/orchestrator/model_service.py to provide
shared analytics helpers for all layers (core, tools, visualization).
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Type alias for DEXPI models
DexpiModel = Any  # pydexpi.dexpi_classes.PlantModel


def extract_metadata(dexpi_model: DexpiModel) -> Dict[str, Any]:
    """
    Extract metadata from DEXPI model.

    Args:
        dexpi_model: pydexpi PlantModel instance

    Returns:
        Metadata dictionary with project info and element counts
    """
    metadata = {
        "project": None,
        "drawing_number": None,
        "revision": None,
        "equipment_count": 0,
        "piping_segments": 0,
        "instrumentation_count": 0,
        "valves_count": 0
    }

    try:
        conceptual = getattr(dexpi_model, 'conceptualModel', None)

        # Extract project metadata
        if hasattr(dexpi_model, 'originatingSystemName'):
            metadata["project"] = dexpi_model.originatingSystemName
        if hasattr(dexpi_model, 'originatingSystemVersion'):
            metadata["drawing_number"] = dexpi_model.originatingSystemVersion

        # Count equipment
        equipment = []
        if conceptual and getattr(conceptual, 'taggedPlantItems', None):
            equipment = conceptual.taggedPlantItems
            metadata["equipment_count"] = len(equipment)

        # Count piping segments
        if conceptual and getattr(conceptual, 'pipingNetworkSystems', None):
            segment_total = 0
            for system in conceptual.pipingNetworkSystems:
                segment_total += len(getattr(system, 'segments', []) or [])
            metadata["piping_segments"] = segment_total

        # Count instrumentation
        instrumentation = [
            item for item in equipment
            if "Instrumentation" in type(item).__name__ or "Signal" in type(item).__name__
        ]
        metadata["instrumentation_count"] = len(instrumentation)

        # Count valves
        valves = [
            item for item in equipment
            if "Valve" in type(item).__name__
        ]
        metadata["valves_count"] = len(valves)

    except Exception as e:
        logger.warning(f"Failed to extract some metadata: {e}")

    return metadata


def validate_model(dexpi_model: DexpiModel) -> Dict[str, Any]:
    """
    Validate DEXPI model for completeness and structural integrity.

    Args:
        dexpi_model: pydexpi PlantModel instance

    Returns:
        Validation results with warnings and errors
    """
    results = {
        "valid": True,
        "warnings": [],
        "errors": []
    }

    try:
        conceptual = getattr(dexpi_model, 'conceptualModel', None)

        # Check for plant information
        if not getattr(dexpi_model, 'PlantInformation', None):
            results["warnings"].append("Missing PlantInformation")

        # Check for equipment
        equipment = getattr(conceptual, 'taggedPlantItems', []) or []
        if not equipment:
            results["warnings"].append("No equipment defined")

        # Check piping connectivity
        piping_systems = getattr(conceptual, 'pipingNetworkSystems', []) or []
        unconnected = []
        for system in piping_systems:
            for segment in getattr(system, 'segments', []) or []:
                if not getattr(segment, 'sourceNode', None) or not getattr(segment, 'targetNode', None):
                    unconnected.append(getattr(segment, 'id', 'unknown'))

        if unconnected:
            results["warnings"].append(
                f"Unconnected piping segments: {unconnected[:5]}"
            )

        # Check for presentation data
        has_presentation = any(
            getattr(equip, 'Presentation', None) is not None for equip in equipment
        )
        if not has_presentation:
            results["warnings"].append(
                "No presentation data found (coordinates, symbols)"
            )

    except Exception as e:
        results["errors"].append(f"Validation error: {str(e)}")
        results["valid"] = False

    # Set overall validity based on errors
    if results["errors"]:
        results["valid"] = False

    return results


def calculate_complexity(dexpi_model: DexpiModel) -> Dict[str, Any]:
    """
    Calculate model complexity metrics.

    Args:
        dexpi_model: pydexpi PlantModel instance

    Returns:
        Complexity metrics dictionary
    """
    complexity = {
        "total_elements": 0,
        "connection_density": 0.0,
        "has_presentation": False,
        "has_instrumentation": False
    }

    try:
        conceptual = getattr(dexpi_model, 'conceptualModel', None)
        equipment = getattr(conceptual, 'taggedPlantItems', []) or []
        piping_systems = getattr(conceptual, 'pipingNetworkSystems', []) or []
        connection_count = sum(
            len(getattr(system, 'segments', []) or [])
            for system in piping_systems
        )

        complexity["total_elements"] = len(equipment) + connection_count
        complexity["connection_density"] = (
            connection_count / len(equipment) if equipment else 0.0
        )
        complexity["has_instrumentation"] = any(
            "Instrumentation" in type(item).__name__ or "Signal" in type(item).__name__
            for item in equipment
        )
        complexity["has_presentation"] = any(
            getattr(item, 'Presentation', None) is not None for item in equipment
        )

    except Exception as e:
        logger.warning(f"Failed to calculate complexity metrics: {e}")

    return complexity


def summarize(dexpi_model: DexpiModel) -> Dict[str, Any]:
    """
    Generate comprehensive model summary with metadata, validation, and complexity.

    This is the main entry point for getting all analytics about a DEXPI model.

    Args:
        dexpi_model: pydexpi PlantModel instance

    Returns:
        Complete statistics dictionary
    """
    return {
        "metadata": extract_metadata(dexpi_model),
        "validation": validate_model(dexpi_model),
        "complexity": calculate_complexity(dexpi_model)
    }
