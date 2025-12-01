#!/usr/bin/env python3
"""
Migrate geometry data from catalog.json to merged_catalog.json.

catalog.json has complete geometry data (bounding_box, ports, anchor_point)
for ~82 priority symbols (pumps, tanks, valves), but merged_catalog.json
(805 symbols) has NO geometry data.

This script:
1. Loads geometry from catalog.json (array format)
2. Matches symbols by ID
3. Adds geometry fields to merged_catalog.json (dict format)
4. Saves the updated merged_catalog.json
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_geometry_source(source_path: Path) -> Dict[str, Dict[str, Any]]:
    """Load geometry data from catalog.json (array format).

    Args:
        source_path: Path to catalog.json

    Returns:
        Dict mapping symbol_id -> geometry fields
    """
    with open(source_path, 'r') as f:
        source = json.load(f)

    geometry_lookup = {}
    symbols = source.get("symbols", [])

    for symbol in symbols:
        symbol_id = symbol.get("id")
        if not symbol_id:
            continue

        # Extract geometry fields
        geometry = {}
        if symbol.get("bounding_box"):
            geometry["bounding_box"] = symbol["bounding_box"]
        if symbol.get("ports"):
            geometry["ports"] = symbol["ports"]
        if symbol.get("anchor_point"):
            geometry["anchor_point"] = symbol["anchor_point"]
        if symbol.get("scalable") is not None:
            geometry["scalable"] = symbol["scalable"]
        if symbol.get("rotatable") is not None:
            geometry["rotatable"] = symbol["rotatable"]

        if geometry:
            geometry_lookup[symbol_id] = geometry

    return geometry_lookup


def migrate_geometry(
    target_path: Path,
    geometry_lookup: Dict[str, Dict[str, Any]]
) -> Tuple[int, int]:
    """Migrate geometry data to merged_catalog.json.

    Args:
        target_path: Path to merged_catalog.json
        geometry_lookup: Dict mapping symbol_id -> geometry fields

    Returns:
        Tuple of (migrated_count, total_with_geometry)
    """
    with open(target_path, 'r') as f:
        target = json.load(f)

    symbols = target.get("symbols", {})
    migrated = 0
    skipped = 0

    for symbol_id, data in symbols.items():
        if symbol_id in geometry_lookup:
            geom = geometry_lookup[symbol_id]

            # Add geometry fields
            if "bounding_box" in geom:
                data["bounding_box"] = geom["bounding_box"]
            if "ports" in geom:
                data["ports"] = geom["ports"]
            if "anchor_point" in geom:
                data["anchor_point"] = geom["anchor_point"]
            if "scalable" in geom:
                data["scalable"] = geom["scalable"]
            if "rotatable" in geom:
                data["rotatable"] = geom["rotatable"]

            migrated += 1
        else:
            skipped += 1

    # Save updated target
    with open(target_path, 'w') as f:
        json.dump(target, f, indent=2)

    return migrated, len(geometry_lookup)


def count_symbols_with_geometry(target_path: Path) -> Dict[str, int]:
    """Count symbols that have geometry data after migration.

    Args:
        target_path: Path to merged_catalog.json

    Returns:
        Dict with counts by category
    """
    with open(target_path, 'r') as f:
        target = json.load(f)

    counts = {
        "total": 0,
        "with_bounding_box": 0,
        "with_ports": 0,
        "with_anchor": 0,
        "by_category": {}
    }

    for symbol_id, data in target.get("symbols", {}).items():
        counts["total"] += 1

        has_bbox = "bounding_box" in data
        has_ports = "ports" in data and len(data["ports"]) > 0
        has_anchor = "anchor_point" in data

        if has_bbox:
            counts["with_bounding_box"] += 1
        if has_ports:
            counts["with_ports"] += 1
        if has_anchor:
            counts["with_anchor"] += 1

        # By category
        category = data.get("category", "Unknown")
        if category not in counts["by_category"]:
            counts["by_category"][category] = {"total": 0, "with_geometry": 0}
        counts["by_category"][category]["total"] += 1
        if has_bbox:
            counts["by_category"][category]["with_geometry"] += 1

    return counts


def main():
    """Main entry point."""
    # Determine paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    assets_dir = project_root / "src" / "visualization" / "symbols" / "assets"

    source_path = assets_dir / "catalog.json"
    target_path = assets_dir / "merged_catalog.json"

    # Validate paths
    if not source_path.exists():
        logger.error(f"Source catalog not found: {source_path}")
        return 1
    if not target_path.exists():
        logger.error(f"Target catalog not found: {target_path}")
        return 1

    logger.info(f"Source: {source_path}")
    logger.info(f"Target: {target_path}")

    # Load geometry from source
    logger.info("Loading geometry from catalog.json...")
    geometry_lookup = load_geometry_source(source_path)
    logger.info(f"Found geometry for {len(geometry_lookup)} symbols")

    # Migrate to target
    logger.info("Migrating geometry to merged_catalog.json...")
    migrated, total = migrate_geometry(target_path, geometry_lookup)
    logger.info(f"Migrated geometry for {migrated} symbols (source had {total})")

    # Count results
    counts = count_symbols_with_geometry(target_path)
    logger.info(f"\nPost-migration statistics:")
    logger.info(f"  Total symbols: {counts['total']}")
    logger.info(f"  With bounding_box: {counts['with_bounding_box']}")
    logger.info(f"  With ports: {counts['with_ports']}")
    logger.info(f"  With anchor_point: {counts['with_anchor']}")

    logger.info(f"\nBy category:")
    for category, cat_counts in sorted(counts["by_category"].items()):
        pct = (cat_counts["with_geometry"] / cat_counts["total"] * 100) if cat_counts["total"] > 0 else 0
        logger.info(f"  {category}: {cat_counts['with_geometry']}/{cat_counts['total']} ({pct:.1f}%)")

    logger.info("\nMigration complete!")
    return 0


if __name__ == "__main__":
    exit(main())
