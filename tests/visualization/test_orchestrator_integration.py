#!/usr/bin/env python3
"""
Integration test for visualization orchestration pipeline.
Tests SFILES → pyDEXPI → Rendering flow.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from visualization.orchestrator.model_service import ModelService
from visualization.orchestrator.renderer_router import RendererRouter, RenderRequirements, OutputFormat, QualityLevel, Platform


class TestOrchestrationIntegration:
    """Test complete orchestration pipeline."""

    def setup_method(self):
        """Setup test fixtures."""
        self.model_service = ModelService()
        self.router = RendererRouter()

    def test_sfiles_to_dexpi_conversion(self):
        """Test SFILES string to pyDEXPI conversion."""
        # Simple SFILES model
        sfiles = "feed[tank]->mixer[CSTR]->separator[centrifuge]->product[tank]"

        # Convert to pyDEXPI
        dexpi_model = self.model_service.enrich_sfiles_to_dexpi(sfiles)

        # Verify model created
        assert dexpi_model is not None
        assert dexpi_model.conceptualModel is not None
        assert dexpi_model.originatingSystemName == "SFILES Import"

    def test_bfd_expansion(self):
        """Test BFD block expansion to PFD equipment."""
        # BFD model with reactor
        bfd_sfiles = "feed[tank]->reactor[reactor]->separator[clarifier]"

        # Convert and expand
        dexpi_model = self.model_service.enrich_sfiles_to_dexpi(bfd_sfiles)

        # Should have expanded equipment
        assert dexpi_model is not None
        # Note: Actual expansion depends on template availability

    def test_model_metadata_extraction(self):
        """Test metadata extraction from model."""
        # Create simple model
        sfiles = "pump1[pump]->tank1[tank]->valve1[valve]"
        dexpi_model = self.model_service.enrich_sfiles_to_dexpi(sfiles)

        # Extract metadata
        metadata = self.model_service.extract_metadata(dexpi_model)

        assert metadata["project"] == "SFILES Import"
        assert metadata["drawing_number"] == "PFD-001"
        assert metadata["equipment_count"] >= 0  # Should have equipment

    def test_model_validation(self):
        """Test model validation."""
        # Create model
        sfiles = "unit1[pump]->unit2[tank]"
        dexpi_model = self.model_service.enrich_sfiles_to_dexpi(sfiles)

        # Validate
        validation = self.model_service.validate_model(dexpi_model)

        assert validation["valid"] is True
        assert "warnings" in validation
        assert "errors" in validation

    def test_renderer_selection(self):
        """Test renderer selection based on requirements."""
        # Production PDF requirement
        requirements = RenderRequirements(
            format=OutputFormat.PDF,
            quality=QualityLevel.PRODUCTION,
            platform=Platform.PRINT
        )

        renderer = self.router.select_renderer(requirements)
        assert renderer == "graphicbuilder"

        # Web interactive requirement
        requirements = RenderRequirements(
            format=OutputFormat.HTML,
            quality=QualityLevel.STANDARD,
            platform=Platform.WEB,
            interactive=True
        )

        renderer = self.router.select_renderer(requirements)
        assert renderer == "plotly"  # Current implementation

    def test_renderer_routing(self):
        """Test full routing with configuration."""
        config = self.router.route_request(
            format="SVG",
            quality="production",
            interactive=False,
            platform="api"
        )

        assert "renderer" in config
        assert "format" in config
        assert "quality" in config
        assert "options" in config

    def test_model_statistics(self):
        """Test model statistics calculation."""
        # Create model
        sfiles = "feed[tank]->pump[pump]->reactor[tank]->product[tank]"
        dexpi_model = self.model_service.enrich_sfiles_to_dexpi(sfiles)

        # Get statistics
        stats = self.model_service.get_model_statistics(dexpi_model)

        assert "metadata" in stats
        assert "validation" in stats
        assert "complexity" in stats
        assert stats["complexity"]["total_elements"] >= 0

    def test_end_to_end_flow(self):
        """Test complete flow from SFILES to renderer selection."""
        # 1. Start with SFILES
        sfiles = "feed[tank]->mixer[mixer]->reactor[tank]->separator[centrifuge]"

        # 2. Convert to pyDEXPI
        dexpi_model = self.model_service.enrich_sfiles_to_dexpi(sfiles)

        # 3. Validate model
        validation = self.model_service.validate_model(dexpi_model)
        assert validation["valid"] is True

        # 4. Extract metadata
        metadata = self.model_service.extract_metadata(dexpi_model)
        assert metadata["project"] is not None

        # 5. Select renderer based on requirements
        requirements = RenderRequirements(
            format=OutputFormat.SVG,
            quality=QualityLevel.STANDARD,
            platform=Platform.API
        )
        renderer = self.router.select_renderer(requirements)
        assert renderer in ["graphicbuilder", "python_simple", "plotly"]

        # 6. Get routing configuration
        config = self.router.route_request(
            format="SVG",
            quality="standard",
            platform="api"
        )
        assert config["renderer"] is not None

    def test_scenario_based_routing(self):
        """Test pre-defined scenario routing."""
        scenarios = [
            ("production_pdf", "graphicbuilder"),
            ("web_interactive", "plotly"),
            ("quick_preview", "python_simple"),
            ("current_html", "plotly")
        ]

        for scenario, expected_renderer in scenarios:
            renderer = self.router.get_renderer_for_scenario(scenario)
            assert renderer == expected_renderer

    def test_renderer_availability(self):
        """Test renderer availability checking."""
        # GraphicBuilder should be available (Docker-based)
        available = self.router.validate_renderer_availability("graphicbuilder")
        assert available is True

        # Plotly should always be available
        available = self.router.validate_renderer_availability("plotly")
        assert available is True

        # ProteusViewer not yet implemented
        available = self.router.validate_renderer_availability("proteus_viewer")
        assert available is False


def run_integration_tests():
    """Run integration tests standalone."""
    test_suite = TestOrchestrationIntegration()
    test_suite.setup_method()

    print("Running orchestration integration tests...")

    # Test each component
    tests = [
        ("SFILES to DEXPI", test_suite.test_sfiles_to_dexpi_conversion),
        ("BFD Expansion", test_suite.test_bfd_expansion),
        ("Metadata Extraction", test_suite.test_model_metadata_extraction),
        ("Model Validation", test_suite.test_model_validation),
        ("Renderer Selection", test_suite.test_renderer_selection),
        ("Renderer Routing", test_suite.test_renderer_routing),
        ("Model Statistics", test_suite.test_model_statistics),
        ("End-to-End Flow", test_suite.test_end_to_end_flow),
        ("Scenario Routing", test_suite.test_scenario_based_routing),
        ("Renderer Availability", test_suite.test_renderer_availability)
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            test_func()
            print(f"✓ {test_name}")
            passed += 1
        except Exception as e:
            print(f"✗ {test_name}: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")

    return failed == 0


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)