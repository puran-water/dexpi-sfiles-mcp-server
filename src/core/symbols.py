"""
Core Symbol Module - Single Source of Truth for Symbol Mappings

This module consolidates symbol mappings from:
- mapper.py (DEXPI to Symbol ID mappings)
- catalog.py (symbol metadata and categories)
- importer.py (symbol file locations)
- merge_symbol_libraries.py (NOAKA vs DISC provenance)

Provides unified access to symbol data with provenance tracking.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class SymbolSource(Enum):
    """Symbol library sources."""
    NOAKADEXPI = "NOAKADEXPI"
    DISCDEXPI = "DISCDEXPI"
    CUSTOM = "CUSTOM"
    MERGED = "MERGED"


class SymbolCategory(Enum):
    """Symbol categories for organization."""
    PUMPS = "Pumps"
    VALVES = "Valves"
    TANKS = "Tanks"
    EQUIPMENT = "Equipment"
    FILTERS = "Filters"
    SEPARATORS = "Separators"
    INSTRUMENTATION = "Instrumentation"
    ANNOTATIONS = "Annotations"
    SPECIAL = "Special"
    DETAIL = "Detail"
    ORIGO = "Origo"
    UNKNOWN = "Unknown"


@dataclass
class SymbolInfo:
    """Complete information about a symbol."""
    # Identifiers
    symbol_id: str  # e.g., "PP0101"
    name: str  # Display name

    # Classification
    category: SymbolCategory
    dexpi_class: Optional[str] = None  # DEXPI class name

    # File information
    file_path: Optional[str] = None  # Relative path to SVG
    file_hash: Optional[str] = None  # SHA256 for deduplication

    # Provenance
    source: SymbolSource = SymbolSource.MERGED
    original_source: Optional[SymbolSource] = None  # If merged
    is_unique_to_source: bool = False

    # Metadata
    variants: List[str] = None  # Alternative symbol IDs
    tags: List[str] = None  # Searchable tags
    attributes: Dict = None  # Additional metadata


class SymbolRegistry:
    """
    Central registry for all symbol mappings and metadata.
    Consolidates data from NOAKADEXPI and DISCDEXPI libraries.
    """

    def __init__(self, assets_dir: Optional[Path] = None):
        """Initialize registry with symbol data."""
        if assets_dir is None:
            # Default to visualization/symbols/assets
            assets_dir = Path(__file__).parent.parent / "visualization" / "symbols" / "assets"

        self.assets_dir = assets_dir
        self._symbols: Dict[str, SymbolInfo] = {}
        self._dexpi_map: Dict[str, List[str]] = {}  # DEXPI class → symbol IDs
        self._category_map: Dict[SymbolCategory, List[str]] = {}  # Category → symbol IDs

        # Load symbol data
        self._load_merged_catalog()
        self._build_indices()

    def _load_merged_catalog(self):
        """Load the merged symbol catalog if it exists."""
        catalog_path = self.assets_dir / "merged_catalog.json"

        if not catalog_path.exists():
            logger.warning(f"Merged catalog not found at {catalog_path}, loading defaults")
            self._load_default_mappings()
            return

        try:
            with open(catalog_path) as f:
                catalog = json.load(f)

            # Process each symbol
            for symbol_id, data in catalog.get("symbols", {}).items():
                # Determine category
                category_str = data.get("category", "Unknown")
                try:
                    category = SymbolCategory[category_str.upper().replace(" ", "_")]
                except KeyError:
                    category = self._guess_category(symbol_id)

                # Determine source
                provenance = data.get("provenance", {})
                source_str = provenance.get("source_repo", "MERGED")
                try:
                    source = SymbolSource[source_str]
                except KeyError:
                    source = SymbolSource.MERGED

                # Create symbol info
                symbol = SymbolInfo(
                    symbol_id=symbol_id,
                    name=data.get("name", symbol_id),
                    category=category,
                    dexpi_class=data.get("dexpi_class"),
                    file_path=data.get("source_file"),
                    file_hash=provenance.get("file_hash"),
                    source=source,
                    is_unique_to_source=provenance.get("is_unique_to_source", False),
                    attributes=data.get("metadata", {})
                )

                self._symbols[symbol_id] = symbol

            logger.info(f"Loaded {len(self._symbols)} symbols from merged catalog")

        except Exception as e:
            logger.error(f"Failed to load merged catalog: {e}")
            # NO FALLBACKS - re-raise so we know the catalog is broken
            raise

    def _load_default_mappings(self):
        """Load default symbol mappings as fallback."""
        # Critical default mappings for common equipment
        # NOTE: These use NOAKADEXPI PP001A format (3 digits + letter)
        # Symbol IDs verified against merged_catalog.json
        defaults = [
            # Pumps (verified in catalog)
            ("PP001A", "Centrifugal Pump", SymbolCategory.PUMPS, "CentrifugalPump"),
            ("PP010A", "Reciprocating Pump", SymbolCategory.PUMPS, "ReciprocatingPump"),
            ("PP003A", "Gear Pump", SymbolCategory.PUMPS, "GearPump"),

            # Valves (verified in catalog)
            ("PV005A", "Gate Valve", SymbolCategory.VALVES, "GateValve"),
            ("PV007A", "Globe Valve", SymbolCategory.VALVES, "GlobeValve"),
            ("PV019A", "Ball Valve", SymbolCategory.VALVES, "BallValve"),
            ("PV018A", "Butterfly Valve", SymbolCategory.VALVES, "ButterflyValve"),
            ("PV013A", "Check Valve", SymbolCategory.VALVES, "CheckValve"),
            ("PV001A", "Control Valve", SymbolCategory.VALVES, "OperatedValve"),  # Placeholder

            # Tanks (verified in catalog where available)
            ("PE025A", "Storage Tank", SymbolCategory.TANKS, "Tank"),
            ("PT002A", "Pressure Vessel", SymbolCategory.TANKS, "PressureVessel"),  # Verified in XLSM
            ("PT006A", "Silo", SymbolCategory.TANKS, "Silo"),

            # Equipment (verified in catalog where available)
            ("PE037A", "Heat Exchanger", SymbolCategory.EQUIPMENT, "HeatExchanger"),
            ("PE001A", "Heater", SymbolCategory.EQUIPMENT, "Heater"),  # Placeholder
            ("PE002A", "Cooler", SymbolCategory.EQUIPMENT, "Cooler"),  # Placeholder
            ("PE003A", "Reactor", SymbolCategory.EQUIPMENT, "Reactor"),  # Placeholder
            ("PE012A", "Separator", SymbolCategory.EQUIPMENT, "Separator"),
            ("PE030A", "Centrifuge", SymbolCategory.EQUIPMENT, "Centrifuge"),
            ("PE004A", "Column", SymbolCategory.EQUIPMENT, "ProcessColumn"),  # Placeholder
            ("PE005A", "Mixer", SymbolCategory.EQUIPMENT, "Mixer"),  # Placeholder

            # Filters (verified in catalog)
            ("PS014A", "Filter", SymbolCategory.FILTERS, "Filter"),
            ("PF001A", "Strainer", SymbolCategory.FILTERS, "Filter"),  # Placeholder

            # Instrumentation (verified in catalog where available)
            ("IM005A", "Transmitter", SymbolCategory.INSTRUMENTATION, "Transmitter"),  # Placeholder
            ("ND0006", "Controller", SymbolCategory.ANNOTATIONS, "ProcessControlFunction"),  # Exception: ND series uses 4-digit format
            ("IM017A", "Indicator", SymbolCategory.INSTRUMENTATION, "ProcessIndicator"),  # Placeholder
        ]

        for symbol_id, name, category, dexpi_class in defaults:
            self._symbols[symbol_id] = SymbolInfo(
                symbol_id=symbol_id,
                name=name,
                category=category,
                dexpi_class=dexpi_class,
                source=SymbolSource.CUSTOM
            )

        logger.info(f"Loaded {len(self._symbols)} default symbol mappings")

    def _guess_category(self, symbol_id: str) -> SymbolCategory:
        """Guess category from symbol ID prefix."""
        prefix_map = {
            "PP": SymbolCategory.PUMPS,
            "PV": SymbolCategory.VALVES,
            "PT": SymbolCategory.TANKS,
            "PE": SymbolCategory.EQUIPMENT,
            "PF": SymbolCategory.FILTERS,
            "PS": SymbolCategory.SEPARATORS,
            "IM": SymbolCategory.INSTRUMENTATION,
            "ND": SymbolCategory.ANNOTATIONS,
            "LZ": SymbolCategory.SPECIAL
        }

        # Check for Detail or Origo suffix
        if "_Detail" in symbol_id:
            return SymbolCategory.DETAIL
        if "_Origo" in symbol_id:
            return SymbolCategory.ORIGO

        # Check prefix
        prefix = symbol_id[:2] if len(symbol_id) >= 2 else ""
        return prefix_map.get(prefix, SymbolCategory.UNKNOWN)

    def _build_indices(self):
        """Build lookup indices for efficient searching."""
        # Clear indices
        self._dexpi_map.clear()
        self._category_map.clear()

        # Build indices
        for symbol_id, symbol in self._symbols.items():
            # DEXPI class index
            if symbol.dexpi_class:
                if symbol.dexpi_class not in self._dexpi_map:
                    self._dexpi_map[symbol.dexpi_class] = []
                self._dexpi_map[symbol.dexpi_class].append(symbol_id)

            # Category index
            if symbol.category not in self._category_map:
                self._category_map[symbol.category] = []
            self._category_map[symbol.category].append(symbol_id)

    def get_symbol(self, symbol_id: str) -> Optional[SymbolInfo]:
        """
        Get symbol information by ID.

        Args:
            symbol_id: Symbol ID (e.g., PP001A)

        Returns:
            SymbolInfo if found, None otherwise
        """
        return self._symbols.get(symbol_id)

    def get_by_dexpi_class(
        self,
        dexpi_class: str,
        prefer_source: Optional[SymbolSource] = None
    ) -> Optional[SymbolInfo]:
        """
        Get best symbol for a DEXPI class.

        Args:
            dexpi_class: DEXPI class name
            prefer_source: Preferred source (NOAKA or DISC)

        Returns:
            Best matching symbol or None
        """
        symbol_ids = self._dexpi_map.get(dexpi_class, [])
        if not symbol_ids:
            # Try without "Custom" prefix
            if dexpi_class.startswith("Custom"):
                base_class = dexpi_class[6:]  # Remove "Custom"
                symbol_ids = self._dexpi_map.get(base_class, [])

        if not symbol_ids:
            return None

        # If preference specified, try to find from that source
        if prefer_source:
            for symbol_id in symbol_ids:
                symbol = self._symbols[symbol_id]
                if symbol.source == prefer_source or symbol.original_source == prefer_source:
                    return symbol

        # Return first (or most common) symbol
        return self._symbols[symbol_ids[0]]

    def get_by_category(self, category: SymbolCategory) -> List[SymbolInfo]:
        """Get all symbols in a category."""
        symbol_ids = self._category_map.get(category, [])
        return [self._symbols[sid] for sid in symbol_ids]

    def search(
        self,
        query: str,
        category: Optional[SymbolCategory] = None,
        source: Optional[SymbolSource] = None
    ) -> List[SymbolInfo]:
        """
        Search for symbols by query string.

        Args:
            query: Search term (matches ID, name, or tags)
            category: Filter by category
            source: Filter by source

        Returns:
            List of matching symbols
        """
        query_lower = query.lower()
        results = []

        for symbol in self._symbols.values():
            # Apply filters
            if category and symbol.category != category:
                continue
            if source and symbol.source != source and symbol.original_source != source:
                continue

            # Check matches
            if (
                query_lower in symbol.symbol_id.lower() or
                query_lower in symbol.name.lower() or
                (symbol.dexpi_class and query_lower in symbol.dexpi_class.lower()) or
                (symbol.tags and any(query_lower in tag.lower() for tag in symbol.tags))
            ):
                results.append(symbol)

        return results

    def get_statistics(self) -> Dict:
        """Get statistics about the symbol library."""
        stats = {
            "total": len(self._symbols),
            "by_category": {},
            "by_source": {},
            "with_dexpi_class": 0,
            "unique_to_source": 0
        }

        for symbol in self._symbols.values():
            # Category stats
            cat_name = symbol.category.value
            stats["by_category"][cat_name] = stats["by_category"].get(cat_name, 0) + 1

            # Source stats
            src_name = symbol.source.value
            stats["by_source"][src_name] = stats["by_source"].get(src_name, 0) + 1

            # Other stats
            if symbol.dexpi_class:
                stats["with_dexpi_class"] += 1
            if symbol.is_unique_to_source:
                stats["unique_to_source"] += 1

        return stats

    def get_symbol_path(self, symbol_id: str) -> Optional[Path]:
        """
        Get full path to symbol SVG file.

        Args:
            symbol_id: Symbol ID (e.g., PP001A)

        Returns:
            Path to SVG file if found, None otherwise
        """
        # Get symbol info
        symbol = self.get_symbol(symbol_id)
        if symbol and symbol.file_path:
            # Try registered file path first
            full_path = self.assets_dir / symbol.file_path
            if full_path.exists():
                return full_path

        # Try common locations
        alternatives = [
            self.assets_dir / "DISCDEXPI" / f"{symbol_id}.svg",
            self.assets_dir / "NOAKADEXPI" / f"{symbol_id}.svg",
            self.assets_dir / "DISCDEXPI" / "Detail" / f"{symbol_id}.svg",
            self.assets_dir / "NOAKADEXPI" / "Detail" / f"{symbol_id}.svg",
            self.assets_dir / "DISCDEXPI" / "Origo" / f"{symbol_id}.svg",
            self.assets_dir / "NOAKADEXPI" / "Origo" / f"{symbol_id}.svg",
        ]

        for alt_path in alternatives:
            if alt_path.exists():
                logger.debug(f"Found symbol file for {symbol_id} at {alt_path}")
                return alt_path

        logger.warning(f"Could not find symbol file for {symbol_id}")
        return None

    def export_mapping(self, output_path: Optional[Path] = None) -> Dict:
        """Export symbol mappings for external tools."""
        mapping = {
            "version": "2.0",
            "symbols": {},
            "dexpi_mappings": self._dexpi_map,
            "statistics": self.get_statistics()
        }

        for symbol_id, symbol in self._symbols.items():
            mapping["symbols"][symbol_id] = {
                "name": symbol.name,
                "category": symbol.category.value,
                "dexpi_class": symbol.dexpi_class,
                "source": symbol.source.value,
                "file_path": symbol.file_path
            }

        if output_path:
            with open(output_path, 'w') as f:
                json.dump(mapping, f, indent=2)
            logger.info(f"Exported symbol mapping to {output_path}")

        return mapping


# Singleton instance for global access
_registry: Optional[SymbolRegistry] = None


def get_registry() -> SymbolRegistry:
    """Get the global symbol registry."""
    global _registry
    if _registry is None:
        _registry = SymbolRegistry()
    return _registry