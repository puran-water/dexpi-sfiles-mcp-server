"""High-value batch and automation tools for engineering MCP server."""

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from mcp import Tool
from ..utils.response import success_response, error_response, create_issue, is_success

logger = logging.getLogger(__name__)


class BatchTools:
    """Handles batch operations, validation, and smart connections."""
    
    def __init__(self, dexpi_tools, sfiles_tools, dexpi_models, flowsheets):
        """Initialize with references to existing tool handlers."""
        self.dexpi_tools = dexpi_tools
        self.sfiles_tools = sfiles_tools
        self.dexpi_models = dexpi_models
        self.flowsheets = flowsheets
        self.idempotency_cache = {}  # Track completed operations
    
    def get_tools(self) -> List[Tool]:
        """Return all batch tools."""
        return [
            Tool(
                name="model_batch_apply",
                description="Execute multiple operations in a single call for efficiency",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string", "description": "Model to operate on"},
                        "operations": {
                            "type": "array",
                            "description": "List of operations to execute",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "tool": {"type": "string", "description": "Tool name to execute"},
                                    "params": {"type": "object", "description": "Parameters for the tool"}
                                },
                                "required": ["tool", "params"]
                            }
                        },
                        "idempotency_key": {
                            "type": "string",
                            "description": "Optional key to prevent duplicate execution"
                        },
                        "stop_on_error": {
                            "type": "boolean",
                            "default": True,
                            "description": "Whether to stop on first error"
                        }
                    },
                    "required": ["model_id", "operations"]
                }
            ),
            Tool(
                name="rules_apply",
                description="Apply validation rules and return structured issues for LLM processing. Optionally auto-fix issues.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string", "description": "Model to validate"},
                        "rule_sets": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Rule sets to apply (default: all)",
                            "default": ["syntax", "topology", "connectivity"]
                        },
                        "scope": {
                            "type": "string",
                            "enum": ["model", "area", "selection"],
                            "default": "model",
                            "description": "Validation scope"
                        },
                        "autofix": {
                            "type": "boolean",
                            "default": False,
                            "description": "Automatically fix issues when possible"
                        }
                    },
                    "required": ["model_id"]
                }
            ),
            Tool(
                name="graph_connect",
                description="Smart autowiring with patterns and optional inline components",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string", "description": "Model to modify"},
                        "strategy": {
                            "type": "string",
                            "enum": ["by_port_type", "pumps_to_header"],
                            "description": "Connection strategy"
                        },
                        "rules": {
                            "type": "object",
                            "properties": {
                                "from_selector": {"type": "string", "description": "Source equipment pattern"},
                                "to_selector": {"type": "string", "description": "Target equipment/header"},
                                "insert_components": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Components to insert inline (e.g., check_valve, isolation_valve)"
                                },
                                "line_class": {
                                    "type": "string",
                                    "default": "CS150",
                                    "description": "Piping class for connections"
                                }
                            },
                            "required": ["from_selector", "to_selector"]
                        }
                    },
                    "required": ["model_id", "strategy", "rules"]
                }
            )
        ]
    
    async def handle_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route tool calls to appropriate handlers."""
        if name == "model_batch_apply":
            return await self.model_batch_apply(arguments)
        elif name == "rules_apply":
            return await self.rules_apply(arguments)
        elif name == "graph_connect":
            return await self.graph_connect(arguments)
        else:
            return error_response(f"Unknown batch tool: {name}")
    
    async def model_batch_apply(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute multiple operations in sequence."""
        model_id = arguments["model_id"]
        operations = arguments["operations"]
        idempotency_key = arguments.get("idempotency_key")
        stop_on_error = arguments.get("stop_on_error", True)
        
        # Check idempotency
        if idempotency_key and idempotency_key in self.idempotency_cache:
            return success_response({
                "cached": True,
                "results": self.idempotency_cache[idempotency_key]
            })
        
        results = []
        success_count = 0
        error_count = 0
        name_map = {}  # Track requested->actual names
        
        for i, op in enumerate(operations):
            try:
                tool_name = op["tool"]
                params = op["params"].copy()
                
                # Inject model_id if not present
                if "model_id" not in params and "flowsheet_id" not in params:
                    if tool_name.startswith("dexpi"):
                        params["model_id"] = model_id
                    elif tool_name.startswith("sfiles"):
                        params["flowsheet_id"] = model_id
                
                # Dispatch to appropriate tool handler
                if tool_name.startswith("dexpi"):
                    result = await self.dexpi_tools.handle_tool(tool_name, params)
                elif tool_name.startswith("sfiles"):
                    result = await self.sfiles_tools.handle_tool(tool_name, params)
                else:
                    result = error_response(f"Unknown tool: {tool_name}")
                
                # Check success using normalized helper
                op_success = is_success(result)
                
                # Track name changes for SFILES units
                if op_success and tool_name == "sfiles_add_unit":
                    requested_name = params.get("unit_name")
                    actual_name = result.get("data", {}).get("unit_name")
                    if requested_name and actual_name and requested_name != actual_name:
                        name_map[requested_name] = actual_name
                
                results.append({
                    "index": i,
                    "tool": tool_name,
                    "result": result,
                    "ok": op_success
                })
                
                if op_success:
                    success_count += 1
                else:
                    error_count += 1
                    if stop_on_error:
                        break
                        
            except Exception as e:
                error_result = {
                    "index": i,
                    "tool": op.get("tool", "unknown"),
                    "error": str(e),
                    "ok": False
                }
                results.append(error_result)
                error_count += 1
                
                if stop_on_error:
                    break
        
        # Cache if idempotency key provided
        if idempotency_key:
            self.idempotency_cache[idempotency_key] = results
        
        response_data = {
            "results": results,
            "stats": {
                "total": len(operations),
                "executed": len(results),
                "success": success_count,
                "errors": error_count
            }
        }
        
        # Include name map if any names changed
        if name_map:
            response_data["name_map"] = name_map
        
        return success_response(response_data)
    
    async def rules_apply(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply validation rules using upstream libraries.

        - DEXPI models: Uses MLGraphLoader.validate_graph_format()
        - SFILES models: Uses round-trip conversion (parse → convert → compare)

        Both approaches leverage upstream library validation capabilities.

        With autofix enabled, automatically corrects issues when possible.
        """
        model_id = arguments["model_id"]
        rule_sets = arguments.get("rule_sets", ["syntax", "topology", "connectivity"])
        scope = arguments.get("scope", "model")
        autofix = arguments.get("autofix", False)

        # Check if DEXPI model
        if model_id in self.dexpi_models:
            return await self._validate_dexpi(model_id, rule_sets, scope, autofix)

        # Check if SFILES model
        elif model_id in self.flowsheets:
            return await self._validate_sfiles(model_id, rule_sets, scope, autofix)

        # Model not found
        else:
            return error_response(f"Model not found: {model_id}")

    async def _validate_dexpi(self, model_id: str, rule_sets: List[str], scope: str, autofix: bool = False) -> Dict[str, Any]:
        """Validate DEXPI model using MLGraphLoader."""
        from pydexpi.loaders.ml_graph_loader import MLGraphLoader

        issues = []
        fixes_applied = []

        try:
            model = self.dexpi_models[model_id]
            loader = MLGraphLoader()

            # Convert DEXPI model to graph (stores internally in loader.plant_graph)
            try:
                graph = loader.dexpi_to_graph(model)
                logger.info(f"DEXPI graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
            except Exception as e:
                logger.error(f"Error during dexpi_to_graph: {type(e).__name__}: {e}")
                raise

            # Validate using MLGraphLoader (operates on internal plant_graph)
            try:
                logger.info("Validating DEXPI format...")
                loader.validate_graph_format()
                logger.info("DEXPI validation passed!")
            except AttributeError as e:
                error_msg = str(e)
                logger.warning(f"DEXPI validation failed: {error_msg}")

                if "missing required attribute" in error_msg.lower():
                    issues.append({
                        "severity": "error",
                        "message": error_msg,
                        "location": None,
                        "rule": "dexpi_attribute_compliance",
                        "scope": scope,
                        "can_autofix": False,
                        "suggested_fix": "Add missing required attributes to nodes/edges"
                    })
                elif "invalid class" in error_msg.lower():
                    issues.append({
                        "severity": "error",
                        "message": error_msg,
                        "location": None,
                        "rule": "dexpi_class_compliance",
                        "scope": scope,
                        "can_autofix": False,
                        "suggested_fix": "Use valid DEXPI node/edge classes"
                    })
                else:
                    issues.append({
                        "severity": "error",
                        "message": error_msg,
                        "location": None,
                        "rule": "dexpi_format_validation",
                        "scope": scope,
                        "can_autofix": False,
                        "suggested_fix": None
                    })

        except Exception as e:
            issues.append({
                "severity": "error",
                "message": f"DEXPI validation failed: {str(e)}",
                "location": None,
                "rule": "validation_error",
                "scope": scope,
                "can_autofix": False,
                "suggested_fix": None
            })

        # Apply autofixes if requested
        if autofix and issues:
            fixes_applied = await self._apply_dexpi_fixes(model_id, issues)

        # Calculate statistics
        error_count = sum(1 for i in issues if i["severity"] == "error")
        warning_count = sum(1 for i in issues if i["severity"] == "warning")
        info_count = sum(1 for i in issues if i["severity"] == "info")

        response_data = {
            "valid": error_count == 0,
            "issues": issues,
            "stats": {
                "total": len(issues),
                "errors": error_count,
                "warnings": warning_count,
                "info": info_count
            },
            "rule_sets_applied": rule_sets,
            "validation_method": "MLGraphLoader"
        }

        if autofix:
            response_data["autofix_enabled"] = True
            response_data["fixes_applied"] = fixes_applied
            response_data["fixes_count"] = len(fixes_applied)

        return success_response(response_data)

    async def _validate_sfiles(self, model_id: str, rule_sets: List[str], scope: str, autofix: bool = False) -> Dict[str, Any]:
        """Validate SFILES model using round-trip conversion."""
        from ..adapters.sfiles_adapter import get_flowsheet_class
        Flowsheet = get_flowsheet_class()

        issues = []
        flowsheet = self.flowsheets[model_id]

        try:
            # Convert flowsheet to canonical SFILES string
            flowsheet.convert_to_sfiles(version="v2", canonical=True)
            original_sfiles = flowsheet.sfiles

            if not original_sfiles:
                issues.append({
                    "severity": "error",
                    "message": "Flowsheet has no SFILES representation (empty model)",
                    "location": None,
                    "rule": "sfiles_empty",
                    "scope": scope,
                    "can_autofix": False,
                    "suggested_fix": "Add units and streams to the flowsheet"
                })
            else:
                # Round-trip validation: parse and convert back
                logger.info(f"SFILES round-trip validation for {len(original_sfiles)} char string")
                test_flowsheet = Flowsheet()
                test_flowsheet.create_from_sfiles(original_sfiles)
                test_flowsheet.convert_to_sfiles(version="v2", canonical=True)
                regenerated_sfiles = test_flowsheet.sfiles

                # Compare canonical forms
                if original_sfiles != regenerated_sfiles:
                    issues.append({
                        "severity": "error",
                        "message": "Round-trip validation failed: topology not preserved",
                        "location": None,
                        "rule": "sfiles_round_trip",
                        "scope": scope,
                        "can_autofix": True,
                        "suggested_fix": "Normalize SFILES representation to canonical form"
                    })
                else:
                    logger.info(f"SFILES validation passed: {test_flowsheet.state.number_of_nodes()} nodes, {test_flowsheet.state.number_of_edges()} edges")

        except Exception as e:
            logger.error(f"SFILES validation error: {type(e).__name__}: {e}")
            issues.append({
                "severity": "error",
                "message": f"SFILES validation failed: {str(e)}",
                "location": None,
                "rule": "sfiles_parse",
                "scope": scope,
                "can_autofix": False,
                "suggested_fix": "Check SFILES syntax and ensure model can be parsed"
            })

        # Apply autofixes if requested
        fixes_applied = []
        if autofix and issues:
            fixes_applied = await self._apply_sfiles_fixes(model_id, issues)

        # Calculate statistics
        error_count = sum(1 for i in issues if i["severity"] == "error")
        warning_count = sum(1 for i in issues if i["severity"] == "warning")
        info_count = sum(1 for i in issues if i["severity"] == "info")

        response_data = {
            "valid": error_count == 0,
            "issues": issues,
            "stats": {
                "total": len(issues),
                "errors": error_count,
                "warnings": warning_count,
                "info": info_count
            },
            "rule_sets_applied": rule_sets,
            "validation_method": "round_trip"
        }

        if autofix:
            response_data["autofix_enabled"] = True
            response_data["fixes_applied"] = fixes_applied
            response_data["fixes_count"] = len(fixes_applied)

        return success_response(response_data)
    
    async def graph_connect(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Smart autowiring with patterns and optional inline components."""
        model_id = arguments["model_id"]
        strategy = arguments["strategy"]
        rules = arguments["rules"]
        
        # Check if model exists
        if model_id not in self.dexpi_models:
            return error_response(f"Model not found: {model_id}")
        
        model = self.dexpi_models[model_id]
        connections_made = []
        components_inserted = []
        
        try:
            if strategy == "pumps_to_header":
                # Find all pumps matching the pattern
                from_pattern = rules["from_selector"]
                to_header = rules["to_selector"]
                insert_components = rules.get("insert_components", [])
                line_class = rules.get("line_class", "CS150")
                
                # Find pumps (simplified - in real implementation would use proper search)
                pumps = self._find_equipment_by_pattern(model, from_pattern)
                
                for pump in pumps:
                    # Create line number for this connection
                    line_number = f"L-{pump['tag']}-{to_header}"
                    
                    # First, connect pump to header to create the segment
                    connect_result = await self.dexpi_tools.handle_tool(
                        "dexpi_connect_components",
                        {
                            "model_id": model_id,
                            "from_component": pump["tag"],
                            "to_component": to_header,
                            "line_number": line_number,
                            "pipe_class": line_class
                        }
                    )
                    
                    if is_success(connect_result):
                        connections_made.append(f"{pump['tag']} -> {to_header} (line: {line_number})")
                        
                        # Get segment_id from connection result
                        segment_id = connect_result.get("data", {}).get("segment_id")
                        
                        # Now insert valves inline into the created segment
                        if segment_id and insert_components:
                            for component_type in insert_components:
                                if component_type == "check_valve":
                                    valve_tag = f"CHK-{pump['tag']}"
                                    # Insert check valve inline into the segment
                                    # The valve will be created as part of the insertion
                                    insert_result = await self.dexpi_tools.handle_tool(
                                        "dexpi_insert_valve_in_segment",
                                        {
                                            "model_id": model_id,
                                            "segment_id": segment_id,
                                            "valve_type": "CheckValve",
                                            "tag_name": valve_tag,
                                            "at_position": 0.3  # Near pump discharge
                                        }
                                    )
                                    if is_success(insert_result):
                                        components_inserted.append(valve_tag)
                                
                                elif component_type == "isolation_valve":
                                    valve_tag = f"ISO-{pump['tag']}"
                                    # Insert gate valve inline into the segment
                                    # The valve will be created as part of the insertion
                                    insert_result = await self.dexpi_tools.handle_tool(
                                        "dexpi_insert_valve_in_segment",
                                        {
                                            "model_id": model_id,
                                            "segment_id": segment_id,
                                            "valve_type": "GateValve",
                                            "tag_name": valve_tag,
                                            "at_position": 0.7  # Near header
                                        }
                                    )
                                    if is_success(insert_result):
                                        components_inserted.append(valve_tag)
            
            elif strategy == "by_port_type":
                # Connect by matching port types intelligently (outlet to inlet, one-to-one)
                from_selector = rules["from_selector"]
                to_selector = rules["to_selector"]
                insert_components = rules.get("insert_components", [])
                line_class = rules.get("line_class", "CS150")
                
                # Find source and target equipment
                source_equipment = self._find_equipment(model, from_selector)
                target_equipment = self._find_equipment(model, to_selector)
                
                if source_equipment and target_equipment:
                    # Create single connection (not multiple)
                    line_number = f"L-{source_equipment['tag']}-{target_equipment['tag']}"
                    
                    connect_result = await self.dexpi_tools.handle_tool(
                        "dexpi_connect_components",
                        {
                            "model_id": model_id,
                            "from_component": source_equipment["tag"],
                            "to_component": target_equipment["tag"],
                            "line_number": line_number,
                            "pipe_class": line_class
                        }
                    )
                    
                    if is_success(connect_result):
                        connections_made.append(f"{source_equipment['tag']} -> {target_equipment['tag']}")
                        
                        # Get segment_id from connection result for inline insertion
                        segment_id = connect_result.get("data", {}).get("segment_id")
                        
                        # Insert inline components if requested
                        if segment_id and insert_components:
                            for idx, component_type in enumerate(insert_components):
                                position = (idx + 1) / (len(insert_components) + 1)  # Distribute evenly
                                
                                if component_type == "check_valve":
                                    valve_tag = f"CHK-{line_number}"
                                    insert_result = await self.dexpi_tools.handle_tool(
                                        "dexpi_insert_valve_in_segment",
                                        {
                                            "model_id": model_id,
                                            "segment_id": segment_id,
                                            "valve_type": "CheckValve",
                                            "tag_name": valve_tag,
                                            "at_position": position
                                        }
                                    )
                                    if is_success(insert_result):
                                        components_inserted.append(valve_tag)
                                
                                elif component_type == "isolation_valve":
                                    valve_tag = f"ISO-{line_number}"
                                    insert_result = await self.dexpi_tools.handle_tool(
                                        "dexpi_insert_valve_in_segment",
                                        {
                                            "model_id": model_id,
                                            "segment_id": segment_id,
                                            "valve_type": "GateValve",
                                            "tag_name": valve_tag,
                                            "at_position": position
                                        }
                                    )
                                    if is_success(insert_result):
                                        components_inserted.append(valve_tag)
            
            else:
                return error_response(f"Strategy not implemented: {strategy}")
            
            return success_response({
                "connections_made": connections_made,
                "components_inserted": components_inserted,
                "stats": {
                    "connections": len(connections_made),
                    "components": len(components_inserted)
                }
            })
            
        except Exception as e:
            logger.error(f"Error in graph_connect: {e}")
            return error_response(f"Connection failed: {str(e)}")
    
    def _find_equipment_by_pattern(self, model, pattern: str) -> List[Dict]:
        """Find equipment matching a tag pattern."""
        results = []
        
        # Simple pattern matching (in real implementation would be more sophisticated)
        if hasattr(model, 'conceptualModel') and hasattr(model.conceptualModel, 'taggedPlantItems'):
            for item in model.conceptualModel.taggedPlantItems:
                if hasattr(item, 'tagName'):
                    tag = item.tagName
                    # Simple wildcard matching
                    if pattern == "*":
                        # Match all
                        match = True
                    elif "*" in pattern:
                        # Wildcard pattern - convert to prefix matching
                        prefix = pattern.replace("*", "")
                        match = tag.startswith(prefix)
                    else:
                        # Exact match or contains
                        match = (pattern == tag or pattern in tag)
                    
                    if match:
                        results.append({
                            "tag": tag,
                            "type": item.__class__.__name__,
                            "id": getattr(item, 'id', None)
                        })
        
        return results
    
    def _find_open_ports(self, model, filter_pattern: str) -> List[Dict]:
        """Find unconnected nozzles/ports."""
        open_ports = []
        
        if hasattr(model, 'conceptualModel') and hasattr(model.conceptualModel, 'taggedPlantItems'):
            for equipment in model.conceptualModel.taggedPlantItems:
                if hasattr(equipment, 'nozzles'):
                    for nozzle in equipment.nozzles:
                        # Check if nozzle is connected (simplified)
                        if not self._is_connected(nozzle):
                            open_ports.append({
                                "equipment": equipment.tagName,
                                "nozzle": getattr(nozzle, 'subTagName', 'N/A'),
                                "type": getattr(nozzle, 'nozzleType', 'unknown')
                            })
        
        return open_ports
    
    def _find_equipment(self, model, tag: str) -> Dict:
        """Find specific equipment by tag."""
        if hasattr(model, 'conceptualModel') and hasattr(model.conceptualModel, 'taggedPlantItems'):
            for item in model.conceptualModel.taggedPlantItems:
                if hasattr(item, 'tagName') and item.tagName == tag:
                    return {
                        "tag": item.tagName,
                        "type": item.__class__.__name__,
                        "id": getattr(item, 'id', None)
                    }
        
        return {"tag": tag, "type": "unknown", "id": None}
    
    def _is_connected(self, nozzle) -> bool:
        """Check if a nozzle is connected (simplified)."""
        # Check if nozzle has any piping connections
        return hasattr(nozzle, 'pipingConnection') and nozzle.pipingConnection is not None

    async def _apply_dexpi_fixes(self, model_id: str, issues: List[Dict]) -> List[Dict]:
        """
        Apply automatic fixes to DEXPI model issues.

        Currently, DEXPI validation issues from MLGraphLoader are typically
        structural (missing attributes, invalid classes) which cannot be
        safely auto-fixed without user input.

        Returns list of fixes that were successfully applied.
        """
        fixes_applied = []

        # Currently, most DEXPI issues require manual intervention
        # Future enhancements could add specific autofixes for:
        # - Adding default attribute values
        # - Fixing tag naming conventions
        # - Removing orphaned nodes

        logger.info(f"DEXPI autofix: {len(issues)} issues found, 0 automatically fixable")

        return fixes_applied

    async def _apply_sfiles_fixes(self, model_id: str, issues: List[Dict]) -> List[Dict]:
        """
        Apply automatic fixes to SFILES model issues.

        Can fix certain issues like:
        - Normalizing SFILES representation
        - Removing invalid characters
        - Fixing basic syntax errors

        Returns list of fixes that were successfully applied.
        """
        from ..adapters.sfiles_adapter import get_flowsheet_class
        Flowsheet = get_flowsheet_class()

        fixes_applied = []
        flowsheet = self.flowsheets[model_id]

        for issue in issues:
            if not issue.get("can_autofix", False):
                continue

            rule = issue.get("rule")

            # Fix round-trip issues by normalizing
            if rule == "sfiles_round_trip":
                try:
                    # Regenerate canonical form
                    flowsheet.convert_to_sfiles(version="v2", canonical=True)

                    # Verify fix by re-parsing
                    test_flowsheet = Flowsheet()
                    test_flowsheet.create_from_sfiles(flowsheet.sfiles)
                    test_flowsheet.convert_to_sfiles(version="v2", canonical=True)

                    if flowsheet.sfiles == test_flowsheet.sfiles:
                        fixes_applied.append({
                            "rule": rule,
                            "fix": "Normalized SFILES representation to canonical form",
                            "success": True
                        })
                        logger.info(f"Fixed {rule}: normalized SFILES")
                    else:
                        fixes_applied.append({
                            "rule": rule,
                            "fix": "Attempted normalization but round-trip still fails",
                            "success": False
                        })
                except Exception as e:
                    logger.error(f"Failed to fix {rule}: {e}")
                    fixes_applied.append({
                        "rule": rule,
                        "fix": f"Auto-fix failed: {str(e)}",
                        "success": False
                    })

        logger.info(f"SFILES autofix: {len(fixes_applied)} fixes attempted, {sum(1 for f in fixes_applied if f['success'])} successful")

        return fixes_applied