"""
Tests for SymbolInfo geometry extensions (Week 6).

Tests the new geometry types:
- Point: 2D coordinate
- BoundingBox: Symbol dimensions with center calculation
- Port: Connection point with direction/flow
- SymbolInfo geometry fields
"""

import pytest
from src.core.symbols import (
    Point,
    BoundingBox,
    Port,
    SymbolInfo,
    SymbolCategory,
    SymbolSource
)


class TestPoint:
    """Tests for Point dataclass."""

    def test_point_creation(self):
        """Test basic Point creation."""
        p = Point(x=10.0, y=20.0)
        assert p.x == 10.0
        assert p.y == 20.0

    def test_point_equality(self):
        """Test Point equality comparison."""
        p1 = Point(x=5.0, y=10.0)
        p2 = Point(x=5.0, y=10.0)
        p3 = Point(x=5.0, y=11.0)

        assert p1 == p2
        assert p1 != p3

    def test_point_negative_coordinates(self):
        """Test Point with negative coordinates."""
        p = Point(x=-5.0, y=-10.0)
        assert p.x == -5.0
        assert p.y == -10.0

    def test_point_zero_coordinates(self):
        """Test Point at origin."""
        p = Point(x=0.0, y=0.0)
        assert p.x == 0.0
        assert p.y == 0.0


class TestBoundingBox:
    """Tests for BoundingBox dataclass."""

    def test_bounding_box_creation(self):
        """Test basic BoundingBox creation."""
        bb = BoundingBox(x=0.0, y=0.0, width=100.0, height=50.0)
        assert bb.x == 0.0
        assert bb.y == 0.0
        assert bb.width == 100.0
        assert bb.height == 50.0

    def test_bounding_box_center_at_origin(self):
        """Test center calculation for box at origin."""
        bb = BoundingBox(x=0.0, y=0.0, width=100.0, height=50.0)
        center = bb.center

        assert center.x == 50.0
        assert center.y == 25.0

    def test_bounding_box_center_offset(self):
        """Test center calculation for offset box."""
        bb = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        center = bb.center

        assert center.x == 60.0  # 10 + 100/2
        assert center.y == 45.0  # 20 + 50/2

    def test_bounding_box_square(self):
        """Test center calculation for square box."""
        bb = BoundingBox(x=0.0, y=0.0, width=100.0, height=100.0)
        center = bb.center

        assert center.x == 50.0
        assert center.y == 50.0

    def test_bounding_box_equality(self):
        """Test BoundingBox equality comparison."""
        bb1 = BoundingBox(x=0.0, y=0.0, width=100.0, height=50.0)
        bb2 = BoundingBox(x=0.0, y=0.0, width=100.0, height=50.0)
        bb3 = BoundingBox(x=0.0, y=0.0, width=100.0, height=60.0)

        assert bb1 == bb2
        assert bb1 != bb3


class TestPort:
    """Tests for Port dataclass."""

    def test_port_minimal_creation(self):
        """Test Port creation with required fields only."""
        port = Port(id="inlet", x=0.0, y=25.0)

        assert port.id == "inlet"
        assert port.x == 0.0
        assert port.y == 25.0
        assert port.direction is None
        assert port.type is None
        assert port.flow_direction is None

    def test_port_full_creation(self):
        """Test Port creation with all fields."""
        port = Port(
            id="N1",
            x=50.0,
            y=0.0,
            direction="N",
            type="inlet",
            flow_direction="in"
        )

        assert port.id == "N1"
        assert port.x == 50.0
        assert port.y == 0.0
        assert port.direction == "N"
        assert port.type == "inlet"
        assert port.flow_direction == "in"

    def test_port_directions(self):
        """Test valid port directions."""
        valid_directions = ["N", "S", "E", "W", "NE", "NW", "SE", "SW"]

        for direction in valid_directions:
            port = Port(id="test", x=0.0, y=0.0, direction=direction)
            assert port.direction == direction

    def test_port_flow_directions(self):
        """Test valid flow directions."""
        valid_flows = ["in", "out", "bidirectional"]

        for flow in valid_flows:
            port = Port(id="test", x=0.0, y=0.0, flow_direction=flow)
            assert port.flow_direction == flow

    def test_port_types(self):
        """Test valid port types."""
        valid_types = ["inlet", "outlet", "auxiliary"]

        for port_type in valid_types:
            port = Port(id="test", x=0.0, y=0.0, type=port_type)
            assert port.type == port_type


class TestSymbolInfoGeometry:
    """Tests for SymbolInfo geometry extensions."""

    def test_symbol_info_default_geometry(self):
        """Test SymbolInfo has default geometry values."""
        symbol = SymbolInfo(
            symbol_id="PP001A",
            name="Centrifugal Pump",
            category=SymbolCategory.PUMPS
        )

        assert symbol.bounding_box is None
        assert symbol.anchor_point is None
        assert symbol.ports == []
        assert symbol.scalable is True
        assert symbol.rotatable is True

    def test_symbol_info_with_bounding_box(self):
        """Test SymbolInfo with bounding box."""
        bb = BoundingBox(x=0.0, y=0.0, width=100.0, height=50.0)
        symbol = SymbolInfo(
            symbol_id="PP001A",
            name="Centrifugal Pump",
            category=SymbolCategory.PUMPS,
            bounding_box=bb
        )

        assert symbol.bounding_box is not None
        assert symbol.bounding_box.width == 100.0
        assert symbol.bounding_box.height == 50.0

    def test_symbol_info_with_anchor_point(self):
        """Test SymbolInfo with explicit anchor point."""
        anchor = Point(x=50.0, y=25.0)
        symbol = SymbolInfo(
            symbol_id="PP001A",
            name="Centrifugal Pump",
            category=SymbolCategory.PUMPS,
            anchor_point=anchor
        )

        assert symbol.anchor_point is not None
        assert symbol.anchor_point.x == 50.0
        assert symbol.anchor_point.y == 25.0

    def test_symbol_info_with_ports(self):
        """Test SymbolInfo with ports list."""
        ports = [
            Port(id="inlet", x=0.0, y=25.0, direction="W", type="inlet", flow_direction="in"),
            Port(id="outlet", x=100.0, y=25.0, direction="E", type="outlet", flow_direction="out")
        ]
        symbol = SymbolInfo(
            symbol_id="PP001A",
            name="Centrifugal Pump",
            category=SymbolCategory.PUMPS,
            ports=ports
        )

        assert len(symbol.ports) == 2
        assert symbol.ports[0].id == "inlet"
        assert symbol.ports[1].id == "outlet"

    def test_symbol_info_get_anchor_explicit(self):
        """Test get_anchor returns explicit anchor when set."""
        anchor = Point(x=30.0, y=40.0)
        bb = BoundingBox(x=0.0, y=0.0, width=100.0, height=50.0)

        symbol = SymbolInfo(
            symbol_id="PP001A",
            name="Centrifugal Pump",
            category=SymbolCategory.PUMPS,
            bounding_box=bb,
            anchor_point=anchor
        )

        result = symbol.get_anchor()
        assert result.x == 30.0  # Should use explicit anchor
        assert result.y == 40.0

    def test_symbol_info_get_anchor_from_bounding_box(self):
        """Test get_anchor derives from bounding box center when no explicit anchor."""
        bb = BoundingBox(x=0.0, y=0.0, width=100.0, height=50.0)

        symbol = SymbolInfo(
            symbol_id="PP001A",
            name="Centrifugal Pump",
            category=SymbolCategory.PUMPS,
            bounding_box=bb
        )

        result = symbol.get_anchor()
        assert result.x == 50.0  # Box center
        assert result.y == 25.0

    def test_symbol_info_get_anchor_none(self):
        """Test get_anchor returns None when no geometry."""
        symbol = SymbolInfo(
            symbol_id="PP001A",
            name="Centrifugal Pump",
            category=SymbolCategory.PUMPS
        )

        result = symbol.get_anchor()
        assert result is None

    def test_symbol_info_render_hints(self):
        """Test render hints can be customized."""
        symbol = SymbolInfo(
            symbol_id="IM001A",
            name="Pressure Indicator",
            category=SymbolCategory.INSTRUMENTATION,
            scalable=False,  # Some instruments shouldn't scale
            rotatable=True
        )

        assert symbol.scalable is False
        assert symbol.rotatable is True

    def test_symbol_info_backward_compatibility(self):
        """Test existing code works without geometry fields."""
        # Create symbol the old way - should still work
        symbol = SymbolInfo(
            symbol_id="PV019A",
            name="Ball Valve",
            category=SymbolCategory.VALVES,
            dexpi_class="BallValve",
            file_path="NOAKADEXPI/PV019A.svg",
            source=SymbolSource.NOAKADEXPI
        )

        assert symbol.symbol_id == "PV019A"
        assert symbol.dexpi_class == "BallValve"
        assert symbol.bounding_box is None
        assert symbol.ports == []


class TestSymbolInfoFullGeometry:
    """Integration tests for complete geometry setup."""

    def test_pump_with_full_geometry(self):
        """Test pump symbol with complete geometry configuration."""
        # Define typical pump geometry
        bb = BoundingBox(x=0.0, y=0.0, width=80.0, height=60.0)
        ports = [
            Port(id="suction", x=0.0, y=30.0, direction="W", type="inlet", flow_direction="in"),
            Port(id="discharge", x=80.0, y=30.0, direction="E", type="outlet", flow_direction="out"),
            Port(id="vent", x=40.0, y=0.0, direction="N", type="auxiliary", flow_direction="out")
        ]

        symbol = SymbolInfo(
            symbol_id="PP001A",
            name="Centrifugal Pump",
            category=SymbolCategory.PUMPS,
            dexpi_class="CentrifugalPump",
            bounding_box=bb,
            ports=ports,
            scalable=True,
            rotatable=True
        )

        # Verify full setup
        assert symbol.get_anchor().x == 40.0  # Center of 80-wide box
        assert len(symbol.ports) == 3
        assert symbol.ports[0].direction == "W"
        assert symbol.ports[1].direction == "E"

    def test_tank_with_multiple_ports(self):
        """Test tank symbol with multiple nozzle ports."""
        bb = BoundingBox(x=0.0, y=0.0, width=100.0, height=150.0)
        ports = [
            Port(id="N1", x=25.0, y=0.0, direction="N", type="inlet", flow_direction="in"),
            Port(id="N2", x=75.0, y=0.0, direction="N", type="inlet", flow_direction="in"),
            Port(id="S1", x=50.0, y=150.0, direction="S", type="outlet", flow_direction="out"),
            Port(id="E1", x=100.0, y=75.0, direction="E", type="auxiliary", flow_direction="bidirectional")
        ]

        symbol = SymbolInfo(
            symbol_id="PT001A",
            name="Vertical Tank",
            category=SymbolCategory.TANKS,
            dexpi_class="Tank",
            bounding_box=bb,
            ports=ports
        )

        assert len(symbol.ports) == 4
        inlet_ports = [p for p in symbol.ports if p.type == "inlet"]
        assert len(inlet_ports) == 2


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
