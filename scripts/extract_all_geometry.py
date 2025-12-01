#!/usr/bin/env python3
"""
Extract geometry from all SVG files and update merged_catalog.json.

This script:
1. Iterates through all symbols in merged_catalog.json
2. Finds corresponding SVG files
3. Extracts bounding_box, anchor_point, ports from SVG
4. Updates merged_catalog.json with geometry data
"""

import json
import xml.etree.ElementTree as ET
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_svg_geometry(svg_path: Path) -> Optional[Dict[str, Any]]:
    """
    Extract geometry metadata from an SVG file.

    Args:
        svg_path: Path to SVG file

    Returns:
        Dict with bounding_box, anchor_point, ports, scalable, rotatable
    """
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()

        # SVG namespace
        ns = {'svg': 'http://www.w3.org/2000/svg'}

        # Extract viewBox or dimensions
        viewbox = root.get('viewBox')
        if viewbox:
            parts = viewbox.split()
            if len(parts) >= 4:
                x, y, width, height = map(float, parts[:4])
            else:
                x, y, width, height = 0, 0, 100, 100
        else:
            width_str = root.get('width', '100')
            height_str = root.get('height', '100')
            # Remove px, pt, mm suffixes
            width = float(''.join(c for c in width_str if c.isdigit() or c == '.') or '100')
            height = float(''.join(c for c in height_str if c.isdigit() or c == '.') or '100')
            x, y = 0, 0

        bounding_box = {
            "x": x,
            "y": y,
            "width": width,
            "height": height
        }

        # Calculate default anchor (center)
        anchor_x = x + width / 2
        anchor_y = y + height / 2

        # Look for marked anchor point in SVG
        anchor_elem = root.find(".//*[@id='anchor']")
        if anchor_elem is not None:
            cx = anchor_elem.get('cx')
            cy = anchor_elem.get('cy')
            if cx and cy:
                anchor_x = float(cx)
                anchor_y = float(cy)

        anchor_point = {"x": anchor_x, "y": anchor_y}

        # Extract ports (connection points)
        ports = []

        # Method 1: Look for elements with class='port'
        for elem in root.iter():
            elem_class = elem.get('class', '')
            if 'port' in elem_class.lower():
                port = _extract_port_from_element(elem, width, height, len(ports))
                if port:
                    ports.append(port)

        # Method 2: Look for elements with id starting with 'port'
        if not ports:
            for elem in root.iter():
                elem_id = elem.get('id', '')
                if elem_id.lower().startswith('port'):
                    port = _extract_port_from_element(elem, width, height, len(ports))
                    if port:
                        ports.append(port)

        # Method 3: Look for nozzle markers
        if not ports:
            for elem in root.iter():
                elem_id = elem.get('id', '').lower()
                if 'nozzle' in elem_id or 'connection' in elem_id:
                    port = _extract_port_from_element(elem, width, height, len(ports))
                    if port:
                        ports.append(port)

        # Method 4: Infer ports from symbol type if still empty
        if not ports:
            ports = _infer_default_ports(svg_path, width, height)

        return {
            "bounding_box": bounding_box,
            "anchor_point": anchor_point,
            "ports": ports,
            "scalable": True,
            "rotatable": True
        }

    except Exception as e:
        logger.debug(f"Failed to extract geometry from {svg_path}: {e}")
        return None


def _extract_port_from_element(elem: ET.Element, width: float, height: float, index: int) -> Optional[Dict]:
    """Extract port data from an SVG element."""
    # Get position based on element type
    x, y = None, None

    # Circle element
    if 'circle' in elem.tag.lower():
        x = elem.get('cx')
        y = elem.get('cy')
    # Rectangle element
    elif 'rect' in elem.tag.lower():
        x = elem.get('x')
        y = elem.get('y')
        w = elem.get('width', '0')
        h = elem.get('height', '0')
        if x and y:
            x = float(x) + float(w) / 2
            y = float(y) + float(h) / 2
    # Line element (use midpoint)
    elif 'line' in elem.tag.lower():
        x1 = elem.get('x1', '0')
        x2 = elem.get('x2', '0')
        y1 = elem.get('y1', '0')
        y2 = elem.get('y2', '0')
        x = (float(x1) + float(x2)) / 2
        y = (float(y1) + float(y2)) / 2
    # Use transform if present
    elif elem.get('transform'):
        # Try to extract translate values
        transform = elem.get('transform', '')
        if 'translate' in transform:
            import re
            match = re.search(r'translate\s*\(\s*([-\d.]+)\s*,?\s*([-\d.]+)?\s*\)', transform)
            if match:
                x = float(match.group(1))
                y = float(match.group(2)) if match.group(2) else 0

    if x is None or y is None:
        return None

    x, y = float(x), float(y)

    # Determine direction based on position
    direction = _determine_port_direction(x, y, width, height)

    # Determine port type from ID or position
    elem_id = elem.get('id', f'port_{index}').lower()
    if 'inlet' in elem_id or 'in' in elem_id:
        port_type = 'inlet'
    elif 'outlet' in elem_id or 'out' in elem_id:
        port_type = 'outlet'
    elif 'vent' in elem_id or 'aux' in elem_id:
        port_type = 'auxiliary'
    else:
        port_type = 'inlet' if index == 0 else 'outlet'

    return {
        "id": elem.get('id', f'port_{index}'),
        "position": {"x": x, "y": y},
        "direction": direction,
        "type": port_type,
        "flow_direction": None
    }


def _determine_port_direction(x: float, y: float, width: float, height: float) -> str:
    """Determine port direction based on position relative to symbol bounds."""
    if width == 0 or height == 0:
        return 'E'

    rel_x = x / width
    rel_y = y / height

    # Edge detection with tolerance
    if rel_x < 0.15:
        return 'W'
    elif rel_x > 0.85:
        return 'E'
    elif rel_y < 0.15:
        return 'N'
    elif rel_y > 0.85:
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


def _infer_default_ports(svg_path: Path, width: float, height: float) -> List[Dict]:
    """Infer default ports based on symbol type."""
    path_lower = str(svg_path).lower()
    ports = []

    # Pumps - inlet on left (W), outlet on right (E)
    if 'pump' in path_lower or path_lower.startswith('pp'):
        ports = [
            {"id": "inlet", "position": {"x": 0, "y": height / 2}, "direction": "W", "type": "inlet", "flow_direction": None},
            {"id": "outlet", "position": {"x": width, "y": height / 2}, "direction": "E", "type": "outlet", "flow_direction": None}
        ]
    # Tanks - inlet on top (N), outlet on bottom (S)
    elif 'tank' in path_lower or 'vessel' in path_lower or path_lower.startswith('pt'):
        ports = [
            {"id": "inlet", "position": {"x": width / 2, "y": 0}, "direction": "N", "type": "inlet", "flow_direction": None},
            {"id": "outlet", "position": {"x": width / 2, "y": height}, "direction": "S", "type": "outlet", "flow_direction": None}
        ]
    # Valves - inline (W to E)
    elif 'valve' in path_lower or path_lower.startswith('pv'):
        ports = [
            {"id": "inlet", "position": {"x": 0, "y": height / 2}, "direction": "W", "type": "inlet", "flow_direction": None},
            {"id": "outlet", "position": {"x": width, "y": height / 2}, "direction": "E", "type": "outlet", "flow_direction": None}
        ]
    # Heat exchangers
    elif 'heat' in path_lower or 'exchanger' in path_lower or path_lower.startswith('pe'):
        ports = [
            {"id": "shell_in", "position": {"x": 0, "y": height / 3}, "direction": "W", "type": "inlet", "flow_direction": None},
            {"id": "shell_out", "position": {"x": width, "y": height / 3}, "direction": "E", "type": "outlet", "flow_direction": None},
            {"id": "tube_in", "position": {"x": 0, "y": 2 * height / 3}, "direction": "W", "type": "inlet", "flow_direction": None},
            {"id": "tube_out", "position": {"x": width, "y": 2 * height / 3}, "direction": "E", "type": "outlet", "flow_direction": None}
        ]
    # Filters
    elif 'filter' in path_lower or path_lower.startswith('pf'):
        ports = [
            {"id": "inlet", "position": {"x": 0, "y": height / 2}, "direction": "W", "type": "inlet", "flow_direction": None},
            {"id": "outlet", "position": {"x": width, "y": height / 2}, "direction": "E", "type": "outlet", "flow_direction": None}
        ]
    # Separators
    elif 'separator' in path_lower or 'centrifuge' in path_lower or path_lower.startswith('ps'):
        ports = [
            {"id": "inlet", "position": {"x": 0, "y": height / 2}, "direction": "W", "type": "inlet", "flow_direction": None},
            {"id": "light_out", "position": {"x": width / 2, "y": 0}, "direction": "N", "type": "outlet", "flow_direction": None},
            {"id": "heavy_out", "position": {"x": width / 2, "y": height}, "direction": "S", "type": "outlet", "flow_direction": None}
        ]

    return ports


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

        # Extract geometry
        geometry = extract_svg_geometry(svg_path)
        if geometry:
            data["bounding_box"] = geometry["bounding_box"]
            data["anchor_point"] = geometry["anchor_point"]
            if geometry["ports"]:
                data["ports"] = geometry["ports"]
            data["scalable"] = geometry["scalable"]
            data["rotatable"] = geometry["rotatable"]
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
