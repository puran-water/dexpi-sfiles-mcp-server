"""
Tests for SVG metadata extraction (src/core/svg_parser.py).

Week 8: Consolidated SVG parsing module tests.
"""

import pytest
import tempfile
from pathlib import Path

from src.core.svg_parser import (
    extract_svg_metadata,
    determine_port_direction,
    SVGMetadata,
    _extract_bounding_box,
    _parse_dimension,
    _infer_default_ports
)
from src.core.symbols import Point, BoundingBox, Port


class TestExtractSVGMetadata:
    """Tests for extract_svg_metadata function."""

    def test_extract_from_valid_svg(self):
        """Test extraction from a simple valid SVG."""
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50">
            <rect x="0" y="0" width="100" height="50"/>
        </svg>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
            f.write(svg_content)
            svg_path = Path(f.name)

        try:
            metadata = extract_svg_metadata(svg_path)
            assert metadata is not None
            assert metadata.bounding_box.width == 100
            assert metadata.bounding_box.height == 50
            assert metadata.anchor_point.x == 50  # center
            assert metadata.anchor_point.y == 25  # center
            assert metadata.file_hash is not None
        finally:
            svg_path.unlink()

    def test_extract_with_ports(self):
        """Test extraction of port elements."""
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50">
            <circle id="port_inlet" class="port" cx="0" cy="25"/>
            <circle id="port_outlet" class="port" cx="100" cy="25"/>
        </svg>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
            f.write(svg_content)
            svg_path = Path(f.name)

        try:
            metadata = extract_svg_metadata(svg_path)
            assert metadata is not None
            assert len(metadata.ports) == 2
            assert metadata.ports[0].direction == 'W'  # x=0 → West
            assert metadata.ports[1].direction == 'E'  # x=100 → East
        finally:
            svg_path.unlink()

    def test_extract_with_explicit_anchor(self):
        """Test extraction with explicit anchor point."""
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50">
            <circle id="anchor" cx="30" cy="40"/>
        </svg>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
            f.write(svg_content)
            svg_path = Path(f.name)

        try:
            metadata = extract_svg_metadata(svg_path)
            assert metadata is not None
            assert metadata.anchor_point.x == 30
            assert metadata.anchor_point.y == 40
        finally:
            svg_path.unlink()

    def test_extract_with_width_height(self):
        """Test extraction from SVG with width/height instead of viewBox."""
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <svg xmlns="http://www.w3.org/2000/svg" width="200px" height="100px">
            <rect x="0" y="0" width="200" height="100"/>
        </svg>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
            f.write(svg_content)
            svg_path = Path(f.name)

        try:
            metadata = extract_svg_metadata(svg_path)
            assert metadata is not None
            assert metadata.bounding_box.width == 200
            assert metadata.bounding_box.height == 100
        finally:
            svg_path.unlink()

    def test_extract_returns_none_for_invalid_file(self):
        """Test that invalid files return None gracefully."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
            f.write("not valid xml")
            svg_path = Path(f.name)

        try:
            metadata = extract_svg_metadata(svg_path)
            assert metadata is None
        finally:
            svg_path.unlink()


class TestDeterminePortDirection:
    """Tests for port direction determination."""

    def test_west_edge(self):
        """Port at left edge should be West."""
        assert determine_port_direction(0, 50, 100, 100) == 'W'
        assert determine_port_direction(10, 50, 100, 100) == 'W'

    def test_east_edge(self):
        """Port at right edge should be East."""
        assert determine_port_direction(100, 50, 100, 100) == 'E'
        assert determine_port_direction(90, 50, 100, 100) == 'E'

    def test_north_edge(self):
        """Port at top edge should be North."""
        assert determine_port_direction(50, 0, 100, 100) == 'N'
        assert determine_port_direction(50, 10, 100, 100) == 'N'

    def test_south_edge(self):
        """Port at bottom edge should be South."""
        assert determine_port_direction(50, 100, 100, 100) == 'S'
        assert determine_port_direction(50, 90, 100, 100) == 'S'

    def test_corners(self):
        """Ports in corners should return diagonal directions."""
        # NW corner
        assert determine_port_direction(30, 30, 100, 100) == 'NW'
        # NE corner
        assert determine_port_direction(70, 30, 100, 100) == 'NE'
        # SW corner
        assert determine_port_direction(30, 70, 100, 100) == 'SW'
        # SE corner
        assert determine_port_direction(70, 70, 100, 100) == 'SE'

    def test_zero_dimensions(self):
        """Zero dimensions should return default 'E'."""
        assert determine_port_direction(50, 50, 0, 0) == 'E'
        assert determine_port_direction(50, 50, 0, 100) == 'E'

    def test_offset_viewbox(self):
        """Direction accounts for non-zero/negative viewBox origins."""
        # Bounding box spans -10..10 in X; port at 10 is still east
        assert determine_port_direction(10, 0, 20, 20, origin_x=-10, origin_y=-10) == 'E'
        # Port at -10 is on the west edge
        assert determine_port_direction(-10, 0, 20, 20, origin_x=-10, origin_y=-10) == 'W'


class TestInferDefaultPorts:
    """Tests for default port inference based on symbol type."""

    def test_pump_ports(self):
        """Pumps should have W inlet, E outlet."""
        bbox = BoundingBox(x=0, y=0, width=100, height=50)
        ports = _infer_default_ports(Path("/symbols/pump.svg"), bbox)
        assert len(ports) == 2
        assert ports[0].direction == 'W'
        assert ports[0].type == 'inlet'
        assert ports[0].x == 0  # Left edge
        assert ports[1].direction == 'E'
        assert ports[1].type == 'outlet'
        assert ports[1].x == 100  # Right edge

    def test_pump_by_prefix(self):
        """PP prefix should be recognized as pump."""
        bbox = BoundingBox(x=0, y=0, width=100, height=50)
        ports = _infer_default_ports(Path("/symbols/PP001A.svg"), bbox)
        assert len(ports) == 2
        assert ports[0].direction == 'W'

    def test_pump_with_offset_bbox(self):
        """Ports should use absolute coordinates for offset bboxes."""
        bbox = BoundingBox(x=-50, y=-25, width=100, height=50)
        ports = _infer_default_ports(Path("/symbols/pump.svg"), bbox)
        assert len(ports) == 2
        assert ports[0].x == -50  # Left edge at bbox.x
        assert ports[0].y == 0    # Center Y at bbox.y + height/2
        assert ports[1].x == 50   # Right edge at bbox.x + width

    def test_tank_ports(self):
        """Tanks should have N inlet, S outlet."""
        bbox = BoundingBox(x=0, y=0, width=100, height=150)
        ports = _infer_default_ports(Path("/symbols/tank.svg"), bbox)
        assert len(ports) == 2
        assert ports[0].direction == 'N'
        assert ports[0].type == 'inlet'
        assert ports[0].y == 0  # Top edge
        assert ports[1].direction == 'S'
        assert ports[1].type == 'outlet'
        assert ports[1].y == 150  # Bottom edge

    def test_valve_ports(self):
        """Valves should be inline (W to E)."""
        bbox = BoundingBox(x=0, y=0, width=50, height=50)
        ports = _infer_default_ports(Path("/symbols/valve.svg"), bbox)
        assert len(ports) == 2
        assert ports[0].direction == 'W'
        assert ports[1].direction == 'E'

    def test_heat_exchanger_ports(self):
        """Heat exchangers should have shell and tube ports."""
        bbox = BoundingBox(x=0, y=0, width=100, height=60)
        ports = _infer_default_ports(Path("/symbols/heat_exchanger.svg"), bbox)
        assert len(ports) == 4
        ids = [p.id for p in ports]
        assert 'shell_in' in ids
        assert 'shell_out' in ids
        assert 'tube_in' in ids
        assert 'tube_out' in ids

    def test_separator_ports(self):
        """Separators should have inlet and two outlets."""
        bbox = BoundingBox(x=0, y=0, width=100, height=100)
        ports = _infer_default_ports(Path("/symbols/separator.svg"), bbox)
        assert len(ports) == 3
        directions = [p.direction for p in ports]
        assert 'W' in directions  # inlet
        assert 'N' in directions  # light outlet
        assert 'S' in directions  # heavy outlet

    def test_unknown_type(self):
        """Unknown types should return empty list."""
        bbox = BoundingBox(x=0, y=0, width=100, height=100)
        ports = _infer_default_ports(Path("/symbols/unknown.svg"), bbox)
        assert ports == []


class TestSVGMetadata:
    """Tests for SVGMetadata dataclass."""

    def test_to_dict(self):
        """Test serialization to dictionary."""
        bbox = BoundingBox(x=0, y=0, width=100, height=50)
        anchor = Point(x=50, y=25)
        ports = [
            Port(id="inlet", x=0, y=25, direction="W", type="inlet", flow_direction=None)
        ]
        metadata = SVGMetadata(
            bounding_box=bbox,
            anchor_point=anchor,
            ports=ports,
            file_hash="abc123"
        )

        d = metadata.to_dict()
        assert d["bounding_box"]["width"] == 100
        assert d["anchor_point"]["x"] == 50
        assert len(d["ports"]) == 1
        assert d["ports"][0]["id"] == "inlet"
        assert d["file_hash"] == "abc123"


class TestParseDimension:
    """Tests for dimension parsing."""

    def test_plain_number(self):
        """Plain numbers should parse correctly."""
        assert _parse_dimension("100") == 100.0
        assert _parse_dimension("50.5") == 50.5

    def test_with_px_suffix(self):
        """px suffix should be stripped."""
        assert _parse_dimension("100px") == 100.0
        assert _parse_dimension("50.5px") == 50.5

    def test_with_other_suffixes(self):
        """Other unit suffixes should be stripped."""
        assert _parse_dimension("100pt") == 100.0
        assert _parse_dimension("100mm") == 100.0

    def test_invalid_returns_default(self):
        """Invalid strings should return default 100."""
        assert _parse_dimension("") == 100.0
        assert _parse_dimension("abc") == 100.0


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
