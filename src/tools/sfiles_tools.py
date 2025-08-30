"""SFILES2-based tools for BFD/PFD generation and manipulation."""

import json
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from mcp import Tool
from Flowsheet_Class.flowsheet import Flowsheet
import networkx as nx

logger = logging.getLogger(__name__)


class SfilesTools:
    """Handles all SFILES2-related MCP tools."""
    
    def __init__(self, flowsheet_store: Dict[str, Flowsheet]):
        """Initialize with a reference to the flowsheet store."""
        self.flowsheets = flowsheet_store
    
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
                            "enum": ["FC", "LC", "TC", "PC"],
                            "description": "Control type (Flow, Level, Temperature, Pressure)"
                        },
                        "control_name": {"type": "string"},
                        "connected_unit": {"type": "string"},
                        "signal_to": {
                            "type": "string",
                            "description": "Optional target for control signal"
                        }
                    },
                    "required": ["flowsheet_id", "control_type", "control_name", "connected_unit"]
                }
            ),
            Tool(
                name="sfiles_validate_topology",
                description="Validate flowsheet topology and connectivity",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "flowsheet_id": {"type": "string"}
                    },
                    "required": ["flowsheet_id"]
                }
            ),
            Tool(
                name="sfiles_validate_syntax",
                description="Validate SFILES syntax using round-trip conversion",
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
            Tool(
                name="sfiles_init_project",
                description="Initialize a new git project for storing DEXPI and SFILES models",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string", "description": "Path where project should be created"},
                        "project_name": {"type": "string", "description": "Name of the project"},
                        "description": {"type": "string", "description": "Optional project description", "default": ""}
                    },
                    "required": ["project_path", "project_name"]
                }
            ),
            Tool(
                name="sfiles_save_to_project",
                description="Save SFILES flowsheet to a git project with version control",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "flowsheet_id": {"type": "string", "description": "Flowsheet ID to save"},
                        "project_path": {"type": "string", "description": "Path to project root"},
                        "flowsheet_name": {"type": "string", "description": "Name for saved flowsheet (without extension)"},
                        "commit_message": {"type": "string", "description": "Optional git commit message"}
                    },
                    "required": ["flowsheet_id", "project_path", "flowsheet_name"]
                }
            ),
            Tool(
                name="sfiles_load_from_project",
                description="Load SFILES flowsheet from a git project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string", "description": "Path to project root"},
                        "flowsheet_name": {"type": "string", "description": "Name of flowsheet to load (without extension)"},
                        "flowsheet_id": {"type": "string", "description": "Optional ID for loaded flowsheet"}
                    },
                    "required": ["project_path", "flowsheet_name"]
                }
            ),
            Tool(
                name="sfiles_list_project_models",
                description="List all DEXPI and SFILES models in a project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string", "description": "Path to project root"}
                    },
                    "required": ["project_path"]
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
            "sfiles_validate_topology": self._validate_topology,
            "sfiles_validate_syntax": self._validate_syntax,
            "sfiles_parse_and_validate": self._parse_and_validate,
            "sfiles_canonical_form": self._canonical_form,
            "sfiles_pattern_helper": self._pattern_helper,
            "sfiles_init_project": self._init_project,
            "sfiles_save_to_project": self._save_to_project,
            "sfiles_load_from_project": self._load_from_project,
            "sfiles_list_project_models": self._list_project_models,
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
        
        # Store flowsheet
        self.flowsheets[flowsheet_id] = flowsheet
        
        return {
            "status": "success",
            "flowsheet_id": flowsheet_id,
            "name": args["name"],
            "type": args.get("type", "PFD")
        }
    
    async def _add_unit(self, args: dict) -> dict:
        """Add a unit operation to flowsheet."""
        flowsheet_id = args["flowsheet_id"]
        if flowsheet_id not in self.flowsheets:
            raise ValueError(f"Flowsheet {flowsheet_id} not found")
        
        flowsheet = self.flowsheets[flowsheet_id]
        unit_name = args["unit_name"]
        unit_type = args["unit_type"]
        parameters = args.get("parameters", {})
        
        # Ensure unit name follows SFILES2 convention (type-number format)
        # ALL units must have the format [TYPE]-[NUMBER] for SFILES2 sorting to work
        if '-' not in unit_name and '/' not in unit_name:
            # Count existing units of this type
            existing_units = [n for n in flowsheet.state.nodes() if n.startswith(unit_type)]
            unit_number = len(existing_units)
            # Use the unit_type as base, even for feed/product
            formatted_name = f"{unit_type}-{unit_number}"
        else:
            # Already has the right format
            formatted_name = unit_name
        
        # Add unit with parameters
        # Flowsheet.add_unit takes unique_name and kwargs
        # unit_type must be passed as a kwarg
        unit_kwargs = {"unit_type": unit_type}
        unit_kwargs.update(parameters)
        
        flowsheet.add_unit(
            unique_name=formatted_name,
            **unit_kwargs
        )
        
        return {
            "status": "success",
            "flowsheet_id": flowsheet_id,
            "unit_name": formatted_name,  # Return the actual name used
            "unit_type": unit_type
        }
    
    async def _add_stream(self, args: dict) -> dict:
        """Add a stream between units."""
        flowsheet_id = args["flowsheet_id"]
        if flowsheet_id not in self.flowsheets:
            raise ValueError(f"Flowsheet {flowsheet_id} not found")
        
        flowsheet = self.flowsheets[flowsheet_id]
        from_unit = args["from_unit"]
        to_unit = args["to_unit"]
        stream_name = args.get("stream_name", f"{from_unit}_to_{to_unit}")
        tags = args.get("tags", {})
        properties = args.get("properties", {})
        
        # Ensure tags always has 'he' and 'col' keys (SFILES2 requirement)
        if 'he' not in tags:
            tags['he'] = []
        if 'col' not in tags:
            tags['col'] = []
        
        # Add stream with tags and properties
        flowsheet.add_stream(
            node1=from_unit,
            node2=to_unit,
            tags=tags,
            stream_name=stream_name,
            **properties
        )
        
        return {
            "status": "success",
            "flowsheet_id": flowsheet_id,
            "stream_name": stream_name,
            "from": from_unit,
            "to": to_unit
        }
    
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
        
        return {
            "status": "success",
            "flowsheet_id": flowsheet_id,
            "version": version,
            "sfiles": sfiles_string
        }
    
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
        
        return {
            "status": "success",
            "flowsheet_id": flowsheet_id,
            "num_units": num_units,
            "num_streams": num_streams
        }
    
    async def _export_networkx(self, args: dict) -> dict:
        """Export flowsheet as NetworkX graph."""
        flowsheet_id = args["flowsheet_id"]
        if flowsheet_id not in self.flowsheets:
            raise ValueError(f"Flowsheet {flowsheet_id} not found")
        
        flowsheet = self.flowsheets[flowsheet_id]
        
        # Convert NetworkX graph to node-link format
        graph_data = nx.node_link_data(flowsheet.state)
        
        return {
            "status": "success",
            "flowsheet_id": flowsheet_id,
            "graph": graph_data
        }
    
    async def _export_graphml(self, args: dict) -> dict:
        """Export flowsheet as GraphML."""
        flowsheet_id = args["flowsheet_id"]
        if flowsheet_id not in self.flowsheets:
            raise ValueError(f"Flowsheet {flowsheet_id} not found")
        
        flowsheet = self.flowsheets[flowsheet_id]
        
        # Convert to GraphML
        from io import StringIO
        graphml_buffer = StringIO()
        nx.write_graphml(flowsheet.state, graphml_buffer)
        graphml_content = graphml_buffer.getvalue()
        
        return {
            "status": "success",
            "flowsheet_id": flowsheet_id,
            "graphml": graphml_content
        }
    
    async def _add_control(self, args: dict) -> dict:
        """Add control instrumentation."""
        flowsheet_id = args["flowsheet_id"]
        if flowsheet_id not in self.flowsheets:
            raise ValueError(f"Flowsheet {flowsheet_id} not found")
        
        flowsheet = self.flowsheets[flowsheet_id]
        control_type = args["control_type"]
        control_name = args["control_name"]
        connected_unit = args["connected_unit"]
        signal_to = args.get("signal_to")
        
        # Add control as a unit
        flowsheet.add_unit(
            unique_name=control_name,
            unit_type="Control",
            control_type=control_type
        )
        
        # Add measurement connection
        flowsheet.add_stream(
            node1=connected_unit,
            node2=control_name,
            tags={"signal": True},
            stream_type="measurement"
        )
        
        # Add control signal if specified
        if signal_to:
            flowsheet.add_stream(
                node1=control_name,
                node2=signal_to,
                tags={"signal": True, "not_next_unitop": True},
                stream_type="control"
            )
        
        return {
            "status": "success",
            "flowsheet_id": flowsheet_id,
            "control_name": control_name,
            "control_type": control_type,
            "connected_unit": connected_unit
        }
    
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
            result = flowsheet.convert_to_sfiles(version=version, canonical=True)
            
            # Handle different return types
            if isinstance(result, tuple) and len(result) >= 2:
                sfiles_list, canonical_sfiles = result
            elif isinstance(result, str):
                canonical_sfiles = result
                sfiles_list = flowsheet.SFILES_parser(sfiles_string)
            else:
                raise ValueError(f"Unexpected result from convert_to_sfiles")
            
            return {
                "status": "success",
                "original": sfiles_string,
                "canonical": canonical_sfiles,
                "version": version,
                "num_elements": len(sfiles_list) if sfiles_list else 0
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "original": sfiles_string
            }
    
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
