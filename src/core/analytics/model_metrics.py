"""
Model metrics and analytics for DEXPI models.

Extracted from visualization/orchestrator/model_service.py to provide
shared analytics helpers for all layers (core, tools, visualization).
"""

from typing import Dict, Any, Optional, Set
import logging
from lxml import etree

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


def calculate_export_fidelity(
    component: Any,
    exported_element: etree._Element,
    threshold: float = 0.80,
    fail_below_threshold: bool = False
) -> Dict[str, Any]:
    """
    Calculate fidelity of exported attributes vs source data.

    Measures what percentage of populated pyDEXPI data attributes were successfully
    exported to Proteus GenericAttributes. Uses the same filtering and name
    transformation logic as GenericAttributeExporter to ensure accurate comparison.

    Args:
        component: pyDEXPI component with get_data_attributes() method
        exported_element: lxml Element containing GenericAttribute children
        threshold: Minimum acceptable fidelity ratio (default 0.80 = 80%)
        fail_below_threshold: Raise ValueError if fidelity < threshold

    Returns:
        Dictionary with keys:
            - component_type (str): Component class name
            - source_count (int): Number of non-empty source attributes
            - exported_count (int): Number of unique exported GenericAttribute Names
            - fidelity_percent (float): Preservation percentage (0-100)
            - missing_attributes (list[str]): Source attribute names not found in export
            - threshold (float): Threshold used for pass/fail determination
            - status (str): "PASS" if fidelity >= threshold, "FAIL" otherwise

    Raises:
        TypeError: Component does not have get_data_attributes() method
        ValueError: Component has zero populated data attributes (data quality issue)
        RuntimeError: Exported XML has zero GenericAttributes (exporter failure)
        ValueError: Fidelity below threshold (only if fail_below_threshold=True)

    Example:
        >>> result = calculate_export_fidelity(tank, tank_xml, threshold=0.80)
        >>> print(f"Fidelity: {result['fidelity_percent']:.1f}% - {result['status']}")
        Fidelity: 85.7% - PASS
    """
    # Import here to avoid circular dependency (analytics should not depend on exporters)
    try:
        from pydexpi.toolkits.base_model_utils import get_data_attributes
    except ImportError as e:
        raise ImportError(
            f"Cannot import get_data_attributes from pyDEXPI: {e}. "
            "Ensure pyDEXPI is installed and available."
        ) from e

    from src.exporters.attribute_utils import (
        normalize_attribute_name,
        is_empty_attribute_value
    )

    component_type = type(component).__name__

    # 1. Validate component type and get_data_attributes availability
    # Note: get_data_attributes is called ON the component, not as a method of it
    # The function is imported from pydexpi.toolkits.base_model_utils
    if not hasattr(component, '__class__') or not hasattr(component, 'id'):
        raise TypeError(
            f"Component must be a pyDEXPI object with id attribute, "
            f"got {type(component)}"
        )

    # 2. Get source attributes and filter out empty values
    try:
        source_attrs = get_data_attributes(component)
    except Exception as e:
        raise TypeError(
            f"Component {component_type} does not support get_data_attributes(): {e}"
        ) from e

    if not isinstance(source_attrs, dict):
        raise TypeError(
            f"get_data_attributes() must return dict, got {type(source_attrs)}"
        )

    # Filter to only non-empty values (matches exporter logic)
    populated_attrs = {
        field_name: value
        for field_name, value in source_attrs.items()
        if not is_empty_attribute_value(value)
    }

    if not populated_attrs:
        raise ValueError(
            f"Component {component_type} has no populated data attributes. "
            f"All {len(source_attrs)} attributes are None/empty. "
            "This indicates a data quality issue - nothing to export."
        )

    # Normalize source attribute names (convert to GenericAttribute Name format)
    # Note: We use suffix="" to match the actual export behavior for data attributes
    normalized_source: Set[str] = set()
    for field_name in populated_attrs.keys():
        # Try both with and without suffix since exporters may use different conventions
        normalized_source.add(normalize_attribute_name(field_name, suffix=""))
        normalized_source.add(normalize_attribute_name(field_name, suffix="AssignmentClass"))

    source_count = len(populated_attrs)

    # 3. Extract exported GenericAttribute Names from XML
    # IMPORTANT: Only count DexpiAttributes set, not custom attributes or other sets
    exported_names: Set[str] = set()

    # Find GenericAttribute elements in DexpiAttributes set only
    # This avoids inflating fidelity with custom attributes
    dexpi_attr_sets = exported_element.findall(".//GenericAttributes[@Set='DexpiAttributes']")

    if not dexpi_attr_sets:
        # Fallback: if no DexpiAttributes set found, try all GenericAttributes
        # This handles older exports or different set naming conventions
        generic_attrs = exported_element.findall(".//GenericAttribute")
    else:
        generic_attrs = []
        for attr_set in dexpi_attr_sets:
            generic_attrs.extend(attr_set.findall("GenericAttribute"))

    if not generic_attrs:
        raise RuntimeError(
            f"Exported XML for {component_type} contains zero GenericAttributes. "
            "This indicates an exporter failure - component should have exported data. "
            f"Expected to export {source_count} attributes: {list(populated_attrs.keys())}"
        )

    for attr_elem in generic_attrs:
        name = attr_elem.get("Name")
        if name:
            exported_names.add(name)

    exported_count = len(exported_names)

    # 4. Calculate fidelity
    fidelity_ratio = exported_count / source_count
    fidelity_percent = fidelity_ratio * 100.0

    # 5. Identify missing attributes
    # An attribute is "found" if either:
    # - Its normalized form (with or without suffix) appears in exports
    # - Any dotted expansion (e.g., "FooAssignmentClass.bar") appears (for dict/composite fields)
    missing_attrs = []
    for field_name in populated_attrs.keys():
        name_no_suffix = normalize_attribute_name(field_name, suffix="")
        name_with_suffix = normalize_attribute_name(field_name, suffix="AssignmentClass")

        # Check exact matches first
        found = (name_no_suffix in exported_names or name_with_suffix in exported_names)

        # If not found, check for dotted expansions (dict/composite flattening)
        # e.g., "equipmentDescription" may export as "EquipmentDescription.en", "EquipmentDescription.de"
        if not found:
            for exported_name in exported_names:
                if (exported_name.startswith(name_no_suffix + ".") or
                    exported_name.startswith(name_with_suffix + ".")):
                    found = True
                    break

        if not found:
            missing_attrs.append(field_name)

    # 6. Determine pass/fail status
    status = "PASS" if fidelity_ratio >= threshold else "FAIL"

    result = {
        "component_type": component_type,
        "source_count": source_count,
        "exported_count": exported_count,
        "fidelity_percent": round(fidelity_percent, 2),
        "missing_attributes": sorted(missing_attrs),
        "threshold": threshold,
        "status": status,
    }

    # 7. Optionally raise on failure
    if fail_below_threshold and status == "FAIL":
        raise ValueError(
            f"Export fidelity {fidelity_percent:.1f}% below {threshold*100:.0f}% threshold "
            f"for {component_type}. Missing {len(missing_attrs)} of {source_count} attributes: "
            f"{missing_attrs[:5]}"
        )

    return result
