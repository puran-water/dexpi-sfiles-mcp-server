"""
Symbol Resolver - Fuzzy Logic Adapter for SymbolRegistry

This module provides fuzzy matching and fallback logic for symbol lookups
while keeping the core SymbolRegistry strict (fail-loud). Consolidates
capabilities from the legacy DexpiSymbolMapper.

Design Philosophy:
- SymbolRegistry: Strict, fail-loud, data-driven
- SymbolResolver: Fuzzy, opt-in, with confidence metrics
- Separation of concerns: Core vs. heuristic logic
"""

import logging
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher

from src.core.symbols import SymbolRegistry, SymbolInfo, get_registry

logger = logging.getLogger(__name__)


class SymbolResolver:
    """
    Adapter providing fuzzy symbol resolution with confidence metrics.

    Adds three capabilities missing from strict SymbolRegistry:
    1. Actuated valve variant lookup (A→B mappings)
    2. Fuzzy matching with confidence scores (opt-in)
    3. Validation with multi-symbol class support

    All fuzzy logic is opt-in and returns confidence scores for caller decision.
    """

    # Known actuated valve mappings (A → B suffix)
    # These are fallback values; we first try to derive from catalog
    ACTUATED_MAPPINGS = {
        "PV003A": "PV003B",  # Three way valve
        "PV004A": "PV004B",  # Four way valve
        "PV005A": "PV005B",  # Gate valve
        "PV007A": "PV007B",  # Globe valve
        "PV008A": "PV008B",  # Float valve
        "PV014A": "PV014B",  # Pinch valve
        "PV015A": "PV015B",  # Diaphragm valve
        "PV016A": "PV016B",  # Needle valve
        "PV018A": "PV018B",  # Butterfly valve
        "PV019A": "PV019B",  # Ball valve
        "PV023A": "PV023B",  # Plug valve
    }

    def __init__(self, registry: Optional[SymbolRegistry] = None):
        """
        Initialize resolver with a symbol registry.

        Args:
            registry: SymbolRegistry instance (uses global if None)
        """
        self.registry = registry or get_registry()
        self._actuated_cache: Optional[Dict[str, str]] = None

    def get_actuated_variant(self, symbol_id: str) -> Optional[str]:
        """
        Get actuated variant of a valve symbol (A → B suffix mapping).

        This method is data-driven: it scans the catalog for A/B pairs
        and falls back to hardcoded mappings only if needed.

        Args:
            symbol_id: Base manual valve symbol ID (e.g., "PV019A")

        Returns:
            Actuated variant symbol ID (e.g., "PV019B") or None

        Examples:
            >>> resolver.get_actuated_variant("PV019A")
            "PV019B"  # Ball valve, manual → actuated
            >>> resolver.get_actuated_variant("PV005A")
            "PV005B"  # Gate valve, manual → actuated
        """
        # Build cache on first use
        if self._actuated_cache is None:
            self._build_actuated_cache()

        return self._actuated_cache.get(symbol_id)

    def _build_actuated_cache(self):
        """
        Build actuated variant cache by scanning catalog for A/B pairs.

        Strategy:
        1. Scan all symbols for A/B suffix pairs
        2. Check attributes/variants field if populated
        3. Use hardcoded ACTUATED_MAPPINGS as fallback

        This keeps the resolver data-driven and prevents drift when
        new operated variants appear in upstream catalogs.
        """
        self._actuated_cache = {}

        # Scan catalog for A/B pairs
        for symbol_id, symbol in self.registry._symbols.items():
            # Check for manual valve (A suffix)
            if symbol_id.endswith("A"):
                base = symbol_id[:-1]  # Remove A suffix
                actuated_id = base + "B"

                # Check if B variant exists in catalog
                if actuated_id in self.registry._symbols:
                    self._actuated_cache[symbol_id] = actuated_id
                    logger.debug(f"Found A/B pair: {symbol_id} → {actuated_id}")

            # Check attributes/variants field (future-proofing)
            if symbol.attributes and "variants" in symbol.attributes:
                variants = symbol.attributes["variants"]
                if isinstance(variants, dict) and "actuated" in variants:
                    self._actuated_cache[symbol_id] = variants["actuated"]

        # Add hardcoded fallbacks for known mappings
        for manual, actuated in self.ACTUATED_MAPPINGS.items():
            if manual not in self._actuated_cache:
                # Only add if not already found in catalog
                self._actuated_cache[manual] = actuated
                logger.debug(f"Using fallback A/B mapping: {manual} → {actuated}")

        logger.info(f"Built actuated variant cache with {len(self._actuated_cache)} mappings")

    def get_by_dexpi_class_fuzzy(
        self,
        dexpi_class: str,
        confidence_threshold: float = 0.7
    ) -> Optional[Tuple[SymbolInfo, float]]:
        """
        Fuzzy lookup for DEXPI class with confidence metric.

        This is OPT-IN fuzzy matching that returns confidence scores
        so callers can decide whether to accept the fallback result.

        Strategy:
        1. Try exact match via registry.get_by_dexpi_class()
        2. Try actuated variant of exact match
        3. Use registry.search() with Levenshtein ranking
        4. Return (symbol, confidence) or None

        Does NOT use base-class inference (catalog lacks generic "Pump", "Valve" entries).

        Args:
            dexpi_class: DEXPI class name to look up
            confidence_threshold: Minimum confidence (0.0-1.0) to return result

        Returns:
            (SymbolInfo, confidence) tuple if match found above threshold, else None
            Confidence = 1.0 for exact matches, <1.0 for fuzzy matches

        Examples:
            >>> resolver.get_by_dexpi_class_fuzzy("CentrifugalPump")
            (SymbolInfo(...), 1.0)  # Exact match
            >>> resolver.get_by_dexpi_class_fuzzy("CustomCentrifugalPump")
            (SymbolInfo(...), 0.85)  # Fuzzy match via search
            >>> resolver.get_by_dexpi_class_fuzzy("UnknownEquipment")
            None  # No match above threshold
        """
        # Step 1: Try exact match (confidence = 1.0)
        exact = self.registry.get_by_dexpi_class(dexpi_class)
        if exact:
            logger.debug(f"Exact match for {dexpi_class}: {exact.symbol_id}")
            return (exact, 1.0)

        # Step 2: Try Custom prefix stripping (confidence = 0.95)
        if dexpi_class.startswith("Custom"):
            base_class = dexpi_class[6:]  # Remove "Custom"
            base = self.registry.get_by_dexpi_class(base_class)
            if base:
                logger.debug(f"Custom prefix match for {dexpi_class}: {base.symbol_id}")
                return (base, 0.95)

        # Step 3: Fuzzy search using registry.search() with Levenshtein ranking
        # Search in DEXPI class names, symbol IDs, and display names
        candidates = self.registry.search(dexpi_class)

        if not candidates:
            logger.debug(f"No fuzzy matches found for {dexpi_class}")
            return None

        # Rank candidates by Levenshtein similarity
        ranked = []
        for candidate in candidates:
            # Compare against DEXPI class if available
            if candidate.dexpi_class:
                ratio = self._levenshtein_ratio(dexpi_class, candidate.dexpi_class)
            else:
                # Fallback to symbol name comparison
                ratio = self._levenshtein_ratio(dexpi_class, candidate.name)

            ranked.append((candidate, ratio))

        # Sort by confidence (descending)
        ranked.sort(key=lambda x: x[1], reverse=True)

        # Return best match if above threshold
        best_symbol, best_confidence = ranked[0]
        if best_confidence >= confidence_threshold:
            logger.debug(
                f"Fuzzy match for {dexpi_class}: {best_symbol.symbol_id} "
                f"(confidence: {best_confidence:.2f})"
            )
            return (best_symbol, best_confidence)

        logger.debug(
            f"Best fuzzy match for {dexpi_class} below threshold: "
            f"{best_symbol.symbol_id} (confidence: {best_confidence:.2f} < {confidence_threshold})"
        )
        return None

    def _levenshtein_ratio(self, s1: str, s2: str) -> float:
        """
        Calculate Levenshtein similarity ratio (0.0 to 1.0).

        Uses Python's difflib.SequenceMatcher for efficient comparison.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Similarity ratio (1.0 = identical, 0.0 = completely different)
        """
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    def validate_mapping(
        self,
        dexpi_class: str,
        symbol_id: str,
        allow_actuated: bool = True
    ) -> Tuple[bool, str]:
        """
        Validate if a symbol is appropriate for a DEXPI class.

        Handles multiple symbols per DEXPI class (catalog can have several
        valid symbols for one class). Also checks actuated variants when enabled.

        Args:
            dexpi_class: DEXPI class name
            symbol_id: Symbol ID to validate
            allow_actuated: Whether to accept A/B actuated variants

        Returns:
            (is_valid, reason) tuple
            - is_valid: True if symbol is valid for this class
            - reason: Human-readable explanation

        Examples:
            >>> resolver.validate_mapping("BallValve", "PV019A")
            (True, "Exact match in catalog")
            >>> resolver.validate_mapping("BallValve", "PV019B")
            (True, "Valid actuated variant")
            >>> resolver.validate_mapping("BallValve", "PP001A")
            (False, "Symbol PP001A not mapped to BallValve")
        """
        # Get all valid symbols for this DEXPI class
        symbol_ids = self.registry._dexpi_map.get(dexpi_class, [])

        # Check exact match
        if symbol_id in symbol_ids:
            return (True, "Exact match in catalog")

        # Check if symbol_id is actuated variant of any valid symbol
        if allow_actuated:
            for valid_id in symbol_ids:
                actuated = self.get_actuated_variant(valid_id)
                if actuated == symbol_id:
                    return (True, f"Valid actuated variant of {valid_id}")

            # Also check reverse: if symbol_id ends in A, check if its B variant matches
            if symbol_id.endswith("A"):
                actuated = self.get_actuated_variant(symbol_id)
                if actuated and actuated in symbol_ids:
                    return (True, f"Manual variant of actuated symbol {actuated}")

        # Check Custom prefix stripping
        if dexpi_class.startswith("Custom"):
            base_class = dexpi_class[6:]
            base_symbols = self.registry._dexpi_map.get(base_class, [])
            if symbol_id in base_symbols:
                return (True, f"Valid for base class {base_class}")

        # Invalid
        if symbol_ids:
            return (
                False,
                f"Symbol {symbol_id} not mapped to {dexpi_class}. "
                f"Valid symbols: {', '.join(symbol_ids)}"
            )
        else:
            return (
                False,
                f"DEXPI class {dexpi_class} not found in catalog"
            )

    # Convenience methods delegating to registry (backward compatibility)

    def get_symbol(self, symbol_id: str) -> Optional[SymbolInfo]:
        """Get symbol by ID (delegates to registry)."""
        return self.registry.get_symbol(symbol_id)

    def get_by_dexpi_class(
        self,
        dexpi_class: str,
        prefer_source=None
    ) -> Optional[SymbolInfo]:
        """Get symbol by DEXPI class, strict mode (delegates to registry)."""
        return self.registry.get_by_dexpi_class(dexpi_class, prefer_source)

    def search(self, query: str, category=None, source=None) -> List[SymbolInfo]:
        """Search symbols (delegates to registry)."""
        return self.registry.search(query, category, source)


# Singleton instance for global access
_resolver: Optional[SymbolResolver] = None


def get_resolver() -> SymbolResolver:
    """Get the global symbol resolver."""
    global _resolver
    if _resolver is None:
        _resolver = SymbolResolver()
    return _resolver
