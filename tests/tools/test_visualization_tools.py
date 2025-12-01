"""Tests for MCP visualization tools."""

import pytest
import asyncio
from unittest.mock import MagicMock, patch

from src.tools.visualization_tools import VisualizationTools
from src.utils.response import is_success


@pytest.fixture
def visualization_tools():
    """Create visualization tools with empty stores."""
    dexpi_models = {}
    flowsheets = {}
    return VisualizationTools(dexpi_models, flowsheets)


@pytest.fixture
def visualization_tools_with_sfiles():
    """Create visualization tools with a sample SFILES flowsheet."""
    from src.adapters.sfiles_adapter import get_flowsheet_class
    Flowsheet = get_flowsheet_class()

    # Use simple SFILES string format with linear flow
    flowsheet = Flowsheet(sfiles_in="(P-101)(T-101)")

    flowsheets = {"test_fs": flowsheet}
    dexpi_models = {}
    return VisualizationTools(dexpi_models, flowsheets)


@pytest.fixture
def visualization_tools_with_dexpi():
    """Create visualization tools with a sample DEXPI model."""
    from pydexpi.dexpi_classes.dexpiModel import DexpiModel, ConceptualModel
    from pydexpi.dexpi_classes.metaData import MetaData
    from pydexpi.dexpi_classes.equipment import Tank, CentrifugalPump

    # Create minimal DEXPI model with proper structure
    conceptual = ConceptualModel(
        metaData=MetaData(title="Test Model", description="Test visualization")
    )
    model = DexpiModel(conceptualModel=conceptual)

    # Add equipment
    tank = Tank(tagName="T-101")
    pump = CentrifugalPump(tagName="P-101")
    model.conceptualModel.taggedPlantItems = [tank, pump]

    dexpi_models = {"test_pid": model}
    flowsheets = {}
    return VisualizationTools(dexpi_models, flowsheets)


class TestVisualizationToolsGetTools:
    """Test tool registration."""

    def test_get_tools_returns_list(self, visualization_tools):
        """Test that get_tools returns a list of tools."""
        tools = visualization_tools.get_tools()
        assert isinstance(tools, list)
        assert len(tools) >= 2

    def test_visualize_model_tool_exists(self, visualization_tools):
        """Test that visualize_model tool is defined."""
        tools = visualization_tools.get_tools()
        tool_names = [t.name for t in tools]
        assert "visualize_model" in tool_names

    def test_visualize_list_renderers_tool_exists(self, visualization_tools):
        """Test that visualize_list_renderers tool is defined."""
        tools = visualization_tools.get_tools()
        tool_names = [t.name for t in tools]
        assert "visualize_list_renderers" in tool_names

    def test_visualize_model_schema(self, visualization_tools):
        """Test visualize_model has correct input schema."""
        tools = visualization_tools.get_tools()
        visualize_tool = next(t for t in tools if t.name == "visualize_model")

        schema = visualize_tool.inputSchema
        assert schema["type"] == "object"
        assert "model_id" in schema["properties"]
        assert "model_id" in schema["required"]
        assert "format" in schema["properties"]
        assert "quality" in schema["properties"]


class TestVisualizationToolsHandleTool:
    """Test tool handling."""

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(self, visualization_tools):
        """Test handling of unknown tool name."""
        result = await visualization_tools.handle_tool("unknown_tool", {})
        assert result["ok"] is False
        assert "UNKNOWN_TOOL" in result.get("error", {}).get("code", "")

    @pytest.mark.asyncio
    async def test_handle_visualize_model_not_found(self, visualization_tools):
        """Test visualize_model with non-existent model."""
        result = await visualization_tools.handle_tool(
            "visualize_model",
            {"model_id": "nonexistent"}
        )
        assert result["ok"] is False
        assert "not found" in result.get("error", {}).get("message", "").lower()


class TestListRenderers:
    """Test visualize_list_renderers tool."""

    @pytest.mark.asyncio
    async def test_list_renderers_returns_list(self, visualization_tools):
        """Test that list_renderers returns renderer information."""
        result = await visualization_tools.handle_tool(
            "visualize_list_renderers",
            {}
        )
        assert is_success(result)
        assert "renderers" in result["data"]
        assert isinstance(result["data"]["renderers"], list)

    @pytest.mark.asyncio
    async def test_list_renderers_includes_plotly(self, visualization_tools):
        """Test that Plotly renderer is listed."""
        result = await visualization_tools.handle_tool(
            "visualize_list_renderers",
            {}
        )
        renderer_ids = [r["id"] for r in result["data"]["renderers"]]
        assert "plotly" in renderer_ids

    @pytest.mark.asyncio
    async def test_list_renderers_includes_availability(self, visualization_tools):
        """Test that renderers include availability status."""
        result = await visualization_tools.handle_tool(
            "visualize_list_renderers",
            {}
        )
        for renderer in result["data"]["renderers"]:
            assert "available" in renderer
            assert isinstance(renderer["available"], bool)


class TestVisualizeModelSFILES:
    """Test visualize_model with SFILES flowsheets."""

    @pytest.mark.asyncio
    async def test_visualize_sfiles_html(self, visualization_tools_with_sfiles):
        """Test HTML visualization of SFILES flowsheet."""
        result = await visualization_tools_with_sfiles.handle_tool(
            "visualize_model",
            {"model_id": "test_fs", "format": "html"}
        )
        assert is_success(result)
        assert result["data"]["format"] == "html"
        assert result["data"]["renderer"] == "plotly"
        assert "content" in result["data"]
        assert "<html" in result["data"]["content"].lower()

    @pytest.mark.asyncio
    async def test_visualize_sfiles_auto_type(self, visualization_tools_with_sfiles):
        """Test auto-detection of model type for SFILES."""
        result = await visualization_tools_with_sfiles.handle_tool(
            "visualize_model",
            {"model_id": "test_fs", "model_type": "auto"}
        )
        assert is_success(result)
        assert result["data"]["model_type"] == "sfiles"

    @pytest.mark.asyncio
    async def test_visualize_sfiles_graphml(self, visualization_tools_with_sfiles):
        """Test GraphML export of SFILES flowsheet."""
        result = await visualization_tools_with_sfiles.handle_tool(
            "visualize_model",
            {"model_id": "test_fs", "format": "graphml"}
        )
        assert is_success(result)
        assert result["data"]["format"] == "graphml"
        assert "content" in result["data"]
        # GraphML is XML format
        assert "<?xml" in result["data"]["content"] or "<graphml" in result["data"]["content"]


class TestVisualizeModelDEXPI:
    """Test visualize_model with DEXPI models."""

    @pytest.mark.asyncio
    async def test_visualize_dexpi_html(self, visualization_tools_with_dexpi):
        """Test HTML visualization of DEXPI model."""
        result = await visualization_tools_with_dexpi.handle_tool(
            "visualize_model",
            {"model_id": "test_pid", "format": "html"}
        )
        assert is_success(result)
        assert result["data"]["format"] == "html"
        assert result["data"]["model_type"] == "dexpi"
        assert "content" in result["data"]

    @pytest.mark.asyncio
    async def test_visualize_dexpi_auto_type(self, visualization_tools_with_dexpi):
        """Test auto-detection of model type for DEXPI."""
        result = await visualization_tools_with_dexpi.handle_tool(
            "visualize_model",
            {"model_id": "test_pid", "model_type": "auto"}
        )
        assert is_success(result)
        assert result["data"]["model_type"] == "dexpi"


class TestRenderingOptions:
    """Test rendering options."""

    @pytest.mark.asyncio
    async def test_layout_option(self, visualization_tools_with_sfiles):
        """Test layout option is accepted."""
        result = await visualization_tools_with_sfiles.handle_tool(
            "visualize_model",
            {"model_id": "test_fs", "layout": "spring"}
        )
        assert is_success(result)

    @pytest.mark.asyncio
    async def test_quality_option(self, visualization_tools_with_sfiles):
        """Test quality option is accepted."""
        result = await visualization_tools_with_sfiles.handle_tool(
            "visualize_model",
            {"model_id": "test_fs", "quality": "standard"}
        )
        assert is_success(result)

    @pytest.mark.asyncio
    async def test_custom_options(self, visualization_tools_with_sfiles):
        """Test custom rendering options are accepted."""
        result = await visualization_tools_with_sfiles.handle_tool(
            "visualize_model",
            {
                "model_id": "test_fs",
                "options": {
                    "show_labels": True,
                    "node_size": 15,
                    "width": 1024,
                    "height": 768
                }
            }
        )
        assert is_success(result)


class TestPlotlyRendering:
    """Test Plotly rendering functionality."""

    def test_render_plotly_basic(self, visualization_tools_with_sfiles):
        """Test basic Plotly rendering."""
        # Get the flowsheet graph
        flowsheet = visualization_tools_with_sfiles.flowsheets["test_fs"]
        graph = flowsheet.state

        html = visualization_tools_with_sfiles._render_plotly(
            graph, "test", "spring", {}
        )

        assert "<html" in html.lower()
        assert "plotly" in html.lower()

    def test_render_plotly_with_options(self, visualization_tools_with_sfiles):
        """Test Plotly rendering with custom options."""
        flowsheet = visualization_tools_with_sfiles.flowsheets["test_fs"]
        graph = flowsheet.state

        html = visualization_tools_with_sfiles._render_plotly(
            graph,
            "test",
            "spring",
            {"show_labels": False, "node_size": 20}
        )

        assert "<html" in html.lower()


class TestGraphMLRouting:
    """Test GraphML export routing (bug fix verification)."""

    @pytest.mark.asyncio
    async def test_graphml_not_routed_through_renderer(self, visualization_tools_with_sfiles):
        """Test that GraphML requests go directly to export, not through renderer router.

        This verifies the fix for the GraphML routing bug where GraphML format
        could be incorrectly routed through the RendererRouter.
        """
        result = await visualization_tools_with_sfiles.handle_tool(
            "visualize_model",
            {"model_id": "test_fs", "format": "graphml"}
        )
        assert is_success(result)
        assert result["data"]["format"] == "graphml"
        assert result["data"]["renderer"] == "export"  # Should be export, not graphicbuilder
        assert "<?xml" in result["data"]["content"] or "<graphml" in result["data"]["content"]

    @pytest.mark.asyncio
    async def test_graphml_with_dexpi_model(self, visualization_tools_with_dexpi):
        """Test GraphML export with DEXPI model."""
        result = await visualization_tools_with_dexpi.handle_tool(
            "visualize_model",
            {"model_id": "test_pid", "format": "graphml"}
        )
        assert is_success(result)
        assert result["data"]["format"] == "graphml"
        assert result["data"]["renderer"] == "export"
        assert result["data"]["model_type"] == "dexpi"


class TestGraphicBuilderErrorHandling:
    """Test error handling in GraphicBuilder path."""

    @pytest.mark.asyncio
    async def test_graphicbuilder_unsupported_model_type(self, visualization_tools_with_sfiles):
        """Test that GraphicBuilder rejects non-DEXPI models.

        This test verifies error handling when GraphicBuilder is requested
        for an SFILES model (which it doesn't support).
        """
        # Force PNG format which would route to GraphicBuilder
        # Since GraphicBuilder isn't available, it should fall back to Plotly
        result = await visualization_tools_with_sfiles.handle_tool(
            "visualize_model",
            {"model_id": "test_fs", "format": "png"}
        )
        # Should succeed with fallback to Plotly
        assert is_success(result)
        # Either falls back to HTML or shows fallback info
        assert result["data"]["format"] == "html" or result["data"].get("fallback") is True

    @pytest.mark.asyncio
    async def test_visualization_with_invalid_format(self, visualization_tools_with_sfiles):
        """Test handling of invalid format option."""
        result = await visualization_tools_with_sfiles.handle_tool(
            "visualize_model",
            {"model_id": "test_fs", "format": "invalid_format"}
        )
        # Should return user-friendly error with INVALID_FORMAT code
        assert result["ok"] is False
        assert result["error"]["code"] == "INVALID_FORMAT"
        assert "Supported formats" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_visualization_with_invalid_quality(self, visualization_tools_with_sfiles):
        """Test handling of invalid quality option."""
        result = await visualization_tools_with_sfiles.handle_tool(
            "visualize_model",
            {"model_id": "test_fs", "quality": "ultra_hd"}
        )
        # Should return user-friendly error with INVALID_QUALITY code
        assert result["ok"] is False
        assert result["error"]["code"] == "INVALID_QUALITY"
        assert "Supported levels" in result["error"]["message"]
