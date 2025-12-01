"""Tests for the layout system (Codex Consensus #019adb91).

Tests cover:
- Layout schema (LayoutMetadata, EdgeRoute, PortLayout)
- ELK layout engine integration
- Layout store (CRUD, optimistic concurrency)
- Layout tools (MCP interface)
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Any

import networkx as nx
import pytest

from src.models.layout_metadata import (
    LayoutMetadata,
    NodePosition,
    EdgeRoute,
    EdgeSection,
    PortLayout,
    LabelPosition,
    ModelReference,
    BoundingBox,
)
from src.core.layout_store import (
    LayoutStore,
    LayoutNotFoundError,
    OptimisticLockError,
    create_layout_store,
)
from src.layout.engines.elk import ELKLayoutEngine, PID_LAYOUT_OPTIONS
from src.layout.engines.base import LayoutEngine


# =============================================================================
# Schema Tests
# =============================================================================


class TestLayoutMetadataSchema:
    """Test LayoutMetadata schema validation and serialization."""

    def test_minimal_layout(self):
        """Test creating minimal layout with just positions."""
        layout = LayoutMetadata(
            algorithm="spring",
            positions={"n1": NodePosition(x=0, y=0)},
        )
        assert layout.algorithm == "spring"
        assert len(layout.positions) == 1
        assert layout.etag is not None  # Auto-computed

    def test_layout_with_edges(self):
        """Test layout with edge routing data."""
        layout = LayoutMetadata(
            algorithm="elk",
            positions={
                "n1": NodePosition(x=0, y=0),
                "n2": NodePosition(x=100, y=0),
            },
            edges={
                "e1": EdgeRoute(
                    sections=[
                        EdgeSection(
                            startPoint=(30, 20),
                            endPoint=(70, 20),
                            bendPoints=[(50, 20)],
                        )
                    ],
                    source_port="n1_out",
                    target_port="n2_in",
                )
            },
        )
        assert len(layout.edges) == 1
        assert layout.edges["e1"].source_port == "n1_out"
        assert len(layout.edges["e1"].sections[0].bendPoints) == 1

    def test_layout_with_ports(self):
        """Test layout with port position data."""
        layout = LayoutMetadata(
            algorithm="elk",
            positions={"n1": NodePosition(x=0, y=0)},
            port_layouts={
                "n1_in": PortLayout(id="n1_in", x=0, y=20, side="WEST"),
                "n1_out": PortLayout(id="n1_out", x=60, y=20, side="EAST"),
            },
        )
        assert len(layout.port_layouts) == 2
        assert layout.port_layouts["n1_in"].side == "WEST"

    def test_etag_computation(self):
        """Test etag is computed from content (excludes timestamps)."""
        layout1 = LayoutMetadata(
            algorithm="elk",
            positions={"n1": NodePosition(x=10, y=20)},
        )
        layout2 = LayoutMetadata(
            algorithm="elk",
            positions={"n1": NodePosition(x=10, y=20)},
        )
        # Same content should produce same etag
        assert layout1.etag == layout2.etag

    def test_etag_changes_with_content(self):
        """Test etag changes when content changes."""
        layout1 = LayoutMetadata(
            algorithm="elk",
            positions={"n1": NodePosition(x=10, y=20)},
        )
        layout2 = LayoutMetadata(
            algorithm="elk",
            positions={"n1": NodePosition(x=10, y=30)},  # Different y
        )
        assert layout1.etag != layout2.etag

    def test_bounding_box_auto_computed(self):
        """Test bounding box is auto-computed from positions."""
        layout = LayoutMetadata(
            algorithm="elk",
            positions={
                "n1": NodePosition(x=10, y=20),
                "n2": NodePosition(x=100, y=80),
            },
        )
        assert layout.bounding_box is not None
        assert layout.bounding_box.min_x == 10
        assert layout.bounding_box.max_x == 100
        assert layout.bounding_box.min_y == 20
        assert layout.bounding_box.max_y == 80

    def test_model_reference(self):
        """Test layout with model reference."""
        ref = ModelReference(type="dexpi", model_id="P-101")
        layout = LayoutMetadata(
            algorithm="elk",
            positions={"n1": NodePosition(x=0, y=0)},
            model_ref=ref,
        )
        assert layout.model_ref.type == "dexpi"
        assert layout.model_ref.model_id == "P-101"

    def test_to_dict_deterministic(self):
        """Test to_dict produces deterministic output."""
        layout = LayoutMetadata(
            algorithm="elk",
            positions={
                "n2": NodePosition(x=100, y=0),
                "n1": NodePosition(x=0, y=0),
            },
        )
        dict1 = layout.to_dict()
        dict2 = layout.to_dict()
        # Should be identical (sorted keys)
        assert json.dumps(dict1, sort_keys=True) == json.dumps(dict2, sort_keys=True)


class TestEdgeRoute:
    """Test EdgeRoute and EdgeSection classes."""

    def test_edge_route_get_all_points(self):
        """Test getting all points from edge route."""
        route = EdgeRoute(
            sections=[
                EdgeSection(
                    startPoint=(0, 0),
                    endPoint=(50, 0),
                    bendPoints=[],
                ),
                EdgeSection(
                    startPoint=(50, 0),
                    endPoint=(50, 50),
                    bendPoints=[],
                ),
            ]
        )
        points = route.get_all_points()
        # Should be: (0,0) -> (50,0) -> (50,50) without duplicate at boundary
        assert points == [(0, 0), (50, 0), (50, 50)]

    def test_edge_section_get_all_points(self):
        """Test getting all points from single section."""
        section = EdgeSection(
            startPoint=(0, 0),
            endPoint=(100, 0),
            bendPoints=[(30, 10), (70, 10)],
        )
        points = section.get_all_points()
        assert points == [(0, 0), (30, 10), (70, 10), (100, 0)]


# =============================================================================
# Layout Store Tests
# =============================================================================


class TestLayoutStore:
    """Test LayoutStore CRUD operations and concurrency."""

    def test_create_and_get(self):
        """Test creating and retrieving layout."""
        store = create_layout_store()
        layout = LayoutMetadata(
            algorithm="elk",
            positions={"n1": NodePosition(x=10, y=20)},
        )

        layout_id = store.save(layout)
        assert layout_id is not None

        retrieved = store.get(layout_id)
        assert retrieved.algorithm == "elk"
        assert len(retrieved.positions) == 1

    def test_update_with_etag(self):
        """Test update with optimistic concurrency."""
        store = create_layout_store()
        layout = LayoutMetadata(
            algorithm="elk",
            positions={"n1": NodePosition(x=10, y=20)},
        )

        layout_id = store.save(layout)
        original = store.get(layout_id)

        # Update with correct etag
        modified = LayoutMetadata(
            algorithm="elk",
            positions={"n1": NodePosition(x=20, y=30)},
        )
        new_etag = store.update(layout_id, modified, expected_etag=original.etag)
        assert new_etag != original.etag

    def test_update_with_wrong_etag(self):
        """Test update fails with wrong etag."""
        store = create_layout_store()
        layout = LayoutMetadata(
            algorithm="elk",
            positions={"n1": NodePosition(x=10, y=20)},
        )

        layout_id = store.save(layout)

        modified = LayoutMetadata(
            algorithm="elk",
            positions={"n1": NodePosition(x=20, y=30)},
        )

        with pytest.raises(OptimisticLockError):
            store.update(layout_id, modified, expected_etag="wrong-etag")

    def test_delete(self):
        """Test deleting layout."""
        store = create_layout_store()
        layout = LayoutMetadata(
            algorithm="elk",
            positions={"n1": NodePosition(x=10, y=20)},
        )

        layout_id = store.save(layout)
        assert store.exists(layout_id)

        assert store.delete(layout_id)
        assert not store.exists(layout_id)

    def test_list_by_model(self):
        """Test listing layouts by model."""
        store = create_layout_store()

        # Create layouts for different models
        layout1 = LayoutMetadata(
            algorithm="elk",
            positions={"n1": NodePosition(x=0, y=0)},
        )
        layout2 = LayoutMetadata(
            algorithm="elk",
            positions={"n1": NodePosition(x=10, y=10)},
        )

        ref1 = ModelReference(type="dexpi", model_id="model-A")
        ref2 = ModelReference(type="dexpi", model_id="model-B")

        store.save(layout1, model_ref=ref1)
        store.save(layout2, model_ref=ref2)

        # List by model
        layouts_a = store.list_by_model("dexpi", "model-A")
        layouts_b = store.list_by_model("dexpi", "model-B")

        assert len(layouts_a) == 1
        assert len(layouts_b) == 1

    def test_version_increment(self):
        """Test version increments on update."""
        store = create_layout_store()
        layout = LayoutMetadata(
            algorithm="elk",
            positions={"n1": NodePosition(x=10, y=20)},
        )

        layout_id = store.save(layout)
        original = store.get(layout_id)
        assert original.version == 1

        modified = LayoutMetadata(
            algorithm="elk",
            positions={"n1": NodePosition(x=20, y=30)},
        )
        store.update(layout_id, modified)

        updated = store.get(layout_id)
        assert updated.version == 2


class TestLayoutStoreFilePersistence:
    """Test layout store file persistence."""

    def test_save_and_load_file(self):
        """Test saving layout to file and loading back."""
        store = create_layout_store()
        layout = LayoutMetadata(
            algorithm="elk",
            positions={
                "n1": NodePosition(x=10, y=20),
                "n2": NodePosition(x=100, y=20),
            },
            edges={
                "e1": EdgeRoute(
                    sections=[
                        EdgeSection(
                            startPoint=(30, 20),
                            endPoint=(80, 20),
                        )
                    ]
                )
            },
        )

        layout_id = store.save(layout)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Save to file
            file_path = store.save_to_file(layout_id, tmpdir, "test_model", "pid")
            assert file_path.exists()

            # Create new store and load
            new_store = create_layout_store()
            loaded_id = new_store.load_from_file(tmpdir, "test_model", "pid")

            loaded = new_store.get(loaded_id)
            assert loaded.algorithm == "elk"
            assert len(loaded.positions) == 2
            assert len(loaded.edges) == 1

    def test_file_format_is_json(self):
        """Test saved file is valid JSON."""
        store = create_layout_store()
        layout = LayoutMetadata(
            algorithm="elk",
            positions={"n1": NodePosition(x=10, y=20)},
        )

        layout_id = store.save(layout)

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = store.save_to_file(layout_id, tmpdir, "test", "pid")

            with open(file_path) as f:
                data = json.load(f)

            assert data["algorithm"] == "elk"
            assert "positions" in data


# =============================================================================
# ELK Layout Engine Tests
# =============================================================================


class TestELKLayoutEngine:
    """Test ELK layout engine integration."""

    @pytest.fixture
    def elk_engine(self):
        """Create ELK engine instance."""
        return ELKLayoutEngine()

    def test_engine_properties(self, elk_engine):
        """Test engine property accessors."""
        assert elk_engine.name == "elk"
        assert elk_engine.supports_orthogonal_routing is True
        assert elk_engine.supports_ports is True

    @pytest.mark.asyncio
    async def test_elk_availability(self, elk_engine):
        """Test checking ELK availability."""
        # This depends on Node.js being installed
        available = await elk_engine.is_available()
        # Just check it returns a boolean
        assert isinstance(available, bool)

    @pytest.mark.asyncio
    async def test_simple_layout(self, elk_engine):
        """Test computing layout for simple graph."""
        if not await elk_engine.is_available():
            pytest.skip("ELK not available (Node.js required)")

        graph = nx.DiGraph()
        graph.add_node("n1", width=60, height=40, label="Node 1")
        graph.add_node("n2", width=60, height=40, label="Node 2")
        graph.add_edge("n1", "n2", id="e1")

        layout = await elk_engine.layout(graph)

        assert layout.algorithm == "elk"
        assert len(layout.positions) == 2
        assert "n1" in layout.positions
        assert "n2" in layout.positions
        # Nodes should be separated
        assert layout.positions["n1"].x != layout.positions["n2"].x or \
               layout.positions["n1"].y != layout.positions["n2"].y

    @pytest.mark.asyncio
    async def test_layout_with_custom_options(self, elk_engine):
        """Test layout with custom ELK options."""
        if not await elk_engine.is_available():
            pytest.skip("ELK not available")

        graph = nx.DiGraph()
        graph.add_node("n1", width=60, height=40)
        graph.add_node("n2", width=60, height=40)
        graph.add_edge("n1", "n2")

        # Use DOWN direction instead of RIGHT
        options = {"elk.direction": "DOWN"}
        layout = await elk_engine.layout(graph, options)

        # With DOWN direction, n2 should be below n1
        assert layout.positions["n2"].y > layout.positions["n1"].y

    @pytest.mark.asyncio
    async def test_layout_has_edge_sections(self, elk_engine):
        """Test layout includes edge routing sections."""
        if not await elk_engine.is_available():
            pytest.skip("ELK not available")

        graph = nx.DiGraph()
        graph.add_node("n1", width=60, height=40)
        graph.add_node("n2", width=60, height=40)
        graph.add_edge("n1", "n2", id="e1")

        layout = await elk_engine.layout(graph)

        # Should have edge routing data
        assert len(layout.edges) == 1
        assert "e1" in layout.edges
        assert len(layout.edges["e1"].sections) > 0


class TestPIDLayoutOptions:
    """Test P&ID-specific ELK options."""

    def test_default_options_present(self):
        """Test PID_LAYOUT_OPTIONS has expected settings."""
        assert PID_LAYOUT_OPTIONS["elk.algorithm"] == "layered"
        assert PID_LAYOUT_OPTIONS["elk.edgeRouting"] == "ORTHOGONAL"
        assert PID_LAYOUT_OPTIONS["elk.portConstraints"] == "FIXED_ORDER"

    def test_spacing_values(self):
        """Test spacing values are reasonable for P&ID (mm)."""
        spacing = PID_LAYOUT_OPTIONS["elk.layered.spacing.nodeNodeBetweenLayers"]
        assert 30 <= spacing <= 100  # Reasonable range for mm


# =============================================================================
# Integration Tests
# =============================================================================


class TestLayoutIntegration:
    """Integration tests for complete layout workflow."""

    @pytest.mark.asyncio
    async def test_compute_store_retrieve(self):
        """Test computing layout, storing, and retrieving."""
        engine = ELKLayoutEngine()
        if not await engine.is_available():
            pytest.skip("ELK not available")

        store = create_layout_store()

        # Create graph
        graph = nx.DiGraph()
        graph.add_node("pump", width=60, height=40, label="P-101")
        graph.add_node("tank", width=80, height=60, label="T-101")
        graph.add_edge("pump", "tank", id="line-1")

        # Compute layout
        layout = await engine.layout(graph)

        # Store with model reference
        ref = ModelReference(type="dexpi", model_id="test-pid")
        layout_id = store.save(layout, model_ref=ref)

        # Retrieve and verify
        retrieved = store.get(layout_id)
        assert retrieved.model_ref.model_id == "test-pid"
        assert len(retrieved.positions) == 2
        assert len(retrieved.edges) == 1

    @pytest.mark.asyncio
    async def test_full_file_roundtrip(self):
        """Test complete roundtrip: compute -> store -> file -> load."""
        engine = ELKLayoutEngine()
        if not await engine.is_available():
            pytest.skip("ELK not available")

        # Create graph
        graph = nx.DiGraph()
        graph.add_node("R-101", width=80, height=60)
        graph.add_node("E-101", width=60, height=40)
        graph.add_node("P-101", width=40, height=30)
        graph.add_edge("R-101", "E-101", id="line-1")
        graph.add_edge("E-101", "P-101", id="line-2")

        # Compute layout
        layout = await engine.layout(graph)

        store = create_layout_store()
        ref = ModelReference(type="dexpi", model_id="reactor-system")
        layout_id = store.save(layout, model_ref=ref)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Save to file
            store.save_to_file(layout_id, tmpdir, "reactor_system", "pid")

            # Load into new store
            new_store = create_layout_store()
            loaded_id = new_store.load_from_file(tmpdir, "reactor_system")

            loaded = new_store.get(loaded_id)

            # Verify content preserved
            assert loaded.algorithm == "elk"
            assert len(loaded.positions) == 3
            assert len(loaded.edges) == 2
            # Verify edge routing preserved
            assert len(loaded.edges["line-1"].sections) > 0


# =============================================================================
# Test Layout Update Tool (Codex Consensus #019adb91)
# =============================================================================


class TestLayoutUpdate:
    """Tests for layout_update tool with optimistic concurrency."""

    @pytest.fixture
    def store(self):
        """Create layout store with test layout."""
        store = create_layout_store()

        layout = LayoutMetadata(
            algorithm="elk",
            positions={
                "P-101": NodePosition(x=100, y=100),
                "R-101": NodePosition(x=200, y=100),
            },
            edges={},
        )
        layout_id = store.save(layout, layout_id="test-layout")
        return store

    def test_update_positions_with_valid_etag(self, store):
        """Update positions succeeds with correct etag."""
        layout = store.get("test-layout")
        original_etag = layout.etag

        # Update position
        layout.positions["P-101"] = NodePosition(x=150, y=150)

        # Update with valid etag
        new_etag = store.update("test-layout", layout, expected_etag=original_etag)

        # Verify update
        updated = store.get("test-layout")
        assert updated.positions["P-101"].x == 150
        assert updated.positions["P-101"].y == 150
        assert updated.etag == new_etag
        assert updated.version == 2

    def test_update_fails_with_wrong_etag(self, store):
        """Update fails when etag doesn't match (concurrent modification)."""
        layout = store.get("test-layout")

        # Update position
        layout.positions["P-101"] = NodePosition(x=150, y=150)

        # Try update with wrong etag
        with pytest.raises(OptimisticLockError) as exc_info:
            store.update("test-layout", layout, expected_etag="wrong-etag")

        assert exc_info.value.layout_id == "test-layout"
        assert exc_info.value.expected_etag == "wrong-etag"

    def test_version_increments_on_update(self, store):
        """Version increments with each update."""
        layout = store.get("test-layout")
        assert layout.version == 1

        # First update
        layout.positions["P-101"] = NodePosition(x=150, y=150)
        store.update("test-layout", layout, expected_etag=layout.etag)

        layout = store.get("test-layout")
        assert layout.version == 2

        # Second update
        layout.positions["P-101"] = NodePosition(x=200, y=200)
        store.update("test-layout", layout, expected_etag=layout.etag)

        layout = store.get("test-layout")
        assert layout.version == 3


# =============================================================================
# Test Layout Validate Tool (Codex Consensus #019adb91)
# =============================================================================


class TestLayoutValidate:
    """Tests for layout_validate tool."""

    def test_validate_basic_layout(self):
        """Basic validation passes for valid layout."""
        store = create_layout_store()

        layout = LayoutMetadata(
            algorithm="elk",
            positions={
                "P-101": NodePosition(x=100, y=100),
            },
        )
        store.save(layout, layout_id="test-layout")

        # Get layout and validate fields
        retrieved = store.get("test-layout")
        assert retrieved.algorithm == "elk"
        assert len(retrieved.positions) == 1
        assert retrieved.etag is not None

    def test_etag_recomputation(self):
        """Etag can be recomputed to verify integrity."""
        store = create_layout_store()

        layout = LayoutMetadata(
            algorithm="elk",
            positions={
                "P-101": NodePosition(x=100, y=100),
            },
        )
        store.save(layout, layout_id="test-layout")

        # Verify etag matches recomputation
        retrieved = store.get("test-layout")
        computed_etag = retrieved.compute_etag()
        assert retrieved.etag == computed_etag

    def test_bounding_box_consistency(self):
        """Bounding box auto-computed from positions."""
        layout = LayoutMetadata(
            algorithm="elk",
            positions={
                "P-101": NodePosition(x=100, y=100),
                "R-101": NodePosition(x=300, y=200),
            },
        )

        assert layout.bounding_box is not None
        assert layout.bounding_box.min_x == 100
        assert layout.bounding_box.max_x == 300
        assert layout.bounding_box.min_y == 100
        assert layout.bounding_box.max_y == 200


# =============================================================================
# Test Layout Tools MCP Interface
# =============================================================================


class TestLayoutToolsMCP:
    """Tests for layout tools MCP interface."""

    @pytest.fixture
    def layout_tools(self):
        """Create layout tools instance."""
        from src.tools.layout_tools import LayoutTools

        return LayoutTools(
            dexpi_models={},
            flowsheets={},
        )

    @pytest.mark.asyncio
    async def test_layout_update_tool_exists(self, layout_tools):
        """layout_update tool is registered."""
        tools = layout_tools.get_tools()
        tool_names = [t.name for t in tools]
        assert "layout_update" in tool_names

    @pytest.mark.asyncio
    async def test_layout_validate_tool_exists(self, layout_tools):
        """layout_validate tool is registered."""
        tools = layout_tools.get_tools()
        tool_names = [t.name for t in tools]
        assert "layout_validate" in tool_names

    @pytest.mark.asyncio
    async def test_layout_update_requires_etag(self, layout_tools):
        """layout_update tool requires etag parameter."""
        tools = layout_tools.get_tools()
        update_tool = next(t for t in tools if t.name == "layout_update")

        schema = update_tool.inputSchema
        assert "etag" in schema["required"]
        assert "layout_id" in schema["required"]

    @pytest.mark.asyncio
    async def test_layout_update_handler(self, layout_tools):
        """Test layout_update handler with valid etag."""
        # Create initial layout
        layout = LayoutMetadata(
            algorithm="elk",
            positions={
                "P-101": NodePosition(x=100, y=100),
            },
        )
        layout_id = layout_tools.layout_store.save(layout, layout_id="test-layout")

        # Get etag
        stored = layout_tools.layout_store.get(layout_id)
        etag = stored.etag

        # Update via tool
        result = await layout_tools.handle_tool("layout_update", {
            "layout_id": layout_id,
            "etag": etag,
            "positions": {
                "P-101": {"x": 150, "y": 150}
            }
        })

        assert result["ok"] is True
        assert result["data"]["updated"] is True
        assert result["data"]["version"] == 2

    @pytest.mark.asyncio
    async def test_layout_update_fails_with_wrong_etag(self, layout_tools):
        """Test layout_update fails with wrong etag."""
        # Create initial layout
        layout = LayoutMetadata(
            algorithm="elk",
            positions={
                "P-101": NodePosition(x=100, y=100),
            },
        )
        layout_tools.layout_store.save(layout, layout_id="test-layout")

        # Update via tool with wrong etag
        result = await layout_tools.handle_tool("layout_update", {
            "layout_id": "test-layout",
            "etag": "wrong-etag",
            "positions": {
                "P-101": {"x": 150, "y": 150}
            }
        })

        assert result["ok"] is False
        assert result["error"]["code"] == "ETAG_MISMATCH"

    @pytest.mark.asyncio
    async def test_layout_validate_handler(self, layout_tools):
        """Test layout_validate handler."""
        # Create layout
        layout = LayoutMetadata(
            algorithm="elk",
            positions={
                "P-101": NodePosition(x=100, y=100),
            },
        )
        layout_tools.layout_store.save(layout, layout_id="test-layout")

        # Validate via tool
        result = await layout_tools.handle_tool("layout_validate", {
            "layout_id": "test-layout"
        })

        assert result["ok"] is True
        assert result["data"]["valid"] is True
        assert result["data"]["node_count"] == 1


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
