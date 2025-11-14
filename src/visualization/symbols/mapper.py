"""
DEPRECATED: DEXPI Class to NOAKADEXPI Symbol Mapper

This module has been replaced by src.core.symbol_resolver.SymbolResolver
which provides the same functionality with a more robust, data-driven approach.

This file now contains only a thin wrapper for backward compatibility.
All new code should use SymbolResolver directly.

Migration Guide:
    OLD: from src.visualization.symbols.mapper import DexpiSymbolMapper
    NEW: from src.core.symbol_resolver import SymbolResolver

    OLD: mapper = DexpiSymbolMapper()
    NEW: resolver = SymbolResolver()

    OLD: mapper.get_symbol_for_dexpi_class("CentrifugalPump")
    NEW: symbol = resolver.get_by_dexpi_class("CentrifugalPump")
         symbol_id = symbol.symbol_id if symbol else None

Removal Timeline: This wrapper will be removed in v2.0 (targeting Q2 2025).
"""

from typing import Optional, List
from dataclasses import dataclass
import warnings
import logging

# Import new resolver
from src.core.symbol_resolver import SymbolResolver, get_resolver
from src.core.symbols import SymbolInfo

logger = logging.getLogger(__name__)


def _deprecation_warning(method_name: str):
    """Emit deprecation warning for old DexpiSymbolMapper usage."""
    warnings.warn(
        f"DexpiSymbolMapper.{method_name}() is deprecated and will be removed in v2.0. "
        f"Use src.core.symbol_resolver.SymbolResolver instead. "
        f"See docs/active/CORE_LAYER_MIGRATION_PLAN.md for migration guide.",
        DeprecationWarning,
        stacklevel=3
    )


@dataclass
class SymbolMapping:
    """
    DEPRECATED: Legacy symbol mapping entry.
    Use SymbolInfo from src.core.symbols instead.
    """
    symbol_id: str
    description: str
    grouping: str
    dexpi_class: Optional[str] = None
    variants: List[str] = None


class DexpiSymbolMapper:
    """
    DEPRECATED: Legacy DEXPI class to symbol mapper.

    This class is now a thin wrapper around SymbolResolver for backward compatibility.
    All functionality has been migrated to the new core symbol system.

    **WARNING**: This class will be removed in v2.0.

    Migration:
        - Use SymbolResolver from src.core.symbol_resolver
        - See migration plan at docs/active/CORE_LAYER_MIGRATION_PLAN.md
    """

    # Legacy constants kept for reference only
    # These are NOT used by the wrapper - all data comes from SymbolRegistry/SymbolResolver
    SYMBOL_MAPPINGS = {}  # Deprecated
    ALTERNATIVE_MAPPINGS = {}  # Deprecated

    def __init__(self):
        """
        Initialize mapper wrapper.

        Emits deprecation warning and delegates to SymbolResolver.
        """
        # Emit warning on instantiation
        warnings.warn(
            "DexpiSymbolMapper is deprecated and will be removed in v2.0. "
            "Use SymbolResolver from src.core.symbol_resolver instead. "
            "See docs/active/CORE_LAYER_MIGRATION_PLAN.md for migration guide.",
            DeprecationWarning,
            stacklevel=2
        )

        # Delegate to new resolver
        self._resolver = get_resolver()

        # Legacy attribute for compatibility
        self.mappings = {}
        self.alternatives = {}

    def get_symbol_for_dexpi_class(self, dexpi_class: str) -> Optional[str]:
        """
        DEPRECATED: Get symbol ID for DEXPI class.

        Use SymbolResolver.get_by_dexpi_class() instead.

        Args:
            dexpi_class: DEXPI class name

        Returns:
            Symbol ID or None
        """
        _deprecation_warning("get_symbol_for_dexpi_class")

        # Try exact match first
        symbol = self._resolver.get_by_dexpi_class(dexpi_class)
        if symbol:
            return symbol.symbol_id

        # Fall back to fuzzy matching (preserves old behavior)
        result = self._resolver.get_by_dexpi_class_fuzzy(
            dexpi_class,
            confidence_threshold=0.6  # Lower threshold for backward compatibility
        )
        if result:
            symbol, confidence = result
            logger.debug(
                f"Fuzzy match for {dexpi_class}: {symbol.symbol_id} "
                f"(confidence: {confidence:.2f})"
            )
            return symbol.symbol_id

        logger.warning(f"No symbol mapping found for DEXPI class: {dexpi_class}")
        return None

    def get_symbol_info(self, symbol_id: str) -> Optional[SymbolMapping]:
        """
        DEPRECATED: Get symbol information.

        Use SymbolResolver.get_symbol() instead.

        Args:
            symbol_id: Symbol ID

        Returns:
            SymbolMapping (legacy format) or None
        """
        _deprecation_warning("get_symbol_info")

        symbol = self._resolver.get_symbol(symbol_id)
        if symbol:
            # Convert SymbolInfo to legacy SymbolMapping format
            return SymbolMapping(
                symbol_id=symbol.symbol_id,
                description=symbol.name,
                grouping=symbol.category.value,
                dexpi_class=symbol.dexpi_class
            )
        return None

    def get_actuated_variant(self, symbol_id: str) -> Optional[str]:
        """
        DEPRECATED: Get actuated variant of valve symbol.

        Use SymbolResolver.get_actuated_variant() instead.

        Args:
            symbol_id: Base symbol ID

        Returns:
            Actuated variant ID or None
        """
        _deprecation_warning("get_actuated_variant")
        return self._resolver.get_actuated_variant(symbol_id)

    def list_categories(self) -> List[str]:
        """
        DEPRECATED: Get list of all categories.

        Use SymbolRegistry.get_statistics() instead.

        Returns:
            List of category names
        """
        _deprecation_warning("list_categories")

        stats = self._resolver.registry.get_statistics()
        return sorted(stats.get("by_category", {}).keys())

    def get_symbols_by_category(self, category: str) -> List[SymbolMapping]:
        """
        DEPRECATED: Get all symbols in a category.

        Use SymbolRegistry.get_by_category() instead.

        Args:
            category: Category name

        Returns:
            List of SymbolMapping (legacy format)
        """
        _deprecation_warning("get_symbols_by_category")

        # Convert category string to SymbolCategory enum
        from src.core.symbols import SymbolCategory

        try:
            cat_enum = SymbolCategory[category.upper().replace(" ", "_")]
        except KeyError:
            logger.warning(f"Unknown category: {category}")
            return []

        symbols = self._resolver.registry.get_by_category(cat_enum)

        # Convert to legacy SymbolMapping format
        return [
            SymbolMapping(
                symbol_id=s.symbol_id,
                description=s.name,
                grouping=s.category.value,
                dexpi_class=s.dexpi_class
            )
            for s in symbols
        ]

    def validate_mapping(self, dexpi_class: str, symbol_id: str) -> bool:
        """
        DEPRECATED: Validate if symbol is appropriate for DEXPI class.

        Use SymbolResolver.validate_mapping() instead.

        Args:
            dexpi_class: DEXPI class name
            symbol_id: Symbol ID to validate

        Returns:
            True if valid
        """
        _deprecation_warning("validate_mapping")

        is_valid, reason = self._resolver.validate_mapping(
            dexpi_class,
            symbol_id,
            allow_actuated=True
        )
        if not is_valid:
            logger.debug(f"Validation failed: {reason}")
        return is_valid


# Backward compatibility: Keep module-level constants
# These are NOT used by the wrapper but may be referenced externally
SYMBOL_MAPPINGS = {}  # Deprecated - data now in SymbolRegistry
ALTERNATIVE_MAPPINGS = {}  # Deprecated - data now in SymbolRegistry
