"""
Symbol Catalog and Registry
Manages DEXPI symbol library with metadata extraction

DEPRECATION NOTICE (Week 8):
- DEXPI_CLASS_MAPPING: Use src.core.symbols.SymbolRegistry.get_by_dexpi_class() instead
- extract_svg_metadata(): Use src.core.svg_parser.extract_svg_metadata() instead
- SymbolCatalog: Use src.core.symbols.SymbolRegistry for authoritative symbol lookups

The unified symbol data is in merged_catalog.json, accessed via SymbolRegistry.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
import logging
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class Point:
    """2D point."""
    x: float
    y: float


@dataclass
class BoundingBox:
    """Bounding box for symbol."""
    x: float
    y: float
    width: float
    height: float


@dataclass
class Size:
    """Size specification."""
    width: float
    height: float


@dataclass
class PortSpec:
    """Connection port specification."""
    id: str
    position: Point
    direction: str  # N, S, E, W, NE, NW, SE, SW
    type: str  # inlet, outlet, auxiliary
    flow_direction: Optional[str] = None  # in, out, bidirectional


@dataclass
class SymbolMetadata:
    """Complete metadata for a symbol."""
    id: str                    # e.g., "P-01-01"
    name: str                  # e.g., "Centrifugal Pump"
    dexpi_class: str          # e.g., "CentrifugalPump"
    category: str             # e.g., "Equipment"
    svg_path: str            # Path to SVG file

    # Extracted metadata
    bounding_box: BoundingBox
    ports: List[PortSpec]
    anchor_point: Point       # Rotation center

    # Rendering hints
    default_size: Size
    scalable: bool = True
    rotatable: bool = True

    # Variants
    variants: List[str] = None  # e.g., ["vertical", "horizontal"]
    tags: List[str] = None      # Additional tags for searching

    # File info
    file_hash: str = None       # MD5 hash for change detection


class SymbolCatalog:
    """Symbol catalog management."""

    # DEPRECATED: Use src.core.symbols.SymbolRegistry.get_by_dexpi_class() instead.
    # This mapping is maintained for backward compatibility only.
    # The authoritative DEXPI class to symbol mappings are in merged_catalog.json.
    # See: src/core/symbols.py SymbolRegistry for the recommended API.
    DEXPI_CLASS_MAPPING = {
        # Pumps
        "CentrifugalPump": "P-01-01",
        "RotaryPump": "P-01-02",
        "ReciprocatingPump": "P-01-03",
        "VerticalPump": "P-01-04",

        # Tanks
        "Tank": "TK-01-01",
        "PressureVessel": "TK-01-02",
        "Silo": "TK-01-03",

        # Valves
        "GateValve": "V-01-01",
        "BallValve": "V-01-02",
        "ButterflyValve": "V-01-03",
        "CheckValve": "V-01-04",
        "GlobeValve": "V-01-05",
        "PlugValve": "V-01-06",

        # Mixers
        "Agitator": "MX-01-01",
        "StaticMixer": "MX-01-02",
        "Mixer": "MX-01-01",

        # Filters
        "Filter": "F-01-01",
        "LiquidFilter": "F-01-02",
        "GasFilter": "F-01-03",

        # Blowers
        "CentrifugalBlower": "BL-01-01",
        "RotaryBlower": "BL-01-02",
        "Blower": "BL-01-01",

        # Heat Exchangers
        "HeatExchanger": "HX-01-01",
        "TubularHeatExchanger": "HX-01-02",
        "PlateHeatExchanger": "HX-01-03",

        # Clarifiers
        "Separator": "CL-01-01",
        "Centrifuge": "CL-01-02",

        # Instrumentation
        "ProcessSignalGeneratingSystem": "I-01-01",
        "ProcessControlFunction": "I-01-02",
        "Transmitter": "I-01-03",
        "FlowDetector": "FIT-01",
        "LevelDetector": "LIT-01",
        "TemperatureDetector": "TIT-01",
        "PressureDetector": "PIT-01",
    }

    def __init__(self, base_path: Path = None):
        """
        Initialize catalog.

        Args:
            base_path: Base path for symbol library
        """
        if base_path is None:
            base_path = Path(__file__).parent / "assets"

        self.base_path = base_path
        self.catalog_file = base_path / "catalog.json"
        self.symbols: Dict[str, SymbolMetadata] = {}

        # Load existing catalog if exists
        if self.catalog_file.exists():
            self.load_catalog()

    def load_catalog(self) -> None:
        """Load catalog from JSON file."""
        try:
            with open(self.catalog_file) as f:
                data = json.load(f)

            for item in data.get("symbols", []):
                # Reconstruct dataclass objects
                item["bounding_box"] = BoundingBox(**item["bounding_box"])
                item["anchor_point"] = Point(**item["anchor_point"])
                item["default_size"] = Size(**item["default_size"])

                ports = []
                for port_data in item.get("ports", []):
                    port_data["position"] = Point(**port_data["position"])
                    ports.append(PortSpec(**port_data))
                item["ports"] = ports

                symbol = SymbolMetadata(**item)
                self.symbols[symbol.id] = symbol

            logger.info(f"Loaded {len(self.symbols)} symbols from catalog")

        except Exception as e:
            logger.error(f"Failed to load catalog: {e}")

    def save_catalog(self) -> None:
        """Save catalog to JSON file."""
        try:
            # Convert to JSON-serializable format
            data = {
                "symbols": [],
                "version": "1.0",
                "count": len(self.symbols)
            }

            for symbol in self.symbols.values():
                # Convert dataclasses to dicts
                symbol_dict = asdict(symbol)
                data["symbols"].append(symbol_dict)

            # Save to file
            self.catalog_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.catalog_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved {len(self.symbols)} symbols to catalog")

        except Exception as e:
            logger.error(f"Failed to save catalog: {e}")

    def extract_svg_metadata(self, svg_path: Path) -> Dict[str, any]:
        """
        Extract metadata from SVG file.

        Args:
            svg_path: Path to SVG file

        Returns:
            Extracted metadata
        """
        try:
            # Parse SVG
            tree = ET.parse(svg_path)
            root = tree.getroot()

            # Get SVG namespace
            ns = {'svg': 'http://www.w3.org/2000/svg'}

            # Extract viewBox or dimensions
            viewbox = root.get('viewBox')
            if viewbox:
                x, y, width, height = map(float, viewbox.split())
            else:
                width = float(root.get('width', '100').replace('px', ''))
                height = float(root.get('height', '100').replace('px', ''))
                x, y = 0, 0

            bbox = BoundingBox(x, y, width, height)

            # Find anchor point (center by default)
            anchor = Point(width / 2, height / 2)

            # Look for marked anchor point
            anchor_elem = root.find(".//svg:circle[@id='anchor']", ns)
            if anchor_elem is not None:
                anchor = Point(
                    float(anchor_elem.get('cx', width / 2)),
                    float(anchor_elem.get('cy', height / 2))
                )

            # Extract ports (connection points)
            ports = []
            port_elems = root.findall(".//svg:circle[@class='port']", ns)
            for i, port_elem in enumerate(port_elems):
                cx = float(port_elem.get('cx', 0))
                cy = float(port_elem.get('cy', 0))

                # Determine direction based on position
                direction = self._determine_port_direction(cx, cy, width, height)

                # Get port type from data attribute or default
                port_type = port_elem.get('data-type', 'inlet' if i == 0 else 'outlet')

                ports.append(PortSpec(
                    id=port_elem.get('id', f'port_{i}'),
                    position=Point(cx, cy),
                    direction=direction,
                    type=port_type
                ))

            # If no ports found, add default ones
            if not ports:
                # Add default inlet/outlet ports for equipment
                if 'pump' in str(svg_path).lower():
                    ports = [
                        PortSpec('inlet', Point(0, height / 2), 'W', 'inlet'),
                        PortSpec('outlet', Point(width, height / 2), 'E', 'outlet')
                    ]
                elif 'tank' in str(svg_path).lower():
                    ports = [
                        PortSpec('inlet', Point(width / 2, 0), 'N', 'inlet'),
                        PortSpec('outlet', Point(width / 2, height), 'S', 'outlet'),
                        PortSpec('vent', Point(width / 2, 0), 'N', 'auxiliary')
                    ]

            # Calculate file hash
            file_hash = hashlib.md5(svg_path.read_bytes()).hexdigest()

            return {
                'bounding_box': bbox,
                'anchor_point': anchor,
                'ports': ports,
                'default_size': Size(width, height),
                'file_hash': file_hash
            }

        except Exception as e:
            logger.error(f"Failed to extract metadata from {svg_path}: {e}")
            # Return defaults
            return {
                'bounding_box': BoundingBox(0, 0, 100, 100),
                'anchor_point': Point(50, 50),
                'ports': [],
                'default_size': Size(100, 100),
                'file_hash': None
            }

    def _determine_port_direction(self, x: float, y: float, width: float, height: float) -> str:
        """Determine port direction based on position."""
        # Calculate relative position
        rel_x = x / width
        rel_y = y / height

        # Determine primary direction
        if rel_x < 0.2:
            return 'W'
        elif rel_x > 0.8:
            return 'E'
        elif rel_y < 0.2:
            return 'N'
        elif rel_y > 0.8:
            return 'S'
        else:
            # Corner cases
            if rel_x < 0.5 and rel_y < 0.5:
                return 'NW'
            elif rel_x > 0.5 and rel_y < 0.5:
                return 'NE'
            elif rel_x < 0.5 and rel_y > 0.5:
                return 'SW'
            else:
                return 'SE'

    def add_symbol(
        self,
        symbol_id: str,
        name: str,
        dexpi_class: str,
        category: str,
        svg_path: Path,
        **kwargs
    ) -> SymbolMetadata:
        """
        Add symbol to catalog.

        Args:
            symbol_id: Unique symbol ID
            name: Display name
            dexpi_class: DEXPI class name
            category: Category (Equipment, Valves, etc.)
            svg_path: Path to SVG file
            **kwargs: Additional metadata

        Returns:
            Created SymbolMetadata
        """
        # Extract metadata from SVG
        svg_metadata = self.extract_svg_metadata(svg_path)

        # Create symbol metadata
        symbol = SymbolMetadata(
            id=symbol_id,
            name=name,
            dexpi_class=dexpi_class,
            category=category,
            svg_path=str(svg_path.relative_to(self.base_path)),
            bounding_box=svg_metadata['bounding_box'],
            ports=svg_metadata['ports'],
            anchor_point=svg_metadata['anchor_point'],
            default_size=svg_metadata['default_size'],
            file_hash=svg_metadata['file_hash'],
            **kwargs
        )

        # Add to catalog
        self.symbols[symbol_id] = symbol
        logger.info(f"Added symbol {symbol_id}: {name}")

        return symbol

    def find_symbol_for_class(self, dexpi_class: str) -> Optional[SymbolMetadata]:
        """
        Find symbol for DEXPI class.

        Args:
            dexpi_class: DEXPI class name

        Returns:
            Symbol metadata or None
        """
        # First check direct mapping
        symbol_id = self.DEXPI_CLASS_MAPPING.get(dexpi_class)
        if symbol_id and symbol_id in self.symbols:
            return self.symbols[symbol_id]

        # Then search by dexpi_class field
        for symbol in self.symbols.values():
            if symbol.dexpi_class == dexpi_class:
                return symbol

        # Try fuzzy match
        for symbol in self.symbols.values():
            if dexpi_class.lower() in symbol.dexpi_class.lower():
                return symbol

        return None

    def search_symbols(
        self,
        query: str = None,
        category: str = None,
        tags: List[str] = None
    ) -> List[SymbolMetadata]:
        """
        Search symbols.

        Args:
            query: Search query
            category: Filter by category
            tags: Filter by tags

        Returns:
            List of matching symbols
        """
        results = []

        for symbol in self.symbols.values():
            # Category filter
            if category and symbol.category != category:
                continue

            # Tags filter
            if tags and symbol.tags:
                if not any(tag in symbol.tags for tag in tags):
                    continue

            # Query search
            if query:
                query_lower = query.lower()
                if not any([
                    query_lower in symbol.name.lower(),
                    query_lower in symbol.id.lower(),
                    query_lower in symbol.dexpi_class.lower()
                ]):
                    continue

            results.append(symbol)

        return results

    def get_categories(self) -> List[str]:
        """Get list of categories."""
        categories = set()
        for symbol in self.symbols.values():
            categories.add(symbol.category)
        return sorted(list(categories))

    def get_statistics(self) -> Dict:
        """Get catalog statistics."""
        stats = {
            "total_symbols": len(self.symbols),
            "categories": {}
        }

        for symbol in self.symbols.values():
            cat = symbol.category
            if cat not in stats["categories"]:
                stats["categories"][cat] = 0
            stats["categories"][cat] += 1

        return stats