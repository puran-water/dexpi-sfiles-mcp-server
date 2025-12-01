#!/usr/bin/env python3
"""
Extract geometry from all SVG files and update merged_catalog.json.

This script:
1. Iterates through all symbols in merged_catalog.json
2. Finds corresponding SVG files
3. Extracts bounding_box, anchor_point, ports from SVG using src/core/svg_parser
4. Updates merged_catalog.json with geometry data

NOTE: Uses the consolidated svg_parser module to avoid code duplication.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Optional

# Add project root to path for imports
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from src.core.svg_parser import extract_svg_metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_svg_for_symbol(symbol_id: str, source_file: str, assets_dir: Path) -> Optional[Path]:
    """Find the SVG file for a symbol."""
    # Try source_file first
    if source_file:
        svg_path = assets_dir / source_file
        if svg_path.exists():
            return svg_path

    # Try common locations
    search_paths = [
        assets_dir / "NOAKADEXPI" / f"{symbol_id}.svg",
        assets_dir / "DISCDEXPI" / f"{symbol_id}.svg",
        assets_dir / "NOAKADEXPI" / "Detail" / f"{symbol_id}.svg",
        assets_dir / "DISCDEXPI" / "Detail" / f"{symbol_id}.svg",
        assets_dir / "NOAKADEXPI" / "Origo" / f"{symbol_id}.svg",
        assets_dir / "DISCDEXPI" / "Origo" / f"{symbol_id}.svg",
    ]

    for path in search_paths:
        if path.exists():
            return path

    return None


def main():
    """Main entry point."""
    assets_dir = project_root / "src" / "visualization" / "symbols" / "assets"
    catalog_path = assets_dir / "merged_catalog.json"

    if not catalog_path.exists():
        logger.error(f"Catalog not found: {catalog_path}")
        return 1

    # Load catalog
    logger.info("Loading merged_catalog.json...")
    with open(catalog_path, 'r') as f:
        catalog = json.load(f)

    symbols = catalog.get("symbols", {})
    logger.info(f"Found {len(symbols)} symbols")

    # Process each symbol
    extracted = 0
    already_have = 0
    no_svg = 0
    failed = 0

    for symbol_id, data in symbols.items():
        # Skip if already has geometry
        if data.get("bounding_box"):
            already_have += 1
            continue

        # Find SVG file
        source_file = data.get("source_file", "")
        svg_path = find_svg_for_symbol(symbol_id, source_file, assets_dir)

        if not svg_path:
            no_svg += 1
            continue

        # Extract geometry using the consolidated svg_parser module
        metadata = extract_svg_metadata(svg_path, include_hash=True)
        if metadata:
            data["bounding_box"] = {
                "x": metadata.bounding_box.x,
                "y": metadata.bounding_box.y,
                "width": metadata.bounding_box.width,
                "height": metadata.bounding_box.height
            }
            data["anchor_point"] = {
                "x": metadata.anchor_point.x,
                "y": metadata.anchor_point.y
            }
            if metadata.ports:
                data["ports"] = [
                    {
                        "id": p.id,
                        "position": {"x": p.x, "y": p.y},
                        "direction": p.direction,
                        "type": p.type,
                        "flow_direction": p.flow_direction
                    }
                    for p in metadata.ports
                ]
            data["scalable"] = metadata.scalable
            data["rotatable"] = metadata.rotatable
            if metadata.file_hash:
                # Update file hash if not present in provenance
                if "provenance" not in data:
                    data["provenance"] = {}
                data["provenance"]["file_hash"] = metadata.file_hash
            extracted += 1
        else:
            failed += 1

    # Save updated catalog
    logger.info("Saving updated catalog...")
    with open(catalog_path, 'w') as f:
        json.dump(catalog, f, indent=2)

    # Report results
    logger.info(f"\nExtraction complete:")
    logger.info(f"  Already had geometry: {already_have}")
    logger.info(f"  Newly extracted: {extracted}")
    logger.info(f"  No SVG found: {no_svg}")
    logger.info(f"  Failed to extract: {failed}")
    logger.info(f"  Total with geometry: {already_have + extracted}")

    # Count by category
    logger.info(f"\nGeometry coverage by category:")
    category_counts = {}
    for symbol_id, data in symbols.items():
        category = data.get("category", "Unknown")
        if category not in category_counts:
            category_counts[category] = {"total": 0, "with_geometry": 0}
        category_counts[category]["total"] += 1
        if data.get("bounding_box"):
            category_counts[category]["with_geometry"] += 1

    for category, counts in sorted(category_counts.items()):
        pct = (counts["with_geometry"] / counts["total"] * 100) if counts["total"] > 0 else 0
        logger.info(f"  {category}: {counts['with_geometry']}/{counts['total']} ({pct:.1f}%)")

    return 0


if __name__ == "__main__":
    exit(main())
