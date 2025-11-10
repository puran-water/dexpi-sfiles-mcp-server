"""
Configuration and Feature Flags for Phase 1 Migration

This module provides feature flags for gradual rollout of the core layer
migration. Flags are controlled via environment variables for safe toggling
without code changes.

Usage:
    from src.config.settings import is_enabled

    if is_enabled('use_core_equipment_factory'):
        # New core layer path
        factory = get_factory()
        equipment = factory.create(type, tag, params)
    else:
        # Legacy path
        equipment = Tank(...)

Environment Variables:
    USE_CORE_FACTORY=true/false - Toggle core equipment factory
    USE_CORE_ENGINE=true/false  - Toggle core conversion engine

Rollback Strategy:
    Emergency disable via environment:
    $ export USE_CORE_FACTORY=false
    $ export USE_CORE_ENGINE=false
    System immediately reverts to legacy behavior.
"""

import os
from typing import Dict


# Feature flags with environment variable overrides
FEATURE_FLAGS: Dict[str, bool] = {
    # Equipment factory migration (Day 3)
    'use_core_equipment_factory': os.getenv('USE_CORE_FACTORY', 'false').lower() == 'true',

    # Conversion engine migration (Day 4)
    'use_core_conversion_engine': os.getenv('USE_CORE_ENGINE', 'false').lower() == 'true',
}


def is_enabled(flag: str) -> bool:
    """
    Check if a feature flag is enabled.

    Args:
        flag: Feature flag name (e.g., 'use_core_equipment_factory')

    Returns:
        True if flag is enabled, False otherwise

    Raises:
        KeyError: If flag name is not recognized

    Example:
        >>> is_enabled('use_core_equipment_factory')
        False  # Default

        >>> # After: export USE_CORE_FACTORY=true
        >>> is_enabled('use_core_equipment_factory')
        True
    """
    if flag not in FEATURE_FLAGS:
        available = ', '.join(FEATURE_FLAGS.keys())
        raise KeyError(
            f"Unknown feature flag: '{flag}'. "
            f"Available flags: {available}"
        )

    return FEATURE_FLAGS[flag]


def get_all_flags() -> Dict[str, bool]:
    """
    Get all feature flags and their current state.

    Returns:
        Dictionary of flag names to boolean values

    Example:
        >>> get_all_flags()
        {
            'use_core_equipment_factory': False,
            'use_core_conversion_engine': False
        }
    """
    return FEATURE_FLAGS.copy()


def set_flag(flag: str, enabled: bool) -> None:
    """
    Programmatically set a feature flag (for testing only).

    Args:
        flag: Feature flag name
        enabled: True to enable, False to disable

    Warning:
        This is for testing only. In production, use environment variables.

    Example:
        >>> set_flag('use_core_equipment_factory', True)
        >>> is_enabled('use_core_equipment_factory')
        True
    """
    if flag not in FEATURE_FLAGS:
        available = ', '.join(FEATURE_FLAGS.keys())
        raise KeyError(
            f"Unknown feature flag: '{flag}'. "
            f"Available flags: {available}"
        )

    FEATURE_FLAGS[flag] = enabled
