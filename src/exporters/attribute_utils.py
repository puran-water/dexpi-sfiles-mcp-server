"""Shared utilities for attribute name transformation and filtering.

Extracted from GenericAttributeExporter to avoid circular dependencies between
core analytics and exporter modules.
"""

from typing import Any


def normalize_attribute_name(field_name: str, suffix: str = "AssignmentClass") -> str:
    """
    Transform pyDEXPI field name to GenericAttribute Name format.

    Matches the logic from GenericAttributeExporter._attribute_name():
    - Converts snake_case to CamelCase
    - Appends suffix (default: "AssignmentClass")

    Examples:
        >>> normalize_attribute_name("process_tag")
        'ProcessTagAssignmentClass'
        >>> normalize_attribute_name("tagName", "")
        'TagName'

    Args:
        field_name: pyDEXPI field name (snake_case or camelCase)
        suffix: Optional suffix to append (default: "AssignmentClass")

    Returns:
        Normalized GenericAttribute Name
    """
    if not field_name:
        return suffix or ""

    if "_" in field_name:
        # Convert snake_case to CamelCase
        camel = "".join(part.capitalize() for part in field_name.split("_") if part)
    else:
        # Ensure first letter is uppercase
        camel = field_name[0].upper() + field_name[1:]

    return f"{camel}{suffix}" if suffix else camel


def is_empty_attribute_value(value: Any) -> bool:
    """
    Check if attribute value should be skipped during export.

    Matches the logic from GenericAttributeExporter._is_empty_value():
    - None values
    - Empty strings
    - Empty collections (list, tuple, set, dict)

    Note: Zero, False, and empty datetime are NOT considered empty.

    Examples:
        >>> is_empty_attribute_value(None)
        True
        >>> is_empty_attribute_value("")
        True
        >>> is_empty_attribute_value([])
        True
        >>> is_empty_attribute_value(0)
        False
        >>> is_empty_attribute_value(False)
        False

    Args:
        value: Attribute value to check

    Returns:
        True if value should be skipped, False otherwise
    """
    if value is None:
        return True
    if isinstance(value, str) and value == "":
        return True
    if isinstance(value, (list, tuple, set, dict)) and not value:
        return True
    return False
