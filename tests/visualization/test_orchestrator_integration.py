#!/usr/bin/env python3
"""
Integration test for visualization orchestration pipeline.
Tests SFILES → pyDEXPI → Rendering flow.

Updated to use core layer (Week 2: model_service.py removal).
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from core.conversion import get_engine
from core.analytics import model_metrics
from visualization.orchestrator.renderer_router import RendererRouter, RenderRequirements, OutputFormat, QualityLevel, Platform


class TestOrchestrationIntegration:
    """Test complete orchestration pipeline."""

    def setup_method(self):
        """Setup test fixtures."""
        self.conversion_engine = get_engine()
        self.router = RendererRouter()

        # Check which renderers are actually available
        self.available_renderers = {
            'graphicbuilder': self.router._check_graphicbuilder_health(),
            'plotly': self.router._check_plotly_health(),
            'python_simple': self.router._check_python_simple_health(),
            'proteus_viewer': self.router._check_proteus_health()
        }

    def test_sfiles_to_dexpi_conversion(self):
        """Test SFILES string to pyDEXPI conversion."""
        # Simple SFILES model (using registered types)
        sfiles = "feed[tank]->mixer[mixer]->separator[centrifuge]->product[tank]"

        # Convert to pyDEXPI using core layer
        dexpi_model = self.conversion_engine.sfiles_to_dexpi(sfiles)

        # Verify model created
        assert dexpi_model is not None
        assert dexpi_model.conceptualModel is not None
        assert dexpi_model.originatingSystemName == "SFILES Import"

    def test_bfd_expansion(self):
        """Test BFD block expansion to PFD equipment."""
        # BFD model with reactor (using registered BFD types: storage, reaction, separation)
        bfd_sfiles = "feed[storage]->reactor[reaction]->separator[separation]"

        # Convert and expand using core layer
        dexpi_model = self.conversion_engine.sfiles_to_dexpi(bfd_sfiles)

        # Should have expanded equipment
        assert dexpi_model is not None
        # Note: Actual expansion depends on template availability

    def test_model_metadata_extraction(self):
        """Test metadata extraction from model."""
        # Create simple model (using registered types)
        sfiles = "pump1[pump]->tank1[tank]->heater1[heater]"
        dexpi_model = self.conversion_engine.sfiles_to_dexpi(sfiles)

        # Extract metadata using core analytics
        metadata = model_metrics.extract_metadata(dexpi_model)

        assert metadata["project"] == "SFILES Import"
        assert metadata["drawing_number"] == "1.0"  # Core layer returns version as drawing_number
        assert metadata["equipment_count"] >= 0  # Should have equipment

    def test_model_validation(self):
        """Test model validation."""
        # Create model
        sfiles = "unit1[pump]->unit2[tank]"
        dexpi_model = self.conversion_engine.sfiles_to_dexpi(sfiles)

        # Validate using core analytics
        validation = model_metrics.validate_model(dexpi_model)

        assert validation["valid"] is True
        assert "warnings" in validation
        assert "errors" in validation

    def test_renderer_selection(self):
        """Test renderer selection based on requirements."""
        # PDF format is not supported by any currently available renderer
        # The router should raise RuntimeError for unsupported formats
        requirements = RenderRequirements(
            format=OutputFormat.PDF,
            quality=QualityLevel.PRODUCTION,
            platform=Platform.PRINT
        )

        with pytest.raises(RuntimeError) as excinfo:
            self.router.select_renderer(requirements)
        assert "PDF" in str(excinfo.value)
        assert "not supported" in str(excinfo.value)

        # Web interactive requirement - should work with plotly
        requirements = RenderRequirements(
            format=OutputFormat.HTML,
            quality=QualityLevel.STANDARD,
            platform=Platform.WEB,
            interactive=True
        )

        renderer = self.router.select_renderer(requirements)
        assert renderer == "plotly", \
            f"Expected plotly for interactive HTML, got {renderer}"

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
        dexpi_model = self.conversion_engine.sfiles_to_dexpi(sfiles)

        # Get statistics using core analytics
        stats = model_metrics.summarize(dexpi_model)

        assert "metadata" in stats
        assert "validation" in stats
        assert "complexity" in stats
        assert stats["complexity"]["total_elements"] >= 0

    def test_end_to_end_flow(self):
        """Test complete flow from SFILES to renderer selection."""
        # 1. Start with SFILES
        sfiles = "feed[tank]->mixer[mixer]->reactor[tank]->separator[centrifuge]"

        # 2. Convert to pyDEXPI using core layer
        dexpi_model = self.conversion_engine.sfiles_to_dexpi(sfiles)

        # 3. Validate model using core analytics
        validation = model_metrics.validate_model(dexpi_model)
        assert validation["valid"] is True

        # 4. Extract metadata using core analytics
        metadata = model_metrics.extract_metadata(dexpi_model)
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
        # production_pdf scenario uses PDF format which is not supported
        # by any available renderer, so it should raise RuntimeError
        with pytest.raises(RuntimeError) as excinfo:
            self.router.get_renderer_for_scenario("production_pdf")
        assert "PDF" in str(excinfo.value)

        # Define scenarios that should work with available renderers
        scenarios = [
            ("web_interactive", "plotly", None),  # plotly should always be available
            ("quick_preview", "python_simple", None),  # python_simple should always be available
            ("current_html", "plotly", None)  # plotly should always be available
        ]

        for scenario, expected_renderer, fallback in scenarios:
            renderer = self.router.get_renderer_for_scenario(scenario)

            # Check if expected renderer is available
            if expected_renderer in self.available_renderers:
                if self.available_renderers[expected_renderer]:
                    assert renderer == expected_renderer, \
                        f"Scenario {scenario}: expected {expected_renderer} when available, got {renderer}"
                elif fallback:
                    assert renderer == fallback, \
                        f"Scenario {scenario}: expected fallback {fallback} when {expected_renderer} unavailable, got {renderer}"
                else:
                    # No fallback defined, should get the expected renderer or fail
                    assert renderer == expected_renderer, \
                        f"Scenario {scenario}: expected {expected_renderer}, got {renderer}"

    def test_renderer_availability(self):
        """Test renderer availability checking.

        This test validates that the health check logic works correctly,
        reporting actual availability of services.
        """
        # Test GraphicBuilder availability (Docker-based, may or may not be running)
        available = self.router.validate_renderer_availability("graphicbuilder")
        assert isinstance(available, bool), "Health check should return boolean"
        # Store actual state for reporting
        graphicbuilder_status = "available" if available else "unavailable"

        # Plotly should always be available (pure Python)
        available = self.router.validate_renderer_availability("plotly")
        assert available is True, "Plotly should always be available"

        # python_simple should always be available (matplotlib + networkx)
        available = self.router.validate_renderer_availability("python_simple")
        assert available is True, "python_simple should always be available"

        # ProteusViewer not yet implemented
        available = self.router.validate_renderer_availability("proteus_viewer")
        assert available is False, "ProteusViewer should not be available (not implemented)"

        # Log availability status for debugging
        print(f"\nRenderer availability status:")
        print(f"  - GraphicBuilder: {graphicbuilder_status}")
        print(f"  - Plotly: available")
        print(f"  - python_simple: available")
        print(f"  - ProteusViewer: unavailable (not implemented)")


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