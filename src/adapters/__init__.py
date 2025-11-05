"""
Adapter modules for external library integrations.

This package contains safe wrappers and adapters for upstream libraries
to provide better error messages and graceful degradation.
"""

from .sfiles_adapter import (
    get_flowsheet_class,
    get_flowsheet_class_cached,
    validate_sfiles_available
)

__all__ = [
    'get_flowsheet_class',
    'get_flowsheet_class_cached',
    'validate_sfiles_available',
]
