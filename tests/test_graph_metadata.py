"""Tests for graph metadata validators.

These tests verify that the Pydantic schemas correctly validate NetworkX
graph attributes from pyDEXPI and SFILES2 without replacing upstream formats.
"""

import pytest
import networkx as nx
from src.models.graph_metadata import (
    NodeMetadata,
    EdgeMetadata,
    GraphMetadata,
    GraphMetadataSerializer,
)


class TestNodeMetadata:
    """Test NodeMetadata validation of pyDEXPI/SFILES2 node attributes."""

    def test_validate_pydexpi_node(self):
        """Test validation of pyDEXPI node attributes."""
        attrs = {
            "dexpi_class": "Tank",
            "equipment_tag": "TK-101",
            "pos": [100.0, 200.0]
        }
        node = NodeMetadata(**attrs)
        assert node.dexpi_class == "Tank"
        assert node.equipment_tag == "TK-101"
        assert node.pos == [100.0, 200.0]

    def test_validate_sfiles_node(self):
        """Test validation of SFILES2 node attributes."""
        attrs = {
            "unit_type": "reactor",
            "unit_type_specific": {"volume": 1000},
            "pos": [50.0, 150.0]
        }
        node = NodeMetadata(**attrs)
        assert node.unit_type == "reactor"
        assert node.unit_type_specific == {"volume": 1000}
        assert node.pos == [50.0, 150.0]

    def test_validate_position_format(self):
        """Test position validation requires [x, y] pair."""
        with pytest.raises(ValueError, match="Position must be \\[x, y\\]"):
            NodeMetadata(pos=[100.0])  # Invalid: only one coordinate

        with pytest.raises(ValueError, match="Position must be \\[x, y\\]"):
            NodeMetadata(pos=[100.0, 200.0, 300.0])  # Invalid: three coordinates

    def test_allow_extra_fields(self):
        """Test that extra upstream-specific fields are preserved."""
        attrs = {
            "dexpi_class": "Pump",
            "custom_field": "custom_value",
            "another_field": 42
        }
        node = NodeMetadata(**attrs)
        node_dict = node.to_dict(exclude_none=False)
        assert "custom_field" in node_dict
        assert node_dict["custom_field"] == "custom_value"
        assert node_dict["another_field"] == 42

    def test_deterministic_serialization(self):
        """Test that to_dict produces sorted keys for git-friendly diffs."""
        attrs = {
            "z_field": "last",
            "a_field": "first",
            "m_field": "middle",
            "pos": [0.0, 0.0]
        }
        node = NodeMetadata(**attrs)
        node_dict = node.to_dict()
        keys = list(node_dict.keys())
        assert keys == sorted(keys), "Keys should be sorted alphabetically"


class TestEdgeMetadata:
    """Test EdgeMetadata validation of pyDEXPI/SFILES2 edge attributes."""

    def test_validate_sfiles_edge(self):
        """Test validation of SFILES2 edge attributes."""
        attrs = {
            "tags": {"he": ["HX-101"], "col": []},
            "processstream_name": "S1"
        }
        edge = EdgeMetadata(**attrs)
        assert edge.tags == {"he": ["HX-101"], "col": []}
        assert edge.processstream_name == "S1"

    def test_validate_pydexpi_edge(self):
        """Test validation of pyDEXPI edge attributes."""
        attrs = {
            "piping_class": "CS150",
            "line_number": "L-101"
        }
        edge = EdgeMetadata(**attrs)
        assert edge.piping_class == "CS150"
        assert edge.line_number == "L-101"

    def test_sfiles_tags_validation(self):
        """Test SFILES2 tags structure validation."""
        # Valid tags
        attrs = {"tags": {"he": [], "col": ["COL-101"]}}
        edge = EdgeMetadata(**attrs)
        assert edge.tags["col"] == ["COL-101"]

        # Invalid: missing 'he' key
        with pytest.raises(ValueError, match="must have 'he' and 'col' keys"):
            EdgeMetadata(tags={"col": []})

        # Invalid: missing 'col' key
        with pytest.raises(ValueError, match="must have 'he' and 'col' keys"):
            EdgeMetadata(tags={"he": []})

        # Invalid: values not lists (Pydantic type checking catches this)
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            EdgeMetadata(tags={"he": "not_a_list", "col": []})

    def test_deterministic_serialization(self):
        """Test that to_dict produces sorted keys."""
        attrs = {
            "z_field": "last",
            "a_field": "first",
            "tags": {"he": [], "col": []}
        }
        edge = EdgeMetadata(**attrs)
        edge_dict = edge.to_dict()
        keys = list(edge_dict.keys())
        assert keys == sorted(keys)


class TestGraphMetadata:
    """Test GraphMetadata validation of graph-level attributes."""

    def test_validate_bfd_metadata(self):
        """Test BFD metadata validation."""
        metadata = GraphMetadata(
            diagram_type="BFD",
            diagram_level=0,
            source_format="sfiles",
            project_name="Test Plant"
        )
        assert metadata.diagram_type == "BFD"
        assert metadata.diagram_level == 0
        assert metadata.source_format == "sfiles"

    def test_validate_pfd_metadata(self):
        """Test PFD metadata validation."""
        metadata = GraphMetadata(
            diagram_type="PFD",
            diagram_level=1,
            source_format="sfiles",
            traceability=["bfd_001"]
        )
        assert metadata.diagram_level == 1
        assert metadata.traceability == ["bfd_001"]

    def test_validate_pid_metadata(self):
        """Test P&ID metadata validation."""
        metadata = GraphMetadata(
            diagram_type="PID",
            diagram_level=2,
            source_format="dexpi",
            drawing_number="PID-001",
            traceability=["bfd_001", "pfd_001"]
        )
        assert metadata.diagram_level == 2
        assert metadata.drawing_number == "PID-001"

    def test_diagram_level_consistency(self):
        """Test that diagram_level matches diagram_type."""
        # Valid combinations
        GraphMetadata(diagram_type="BFD", diagram_level=0, source_format="sfiles")
        GraphMetadata(diagram_type="PFD", diagram_level=1, source_format="sfiles")
        GraphMetadata(diagram_type="PID", diagram_level=2, source_format="dexpi")

        # Invalid: BFD with level 1
        with pytest.raises(ValueError, match="BFD must have diagram_level=0"):
            GraphMetadata(diagram_type="BFD", diagram_level=1, source_format="sfiles")

        # Invalid: PFD with level 2
        with pytest.raises(ValueError, match="PFD must have diagram_level=1"):
            GraphMetadata(diagram_type="PFD", diagram_level=2, source_format="sfiles")


class TestGraphMetadataSerializer:
    """Test round-trip serialization of NetworkX graphs."""

    def test_serialize_simple_graph(self):
        """Test serialization of simple graph."""
        # Create graph
        graph = nx.DiGraph()
        graph.add_node("N1", unit_type="reactor", pos=[0.0, 0.0])
        graph.add_node("N2", unit_type="tank", pos=[100.0, 0.0])
        graph.add_edge("N1", "N2", tags={"he": [], "col": []})

        metadata = GraphMetadata(
            diagram_type="BFD",
            diagram_level=0,
            source_format="sfiles"
        )

        # Serialize
        serializer = GraphMetadataSerializer()
        json_str = serializer.to_json(graph, metadata)

        assert "N1" in json_str
        assert "N2" in json_str
        assert "reactor" in json_str
        assert "tank" in json_str

    def test_round_trip_preserves_data(self):
        """Test that to_json → from_json preserves all data."""
        # Create original graph
        original_graph = nx.DiGraph()
        original_graph.add_node("N1", dexpi_class="Pump", pos=[50.0, 50.0])
        original_graph.add_node("N2", dexpi_class="Tank", pos=[150.0, 50.0])
        original_graph.add_edge("N1", "N2", piping_class="CS150")

        original_metadata = GraphMetadata(
            diagram_type="PID",
            diagram_level=2,
            source_format="dexpi",
            drawing_number="PID-001"
        )

        # Round-trip
        serializer = GraphMetadataSerializer()
        json_str = serializer.to_json(original_graph, original_metadata)
        restored_graph, restored_metadata = serializer.from_json(json_str)

        # Verify graph structure
        assert list(restored_graph.nodes()) == list(original_graph.nodes())
        assert list(restored_graph.edges()) == list(original_graph.edges())

        # Verify node attributes
        assert restored_graph.nodes["N1"]["dexpi_class"] == "Pump"
        assert restored_graph.nodes["N1"]["pos"] == [50.0, 50.0]
        assert restored_graph.nodes["N2"]["dexpi_class"] == "Tank"

        # Verify edge attributes
        assert restored_graph.edges["N1", "N2"]["piping_class"] == "CS150"

        # Verify metadata
        assert restored_metadata.diagram_type == "PID"
        assert restored_metadata.diagram_level == 2
        assert restored_metadata.drawing_number == "PID-001"

    def test_validate_graph_success(self):
        """Test graph validation with valid attributes."""
        graph = nx.Graph()
        graph.add_node("N1", unit_type="reactor", pos=[0.0, 0.0])
        graph.add_node("N2", unit_type="tank", pos=[100.0, 0.0])
        graph.add_edge("N1", "N2", tags={"he": [], "col": []})

        serializer = GraphMetadataSerializer()
        report = serializer.validate_graph(graph)

        assert report["valid"] is True
        assert report["nodes_validated"] == 2  # Both N1 and N2
        assert report["edges_validated"] == 1
        assert len(report["errors"]) == 0

    def test_validate_graph_failure(self):
        """Test graph validation with invalid attributes."""
        graph = nx.Graph()
        graph.add_node("N1", pos=[0.0])  # Invalid: position needs [x, y]

        serializer = GraphMetadataSerializer()
        report = serializer.validate_graph(graph)

        assert report["valid"] is False
        assert len(report["errors"]) == 1
        assert report["errors"][0]["type"] == "node"
        assert report["errors"][0]["id"] == "N1"
        assert "Position must be [x, y]" in report["errors"][0]["error"]
