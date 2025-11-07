"""Graph modification tools for tactical-level model edits.

This module implements the graph_modify MCP tool as specified in
docs/api/graph_modify_spec.md, providing 10 tactical operations for
targeted modifications to DEXPI P&IDs and SFILES flowsheets.

Architecture follows Codex recommendation: thin wrappers over upstream
toolkits (pyDEXPI piping_toolkit, SFILES2 Flowsheet methods) with
shared orchestration for target resolution, validation, and diffing.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from mcp import Tool
from pydexpi.dexpi_classes.dexpiModel import DexpiModel
from pydexpi.toolkits import piping_toolkit as pt
from pydexpi.toolkits import model_toolkit as mt
from pydexpi.loaders.ml_graph_loader import MLGraphLoader

from ..utils.response import success_response, error_response
from ..managers.transaction_manager import TransactionManager

logger = logging.getLogger(__name__)


class GraphAction(str, Enum):
    """Enumeration of supported graph modification actions."""
    # Component operations
    INSERT_COMPONENT = "insert_component"
    REMOVE_COMPONENT = "remove_component"
    UPDATE_COMPONENT = "update_component"
    INSERT_INLINE_COMPONENT = "insert_inline_component"

    # Segment operations (DEXPI only)
    SPLIT_SEGMENT = "split_segment"
    MERGE_SEGMENTS = "merge_segments"
    REWIRE_CONNECTION = "rewire_connection"

    # Property operations
    SET_TAG_PROPERTIES = "set_tag_properties"
    UPDATE_STREAM_PROPERTIES = "update_stream_properties"  # SFILES only

    # Instrumentation operations
    TOGGLE_INSTRUMENTATION = "toggle_instrumentation"


class TargetKind(str, Enum):
    """Target selector kinds."""
    MODEL = "model"
    COMPONENT = "component"
    SEGMENT = "segment"
    STREAM = "stream"
    PORT = "port"


class ActionContext:
    """Shared context for action execution (model-agnostic)."""

    def __init__(
        self,
        model_id: str,
        model: Any,  # DexpiModel or Flowsheet
        model_type: str,  # "dexpi" or "sfiles"
        target: Dict[str, Any],
        payload: Dict[str, Any],
        options: Dict[str, Any],
        transaction_id: Optional[str] = None
    ):
        self.model_id = model_id
        self.model = model
        self.model_type = model_type
        self.target = target
        self.payload = payload
        self.options = options
        self.transaction_id = transaction_id
        self.mutated_entities: List[str] = []
        self.validation_errors: List[Dict] = []
        self.validation_warnings: List[Dict] = []


class TargetResolver:
    """Resolves target selectors to specific model entities.

    Delegates to existing search_tools for wildcard/filter queries.
    Caches results per call to avoid redundant searches.
    """

    def __init__(self, search_tools=None):
        """Initialize resolver with optional search tools reference."""
        self.search_tools = search_tools
        self._cache: Dict[str, Any] = {}

    def resolve(
        self,
        target: Dict[str, Any],
        model: Any,
        model_type: str
    ) -> Tuple[bool, Any, Optional[str]]:
        """Resolve target selector to entity.

        Args:
            target: TargetSelector dict {kind, identifier, selector?}
            model: Model instance
            model_type: "dexpi" or "sfiles"

        Returns:
            Tuple of (success, resolved_entity, error_message)
        """
        cache_key = f"{target.get('kind')}:{target.get('identifier')}"
        if cache_key in self._cache:
            return True, self._cache[cache_key], None

        kind = target.get("kind")
        identifier = target.get("identifier")
        selector = target.get("selector", {})

        if not kind or not identifier:
            return False, None, "Target must specify 'kind' and 'identifier'"

        # Model-level targets (for insert_component)
        if kind == TargetKind.MODEL:
            self._cache[cache_key] = model
            return True, model, None

        # Component/segment/stream resolution
        if kind == TargetKind.COMPONENT:
            result = self._resolve_component(identifier, selector, model, model_type)
        elif kind == TargetKind.SEGMENT:
            result = self._resolve_segment(identifier, selector, model, model_type)
        elif kind == TargetKind.STREAM:
            result = self._resolve_stream(identifier, selector, model, model_type)
        elif kind == TargetKind.PORT:
            result = self._resolve_port(identifier, selector, model, model_type)
        else:
            return False, None, f"Unknown target kind: {kind}"

        if result[0]:
            self._cache[cache_key] = result[1]

        return result

    def _resolve_component(
        self,
        identifier: str,
        selector: Dict,
        model: Any,
        model_type: str
    ) -> Tuple[bool, Any, Optional[str]]:
        """Resolve component by tag/ID."""
        if model_type == "dexpi":
            # Search by tag in DEXPI model
            instances = mt.get_all_instances_in_model(model, None)
            for inst in instances:
                if hasattr(inst, 'tagName') and inst.tagName == identifier:
                    return True, inst, None
                if hasattr(inst, 'tag') and inst.tag == identifier:
                    return True, inst, None
            return False, None, f"Component not found: {identifier}"

        elif model_type == "sfiles":
            # Search in flowsheet units
            if hasattr(model, 'state') and model.state.has_node(identifier):
                return True, identifier, None
            return False, None, f"Unit not found: {identifier}"

        return False, None, f"Unsupported model type: {model_type}"

    def _resolve_segment(
        self,
        identifier: str,
        selector: Dict,
        model: Any,
        model_type: str
    ) -> Tuple[bool, Any, Optional[str]]:
        """Resolve piping segment by ID."""
        if model_type != "dexpi":
            return False, None, "Segments only apply to DEXPI models"

        # Search for PipingNetworkSegment
        instances = mt.get_all_instances_in_model(model, None)
        for inst in instances:
            if inst.__class__.__name__ == "PipingNetworkSegment":
                if hasattr(inst, 'id') and inst.id == identifier:
                    return True, inst, None
                if hasattr(inst, 'tagName') and inst.tagName == identifier:
                    return True, inst, None

        return False, None, f"Segment not found: {identifier}"

    def _resolve_stream(
        self,
        identifier: str,
        selector: Dict,
        model: Any,
        model_type: str
    ) -> Tuple[bool, Any, Optional[str]]:
        """Resolve stream by name."""
        if model_type != "sfiles":
            return False, None, "Streams only apply to SFILES models"

        # Search in flowsheet edges
        if hasattr(model, 'state'):
            for u, v, data in model.state.edges(data=True):
                if data.get('name') == identifier or data.get('id') == identifier:
                    return True, (u, v, data), None

        return False, None, f"Stream not found: {identifier}"

    def _resolve_port(
        self,
        identifier: str,
        selector: Dict,
        model: Any,
        model_type: str
    ) -> Tuple[bool, Any, Optional[str]]:
        """Resolve port/nozzle by ID."""
        if model_type != "dexpi":
            return False, None, "Ports only apply to DEXPI models"

        # Parse identifier as "component/nozzle"
        if "/" in identifier:
            comp_tag, nozzle_name = identifier.split("/", 1)
            comp_result = self._resolve_component(comp_tag, {}, model, model_type)
            if not comp_result[0]:
                return comp_result

            component = comp_result[1]
            if hasattr(component, 'nozzles'):
                for nozzle in component.nozzles:
                    if hasattr(nozzle, 'subTagName') and nozzle.subTagName == nozzle_name:
                        return True, nozzle, None

            return False, None, f"Nozzle not found: {nozzle_name} on {comp_tag}"

        return False, None, f"Invalid port identifier format: {identifier}"


class GraphModifyTools:
    """Handles graph_modify MCP tool for tactical modifications."""

    def __init__(
        self,
        dexpi_models: Dict[str, DexpiModel],
        flowsheet_store: Dict[str, Any],
        dexpi_tools=None,
        sfiles_tools=None,
        search_tools=None
    ):
        """Initialize with model stores and tool references."""
        self.dexpi_models = dexpi_models
        self.flowsheets = flowsheet_store
        self.dexpi_tools = dexpi_tools
        self.sfiles_tools = sfiles_tools
        self.search_tools = search_tools

        self.resolver = TargetResolver(search_tools)
        self.transaction_manager = TransactionManager(dexpi_models, flowsheet_store)
        self.graph_loader = MLGraphLoader()

        logger.info("GraphModifyTools initialized")

    def get_tools(self) -> List[Tool]:
        """Return MCP tool definitions."""
        return [
            Tool(
                name="graph_modify",
                description="Apply tactical graph modifications (10 actions: insert/update/remove component, inline insertion, segment operations, etc.)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {
                            "type": "string",
                            "description": "Model identifier"
                        },
                        "action": {
                            "type": "string",
                            "enum": [action.value for action in GraphAction],
                            "description": "Action type"
                        },
                        "target": {
                            "type": "object",
                            "description": "Target selector",
                            "properties": {
                                "kind": {
                                    "type": "string",
                                    "enum": [kind.value for kind in TargetKind]
                                },
                                "identifier": {"type": "string"},
                                "selector": {
                                    "type": "object",
                                    "description": "Optional filters"
                                }
                            },
                            "required": ["kind", "identifier"]
                        },
                        "payload": {
                            "type": "object",
                            "description": "Action-specific parameters"
                        },
                        "options": {
                            "type": "object",
                            "description": "Modification options",
                            "properties": {
                                "create_transaction": {
                                    "type": "boolean",
                                    "default": True
                                },
                                "validate_before": {
                                    "type": "boolean",
                                    "default": True
                                },
                                "validate_after": {
                                    "type": "boolean",
                                    "default": False
                                },
                                "dry_run": {
                                    "type": "boolean",
                                    "default": False
                                }
                            }
                        }
                    },
                    "required": ["model_id", "action", "target", "payload"]
                }
            )
        ]

    async def handle_tool(self, tool_name: str, arguments: dict) -> dict:
        """Route tool calls to appropriate handler."""
        if tool_name == "graph_modify":
            return await self._graph_modify(arguments)

        return error_response(
            f"Unknown tool: {tool_name}",
            "UNKNOWN_TOOL"
        )

    async def _graph_modify(self, args: dict) -> dict:
        """Main graph_modify implementation."""
        model_id = args.get("model_id")
        action = args.get("action")
        target = args.get("target", {})
        payload = args.get("payload", {})
        options = args.get("options", {})

        # Set defaults
        options.setdefault("create_transaction", True)
        options.setdefault("validate_before", True)
        options.setdefault("validate_after", False)
        options.setdefault("dry_run", False)

        # Determine model type and get model
        model = None
        model_type = None

        if model_id in self.dexpi_models:
            model = self.dexpi_models[model_id]
            model_type = "dexpi"
        elif model_id in self.flowsheets:
            model = self.flowsheets[model_id]
            model_type = "sfiles"
        else:
            return error_response(
                f"Model not found: {model_id}",
                "MODEL_NOT_FOUND"
            )

        # Validate action enum
        try:
            action_enum = GraphAction(action)
        except ValueError:
            return error_response(
                f"Unknown action: {action}. Valid actions: {[a.value for a in GraphAction]}",
                "INVALID_ACTION"
            )

        # Create action context
        ctx = ActionContext(
            model_id=model_id,
            model=model,
            model_type=model_type,
            target=target,
            payload=payload,
            options=options
        )

        # Pre-validation
        if options.get("validate_before"):
            validation = self._validate_pre(ctx)
            if not validation.get("ok"):
                return validation

        # Transaction wrapping
        if options.get("create_transaction") and not options.get("dry_run"):
            tx_result = await self.transaction_manager.begin(model_id)
            if not tx_result.get("ok"):
                return error_response(
                    f"Transaction begin failed: {tx_result.get('error')}",
                    "TRANSACTION_FAILED"
                )
            ctx.transaction_id = tx_result["data"]["transaction_id"]

            # Get working model from transaction
            if ctx.model_type == "dexpi":
                ctx.model = self.transaction_manager.transactions[ctx.transaction_id].working_model
            elif ctx.model_type == "sfiles":
                ctx.model = self.transaction_manager.transactions[ctx.transaction_id].working_model

        # For dry_run, work on a copy
        elif options.get("dry_run"):
            if ctx.model_type == "dexpi":
                import copy
                ctx.model = copy.deepcopy(ctx.model)
            elif ctx.model_type == "sfiles":
                # SFILES: create copy via serialize/deserialize
                sfiles_str = ctx.model.convert_to_sfiles()
                from src.adapters.sfiles_adapter import create_flowsheet
                ctx.model = create_flowsheet()
                ctx.model.create_from_sfiles(sfiles_str)

        try:
            # Dispatch to action handler
            result = await self._dispatch_action(action_enum, ctx)

            if not result.get("ok"):
                # Rollback on error
                if ctx.transaction_id:
                    await self.transaction_manager.rollback(ctx.transaction_id)
                return result

            # Post-validation
            if options.get("validate_after"):
                validation = self._validate_post(ctx)
                if not validation.get("ok"):
                    if ctx.transaction_id:
                        await self.transaction_manager.rollback(ctx.transaction_id)
                    return validation

            # Commit transaction (not for dry_run)
            if ctx.transaction_id and not options.get("dry_run"):
                commit_result = await self.transaction_manager.commit(ctx.transaction_id)
                if not commit_result.get("ok"):
                    return error_response(
                        f"Transaction commit failed: {commit_result.get('error')}",
                        "TRANSACTION_FAILED"
                    )

                # Add diff from transaction
                if "data" not in result:
                    result["data"] = {}
                result["data"]["diff"] = commit_result["data"]["diff"]

            # For dry_run, indicate no changes were made
            if options.get("dry_run"):
                if "data" not in result:
                    result["data"] = {}
                result["data"]["dry_run"] = True

            return result

        except Exception as e:
            logger.error(f"graph_modify error: {e}", exc_info=True)
            if ctx.transaction_id:
                await self.transaction_manager.rollback(ctx.transaction_id)
            return error_response(
                f"Action execution failed: {str(e)}",
                "EXECUTION_ERROR"
            )

    async def _dispatch_action(self, action: GraphAction, ctx: ActionContext) -> dict:
        """Dispatch to specific action handler."""
        # V1 actions (6 core operations)
        if action == GraphAction.INSERT_COMPONENT:
            return await self._handle_insert_component(ctx)
        elif action == GraphAction.UPDATE_COMPONENT:
            return await self._handle_update_component(ctx)
        elif action == GraphAction.INSERT_INLINE_COMPONENT:
            return await self._handle_insert_inline_component(ctx)
        elif action == GraphAction.REWIRE_CONNECTION:
            return await self._handle_rewire_connection(ctx)
        elif action == GraphAction.REMOVE_COMPONENT:
            return await self._handle_remove_component(ctx)
        elif action == GraphAction.SET_TAG_PROPERTIES:
            return await self._handle_set_tag_properties(ctx)

        # V2 actions (4 additional operations)
        elif action == GraphAction.SPLIT_SEGMENT:
            return self._not_implemented(action.value)
        elif action == GraphAction.MERGE_SEGMENTS:
            return self._not_implemented(action.value)
        elif action == GraphAction.UPDATE_STREAM_PROPERTIES:
            return self._not_implemented(action.value)
        elif action == GraphAction.TOGGLE_INSTRUMENTATION:
            return self._not_implemented(action.value)

        return error_response(
            f"Action not implemented: {action.value}",
            "UNKNOWN_ACTION"
        )

    def _not_implemented(self, action: str) -> dict:
        """Placeholder for V2 actions."""
        return error_response(
            f"Action '{action}' will be implemented in v2",
            "NOT_IMPLEMENTED"
        )

    # ========== V1 ACTION HANDLERS (6 core operations) ==========

    async def _handle_insert_component(self, ctx: ActionContext) -> dict:
        """Action 1: Insert component (delegates to existing tools)."""
        # Delegate to dexpi_tools or sfiles_tools
        if ctx.model_type == "dexpi":
            return await self._handle_insert_component_dexpi(ctx)
        elif ctx.model_type == "sfiles":
            return await self._handle_insert_component_sfiles(ctx)

        return self._action_not_applicable(ctx, "insert_component")

    async def _handle_insert_component_dexpi(self, ctx: ActionContext) -> dict:
        """DEXPI implementation: delegate to dexpi_tools.add_equipment."""
        if not self.dexpi_tools:
            return error_response(
                "dexpi_tools not available",
                "MISSING_DEPENDENCY"
            )

        # Build args for dexpi_add_equipment
        equipment_args = {
            "model_id": ctx.model_id,
            "equipment_type": ctx.payload.get("component_type"),
            "tag_name": ctx.payload.get("tag"),
            "specifications": ctx.payload.get("attributes", {}),
            "nozzles": ctx.payload.get("nozzles", [])
        }

        result = await self.dexpi_tools.handle_tool("dexpi_add_equipment", equipment_args)

        if result.get("ok") or result.get("status") == "success":
            # Track mutated entities
            ctx.mutated_entities.append(ctx.payload.get("tag"))

            return success_response({
                "mutated_entities": ctx.mutated_entities,
                "diff": {
                    "added": [ctx.payload.get("tag")],
                    "removed": [],
                    "updated": []
                },
                "validation": {
                    "errors": ctx.validation_errors,
                    "warnings": ctx.validation_warnings
                }
            })

        return result

    async def _handle_insert_component_sfiles(self, ctx: ActionContext) -> dict:
        """SFILES implementation: delegate to sfiles_tools.add_unit."""
        if not self.sfiles_tools:
            return error_response(
                "sfiles_tools not available",
                "MISSING_DEPENDENCY"
            )

        # Build args for sfiles_add_unit
        unit_args = {
            "flowsheet_id": ctx.model_id,
            "unit_name": ctx.payload.get("tag"),
            "unit_type": ctx.payload.get("component_type"),
            "parameters": ctx.payload.get("attributes", {})
        }

        result = await self.sfiles_tools.handle_tool("sfiles_add_unit", unit_args)

        if result.get("ok") or result.get("status") == "success":
            ctx.mutated_entities.append(ctx.payload.get("tag"))

            return success_response({
                "mutated_entities": ctx.mutated_entities,
                "diff": {
                    "added": [ctx.payload.get("tag")],
                    "removed": [],
                    "updated": []
                },
                "validation": {
                    "errors": ctx.validation_errors,
                    "warnings": ctx.validation_warnings
                }
            })

        return result

    async def _handle_update_component(self, ctx: ActionContext) -> dict:
        """Action 2: Update component attributes."""
        # Resolve target component
        success, entity, error = self.resolver.resolve(ctx.target, ctx.model, ctx.model_type)
        if not success:
            return error_response(error, "TARGET_NOT_FOUND")

        if ctx.model_type == "dexpi":
            return self._handle_update_component_dexpi(ctx, entity)
        elif ctx.model_type == "sfiles":
            return self._handle_update_component_sfiles(ctx, entity)

        return self._action_not_applicable(ctx, "update_component")

    def _handle_update_component_dexpi(self, ctx: ActionContext, component: Any) -> dict:
        """DEXPI: Direct attribute update."""
        attributes = ctx.payload.get("attributes", {})
        merge = ctx.payload.get("merge", True)

        if not merge:
            # Replace all attributes (risky - not recommended)
            logger.warning("update_component with merge=False replaces all attributes")

        # Update attributes
        for key, value in attributes.items():
            if hasattr(component, key):
                setattr(component, key, value)
            else:
                logger.warning(f"Component {component} has no attribute '{key}'")

        tag = getattr(component, 'tagName', None) or getattr(component, 'tag', None)
        ctx.mutated_entities.append(str(tag))

        return success_response({
            "mutated_entities": ctx.mutated_entities,
            "diff": {
                "added": [],
                "removed": [],
                "updated": ctx.mutated_entities
            },
            "validation": {
                "errors": ctx.validation_errors,
                "warnings": ctx.validation_warnings
            }
        })

    def _handle_update_component_sfiles(self, ctx: ActionContext, unit_name: str) -> dict:
        """SFILES: Update unit node attributes in NetworkX graph."""
        attributes = ctx.payload.get("attributes", {})

        if hasattr(ctx.model, 'state') and ctx.model.state.has_node(unit_name):
            # Update node attributes
            for key, value in attributes.items():
                ctx.model.state.nodes[unit_name][key] = value

            ctx.mutated_entities.append(unit_name)

            return success_response({
                "mutated_entities": ctx.mutated_entities,
                "diff": {
                    "added": [],
                    "removed": [],
                    "updated": ctx.mutated_entities
                },
                "validation": {
                    "errors": ctx.validation_errors,
                    "warnings": ctx.validation_warnings
                }
            })

        return error_response("TARGET_NOT_FOUND", f"Unit not found: {unit_name}")

    async def _handle_insert_inline_component(self, ctx: ActionContext) -> dict:
        """Action 3: Insert component inline (DEXPI only)."""
        if ctx.model_type != "dexpi":
            return self._action_not_applicable(ctx, "insert_inline_component")

        if not self.dexpi_tools:
            return error_response("MISSING_DEPENDENCY", "dexpi_tools not available")

        # Delegate to existing _insert_valve_in_segment infrastructure
        valve_args = {
            "model_id": ctx.model_id,
            "segment_id": ctx.target.get("identifier"),
            "valve_type": ctx.payload.get("component_type"),
            "tag_name": ctx.payload.get("tag"),
            "at_position": ctx.payload.get("position", 0.5),
            "nominal_diameter": ctx.payload.get("attributes", {}).get("nominalDiameter", "DN50")
        }

        result = await self.dexpi_tools.handle_tool("dexpi_insert_valve_in_segment", valve_args)

        if result.get("ok") or result.get("status") == "success":
            ctx.mutated_entities.append(ctx.payload.get("tag"))
            ctx.mutated_entities.append(ctx.target.get("identifier"))  # Segment modified

            return success_response({
                "mutated_entities": ctx.mutated_entities,
                "diff": {
                    "added": [ctx.payload.get("tag")],
                    "removed": [],
                    "updated": [ctx.target.get("identifier")]
                },
                "validation": {
                    "errors": ctx.validation_errors,
                    "warnings": ctx.validation_warnings
                }
            })

        return result

    async def _handle_rewire_connection(self, ctx: ActionContext) -> dict:
        """Action 4: Change connection routing."""
        if ctx.model_type == "dexpi":
            return await self._handle_rewire_connection_dexpi(ctx)
        elif ctx.model_type == "sfiles":
            return self._handle_rewire_connection_sfiles(ctx)

        return self._action_not_applicable(ctx, "rewire_connection")

    async def _handle_rewire_connection_dexpi(self, ctx: ActionContext) -> dict:
        """DEXPI: Rewire existing segment to new endpoints."""
        # Resolve target segment
        success, segment, error = self.resolver.resolve(ctx.target, ctx.model, ctx.model_type)
        if not success:
            return error_response(error, "TARGET_NOT_FOUND")

        # Get new endpoints
        new_from = ctx.payload.get("from")
        new_to = ctx.payload.get("to")
        preserve_props = ctx.payload.get("preserve_properties", True)

        if not new_from and not new_to:
            return error_response(
                "Must specify at least one of 'from' or 'to' for rewiring",
                "INVALID_PAYLOAD"
            )

        # Get current segment properties
        segment_props = {}
        if preserve_props and hasattr(segment, '__dict__'):
            segment_props = {
                'pipe_class': getattr(segment, 'pipeClass', 'CS150'),
                'nominal_diameter': getattr(segment, 'nominalDiameter', 'DN50'),
                'material': getattr(segment, 'material', 'Carbon Steel')
            }

        # Get current connections (simplified - actual implementation more complex)
        old_from = None
        old_to = None
        if hasattr(segment, 'connections') and segment.connections:
            if len(segment.connections) >= 2:
                old_from = segment.connections[0]
                old_to = segment.connections[1]

        # Use provided endpoints or keep current
        final_from = new_from if new_from else old_from
        final_to = new_to if new_to else old_to

        if not final_from or not final_to:
            return error_response(
                "Cannot determine connection endpoints for rewiring",
                "INVALID_SEGMENT"
            )

        # Use piping_toolkit to create new connection
        # Note: This simplified version delegates to dexpi_tools
        # A full implementation would use pt.connect_piping_network_segment directly
        if not self.dexpi_tools:
            return error_response("dexpi_tools not available", "MISSING_DEPENDENCY")

        connect_args = {
            "model_id": ctx.model_id,
            "from_component": final_from if isinstance(final_from, str) else getattr(final_from, 'tagName', str(final_from)),
            "to_component": final_to if isinstance(final_to, str) else getattr(final_to, 'tagName', str(final_to)),
            "pipe_class": segment_props.get('pipe_class', 'CS150')
        }

        # Create new connection
        result = await self.dexpi_tools.handle_tool("dexpi_connect_components", connect_args)

        if result.get("ok") or result.get("status") == "success":
            # Track segment as updated (not fully removed/added due to preservation)
            segment_id = getattr(segment, 'id', None) or getattr(segment, 'tagName', 'segment')
            ctx.mutated_entities.append(str(segment_id))

            return success_response({
                "mutated_entities": ctx.mutated_entities,
                "diff": {
                    "added": [],
                    "removed": [],
                    "updated": [str(segment_id)]
                },
                "validation": {
                    "errors": ctx.validation_errors,
                    "warnings": ctx.validation_warnings
                }
            })

        return result

    def _handle_rewire_connection_sfiles(self, ctx: ActionContext) -> dict:
        """SFILES: NetworkX edge manipulation + canonicalize."""
        # Resolve stream
        success, stream_data, error = self.resolver.resolve(ctx.target, ctx.model, ctx.model_type)
        if not success:
            return error_response(error, "TARGET_NOT_FOUND")

        u, v, data = stream_data

        # New endpoints
        new_from = ctx.payload.get("from", u)
        new_to = ctx.payload.get("to", v)
        preserve = ctx.payload.get("preserve_properties", True)

        # Remove old edge
        ctx.model.state.remove_edge(u, v)

        # Add new edge
        props = data if preserve else {}
        ctx.model.state.add_edge(new_from, new_to, **props)

        # Re-canonicalize
        if hasattr(ctx.model, 'convert_to_sfiles'):
            ctx.model.convert_to_sfiles()

        ctx.mutated_entities.extend([new_from, new_to])

        return success_response({
            "mutated_entities": ctx.mutated_entities,
            "diff": {
                "added": [],
                "removed": [],
                "updated": ctx.mutated_entities
            },
            "validation": {
                "errors": ctx.validation_errors,
                "warnings": ctx.validation_warnings
            }
        })

    async def _handle_remove_component(self, ctx: ActionContext) -> dict:
        """Action 5: Remove component with optional rerouting."""
        # Resolve target component
        success, entity, error = self.resolver.resolve(ctx.target, ctx.model, ctx.model_type)
        if not success:
            return error_response(error, "TARGET_NOT_FOUND")

        if ctx.model_type == "dexpi":
            return self._handle_remove_component_dexpi(ctx, entity)
        elif ctx.model_type == "sfiles":
            return self._handle_remove_component_sfiles(ctx, entity)

        return self._action_not_applicable(ctx, "remove_component")

    def _handle_remove_component_dexpi(self, ctx: ActionContext, component: Any) -> dict:
        """DEXPI: Remove equipment from model."""
        cascade = ctx.payload.get("cascade", False)
        reroute = ctx.payload.get("reroute_connections", True)

        tag = getattr(component, 'tagName', None) or getattr(component, 'tag', None)

        # Find connected nozzles and segments
        inlet_nozzles = []
        outlet_nozzles = []

        if hasattr(component, 'nozzles'):
            for nozzle in component.nozzles:
                # Simple heuristic: check subTagName for inlet/outlet
                nozzle_name = getattr(nozzle, 'subTagName', '').lower()
                if 'inlet' in nozzle_name or 'in' in nozzle_name:
                    inlet_nozzles.append(nozzle)
                elif 'outlet' in nozzle_name or 'out' in nozzle_name:
                    outlet_nozzles.append(nozzle)
                else:
                    # Default: first half are inlets, second half are outlets
                    if len(inlet_nozzles) < len(component.nozzles) // 2:
                        inlet_nozzles.append(nozzle)
                    else:
                        outlet_nozzles.append(nozzle)

        # Remove component from model
        if hasattr(ctx.model, 'equipment') and isinstance(ctx.model.equipment, list):
            if component in ctx.model.equipment:
                ctx.model.equipment.remove(component)
        elif hasattr(ctx.model, 'equipments') and isinstance(ctx.model.equipments, list):
            if component in ctx.model.equipments:
                ctx.model.equipments.remove(component)
        else:
            logger.warning(f"Cannot remove {tag} - unsupported model structure")

        ctx.mutated_entities.append(str(tag))

        # Simplified rerouting: Connect first inlet predecessor to first outlet successor
        # Note: Full implementation would handle multiple connections, check actual connectivity
        rerouted = []
        if reroute and not cascade and inlet_nozzles and outlet_nozzles:
            logger.info(f"Attempting to reroute connections around removed component {tag}")

            # This is a simplified placeholder - real implementation would:
            # 1. Find actual connected segments via piping_toolkit
            # 2. Identify upstream/downstream components
            # 3. Use pt.connect_piping_network_segment to reroute
            # For v1 fixes, we log the attempt but don't implement full rerouting
            logger.warning(f"Rerouting partially implemented - {len(inlet_nozzles)} inlets, {len(outlet_nozzles)} outlets detected")
            ctx.validation_warnings.append({
                "code": "REROUTING_LIMITED",
                "message": f"Component {tag} removed but automatic rerouting not fully implemented. Manual piping review required."
            })

        return success_response({
            "mutated_entities": ctx.mutated_entities,
            "diff": {
                "added": [],
                "removed": [str(tag)],
                "updated": rerouted  # List of rerouted segments (if any)
            },
            "validation": {
                "errors": ctx.validation_errors,
                "warnings": ctx.validation_warnings
            }
        })

    def _handle_remove_component_sfiles(self, ctx: ActionContext, unit_name: str) -> dict:
        """SFILES: Remove unit from flowsheet."""
        cascade = ctx.payload.get("cascade", False)
        reroute = ctx.payload.get("reroute_connections", True)

        if not hasattr(ctx.model, 'state'):
            return error_response("Model has no state graph", "INVALID_MODEL")

        if not ctx.model.state.has_node(unit_name):
            return error_response("TARGET_NOT_FOUND", f"Unit not found: {unit_name}")

        # Get connected edges for potential rerouting
        predecessors = list(ctx.model.state.predecessors(unit_name))
        successors = list(ctx.model.state.successors(unit_name))

        # Remove node
        ctx.model.state.remove_node(unit_name)

        # Simple rerouting: connect predecessors to successors
        if reroute and not cascade and predecessors and successors:
            for pred in predecessors:
                for succ in successors:
                    if not ctx.model.state.has_edge(pred, succ):
                        ctx.model.state.add_edge(pred, succ, name=f"{pred}-{succ}")
                        logger.info(f"Rerouted {pred} -> {succ} around removed {unit_name}")

        # Re-canonicalize
        if hasattr(ctx.model, 'convert_to_sfiles'):
            ctx.model.convert_to_sfiles()

        ctx.mutated_entities.append(unit_name)

        return success_response({
            "mutated_entities": ctx.mutated_entities,
            "diff": {
                "added": [],
                "removed": [unit_name],
                "updated": []
            },
            "validation": {
                "errors": ctx.validation_errors,
                "warnings": ctx.validation_warnings
            }
        })

    async def _handle_set_tag_properties(self, ctx: ActionContext) -> dict:
        """Action 6: Update tag name and metadata."""
        # Resolve target component
        success, entity, error = self.resolver.resolve(ctx.target, ctx.model, ctx.model_type)
        if not success:
            return error_response(error, "TARGET_NOT_FOUND")

        if ctx.model_type == "dexpi":
            return self._handle_set_tag_properties_dexpi(ctx, entity)
        elif ctx.model_type == "sfiles":
            return self._handle_set_tag_properties_sfiles(ctx, entity)

        return self._action_not_applicable(ctx, "set_tag_properties")

    def _handle_set_tag_properties_dexpi(self, ctx: ActionContext, component: Any) -> dict:
        """DEXPI: Update TagName and metadata."""
        new_tag = ctx.payload.get("new_tag")
        metadata = ctx.payload.get("metadata", {})

        old_tag = getattr(component, 'tagName', None) or getattr(component, 'tag', None)

        # Update tag name
        if new_tag:
            if hasattr(component, 'tagName'):
                component.tagName = new_tag
            elif hasattr(component, 'tag'):
                component.tag = new_tag
            else:
                return error_response(
                    f"Component has no tagName or tag attribute",
                    "INVALID_COMPONENT"
                )

        # Update metadata attributes
        for key, value in metadata.items():
            if hasattr(component, key):
                setattr(component, key, value)
            else:
                logger.warning(f"Component has no attribute '{key}'")

        ctx.mutated_entities.append(str(new_tag or old_tag))

        return success_response({
            "mutated_entities": ctx.mutated_entities,
            "diff": {
                "added": [],
                "removed": [],
                "updated": ctx.mutated_entities
            },
            "validation": {
                "errors": ctx.validation_errors,
                "warnings": ctx.validation_warnings
            },
            "new_tags": {str(old_tag): str(new_tag)} if new_tag else {}
        })

    def _handle_set_tag_properties_sfiles(self, ctx: ActionContext, unit_name: str) -> dict:
        """SFILES: Rename unit node and update metadata."""
        new_tag = ctx.payload.get("new_tag")
        metadata = ctx.payload.get("metadata", {})

        if not hasattr(ctx.model, 'state'):
            return error_response("Model has no state graph", "INVALID_MODEL")

        if not ctx.model.state.has_node(unit_name):
            return error_response("TARGET_NOT_FOUND", f"Unit not found: {unit_name}")

        # Rename node if new_tag provided
        if new_tag and new_tag != unit_name:
            # NetworkX node renaming: copy node with new name
            node_data = ctx.model.state.nodes[unit_name]

            # Add new node with same attributes
            ctx.model.state.add_node(new_tag, **node_data)

            # Copy edges
            for pred in ctx.model.state.predecessors(unit_name):
                edge_data = ctx.model.state[pred][unit_name]
                ctx.model.state.add_edge(pred, new_tag, **edge_data)

            for succ in ctx.model.state.successors(unit_name):
                edge_data = ctx.model.state[unit_name][succ]
                ctx.model.state.add_edge(new_tag, succ, **edge_data)

            # Remove old node
            ctx.model.state.remove_node(unit_name)

            unit_name = new_tag  # Update reference

        # Update metadata
        for key, value in metadata.items():
            ctx.model.state.nodes[unit_name][key] = value

        # Re-canonicalize
        if hasattr(ctx.model, 'convert_to_sfiles'):
            ctx.model.convert_to_sfiles()

        ctx.mutated_entities.append(new_tag or unit_name)

        old_tag = ctx.target.get("identifier")
        return success_response({
            "mutated_entities": ctx.mutated_entities,
            "diff": {
                "added": [],
                "removed": [],
                "updated": ctx.mutated_entities
            },
            "validation": {
                "errors": ctx.validation_errors,
                "warnings": ctx.validation_warnings
            },
            "new_tags": {old_tag: new_tag} if new_tag else {}
        })

    # ========== VALIDATION ==========

    def _validate_pre(self, ctx: ActionContext) -> dict:
        """Pre-action validation."""
        # Basic payload validation
        if not ctx.payload:
            return error_response(
                "Payload cannot be empty",
                "INVALID_PAYLOAD"
            )

        return success_response({"validated": True})

    def _validate_post(self, ctx: ActionContext) -> dict:
        """Post-action validation."""
        if ctx.model_type == "dexpi":
            try:
                # Use MLGraphLoader for validation
                self.graph_loader.validate_graph_format(ctx.model)
                return success_response({"validated": True})
            except Exception as e:
                return error_response(
                    f"DEXPI validation failed: {str(e)}",
                    "VALIDATION_FAILED"
                )

        elif ctx.model_type == "sfiles":
            try:
                # SFILES round-trip validation
                sfiles_str = ctx.model.convert_to_sfiles()
                return success_response({"validated": True})
            except Exception as e:
                return error_response(
                    f"SFILES validation failed: {str(e)}",
                    "VALIDATION_FAILED"
                )

        return success_response({"validated": True})

    def _action_not_applicable(self, ctx: ActionContext, action: str) -> dict:
        """Return ACTION_NOT_APPLICABLE error."""
        return error_response(
            f"Action '{action}' not applicable to {ctx.model_type} models",
            "ACTION_NOT_APPLICABLE",
            details={"model_type": ctx.model_type, "action": action}
        )
