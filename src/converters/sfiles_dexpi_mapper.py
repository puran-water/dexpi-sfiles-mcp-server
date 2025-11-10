"""Deprecated: Bidirectional mapper between SFILES and DEXPI formats.

This module is DEPRECATED and maintained only for backward compatibility.
All functionality has been migrated to src.core.conversion module.

Phase 1 Migration: This is now a thin wrapper around get_engine().
Original mapper (~588 lines) replaced with core layer integration (~50 lines).

For new code, use:
    from src.core.conversion import get_engine
    engine = get_engine()
    dexpi_model = engine.sfiles_to_dexpi(sfiles_model)
    sfiles_string = engine.dexpi_to_sfiles(dexpi_model)
"""

import warnings
import logging
from typing import Any

from ..adapters.sfiles_adapter import get_flowsheet_class
from ..core.conversion import get_engine

# Safe import with helpful error messages
Flowsheet = get_flowsheet_class()

logger = logging.getLogger(__name__)


class SfilesDexpiMapper:
    """DEPRECATED: Maps between SFILES notation and DEXPI P&ID models.

    This class is maintained only for backward compatibility.
    All methods now delegate to the core conversion engine.

    Migration path:
        OLD: mapper = SfilesDexpiMapper(); model = mapper.sfiles_to_dexpi(fs)
        NEW: engine = get_engine(); model = engine.sfiles_to_dexpi(sfiles_model)
    """

    def __init__(self):
        """Initialize the mapper (deprecated).

        Issues deprecation warning and creates core engine instance.
        """
        warnings.warn(
            "SfilesDexpiMapper is deprecated. Use src.core.conversion.get_engine() instead. "
            "This wrapper will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2
        )
        self.engine = get_engine()
        logger.warning(
            "SfilesDexpiMapper is deprecated - using core conversion engine instead"
        )

    def sfiles_to_dexpi(self, flowsheet: Flowsheet) -> Any:
        """Convert SFILES flowsheet to DEXPI P&ID model.

        DEPRECATED: Use get_engine().sfiles_to_dexpi() instead.

        Args:
            flowsheet: SFILES flowsheet object

        Returns:
            DexpiModel with equipment, piping, and instrumentation
        """
        # Handle SFILES2 API: get SFILES string from flowsheet
        if hasattr(flowsheet, 'sfiles') and flowsheet.sfiles:
            sfiles_string = flowsheet.sfiles
        elif hasattr(flowsheet, 'convert_to_sfiles'):
            flowsheet.convert_to_sfiles()
            sfiles_string = flowsheet.sfiles
        else:
            sfiles_string = str(flowsheet)

        # Parse and convert via core engine
        sfiles_model = self.engine.parse_sfiles(sfiles_string)
        return self.engine.sfiles_to_dexpi(sfiles_model)

    def dexpi_to_sfiles(self, dexpi_model: Any) -> Flowsheet:
        """Convert DEXPI P&ID model to SFILES flowsheet.

        DEPRECATED: Use get_engine().dexpi_to_sfiles() instead.

        Args:
            dexpi_model: DEXPI model to convert

        Returns:
            SFILES flowsheet object
        """
        # Convert via core engine (returns SFILES string)
        sfiles_string = self.engine.dexpi_to_sfiles(dexpi_model)

        # Create Flowsheet object from SFILES string (proper SFILES2 API)
        flowsheet = Flowsheet(sfiles_in=sfiles_string)

        return flowsheet
