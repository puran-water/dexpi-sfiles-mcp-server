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

        # Store swapping for isolation (scoped to this invocation)
        original_model = None  # Local variable, not instance attribute
        swapped_store = False

        # Transaction wrapping
        if options.get("create_transaction") and not options.get("dry_run"):
            # begin() returns string transaction_id, not dict
            ctx.transaction_id = await self.transaction_manager.begin(model_id)

            # Get working model from transaction (public API that materializes from snapshot)
            ctx.model = self.transaction_manager.get_working_model(ctx.transaction_id)

            # CRITICAL: Temporarily swap store entry so delegates operate on working copy
            # This ensures all mutations (via dexpi_tools/sfiles_tools) affect the transaction
            if ctx.model_type == "dexpi":
                original_model = self.dexpi_models[model_id]  # Save original
                self.dexpi_models[model_id] = ctx.model  # Point to working copy
                swapped_store = True
            elif ctx.model_type == "sfiles":
                original_model = self.flowsheets[model_id]  # Save original
                self.flowsheets[model_id] = ctx.model  # Point to working copy
                swapped_store = True

        # For dry_run, work on a copy and swap stores
        elif options.get("dry_run"):
            if ctx.model_type == "dexpi":
                import copy
                ctx.model = copy.deepcopy(ctx.model)
                # Swap store entry so delegates operate on copy
                original_model = self.dexpi_models[model_id]
                self.dexpi_models[model_id] = ctx.model
                swapped_store = True
            elif ctx.model_type == "sfiles":
                # SFILES: create copy via serialize/deserialize
                sfiles_str = ctx.model.convert_to_sfiles()
                from src.adapters.sfiles_adapter import create_flowsheet
                ctx.model = create_flowsheet()
                ctx.model.create_from_sfiles(sfiles_str)
                # Swap store entry so delegates operate on copy
                original_model = self.flowsheets[model_id]
                self.flowsheets[model_id] = ctx.model
                swapped_store = True

        try:
            # Dispatch to action handler
            result = await self._dispatch_action(action_enum, ctx)

            if not result.get("ok"):
                # Rollback on error
                if ctx.transaction_id:
                    await self.transaction_manager.rollback(ctx.transaction_id)

                # Restore original model if we swapped stores
                if swapped_store and original_model is not None:
                    if ctx.model_type == "dexpi":
                        self.dexpi_models[model_id] = original_model
                    elif ctx.model_type == "sfiles":
                        self.flowsheets[model_id] = original_model

                return result

            # Post-validation
            if options.get("validate_after"):
                validation = self._validate_post(ctx)
                if not validation.get("ok"):
                    if ctx.transaction_id:
                        await self.transaction_manager.rollback(ctx.transaction_id)

                    # Restore original model if we swapped stores
                    if swapped_store and original_model is not None:
                        if ctx.model_type == "dexpi":
                            self.dexpi_models[model_id] = original_model
                        elif ctx.model_type == "sfiles":
                            self.flowsheets[model_id] = original_model

                    return validation

            # Commit transaction (not for dry_run)
            if ctx.transaction_id and not options.get("dry_run"):
                # commit() returns CommitResult dataclass, not dict
                commit_result = await self.transaction_manager.commit(ctx.transaction_id)

                # Add diff from transaction (access dataclass attributes)
                if "data" not in result:
                    result["data"] = {}
                result["data"]["diff"] = {
                    "added": commit_result.diff.added,
                    "removed": commit_result.diff.removed,
                    "modified": commit_result.diff.modified,
                    "metadata": commit_result.diff.metadata
                }
                result["data"]["operations_applied"] = commit_result.operations_applied

            # For dry_run, indicate no changes were made and restore original
            if options.get("dry_run"):
                if "data" not in result:
                    result["data"] = {}
                result["data"]["dry_run"] = True

                # Restore original model from store (dry_run shouldn't persist)
                if swapped_store and original_model is not None:
                    if ctx.model_type == "dexpi":
                        self.dexpi_models[model_id] = original_model
                    elif ctx.model_type == "sfiles":
                        self.flowsheets[model_id] = original_model

            return result

        except Exception as e:
            logger.error(f"graph_modify error: {e}", exc_info=True)
            if ctx.transaction_id:
                await self.transaction_manager.rollback(ctx.transaction_id)

            # Restore original model on error (if we swapped)
            if swapped_store and original_model is not None:
                if ctx.model_type == "dexpi":
                    self.dexpi_models[model_id] = original_model
                elif ctx.model_type == "sfiles":
                    self.flowsheets[model_id] = original_model

            return error_response(
                f"Action execution failed: {str(e)}",
                "EXECUTION_ERROR"
            )

        finally:
            # Restore original model if we swapped stores for transaction
            # (transaction commit handles persistence to the real store)
            if swapped_store and original_model is not None and ctx.transaction_id:
                if ctx.model_type == "dexpi":
                    # Commit already persisted working model to store, safe to cleanup
                    pass
                elif ctx.model_type == "sfiles":
                    # Commit already persisted working model to store, safe to cleanup
                    pass
                # Note: For transactions, we don't restore because commit() already
                # wrote the working model to the store. The swap was just temporary
                # for delegate isolation during execution.

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
            return await self._handle_split_segment(ctx)
        elif action == GraphAction.MERGE_SEGMENTS:
            return await self._handle_merge_segments(ctx)
        elif action == GraphAction.UPDATE_STREAM_PROPERTIES:
            return await self._handle_update_stream_properties(ctx)
        elif action == GraphAction.TOGGLE_INSTRUMENTATION:
            return await self._handle_toggle_instrumentation(ctx)

        return error_response(
            f"Action not implemented: {action.value}",
            "UNKNOWN_ACTION"
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

        return error_response(f"Unit not found: {unit_name}", "TARGET_NOT_FOUND")

    async def _handle_insert_inline_component(self, ctx: ActionContext) -> dict:
        """Action 3: Insert component inline (DEXPI only)."""
        if ctx.model_type != "dexpi":
            return self._action_not_applicable(ctx, "insert_inline_component")

        if not self.dexpi_tools:
            return error_response("dexpi_tools not available", "MISSING_DEPENDENCY")

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
        """DEXPI: Rewire existing segment to new endpoints using piping_toolkit."""
        from pydexpi.toolkits import piping_toolkit as pt

        # Resolve target segment
        success, segment, error = self.resolver.resolve(ctx.target, ctx.model, ctx.model_type)
        if not success:
            return error_response(error, "TARGET_NOT_FOUND")

        # Validate segment type
        if not hasattr(segment, '__class__') or 'PipingNetworkSegment' not in segment.__class__.__name__:
            return error_response(
                f"Target is not a PipingNetworkSegment: {type(segment).__name__}",
                "INVALID_TARGET_TYPE"
            )

        # Get new endpoints
        new_from = ctx.payload.get("from")  # Component/nozzle to connect as source
        new_to = ctx.payload.get("to")      # Component/nozzle to connect as target
        preserve_props = ctx.payload.get("preserve_properties", True)

        if not new_from and not new_to:
            return error_response(
                "Must specify at least one of 'from' or 'to' for rewiring",
                "INVALID_PAYLOAD"
            )

        # Save segment properties if preserving
        segment_props = {}
        if preserve_props:
            segment_props = {
                'pipeClass': getattr(segment, 'pipeClass', None),
                'nominalDiameter': getattr(segment, 'nominalDiameter', None),
                'material': getattr(segment, 'material', None)
            }

        # Resolve new endpoint entities
        def resolve_endpoint(endpoint_spec):
            """Resolve endpoint to equipment/nozzle object."""
            if isinstance(endpoint_spec, str):
                # Look up component by tag
                from pydexpi.toolkits import model_toolkit as mt
                equipments = mt.get_all_instances_in_model(ctx.model, 'Equipment')
                for eq in equipments:
                    if getattr(eq, 'tagName', None) == endpoint_spec:
                        return eq
                return None
            return endpoint_spec  # Assume already an object

        # Reconnect using piping_toolkit
        try:
            # Rewire source connection
            if new_from:
                from_obj = resolve_endpoint(new_from)
                if not from_obj:
                    return error_response(f"Cannot resolve 'from' endpoint: {new_from}", "TARGET_NOT_FOUND")

                # Disconnect current source and connect to new one
                pt.connect_piping_network_segment(
                    piping_segment=segment,
                    connector_item=from_obj,
                    as_source=False,  # Connecting TO the segment (segment receives flow FROM this)
                    force_reconnect=True
                )

            # Rewire target connection
            if new_to:
                to_obj = resolve_endpoint(new_to)
                if not to_obj:
                    return error_response(f"Cannot resolve 'to' endpoint: {new_to}", "TARGET_NOT_FOUND")

                # Disconnect current target and connect to new one
                pt.connect_piping_network_segment(
                    piping_segment=segment,
                    connector_item=to_obj,
                    as_source=True,  # Connecting FROM the segment (segment sends flow TO this)
                    force_reconnect=True
                )

            # Restore properties if preserving
            if preserve_props:
                for key, value in segment_props.items():
                    if value is not None:
                        setattr(segment, key, value)

            # Track segment as updated
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

        except (pt.DexpiConnectionException, pt.DexpiCorruptPipingSegmentException, ValueError) as e:
            logger.error(f"Rewire connection failed: {e}")
            return error_response(
                f"Failed to rewire segment: {str(e)}",
                "REWIRE_FAILED"
            )
        except Exception as e:
            logger.error(f"Unexpected error in rewire_connection: {e}", exc_info=True)
            return error_response(
                f"Rewire operation failed: {str(e)}",
                "EXECUTION_ERROR"
            )

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
        """DEXPI: Remove equipment from model.

        Note: Automatic rerouting is NOT implemented in v1.
        If reroute_connections is requested, returns ACTION_NOT_APPLICABLE.
        """
        cascade = ctx.payload.get("cascade", False)
        reroute = ctx.payload.get("reroute_connections", False)  # Changed default to False

        tag = getattr(component, 'tagName', None) or getattr(component, 'tag', None)

        # Check if rerouting was explicitly requested
        if reroute:
            return error_response(
                f"Automatic rerouting not implemented. To remove {tag}, set reroute_connections=False "
                f"and manually reconnect piping, or use cascade=True to remove connected segments.",
                "ACTION_NOT_APPLICABLE",
                details={
                    "component": str(tag),
                    "requested_feature": "reroute_connections",
                    "status": "not_implemented",
                    "alternatives": [
                        "Set reroute_connections=False and manually reconnect piping",
                        "Use cascade=True to remove component and connected segments"
                    ]
                }
            )

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

        # Add warning about connected piping
        if hasattr(component, 'nozzles') and component.nozzles:
            ctx.validation_warnings.append({
                "code": "MANUAL_REROUTE_REQUIRED",
                "message": f"Component {tag} removed. {len(component.nozzles)} nozzles were connected - "
                          f"piping segments may now be disconnected and require manual reconnection."
            })

        return success_response({
            "mutated_entities": ctx.mutated_entities,
            "diff": {
                "added": [],
                "removed": [str(tag)],
                "updated": []  # No rerouting in v1
            },
            "validation": {
                "errors": ctx.validation_errors,
                "warnings": ctx.validation_warnings
            }
        })

    def _handle_remove_component_sfiles(self, ctx: ActionContext, unit_name: str) -> dict:
        """SFILES: Remove unit from flowsheet.

        Note: Automatic rerouting is NOT implemented in v1.
        If reroute_connections is requested, returns ACTION_NOT_APPLICABLE.
        """
        cascade = ctx.payload.get("cascade", False)
        reroute = ctx.payload.get("reroute_connections", False)  # Changed default to False

        if not hasattr(ctx.model, 'state'):
            return error_response("Model has no state graph", "INVALID_MODEL")

        if not ctx.model.state.has_node(unit_name):
            return error_response(f"Unit not found: {unit_name}", "TARGET_NOT_FOUND")

        # Get connected edges
        predecessors = list(ctx.model.state.predecessors(unit_name))
        successors = list(ctx.model.state.successors(unit_name))

        # Check if rerouting is explicitly requested
        # For SFILES, we have basic implementation (connect predecessors to successors)
        if reroute and (len(predecessors) > 1 or len(successors) > 1):
            # Complex rerouting (multiple branches) not supported
            return error_response(
                f"Cannot reroute complex topology around {unit_name}. "
                f"Found {len(predecessors)} predecessors and {len(successors)} successors. "
                f"Set reroute_connections=False and manually reconnect streams.",
                "ACTION_NOT_APPLICABLE",
                details={
                    "unit": unit_name,
                    "predecessors": predecessors,
                    "successors": successors,
                    "status": "complex_topology_not_supported"
                }
            )

        # Remove node
        ctx.model.state.remove_node(unit_name)

        # Simple rerouting: connect single predecessor to single successor
        rerouted_streams = []
        if reroute and not cascade and len(predecessors) == 1 and len(successors) == 1:
            pred = predecessors[0]
            succ = successors[0]
            if not ctx.model.state.has_edge(pred, succ):
                ctx.model.state.add_edge(pred, succ, name=f"{pred}-{succ}")
                rerouted_streams.append(f"{pred}-{succ}")
                logger.info(f"Rerouted {pred} -> {succ} around removed {unit_name}")
        elif (predecessors or successors) and not reroute:
            # Warn about disconnected streams
            ctx.validation_warnings.append({
                "code": "MANUAL_REROUTE_REQUIRED",
                "message": f"Unit {unit_name} removed with {len(predecessors)} incoming and "
                          f"{len(successors)} outgoing streams. Manual reconnection may be required."
            })

        # Re-canonicalize
        if hasattr(ctx.model, 'convert_to_sfiles'):
            ctx.model.convert_to_sfiles()

        ctx.mutated_entities.append(unit_name)

        return success_response({
            "mutated_entities": ctx.mutated_entities,
            "diff": {
                "added": rerouted_streams if reroute else [],  # New streams created by rerouting
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
            return error_response(f"Unit not found: {unit_name}", "TARGET_NOT_FOUND")

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

    # ================================================================
    # V2 ACTION HANDLERS (4 additional operations)
    # ================================================================

    async def _handle_split_segment(self, ctx: ActionContext) -> dict:
        """Split a piping segment at a specific position (DEXPI only)."""
        if ctx.model_type == "sfiles":
            return self._action_not_applicable(ctx, "split_segment")

        # DEXPI implementation
        return await self._handle_split_segment_dexpi(ctx)

    async def _handle_split_segment_dexpi(self, ctx: ActionContext) -> dict:
        """DEXPI: Split segment using pyDEXPI utilities."""
        payload = ctx.payload

        # Validate payload
        if "split_point" not in payload:
            return error_response("Missing required field: split_point", "INVALID_PAYLOAD")

        split_point = payload.get("split_point", 0.5)
        if not (0.0 < split_point < 1.0):
            return error_response(
                "split_point must be between 0.0 and 1.0 (exclusive)",
                "INVALID_PAYLOAD"
            )

        # For now, return NOT_IMPLEMENTED with detailed guidance (skip segment resolution)
        # Full implementation would require:
        # 1. Find segment start/end connections
        # 2. Create two new segments at split point
        # 3. Optionally insert component at split
        # 4. Remove old segment, add new segments
        # 5. Validate with piping_network_segment_validity_check
        return error_response(
            "split_segment requires custom segment surgery logic not yet implemented. "
            "Use insert_inline_component instead for adding components to segments.",
            "NOT_IMPLEMENTED",
            details={
                "alternative": "Use insert_inline_component to add components at specific positions",
                "specification": "See docs/api/graph_modify_spec.md lines 247-319"
            }
        )

    async def _handle_merge_segments(self, ctx: ActionContext) -> dict:
        """Combine two adjacent segments into one (DEXPI only)."""
        if ctx.model_type == "sfiles":
            return self._action_not_applicable(ctx, "merge_segments")

        # DEXPI implementation
        return await self._handle_merge_segments_dexpi(ctx)

    async def _handle_merge_segments_dexpi(self, ctx: ActionContext) -> dict:
        """DEXPI: Merge adjacent segments with validity checks."""
        payload = ctx.payload

        # Validate payload
        if "second_segment_id" not in payload:
            return error_response("Missing required field: second_segment_id", "INVALID_PAYLOAD")

        # For now, return NOT_IMPLEMENTED with detailed guidance (skip segment resolution)
        # Full implementation would require:
        # 1. Verify segments are adjacent (share connection point)
        # 2. Create merged segment from start of seg1 to end of seg2
        # 3. Inherit properties based on payload.inherit_properties
        # 4. Remove both old segments, add merged segment
        # 5. Validate with piping_network_segment_validity_check
        return error_response(
            "merge_segments requires adjacency checking and segment surgery not yet implemented. "
            "Merge can be achieved manually by: (1) remove intermediate component, (2) rewire_connection.",
            "NOT_IMPLEMENTED",
            details={
                "alternative": "Use remove_component + rewire_connection for similar effect",
                "specification": "See docs/api/graph_modify_spec.md lines 323-362"
            }
        )

    async def _handle_update_stream_properties(self, ctx: ActionContext) -> dict:
        """Update stream properties (SFILES only)."""
        if ctx.model_type == "dexpi":
            return self._action_not_applicable(ctx, "update_stream_properties")

        # SFILES implementation
        return await self._handle_update_stream_properties_sfiles(ctx)

    async def _handle_update_stream_properties_sfiles(self, ctx: ActionContext) -> dict:
        """SFILES: Update stream properties with re-canonicalization."""
        payload = ctx.payload
        flowsheet = ctx.model

        # Validate payload
        if "properties" not in payload:
            return error_response("Missing required field: properties", "INVALID_PAYLOAD")

        properties = payload["properties"]
        merge = payload.get("merge", True)

        # Resolve stream from target
        target_id = ctx.target.get("identifier", "")

        # Parse stream identifier (format: "from_unit->to_unit" or stream name)
        if "->" in target_id:
            parts = target_id.split("->")
            if len(parts) != 2:
                return error_response(
                    "Stream identifier must be 'from_unit->to_unit' format",
                    "INVALID_TARGET"
                )
            from_unit, to_unit = parts[0].strip(), parts[1].strip()
        else:
            # Try to find stream by name in flowsheet
            return error_response(
                "Stream lookup by name not yet implemented. Use 'from_unit->to_unit' format.",
                "NOT_IMPLEMENTED",
                details={"example": "reactor-1->tank-2"}
            )

        # Check if edge exists
        if not flowsheet.state.has_edge(from_unit, to_unit):
            return error_response(
                f"Stream edge not found: {from_unit} -> {to_unit}",
                "TARGET_NOT_FOUND"
            )

        # Update properties
        edge_data = flowsheet.state[from_unit][to_unit]

        if merge:
            # Merge new properties into existing
            edge_data.update(properties)
        else:
            # Replace all properties
            # Keep system properties (if any), replace user properties
            flowsheet.state.remove_edge(from_unit, to_unit)
            flowsheet.state.add_edge(from_unit, to_unit, **properties)

        # Re-canonicalize SFILES representation
        try:
            flowsheet.convert_to_sfiles(version="v2", canonical=True)
        except Exception as e:
            logger.error(f"SFILES canonicalization failed after property update: {e}")
            return error_response(
                f"Failed to re-canonicalize SFILES: {str(e)}",
                "CANONICALIZATION_FAILED"
            )

        ctx.mutated_entities.append(f"stream:{from_unit}->{to_unit}")

        return success_response({
            "mutated": ctx.mutated_entities,
            "stream": f"{from_unit} -> {to_unit}",
            "properties_updated": list(properties.keys()),
            "merge_mode": merge
        })

    async def _handle_toggle_instrumentation(self, ctx: ActionContext) -> dict:
        """Add or remove instrumentation."""
        payload = ctx.payload

        # Validate operation
        operation = payload.get("operation")
        if operation not in ["add", "remove"]:
            return error_response(
                "operation must be 'add' or 'remove'",
                "INVALID_PAYLOAD"
            )

        if ctx.model_type == "dexpi":
            return await self._handle_toggle_instrumentation_dexpi(ctx)
        else:
            return await self._handle_toggle_instrumentation_sfiles(ctx)

    async def _handle_toggle_instrumentation_dexpi(self, ctx: ActionContext) -> dict:
        """DEXPI: Add/remove instruments and signal lines."""
        payload = ctx.payload
        operation = payload["operation"]

        if operation == "add":
            # Use dexpi_add_instrumentation or dexpi_add_control_loop
            instrument_type = payload.get("instrument_type")
            tag = payload.get("tag")

            if not instrument_type or not tag:
                return error_response(
                    "Missing required fields: instrument_type, tag",
                    "INVALID_PAYLOAD"
                )

            # For now, delegate to existing dexpi_tools
            return error_response(
                "toggle_instrumentation (add) should use dexpi_add_instrumentation or dexpi_add_control_loop directly. "
                "This action is redundant with existing specialized tools.",
                "NOT_IMPLEMENTED",
                details={
                    "alternative": "Use dexpi_add_instrumentation or dexpi_add_control_loop",
                    "reason": "Dedicated tools provide better parameter validation and documentation"
                }
            )
        else:  # remove
            # Need to find and remove instrument by tag
            return error_response(
                "toggle_instrumentation (remove) requires traversing signal lines and removing instruments, "
                "not yet implemented. Use remove_component for simple instrument removal.",
                "NOT_IMPLEMENTED",
                details={
                    "alternative": "Use remove_component to remove instrument by tag",
                    "specification": "See docs/api/graph_modify_spec.md lines 549-587"
                }
            )

    async def _handle_toggle_instrumentation_sfiles(self, ctx: ActionContext) -> dict:
        """SFILES: Add/remove control tags."""
        payload = ctx.payload
        operation = payload["operation"]

        if operation == "add":
            # Use sfiles_add_control
            control_type = payload.get("instrument_type")  # FC, LC, TC, PC, etc.
            tag = payload.get("tag")
            connected_unit = payload.get("sensing_location")  # Where to attach control

            if not all([control_type, tag, connected_unit]):
                return error_response(
                    "Missing required fields: instrument_type, tag, sensing_location",
                    "INVALID_PAYLOAD"
                )

            # Delegate to sfiles_add_control
            return error_response(
                "toggle_instrumentation (add) should use sfiles_add_control directly. "
                "This action is redundant with existing specialized tools.",
                "NOT_IMPLEMENTED",
                details={
                    "alternative": "Use sfiles_add_control",
                    "reason": "Dedicated tool provides better parameter validation and documentation"
                }
            )
        else:  # remove
            # Need to find and remove control tag
            return error_response(
                "toggle_instrumentation (remove) requires finding control nodes in flowsheet, "
                "not yet implemented.",
                "NOT_IMPLEMENTED",
                details={
                    "specification": "See docs/api/graph_modify_spec.md lines 549-587"
                }
            )

    def _action_not_applicable(self, ctx: ActionContext, action: str) -> dict:
        """Return ACTION_NOT_APPLICABLE error."""
        return error_response(
            f"Action '{action}' not applicable to {ctx.model_type} models",
            "ACTION_NOT_APPLICABLE",
            details={"model_type": ctx.model_type, "action": action}
        )
