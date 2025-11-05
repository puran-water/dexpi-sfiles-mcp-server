"""Deprecation utilities for MCP tools."""

import logging
import functools
import warnings
from typing import Callable, Optional

logger = logging.getLogger(__name__)


def deprecated(
    reason: str,
    replacement: Optional[str] = None,
    removal_version: Optional[str] = None
) -> Callable:
    """Decorator to mark MCP tool methods as deprecated.

    Args:
        reason: Reason for deprecation
        replacement: Suggested replacement tool/method
        removal_version: Version when this will be removed

    Example:
        @deprecated(
            reason="Tool consolidation",
            replacement="model_batch_apply",
            removal_version="1.0.0"
        )
        async def old_tool(self, args):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Build deprecation message
            msg = f"Tool '{func.__name__}' is deprecated: {reason}."

            if replacement:
                msg += f" Use '{replacement}' instead."

            if removal_version:
                msg += f" Will be removed in version {removal_version}."

            # Log warning
            logger.warning(msg)

            # Also emit Python warning for visibility
            warnings.warn(msg, DeprecationWarning, stacklevel=2)

            # Call original function
            return await func(*args, **kwargs)

        # Mark function as deprecated
        wrapper.__deprecated__ = True
        wrapper.__deprecation_info__ = {
            "reason": reason,
            "replacement": replacement,
            "removal_version": removal_version
        }

        return wrapper

    return decorator


def is_deprecated(func: Callable) -> bool:
    """Check if a function is marked as deprecated.

    Args:
        func: Function to check

    Returns:
        True if deprecated, False otherwise
    """
    return getattr(func, "__deprecated__", False)


def get_deprecation_info(func: Callable) -> Optional[dict]:
    """Get deprecation information for a function.

    Args:
        func: Function to check

    Returns:
        Deprecation info dict or None if not deprecated
    """
    return getattr(func, "__deprecation_info__", None)
