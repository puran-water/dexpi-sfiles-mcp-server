#!/usr/bin/env python3
"""
Validate geometry data in merged_catalog.json.

This script checks:
1. Every symbol has bounding_box with positive width/height
2. Every symbol has anchor_point (or defaults to bbox center)
3. Port directions are valid compass values
4. Port positions fall within bbox bounds (with tolerance)
5. File hashes are present and consistent length (SHA-256)

Run this as a CI check to ensure data quality before rendering.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Valid compass directions
VALID_DIRECTIONS = {'N', 'S', 'E', 'W', 'NE', 'NW', 'SE', 'SW'}

# Tolerance for port position checks (fraction of bbox dimension)
POSITION_TOLERANCE = 0.05  # 5% tolerance

# Categories that are allowed to have zero dimensions (origin markers, annotations)
ZERO_DIMENSION_ALLOWED_CATEGORIES = {'Origo', 'Annotations'}


def validate_bounding_box(symbol_id: str, data: Dict) -> List[str]:
    """Validate bounding box."""
    errors = []
    bbox = data.get("bounding_box")
    category = data.get("category", "")

    if not bbox:
        errors.append(f"{symbol_id}: Missing bounding_box")
        return errors

    width = bbox.get("width", 0)
    height = bbox.get("height", 0)

    # Allow zero dimensions for certain categories (origin markers, annotations)
    if category in ZERO_DIMENSION_ALLOWED_CATEGORIES:
        return errors  # Skip dimension checks for allowed categories

    if width <= 0:
        errors.append(f"{symbol_id}: bounding_box.width must be positive (got {width})")
    if height <= 0:
        errors.append(f"{symbol_id}: bounding_box.height must be positive (got {height})")

    return errors


def validate_anchor_point(symbol_id: str, data: Dict) -> List[str]:
    """Validate anchor point."""
    errors = []
    anchor = data.get("anchor_point")
    bbox = data.get("bounding_box")

    if not anchor:
        errors.append(f"{symbol_id}: Missing anchor_point")
        return errors

    if bbox:
        x = anchor.get("x", 0)
        y = anchor.get("y", 0)
        bbox_x = bbox.get("x", 0)
        bbox_y = bbox.get("y", 0)
        width = bbox.get("width", 0)
        height = bbox.get("height", 0)

        # Check anchor is within bbox (with tolerance)
        min_x = bbox_x - width * POSITION_TOLERANCE
        max_x = bbox_x + width * (1 + POSITION_TOLERANCE)
        min_y = bbox_y - height * POSITION_TOLERANCE
        max_y = bbox_y + height * (1 + POSITION_TOLERANCE)

        if not (min_x <= x <= max_x):
            errors.append(f"{symbol_id}: anchor_point.x ({x}) outside bbox range [{bbox_x}, {bbox_x + width}]")
        if not (min_y <= y <= max_y):
            errors.append(f"{symbol_id}: anchor_point.y ({y}) outside bbox range [{bbox_y}, {bbox_y + height}]")

    return errors


def validate_ports(symbol_id: str, data: Dict) -> List[str]:
    """Validate port data."""
    errors = []
    ports = data.get("ports", [])
    bbox = data.get("bounding_box")

    for i, port in enumerate(ports):
        port_id = port.get("id", f"port_{i}")

        # Check direction
        direction = port.get("direction")
        if direction not in VALID_DIRECTIONS:
            errors.append(f"{symbol_id}.{port_id}: Invalid direction '{direction}' (expected one of {VALID_DIRECTIONS})")

        # Check position is within bbox
        if bbox:
            pos = port.get("position", {})
            x = pos.get("x", 0)
            y = pos.get("y", 0)
            bbox_x = bbox.get("x", 0)
            bbox_y = bbox.get("y", 0)
            width = bbox.get("width", 0)
            height = bbox.get("height", 0)

            # Allow some tolerance for edge ports
            min_x = bbox_x - width * POSITION_TOLERANCE
            max_x = bbox_x + width * (1 + POSITION_TOLERANCE)
            min_y = bbox_y - height * POSITION_TOLERANCE
            max_y = bbox_y + height * (1 + POSITION_TOLERANCE)

            if not (min_x <= x <= max_x):
                errors.append(f"{symbol_id}.{port_id}: position.x ({x}) outside bbox range [{bbox_x}, {bbox_x + width}]")
            if not (min_y <= y <= max_y):
                errors.append(f"{symbol_id}.{port_id}: position.y ({y}) outside bbox range [{bbox_y}, {bbox_y + height}]")

        # Check port type
        port_type = port.get("type")
        if port_type not in {"inlet", "outlet", "auxiliary", None}:
            errors.append(f"{symbol_id}.{port_id}: Invalid port type '{port_type}'")

    return errors


def validate_file_hash(symbol_id: str, data: Dict) -> List[str]:
    """Validate file hash format."""
    errors = []
    provenance = data.get("provenance", {})
    file_hash = provenance.get("file_hash")

    if file_hash:
        # SHA-256 produces 64-character hex strings
        if len(file_hash) == 32:
            errors.append(f"{symbol_id}: file_hash appears to be MD5 (32 chars), should be SHA-256 (64 chars)")
        elif len(file_hash) != 64:
            errors.append(f"{symbol_id}: file_hash length {len(file_hash)} is unexpected (expected 64 for SHA-256)")

    return errors


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
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

    # Validate each symbol
    all_errors = []
    symbols_with_geometry = 0
    symbols_without_geometry = 0
    symbols_with_ports = 0
    symbols_without_ports = 0

    for symbol_id, data in symbols.items():
        errors = []

        # Validate bounding box
        errors.extend(validate_bounding_box(symbol_id, data))

        if data.get("bounding_box"):
            symbols_with_geometry += 1

            # Validate anchor point
            errors.extend(validate_anchor_point(symbol_id, data))

            # Validate ports
            errors.extend(validate_ports(symbol_id, data))

            # Validate file hash
            errors.extend(validate_file_hash(symbol_id, data))

            if data.get("ports"):
                symbols_with_ports += 1
            else:
                symbols_without_ports += 1
        else:
            symbols_without_geometry += 1

        all_errors.extend(errors)

    # Report results
    logger.info(f"\nValidation Summary:")
    logger.info(f"  Total symbols: {len(symbols)}")
    logger.info(f"  With geometry: {symbols_with_geometry}")
    logger.info(f"  Without geometry: {symbols_without_geometry}")
    logger.info(f"  With ports: {symbols_with_ports}")
    logger.info(f"  Without ports: {symbols_without_ports}")

    if all_errors:
        logger.error(f"\nFound {len(all_errors)} validation errors:")
        for error in all_errors[:50]:  # Show first 50 errors
            logger.error(f"  {error}")
        if len(all_errors) > 50:
            logger.error(f"  ... and {len(all_errors) - 50} more errors")
        return 1
    else:
        logger.info(f"\n✓ All validations passed!")
        return 0


if __name__ == "__main__":
    exit(main())
