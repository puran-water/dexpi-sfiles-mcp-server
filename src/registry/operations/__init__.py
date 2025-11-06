"""
Initial operation registrations for engineering-mcp-server.

Registers core DEXPI, SFILES, and template operations with the registry.
"""

from .dexpi_operations import register_dexpi_operations
from .sfiles_operations import register_sfiles_operations
from .template_operations import register_template_operations


def register_all_operations():
    """Register all initial operations."""
    register_dexpi_operations()
    register_sfiles_operations()
    register_template_operations()


__all__ = [
    'register_all_operations',
    'register_dexpi_operations',
    'register_sfiles_operations',
    'register_template_operations',
]
