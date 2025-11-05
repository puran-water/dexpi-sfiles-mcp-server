"""
Safe import wrapper for SFILES2 Flowsheet_Class.

This adapter provides clear error messages if the SFILES2 package is not installed,
preventing cryptic ImportErrors at runtime.

The Flowsheet_Class module is exposed when SFILES2 is properly installed as a wheel.
See: https://github.com/process-intelligence-research/SFILES2

Usage:
    from src.adapters.sfiles_adapter import get_flowsheet_class
    Flowsheet = get_flowsheet_class()
"""

import logging

logger = logging.getLogger(__name__)


def get_flowsheet_class():
    """
    Import Flowsheet with helpful error on failure.

    Returns:
        Flowsheet class from SFILES2

    Raises:
        ImportError: If SFILES2 is not installed, with installation instructions
    """
    try:
        from Flowsheet_Class.flowsheet import Flowsheet
        logger.debug("✓ SFILES2 (Flowsheet_Class) imported successfully")
        return Flowsheet
    except ImportError as e:
        error_msg = (
            "SFILES2 (Flowsheet_Class) not found. Install with:\n"
            "  pip install git+https://github.com/process-intelligence-research/SFILES2.git\n"
            "\n"
            "Or if you have a local clone:\n"
            "  cd /path/to/SFILES2\n"
            "  pip install -e .\n"
            "\n"
            f"Original error: {e}"
        )
        logger.error(error_msg)
        raise ImportError(error_msg) from e


def validate_sfiles_available() -> bool:
    """
    Check if SFILES2 is available without raising exception.

    Returns:
        True if SFILES2 can be imported, False otherwise
    """
    try:
        get_flowsheet_class()
        return True
    except ImportError:
        return False


# Optional: Cache the class after first successful import
_flowsheet_class = None


def get_flowsheet_class_cached():
    """
    Import Flowsheet with caching for performance.

    Returns:
        Flowsheet class from SFILES2 (cached after first import)
    """
    global _flowsheet_class

    if _flowsheet_class is None:
        _flowsheet_class = get_flowsheet_class()

    return _flowsheet_class
