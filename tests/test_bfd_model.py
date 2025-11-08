"""Tests for BFD (Block Flow Diagram) models.

These tests verify Pydantic validation schemas for BFD operations
integrated with SFILES2 tools (Sprint 2 - Codex Review #6 minimal approach).
"""

import pytest
from pydantic import ValidationError
from src.models.bfd import (
    BfdPortType,
    BfdPortSpec,
    BfdCreateArgs,
    BfdBlockArgs,
    BfdFlowArgs,
    BfdBlockMetadata,
    BfdFlowMetadata,
    BfdToPfdExpansionOption,
    BfdToPfdExpansionPlan,
)
from src.models.port_spec import CardinalDirection


class TestBfdPortType:
    """Test BfdPortType enumeration."""

    def test_valid_port_types(self):
        """Test all valid BFD port types."""
        assert BfdPortType.INPUT == "input"
        assert BfdPortType.OUTPUT == "output"
        assert BfdPortType.BIDIRECTIONAL == "bidirectional"

    def test_port_type_values(self):
        """Test creating port types from strings."""
        assert BfdPortType("input") == BfdPortType.INPUT
        assert BfdPortType("output") == BfdPortType.OUTPUT
        assert BfdPortType("bidirectional") == BfdPortType.BIDIRECTIONAL


class TestBfdPortSpec:
    """Test BfdPortSpec model (extends Sprint 1 PortSpec)."""

    def test_create_input_port(self):
        """Test creating input port specification."""
        port = BfdPortSpec(
            port_id="inlet",
            cardinal_direction=CardinalDirection.WEST,
            port_type=BfdPortType.INPUT,
            stream_type="material"
        )
        assert port.port_id == "inlet"
        assert port.cardinal_direction == CardinalDirection.WEST
        assert port.port_type == BfdPortType.INPUT
        assert port.stream_type == "material"

    def test_create_output_port(self):
        """Test creating output port specification."""
        port = BfdPortSpec(
            port_id="outlet",
            cardinal_direction=CardinalDirection.EAST,
            port_type=BfdPortType.OUTPUT,
            stream_type="material"
        )
        assert port.port_type == BfdPortType.OUTPUT

    def test_bidirectional_port(self):
        """Test creating bidirectional port."""
        port = BfdPortSpec(
            port_id="service",
            cardinal_direction=CardinalDirection.SOUTH,
            port_type=BfdPortType.BIDIRECTIONAL,
            stream_type="energy"
        )
        assert port.port_type == BfdPortType.BIDIRECTIONAL

    def test_optional_stream_type(self):
        """Test that stream_type is optional."""
        port = BfdPortSpec(
            port_id="generic",
            cardinal_direction=CardinalDirection.NORTH,
            port_type=BfdPortType.INPUT
        )
        assert port.stream_type is None

    def test_canonical_port_spec_optional(self):
        """Test that canonical PortSpec is optional (Codex Review #7)."""
        port = BfdPortSpec(
            port_id="inlet",
            cardinal_direction=CardinalDirection.WEST,
            port_type=BfdPortType.INPUT
        )
        assert port.canonical is None  # Not populated during BFD modeling

    def test_canonical_port_spec_population(self):
        """Test populating canonical PortSpec during expansion (Codex Review #7)."""
        from src.models.port_spec import PortSpec, NumberOfPortsClassification

        # Create BFD port
        bfd_port = BfdPortSpec(
            port_id="inlet",
            cardinal_direction=CardinalDirection.WEST,
            port_type=BfdPortType.INPUT
        )

        # Simulate Sprint 3 expansion: populate canonical field
        canonical_port = PortSpec(
            dexpi_classification=NumberOfPortsClassification.TwoPortValve,
            cardinal_direction=CardinalDirection.WEST,
            sub_tag="N1",
            nominal_diameter="DN50"
        )
        bfd_port.canonical = canonical_port

        # Verify canonical field is populated
        assert bfd_port.canonical is not None
        assert bfd_port.canonical.dexpi_classification == NumberOfPortsClassification.TwoPortValve
        assert bfd_port.canonical.nominal_diameter == "DN50"

        # Verify BFD-level metadata still accessible
        assert bfd_port.port_type == BfdPortType.INPUT
        assert bfd_port.cardinal_direction == CardinalDirection.WEST


class TestBfdCreateArgs:
    """Test BfdCreateArgs validation schema."""

    def test_minimal_valid_args(self):
        """Test creating BFD with minimal required fields."""
        args = BfdCreateArgs(name="Wastewater Treatment Plant")
        assert args.name == "Wastewater Treatment Plant"
        assert args.type == "BFD"
        assert args.description is None
        assert args.flowsheet_id is None

    def test_full_args(self):
        """Test creating BFD with all fields."""
        args = BfdCreateArgs(
            name="Plant A",
            type="BFD",
            description="Main treatment facility",
            flowsheet_id="test-id-123"
        )
        assert args.description == "Main treatment facility"
        assert args.flowsheet_id == "test-id-123"

    def test_type_must_be_bfd(self):
        """Test that type field must be 'BFD'."""
        with pytest.raises(ValidationError):
            BfdCreateArgs(name="Test", type="PFD")

    def test_name_required(self):
        """Test that name is required."""
        with pytest.raises(ValidationError):
            BfdCreateArgs()

    def test_name_length_validation(self):
        """Test name length constraints."""
        # Empty name should fail
        with pytest.raises(ValidationError):
            BfdCreateArgs(name="")

        # Very long name (over 200 chars) should fail
        with pytest.raises(ValidationError):
            BfdCreateArgs(name="x" * 201)


class TestBfdBlockArgs:
    """Test BfdBlockArgs validation schema."""

    def test_minimal_valid_args(self):
        """Test creating BFD block with minimal fields."""
        args = BfdBlockArgs(
            flowsheet_id="fs-123",
            unit_type="Aeration Tank"
        )
        assert args.flowsheet_id == "fs-123"
        assert args.unit_type == "Aeration Tank"
        assert args.unit_name is None
        assert args.sequence_number is None
        assert args.allow_custom is False
        assert args.parameters == {}

    def test_full_args(self):
        """Test creating BFD block with all fields."""
        args = BfdBlockArgs(
            flowsheet_id="fs-123",
            unit_type="Aeration Tank",
            unit_name="Main Aeration Basin",
            sequence_number=1,
            parameters={"volume": 1000, "detention_time": 6},
            allow_custom=True
        )
        assert args.unit_name == "Main Aeration Basin"
        assert args.sequence_number == 1
        assert args.parameters["volume"] == 1000
        assert args.allow_custom is True

    def test_sequence_number_validation(self):
        """Test that sequence_number must be >= 1."""
        with pytest.raises(ValidationError):
            BfdBlockArgs(
                flowsheet_id="fs-123",
                unit_type="Tank",
                sequence_number=0  # Invalid
            )

    def test_with_port_specs(self):
        """Test adding typed ports to block."""
        port1 = BfdPortSpec(
            port_id="inlet",
            cardinal_direction=CardinalDirection.WEST,
            port_type=BfdPortType.INPUT
        )
        port2 = BfdPortSpec(
            port_id="outlet",
            cardinal_direction=CardinalDirection.EAST,
            port_type=BfdPortType.OUTPUT
        )

        args = BfdBlockArgs(
            flowsheet_id="fs-123",
            unit_type="Tank",
            port_specs=[port1, port2]
        )
        assert len(args.port_specs) == 2
        assert args.port_specs[0].port_type == BfdPortType.INPUT


class TestBfdFlowArgs:
    """Test BfdFlowArgs validation schema."""

    def test_minimal_valid_args(self):
        """Test creating BFD flow with minimal fields."""
        args = BfdFlowArgs(
            flowsheet_id="fs-123",
            from_unit="PrimaryClarification-01",
            to_unit="AerationTank-01"
        )
        assert args.flowsheet_id == "fs-123"
        assert args.from_unit == "PrimaryClarification-01"
        assert args.to_unit == "AerationTank-01"
        assert args.stream_name is None
        assert args.stream_type is None
        assert args.properties == {}

    def test_full_args(self):
        """Test creating BFD flow with all fields."""
        args = BfdFlowArgs(
            flowsheet_id="fs-123",
            from_unit="Tank-01",
            to_unit="Tank-02",
            stream_name="primary_effluent",
            stream_type="material",
            properties={"flow_rate": 1000, "temperature": 20}
        )
        assert args.stream_name == "primary_effluent"
        assert args.stream_type == "material"
        assert args.properties["flow_rate"] == 1000

    def test_required_fields(self):
        """Test that from_unit and to_unit are required."""
        with pytest.raises(ValidationError):
            BfdFlowArgs(
                flowsheet_id="fs-123",
                from_unit="Tank-01"
                # Missing to_unit
            )


class TestBfdBlockMetadata:
    """Test BfdBlockMetadata (extends Sprint 1 NodeMetadata)."""

    def test_minimal_metadata(self):
        """Test BFD block metadata with minimal fields."""
        metadata = BfdBlockMetadata(
            node_id="AS-01",
            node_type="process_block"
        )
        assert metadata.node_id == "AS-01"
        assert metadata.equipment_tag is None
        assert metadata.area_number is None

    def test_full_bfd_metadata(self):
        """Test BFD block metadata with all BFD-specific fields."""
        metadata = BfdBlockMetadata(
            node_id="AS-01",
            node_type="process_block",
            equipment_tag="201-AS-01",
            area_number=201,
            process_unit_id="AS",
            sequence_number=1,
            category="Secondary Treatment",
            subcategory="Activated Sludge",
            is_custom=False
        )
        assert metadata.equipment_tag == "201-AS-01"
        assert metadata.area_number == 201
        assert metadata.process_unit_id == "AS"
        assert metadata.sequence_number == 1
        assert metadata.category == "Secondary Treatment"

    def test_sequence_number_validation(self):
        """Test sequence_number >= 1 constraint."""
        with pytest.raises(ValidationError):
            BfdBlockMetadata(
                node_id="AS-01",
                node_type="process_block",
                sequence_number=0  # Invalid
            )


class TestBfdFlowMetadata:
    """Test BfdFlowMetadata (extends Sprint 1 EdgeMetadata)."""

    def test_minimal_metadata(self):
        """Test BFD flow metadata with minimal fields."""
        metadata = BfdFlowMetadata(
            edge_id="flow-01",
            source="AS-01",
            target="SC-01"
        )
        assert metadata.edge_id == "flow-01"
        assert metadata.stream_type is None
        assert metadata.flow_direction is None

    def test_full_bfd_metadata(self):
        """Test BFD flow metadata with all BFD-specific fields."""
        metadata = BfdFlowMetadata(
            edge_id="flow-01",
            source="AS-01",
            target="SC-01",
            stream_type="material",
            flow_direction="forward"
        )
        assert metadata.stream_type == "material"
        assert metadata.flow_direction == "forward"


class TestBfdToPfdExpansionOption:
    """Test BfdToPfdExpansionOption model."""

    def test_create_expansion_option(self):
        """Test creating PFD expansion option."""
        option = BfdToPfdExpansionOption(
            equipment_type="clarifier",
            description="Circular primary clarifier",
            typical_count=2,
            configuration="parallel"
        )
        assert option.equipment_type == "clarifier"
        assert option.typical_count == 2
        assert option.configuration == "parallel"

    def test_typical_count_validation(self):
        """Test typical_count >= 1 constraint."""
        with pytest.raises(ValidationError):
            BfdToPfdExpansionOption(
                equipment_type="tank",
                description="Test",
                typical_count=0  # Invalid
            )


class TestBfdToPfdExpansionPlan:
    """Test BfdToPfdExpansionPlan model."""

    def test_create_expansion_plan(self):
        """Test creating complete expansion plan."""
        option1 = BfdToPfdExpansionOption(
            equipment_type="clarifier",
            description="Circular clarifier",
            typical_count=2
        )
        option2 = BfdToPfdExpansionOption(
            equipment_type="clarifier",
            description="Rectangular clarifier",
            typical_count=2
        )

        plan = BfdToPfdExpansionPlan(
            bfd_block="PrimaryClarification-01",
            process_type="Primary Clarification",
            pfd_options=[option1, option2],
            recommended_option=0
        )

        assert plan.bfd_block == "PrimaryClarification-01"
        assert plan.process_type == "Primary Clarification"
        assert len(plan.pfd_options) == 2
        assert plan.recommended_option == 0

    def test_optional_recommendation(self):
        """Test that recommended_option is optional."""
        option = BfdToPfdExpansionOption(
            equipment_type="tank",
            description="Test",
            typical_count=1
        )

        plan = BfdToPfdExpansionPlan(
            bfd_block="Block-01",
            process_type="Generic",
            pfd_options=[option]
        )

        assert plan.recommended_option is None

    def test_recommended_option_validation(self):
        """Test recommended_option >= 0 constraint."""
        option = BfdToPfdExpansionOption(
            equipment_type="tank",
            description="Test",
            typical_count=1
        )

        with pytest.raises(ValidationError):
            BfdToPfdExpansionPlan(
                bfd_block="Block-01",
                process_type="Generic",
                pfd_options=[option],
                recommended_option=-1  # Invalid
            )
