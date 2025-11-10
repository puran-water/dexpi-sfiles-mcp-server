#!/usr/bin/env python3
"""
NOAKADEXPI Symbol Importer
Downloads and imports priority symbols from NOAKADEXPI library
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

    # Priority symbols for Phase 1 (30-40 symbols)
    # Using actual NOAKADEXPI symbol files from Symbols directory
    # Naming convention: PP=Pumps, PV=Valves, PT=Tanks, PE=Equipment, PF=Filters, PS=Separators
    PRIORITY_SYMBOLS = {
        # Tanks/Vessels (PT prefix)
        "PT001A": {
            "name": "Atmospheric Tank",
            "path": "Symbols/PT001A.svg",
            "dexpi_class": "Tank",
            "category": "Equipment"
        },
        "PT002A": {
            "name": "Pressure Vessel",
            "path": "Symbols/PT002A.svg",
            "dexpi_class": "PressureVessel",
            "category": "Equipment"
        },
        "TK-01-03": {
            "name": "Cone Bottom Tank",
            "path": "Equipment/Tanks/TK-01-03.svg",
            "dexpi_class": "Tank",
            "category": "Equipment"
        },
        "TK-01-04": {
            "name": "Horizontal Tank",
            "path": "Equipment/Tanks/TK-01-04.svg",
            "dexpi_class": "Tank",
            "category": "Equipment"
        },
        "TK-01-05": {
            "name": "Silo",
            "path": "Equipment/Tanks/TK-01-05.svg",
            "dexpi_class": "Silo",
            "category": "Equipment"
        },

        # Pumps (10)
        "P-01-01": {
            "name": "Centrifugal Pump",
            "path": "Equipment/Pumps/P-01-01.svg",
            "dexpi_class": "CentrifugalPump",
            "category": "Equipment"
        },
        "P-01-02": {
            "name": "Vertical Centrifugal Pump",
            "path": "Equipment/Pumps/P-01-02.svg",
            "dexpi_class": "CentrifugalPump",
            "category": "Equipment",
            "variants": ["vertical"]
        },
        "P-01-03": {
            "name": "Rotary Pump",
            "path": "Equipment/Pumps/P-01-03.svg",
            "dexpi_class": "RotaryPump",
            "category": "Equipment"
        },
        "P-01-04": {
            "name": "Reciprocating Pump",
            "path": "Equipment/Pumps/P-01-04.svg",
            "dexpi_class": "ReciprocatingPump",
            "category": "Equipment"
        },
        "P-01-05": {
            "name": "Diaphragm Pump",
            "path": "Equipment/Pumps/P-01-05.svg",
            "dexpi_class": "ReciprocatingPump",
            "category": "Equipment",
            "variants": ["diaphragm"]
        },
        "P-01-06": {
            "name": "Screw Pump",
            "path": "Equipment/Pumps/P-01-06.svg",
            "dexpi_class": "RotaryPump",
            "category": "Equipment",
            "variants": ["screw"]
        },
        "P-01-07": {
            "name": "Gear Pump",
            "path": "Equipment/Pumps/P-01-07.svg",
            "dexpi_class": "RotaryPump",
            "category": "Equipment",
            "variants": ["gear"]
        },
        "P-01-08": {
            "name": "Submersible Pump",
            "path": "Equipment/Pumps/P-01-08.svg",
            "dexpi_class": "CentrifugalPump",
            "category": "Equipment",
            "variants": ["submersible"]
        },
        "P-01-09": {
            "name": "Turbine Pump",
            "path": "Equipment/Pumps/P-01-09.svg",
            "dexpi_class": "CentrifugalPump",
            "category": "Equipment",
            "variants": ["turbine"]
        },
        "P-01-10": {
            "name": "Progressive Cavity Pump",
            "path": "Equipment/Pumps/P-01-10.svg",
            "dexpi_class": "RotaryPump",
            "category": "Equipment",
            "variants": ["progressive_cavity"]
        },

        # Valves (10)
        "V-01-01": {
            "name": "Gate Valve",
            "path": "Valves/V-01-01.svg",
            "dexpi_class": "GateValve",
            "category": "Valves"
        },
        "V-01-02": {
            "name": "Ball Valve",
            "path": "Valves/V-01-02.svg",
            "dexpi_class": "BallValve",
            "category": "Valves"
        },
        "V-01-03": {
            "name": "Butterfly Valve",
            "path": "Valves/V-01-03.svg",
            "dexpi_class": "ButterflyValve",
            "category": "Valves"
        },
        "V-01-04": {
            "name": "Check Valve",
            "path": "Valves/V-01-04.svg",
            "dexpi_class": "CheckValve",
            "category": "Valves"
        },
        "V-01-05": {
            "name": "Globe Valve",
            "path": "Valves/V-01-05.svg",
            "dexpi_class": "GlobeValve",
            "category": "Valves"
        },
        "V-01-06": {
            "name": "Plug Valve",
            "path": "Valves/V-01-06.svg",
            "dexpi_class": "PlugValve",
            "category": "Valves"
        },
        "V-01-07": {
            "name": "Needle Valve",
            "path": "Valves/V-01-07.svg",
            "dexpi_class": "NeedleValve",
            "category": "Valves"
        },
        "V-01-08": {
            "name": "Diaphragm Valve",
            "path": "Valves/V-01-08.svg",
            "dexpi_class": "CustomOperatedValve",
            "category": "Valves",
            "variants": ["diaphragm"]
        },
        "V-01-09": {
            "name": "Safety Valve",
            "path": "Valves/V-01-09.svg",
            "dexpi_class": "SafetyValveOrFitting",
            "category": "Valves"
        },
        "V-01-10": {
            "name": "Control Valve",
            "path": "Valves/V-01-10.svg",
            "dexpi_class": "OperatedValve",
            "category": "Valves"
        },

        # Mixers (3)
        "MX-01-01": {
            "name": "Top Entry Mixer",
            "path": "Equipment/Mixers/MX-01-01.svg",
            "dexpi_class": "Agitator",
            "category": "Equipment",
            "variants": ["top_entry"]
        },
        "MX-01-02": {
            "name": "Side Entry Mixer",
            "path": "Equipment/Mixers/MX-01-02.svg",
            "dexpi_class": "Agitator",
            "category": "Equipment",
            "variants": ["side_entry"]
        },
        "MX-01-03": {
            "name": "Static Mixer",
            "path": "Equipment/Mixers/MX-01-03.svg",
            "dexpi_class": "StaticMixer",
            "category": "Equipment"
        },

        # Filters (5)
        "F-01-01": {
            "name": "Cartridge Filter",
            "path": "Equipment/Filters/F-01-01.svg",
            "dexpi_class": "LiquidFilter",
            "category": "Equipment",
            "variants": ["cartridge"]
        },
        "F-01-02": {
            "name": "Bag Filter",
            "path": "Equipment/Filters/F-01-02.svg",
            "dexpi_class": "LiquidFilter",
            "category": "Equipment",
            "variants": ["bag"]
        },
        "F-01-03": {
            "name": "Sand Filter",
            "path": "Equipment/Filters/F-01-03.svg",
            "dexpi_class": "LiquidFilter",
            "category": "Equipment",
            "variants": ["sand"]
        },
        "F-01-04": {
            "name": "Plate Filter",
            "path": "Equipment/Filters/F-01-04.svg",
            "dexpi_class": "Filter",
            "category": "Equipment",
            "variants": ["plate"]
        },
        "F-01-05": {
            "name": "Strainer",
            "path": "Equipment/Filters/F-01-05.svg",
            "dexpi_class": "Filter",
            "category": "Equipment",
            "variants": ["strainer"]
        },

        # Blowers (3)
        "BL-01-01": {
            "name": "Centrifugal Blower",
            "path": "Equipment/Blowers/BL-01-01.svg",
            "dexpi_class": "CentrifugalBlower",
            "category": "Equipment"
        },
        "BL-01-02": {
            "name": "Rotary Blower",
            "path": "Equipment/Blowers/BL-01-02.svg",
            "dexpi_class": "RotaryBlower",
            "category": "Equipment"
        },
        "BL-01-03": {
            "name": "Axial Blower",
            "path": "Equipment/Blowers/BL-01-03.svg",
            "dexpi_class": "AxialBlower",
            "category": "Equipment"
        },

        # Clarifiers (2)
        "CL-01-01": {
            "name": "Circular Clarifier",
            "path": "Equipment/Separators/CL-01-01.svg",
            "dexpi_class": "Separator",
            "category": "Equipment",
            "variants": ["circular"]
        },
        "CL-01-02": {
            "name": "Centrifuge",
            "path": "Equipment/Separators/CL-01-02.svg",
            "dexpi_class": "Centrifuge",
            "category": "Equipment"
        },

        # Heat Exchangers (3)
        "HX-01-01": {
            "name": "Shell and Tube Heat Exchanger",
            "path": "Equipment/HeatExchangers/HX-01-01.svg",
            "dexpi_class": "TubularHeatExchanger",
            "category": "Equipment"
        },
        "HX-01-02": {
            "name": "Plate Heat Exchanger",
            "path": "Equipment/HeatExchangers/HX-01-02.svg",
            "dexpi_class": "PlateHeatExchanger",
            "category": "Equipment"
        },
        "HX-01-03": {
            "name": "Air Cooler",
            "path": "Equipment/HeatExchangers/HX-01-03.svg",
            "dexpi_class": "HeatExchanger",
            "category": "Equipment",
            "variants": ["air_cooled"]
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

    def import_priority_symbols(self) -> Dict:
        """
        Import all priority symbols.

        Returns:
            Import statistics
        """
        stats = {
            "total": len(self.PRIORITY_SYMBOLS),
            "success": 0,
            "failed": 0,
            "symbols": []
        }

        logger.info(f"Starting import of {stats['total']} priority symbols")

        for symbol_id, info in self.PRIORITY_SYMBOLS.items():
            if self.download_symbol(symbol_id, info):
                stats["success"] += 1
                stats["symbols"].append(symbol_id)
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
        .category { margin: 20px 0; }
        .category h2 { color: #666; border-bottom: 2px solid #ddd; padding-bottom: 10px; }
        .symbols { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; }
        .symbol { border: 1px solid #ddd; padding: 10px; text-align: center; }
        .symbol img { max-width: 150px; max-height: 150px; }
        .symbol .name { font-weight: bold; margin-top: 10px; }
        .symbol .id { color: #666; font-size: 0.9em; }
        .symbol .class { color: #999; font-size: 0.8em; }
    </style>
</head>
<body>
    <h1>NOAKADEXPI Symbol Library</h1>
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
                svg_path = Path(symbol.svg_path)
                html += f"""
            <div class="symbol">
                <img src="{svg_path}" alt="{symbol.name}"/>
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