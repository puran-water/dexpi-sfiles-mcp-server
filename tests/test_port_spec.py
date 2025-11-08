"""Tests for port specification wrappers.

These tests verify that PortSpec correctly wraps DEXPI port enumerations
without replacing them, and provides useful layout utilities.
"""

import pytest
from src.models.port_spec import (
    NumberOfPortsClassification,
    PortStatusClassification,
    CardinalDirection,
    PortSpec,
    PortLayout,
)


class TestPortSpec:
    """Test PortSpec wrapper around DEXPI enumerations."""

    def test_create_port_with_dexpi_enums(self):
        """Test creating port with DEXPI official enumerations."""
        port = PortSpec(
            dexpi_classification=NumberOfPortsClassification.TwoPortValve,
            dexpi_status=PortStatusClassification.StatusHighPort,
            sub_tag="N1",
            nominal_diameter="DN50"
        )

        assert port.dexpi_classification == NumberOfPortsClassification.TwoPortValve
        assert port.dexpi_status == PortStatusClassification.StatusHighPort
        assert port.sub_tag == "N1"
        assert port.nominal_diameter == "DN50"

    def test_port_with_cardinal_direction_hint(self):
        """Test that cardinal direction is OPTIONAL derived hint."""
        port = PortSpec(
            dexpi_classification=NumberOfPortsClassification.TwoPortValve,
            cardinal_direction=CardinalDirection.NORTH
        )

        # Cardinal direction is present but optional
        assert port.cardinal_direction == CardinalDirection.NORTH

        # Can create port without cardinal direction
        port_no_cardinal = PortSpec(
            dexpi_classification=NumberOfPortsClassification.TwoPortValve
        )
        assert port_no_cardinal.cardinal_direction is None

    def test_from_dexpi_nozzle_factory(self):
        """Test factory method for creating ports from DEXPI nozzle data."""
        port = PortSpec.from_dexpi_nozzle(
            sub_tag="N1",
            nominal_diameter="DN50",
            nominal_pressure="PN16",
            cardinal_hint=CardinalDirection.EAST
        )

        assert port.sub_tag == "N1"
        assert port.nominal_diameter == "DN50"
        assert port.nominal_pressure == "PN16"
        assert port.cardinal_direction == CardinalDirection.EAST
        assert port.dexpi_classification == NumberOfPortsClassification.TwoPortValve

    def test_to_dict_serialization(self):
        """Test port serialization to dict."""
        port = PortSpec(
            dexpi_classification=NumberOfPortsClassification.TwoPortValve,
            dexpi_status=PortStatusClassification.StatusHighPort,
            sub_tag="N1",
            cardinal_direction=CardinalDirection.NORTH
        )

        port_dict = port.to_dict()

        # Keys should be sorted
        keys = list(port_dict.keys())
        assert keys == sorted(keys)

        # Enums should be serialized as strings
        assert isinstance(port_dict["dexpi_classification"], str)
        assert port_dict["dexpi_classification"] == "2 port valve"
        assert port_dict["dexpi_status"] == "H"
        assert port_dict["cardinal_direction"] == "N"

    def test_port_preserves_dexpi_enums(self):
        """Test that DEXPI enums are preserved (not replaced)."""
        port = PortSpec(
            dexpi_classification=NumberOfPortsClassification.ThreePortValve,
            dexpi_status=PortStatusClassification.StatusLowPort
        )

        # Should preserve DEXPI enum types
        assert isinstance(port.dexpi_classification, NumberOfPortsClassification)
        assert isinstance(port.dexpi_status, PortStatusClassification)

        # Values match DEXPI spec (note: values are different from names!)
        assert port.dexpi_classification.value == "3 port valve"
        assert port.dexpi_status.value == "L"


class TestPortLayout:
    """Test PortLayout helper for computing port positions."""

    def test_get_port_offset_north(self):
        """Test north port offset."""
        offset = PortLayout.get_port_offset(
            CardinalDirection.NORTH,
            equipment_width=100.0,
            equipment_height=50.0
        )

        assert offset == (0.0, -25.0)  # Top center

    def test_get_port_offset_south(self):
        """Test south port offset."""
        offset = PortLayout.get_port_offset(
            CardinalDirection.SOUTH,
            equipment_width=100.0,
            equipment_height=50.0
        )

        assert offset == (0.0, 25.0)  # Bottom center

    def test_get_port_offset_east(self):
        """Test east port offset."""
        offset = PortLayout.get_port_offset(
            CardinalDirection.EAST,
            equipment_width=100.0,
            equipment_height=50.0
        )

        assert offset == (50.0, 0.0)  # Right center

    def test_get_port_offset_west(self):
        """Test west port offset."""
        offset = PortLayout.get_port_offset(
            CardinalDirection.WEST,
            equipment_width=100.0,
            equipment_height=50.0
        )

        assert offset == (-50.0, 0.0)  # Left center

    def test_distribute_single_port(self):
        """Test distributing single port."""
        positions = PortLayout.distribute_ports(
            count=1,
            direction=CardinalDirection.NORTH,
            equipment_width=100.0,
            equipment_height=50.0
        )

        assert len(positions) == 1
        assert positions[0] == (0.0, -25.0)

    def test_distribute_multiple_ports_horizontal(self):
        """Test distributing multiple ports on north/south side."""
        positions = PortLayout.distribute_ports(
            count=3,
            direction=CardinalDirection.NORTH,
            equipment_width=100.0,
            equipment_height=50.0,
            spacing=20.0
        )

        assert len(positions) == 3
        # Should be distributed horizontally along north edge
        assert positions[0] == (-20.0, -25.0)  # Left
        assert positions[1] == (0.0, -25.0)     # Center
        assert positions[2] == (20.0, -25.0)    # Right

    def test_distribute_multiple_ports_vertical(self):
        """Test distributing multiple ports on east/west side."""
        positions = PortLayout.distribute_ports(
            count=3,
            direction=CardinalDirection.EAST,
            equipment_width=100.0,
            equipment_height=50.0,
            spacing=15.0
        )

        assert len(positions) == 3
        # Should be distributed vertically along east edge
        assert positions[0] == (50.0, -15.0)  # Top
        assert positions[1] == (50.0, 0.0)     # Middle
        assert positions[2] == (50.0, 15.0)    # Bottom

    def test_distribute_zero_ports(self):
        """Test distributing zero ports."""
        positions = PortLayout.distribute_ports(
            count=0,
            direction=CardinalDirection.NORTH,
            equipment_width=100.0,
            equipment_height=50.0
        )

        assert positions == []


class TestCardinalDirection:
    """Test CardinalDirection enum."""

    def test_cardinal_directions_exist(self):
        """Test that all four cardinal directions are defined."""
        assert CardinalDirection.NORTH.value == "N"
        assert CardinalDirection.SOUTH.value == "S"
        assert CardinalDirection.EAST.value == "E"
        assert CardinalDirection.WEST.value == "W"

    def test_cardinal_direction_from_string(self):
        """Test creating cardinal direction from string."""
        assert CardinalDirection("N") == CardinalDirection.NORTH
        assert CardinalDirection("S") == CardinalDirection.SOUTH
        assert CardinalDirection("E") == CardinalDirection.EAST
        assert CardinalDirection("W") == CardinalDirection.WEST


class TestDEXPIEnumCompatibility:
    """Test compatibility with DEXPI official enumerations."""

    def test_number_of_ports_classification(self):
        """Test NumberOfPortsClassification matches DEXPI spec."""
        # These should match pyDEXPI's enumerations
        assert hasattr(NumberOfPortsClassification, "TwoPortValve")
        assert hasattr(NumberOfPortsClassification, "ThreePortValve")
        assert hasattr(NumberOfPortsClassification, "FourPortValve")

        # Values should match DEXPI spec (note: values != names)
        assert NumberOfPortsClassification.TwoPortValve.value == "2 port valve"
        assert NumberOfPortsClassification.ThreePortValve.value == "3 port valve"

    def test_port_status_classification(self):
        """Test PortStatusClassification matches DEXPI spec."""
        # These should match pyDEXPI's enumerations
        assert hasattr(PortStatusClassification, "StatusHighPort")
        assert hasattr(PortStatusClassification, "StatusLowPort")

        # Values should match DEXPI spec (note: values != names)
        assert PortStatusClassification.StatusHighPort.value == "H"
        assert PortStatusClassification.StatusLowPort.value == "L"

    def test_dexpi_enums_are_imported(self):
        """Test that we're using pyDEXPI enums when available."""
        # This test documents that we import from pyDEXPI
        # (or use fallbacks if not installed)
        from src.models.port_spec import DEXPI_AVAILABLE

        # If DEXPI is available, we should be using real enums
        if DEXPI_AVAILABLE:
            # Verify we're importing from pyDEXPI
            import pydexpi.dexpi_classes.pydantic_classes as pydexpi_classes
            from src.models.port_spec import NumberOfPortsClassification as OurEnum

            # Should be the same class (not a copy)
            assert OurEnum is pydexpi_classes.NumberOfPortsClassification
