"""MCP tools for model visualization.

Exposes visualization capabilities through MCP interface, routing to
appropriate renderers based on requirements and availability.
"""

import base64
import json
import logging
from typing import Any, Dict, List, Optional

from mcp import Tool

from ..utils.response import success_response, error_response
from ..visualization.orchestrator.renderer_router import (
    RendererRouter,
    OutputFormat,
    QualityLevel,
    Platform,
    RenderRequirements
)
from ..converters.graph_converter import UnifiedGraphConverter

logger = logging.getLogger(__name__)


class VisualizationTools:
    """Provides visualization tools for engineering models."""

    def __init__(self, dexpi_models: Dict[str, Any], flowsheets: Dict[str, Any]):
        """Initialize with model stores.

        Args:
            dexpi_models: Store of DEXPI models
            flowsheets: Store of SFILES flowsheets
        """
        self.dexpi_models = dexpi_models
        self.flowsheets = flowsheets
        self.router = RendererRouter()
        self.converter = UnifiedGraphConverter()

    def get_tools(self) -> List[Tool]:
        """Return visualization MCP tools."""
        return [
            Tool(
                name="visualize_model",
                description="Generate visualization of a model. Routes to appropriate renderer based on format and availability. Returns HTML (Plotly) by default for interactive viewing.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {
                            "type": "string",
                            "description": "ID of model to visualize"
                        },
                        "model_type": {
                            "type": "string",
                            "enum": ["dexpi", "sfiles", "auto"],
                            "description": "Model type (auto-detect if not specified)",
                            "default": "auto"
                        },
                        "format": {
                            "type": "string",
                            "enum": ["html", "png", "graphml"],
                            "description": "Output format. HTML is interactive, PNG is production quality.",
                            "default": "html"
                        },
                        "quality": {
                            "type": "string",
                            "enum": ["draft", "standard", "production"],
                            "description": "Rendering quality level",
                            "default": "standard"
                        },
                        "layout": {
                            "type": "string",
                            "enum": ["spring", "hierarchical", "auto"],
                            "description": "Layout algorithm to use",
                            "default": "spring"
                        },
                        "options": {
                            "type": "object",
                            "description": "Renderer-specific options",
                            "properties": {
                                "show_labels": {
                                    "type": "boolean",
                                    "description": "Show node labels",
                                    "default": True
                                },
                                "node_size": {
                                    "type": "integer",
                                    "description": "Node size in pixels",
                                    "default": 10
                                },
                                "width": {
                                    "type": "integer",
                                    "description": "Output width in pixels",
                                    "default": 800
                                },
                                "height": {
                                    "type": "integer",
                                    "description": "Output height in pixels",
                                    "default": 600
                                }
                            }
                        }
                    },
                    "required": ["model_id"]
                }
            ),
            Tool(
                name="visualize_list_renderers",
                description="List available visualization renderers and their capabilities",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            )
        ]

    async def handle_tool(self, name: str, arguments: dict) -> dict:
        """Route tool call to appropriate handler."""
        handlers = {
            "visualize_model": self._visualize_model,
            "visualize_list_renderers": self._list_renderers
        }

        handler = handlers.get(name)
        if not handler:
            return error_response(f"Unknown visualization tool: {name}", code="UNKNOWN_TOOL")

        try:
            return await handler(arguments)
        except Exception as e:
            logger.error(f"Error in {name}: {e}")
            return error_response(str(e), code="VISUALIZATION_ERROR")

    async def _visualize_model(self, args: dict) -> dict:
        """Visualize a model using appropriate renderer.

        Args:
            args: Tool arguments including model_id, format, quality, etc.

        Returns:
            Visualization result with content or URL
        """
        model_id = args["model_id"]
        model_type = args.get("model_type", "auto")
        output_format = args.get("format", "html").upper()
        quality = args.get("quality", "standard")
        layout = args.get("layout", "spring")
        options = args.get("options", {})

        # Validate format enum
        valid_formats = {"HTML", "PNG", "GRAPHML", "SVG", "PDF", "JSON"}
        if output_format not in valid_formats:
            return error_response(
                f"Invalid format '{output_format}'. Supported formats: {sorted(valid_formats)}",
                code="INVALID_FORMAT"
            )

        # Validate quality enum
        valid_qualities = {"draft", "standard", "production"}
        if quality.lower() not in valid_qualities:
            return error_response(
                f"Invalid quality '{quality}'. Supported levels: {sorted(valid_qualities)}",
                code="INVALID_QUALITY"
            )

        # Auto-detect model type
        if model_type == "auto":
            if model_id in self.dexpi_models:
                model_type = "dexpi"
            elif model_id in self.flowsheets:
                model_type = "sfiles"
            else:
                return error_response(
                    f"Model {model_id} not found in any store",
                    code="MODEL_NOT_FOUND"
                )

        # Get the model
        if model_type == "dexpi":
            if model_id not in self.dexpi_models:
                return error_response(f"DEXPI model {model_id} not found", code="MODEL_NOT_FOUND")
            model = self.dexpi_models[model_id]
            graph = self.converter.dexpi_to_networkx(model)
        else:
            if model_id not in self.flowsheets:
                return error_response(f"Flowsheet {model_id} not found", code="MODEL_NOT_FOUND")
            flowsheet = self.flowsheets[model_id]
            graph = flowsheet.state

        # Handle GraphML export directly (no renderer needed - it's a data export)
        if output_format == "GRAPHML":
            if model_type == "dexpi":
                graphml = self.converter.dexpi_to_graphml(model)
            else:
                graphml = self.converter.sfiles_to_graphml(flowsheet)
            return success_response({
                "model_id": model_id,
                "model_type": model_type,
                "format": "graphml",
                "renderer": "export",
                "content_type": "application/graphml+xml",
                "content": graphml,
                "node_count": graph.number_of_nodes(),
                "edge_count": graph.number_of_edges()
            })

        # Route to appropriate renderer for visual formats
        try:
            requirements = RenderRequirements(
                format=OutputFormat[output_format],
                quality=QualityLevel[quality.upper()],
                platform=Platform.API,
                interactive=(output_format == "HTML")
            )
            selected_renderer = self.router.select_renderer(requirements)
        except RuntimeError as e:
            # Fall back to Plotly HTML if no renderer available
            logger.warning(f"No renderer available for {output_format}, falling back to HTML: {e}")
            selected_renderer = "plotly"
            output_format = "HTML"

        # Generate visualization
        if selected_renderer == "plotly":
            content = self._render_plotly(graph, model_id, layout, options)
            return success_response({
                "model_id": model_id,
                "model_type": model_type,
                "format": "html",
                "renderer": "plotly",
                "content_type": "text/html",
                "content": content,
                "node_count": graph.number_of_nodes(),
                "edge_count": graph.number_of_edges()
            })

        elif selected_renderer == "graphicbuilder":
            # GraphicBuilder PNG rendering
            result = await self._render_graphicbuilder(model, model_type, options)
            if result.get("ok") is False:
                return result
            return success_response({
                "model_id": model_id,
                "model_type": model_type,
                "format": "png",
                "renderer": "graphicbuilder",
                "content_type": "image/png",
                "content_base64": result.get("content_base64"),
                "node_count": graph.number_of_nodes(),
                "edge_count": graph.number_of_edges()
            })

        else:
            # Fallback to Plotly HTML
            content = self._render_plotly(graph, model_id, layout, options)
            return success_response({
                "model_id": model_id,
                "model_type": model_type,
                "format": "html",
                "renderer": "plotly",
                "content_type": "text/html",
                "content": content,
                "fallback": True,
                "fallback_reason": f"Renderer {selected_renderer} not fully implemented"
            })

    def _render_plotly(
        self,
        graph,
        model_id: str,
        layout: str = "spring",
        options: dict = None
    ) -> str:
        """Render graph using Plotly for interactive HTML visualization.

        Args:
            graph: NetworkX graph to visualize
            model_id: Model identifier for title
            layout: Layout algorithm (spring, hierarchical)
            options: Additional rendering options

        Returns:
            HTML string with interactive Plotly visualization
        """
        import networkx as nx

        try:
            import plotly.graph_objects as go
        except ImportError:
            logger.error("Plotly not installed")
            raise RuntimeError("Plotly is required for HTML visualization. Install with: pip install plotly")

        options = options or {}
        show_labels = options.get("show_labels", True)
        node_size = options.get("node_size", 10)
        width = options.get("width", 800)
        height = options.get("height", 600)

        # Compute layout
        if layout == "hierarchical" and nx.is_directed_acyclic_graph(graph):
            try:
                # Use topological layout for DAGs
                for i, layer in enumerate(nx.topological_generations(graph)):
                    for j, node in enumerate(layer):
                        graph.nodes[node]["pos"] = (j - len(layer)/2, -i)
                pos = {node: data["pos"] for node, data in graph.nodes(data=True)}
            except Exception:
                pos = nx.spring_layout(graph, seed=42)
        else:
            pos = nx.spring_layout(graph, seed=42)

        # Extract node positions
        node_x = [pos[node][0] for node in graph.nodes()]
        node_y = [pos[node][1] for node in graph.nodes()]

        # Extract edge positions
        edge_x = []
        edge_y = []
        for edge in graph.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        # Create edge trace
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=1, color='#888'),
            hoverinfo='none',
            mode='lines'
        )

        # Get node labels and types
        node_text = []
        node_colors = []
        for node in graph.nodes():
            data = graph.nodes[node]
            label = data.get('tag') or data.get('tagName') or data.get('label') or str(node)
            node_type = data.get('type', 'unknown')
            node_text.append(f"{label}<br>Type: {node_type}")

            # Color by type
            if 'pump' in node_type.lower():
                node_colors.append('#1f77b4')
            elif 'tank' in node_type.lower() or 'vessel' in node_type.lower():
                node_colors.append('#2ca02c')
            elif 'valve' in node_type.lower():
                node_colors.append('#ff7f0e')
            elif 'heat' in node_type.lower() or 'exchanger' in node_type.lower():
                node_colors.append('#d62728')
            elif 'control' in node_type.lower() or 'instrument' in node_type.lower():
                node_colors.append('#9467bd')
            else:
                node_colors.append('#7f7f7f')

        # Create node trace
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text' if show_labels else 'markers',
            hoverinfo='text',
            text=[graph.nodes[node].get('tag') or str(node) for node in graph.nodes()] if show_labels else None,
            textposition="top center",
            hovertext=node_text,
            marker=dict(
                showscale=False,
                color=node_colors,
                size=node_size,
                line_width=2
            )
        )

        # Create figure
        fig = go.Figure(
            data=[edge_trace, node_trace],
            layout=go.Layout(
                title=dict(text=f"Model: {model_id}", font=dict(size=16)),
                showlegend=False,
                hovermode='closest',
                margin=dict(b=20, l=5, r=5, t=40),
                width=width,
                height=height,
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
            )
        )

        return fig.to_html(include_plotlyjs='cdn', full_html=True)

    async def _render_graphicbuilder(
        self,
        model,
        model_type: str,
        options: dict = None
    ) -> dict:
        """Render using GraphicBuilder (PNG output).

        Args:
            model: DEXPI model to render
            model_type: Model type (must be 'dexpi')
            options: Rendering options

        Returns:
            Dict with status and base64-encoded PNG content
        """
        if model_type != "dexpi":
            return error_response(
                "GraphicBuilder only supports DEXPI models",
                code="UNSUPPORTED_MODEL_TYPE"
            )

        try:
            from ..visualization.graphicbuilder.wrapper import GraphicBuilderWrapper

            wrapper = GraphicBuilderWrapper()
            if not wrapper.is_healthy():
                return error_response(
                    "GraphicBuilder service is not available",
                    code="SERVICE_UNAVAILABLE"
                )

            # Export model to temp file and render
            import tempfile
            from pydexpi.loaders import ProteusExporter

            with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
                exporter = ProteusExporter(model)
                exporter.export(f.name)
                temp_xml = f.name

            # Render PNG
            png_path = temp_xml.replace('.xml', '.png')
            result = wrapper.render(temp_xml, png_path, format='png')

            if result.get("status") == "success":
                # Read and base64 encode the PNG
                with open(png_path, 'rb') as f:
                    png_data = f.read()
                content_base64 = base64.b64encode(png_data).decode('utf-8')

                # Cleanup temp files
                import os
                os.unlink(temp_xml)
                os.unlink(png_path)

                return {"status": "success", "content_base64": content_base64}
            else:
                return error_response(
                    result.get("error", "GraphicBuilder render failed"),
                    code="RENDER_FAILED"
                )

        except ImportError as e:
            return error_response(
                f"GraphicBuilder wrapper not available: {e}",
                code="MODULE_NOT_FOUND"
            )
        except Exception as e:
            logger.error(f"GraphicBuilder render error: {e}")
            return error_response(str(e), code="RENDER_ERROR")

    async def _list_renderers(self, args: dict) -> dict:
        """List available renderers and their capabilities.

        Args:
            args: Tool arguments (empty for this tool)

        Returns:
            List of renderers with capabilities and health status
        """
        renderers = self.router.list_renderers()

        # Add health status to each renderer
        for renderer in renderers:
            renderer_id = renderer["id"]
            renderer["available"] = self.router.validate_renderer_availability(renderer_id)

        return success_response({
            "renderers": renderers,
            "default": "plotly",
            "recommended_for_html": "plotly",
            "recommended_for_png": "graphicbuilder"
        })
