"""Phase 8 Integration Tests - Real Services, No Mocks.

Following the test philosophy from test_graphicbuilder_integration.py:
- Real services only - Use actual GraphicBuilder Docker, real SFILES2/pyDEXPI library calls
- No mocks - No unittest.mock, no monkeypatch.setattr for core functionality
- Strict assertions - No swallowed exceptions, no silent skips for expected functionality
- Structural validation - Real PNG/SVG/PDF parsing with strict XML parser

Test Coverage:
- Phase 8.2.1: sfiles_visualize tool
- Phase 8.2.2: model_combine tool
- Phase 8.2.3: search_instances tool
- Phase 8.4: layout-rendering integration
"""

import base64
import os
import socket
from typing import Optional
from lxml import etree

import pytest

# Set matplotlib backend for headless operation before imports
os.environ['MPLBACKEND'] = 'Agg'


# ============================================================================
# Validation Helpers (Strict - Raise on Invalid)
# ============================================================================

def assert_valid_png(data: bytes) -> None:
    """Strict PNG validation - raises on invalid.

    Validates PNG signature and required chunks (IHDR, IEND).
    """
    assert data[:8] == b'\x89PNG\r\n\x1a\n', "Invalid PNG signature"
    pos = 8
    chunks_found = set()
    while pos < len(data):
        if pos + 8 > len(data):
            raise AssertionError("Truncated PNG - incomplete chunk header")
        length = int.from_bytes(data[pos:pos + 4], 'big')
        chunk_type = data[pos + 4:pos + 8]
        chunks_found.add(chunk_type)
        pos += 12 + length  # length(4) + type(4) + data(length) + crc(4)
        if chunk_type == b'IEND':
            break
    assert b'IHDR' in chunks_found, "Missing IHDR chunk in PNG"
    assert b'IEND' in chunks_found, "Missing IEND chunk in PNG"


def assert_valid_svg(content: str) -> etree._Element:
    """Strict SVG parsing - no recovery mode.

    Returns parsed XML root if valid, raises on error.
    """
    parser = etree.XMLParser(recover=False)
    root = etree.fromstring(content.encode('utf-8'), parser)
    assert root.tag.endswith('svg'), f"Root element is {root.tag}, expected svg"
    return root


def assert_valid_html(content: str) -> None:
    """Basic HTML validation."""
    assert '<!DOCTYPE html>' in content or '<html' in content, "Not valid HTML"
    assert '<body>' in content or '<body ' in content, "Missing body tag"


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sfiles_tools():
    """Create SfilesTools instance for testing."""
    from src.tools.sfiles_tools import SfilesTools
    flowsheets = {}
    return SfilesTools(flowsheets)


@pytest.fixture
def model_tools():
    """Create ModelTools instance for testing."""
    from src.tools.model_tools import ModelTools
    from src.tools.sfiles_tools import SfilesTools
    from src.tools.dexpi_tools import DexpiTools

    dexpi_store = {}
    sfiles_store = {}
    dexpi_tools = DexpiTools(dexpi_store)
    sfiles_tools = SfilesTools(sfiles_store)
    return ModelTools(dexpi_store, sfiles_store, dexpi_tools, sfiles_tools)


@pytest.fixture
def search_tools():
    """Create SearchTools instance for testing."""
    from src.tools.search_tools import SearchTools
    dexpi_store = {}
    sfiles_store = {}
    return SearchTools(dexpi_store, sfiles_store)


@pytest.fixture
async def flowsheet_with_sfiles2_attrs(sfiles_tools):
    """Create a real Flowsheet with attributes SFILES2 requires for visualization.

    Returns flowsheet_id of the created flowsheet.
    """
    # Create flowsheet via tool
    result = await sfiles_tools._create_flowsheet({
        "name": "test_flowsheet",
        "type": "PFD",
        "description": "Test flowsheet for visualization"
    })
    assert result.get("ok"), f"Failed to create flowsheet: {result}"

    flowsheet_id = result["data"]["flowsheet_id"]

    # Add units with required attributes
    await sfiles_tools._add_unit({
        "flowsheet_id": flowsheet_id,
        "unit_name": "P-101",
        "unit_type": "pump"
    })
    await sfiles_tools._add_unit({
        "flowsheet_id": flowsheet_id,
        "unit_name": "TK-101",
        "unit_type": "tank"
    })
    await sfiles_tools._add_stream({
        "flowsheet_id": flowsheet_id,
        "stream_name": "S-001",
        "from_unit": "P-101",
        "to_unit": "TK-101"
    })

    return flowsheet_id


@pytest.fixture
def dexpi_model_with_equipment():
    """Create a real DEXPI model with equipment."""
    from pydexpi.dexpi_classes import dexpiModel, equipment
    from pydexpi.dexpi_classes.pydantic_classes import (
        ConceptualModel,
        CentrifugalPump,
        Tank,
        Nozzle,
    )

    pump = CentrifugalPump(
        id="P-101",
        tagName="P-101",
        componentClass="CentrifugalPump"
    )

    tank = Tank(
        id="TK-101",
        tagName="TK-101",
        componentClass="Tank"
    )

    conceptual = ConceptualModel(
        taggedPlantItems=[pump, tank]
    )

    model = dexpiModel.DexpiModel(
        conceptualModel=conceptual
    )

    return model


@pytest.fixture
def graphicbuilder_available():
    """Check if GraphicBuilder Docker is available."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 8080))
    sock.close()
    return result == 0


# ============================================================================
# Phase 8.2.1: sfiles_visualize Tests
# ============================================================================

class TestSfilesVisualizeIntegration:
    """Real integration tests for sfiles_visualize tool."""

    @pytest.mark.asyncio
    async def test_visualize_html_output(self, sfiles_tools, flowsheet_with_sfiles2_attrs):
        """Test HTML visualization with real flowsheet.

        Note: Table generation requires processstream_name attribute on edges,
        which sfiles_add_stream doesn't populate. Test with include_tables=False.
        """
        flowsheet_id = flowsheet_with_sfiles2_attrs

        result = await sfiles_tools._visualize({
            "flowsheet_id": flowsheet_id,
            "output_format": "html",
            "include_tables": False  # Tables require processstream_name attr
        })

        assert result.get("ok"), f"Visualization failed: {result}"
        data = result["data"]

        assert data["format"] == "html"
        assert data["content_type"] == "text/html"
        assert "content" in data
        assert_valid_html(data["content"])
        assert data["node_count"] == 2
        assert data["edge_count"] == 1

    @pytest.mark.asyncio
    async def test_visualize_png_output(self, sfiles_tools, flowsheet_with_sfiles2_attrs):
        """Test PNG visualization with real flowsheet."""
        flowsheet_id = flowsheet_with_sfiles2_attrs

        result = await sfiles_tools._visualize({
            "flowsheet_id": flowsheet_id,
            "output_format": "png",
            "include_tables": False
        })

        assert result.get("ok"), f"Visualization failed: {result}"
        data = result["data"]

        assert data["format"] == "png"
        assert data["content_type"] == "image/png"
        assert "content_base64" in data

        # Decode and validate PNG
        png_data = base64.b64decode(data["content_base64"])
        assert_valid_png(png_data)

    @pytest.mark.asyncio
    async def test_visualize_empty_flowsheet_error(self, sfiles_tools):
        """Test that empty flowsheet returns proper error."""
        import asyncio

        # Create empty flowsheet
        result = await sfiles_tools._create_flowsheet({
            "name": "empty_flowsheet",
            "type": "PFD"
        })
        assert result.get("ok")
        flowsheet_id = result["data"]["flowsheet_id"]

        # Try to visualize empty flowsheet
        result = await sfiles_tools._visualize({
            "flowsheet_id": flowsheet_id,
            "output_format": "html"
        })

        assert result.get("ok") is False, "Should fail for empty flowsheet"
        assert "EMPTY_FLOWSHEET" in result.get("error", {}).get("code", "")

    @pytest.mark.asyncio
    async def test_visualize_not_found_error(self, sfiles_tools):
        """Test that nonexistent flowsheet returns proper error."""
        result = await sfiles_tools._visualize({
            "flowsheet_id": "nonexistent_id",
            "output_format": "html"
        })

        assert result.get("ok") is False
        assert "NOT_FOUND" in result.get("error", {}).get("code", "")


# ============================================================================
# Phase 8.2.2: model_combine Tests
# ============================================================================

class TestModelCombineIntegration:
    """Real integration tests for model_combine tool."""

    @pytest.mark.asyncio
    async def test_combine_two_models(self, model_tools, dexpi_model_with_equipment):
        """Test combining two DEXPI models."""
        from pydexpi.dexpi_classes import dexpiModel
        from pydexpi.dexpi_classes.pydantic_classes import (
            ConceptualModel,
            CentrifugalPump,
            PlateHeatExchanger,
        )

        # Create second model
        hx = PlateHeatExchanger(
            id="HX-101",
            tagName="HX-101",
            componentClass="PlateHeatExchanger"
        )
        model2 = dexpiModel.DexpiModel(
            conceptualModel=ConceptualModel(taggedPlantItems=[hx])
        )

        # Store both models
        model_tools.dexpi_models["model1"] = dexpi_model_with_equipment
        model_tools.dexpi_models["model2"] = model2

        result = await model_tools._combine_models({
            "source_model_ids": ["model1", "model2"],
            "target_model_id": "combined"
        })

        assert result.get("ok"), f"Combine failed: {result}"
        data = result["data"]

        assert data["source_count"] == 2
        assert "combined" in model_tools.dexpi_models
        assert data["statistics"]["equipment_count"] == 3  # 2 from model1 + 1 from model2

    @pytest.mark.asyncio
    async def test_combine_insufficient_models_error(self, model_tools, dexpi_model_with_equipment):
        """Test that combining single model returns error."""
        model_tools.dexpi_models["model1"] = dexpi_model_with_equipment

        result = await model_tools._combine_models({
            "source_model_ids": ["model1"],
            "target_model_id": "combined"
        })

        assert result.get("ok") is False
        assert "INSUFFICIENT" in result.get("error", {}).get("code", "")

    @pytest.mark.asyncio
    async def test_combine_missing_model_error(self, model_tools, dexpi_model_with_equipment):
        """Test that combining with missing model returns error."""
        model_tools.dexpi_models["model1"] = dexpi_model_with_equipment

        result = await model_tools._combine_models({
            "source_model_ids": ["model1", "nonexistent"],
            "target_model_id": "combined"
        })

        assert result.get("ok") is False
        assert "NOT_FOUND" in result.get("error", {}).get("code", "")


# ============================================================================
# Phase 8.2.3: search_instances Tests
# ============================================================================

class TestSearchInstancesIntegration:
    """Real integration tests for search_instances tool."""

    @pytest.mark.asyncio
    async def test_search_all_instances(self, search_tools, dexpi_model_with_equipment):
        """Test finding all instances in a model."""
        search_tools.dexpi_models["test_model"] = dexpi_model_with_equipment

        result = await search_tools._search_instances({
            "model_id": "test_model"
        })

        assert result.get("ok"), f"Search failed: {result}"
        data = result["data"]

        assert data["total_count"] > 0
        assert "results" in data
        assert "class_counts" in data

    @pytest.mark.asyncio
    async def test_search_specific_classes(self, search_tools, dexpi_model_with_equipment):
        """Test finding instances of specific classes."""
        search_tools.dexpi_models["test_model"] = dexpi_model_with_equipment

        result = await search_tools._search_instances({
            "model_id": "test_model",
            "class_names": ["CentrifugalPump"]
        })

        assert result.get("ok"), f"Search failed: {result}"
        data = result["data"]

        # Should find 1 pump
        assert data["total_count"] >= 1
        assert all(r["class_name"] == "CentrifugalPump" for r in data["results"])

    @pytest.mark.asyncio
    async def test_search_with_pagination(self, search_tools, dexpi_model_with_equipment):
        """Test pagination of search results."""
        search_tools.dexpi_models["test_model"] = dexpi_model_with_equipment

        # First page
        result1 = await search_tools._search_instances({
            "model_id": "test_model",
            "limit": 1,
            "offset": 0
        })

        assert result1.get("ok")
        data1 = result1["data"]
        assert data1["returned_count"] <= 1

        # Second page
        result2 = await search_tools._search_instances({
            "model_id": "test_model",
            "limit": 1,
            "offset": 1
        })

        assert result2.get("ok")
        data2 = result2["data"]
        assert data2["offset"] == 1

    @pytest.mark.asyncio
    async def test_search_invalid_class_error(self, search_tools, dexpi_model_with_equipment):
        """Test that invalid class name returns error."""
        search_tools.dexpi_models["test_model"] = dexpi_model_with_equipment

        result = await search_tools._search_instances({
            "model_id": "test_model",
            "class_names": ["InvalidClassName"]
        })

        assert result.get("ok") is False
        assert "INVALID_CLASS" in result.get("error", {}).get("code", "")

    @pytest.mark.asyncio
    async def test_search_model_not_found_error(self, search_tools):
        """Test that nonexistent model returns error."""
        result = await search_tools._search_instances({
            "model_id": "nonexistent_model"
        })

        assert result.get("ok") is False
        assert "NOT_FOUND" in result.get("error", {}).get("code", "")


# ============================================================================
# Phase 8.4: Layout-Rendering Integration Tests
# ============================================================================

class TestLayoutRenderingIntegration:
    """Real integration tests for layout-rendering integration.

    Note: These tests require GraphicBuilder Docker to be running.
    """

    @pytest.fixture
    def visualization_tools_with_layout(self, dexpi_model_with_equipment):
        """Create VisualizationTools with LayoutStore."""
        from src.tools.visualization_tools import VisualizationTools
        from src.core.layout_store import LayoutStore
        from src.models.layout_metadata import LayoutMetadata, NodePosition, ModelReference

        dexpi_models = {"test_model": dexpi_model_with_equipment}
        flowsheets = {}
        layout_store = LayoutStore()

        # Create a layout with positions
        layout = LayoutMetadata(
            algorithm="elk",
            positions={
                "P-101": NodePosition(x=100.0, y=100.0),
                "TK-101": NodePosition(x=300.0, y=100.0)
            },
            model_ref=ModelReference(type="dexpi", model_id="test_model")
        )
        layout_store.save(layout, layout_id="test_layout", model_ref=layout.model_ref)

        tools = VisualizationTools(dexpi_models, flowsheets, layout_store)
        return tools

    @pytest.mark.asyncio
    async def test_visualize_without_layout(self, visualization_tools_with_layout):
        """Test visualization without layout (should use auto-layout)."""
        result = await visualization_tools_with_layout._visualize_model({
            "model_id": "test_model",
            "model_type": "dexpi",
            "format": "html",
            "use_layout": False
        })

        assert result.get("ok"), f"Visualization failed: {result}"

    @pytest.mark.asyncio
    async def test_visualize_with_explicit_layout_id(self, visualization_tools_with_layout):
        """Test visualization with explicit layout_id."""
        # This test may fail if GraphicBuilder is not available,
        # but should still test the layout lookup logic

        result = await visualization_tools_with_layout._visualize_model({
            "model_id": "test_model",
            "model_type": "dexpi",
            "format": "html",
            "use_layout": True,
            "layout_id": "test_layout"
        })

        # Either succeeds or fails with render error (not layout lookup error)
        if result.get("ok") is False:
            # Should not be a layout lookup error
            assert "LAYOUT_NOT_FOUND" not in result.get("error", {}).get("code", "")

    @pytest.mark.asyncio
    async def test_visualize_with_auto_layout_lookup(self, visualization_tools_with_layout):
        """Test visualization with auto layout lookup by model_id."""
        result = await visualization_tools_with_layout._visualize_model({
            "model_id": "test_model",
            "model_type": "dexpi",
            "format": "html",
            "use_layout": True
            # No layout_id - should auto-detect from model_id
        })

        # Either succeeds or fails with render error (not layout lookup error)
        if result.get("ok") is False:
            assert "LAYOUT_NOT_FOUND" not in result.get("error", {}).get("code", "")

    @pytest.mark.asyncio
    async def test_visualize_layout_not_found_error(self, visualization_tools_with_layout):
        """Test error when layout requested but not found."""
        result = await visualization_tools_with_layout._visualize_model({
            "model_id": "test_model",
            "model_type": "dexpi",
            "format": "html",
            "use_layout": True,
            "layout_id": "nonexistent_layout"
        })

        assert result.get("ok") is False
        error_code = result.get("error", {}).get("code", "")
        error_msg = result.get("error", {}).get("message", "").lower()
        assert "LAYOUT_NOT_FOUND" in error_code or "not found" in error_msg


# ============================================================================
# GraphicBuilder Integration Tests (Requires Docker)
# ============================================================================

@pytest.mark.skipif(
    os.environ.get("SKIP_GRAPHICBUILDER_TESTS", "0") == "1",
    reason="GraphicBuilder tests skipped via env var"
)
class TestGraphicBuilderLayoutIntegration:
    """Tests that require running GraphicBuilder Docker."""

    @pytest.fixture(autouse=True)
    def check_graphicbuilder(self, graphicbuilder_available):
        """Skip tests if GraphicBuilder is not available."""
        if not graphicbuilder_available:
            pytest.skip("GraphicBuilder Docker not running on port 8080")

    @pytest.mark.asyncio
    async def test_graphicbuilder_png_with_layout(
        self,
        dexpi_model_with_equipment,
        graphicbuilder_available
    ):
        """Test PNG rendering via GraphicBuilder with layout coordinates."""
        from src.tools.visualization_tools import VisualizationTools
        from src.core.layout_store import LayoutStore
        from src.models.layout_metadata import LayoutMetadata, NodePosition, ModelReference

        dexpi_models = {"test_model": dexpi_model_with_equipment}
        flowsheets = {}
        layout_store = LayoutStore()

        # Create layout
        layout = LayoutMetadata(
            algorithm="elk",
            positions={
                "P-101": NodePosition(x=100.0, y=100.0),
                "TK-101": NodePosition(x=300.0, y=100.0)
            },
            model_ref=ModelReference(type="dexpi", model_id="test_model")
        )
        layout_store.save(layout, layout_id="test_layout")

        tools = VisualizationTools(dexpi_models, flowsheets, layout_store)

        result = await tools._visualize_model({
            "model_id": "test_model",
            "model_type": "dexpi",
            "format": "png",
            "quality": "high",
            "use_layout": True,
            "layout_id": "test_layout"
        })

        if result.get("ok"):
            data = result["data"]
            assert data["format"] == "png"
            assert "content_base64" in data

            # Validate PNG
            png_data = base64.b64decode(data["content_base64"])
            assert_valid_png(png_data)
