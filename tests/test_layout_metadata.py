"""Tests for layout metadata models.

These tests verify that layout metadata correctly captures and persists
positioning information from upstream utilities (SFILES2's _add_positions).
"""

import pytest
import networkx as nx
from src.models.layout_metadata import (
    NodePosition,
    BoundingBox,
    LayoutMetadata,
    LayoutCollection,
)


class TestNodePosition:
    """Test NodePosition model."""

    def test_create_2d_position(self):
        """Test creating 2D position."""
        pos = NodePosition(x=100.0, y=200.0)
        assert pos.x == 100.0
        assert pos.y == 200.0
        assert pos.z is None

    def test_create_3d_position(self):
        """Test creating 3D position."""
        pos = NodePosition(x=100.0, y=200.0, z=300.0)
        assert pos.x == 100.0
        assert pos.y == 200.0
        assert pos.z == 300.0

    def test_from_list_2d(self):
        """Test creating from [x, y] list."""
        pos = NodePosition.from_list([100.0, 200.0])
        assert pos.x == 100.0
        assert pos.y == 200.0
        assert pos.z is None

    def test_from_list_3d(self):
        """Test creating from [x, y, z] list."""
        pos = NodePosition.from_list([100.0, 200.0, 300.0])
        assert pos.x == 100.0
        assert pos.y == 200.0
        assert pos.z == 300.0

    def test_from_list_invalid_length(self):
        """Test that invalid list length raises error."""
        with pytest.raises(ValueError, match="must be \\[x, y\\] or \\[x, y, z\\]"):
            NodePosition.from_list([100.0])  # Only one element

        with pytest.raises(ValueError, match="must be \\[x, y\\] or \\[x, y, z\\]"):
            NodePosition.from_list([100.0, 200.0, 300.0, 400.0])  # Four elements

    def test_to_list_2d(self):
        """Test converting 2D position to list."""
        pos = NodePosition(x=100.0, y=200.0)
        assert pos.to_list() == [100.0, 200.0]

    def test_to_list_3d(self):
        """Test converting 3D position to list."""
        pos = NodePosition(x=100.0, y=200.0, z=300.0)
        assert pos.to_list() == [100.0, 200.0, 300.0]

    def test_to_list_with_include_z(self):
        """Test converting 2D position to 3D list with z=0."""
        pos = NodePosition(x=100.0, y=200.0)
        assert pos.to_list(include_z=True) == [100.0, 200.0, 0.0]


class TestBoundingBox:
    """Test BoundingBox model."""

    def test_create_bounding_box(self):
        """Test creating bounding box."""
        bbox = BoundingBox(min_x=0.0, max_x=100.0, min_y=0.0, max_y=50.0)
        assert bbox.min_x == 0.0
        assert bbox.max_x == 100.0
        assert bbox.min_y == 0.0
        assert bbox.max_y == 50.0

    def test_bounding_box_width(self):
        """Test computed width property."""
        bbox = BoundingBox(min_x=10.0, max_x=110.0, min_y=0.0, max_y=50.0)
        assert bbox.width == 100.0

    def test_bounding_box_height(self):
        """Test computed height property."""
        bbox = BoundingBox(min_x=0.0, max_x=100.0, min_y=10.0, max_y=60.0)
        assert bbox.height == 50.0

    def test_bounding_box_center(self):
        """Test computed center property."""
        bbox = BoundingBox(min_x=0.0, max_x=100.0, min_y=0.0, max_y=50.0)
        assert bbox.center == (50.0, 25.0)

    def test_from_positions(self):
        """Test creating bounding box from node positions."""
        positions = {
            "N1": NodePosition(x=0.0, y=0.0),
            "N2": NodePosition(x=100.0, y=50.0),
            "N3": NodePosition(x=50.0, y=25.0),
        }

        bbox = BoundingBox.from_positions(positions)
        assert bbox.min_x == 0.0
        assert bbox.max_x == 100.0
        assert bbox.min_y == 0.0
        assert bbox.max_y == 50.0

    def test_from_positions_empty(self):
        """Test that empty positions raises error."""
        with pytest.raises(ValueError, match="Cannot compute bounding box from empty positions"):
            BoundingBox.from_positions({})


class TestLayoutMetadata:
    """Test LayoutMetadata model."""

    def test_create_layout_metadata(self):
        """Test creating layout metadata."""
        positions = {
            "N1": NodePosition(x=0.0, y=0.0),
            "N2": NodePosition(x=100.0, y=50.0),
        }

        layout = LayoutMetadata(
            algorithm="spring",
            positions=positions
        )

        assert layout.algorithm == "spring"
        assert len(layout.positions) == 2
        assert layout.positions["N1"].x == 0.0

    def test_bounding_box_auto_computed(self):
        """Test that bounding box is auto-computed if not provided."""
        positions = {
            "N1": NodePosition(x=0.0, y=0.0),
            "N2": NodePosition(x=100.0, y=50.0),
        }

        layout = LayoutMetadata(
            algorithm="spring",
            positions=positions
        )

        # Should auto-compute bounding box
        assert layout.bounding_box is not None
        assert layout.bounding_box.min_x == 0.0
        assert layout.bounding_box.max_x == 100.0

    def test_empty_positions_validation(self):
        """Test that empty positions raises error."""
        with pytest.raises(ValueError, match="at least one positioned node"):
            LayoutMetadata(algorithm="spring", positions={})

    def test_from_networkx_graph(self):
        """Test extracting layout from NetworkX graph."""
        graph = nx.DiGraph()
        graph.add_node("N1", pos=[0.0, 0.0])
        graph.add_node("N2", pos=[100.0, 50.0])

        layout = LayoutMetadata.from_networkx_graph(graph, algorithm="spring")

        assert layout.algorithm == "spring"
        assert len(layout.positions) == 2
        assert layout.positions["N1"].x == 0.0
        assert layout.positions["N2"].x == 100.0

    def test_from_networkx_graph_3d(self):
        """Test extracting 3D layout from NetworkX graph."""
        graph = nx.DiGraph()
        graph.add_node("N1", pos=[0.0, 0.0, 10.0])
        graph.add_node("N2", pos=[100.0, 50.0, 20.0])

        layout = LayoutMetadata.from_networkx_graph(graph, algorithm="spring_3d")

        assert layout.positions["N1"].z == 10.0
        assert layout.positions["N2"].z == 20.0

    def test_from_networkx_graph_missing_pos(self):
        """Test that missing 'pos' attribute raises error."""
        graph = nx.DiGraph()
        graph.add_node("N1", pos=[0.0, 0.0])
        graph.add_node("N2")  # Missing 'pos'

        with pytest.raises(ValueError, match="Node N2 is missing 'pos' attribute"):
            LayoutMetadata.from_networkx_graph(graph)

    def test_apply_to_networkx_graph(self):
        """Test applying layout positions to NetworkX graph."""
        graph = nx.DiGraph()
        graph.add_node("N1")
        graph.add_node("N2")

        positions = {
            "N1": NodePosition(x=0.0, y=0.0),
            "N2": NodePosition(x=100.0, y=50.0),
        }

        layout = LayoutMetadata(algorithm="spring", positions=positions)
        layout.apply_to_networkx_graph(graph)

        assert graph.nodes["N1"]["pos"] == [0.0, 0.0]
        assert graph.nodes["N2"]["pos"] == [100.0, 50.0]

    def test_apply_to_networkx_graph_missing_node(self):
        """Test applying layout when node not in graph (should log warning)."""
        graph = nx.DiGraph()
        graph.add_node("N1")
        # N2 not in graph

        positions = {
            "N1": NodePosition(x=0.0, y=0.0),
            "N2": NodePosition(x=100.0, y=50.0),  # Not in graph
        }

        layout = LayoutMetadata(algorithm="spring", positions=positions)
        layout.apply_to_networkx_graph(graph)  # Should not raise error

        # N1 should be updated, N2 should be skipped
        assert graph.nodes["N1"]["pos"] == [0.0, 0.0]
        assert "N2" not in graph.nodes

    def test_to_dict_deterministic(self):
        """Test that to_dict produces sorted keys."""
        positions = {
            "N2": NodePosition(x=100.0, y=50.0),
            "N1": NodePosition(x=0.0, y=0.0),
        }

        layout = LayoutMetadata(algorithm="spring", positions=positions)
        layout_dict = layout.to_dict()

        # Keys should be sorted
        keys = list(layout_dict.keys())
        assert keys == sorted(keys)

    def test_to_dict_positions_as_lists(self):
        """Test that to_dict converts positions to lists."""
        positions = {
            "N1": NodePosition(x=0.0, y=0.0),
        }

        layout = LayoutMetadata(algorithm="spring", positions=positions)
        layout_dict = layout.to_dict()

        # Positions should be lists, not objects
        assert isinstance(layout_dict["positions"]["N1"], list)
        assert layout_dict["positions"]["N1"] == [0.0, 0.0]

    def test_with_parameters(self):
        """Test layout metadata with algorithm parameters."""
        positions = {
            "N1": NodePosition(x=0.0, y=0.0),
        }

        layout = LayoutMetadata(
            algorithm="spring",
            positions=positions,
            parameters={"iterations": 50, "k": 0.5, "seed": 42}
        )

        assert layout.parameters["iterations"] == 50
        assert layout.parameters["k"] == 0.5
        assert layout.parameters["seed"] == 42


class TestLayoutCollection:
    """Test LayoutCollection model."""

    def test_create_layout_collection(self):
        """Test creating layout collection."""
        spring_layout = LayoutMetadata(
            algorithm="spring",
            positions={"N1": NodePosition(x=0.0, y=0.0)}
        )

        hierarchical_layout = LayoutMetadata(
            algorithm="hierarchical",
            positions={"N1": NodePosition(x=50.0, y=100.0)}
        )

        collection = LayoutCollection(
            default_layout="spring",
            layouts={
                "spring": spring_layout,
                "hierarchical": hierarchical_layout
            }
        )

        assert collection.default_layout == "spring"
        assert len(collection.layouts) == 2

    def test_empty_layouts_validation(self):
        """Test that empty layouts raises error."""
        with pytest.raises(ValueError, match="at least one layout"):
            LayoutCollection(default_layout="spring", layouts={})

    def test_invalid_default_layout(self):
        """Test that invalid default_layout raises error."""
        spring_layout = LayoutMetadata(
            algorithm="spring",
            positions={"N1": NodePosition(x=0.0, y=0.0)}
        )

        with pytest.raises(ValueError, match="default_layout 'hierarchical' not found"):
            LayoutCollection(
                default_layout="hierarchical",  # Doesn't exist
                layouts={"spring": spring_layout}
            )

    def test_get_default(self):
        """Test getting default layout."""
        spring_layout = LayoutMetadata(
            algorithm="spring",
            positions={"N1": NodePosition(x=0.0, y=0.0)}
        )

        collection = LayoutCollection(
            default_layout="spring",
            layouts={"spring": spring_layout}
        )

        default = collection.get_default()
        assert default.algorithm == "spring"

    def test_add_layout(self):
        """Test adding layout to collection."""
        spring_layout = LayoutMetadata(
            algorithm="spring",
            positions={"N1": NodePosition(x=0.0, y=0.0)}
        )

        collection = LayoutCollection(
            default_layout="spring",
            layouts={"spring": spring_layout}
        )

        # Add new layout
        hierarchical_layout = LayoutMetadata(
            algorithm="hierarchical",
            positions={"N1": NodePosition(x=50.0, y=100.0)}
        )

        collection.add_layout("hierarchical", hierarchical_layout)

        assert "hierarchical" in collection.layouts
        assert collection.default_layout == "spring"  # Should not change

    def test_add_layout_set_as_default(self):
        """Test adding layout and setting as default."""
        spring_layout = LayoutMetadata(
            algorithm="spring",
            positions={"N1": NodePosition(x=0.0, y=0.0)}
        )

        collection = LayoutCollection(
            default_layout="spring",
            layouts={"spring": spring_layout}
        )

        # Add new layout and set as default
        manual_layout = LayoutMetadata(
            algorithm="manual",
            positions={"N1": NodePosition(x=75.0, y=125.0)}
        )

        collection.add_layout("manual", manual_layout, set_as_default=True)

        assert collection.default_layout == "manual"
        assert collection.get_default().algorithm == "manual"


class TestLayoutIntegration:
    """Test integration with NetworkX graphs."""

    def test_round_trip_with_networkx(self):
        """Test extracting and re-applying layout."""
        # Create graph with positions
        original_graph = nx.DiGraph()
        original_graph.add_node("N1", pos=[0.0, 0.0])
        original_graph.add_node("N2", pos=[100.0, 50.0])
        original_graph.add_node("N3", pos=[50.0, 75.0])

        # Extract layout
        layout = LayoutMetadata.from_networkx_graph(original_graph, algorithm="spring")

        # Create new graph without positions
        new_graph = nx.DiGraph()
        new_graph.add_node("N1")
        new_graph.add_node("N2")
        new_graph.add_node("N3")

        # Apply layout
        layout.apply_to_networkx_graph(new_graph)

        # Verify positions match
        assert new_graph.nodes["N1"]["pos"] == [0.0, 0.0]
        assert new_graph.nodes["N2"]["pos"] == [100.0, 50.0]
        assert new_graph.nodes["N3"]["pos"] == [50.0, 75.0]
