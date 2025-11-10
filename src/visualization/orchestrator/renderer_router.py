"""
Renderer Router - Intelligent routing to appropriate renderer
Selects best renderer based on requirements
"""

import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class OutputFormat(Enum):
    """Supported output formats."""
    SVG = "SVG"
    PNG = "PNG"
    PDF = "PDF"
    HTML = "HTML"
    GRAPHML = "GRAPHML"
    JSON = "JSON"


class QualityLevel(Enum):
    """Rendering quality levels."""
    DRAFT = "draft"
    STANDARD = "standard"
    PRODUCTION = "production"


class Platform(Enum):
    """Target platform."""
    WEB = "web"
    DESKTOP = "desktop"
    PRINT = "print"
    API = "api"


@dataclass
class RenderRequirements:
    """Requirements for rendering."""
    format: OutputFormat
    quality: QualityLevel = QualityLevel.STANDARD
    platform: Platform = Platform.API
    interactive: bool = False
    speed: str = "normal"  # "fast", "normal", "slow"
    features: List[str] = None  # Required features


@dataclass
class RendererCapabilities:
    """Capabilities of a renderer."""
    name: str
    formats: List[OutputFormat]
    quality_levels: List[QualityLevel]
    platforms: List[Platform]
    interactive: bool
    speed: str  # "fast", "normal", "slow"
    features: List[str]  # Supported features


class RendererRouter:
    """
    Routes rendering requests to appropriate renderer.
    Implements the federated rendering platform strategy.
    """

    def __init__(self):
        """Initialize router with available renderers."""
        self.renderers = {}
        self._initialize_renderers()

    def _initialize_renderers(self):
        """Initialize available renderers and their capabilities."""

        # GraphicBuilder - Production quality DEXPI renderer
        self.renderers["graphicbuilder"] = RendererCapabilities(
            name="GraphicBuilder",
            formats=[OutputFormat.SVG, OutputFormat.PNG, OutputFormat.PDF],
            quality_levels=[QualityLevel.PRODUCTION],
            platforms=[Platform.DESKTOP, Platform.PRINT, Platform.API],
            interactive=False,
            speed="slow",
            features=[
                "full_dexpi_compliance",
                "imagemaps",
                "high_quality",
                "symbol_library",
                "complex_layouts"
            ]
        )

        # ProteusXMLDrawing - Web interactive viewer
        self.renderers["proteus_viewer"] = RendererCapabilities(
            name="ProteusXMLDrawing",
            formats=[OutputFormat.SVG, OutputFormat.HTML],
            quality_levels=[QualityLevel.STANDARD],
            platforms=[Platform.WEB],
            interactive=True,
            speed="normal",
            features=[
                "web_interactive",
                "pan_zoom",
                "selection",
                "realtime_updates",
                "collaboration"
            ]
        )

        # Simple Python renderer (future)
        self.renderers["python_simple"] = RendererCapabilities(
            name="SimplePythonRenderer",
            formats=[OutputFormat.SVG, OutputFormat.PNG],
            quality_levels=[QualityLevel.DRAFT],
            platforms=[Platform.API],
            interactive=False,
            speed="fast",
            features=[
                "quick_preview",
                "basic_layout",
                "minimal_dependencies"
            ]
        )

        # Plotly renderer (current HTML implementation)
        self.renderers["plotly"] = RendererCapabilities(
            name="PlotlyRenderer",
            formats=[OutputFormat.HTML, OutputFormat.JSON],
            quality_levels=[QualityLevel.STANDARD],
            platforms=[Platform.WEB, Platform.API],
            interactive=True,
            speed="fast",
            features=[
                "interactive_graph",
                "spring_layout",
                "quick_visualization",
                "web_based"
            ]
        )

    def select_renderer(self, requirements: RenderRequirements) -> str:
        """
        Select best renderer based on requirements.

        Args:
            requirements: Rendering requirements

        Returns:
            Renderer name
        """
        scores = {}

        for name, capabilities in self.renderers.items():
            if not self.validate_renderer_availability(name):
                logger.debug("Renderer %s is currently unavailable; skipping.", name)
                continue
            score = self._score_renderer(requirements, capabilities)
            scores[name] = score
            logger.debug(f"Renderer {name} score: {score}")

        if not scores:
            raise RuntimeError("No available renderers satisfy the requested requirements")

        # Select highest scoring renderer
        best_renderer = max(scores.keys(), key=lambda k: scores[k])

        logger.info(f"Selected renderer: {best_renderer} (score: {scores[best_renderer]})")

        return best_renderer

    def _score_renderer(
        self,
        requirements: RenderRequirements,
        capabilities: RendererCapabilities
    ) -> float:
        """
        Score a renderer against requirements.

        Args:
            requirements: Required features
            capabilities: Renderer capabilities

        Returns:
            Score (0-100)
        """
        score = 0.0

        # Format compatibility (required)
        if requirements.format not in capabilities.formats:
            return 0  # Cannot use this renderer

        # Platform compatibility (required)
        if requirements.platform not in capabilities.platforms:
            return 0  # Cannot use this renderer

        score = 50  # Base score for compatibility

        # Quality match (20 points)
        if requirements.quality in capabilities.quality_levels:
            score += 20
        elif requirements.quality == QualityLevel.PRODUCTION and \
             QualityLevel.STANDARD in capabilities.quality_levels:
            score += 10  # Partial credit

        # Speed preference (15 points)
        speed_scores = {
            ("fast", "fast"): 15,
            ("fast", "normal"): 5,
            ("normal", "normal"): 15,
            ("normal", "fast"): 10,
            ("normal", "slow"): 5,
            ("slow", "slow"): 15,
            ("slow", "normal"): 10
        }
        speed_key = (requirements.speed, capabilities.speed)
        score += speed_scores.get(speed_key, 0)

        # Interactive requirement (10 points)
        if requirements.interactive == capabilities.interactive:
            score += 10
        elif not requirements.interactive and capabilities.interactive:
            score += 5  # Can work but not optimal

        # Feature requirements (5 points)
        if requirements.features:
            matched = sum(1 for f in requirements.features if f in capabilities.features)
            score += (matched / len(requirements.features)) * 5

        return score

    def get_renderer_for_scenario(self, scenario: str) -> str:
        """
        Get renderer for common scenarios.

        Args:
            scenario: Scenario name

        Returns:
            Recommended renderer
        """
        scenarios = {
            "production_pdf": RenderRequirements(
                format=OutputFormat.PDF,
                quality=QualityLevel.PRODUCTION,
                platform=Platform.PRINT
            ),
            "web_interactive": RenderRequirements(
                format=OutputFormat.HTML,
                quality=QualityLevel.STANDARD,
                platform=Platform.WEB,
                interactive=True
            ),
            "quick_preview": RenderRequirements(
                format=OutputFormat.SVG,
                quality=QualityLevel.DRAFT,
                platform=Platform.API,
                speed="fast"
            ),
            "api_standard": RenderRequirements(
                format=OutputFormat.SVG,
                quality=QualityLevel.STANDARD,
                platform=Platform.API
            ),
            "current_html": RenderRequirements(
                format=OutputFormat.HTML,
                quality=QualityLevel.STANDARD,
                platform=Platform.WEB,
                interactive=True,
                speed="fast"
            )
        }

        if scenario not in scenarios:
            raise ValueError(f"Unknown scenario: {scenario}")

        return self.select_renderer(scenarios[scenario])

    def route_request(
        self,
        format: str = "SVG",
        quality: str = "standard",
        interactive: bool = False,
        platform: str = "api"
    ) -> Dict[str, Any]:
        """
        Route rendering request based on parameters.

        Args:
            format: Output format
            quality: Quality level
            interactive: Interactive requirement
            platform: Target platform

        Returns:
            Routing decision with renderer and config
        """
        try:
            # Parse requirements
            requirements = RenderRequirements(
                format=OutputFormat[format.upper()],
                quality=QualityLevel[quality.upper()],
                platform=Platform[platform.upper()],
                interactive=interactive
            )

            # Select renderer
            renderer = self.select_renderer(requirements)

            # Build configuration
            config = {
                "renderer": renderer,
                "format": format,
                "quality": quality,
                "options": self._get_renderer_options(renderer, requirements)
            }

            return config

        except Exception as e:
            logger.error(f"Failed to route request: {e}")
            # Fallback to default
            return {
                "renderer": "plotly",  # Current default
                "format": "HTML",
                "quality": "standard",
                "options": {}
            }

    def _get_renderer_options(
        self,
        renderer: str,
        requirements: RenderRequirements
    ) -> Dict[str, Any]:
        """
        Get renderer-specific options.

        Args:
            renderer: Renderer name
            requirements: Requirements

        Returns:
            Renderer options
        """
        options = {}

        if renderer == "graphicbuilder":
            options = {
                "dpi": 300 if requirements.quality == QualityLevel.PRODUCTION else 150,
                "include_imagemap": True,
                "scale": 1.0
            }
        elif renderer == "proteus_viewer":
            options = {
                "enable_pan_zoom": True,
                "enable_selection": requirements.interactive,
                "theme": "modern"
            }
        elif renderer == "plotly":
            options = {
                "layout": "spring",
                "node_size": 10,
                "show_labels": True
            }

        return options

    def list_renderers(self) -> List[Dict[str, Any]]:
        """
        List available renderers and capabilities.

        Returns:
            List of renderer information
        """
        renderers = []

        for name, caps in self.renderers.items():
            renderers.append({
                "name": caps.name,
                "id": name,
                "formats": [f.value for f in caps.formats],
                "quality_levels": [q.value for q in caps.quality_levels],
                "platforms": [p.value for p in caps.platforms],
                "interactive": caps.interactive,
                "speed": caps.speed,
                "features": caps.features
            })

        return renderers

    def validate_renderer_availability(self, renderer: str) -> bool:
        """
        Check if a renderer is available via health probes.

        Args:
            renderer: Renderer name

        Returns:
            True if available
        """
        if renderer not in self.renderers:
            return False

        # Check actual availability with health probes
        if renderer == "graphicbuilder":
            return self._check_graphicbuilder_health()
        elif renderer == "proteus_viewer":
            return self._check_proteus_health()
        elif renderer == "python_simple":
            return self._check_python_simple_health()
        elif renderer == "plotly":
            return self._check_plotly_health()

        return False

    def _check_graphicbuilder_health(self) -> bool:
        """
        Health check for GraphicBuilder Docker service.

        Checks:
        1. Docker is installed and running
        2. GraphicBuilder container/service is accessible
        3. Service responds to health endpoint

        Returns:
            True if GraphicBuilder is healthy
        """
        import subprocess
        import socket

        try:
            # Check if Docker is installed
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                timeout=5,
                check=False
            )
            if result.returncode != 0:
                logger.debug("GraphicBuilder unavailable: Docker not installed")
                return False

            # Check if Docker daemon is running
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5,
                check=False
            )
            if result.returncode != 0:
                logger.debug("GraphicBuilder unavailable: Docker daemon not running")
                return False

            # Check if GraphicBuilder service is running
            # Try to connect to expected port (default: 8080)
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(('localhost', 8080))
                sock.close()

                if result == 0:
                    logger.debug("GraphicBuilder health check: PASS")
                    return True
                else:
                    logger.debug("GraphicBuilder unavailable: Service not responding on port 8080")
                    return False
            except Exception as e:
                logger.debug(f"GraphicBuilder health check failed: {e}")
                return False

        except subprocess.TimeoutExpired:
            logger.debug("GraphicBuilder health check timeout")
            return False
        except FileNotFoundError:
            logger.debug("GraphicBuilder unavailable: Docker command not found")
            return False
        except Exception as e:
            logger.debug(f"GraphicBuilder health check exception: {e}")
            return False

    def _check_proteus_health(self) -> bool:
        """
        Health check for Proteus viewer service.

        Currently returns False as Proteus integration is not yet implemented.

        Returns:
            True if Proteus is healthy
        """
        # Proteus viewer not yet integrated
        logger.debug("Proteus viewer not yet available")
        return False

    def _check_python_simple_health(self) -> bool:
        """
        Health check for python_simple renderer.

        Checks if required dependencies are available.

        Returns:
            True if python_simple is healthy
        """
        try:
            import matplotlib
            import networkx
            return True
        except ImportError as e:
            logger.debug(f"python_simple unavailable: Missing dependency {e}")
            return False

    def _check_plotly_health(self) -> bool:
        """
        Health check for Plotly renderer.

        Checks if plotly is installed and can create figures.

        Returns:
            True if Plotly is healthy
        """
        try:
            import plotly.graph_objects as go
            # Try to create a simple figure to verify it works
            _ = go.Figure()
            return True
        except ImportError:
            logger.debug("Plotly unavailable: Module not installed")
            return False
        except Exception as e:
            logger.debug(f"Plotly health check failed: {e}")
            return False
