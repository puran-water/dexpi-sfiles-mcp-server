"""MCP tools for layout computation and management.

Provides tools to:
- Compute layouts using ELK (layered, orthogonal routing)
- Save/load layouts to/from project files
- Get layout information and statistics

Architecture Decision (Codex Consensus #019adb91):
    - Layouts stored alongside models in project structure
    - ELK via elkjs for P&ID-quality layouts
    - Etag-based optimistic concurrency for updates
"""

import logging
from typing import Any, Dict, List, Optional

import networkx as nx
from mcp import Tool

from ..core.layout_store import LayoutStore, LayoutNotFoundError, OptimisticLockError
from ..layout.engines.elk import ELKLayoutEngine, PID_LAYOUT_OPTIONS
from ..models.layout_metadata import LayoutMetadata, ModelReference
from ..utils.response import success_response, error_response

logger = logging.getLogger(__name__)


class LayoutTools:
    """Provides layout computation and management tools."""

    def __init__(
        self,
        dexpi_models: Dict[str, Any],
        flowsheets: Dict[str, Any],
        layout_store: Optional[LayoutStore] = None,
    ):
        """Initialize with model stores and layout store.

        Args:
            dexpi_models: Store of DEXPI models
            flowsheets: Store of SFILES flowsheets
            layout_store: Optional layout store (created if not provided)
        """
        self.dexpi_models = dexpi_models
        self.flowsheets = flowsheets
        self.layout_store = layout_store or LayoutStore()
        self._elk_engine: Optional[ELKLayoutEngine] = None

    @property
    def elk_engine(self) -> ELKLayoutEngine:
        """Lazy initialization of ELK engine."""
        if self._elk_engine is None:
            self._elk_engine = ELKLayoutEngine()
        return self._elk_engine

    def get_tools(self) -> List[Tool]:
        """Return layout MCP tools."""
        return [
            Tool(
                name="layout_compute",
                description="Compute layout for a model using ELK. Produces orthogonal edge routing suitable for P&ID diagrams.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {
                            "type": "string",
                            "description": "ID of model to layout"
                        },
                        "model_type": {
                            "type": "string",
                            "enum": ["dexpi", "sfiles", "auto"],
                            "description": "Model type (auto-detect if not specified)",
                            "default": "auto"
                        },
                        "algorithm": {
                            "type": "string",
                            "enum": ["elk", "spring"],
                            "description": "Layout algorithm (elk recommended for P&ID)",
                            "default": "elk"
                        },
                        "direction": {
                            "type": "string",
                            "enum": ["RIGHT", "DOWN", "LEFT", "UP"],
                            "description": "Primary flow direction",
                            "default": "RIGHT"
                        },
                        "spacing": {
                            "type": "number",
                            "description": "Node spacing in mm (default 50)",
                            "default": 50
                        },
                        "store_result": {
                            "type": "boolean",
                            "description": "Store result in layout store",
                            "default": True
                        }
                    },
                    "required": ["model_id"]
                }
            ),
            Tool(
                name="layout_get",
                description="Get a stored layout by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "layout_id": {
                            "type": "string",
                            "description": "ID of layout to retrieve"
                        },
                        "include_edges": {
                            "type": "boolean",
                            "description": "Include edge routing data",
                            "default": True
                        },
                        "include_ports": {
                            "type": "boolean",
                            "description": "Include port layout data",
                            "default": True
                        }
                    },
                    "required": ["layout_id"]
                }
            ),
            Tool(
                name="layout_list",
                description="List layouts, optionally filtered by model",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {
                            "type": "string",
                            "description": "Filter by model ID"
                        },
                        "model_type": {
                            "type": "string",
                            "enum": ["dexpi", "sfiles"],
                            "description": "Filter by model type"
                        }
                    }
                }
            ),
            Tool(
                name="layout_save_to_file",
                description="Save layout to project file for persistence",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "layout_id": {
                            "type": "string",
                            "description": "ID of layout to save"
                        },
                        "project_path": {
                            "type": "string",
                            "description": "Path to project root"
                        },
                        "model_name": {
                            "type": "string",
                            "description": "Model name (without extension)"
                        },
                        "model_type": {
                            "type": "string",
                            "enum": ["pid", "pfd", "bfd"],
                            "description": "Model directory type",
                            "default": "pid"
                        }
                    },
                    "required": ["layout_id", "project_path", "model_name"]
                }
            ),
            Tool(
                name="layout_load_from_file",
                description="Load layout from project file into store",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to project root"
                        },
                        "model_name": {
                            "type": "string",
                            "description": "Model name (without extension)"
                        },
                        "model_type": {
                            "type": "string",
                            "enum": ["pid", "pfd", "bfd"],
                            "description": "Model directory type (auto-detect if not specified)"
                        },
                        "layout_id": {
                            "type": "string",
                            "description": "Optional ID for loaded layout"
                        }
                    },
                    "required": ["project_path", "model_name"]
                }
            ),
            Tool(
                name="layout_delete",
                description="Delete a layout from the store",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "layout_id": {
                            "type": "string",
                            "description": "ID of layout to delete"
                        }
                    },
                    "required": ["layout_id"]
                }
            ),
            Tool(
                name="layout_update",
                description="Update an existing layout with optimistic concurrency control. Requires etag to prevent concurrent modification conflicts.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "layout_id": {
                            "type": "string",
                            "description": "ID of layout to update"
                        },
                        "etag": {
                            "type": "string",
                            "description": "Expected etag (from layout_get). Update fails if layout was modified since."
                        },
                        "positions": {
                            "type": "object",
                            "description": "Updated node positions: {node_id: {x, y}}",
                            "additionalProperties": {
                                "type": "object",
                                "properties": {
                                    "x": {"type": "number"},
                                    "y": {"type": "number"}
                                },
                                "required": ["x", "y"]
                            }
                        },
                        "edges": {
                            "type": "object",
                            "description": "Updated edge routes: {edge_id: {sections: [...], source_port, target_port}}"
                        },
                        "port_layouts": {
                            "type": "object",
                            "description": "Updated port layouts: {port_id: {x, y, side, ...}}"
                        },
                        "rotation": {
                            "type": "object",
                            "description": "Updated node rotations: {node_id: degrees}",
                            "additionalProperties": {"type": "number"}
                        }
                    },
                    "required": ["layout_id", "etag"]
                }
            ),
            Tool(
                name="layout_validate",
                description="Validate a layout against its schema and optionally check consistency with source model.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "layout_id": {
                            "type": "string",
                            "description": "ID of layout to validate"
                        },
                        "check_model_consistency": {
                            "type": "boolean",
                            "description": "Check if layout matches current model topology",
                            "default": False
                        },
                        "recompute_diff": {
                            "type": "boolean",
                            "description": "Re-run ELK and compute diff (expensive)",
                            "default": False
                        }
                    },
                    "required": ["layout_id"]
                }
            ),
        ]

    async def handle_tool(self, name: str, arguments: dict) -> dict:
        """Route tool call to appropriate handler.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Standardized response
        """
        handlers = {
            "layout_compute": self._compute_layout,
            "layout_get": self._get_layout,
            "layout_list": self._list_layouts,
            "layout_save_to_file": self._save_to_file,
            "layout_load_from_file": self._load_from_file,
            "layout_delete": self._delete_layout,
            "layout_update": self._update_layout,
            "layout_validate": self._validate_layout,
        }

        handler = handlers.get(name)
        if not handler:
            return error_response(f"Unknown layout tool: {name}", code="UNKNOWN_TOOL")

        try:
            return await handler(arguments)
        except Exception as e:
            logger.error(f"Error in {name}: {e}", exc_info=True)
            return error_response(str(e), code="TOOL_ERROR")

    async def _compute_layout(self, args: dict) -> dict:
        """Compute layout for a model."""
        model_id = args["model_id"]
        model_type = args.get("model_type", "auto")
        algorithm = args.get("algorithm", "elk")
        store_result = args.get("store_result", True)

        # Auto-detect model type
        if model_type == "auto":
            if model_id in self.dexpi_models:
                model_type = "dexpi"
            elif model_id in self.flowsheets:
                model_type = "sfiles"
            else:
                return error_response(
                    f"Model {model_id} not found in either store",
                    code="MODEL_NOT_FOUND"
                )

        # Get graph from model
        try:
            graph = await self._get_graph(model_id, model_type)
        except Exception as e:
            return error_response(f"Failed to get graph: {e}", code="GRAPH_ERROR")

        # Check algorithm availability
        if algorithm == "elk":
            if not await self.elk_engine.is_available():
                return error_response(
                    "ELK not available. Install Node.js and run 'npm install elkjs'",
                    code="ELK_NOT_AVAILABLE"
                )

            # Build ELK options
            options = dict(PID_LAYOUT_OPTIONS)
            if "direction" in args:
                options["elk.direction"] = args["direction"]
            if "spacing" in args:
                options["elk.layered.spacing.nodeNodeBetweenLayers"] = args["spacing"]

            # Compute layout
            layout = await self.elk_engine.layout(graph, options)

        elif algorithm == "spring":
            # Fallback to spring layout
            layout = self._compute_spring_layout(graph)
        else:
            return error_response(f"Unknown algorithm: {algorithm}", code="UNKNOWN_ALGORITHM")

        # Store result if requested
        layout_id = None
        if store_result:
            model_ref = ModelReference(type=model_type, model_id=model_id)
            layout_id = self.layout_store.save(layout, model_ref=model_ref)

        # Build response
        result = {
            "algorithm": layout.algorithm,
            "node_count": len(layout.positions),
            "edge_count": len(layout.edges),
            "port_count": len(layout.port_layouts),
            "bounding_box": {
                "min_x": layout.bounding_box.min_x,
                "max_x": layout.bounding_box.max_x,
                "min_y": layout.bounding_box.min_y,
                "max_y": layout.bounding_box.max_y,
                "width": layout.bounding_box.width,
                "height": layout.bounding_box.height,
            } if layout.bounding_box else None,
            "etag": layout.etag[:16] + "...",
        }

        if layout_id:
            result["layout_id"] = layout_id
            result["stored"] = True

        return success_response(result)

    async def _get_graph(self, model_id: str, model_type: str) -> nx.DiGraph:
        """Get NetworkX graph from model.

        Args:
            model_id: Model ID
            model_type: Model type

        Returns:
            NetworkX DiGraph with node/edge data for layout
        """
        if model_type == "dexpi":
            model = self.dexpi_models[model_id]
            # Use pyDEXPI's graph loader
            from pydexpi.loaders.ml_graph_loader import MLGraphLoader
            loader = MLGraphLoader(plant_model=model)
            loader.parse_dexpi_to_graph()

            # Enhance with layout hints
            graph = loader.plant_graph.copy()
            for node_id in graph.nodes():
                node_data = graph.nodes[node_id]
                # Set default sizes based on equipment type
                dexpi_class = node_data.get("dexpi_class", "")
                width, height = self._get_default_size(dexpi_class)
                node_data["width"] = width
                node_data["height"] = height

            return graph

        else:  # sfiles
            flowsheet = self.flowsheets[model_id]
            graph = flowsheet.state.copy()

            # Enhance with layout hints
            for node_id in graph.nodes():
                node_data = graph.nodes[node_id]
                unit_type = node_data.get("unit_type", "")
                width, height = self._get_default_size(unit_type)
                node_data["width"] = width
                node_data["height"] = height

            return graph

    def _get_default_size(self, equipment_type: str) -> tuple:
        """Get default width/height for equipment type.

        Args:
            equipment_type: Equipment or unit type

        Returns:
            (width, height) tuple in mm
        """
        # Size mappings based on typical P&ID conventions
        large_equipment = {"Vessel", "Tank", "Column", "Reactor", "vessel", "tank", "column", "reactor"}
        medium_equipment = {"HeatExchanger", "Pump", "Compressor", "hex", "pump", "compressor"}

        if any(t in equipment_type for t in large_equipment):
            return (80, 60)
        elif any(t in equipment_type for t in medium_equipment):
            return (60, 40)
        else:
            return (40, 30)

    def _compute_spring_layout(self, graph: nx.DiGraph) -> LayoutMetadata:
        """Compute spring layout as fallback.

        Args:
            graph: NetworkX graph

        Returns:
            LayoutMetadata with spring positions
        """
        from ..models.layout_metadata import NodePosition

        pos = nx.spring_layout(graph, seed=42, k=2)

        # Scale to mm (assume 500mm working area)
        scale = 500
        positions = {
            node_id: NodePosition(x=x * scale + 100, y=y * scale + 100)
            for node_id, (x, y) in pos.items()
        }

        return LayoutMetadata(
            algorithm="spring",
            positions=positions,
            layout_options={"seed": 42, "k": 2, "scale": scale},
        )

    async def _get_layout(self, args: dict) -> dict:
        """Get a stored layout."""
        layout_id = args["layout_id"]
        include_edges = args.get("include_edges", True)
        include_ports = args.get("include_ports", True)

        try:
            layout = self.layout_store.get(layout_id)
        except LayoutNotFoundError:
            return error_response(f"Layout {layout_id} not found", code="NOT_FOUND")

        # Build response
        result = {
            "layout_id": layout.layout_id,
            "algorithm": layout.algorithm,
            "version": layout.version,
            "etag": layout.etag,
            "created_at": layout.created_at,
            "updated_at": layout.updated_at,
            "node_count": len(layout.positions),
            "positions": {
                node_id: {"x": pos.x, "y": pos.y}
                for node_id, pos in layout.positions.items()
            },
        }

        if layout.model_ref:
            result["model_ref"] = {
                "type": layout.model_ref.type,
                "model_id": layout.model_ref.model_id,
            }

        if include_edges and layout.edges:
            result["edge_count"] = len(layout.edges)
            result["edges"] = {
                edge_id: {
                    "section_count": len(route.sections),
                    "source_port": route.source_port,
                    "target_port": route.target_port,
                    "points": route.get_all_points(),
                }
                for edge_id, route in layout.edges.items()
            }

        if include_ports and layout.port_layouts:
            result["port_count"] = len(layout.port_layouts)
            result["ports"] = {
                port_id: {
                    "x": port.x,
                    "y": port.y,
                    "side": port.side,
                    "index": port.index,
                }
                for port_id, port in layout.port_layouts.items()
            }

        if layout.bounding_box:
            result["bounding_box"] = {
                "min_x": layout.bounding_box.min_x,
                "max_x": layout.bounding_box.max_x,
                "min_y": layout.bounding_box.min_y,
                "max_y": layout.bounding_box.max_y,
                "width": layout.bounding_box.width,
                "height": layout.bounding_box.height,
            }

        return success_response(result)

    async def _list_layouts(self, args: dict) -> dict:
        """List layouts in store."""
        model_id = args.get("model_id")
        model_type = args.get("model_type")

        if model_id and model_type:
            layout_ids = self.layout_store.list_by_model(model_type, model_id)
        else:
            layout_ids = self.layout_store.list_ids()

        # Build summary for each layout
        layouts = []
        for layout_id in layout_ids:
            try:
                layout = self.layout_store.get(layout_id, copy=False)
                layouts.append({
                    "layout_id": layout_id,
                    "algorithm": layout.algorithm,
                    "node_count": len(layout.positions),
                    "version": layout.version,
                    "model_ref": {
                        "type": layout.model_ref.type,
                        "model_id": layout.model_ref.model_id,
                    } if layout.model_ref else None,
                })
            except LayoutNotFoundError:
                continue

        return success_response({
            "count": len(layouts),
            "layouts": layouts,
        })

    async def _save_to_file(self, args: dict) -> dict:
        """Save layout to project file."""
        layout_id = args["layout_id"]
        project_path = args["project_path"]
        model_name = args["model_name"]
        model_type = args.get("model_type", "pid")

        try:
            file_path = self.layout_store.save_to_file(
                layout_id, project_path, model_name, model_type
            )
            return success_response({
                "layout_id": layout_id,
                "file_path": str(file_path),
                "model_name": model_name,
            })
        except LayoutNotFoundError:
            return error_response(f"Layout {layout_id} not found", code="NOT_FOUND")
        except Exception as e:
            return error_response(f"Failed to save layout: {e}", code="SAVE_ERROR")

    async def _load_from_file(self, args: dict) -> dict:
        """Load layout from project file."""
        project_path = args["project_path"]
        model_name = args["model_name"]
        model_type = args.get("model_type")
        layout_id = args.get("layout_id")

        try:
            loaded_id = self.layout_store.load_from_file(
                project_path, model_name, model_type, layout_id
            )
            layout = self.layout_store.get(loaded_id)

            return success_response({
                "layout_id": loaded_id,
                "algorithm": layout.algorithm,
                "node_count": len(layout.positions),
                "version": layout.version,
                "etag": layout.etag[:16] + "...",
            })
        except FileNotFoundError as e:
            return error_response(str(e), code="FILE_NOT_FOUND")
        except Exception as e:
            return error_response(f"Failed to load layout: {e}", code="LOAD_ERROR")

    async def _delete_layout(self, args: dict) -> dict:
        """Delete a layout from store."""
        layout_id = args["layout_id"]

        if self.layout_store.delete(layout_id):
            return success_response({
                "layout_id": layout_id,
                "deleted": True,
            })
        else:
            return error_response(f"Layout {layout_id} not found", code="NOT_FOUND")

    async def _update_layout(self, args: dict) -> dict:
        """Update a layout with optimistic concurrency control.

        Architecture Decision (Codex Consensus #019adb91):
            - Requires etag to detect concurrent modification
            - Returns new etag/version on success
            - Partial updates supported (only provided fields are updated)
        """
        from ..models.layout_metadata import NodePosition, EdgeRoute, EdgeSection, PortLayout

        layout_id = args["layout_id"]
        expected_etag = args["etag"]

        try:
            # Get current layout
            current = self.layout_store.get(layout_id, copy=True)
        except LayoutNotFoundError:
            return error_response(f"Layout {layout_id} not found", code="NOT_FOUND")

        # Apply partial updates
        updated = False

        # Update positions
        if "positions" in args and args["positions"]:
            for node_id, pos_data in args["positions"].items():
                current.positions[node_id] = NodePosition(x=pos_data["x"], y=pos_data["y"])
            updated = True

        # Update edges
        if "edges" in args and args["edges"]:
            for edge_id, edge_data in args["edges"].items():
                sections = []
                for section_data in edge_data.get("sections", []):
                    sections.append(EdgeSection(
                        id=section_data.get("id"),
                        startPoint=tuple(section_data["startPoint"]),
                        endPoint=tuple(section_data["endPoint"]),
                        bendPoints=[tuple(bp) for bp in section_data.get("bendPoints", [])],
                    ))
                current.edges[edge_id] = EdgeRoute(
                    sections=sections,
                    source_port=edge_data.get("source_port"),
                    target_port=edge_data.get("target_port"),
                    sourcePoint=tuple(edge_data["sourcePoint"]) if edge_data.get("sourcePoint") else None,
                    targetPoint=tuple(edge_data["targetPoint"]) if edge_data.get("targetPoint") else None,
                )
            updated = True

        # Update port layouts
        if "port_layouts" in args and args["port_layouts"]:
            for port_id, port_data in args["port_layouts"].items():
                current.port_layouts[port_id] = PortLayout(
                    id=port_id,
                    x=port_data["x"],
                    y=port_data["y"],
                    side=port_data.get("side", "EAST"),
                    index=port_data.get("index", 0),
                    width=port_data.get("width", 8.0),
                    height=port_data.get("height", 8.0),
                )
            updated = True

        # Update rotations
        if "rotation" in args and args["rotation"]:
            for node_id, angle in args["rotation"].items():
                current.rotation[node_id] = float(angle)
            updated = True

        if not updated:
            return error_response(
                "No updates provided. Include at least one of: positions, edges, port_layouts, rotation",
                code="NO_UPDATES"
            )

        # Perform update with optimistic lock
        try:
            new_etag = self.layout_store.update(layout_id, current, expected_etag=expected_etag)
            updated_layout = self.layout_store.get(layout_id, copy=False)

            return success_response({
                "layout_id": layout_id,
                "version": updated_layout.version,
                "etag": new_etag,
                "updated": True,
                "node_count": len(updated_layout.positions),
                "edge_count": len(updated_layout.edges),
            })

        except OptimisticLockError as e:
            return error_response(
                f"Layout was modified by another process. Expected etag {expected_etag[:16]}..., "
                f"current is {e.actual_etag[:16]}... Refresh and retry.",
                code="ETAG_MISMATCH",
                details={
                    "layout_id": layout_id,
                    "expected_etag": expected_etag,
                    "actual_etag": e.actual_etag,
                }
            )

    async def _validate_layout(self, args: dict) -> dict:
        """Validate a layout against schema and optionally check model consistency.

        Architecture Decision (Codex Consensus #019adb91):
            - Basic validation: schema compliance, required fields
            - Model consistency: check if layout nodes match model topology
            - Recompute diff: re-run ELK and report position differences
        """
        layout_id = args["layout_id"]
        check_model_consistency = args.get("check_model_consistency", False)
        recompute_diff = args.get("recompute_diff", False)

        try:
            layout = self.layout_store.get(layout_id, copy=False)
        except LayoutNotFoundError:
            return error_response(f"Layout {layout_id} not found", code="NOT_FOUND")

        issues = []
        warnings = []

        # Basic schema validation
        if not layout.positions:
            issues.append("Layout has no positions")
        if not layout.algorithm:
            issues.append("Layout missing algorithm field")

        # Check etag integrity
        computed_etag = layout.compute_etag()
        if layout.etag != computed_etag:
            warnings.append(f"Etag mismatch: stored {layout.etag[:16]}... vs computed {computed_etag[:16]}...")

        # Check bounding box consistency
        if layout.bounding_box and layout.positions:
            from ..models.layout_metadata import BoundingBox
            computed_bbox = BoundingBox.from_positions(layout.positions)
            if (abs(layout.bounding_box.min_x - computed_bbox.min_x) > 0.001 or
                abs(layout.bounding_box.max_x - computed_bbox.max_x) > 0.001 or
                abs(layout.bounding_box.min_y - computed_bbox.min_y) > 0.001 or
                abs(layout.bounding_box.max_y - computed_bbox.max_y) > 0.001):
                warnings.append("Bounding box does not match computed from positions")

        # Model consistency check
        model_issues = []
        if check_model_consistency and layout.model_ref:
            model_type = layout.model_ref.type
            model_id = layout.model_ref.model_id

            # Get model nodes
            model_nodes = set()
            try:
                if model_type == "dexpi" and model_id in self.dexpi_models:
                    model = self.dexpi_models[model_id]
                    from pydexpi.loaders.ml_graph_loader import MLGraphLoader
                    loader = MLGraphLoader(plant_model=model)
                    loader.parse_dexpi_to_graph()
                    model_nodes = set(loader.plant_graph.nodes())
                elif model_type == "sfiles" and model_id in self.flowsheets:
                    flowsheet = self.flowsheets[model_id]
                    model_nodes = set(flowsheet.state.nodes())
                else:
                    model_issues.append(f"Model {model_id} not found in {model_type} store")
            except Exception as e:
                model_issues.append(f"Failed to load model graph: {e}")

            if model_nodes:
                layout_nodes = set(layout.positions.keys())
                missing_in_layout = model_nodes - layout_nodes
                extra_in_layout = layout_nodes - model_nodes

                if missing_in_layout:
                    model_issues.append(f"Nodes in model but not layout: {list(missing_in_layout)[:5]}")
                if extra_in_layout:
                    model_issues.append(f"Nodes in layout but not model: {list(extra_in_layout)[:5]}")

        # Recompute diff (expensive)
        recompute_results = None
        if recompute_diff and layout.model_ref:
            try:
                model_type = layout.model_ref.type
                model_id = layout.model_ref.model_id

                # Get graph from model
                graph = await self._get_graph(model_id, model_type)

                # Recompute layout
                if await self.elk_engine.is_available():
                    new_layout = await self.elk_engine.layout(graph, layout.layout_options)

                    # Compare positions
                    position_diffs = []
                    for node_id, new_pos in new_layout.positions.items():
                        if node_id in layout.positions:
                            old_pos = layout.positions[node_id]
                            dx = abs(new_pos.x - old_pos.x)
                            dy = abs(new_pos.y - old_pos.y)
                            if dx > 1.0 or dy > 1.0:  # 1mm threshold
                                position_diffs.append({
                                    "node_id": node_id,
                                    "old": {"x": old_pos.x, "y": old_pos.y},
                                    "new": {"x": new_pos.x, "y": new_pos.y},
                                    "delta": {"x": dx, "y": dy}
                                })

                    recompute_results = {
                        "positions_changed": len(position_diffs),
                        "total_nodes": len(new_layout.positions),
                        "sample_diffs": position_diffs[:5] if position_diffs else []
                    }
                else:
                    warnings.append("ELK not available for recompute diff")
            except Exception as e:
                warnings.append(f"Failed to recompute layout: {e}")

        # Build result
        is_valid = len(issues) == 0

        result = {
            "layout_id": layout_id,
            "valid": is_valid,
            "node_count": len(layout.positions),
            "edge_count": len(layout.edges),
            "version": layout.version,
        }

        if issues:
            result["issues"] = issues
        if warnings:
            result["warnings"] = warnings
        if model_issues:
            result["model_issues"] = model_issues
        if recompute_results:
            result["recompute_diff"] = recompute_results

        return success_response(result)
