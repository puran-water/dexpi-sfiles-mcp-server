#!/usr/bin/env python3
"""
GraphicBuilder Integration Tests
Tests Week 4 implementation: Docker rendering, router fallback, and full pipeline
"""

import asyncio
import pytest
import base64
import tempfile
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.visualization.graphicbuilder.wrapper import (
    GraphicBuilderRenderer,
    RenderOptions,
    RenderResult
)
from src.tools.dexpi_tools import DexpiTools
from src.tools.sfiles_tools import SfilesTools


# Test fixtures
@pytest.fixture
def simple_dexpi_xml():
    """Valid Proteus XML from DEXPI TrainingTestCases for testing."""
    # Use actual DEXPI training example that's known to work
    example_path = Path("/tmp/TrainingTestCases/dexpi 1.2/example pids/E03 Pump With Nozzles/E03V01-AUD.EX01.xml")

    # If TrainingTestCases not available, skip tests
    if not example_path.exists():
        pytest.skip("DEXPI TrainingTestCases not available - run: git clone https://gitlab.com/dexpi/TrainingTestCases /tmp/TrainingTestCases")

    return example_path.read_text()


@pytest.fixture
async def graphicbuilder_client():
    """Async GraphicBuilder client fixture."""
    client = GraphicBuilderRenderer(host="localhost", port=8080)
    yield client
    await client.close()


class TestGraphicBuilderSmoke:
    """Smoke tests that invoke actual GraphicBuilder service."""

    @pytest.mark.asyncio
    async def test_service_health_check(self, graphicbuilder_client):
        """Test GraphicBuilder service is running and healthy."""
        healthy = await graphicbuilder_client.health_check()
        assert healthy, "GraphicBuilder service should be healthy"

    @pytest.mark.asyncio
    async def test_render_svg(self, graphicbuilder_client, simple_dexpi_xml):
        """Test rendering to SVG format (currently returns PNG due to CLI limitations)."""
        result = await graphicbuilder_client.render(
            simple_dexpi_xml,
            format="SVG",
            options=RenderOptions(dpi=300, scale=1.0)
        )

        # NOTE: GraphicBuilder CLI only supports PNG, so even SVG requests return PNG
        assert result.format == "PNG"
        assert result.content is not None
        assert len(result.content) > 0
        assert result.encoded == True  # PNG should be base64 encoded

        # Verify it's valid base64-encoded PNG
        import base64
        decoded = base64.b64decode(result.content)
        assert decoded[:8] == b'\x89PNG\r\n\x1a\n'  # PNG header

    @pytest.mark.asyncio
    async def test_render_png(self, graphicbuilder_client, simple_dexpi_xml):
        """Test rendering to PNG format (base64 encoded)."""
        result = await graphicbuilder_client.render(
            simple_dexpi_xml,
            format="PNG",
            options=RenderOptions(dpi=300)
        )

        assert result.format == "PNG"
        assert result.content is not None
        assert result.encoded == True  # PNG should be base64

        # Verify base64 decoding works
        decoded = base64.b64decode(result.content)
        assert decoded[:8] == b'\x89PNG\r\n\x1a\n'  # PNG header

    @pytest.mark.asyncio
    async def test_render_pdf(self, graphicbuilder_client, simple_dexpi_xml):
        """Test rendering to PDF format (currently returns PNG due to CLI limitations)."""
        result = await graphicbuilder_client.render(
            simple_dexpi_xml,
            format="PDF",
            options=RenderOptions(dpi=300)
        )

        # NOTE: GraphicBuilder CLI only supports PNG
        assert result.format == "PNG"
        assert result.content is not None
        assert result.encoded == True  # PNG should be base64

        # Verify base64 decoding works - should be PNG, not PDF
        decoded = base64.b64decode(result.content)
        assert decoded[:8] == b'\x89PNG\r\n\x1a\n'  # PNG header

    @pytest.mark.asyncio
    async def test_save_to_file(self, graphicbuilder_client, simple_dexpi_xml):
        """Test saving rendered output to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            svg_path = Path(tmpdir) / "output.svg"
            png_path = Path(tmpdir) / "output.png"

            # Render and save SVG
            svg_result = await graphicbuilder_client.render(simple_dexpi_xml, format="SVG")
            svg_result.save_to_file(svg_path)
            assert svg_path.exists()
            assert svg_path.stat().st_size > 0

            # Render and save PNG
            png_result = await graphicbuilder_client.render(simple_dexpi_xml, format="PNG")
            png_result.save_to_file(png_path)
            assert png_path.exists()
            assert png_path.stat().st_size > 0

            # Verify PNG header
            assert png_path.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n'


class TestBase64DecodingRegression:
    """Regression tests for base64 encoding/decoding issues."""

    @pytest.mark.asyncio
    async def test_base64_roundtrip_png(self, graphicbuilder_client, simple_dexpi_xml):
        """Test PNG base64 encoding roundtrip doesn't corrupt data."""
        result = await graphicbuilder_client.render(simple_dexpi_xml, format="PNG")

        # Decode base64
        decoded = base64.b64decode(result.content)

        # Re-encode and verify matches
        reencoded = base64.b64encode(decoded).decode('utf-8')
        assert reencoded == result.content

        # Verify PNG structure
        assert decoded[:8] == b'\x89PNG\r\n\x1a\n'
        assert b'IEND' in decoded  # PNG end marker

    @pytest.mark.asyncio
    async def test_base64_no_padding_issues(self, graphicbuilder_client, simple_dexpi_xml):
        """Test base64 padding is correct."""
        result = await graphicbuilder_client.render(simple_dexpi_xml, format="PNG")

        # base64 should have proper padding
        # Length should be multiple of 4
        assert len(result.content) % 4 == 0

        # Should not raise on decode
        try:
            decoded = base64.b64decode(result.content)
            assert len(decoded) > 0
        except Exception as e:
            pytest.fail(f"Base64 decode failed: {e}")

    @pytest.mark.asyncio
    async def test_svg_not_base64(self, graphicbuilder_client, simple_dexpi_xml):
        """Regression: GraphicBuilder CLI currently only produces PNG (base64)."""
        result = await graphicbuilder_client.render(simple_dexpi_xml, format="SVG")

        # NOTE: CLI limitation - always returns PNG even when SVG requested
        assert result.format == "PNG"
        assert result.encoded == True
        assert isinstance(result.content, str)

        # Should be valid base64 (PNG)
        try:
            decoded = base64.b64decode(result.content)
            assert decoded[:8] == b'\x89PNG\r\n\x1a\n'
        except Exception as e:
            pytest.fail(f"PNG content should be valid base64: {e}")


class TestRendererRouterFallback:
    """Test router fallback when GraphicBuilder Docker is unavailable."""

    @pytest.mark.asyncio
    async def test_fallback_when_service_unavailable(self, simple_dexpi_xml):
        """Test router falls back when GraphicBuilder is down."""
        # Use non-existent port to simulate service down
        client = GraphicBuilderRenderer(host="localhost", port=9999)

        healthy = await client.health_check()
        assert not healthy, "Health check should fail for unavailable service"

        await client.close()

    def test_router_capabilities_registered(self):
        """Test that GraphicBuilder is registered in router."""
        from src.visualization.orchestrator.renderer_router import RendererRouter

        router = RendererRouter()

        assert "graphicbuilder" in router.renderers
        caps = router.renderers["graphicbuilder"]

        assert caps.name == "GraphicBuilder"
        assert "full_dexpi_compliance" in caps.features
        assert "high_quality" in caps.features


class TestFullPipeline:
    """End-to-end pipeline tests: SFILES → pyDEXPI → GraphicBuilder."""

    @pytest.mark.asyncio
    async def test_sfiles_to_dexpi_to_graphicbuilder(self, graphicbuilder_client):
        """Test complete pipeline from SFILES flowsheet to rendered SVG."""
        # Step 1: Create SFILES flowsheet
        sfiles_tools = SfilesTools({})

        result = await sfiles_tools.handle_tool("sfiles_create_flowsheet", {
            "name": "Test Plant",
            "type": "PFD"
        })
        assert result["status"] == "success"
        flowsheet_id = result["data"]["flowsheet_id"]

        # Step 2: Add units to flowsheet
        await sfiles_tools.handle_tool("sfiles_add_unit", {
            "flowsheet_id": flowsheet_id,
            "unit_type": "reactor",
            "unit_name": "Main Reactor"
        })

        await sfiles_tools.handle_tool("sfiles_add_unit", {
            "flowsheet_id": flowsheet_id,
            "unit_type": "pump",
            "unit_name": "Feed Pump"
        })

        # Step 3: Convert SFILES to DEXPI
        dexpi_tools = DexpiTools({})

        convert_result = await dexpi_tools.handle_tool("sfiles_convert_from_sfiles", {
            "flowsheet_id": flowsheet_id
        })

        # Check if conversion is implemented
        if convert_result["status"] == "error":
            pytest.skip("SFILES to DEXPI conversion not yet implemented")

        model_id = convert_result["data"]["model_id"]

        # Step 4: Export DEXPI to Proteus XML
        export_result = await dexpi_tools.handle_tool("dexpi_export_proteus_xml", {
            "model_id": model_id
        })

        if export_result["status"] == "error":
            pytest.skip("Proteus XML export not yet implemented")

        proteus_xml = export_result["data"]["xml"]

        # Step 5: Render with GraphicBuilder
        render_result = await graphicbuilder_client.render(
            proteus_xml,
            format="SVG"
        )

        assert render_result.format == "SVG"
        assert len(render_result.content) > 0

    @pytest.mark.asyncio
    async def test_dexpi_model_to_graphicbuilder(self, graphicbuilder_client):
        """Test rendering from DEXPI model created via MCP tools."""
        dexpi_tools = DexpiTools({})

        # Create P&ID
        create_result = await dexpi_tools.handle_tool("dexpi_create_pid", {
            "project_name": "Test Plant",
            "drawing_number": "PID-001"
        })
        assert create_result["status"] == "success"
        model_id = create_result["data"]["model_id"]

        # Add equipment
        await dexpi_tools.handle_tool("dexpi_add_equipment", {
            "model_id": model_id,
            "equipment_type": "CentrifugalPump",
            "tag_name": "P-101"
        })

        await dexpi_tools.handle_tool("dexpi_add_equipment", {
            "model_id": model_id,
            "equipment_type": "Tank",
            "tag_name": "TK-101"
        })

        # Export to Proteus XML
        export_result = await dexpi_tools.handle_tool("dexpi_export_proteus_xml", {
            "model_id": model_id
        })

        if export_result["status"] == "error":
            pytest.skip("Proteus XML export not yet implemented")

        proteus_xml = export_result["data"]["xml"]

        # Render with GraphicBuilder
        render_result = await graphicbuilder_client.render(
            proteus_xml,
            format="SVG"
        )

        assert render_result.format == "SVG"
        assert len(render_result.content) > 0

        # Verify both equipment items are referenced
        assert "P-101" in render_result.content
        assert "TK-101" in render_result.content


class TestRenderOptions:
    """Test various rendering options and configurations."""

    @pytest.mark.asyncio
    async def test_custom_dpi(self, graphicbuilder_client, simple_dexpi_xml):
        """Test rendering with custom DPI settings."""
        result_300 = await graphicbuilder_client.render(
            simple_dexpi_xml,
            format="PNG",
            options=RenderOptions(dpi=300)
        )

        result_600 = await graphicbuilder_client.render(
            simple_dexpi_xml,
            format="PNG",
            options=RenderOptions(dpi=600)
        )

        # Higher DPI should produce larger file
        size_300 = len(base64.b64decode(result_300.content))
        size_600 = len(base64.b64decode(result_600.content))

        assert size_600 > size_300

    @pytest.mark.asyncio
    async def test_scale_factor(self, graphicbuilder_client, simple_dexpi_xml):
        """Test rendering with different scale factors."""
        result_1x = await graphicbuilder_client.render(
            simple_dexpi_xml,
            format="SVG",
            options=RenderOptions(scale=1.0)
        )

        result_2x = await graphicbuilder_client.render(
            simple_dexpi_xml,
            format="SVG",
            options=RenderOptions(scale=2.0)
        )

        assert len(result_1x.content) > 0
        assert len(result_2x.content) > 0

    @pytest.mark.asyncio
    async def test_imagemap_support(self, graphicbuilder_client, simple_dexpi_xml):
        """Test imagemap generation for interactive SVG."""
        result = await graphicbuilder_client.render(
            simple_dexpi_xml,
            format="SVG",
            options=RenderOptions(include_imagemap=True)
        )

        # Check if imagemap data is present
        imagemap = result.extract_imagemap()
        # Note: May be None if simple_dexpi_xml doesn't have interactive elements
        # Just verify the method doesn't crash


class TestCaching:
    """Test client-side caching behavior."""

    @pytest.mark.asyncio
    async def test_cache_same_request(self, graphicbuilder_client, simple_dexpi_xml):
        """Test that identical requests use cache."""
        # First request
        result1 = await graphicbuilder_client.render(
            simple_dexpi_xml,
            format="SVG"
        )

        # Second identical request (should be cached)
        result2 = await graphicbuilder_client.render(
            simple_dexpi_xml,
            format="SVG"
        )

        # Both should have same content
        assert result1.content == result2.content

    @pytest.mark.asyncio
    async def test_cache_different_formats(self, graphicbuilder_client, simple_dexpi_xml):
        """Test that different formats have separate cache entries."""
        result_svg = await graphicbuilder_client.render(
            simple_dexpi_xml,
            format="SVG"
        )

        result_png = await graphicbuilder_client.render(
            simple_dexpi_xml,
            format="PNG"
        )

        # Should be different content
        assert result_svg.format != result_png.format
        assert result_svg.content != result_png.content


if __name__ == "__main__":
    # Run with: pytest tests/test_graphicbuilder_integration.py -v
    pytest.main([__file__, "-v", "-s"])
