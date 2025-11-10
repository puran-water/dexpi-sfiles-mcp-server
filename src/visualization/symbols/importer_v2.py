#!/usr/bin/env python3
"""
NOAKADEXPI Symbol Importer V2
Downloads actual symbols from NOAKADEXPI repository
"""

import logging
import requests
from pathlib import Path
from typing import List, Dict
import json
from catalog import SymbolCatalog, SymbolMetadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NOAKADEXPIImporter:
    """Import symbols from NOAKADEXPI library."""

    # GitHub repository information
    REPO_OWNER = "equinor"
    REPO_NAME = "NOAKADEXPI"
    BASE_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main"

    # Priority symbols for Phase 1 - Using actual NOAKADEXPI symbols
    # Symbol prefixes: PP=Pumps, PV=Valves, PT=Tanks, PE=Equipment,
    # PF=Filters, PS=Separators, PD=Dryers, PA=Actuators
    PRIORITY_SYMBOLS = {
        # Pumps (PP prefix) - 10 symbols
        "PP001A": {
            "name": "Centrifugal Pump",
            "path": "Symbols/PP001A.svg",
            "dexpi_class": "CentrifugalPump",
            "category": "Pumps"
        },
        "PP002A": {
            "name": "Centrifugal Pump (Vertical)",
            "path": "Symbols/PP002A.svg",
            "dexpi_class": "CentrifugalPump",
            "category": "Pumps",
            "variants": ["vertical"]
        },
        "PP003A": {
            "name": "Rotary Pump",
            "path": "Symbols/PP003A.svg",
            "dexpi_class": "RotaryPump",
            "category": "Pumps"
        },
        "PP004A": {
            "name": "Reciprocating Pump",
            "path": "Symbols/PP004A.svg",
            "dexpi_class": "ReciprocatingPump",
            "category": "Pumps"
        },
        "PP005A": {
            "name": "Diaphragm Pump",
            "path": "Symbols/PP005A.svg",
            "dexpi_class": "ReciprocatingPump",
            "category": "Pumps",
            "variants": ["diaphragm"]
        },
        "PP006A": {
            "name": "Screw Pump",
            "path": "Symbols/PP006A.svg",
            "dexpi_class": "RotaryPump",
            "category": "Pumps",
            "variants": ["screw"]
        },
        "PP007A": {
            "name": "Gear Pump",
            "path": "Symbols/PP007A.svg",
            "dexpi_class": "RotaryPump",
            "category": "Pumps",
            "variants": ["gear"]
        },
        "PP008A": {
            "name": "Submersible Pump",
            "path": "Symbols/PP008A.svg",
            "dexpi_class": "CentrifugalPump",
            "category": "Pumps",
            "variants": ["submersible"]
        },
        "PP009A": {
            "name": "Turbine Pump",
            "path": "Symbols/PP009A.svg",
            "dexpi_class": "CentrifugalPump",
            "category": "Pumps",
            "variants": ["turbine"]
        },
        "PP010A": {
            "name": "Progressive Cavity Pump",
            "path": "Symbols/PP010A.svg",
            "dexpi_class": "RotaryPump",
            "category": "Pumps",
            "variants": ["progressive_cavity"]
        },

        # Valves (PV prefix) - 10 symbols
        "PV001A": {
            "name": "Gate Valve",
            "path": "Symbols/PV001A.svg",
            "dexpi_class": "GateValve",
            "category": "Valves"
        },
        "PV002A": {
            "name": "Ball Valve",
            "path": "Symbols/PV002A.svg",
            "dexpi_class": "BallValve",
            "category": "Valves"
        },
        "PV003A": {
            "name": "Butterfly Valve",
            "path": "Symbols/PV003A.svg",
            "dexpi_class": "ButterflyValve",
            "category": "Valves"
        },
        "PV004A": {
            "name": "Check Valve",
            "path": "Symbols/PV004A.svg",
            "dexpi_class": "CheckValve",
            "category": "Valves"
        },
        "PV005A": {
            "name": "Globe Valve",
            "path": "Symbols/PV005A.svg",
            "dexpi_class": "GlobeValve",
            "category": "Valves"
        },
        "PV007A": {
            "name": "Plug Valve",
            "path": "Symbols/PV007A.svg",
            "dexpi_class": "PlugValve",
            "category": "Valves"
        },
        "PV008A": {
            "name": "Needle Valve",
            "path": "Symbols/PV008A.svg",
            "dexpi_class": "NeedleValve",
            "category": "Valves"
        },
        "PV009A": {
            "name": "Diaphragm Valve",
            "path": "Symbols/PV009A.svg",
            "dexpi_class": "CustomOperatedValve",
            "category": "Valves",
            "variants": ["diaphragm"]
        },
        "PV010A": {
            "name": "Safety Valve",
            "path": "Symbols/PV010A.svg",
            "dexpi_class": "SafetyValveOrFitting",
            "category": "Valves"
        },
        "PV011A": {
            "name": "Control Valve",
            "path": "Symbols/PV011A.svg",
            "dexpi_class": "OperatedValve",
            "category": "Valves"
        },

        # Tanks (PT prefix) - 5 symbols
        "PT001A": {
            "name": "Atmospheric Tank",
            "path": "Symbols/PT001A.svg",
            "dexpi_class": "Tank",
            "category": "Tanks"
        },
        "PT002A": {
            "name": "Pressure Tank",
            "path": "Symbols/PT002A.svg",
            "dexpi_class": "PressureVessel",
            "category": "Tanks"
        },
        "PT003A": {
            "name": "Cone Bottom Tank",
            "path": "Symbols/PT003A.svg",
            "dexpi_class": "Tank",
            "category": "Tanks",
            "variants": ["cone_bottom"]
        },
        "PT004A": {
            "name": "Horizontal Tank",
            "path": "Symbols/PT004A.svg",
            "dexpi_class": "Tank",
            "category": "Tanks",
            "variants": ["horizontal"]
        },
        "PT005A": {
            "name": "Silo",
            "path": "Symbols/PT005A.svg",
            "dexpi_class": "Silo",
            "category": "Tanks"
        },

        # Equipment (PE prefix) - Mixers, Blowers, Heat Exchangers - 8 symbols
        "PE001A": {
            "name": "Top Entry Mixer",
            "path": "Symbols/PE001A.svg",
            "dexpi_class": "Agitator",
            "category": "Equipment",
            "variants": ["top_entry"]
        },
        "PE002A": {
            "name": "Side Entry Mixer",
            "path": "Symbols/PE002A.svg",
            "dexpi_class": "Agitator",
            "category": "Equipment",
            "variants": ["side_entry"]
        },
        "PE003A": {
            "name": "Static Mixer",
            "path": "Symbols/PE003A.svg",
            "dexpi_class": "StaticMixer",
            "category": "Equipment"
        },
        "PE010A": {
            "name": "Centrifugal Blower",
            "path": "Symbols/PE010A.svg",
            "dexpi_class": "CentrifugalBlower",
            "category": "Equipment"
        },
        "PE011A": {
            "name": "Rotary Blower",
            "path": "Symbols/PE011A.svg",
            "dexpi_class": "RotaryBlower",
            "category": "Equipment"
        },
        "PE020A": {
            "name": "Shell and Tube Heat Exchanger",
            "path": "Symbols/PE020A.svg",
            "dexpi_class": "TubularHeatExchanger",
            "category": "Equipment"
        },
        "PE021A": {
            "name": "Plate Heat Exchanger",
            "path": "Symbols/PE021A.svg",
            "dexpi_class": "PlateHeatExchanger",
            "category": "Equipment"
        },
        "PE022A": {
            "name": "Air Cooler",
            "path": "Symbols/PE022A.svg",
            "dexpi_class": "HeatExchanger",
            "category": "Equipment",
            "variants": ["air_cooled"]
        },

        # Filters (PF prefix) - 5 symbols
        "PF001A": {
            "name": "Cartridge Filter",
            "path": "Symbols/PF001A.svg",
            "dexpi_class": "LiquidFilter",
            "category": "Filters",
            "variants": ["cartridge"]
        },
        "PF002A": {
            "name": "Bag Filter",
            "path": "Symbols/PF002A.svg",
            "dexpi_class": "LiquidFilter",
            "category": "Filters",
            "variants": ["bag"]
        },
        "PF003A": {
            "name": "Sand Filter",
            "path": "Symbols/PF003A.svg",
            "dexpi_class": "LiquidFilter",
            "category": "Filters",
            "variants": ["sand"]
        },
        "PF004A": {
            "name": "Plate Filter",
            "path": "Symbols/PF004A.svg",
            "dexpi_class": "Filter",
            "category": "Filters",
            "variants": ["plate"]
        },
        "PF005A": {
            "name": "Strainer",
            "path": "Symbols/PF005A.svg",
            "dexpi_class": "Filter",
            "category": "Filters",
            "variants": ["strainer"]
        },

        # Separators (PS prefix) - 2 symbols
        "PS001A": {
            "name": "Circular Clarifier",
            "path": "Symbols/PS001A.svg",
            "dexpi_class": "Separator",
            "category": "Separators",
            "variants": ["circular"]
        },
        "PS003A": {
            "name": "Centrifuge",
            "path": "Symbols/PS003A.svg",
            "dexpi_class": "Centrifuge",
            "category": "Separators"
        }
    }

    def __init__(self, output_dir: Path = None):
        """
        Initialize importer.

        Args:
            output_dir: Directory to save symbols
        """
        if output_dir is None:
            output_dir = Path(__file__).parent / "assets" / "NOAKADEXPI"

        self.output_dir = output_dir
        self.catalog = SymbolCatalog(output_dir.parent)

    def download_symbol(self, symbol_id: str, info: Dict) -> bool:
        """
        Download single symbol from GitHub.

        Args:
            symbol_id: Symbol ID
            info: Symbol information

        Returns:
            True if successful
        """
        try:
            # Build URL
            url = f"{self.BASE_URL}/{info['path']}"

            logger.info(f"Downloading {symbol_id} from {url}")

            # Download SVG
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # Save to file
            category_dir = self.output_dir / info['category']
            category_dir.mkdir(parents=True, exist_ok=True)

            svg_path = category_dir / f"{symbol_id}.svg"
            svg_path.write_bytes(response.content)

            logger.info(f"Downloaded {symbol_id}: {info['name']}")

            # Add to catalog
            self.catalog.add_symbol(
                symbol_id=symbol_id,
                name=info['name'],
                dexpi_class=info['dexpi_class'],
                category=info['category'],
                svg_path=svg_path,
                variants=info.get('variants', []),
                tags=info.get('tags', [])
            )

            return True

        except Exception as e:
            logger.error(f"Failed to download {symbol_id}: {e}")
            return False

    def import_priority_symbols(self, include_variations: bool = False) -> Dict:
        """
        Import all priority symbols.

        Args:
            include_variations: Also download Detail and Origo variations

        Returns:
            Import statistics
        """
        stats = {
            "total": len(self.PRIORITY_SYMBOLS),
            "success": 0,
            "failed": 0,
            "symbols": []
        }

        # Count variations if requested
        if include_variations:
            stats["total"] *= 3  # Main + Detail + Origo

        logger.info(f"Starting import of {stats['total']} symbols")

        for symbol_id, info in self.PRIORITY_SYMBOLS.items():
            # Download main symbol
            if self.download_symbol(symbol_id, info):
                stats["success"] += 1
                stats["symbols"].append(symbol_id)
            else:
                stats["failed"] += 1

            # Download variations if requested
            if include_variations:
                # Detail variation
                detail_info = info.copy()
                detail_info["path"] = f"Symbols/Detail/{symbol_id}_Detail.svg"
                detail_info["name"] = f"{info['name']} (Detail)"
                if self.download_symbol(f"{symbol_id}_Detail", detail_info):
                    stats["success"] += 1
                    stats["symbols"].append(f"{symbol_id}_Detail")
                else:
                    stats["failed"] += 1

                # Origo variation
                origo_info = info.copy()
                origo_info["path"] = f"Symbols/Origo/{symbol_id}_Origo.svg"
                origo_info["name"] = f"{info['name']} (Origo)"
                if self.download_symbol(f"{symbol_id}_Origo", origo_info):
                    stats["success"] += 1
                    stats["symbols"].append(f"{symbol_id}_Origo")
                else:
                    stats["failed"] += 1

        # Save catalog
        self.catalog.save_catalog()

        logger.info(f"Import complete: {stats['success']} success, {stats['failed']} failed")

        return stats

    def create_symbol_index(self) -> None:
        """Create symbol index HTML for browsing."""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>NOAKADEXPI Symbol Library</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        .stats { background: #f5f5f5; padding: 15px; margin: 20px 0; border-radius: 5px; }
        .category { margin: 20px 0; }
        .category h2 { color: #666; border-bottom: 2px solid #ddd; padding-bottom: 10px; }
        .symbols { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; }
        .symbol { border: 1px solid #ddd; padding: 10px; text-align: center; background: white; border-radius: 5px; }
        .symbol:hover { box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .symbol img { max-width: 150px; max-height: 150px; }
        .symbol .name { font-weight: bold; margin-top: 10px; }
        .symbol .id { color: #666; font-size: 0.9em; }
        .symbol .class { color: #999; font-size: 0.8em; }
    </style>
</head>
<body>
    <h1>NOAKADEXPI Symbol Library - Priority Symbols</h1>
"""

        # Add statistics
        stats = self.catalog.get_statistics()
        html += f"""
    <div class="stats">
        <h3>Library Statistics</h3>
        <p>Total Symbols: {stats['total_symbols']}</p>
"""
        for cat, count in stats['categories'].items():
            html += f"        <p>{cat}: {count} symbols</p>\n"
        html += """    </div>
"""

        # Group symbols by category
        categories = {}
        for symbol in self.catalog.symbols.values():
            if symbol.category not in categories:
                categories[symbol.category] = []
            categories[symbol.category].append(symbol)

        # Generate HTML for each category
        for category, symbols in sorted(categories.items()):
            html += f"""
    <div class="category">
        <h2>{category} ({len(symbols)} symbols)</h2>
        <div class="symbols">
"""
            for symbol in sorted(symbols, key=lambda s: s.id):
                svg_path = self.output_dir / symbol.category / f"{symbol.id}.svg"
                rel_path = svg_path.relative_to(self.output_dir.parent)
                html += f"""
            <div class="symbol">
                <img src="{rel_path}" alt="{symbol.name}"/>
                <div class="name">{symbol.name}</div>
                <div class="id">{symbol.id}</div>
                <div class="class">{symbol.dexpi_class}</div>
            </div>
"""
            html += """
        </div>
    </div>
"""

        html += """
</body>
</html>
"""

        # Save index file
        index_path = self.output_dir.parent / "symbol_index.html"
        index_path.write_text(html)
        logger.info(f"Created symbol index at {index_path}")


def main():
    """Main import function."""
    importer = NOAKADEXPIImporter()

    # Import priority symbols
    stats = importer.import_priority_symbols()

    # Create index
    importer.create_symbol_index()

    # Print statistics
    print("\n=== Import Statistics ===")
    print(f"Total symbols: {stats['total']}")
    print(f"Successfully imported: {stats['success']}")
    print(f"Failed: {stats['failed']}")

    if stats['success'] > 0:
        print(f"\nImported symbols saved to: {importer.output_dir}")
        print(f"Catalog saved to: {importer.catalog.catalog_file}")

    # Print catalog statistics
    cat_stats = importer.catalog.get_statistics()
    print("\n=== Catalog Statistics ===")
    print(f"Total symbols in catalog: {cat_stats['total_symbols']}")
    print("By category:")
    for cat, count in cat_stats['categories'].items():
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()