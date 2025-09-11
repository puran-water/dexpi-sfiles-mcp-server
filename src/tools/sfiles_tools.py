"""SFILES2-based tools for BFD/PFD generation and manipulation."""

import json
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from mcp import Tool
from Flowsheet_Class.flowsheet import Flowsheet
import networkx as nx
from ..utils.response import success_response, error_response, validation_response, create_issue

logger = logging.getLogger(__name__)


class SfilesTools:
    """Handles all SFILES2-related MCP tools."""
    
    def __init__(self, flowsheet_store: Dict[str, Flowsheet], model_store: Dict[str, Any] = None):
        """Initialize with references to both stores."""
        self.flowsheets = flowsheet_store
        self.models = model_store if model_store is not None else {}
    
    def get_tools(self) -> List[Tool]:
        """Return all SFILES tools."""
        return [
            Tool(
                name="sfiles_create_flowsheet",
                description="Initialize a new flowsheet for BFD or PFD",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {
                            "type": "string", 
                            "enum": ["BFD", "PFD"],
                            "default": "PFD"
                        },
                        "description": {"type": "string", "default": ""}
                    },
                    "required": ["name"]
                }
            ),
            Tool(
                name="sfiles_add_unit",
                description="Add a unit operation to the flowsheet",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "flowsheet_id": {"type": "string"},
                        "unit_name": {"type": "string"},
                        "unit_type": {
                            "type": "string",
                            "description": "Unit type (e.g., reactor, distcol, hex, pump, etc.)"
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Unit-specific parameters"
                        }
                    },
                    "required": ["flowsheet_id", "unit_name", "unit_type"]
                }
            ),
            Tool(
                name="sfiles_add_stream",
                description="Add a stream connecting two units",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "flowsheet_id": {"type": "string"},
                        "from_unit": {"type": "string"},
                        "to_unit": {"type": "string"},
                        "stream_name": {"type": "string"},
                        "tags": {
                            "type": "object",
                            "properties": {
                                "he": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Heat exchanger tags"
                                },
                                "col": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Column tags"
                                }
                            },
                            "default": {"he": [], "col": []}
                        },
                        "properties": {
                            "type": "object",
                            "description": "Stream properties (flow, temperature, pressure, etc.)"
                        }
                    },
                    "required": ["flowsheet_id", "from_unit", "to_unit"]
                }
            ),
            Tool(
                name="sfiles_to_string",
                description="Convert flowsheet to compact SFILES string format",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "flowsheet_id": {"type": "string"},
                        "version": {
                            "type": "string", 
                            "enum": ["v1", "v2"],
                            "default": "v2",
                            "description": "SFILES version (v2 includes tags)"
                        },
                        "canonical": {
                            "type": "boolean",
                            "default": True,
                            "description": "Generate canonical (deterministic) representation"
                        }
                    },
                    "required": ["flowsheet_id"]
                }
            ),
            Tool(
                name="sfiles_from_string",
                description="Create flowsheet from SFILES string",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sfiles_string": {"type": "string"},
                        "flowsheet_id": {
                            "type": "string",
                            "description": "Optional ID for the created flowsheet"
                        }
                    },
                    "required": ["sfiles_string"]
                }
            ),
            Tool(
                name="sfiles_export_networkx",
                description="Export flowsheet as NetworkX graph JSON",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "flowsheet_id": {"type": "string"}
                    },
                    "required": ["flowsheet_id"]
                }
            ),
            Tool(
                name="sfiles_export_graphml",
                description="Export flowsheet topology as GraphML",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "flowsheet_id": {"type": "string"}
                    },
                    "required": ["flowsheet_id"]
                }
            ),
            Tool(
                name="sfiles_add_control",
                description="Add control instrumentation to flowsheet",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "flowsheet_id": {"type": "string"},
                        "control_type": {
                            "type": "string",
                            "enum": ["FC", "LC", "TC", "PC", "DO", "ORP", "pH"],
                            "description": "Control type (Flow, Level, Temperature, Pressure, Dissolved Oxygen, ORP, pH)"
                        },
                        "control_name": {"type": "string"},
                        "connected_unit": {"type": "string"},
                        "signal_to": {
                            "type": "string",
                            "description": "Optional target for control signal"
                        },
                        "attachment_target": {
                            "type": "object",
                            "description": "Optional rendering hint for control placement",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["unit", "stream"],
                                    "description": "Whether control is attached to a unit or stream"
                                },
                                "ref": {
                                    "type": "string",
                                    "description": "Unit ID or stream identifier for attachment"
                                }
                            },
                            "required": ["type", "ref"]
                        }
                    },
                    "required": ["flowsheet_id", "control_type", "control_name", "connected_unit"]
                }
            ),
            # Validation tools removed - now handled by unified ValidationTools:
            # - sfiles_validate_topology -> use validate_model(scope="topology")
            # - sfiles_validate_syntax -> use validate_model(scope="syntax")
            Tool(
                name="sfiles_parse_and_validate",
                description="Parse SFILES string and validate against regex patterns",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sfiles_string": {"type": "string"},
                        "return_tokens": {"type": "boolean", "default": False}
                    },
                    "required": ["sfiles_string"]
                }
            ),
            Tool(
                name="sfiles_canonical_form",
                description="Convert SFILES string to canonical form for comparison",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sfiles_string": {"type": "string"},
                        "version": {
                            "type": "string",
                            "enum": ["v1", "v2"],
                            "default": "v2"
                        }
                    },
                    "required": ["sfiles_string"]
                }
            ),
            Tool(
                name="sfiles_pattern_helper",
                description="Get SFILES regex patterns and syntax examples",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "include_examples": {"type": "boolean", "default": True}
                    }
                }
            ),
            # Project tools removed - now handled by unified ProjectTools
            Tool(
                name="sfiles_convert_from_dexpi",
                description="Convert DEXPI P&ID model to SFILES flowsheet",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string", "description": "ID of DEXPI model to convert"},
                        "flowsheet_id": {"type": "string", "description": "Optional ID for the created flowsheet"}
                    },
                    "required": ["model_id"]
                }
            )
        ]
    
    async def handle_tool(self, name: str, arguments: dict) -> dict:
        """Route tool call to appropriate handler."""
        handlers = {
            "sfiles_create_flowsheet": self._create_flowsheet,
            "sfiles_add_unit": self._add_unit,
            "sfiles_add_stream": self._add_stream,
            "sfiles_to_string": self._to_string,
            "sfiles_from_string": self._from_string,
            "sfiles_export_networkx": self._export_networkx,
            "sfiles_export_graphml": self._export_graphml,
            "sfiles_add_control": self._add_control,
            # Removed duplicate handlers - now handled by ValidationTools:
            # "sfiles_validate_topology": use validate_model
            # "sfiles_validate_syntax": use validate_model
            "sfiles_parse_and_validate": self._parse_and_validate,
            "sfiles_canonical_form": self._canonical_form,
            "sfiles_pattern_helper": self._pattern_helper,
            "sfiles_convert_from_dexpi": self._convert_from_dexpi,
            # Removed duplicate handlers:
            # - sfiles_init_project (now in ProjectTools)
            # - sfiles_save_to_project (now in ProjectTools)
            # - sfiles_load_from_project (now in ProjectTools)
            # - sfiles_list_project_models (now in ProjectTools)
        }
        
        handler = handlers.get(name)
        if not handler:
            raise ValueError(f"Unknown SFILES tool: {name}")
        
        return await handler(arguments)
    
    async def _create_flowsheet(self, args: dict) -> dict:
        """Create a new flowsheet."""
        flowsheet_id = str(uuid4())
        
        # Create new flowsheet
        flowsheet = Flowsheet()
        
        # Set metadata as attributes
        flowsheet.name = args["name"]
        flowsheet.type = args.get("type", "PFD")
        flowsheet.description = args.get("description", "")
        
        # The flowsheet's NetworkX graph is already initialized as self.state
        # We'll build it using add_unit() and add_stream() methods
        
        # Store flowsheet
        self.flowsheets[flowsheet_id] = flowsheet
        
        return success_response({
            "flowsheet_id": flowsheet_id,
            "name": args["name"],
            "type": args.get("type", "PFD")
        })
    
    async def _add_unit(self, args: dict) -> dict:
        """Add a unit operation to flowsheet using native graph methods."""
        flowsheet_id = args["flowsheet_id"]
        if flowsheet_id not in self.flowsheets:
            raise ValueError(f"Flowsheet {flowsheet_id} not found")
        
        flowsheet = self.flowsheets[flowsheet_id]
        unit_name = args["unit_name"]
        unit_type = args["unit_type"]
        parameters = args.get("parameters", {})
        
        # Generate unique name for the unit
        # Ensure all units have proper numbering for SFILES compatibility
        if not unit_name or unit_name == unit_type:
            # Count existing units of this type
            existing_units = [n for n in flowsheet.state.nodes if unit_type in n]
            unit_number = len(existing_units)
            unique_name = f"{unit_type}-{unit_number}"
        else:
            # Ensure the name has proper format with a number
            if '-' not in unit_name:
                # Add numbering if not present
                existing_units = [n for n in flowsheet.state.nodes if unit_name in n]
                unit_number = len(existing_units)
                unique_name = f"{unit_name}-{unit_number}"
            else:
                unique_name = unit_name
        
        # Add unit using native Flowsheet method
        # This properly adds it to the NetworkX graph
        flowsheet.add_unit(
            unique_name=unique_name,
            unit_type=unit_type,
            **parameters
        )
        
        return success_response({
            "flowsheet_id": flowsheet_id,
            "unit_name": unique_name,
            "unit_type": unit_type,
            "num_units": flowsheet.state.number_of_nodes()
        })
    
    async def _add_stream(self, args: dict) -> dict:
        """Add a stream between units using native graph methods.
        
        Supports splits (multiple streams from one unit) and 
        merges (multiple streams to one unit).
        """
        flowsheet_id = args["flowsheet_id"]
        if flowsheet_id not in self.flowsheets:
            raise ValueError(f"Flowsheet {flowsheet_id} not found")
        
        flowsheet = self.flowsheets[flowsheet_id]
        from_unit = args["from_unit"]
        to_unit = args["to_unit"]
        stream_name = args.get("stream_name", f"{from_unit}_to_{to_unit}")
        tags = args.get("tags", {"he": [], "col": []})
        properties = args.get("properties", {})
        
        # Ensure both units exist in the flowsheet
        if from_unit not in flowsheet.state.nodes:
            raise ValueError(f"Source unit {from_unit} not found in flowsheet")
        if to_unit not in flowsheet.state.nodes:
            raise ValueError(f"Target unit {to_unit} not found in flowsheet")
        
        # Add stream using native Flowsheet method
        # This properly adds an edge to the NetworkX graph
        flowsheet.add_stream(
            node1=from_unit,
            node2=to_unit,
            tags=tags,
            stream_name=stream_name,
            **properties
        )
        
        # Check if this creates a cycle (recycle)
        import networkx as nx
        if not nx.is_directed_acyclic_graph(flowsheet.state):
            # Mark this as a recycle stream
            cycles = list(nx.simple_cycles(flowsheet.state))
            is_recycle = any(from_unit in cycle and to_unit in cycle for cycle in cycles)
        else:
            is_recycle = False
        
        return success_response({
            "flowsheet_id": flowsheet_id,
            "stream_name": stream_name,
            "from": from_unit,
            "to": to_unit,
            "is_recycle": is_recycle,
            "num_streams": flowsheet.state.number_of_edges()
        })
    
    async def _to_string(self, args: dict) -> dict:
        """Convert flowsheet to SFILES string."""
        flowsheet_id = args["flowsheet_id"]
        if flowsheet_id not in self.flowsheets:
            raise ValueError(f"Flowsheet {flowsheet_id} not found")
        
        flowsheet = self.flowsheets[flowsheet_id]
        version = args.get("version", "v2")
        canonical = args.get("canonical", True)
        
        # Convert to SFILES string
        # convert_to_sfiles doesn't return anything - it sets flowsheet.sfiles attribute
        try:
            flowsheet.convert_to_sfiles(
                version=version,
                canonical=canonical
            )
            
            # Get the result from the flowsheet attributes
            sfiles_string = flowsheet.sfiles
            
            if not sfiles_string:
                raise ValueError("SFILES conversion failed - no output generated")
                
        except Exception as e:
            # Handle empty flowsheet case
            if flowsheet.state.number_of_nodes() == 0:
                raise ValueError("Cannot convert empty flowsheet to SFILES")
            raise ValueError(f"SFILES conversion failed: {str(e)}")
        
        return success_response({
            "flowsheet_id": flowsheet_id,
            "version": version,
            "sfiles": sfiles_string
        })
    
    async def _from_string(self, args: dict) -> dict:
        """Create flowsheet from SFILES string."""
        sfiles_string = args["sfiles_string"]
        flowsheet_id = args.get("flowsheet_id", str(uuid4()))
        
        # Create flowsheet from string
        flowsheet = Flowsheet()
        flowsheet.create_from_sfiles(sfiles_string)
        
        # Store flowsheet
        self.flowsheets[flowsheet_id] = flowsheet
        
        # Count units and streams
        num_units = flowsheet.state.number_of_nodes()
        num_streams = flowsheet.state.number_of_edges()
        
        return success_response({
            "flowsheet_id": flowsheet_id,
            "num_units": num_units,
            "num_streams": num_streams
        })
    
    async def _export_networkx(self, args: dict) -> dict:
        """Export flowsheet as NetworkX graph."""
        flowsheet_id = args["flowsheet_id"]
        if flowsheet_id not in self.flowsheets:
            raise ValueError(f"Flowsheet {flowsheet_id} not found")
        
        flowsheet = self.flowsheets[flowsheet_id]
        
        # Convert NetworkX graph to node-link format
        graph_data = nx.node_link_data(flowsheet.state)
        
        return success_response({
            "flowsheet_id": flowsheet_id,
            "graph": graph_data
        })
    
    async def _export_graphml(self, args: dict) -> dict:
        """Export flowsheet as GraphML."""
        flowsheet_id = args["flowsheet_id"]
        if flowsheet_id not in self.flowsheets:
            raise ValueError(f"Flowsheet {flowsheet_id} not found")
        
        flowsheet = self.flowsheets[flowsheet_id]
        
        # Use UnifiedGraphConverter which sanitizes dict values
        from ..converters.graph_converter import UnifiedGraphConverter
        converter = UnifiedGraphConverter()
        graphml_content = converter.sfiles_to_graphml(flowsheet)
        
        return success_response({
            "flowsheet_id": flowsheet_id,
            "graphml": graphml_content
        })
    
    async def _add_control(self, args: dict) -> dict:
        """Add control instrumentation using signal edges.
        
        Controls are added as separate units with signal connections
        to produce proper canonical SFILES with signal cycles.
        Attachment metadata is stored for render-time placement only.
        """
        flowsheet_id = args["flowsheet_id"]
        if flowsheet_id not in self.flowsheets:
            raise ValueError(f"Flowsheet {flowsheet_id} not found")
        
        flowsheet = self.flowsheets[flowsheet_id]
        control_type = args["control_type"]
        control_name = args["control_name"]
        connected_unit = args["connected_unit"]
        signal_to = args.get("signal_to")
        attachment_target = args.get("attachment_target")
        
        # Format control name according to SFILES2 convention
        # Use (C) as the control unit name for proper signal cycle notation
        # The control type will be stored as an attribute
        if "/" not in control_name:
            # Extract number from control_name if present
            import re
            num_match = re.search(r'\d+', control_name)
            num = num_match.group() if num_match else str(len([n for n in flowsheet.state.nodes if 'C' in n]) + 1)
            # For canonical SFILES, use simple (C) notation
            # The type is stored as metadata
            unique_name = f"C-{num}"
        else:
            # Parse existing format like C-1/FC
            parts = control_name.split('/')
            unique_name = parts[0]
        
        # Ensure connected unit exists
        if connected_unit not in flowsheet.state.nodes:
            raise ValueError(f"Connected unit {connected_unit} not found in flowsheet")
        
        # Validate attachment_target if provided
        if attachment_target:
            att_type = attachment_target.get("type")
            att_ref = attachment_target.get("ref")
            
            if att_type == "unit":
                if att_ref not in flowsheet.state.nodes:
                    raise ValueError(f"Attachment unit {att_ref} not found in flowsheet")
            elif att_type == "stream":
                # Stream can be referenced by name or as edge tuple
                # We'll store it as-is for render-time resolution
                pass
        
        # Add control as a unit with attachment metadata
        flowsheet.add_unit(
            unique_name=unique_name,
            unit_type="Control",
            control_type=control_type,
            attachment_target=attachment_target  # Store for render-time use
        )
        
        # Add signal edge from connected unit to control
        # This creates the measurement signal connection
        flowsheet.add_stream(
            node1=connected_unit,
            node2=unique_name,
            tags={"signal": ["not_next_unitop"], "he": [], "col": []},
            signal_type="measurement"
        )
        
        # If signal_to is specified, add actuation signal
        if signal_to:
            if signal_to not in flowsheet.state.nodes:
                raise ValueError(f"Signal target unit {signal_to} not found in flowsheet")
            
            # Add actuation signal from control to target
            flowsheet.add_stream(
                node1=unique_name,
                node2=signal_to,
                tags={"signal": ["not_next_unitop"], "he": [], "col": []},
                signal_type="actuation"
            )
        
        return success_response({
            "flowsheet_id": flowsheet_id,
            "control_name": unique_name,
            "control_type": control_type,
            "connected_unit": connected_unit,
            "signal_to": signal_to,
            "attachment_target": attachment_target,
            "num_units": flowsheet.state.number_of_nodes(),
            "num_edges": flowsheet.state.number_of_edges()
        })
    
    async def _validate_topology(self, args: dict) -> dict:
        """Validate flowsheet topology."""
        flowsheet_id = args["flowsheet_id"]
        if flowsheet_id not in self.flowsheets:
            raise ValueError(f"Flowsheet {flowsheet_id} not found")
        
        flowsheet = self.flowsheets[flowsheet_id]
        graph = flowsheet.state
        
        issues = []
        
        # Check for disconnected components
        if not nx.is_weakly_connected(graph):
            num_components = nx.number_weakly_connected_components(graph)
            issues.append(f"Graph has {num_components} disconnected components")
        
        # Check for nodes with no connections
        isolated_nodes = list(nx.isolates(graph))
        if isolated_nodes:
            issues.append(f"Isolated units: {isolated_nodes}")
        
        # Check for cycles
        if nx.is_directed_acyclic_graph(graph):
            has_cycles = False
        else:
            has_cycles = True
            cycles = list(nx.simple_cycles(graph))
            if cycles:
                issues.append(f"Contains {len(cycles)} cycles")
        
        # Count statistics
        stats = {
            "num_units": graph.number_of_nodes(),
            "num_streams": graph.number_of_edges(),
            "is_connected": nx.is_weakly_connected(graph),
            "has_cycles": has_cycles
        }
        
        return {
            "status": "success" if not issues else "warning",
            "flowsheet_id": flowsheet_id,
            "issues": issues,
            "statistics": stats
        }
    
    async def _validate_syntax(self, args: dict) -> dict:
        """Validate SFILES syntax using round-trip conversion."""
        sfiles_string = args["sfiles_string"]
        version = args.get("version", "v2")
        
        try:
            # Parse SFILES string into flowsheet
            flowsheet = Flowsheet()
            flowsheet.create_from_sfiles(sfiles_string)
            
            # Convert back to SFILES (canonical form)
            result = flowsheet.convert_to_sfiles(version=version, canonical=True)
            
            # Handle different return types
            if isinstance(result, tuple) and len(result) >= 2:
                _, regenerated_sfiles = result
            elif isinstance(result, str):
                regenerated_sfiles = result
            else:
                raise ValueError(f"Unexpected result from convert_to_sfiles: {type(result)}")
            
            # Also parse original to canonical for comparison
            original_flowsheet = Flowsheet()
            original_flowsheet.create_from_sfiles(sfiles_string)
            original_result = original_flowsheet.convert_to_sfiles(version=version, canonical=True)
            if isinstance(original_result, tuple) and len(original_result) >= 2:
                _, canonical_original = original_result
            elif isinstance(original_result, str):
                canonical_original = original_result
            else:
                canonical_original = sfiles_string
            
            # Compare canonical forms
            is_valid = (canonical_original == regenerated_sfiles)
            
            return {
                "status": "success",
                "valid": is_valid,
                "original": sfiles_string,
                "canonical_original": canonical_original,
                "regenerated": regenerated_sfiles,
                "matches": is_valid,
                "num_units": flowsheet.state.number_of_nodes(),
                "num_streams": flowsheet.state.number_of_edges()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "valid": False,
                "error": str(e),
                "original": sfiles_string
            }
    
    async def _parse_and_validate(self, args: dict) -> dict:
        """Parse SFILES string and validate against regex patterns."""
        sfiles_string = args["sfiles_string"]
        return_tokens = args.get("return_tokens", False)
        
        try:
            # Create flowsheet to access parser
            flowsheet = Flowsheet()
            
            # SFILES_parser expects the string to be in self.sfiles
            flowsheet.sfiles = sfiles_string
            
            # Parse using SFILES_parser (takes no arguments)
            tokens = flowsheet.SFILES_parser()
            
            # Analyze tokens
            token_analysis = {
                "units": [],
                "tags": [],
                "cycles": [],
                "branches": [],
                "operators": []
            }
            
            import re
            unit_pattern = re.compile(r'^\(.+?\)$')
            tag_pattern = re.compile(r'^\{.+?\}$')
            cycle_pattern = re.compile(r'^[<%_]+\d+$')
            branch_pattern = re.compile(r'^\[|\]$')
            
            for token in tokens:
                if unit_pattern.match(token):
                    token_analysis["units"].append(token)
                elif tag_pattern.match(token):
                    token_analysis["tags"].append(token)
                elif cycle_pattern.match(token) or token.isdigit():
                    token_analysis["cycles"].append(token)
                elif branch_pattern.match(token):
                    token_analysis["branches"].append(token)
                else:
                    token_analysis["operators"].append(token)
            
            result = {
                "status": "success",
                "valid": True,
                "num_tokens": len(tokens),
                "token_analysis": token_analysis,
                "summary": {
                    "num_units": len(token_analysis["units"]),
                    "num_tags": len(token_analysis["tags"]),
                    "num_cycles": len(token_analysis["cycles"]) // 2,  # Cycles come in pairs
                    "num_branches": len(token_analysis["branches"]) // 2,  # Branches have open/close
                    "num_operators": len(token_analysis["operators"])
                }
            }
            
            if return_tokens:
                result["tokens"] = tokens
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "valid": False,
                "error": str(e),
                "message": "Failed to parse SFILES string"
            }
    
    async def _canonical_form(self, args: dict) -> dict:
        """Convert SFILES string to canonical form."""
        sfiles_string = args["sfiles_string"]
        version = args.get("version", "v2")
        
        try:
            # Create flowsheet and convert to canonical
            flowsheet = Flowsheet()
            flowsheet.create_from_sfiles(sfiles_string)
            
            # Check if the state was populated
            if not flowsheet.state or flowsheet.state.number_of_nodes() == 0:
                logger.warning(f"Flowsheet state is empty after create_from_sfiles. Input: {sfiles_string}")
                return error_response(f"Failed to parse SFILES string - no nodes created", code="CANONICAL_ERROR")
            
            # convert_to_sfiles doesn't return anything - it sets flowsheet.sfiles
            flowsheet.convert_to_sfiles(version=version, canonical=True)
            
            # Access the canonical SFILES string from the flowsheet attribute
            canonical_sfiles = flowsheet.sfiles
            
            if not canonical_sfiles:
                # Log more details for debugging
                logger.warning(f"Failed to generate canonical SFILES. State nodes: {flowsheet.state.number_of_nodes()}, edges: {flowsheet.state.number_of_edges()}")
                return error_response("Failed to generate canonical SFILES string", code="CANONICAL_ERROR")
            
            # Get the parsed list for element count
            sfiles_list = getattr(flowsheet, 'sfiles_list', [])
            
            return success_response({
                "original": sfiles_string,
                "canonical": canonical_sfiles,
                "version": version,
                "num_elements": len(sfiles_list) if sfiles_list else 0
            })
            
        except Exception as e:
            logger.error(f"Error in canonical_form: {e}")
            return error_response(f"Failed to generate canonical form: {str(e)}", code="CANONICAL_ERROR")
    
    async def _pattern_helper(self, args: dict) -> dict:
        """Provide SFILES regex patterns and examples."""
        include_examples = args.get("include_examples", True)
        
        # The actual regex pattern used in SFILES_parser
        sfiles_regex = r'(\(.+?\)|\{.+?\}|[<%_]+\d+|\]|\[|\<\&\||(?<!<)&\||n\||(?<!&)(?<!n)\||&(?!\|)|\d)'
        
        patterns = {
            "main_pattern": sfiles_regex,
            "element_patterns": {
                "unit": r'(\(.+?\))',
                "tag": r'(\{.+?\})',
                "cycle": r'([<%_]+\d+)',
                "branch": r'(\]|\[)',
                "operators": {
                    "incoming_branch": r'\<\&\|',
                    "ampersand_pipe": r'(?<!<)&\|',
                    "independent_flowsheet": r'n\|',
                    "pipe": r'(?<!&)(?<!n)\|',
                    "ampersand": r'&(?!\|)',
                    "digit": r'\d'
                }
            }
        }
        
        result = {
            "status": "success",
            "patterns": patterns,
            "description": {
                "units": "Unit operations enclosed in parentheses, e.g., (reactor-0)",
                "tags": "Metadata tags in curly braces, e.g., {hot_in}, {1}",
                "cycles": "Recycle notation with < and digits, e.g., <1 and 1",
                "branches": "Branch structures with square brackets []",
                "operators": "Various SFILES operators for connectivity"
            }
        }
        
        if include_examples:
            result["examples"] = {
                "simple_linear": "(feed)(reactor-0)(distcol-0)(product)",
                "with_recycle": "(feed)(reactor-0)<1(distcol-0)1(product)",
                "with_branch": "(feed)[(reactor-0)](distcol-0)(product)",
                "with_tags_v2": "(feed){1}(hex-0){hot_in}(reactor-0){tout}(product)",
                "complex": "(feed)[(mixer-0)<1(reactor-0)](separator-0)[(product-1)]1(product-2)",
                "heat_integration": "(feed){1}(hex-0){2}(reactor-0){3}(hex-1){4}(product){he:1,3}{he:2,4}",
                "control_loop": "(tank-0){PID}(valve-0){PID}(reactor-0)"
            }
            
            result["syntax_rules"] = [
                "Units must be in parentheses: (unit-name)",
                "Tags must be in curly braces: {tag-name}",
                "Cycles use matching numbers: <1 ... 1",
                "Branches use square brackets: [...] for parallel paths",
                "Heat exchanger pairing: {he:tag1,tag2}",
                "Column pairing: {col:tag1,tag2}",
                "Control loops: {PID} or {signal-name}"
            ]
        
        return result
    
    async def _init_project(self, args: dict) -> dict:
        """Initialize a new git project for storing models."""
        from ..persistence import ProjectPersistence
        
        persistence = ProjectPersistence()
        metadata = persistence.init_project(
            args["project_path"],
            args["project_name"],
            args.get("description", "")
        )
        
        return {
            "status": "success",
            "project_metadata": metadata,
            "project_path": args["project_path"]
        }
    
    async def _save_to_project(self, args: dict) -> dict:
        """Save SFILES flowsheet to a git project."""
        from ..persistence import ProjectPersistence
        
        flowsheet_id = args["flowsheet_id"]
        if flowsheet_id not in self.flowsheets:
            raise ValueError(f"Flowsheet {flowsheet_id} not found")
        
        flowsheet = self.flowsheets[flowsheet_id]
        persistence = ProjectPersistence()
        
        saved_paths = persistence.save_sfiles(
            flowsheet,
            args["project_path"],
            args["flowsheet_name"],
            args.get("commit_message")
        )
        
        return {
            "status": "success",
            "saved_paths": saved_paths,
            "flowsheet_id": flowsheet_id
        }
    
    async def _load_from_project(self, args: dict) -> dict:
        """Load SFILES flowsheet from a git project."""
        from ..persistence import ProjectPersistence
        
        persistence = ProjectPersistence()
        flowsheet = persistence.load_sfiles(
            args["project_path"],
            args["flowsheet_name"]
        )
        
        # Assign a new ID for the loaded flowsheet
        flowsheet_id = args.get("flowsheet_id", f"loaded_{args['flowsheet_name']}")
        self.flowsheets[flowsheet_id] = flowsheet
        
        return {
            "status": "success",
            "flowsheet_id": flowsheet_id,
            "num_nodes": flowsheet.state.number_of_nodes(),
            "num_edges": flowsheet.state.number_of_edges()
        }
    
    async def _list_project_models(self, args: dict) -> dict:
        """List all models in a project."""
        from ..persistence import ProjectPersistence
        
        persistence = ProjectPersistence()
        models = persistence.list_models(args["project_path"])
        
        return {
            "status": "success",
            "models": models
        }
    
    async def _convert_from_dexpi(self, args: dict) -> dict:
        """Convert DEXPI P&ID model to SFILES flowsheet."""
        try:
            from ..converters.sfiles_dexpi_mapper import SfilesDexpiMapper
        except ImportError:
            from converters.sfiles_dexpi_mapper import SfilesDexpiMapper
        
        model_id = args["model_id"]
        flowsheet_id = args.get("flowsheet_id", None)
        
        # Use the model store from instance
        if model_id not in self.models:
            return {
                "status": "error",
                "error": f"Model {model_id} not found"
            }
        
        dexpi_model = self.models[model_id]
        
        # Convert to SFILES
        mapper = SfilesDexpiMapper()
        try:
            flowsheet = mapper.dexpi_to_sfiles(dexpi_model)
            
            # Store the flowsheet
            if not flowsheet_id:
                import uuid
                flowsheet_id = str(uuid.uuid4())
            
            self.flowsheets[flowsheet_id] = flowsheet
            
            # Generate SFILES string
            flowsheet.convert_to_sfiles(version="v2", canonical=True)
            
            return {
                "status": "success",
                "flowsheet_id": flowsheet_id,
                "model_id": model_id,
                "sfiles": flowsheet.sfiles,
                "unit_count": flowsheet.state.number_of_nodes(),
                "stream_count": flowsheet.state.number_of_edges()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Conversion failed: {str(e)}"
            }
