"""
SVG Metadata Extraction Module

Provides unified SVG parsing for symbol geometry extraction.
Consolidates SVG parsing logic from catalog.py and extraction scripts.

Uses geometry types from src/core/symbols.py (Point, BoundingBox, Port).
"""

import xml.etree.ElementTree as ET
import hashlib
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict

from src.core.symbols import Point, BoundingBox, Port

logger = logging.getLogger(__name__)


@dataclass
class SVGMetadata:
    """Complete metadata extracted from an SVG file."""
    bounding_box: BoundingBox
    anchor_point: Point
    ports: List[Port]
    scalable: bool = True
    rotatable: bool = True
    file_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "bounding_box": {
                "x": self.bounding_box.x,
                "y": self.bounding_box.y,
                "width": self.bounding_box.width,
                "height": self.bounding_box.height
            },
            "anchor_point": {
                "x": self.anchor_point.x,
                "y": self.anchor_point.y
            },
            "ports": [
                {
                    "id": p.id,
                    "position": {"x": p.x, "y": p.y},
                    "direction": p.direction,
                    "type": p.type,
                    "flow_direction": p.flow_direction
                }
                for p in self.ports
            ],
            "scalable": self.scalable,
            "rotatable": self.rotatable,
            "file_hash": self.file_hash
        }


def extract_svg_metadata(svg_path: Path, include_hash: bool = True) -> Optional[SVGMetadata]:
    """
    Extract geometry metadata from an SVG file.

    Args:
        svg_path: Path to SVG file
        include_hash: Whether to calculate file hash

    Returns:
        SVGMetadata object or None if extraction fails
    """
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()

        # Extract dimensions from viewBox or width/height
        bbox = _extract_bounding_box(root)

        # Extract anchor point
        anchor = _extract_anchor_point(root, bbox)

        # Extract ports
        ports = _extract_ports(root, bbox.width, bbox.height)

        # Infer default ports if none found
        if not ports:
            ports = _infer_default_ports(svg_path, bbox.width, bbox.height)

        # Calculate file hash
        file_hash = None
        if include_hash:
            file_hash = hashlib.md5(svg_path.read_bytes()).hexdigest()

        return SVGMetadata(
            bounding_box=bbox,
            anchor_point=anchor,
            ports=ports,
            scalable=True,
            rotatable=True,
            file_hash=file_hash
        )

    except Exception as e:
        logger.debug(f"Failed to extract metadata from {svg_path}: {e}")
        return None


def _extract_bounding_box(root: ET.Element) -> BoundingBox:
    """Extract bounding box from SVG root element."""
    # Try viewBox first
    viewbox = root.get('viewBox')
    if viewbox:
        parts = viewbox.split()
        if len(parts) >= 4:
            x, y, width, height = map(float, parts[:4])
            return BoundingBox(x=x, y=y, width=width, height=height)

    # Fall back to width/height attributes
    width_str = root.get('width', '100')
    height_str = root.get('height', '100')

    # Remove unit suffixes (px, pt, mm, etc.)
    width = _parse_dimension(width_str)
    height = _parse_dimension(height_str)

    return BoundingBox(x=0, y=0, width=width, height=height)


def _parse_dimension(dim_str: str) -> float:
    """Parse dimension string, removing unit suffixes."""
    # Extract numeric part
    numeric = ''.join(c for c in dim_str if c.isdigit() or c == '.' or c == '-')
    return float(numeric) if numeric else 100.0


def _extract_anchor_point(root: ET.Element, bbox: BoundingBox) -> Point:
    """Extract anchor point from SVG, defaulting to center."""
    # Look for element with id='anchor'
    for elem in root.iter():
        if elem.get('id') == 'anchor':
            # Try circle cx/cy
            cx = elem.get('cx')
            cy = elem.get('cy')
            if cx and cy:
                return Point(x=float(cx), y=float(cy))

            # Try rect center
            x = elem.get('x')
            y = elem.get('y')
            w = elem.get('width', '0')
            h = elem.get('height', '0')
            if x and y:
                return Point(
                    x=float(x) + float(w) / 2,
                    y=float(y) + float(h) / 2
                )

    # Default to bounding box center
    return bbox.center


def _extract_ports(root: ET.Element, width: float, height: float) -> List[Port]:
    """Extract connection ports from SVG elements."""
    ports = []

    # Method 1: Elements with class containing 'port'
    for elem in root.iter():
        elem_class = elem.get('class', '')
        if 'port' in elem_class.lower():
            port = _port_from_element(elem, width, height, len(ports))
            if port:
                ports.append(port)

    # Method 2: Elements with id starting with 'port'
    if not ports:
        for elem in root.iter():
            elem_id = elem.get('id', '')
            if elem_id.lower().startswith('port'):
                port = _port_from_element(elem, width, height, len(ports))
                if port:
                    ports.append(port)

    # Method 3: Elements with 'nozzle' or 'connection' in id
    if not ports:
        for elem in root.iter():
            elem_id = elem.get('id', '').lower()
            if 'nozzle' in elem_id or 'connection' in elem_id:
                port = _port_from_element(elem, width, height, len(ports))
                if port:
                    ports.append(port)

    return ports


def _port_from_element(elem: ET.Element, width: float, height: float, index: int) -> Optional[Port]:
    """Extract port data from an SVG element."""
    x, y = _get_element_position(elem)
    if x is None or y is None:
        return None

    # Determine direction based on position
    direction = determine_port_direction(x, y, width, height)

    # Determine port type from id
    elem_id = elem.get('id', f'port_{index}').lower()
    port_type = _infer_port_type(elem_id, index)

    return Port(
        id=elem.get('id', f'port_{index}'),
        x=x,
        y=y,
        direction=direction,
        type=port_type,
        flow_direction=None
    )


def _get_element_position(elem: ET.Element) -> Tuple[Optional[float], Optional[float]]:
    """Get position from SVG element based on its type."""
    tag = elem.tag.lower().split('}')[-1]  # Remove namespace

    # Circle
    if tag == 'circle':
        cx = elem.get('cx')
        cy = elem.get('cy')
        if cx and cy:
            return float(cx), float(cy)

    # Rectangle (use center)
    if tag == 'rect':
        x = elem.get('x')
        y = elem.get('y')
        w = elem.get('width', '0')
        h = elem.get('height', '0')
        if x and y:
            return float(x) + float(w) / 2, float(y) + float(h) / 2

    # Line (use midpoint)
    if tag == 'line':
        x1 = elem.get('x1', '0')
        x2 = elem.get('x2', '0')
        y1 = elem.get('y1', '0')
        y2 = elem.get('y2', '0')
        return (float(x1) + float(x2)) / 2, (float(y1) + float(y2)) / 2

    # Try transform translate
    transform = elem.get('transform', '')
    if 'translate' in transform:
        match = re.search(r'translate\s*\(\s*([-\d.]+)\s*,?\s*([-\d.]+)?\s*\)', transform)
        if match:
            x = float(match.group(1))
            y = float(match.group(2)) if match.group(2) else 0
            return x, y

    return None, None


def determine_port_direction(x: float, y: float, width: float, height: float) -> str:
    """
    Determine port direction based on position relative to symbol bounds.

    Args:
        x: Port X position
        y: Port Y position
        width: Symbol width
        height: Symbol height

    Returns:
        Direction string: N, S, E, W, NE, NW, SE, SW
    """
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


def _infer_port_type(port_id: str, index: int) -> str:
    """Infer port type from its ID."""
    port_id_lower = port_id.lower()
    if 'inlet' in port_id_lower or 'in' in port_id_lower:
        return 'inlet'
    elif 'outlet' in port_id_lower or 'out' in port_id_lower:
        return 'outlet'
    elif 'vent' in port_id_lower or 'aux' in port_id_lower:
        return 'auxiliary'
    else:
        return 'inlet' if index == 0 else 'outlet'


def _infer_default_ports(svg_path: Path, width: float, height: float) -> List[Port]:
    """Infer default ports based on symbol type from filename."""
    path_str = str(svg_path).lower()
    filename = svg_path.stem.lower()

    # Pumps - inlet on left (W), outlet on right (E)
    if 'pump' in path_str or filename.startswith('pp'):
        return [
            Port(id="inlet", x=0, y=height / 2, direction="W", type="inlet", flow_direction=None),
            Port(id="outlet", x=width, y=height / 2, direction="E", type="outlet", flow_direction=None)
        ]

    # Tanks - inlet on top (N), outlet on bottom (S)
    if 'tank' in path_str or 'vessel' in path_str or filename.startswith('pt'):
        return [
            Port(id="inlet", x=width / 2, y=0, direction="N", type="inlet", flow_direction=None),
            Port(id="outlet", x=width / 2, y=height, direction="S", type="outlet", flow_direction=None)
        ]

    # Valves - inline (W to E)
    if 'valve' in path_str or filename.startswith('pv'):
        return [
            Port(id="inlet", x=0, y=height / 2, direction="W", type="inlet", flow_direction=None),
            Port(id="outlet", x=width, y=height / 2, direction="E", type="outlet", flow_direction=None)
        ]

    # Heat exchangers - shell and tube sides
    if 'heat' in path_str or 'exchanger' in path_str or filename.startswith('pe'):
        return [
            Port(id="shell_in", x=0, y=height / 3, direction="W", type="inlet", flow_direction=None),
            Port(id="shell_out", x=width, y=height / 3, direction="E", type="outlet", flow_direction=None),
            Port(id="tube_in", x=0, y=2 * height / 3, direction="W", type="inlet", flow_direction=None),
            Port(id="tube_out", x=width, y=2 * height / 3, direction="E", type="outlet", flow_direction=None)
        ]

    # Filters - inline
    if 'filter' in path_str or filename.startswith('pf'):
        return [
            Port(id="inlet", x=0, y=height / 2, direction="W", type="inlet", flow_direction=None),
            Port(id="outlet", x=width, y=height / 2, direction="E", type="outlet", flow_direction=None)
        ]

    # Separators - multi-outlet
    if 'separator' in path_str or 'centrifuge' in path_str or filename.startswith('ps'):
        return [
            Port(id="inlet", x=0, y=height / 2, direction="W", type="inlet", flow_direction=None),
            Port(id="light_out", x=width / 2, y=0, direction="N", type="outlet", flow_direction=None),
            Port(id="heavy_out", x=width / 2, y=height, direction="S", type="outlet", flow_direction=None)
        ]

    # Default - no ports (will use bounding box center as connection point)
    return []
