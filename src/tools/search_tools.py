"""Search and query tools for engineering models."""

import logging
import re
from typing import Any, Dict, List, Optional, Union
from fuzzywuzzy import fuzz
import networkx as nx

from mcp import Tool
from ..utils.response import success_response, error_response

# Import native pyDEXPI capabilities for attribute extraction
try:
    from pydexpi.loaders.ml_graph_loader import MLGraphLoader
    from pydexpi.loaders.utils import get_data_attributes
except ImportError:
    MLGraphLoader = None
    get_data_attributes = None

logger = logging.getLogger(__name__)


class SearchTools:
    """Provides search and query capabilities for engineering models."""
    
    def __init__(self, dexpi_models: Dict[str, Any], flowsheets: Dict[str, Any]):
        """Initialize with model stores."""
        self.dexpi_models = dexpi_models
        self.flowsheets = flowsheets
        # Use native pyDEXPI loader if available for better attribute extraction
        self.ml_loader = MLGraphLoader() if MLGraphLoader else None
    
    def get_tools(self) -> List[Tool]:
        """Return search and query tools."""
        return [
            Tool(
                name="search_by_tag",
                description="[DEPRECATED] Search for equipment, instruments, or nodes by tag pattern. Use search_execute(query_type='by_tag') instead.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tag_pattern": {
                            "type": "string",
                            "description": "Tag pattern to search (supports wildcards: * and regex)"
                        },
                        "model_id": {
                            "type": "string",
                            "description": "Specific model to search in (optional)"
                        },
                        "search_scope": {
                            "type": "string",
                            "enum": ["all", "equipment", "instrumentation", "piping"],
                            "description": "Scope of search",
                            "default": "all"
                        },
                        "fuzzy": {
                            "type": "boolean",
                            "description": "Enable fuzzy matching",
                            "default": False
                        }
                    },
                    "required": ["tag_pattern"]
                }
            ),
            Tool(
                name="search_by_type",
                description="[DEPRECATED] Search for components by type (e.g., all pumps, all heat exchangers). Use search_execute(query_type='by_type') instead.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "component_type": {
                            "type": "string",
                            "description": "Type of component to search for"
                        },
                        "model_id": {
                            "type": "string",
                            "description": "Specific model to search in (optional)"
                        },
                        "include_subtypes": {
                            "type": "boolean",
                            "description": "Include subtypes in search",
                            "default": True
                        }
                    },
                    "required": ["component_type"]
                }
            ),
            Tool(
                name="search_by_attributes",
                description="[DEPRECATED] Search for components by attribute values. Use search_execute(query_type='by_attributes') instead.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "attributes": {
                            "type": "object",
                            "description": "Attribute key-value pairs to match"
                        },
                        "model_id": {
                            "type": "string",
                            "description": "Specific model to search in (optional)"
                        },
                        "match_type": {
                            "type": "string",
                            "enum": ["exact", "partial", "regex"],
                            "description": "How to match attribute values",
                            "default": "exact"
                        }
                    },
                    "required": ["attributes"]
                }
            ),
            Tool(
                name="search_connected",
                description="[DEPRECATED] Find all components connected to a specific node. Use search_execute(query_type='connected') instead.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "node_id": {
                            "type": "string",
                            "description": "Node ID or tag to search from"
                        },
                        "model_id": {
                            "type": "string",
                            "description": "Model ID"
                        },
                        "direction": {
                            "type": "string",
                            "enum": ["upstream", "downstream", "both"],
                            "description": "Direction to search",
                            "default": "both"
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum depth to search",
                            "default": 3
                        }
                    },
                    "required": ["node_id", "model_id"]
                }
            ),
            Tool(
                name="query_model_statistics",
                description="[DEPRECATED] Get statistical summary of model contents. Use search_execute(query_type='statistics') instead.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {
                            "type": "string",
                            "description": "Model ID to query (optional - queries all if not specified)"
                        },
                        "group_by": {
                            "type": "string",
                            "enum": ["type", "tag_prefix", "connection_count"],
                            "description": "How to group statistics",
                            "default": "type"
                        }
                    }
                }
            ),
            Tool(
                name="search_by_stream",
                description="[DEPRECATED] Search for streams by properties or connected units. Use search_execute(query_type='by_stream') instead.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "stream_name": {
                            "type": "string",
                            "description": "Stream name or pattern (optional)"
                        },
                        "from_unit": {
                            "type": "string",
                            "description": "Source unit tag (optional)"
                        },
                        "to_unit": {
                            "type": "string",
                            "description": "Target unit tag (optional)"
                        },
                        "properties": {
                            "type": "object",
                            "description": "Stream properties to match (optional)"
                        },
                        "model_id": {
                            "type": "string",
                            "description": "Specific model to search in (optional)"
                        }
                    }
                }
            ),
            Tool(
                name="search_execute",
                description="Unified search tool - consolidates all search_* operations",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query_type": {
                            "type": "string",
                            "enum": ["by_tag", "by_type", "by_attributes", "connected", "statistics", "by_stream"],
                            "description": "Type of search query to execute"
                        },
                        "tag_pattern": {
                            "type": "string",
                            "description": "Tag pattern (for by_tag query)"
                        },
                        "component_type": {
                            "type": "string",
                            "description": "Component type (for by_type query)"
                        },
                        "attributes": {
                            "type": "object",
                            "description": "Attribute key-value pairs (for by_attributes query)"
                        },
                        "node_id": {
                            "type": "string",
                            "description": "Node ID or tag (for connected query)"
                        },
                        "stream_name": {
                            "type": "string",
                            "description": "Stream name or pattern (for by_stream query)"
                        },
                        "from_unit": {
                            "type": "string",
                            "description": "Source unit tag (for by_stream query)"
                        },
                        "to_unit": {
                            "type": "string",
                            "description": "Target unit tag (for by_stream query)"
                        },
                        "properties": {
                            "type": "object",
                            "description": "Stream properties (for by_stream query)"
                        },
                        "model_id": {
                            "type": "string",
                            "description": "Model ID to search in (optional for most queries)"
                        },
                        "search_scope": {
                            "type": "string",
                            "enum": ["all", "equipment", "instrumentation", "piping"],
                            "description": "Search scope (for by_tag query)",
                            "default": "all"
                        },
                        "fuzzy": {
                            "type": "boolean",
                            "description": "Enable fuzzy matching (for by_tag query)",
                            "default": False
                        },
                        "include_subtypes": {
                            "type": "boolean",
                            "description": "Include subtypes (for by_type query)",
                            "default": True
                        },
                        "match_type": {
                            "type": "string",
                            "enum": ["exact", "partial", "regex"],
                            "description": "Attribute matching mode (for by_attributes query)",
                            "default": "exact"
                        },
                        "direction": {
                            "type": "string",
                            "enum": ["upstream", "downstream", "both"],
                            "description": "Search direction (for connected query)",
                            "default": "both"
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum search depth (for connected query)",
                            "default": 3
                        },
                        "group_by": {
                            "type": "string",
                            "enum": ["type", "tag_prefix", "connection_count"],
                            "description": "Grouping method (for statistics query)",
                            "default": "type"
                        }
                    },
                    "required": ["query_type"]
                }
            )
        ]

    async def handle_tool(self, name: str, arguments: dict) -> dict:
        """Route tool call to appropriate handler."""
        handlers = {
            "search_by_tag": self._search_by_tag,
            "search_by_type": self._search_by_type,
            "search_by_attributes": self._search_by_attributes,
            "search_connected": self._search_connected,
            "query_model_statistics": self._query_statistics,
            "search_by_stream": self._search_by_stream,
            "search_execute": self._unified_search
        }
        
        handler = handlers.get(name)
        if not handler:
            return error_response(f"Unknown search tool: {name}", code="UNKNOWN_TOOL")
        
        try:
            return await handler(arguments)
        except Exception as e:
            logger.error(f"Error in {name}: {e}")
            return error_response(str(e), code="TOOL_ERROR")
    
    async def _search_by_tag(self, args: dict) -> dict:
        """Search by tag pattern."""
        tag_pattern = args["tag_pattern"]
        model_id = args.get("model_id")
        search_scope = args.get("search_scope", "all")
        fuzzy = args.get("fuzzy", False)
        
        results = []
        
        # Convert wildcard to regex if needed
        if '*' in tag_pattern and not fuzzy:
            tag_pattern = tag_pattern.replace('*', '.*')
            pattern = re.compile(tag_pattern, re.IGNORECASE)
        else:
            pattern = None
        
        # Search in DEXPI models
        models_to_search = {}
        if model_id:
            if model_id in self.dexpi_models:
                models_to_search[model_id] = self.dexpi_models[model_id]
            elif model_id in self.flowsheets:
                # Handle SFILES separately
                pass
            else:
                return error_response(f"Model {model_id} not found", code="MODEL_NOT_FOUND")
        else:
            models_to_search = self.dexpi_models
        
        for mid, model in models_to_search.items():
            model_results = self._search_dexpi_model(
                model, tag_pattern, pattern, search_scope, fuzzy
            )
            for result in model_results:
                result["model_id"] = mid
                results.append(result)
        
        # Search in SFILES flowsheets
        flowsheets_to_search = {}
        if model_id and model_id in self.flowsheets:
            flowsheets_to_search[model_id] = self.flowsheets[model_id]
        elif not model_id:
            flowsheets_to_search = self.flowsheets
        
        for fid, flowsheet in flowsheets_to_search.items():
            flowsheet_results = self._search_flowsheet(
                flowsheet, tag_pattern, pattern, fuzzy
            )
            for result in flowsheet_results:
                result["model_id"] = fid
                results.append(result)
        
        return success_response({
            "query": tag_pattern,
            "result_count": len(results),
            "results": results[:100]  # Limit results
        })
    
    async def _search_by_type(self, args: dict) -> dict:
        """Search by component type."""
        component_type = args["component_type"].lower()
        model_id = args.get("model_id")
        include_subtypes = args.get("include_subtypes", True)
        
        results = []
        
        # Search DEXPI models
        models_to_search = {}
        if model_id:
            if model_id in self.dexpi_models:
                models_to_search[model_id] = self.dexpi_models[model_id]
        else:
            models_to_search = self.dexpi_models
        
        for mid, model in models_to_search.items():
            if model.conceptualModel and model.conceptualModel.taggedPlantItems:
                for item in model.conceptualModel.taggedPlantItems:
                    item_type = item.__class__.__name__.lower()
                    
                    if include_subtypes:
                        if component_type in item_type or item_type in component_type:
                            results.append({
                                "model_id": mid,
                                "tag": getattr(item, 'tagName', 'Unknown'),
                                "type": item.__class__.__name__,
                                "model_type": "dexpi"
                            })
                    else:
                        if item_type == component_type:
                            results.append({
                                "model_id": mid,
                                "tag": getattr(item, 'tagName', 'Unknown'),
                                "type": item.__class__.__name__,
                                "model_type": "dexpi"
                            })
        
        # Search SFILES flowsheets
        flowsheets_to_search = {}
        if model_id:
            if model_id in self.flowsheets:
                flowsheets_to_search[model_id] = self.flowsheets[model_id]
        else:
            flowsheets_to_search = self.flowsheets
        
        for fid, flowsheet in flowsheets_to_search.items():
            for node, data in flowsheet.state.nodes(data=True):
                # SFILES uses 'unit_type' not 'type'
                node_type = data.get('unit_type', '').lower()
                
                if include_subtypes:
                    # Only check if component_type is in node_type (not vice versa)
                    # Also ensure node_type is not empty
                    if node_type and component_type in node_type:
                        results.append({
                            "model_id": fid,
                            "node": node,
                            "type": data.get('unit_type', 'Unknown'),
                            "model_type": "sfiles"
                        })
                else:
                    if node_type == component_type:
                        results.append({
                            "model_id": fid,
                            "node": node,
                            "type": data.get('unit_type', 'Unknown'),
                            "model_type": "sfiles"
                        })
        
        return success_response({
            "component_type": args["component_type"],
            "result_count": len(results),
            "results": results[:100]
        })
    
    async def _search_by_attributes(self, args: dict) -> dict:
        """Search by attribute values."""
        attributes = args["attributes"]
        model_id = args.get("model_id")
        match_type = args.get("match_type", "exact")
        
        results = []
        
        # Search all models if not specified
        if model_id:
            if model_id in self.flowsheets:
                flowsheet = self.flowsheets[model_id]
                results.extend(self._search_flowsheet_attributes(
                    flowsheet, attributes, match_type, model_id
                ))
            elif model_id in self.dexpi_models:
                model = self.dexpi_models[model_id]
                results.extend(self._search_dexpi_attributes(
                    model, attributes, match_type, model_id
                ))
        else:
            # Search all models
            for fid, flowsheet in self.flowsheets.items():
                results.extend(self._search_flowsheet_attributes(
                    flowsheet, attributes, match_type, fid
                ))
            
            for mid, model in self.dexpi_models.items():
                results.extend(self._search_dexpi_attributes(
                    model, attributes, match_type, mid
                ))
        
        return success_response({
            "attributes": attributes,
            "result_count": len(results),
            "results": results[:100]
        })
    
    async def _search_connected(self, args: dict) -> dict:
        """Find connected components."""
        node_id = args["node_id"]
        model_id = args["model_id"]
        direction = args.get("direction", "both")
        max_depth = args.get("max_depth", 3)
        
        # Get the graph
        if model_id in self.flowsheets:
            graph = self.flowsheets[model_id].state
        elif model_id in self.dexpi_models:
            # Convert DEXPI to graph
            from ..converters.graph_converter import UnifiedGraphConverter
            converter = UnifiedGraphConverter()
            graph = converter.dexpi_to_networkx(self.dexpi_models[model_id])
        else:
            return error_response(f"Model {model_id} not found", code="MODEL_NOT_FOUND")
        
        # Find the node
        target_node = None
        for node in graph.nodes():
            if node == node_id:
                target_node = node
                break
            # Check node data for tag
            data = graph.nodes[node]
            if data.get('tag') == node_id or data.get('tagName') == node_id:
                target_node = node
                break
        
        if not target_node:
            return error_response(f"Node {node_id} not found", code="NODE_NOT_FOUND")
        
        connected = {"upstream": [], "downstream": []}
        
        if direction in ["upstream", "both"]:
            # BFS upstream
            visited = set()
            queue = [(target_node, 0)]
            
            while queue:
                node, depth = queue.pop(0)
                if depth > max_depth:
                    continue
                if node in visited:
                    continue
                visited.add(node)
                
                if node != target_node:
                    connected["upstream"].append({
                        "node": node,
                        "depth": depth,
                        "data": dict(graph.nodes[node])
                    })
                
                for pred in graph.predecessors(node):
                    if pred not in visited:
                        queue.append((pred, depth + 1))
        
        if direction in ["downstream", "both"]:
            # BFS downstream
            visited = set()
            queue = [(target_node, 0)]
            
            while queue:
                node, depth = queue.pop(0)
                if depth > max_depth:
                    continue
                if node in visited:
                    continue
                visited.add(node)
                
                if node != target_node:
                    connected["downstream"].append({
                        "node": node,
                        "depth": depth,
                        "data": dict(graph.nodes[node])
                    })
                
                for succ in graph.successors(node):
                    if succ not in visited:
                        queue.append((succ, depth + 1))
        
        return success_response({
            "source_node": target_node,
            "connected_components": connected,
            "upstream_count": len(connected["upstream"]),
            "downstream_count": len(connected["downstream"])
        })
    
    async def _query_statistics(self, args: dict) -> dict:
        """Get model statistics."""
        model_id = args.get("model_id")
        group_by = args.get("group_by", "type")
        
        statistics = {}
        
        # Collect statistics for DEXPI models
        if model_id:
            if model_id in self.dexpi_models:
                statistics[model_id] = self._get_dexpi_statistics(
                    self.dexpi_models[model_id], group_by
                )
            elif model_id in self.flowsheets:
                statistics[model_id] = self._get_flowsheet_statistics(
                    self.flowsheets[model_id], group_by
                )
        else:
            # All models
            for mid, model in self.dexpi_models.items():
                statistics[mid] = self._get_dexpi_statistics(model, group_by)
            
            for fid, flowsheet in self.flowsheets.items():
                statistics[fid] = self._get_flowsheet_statistics(flowsheet, group_by)
        
        # Aggregate statistics
        total_stats = {
            "total_models": len(statistics),
            "by_model": statistics
        }
        
        if group_by == "type":
            type_counts = {}
            for model_stats in statistics.values():
                for type_name, count in model_stats.get("by_type", {}).items():
                    type_counts[type_name] = type_counts.get(type_name, 0) + count
            total_stats["aggregate_by_type"] = type_counts
        
        return success_response(total_stats)
    
    async def _search_by_stream(self, args: dict) -> dict:
        """Search for streams."""
        results = []
        
        # This primarily applies to SFILES models
        flowsheets_to_search = {}
        model_id = args.get("model_id")
        
        if model_id:
            if model_id in self.flowsheets:
                flowsheets_to_search[model_id] = self.flowsheets[model_id]
        else:
            flowsheets_to_search = self.flowsheets
        
        stream_name = args.get("stream_name")
        from_unit = args.get("from_unit")
        to_unit = args.get("to_unit")
        properties = args.get("properties", {})
        
        for fid, flowsheet in flowsheets_to_search.items():
            for u, v, data in flowsheet.state.edges(data=True):
                match = True
                
                # Check stream name
                if stream_name:
                    edge_name = data.get('stream_name', '')
                    if '*' in stream_name:
                        pattern = stream_name.replace('*', '.*')
                        if not re.match(pattern, edge_name, re.IGNORECASE):
                            match = False
                    elif stream_name.lower() not in edge_name.lower():
                        match = False
                
                # Check source
                if from_unit and from_unit not in str(u):
                    match = False
                
                # Check target
                if to_unit and to_unit not in str(v):
                    match = False
                
                # Check properties
                for key, value in properties.items():
                    if key not in data or data[key] != value:
                        match = False
                        break
                
                if match:
                    results.append({
                        "model_id": fid,
                        "from": u,
                        "to": v,
                        "stream_data": data,
                        "model_type": "sfiles"
                    })
        
        return success_response({
            "result_count": len(results),
            "results": results[:100]
        })
    
    # Helper methods
    
    def _search_dexpi_model(self, model: Any, tag_pattern: str, pattern: Any,
                           search_scope: str, fuzzy: bool) -> List[Dict]:
        """Search within a DEXPI model."""
        results = []
        
        if not model.conceptualModel:
            return results
        
        # Search equipment
        if search_scope in ["all", "equipment"]:
            if model.conceptualModel.taggedPlantItems:
                for item in model.conceptualModel.taggedPlantItems:
                    tag = getattr(item, 'tagName', '')
                    if self._match_pattern(tag, tag_pattern, pattern, fuzzy):
                        results.append({
                            "tag": tag,
                            "type": item.__class__.__name__,
                            "category": "equipment",
                            "model_type": "dexpi"
                        })
        
        # Search instrumentation
        if search_scope in ["all", "instrumentation"]:
            if model.conceptualModel.processInstrumentationFunctions:
                for func in model.conceptualModel.processInstrumentationFunctions:
                    tag = getattr(func, 'tagName', '')
                    if self._match_pattern(tag, tag_pattern, pattern, fuzzy):
                        results.append({
                            "tag": tag,
                            "type": func.__class__.__name__,
                            "category": "instrumentation",
                            "model_type": "dexpi"
                        })
        
        # Search piping
        if search_scope in ["all", "piping"]:
            if model.conceptualModel.pipingNetworkSystems:
                for system in model.conceptualModel.pipingNetworkSystems:
                    if hasattr(system, 'segments'):
                        for segment in system.segments:
                            tag = getattr(segment, 'tagName', '')
                            if tag and self._match_pattern(tag, tag_pattern, pattern, fuzzy):
                                results.append({
                                    "tag": tag,
                                    "type": "PipingSegment",
                                    "category": "piping",
                                    "model_type": "dexpi"
                                })
        
        return results
    
    def _search_flowsheet(self, flowsheet: Any, tag_pattern: str,
                         pattern: Any, fuzzy: bool) -> List[Dict]:
        """Search within a flowsheet."""
        results = []
        
        for node, data in flowsheet.state.nodes(data=True):
            # Check node ID and any tag attributes
            tags_to_check = [node]
            if 'tag' in data:
                tags_to_check.append(data['tag'])
            if 'tagName' in data:
                tags_to_check.append(data['tagName'])
            
            for tag in tags_to_check:
                if self._match_pattern(str(tag), tag_pattern, pattern, fuzzy):
                    results.append({
                        "node": node,
                        "tag": tag,
                        "type": data.get('unit_type', 'Unknown'),
                        "model_type": "sfiles",
                        "data": dict(data)
                    })
                    break
        
        return results
    
    def _search_flowsheet_attributes(self, flowsheet: Any, attributes: Dict,
                                    match_type: str, model_id: str) -> List[Dict]:
        """Search flowsheet by attributes."""
        results = []
        
        for node, data in flowsheet.state.nodes(data=True):
            if self._match_attributes(data, attributes, match_type):
                results.append({
                    "model_id": model_id,
                    "node": node,
                    "attributes": dict(data),
                    "model_type": "sfiles"
                })
        
        return results
    
    def _search_dexpi_attributes(self, model: Any, attributes: Dict,
                                match_type: str, model_id: str) -> List[Dict]:
        """Search DEXPI model by attributes using native extraction if available."""
        results = []
        
        if model.conceptualModel and model.conceptualModel.taggedPlantItems:
            for item in model.conceptualModel.taggedPlantItems:
                # Use native pyDEXPI attribute extraction if available
                if get_data_attributes:
                    try:
                        item_dict = get_data_attributes(item)
                    except:
                        # Fallback to manual extraction
                        item_dict = self._extract_attributes_manual(item)
                else:
                    item_dict = self._extract_attributes_manual(item)
                
                if self._match_attributes(item_dict, attributes, match_type):
                    results.append({
                        "model_id": model_id,
                        "tag": getattr(item, 'tagName', 'Unknown'),
                        "type": item.__class__.__name__,
                        "attributes": item_dict,
                        "model_type": "dexpi"
                    })
        
        return results
    
    def _extract_attributes_manual(self, item: Any) -> Dict:
        """Manual fallback for attribute extraction."""
        item_dict = {}
        for attr in dir(item):
            if not attr.startswith('_'):
                try:
                    value = getattr(item, attr)
                    if not callable(value):
                        item_dict[attr] = value
                except:
                    pass
        return item_dict
    
    def _match_pattern(self, text: str, pattern_str: str,
                      compiled_pattern: Any, fuzzy: bool) -> bool:
        """Match text against pattern."""
        if fuzzy:
            # Fuzzy matching
            return fuzz.partial_ratio(text.lower(), pattern_str.lower()) > 70
        elif compiled_pattern:
            # Regex matching
            return bool(compiled_pattern.match(text))
        else:
            # Exact substring matching
            return pattern_str.lower() in text.lower()
    
    def _match_attributes(self, data: Dict, attributes: Dict, match_type: str) -> bool:
        """Match attributes against data."""
        for key, value in attributes.items():
            if key not in data:
                return False
            
            data_value = str(data[key])
            search_value = str(value)
            
            if match_type == "exact":
                if data_value != search_value:
                    return False
            elif match_type == "partial":
                if search_value.lower() not in data_value.lower():
                    return False
            elif match_type == "regex":
                if not re.match(search_value, data_value, re.IGNORECASE):
                    return False
        
        return True
    
    def _get_dexpi_statistics(self, model: Any, group_by: str) -> Dict:
        """Get statistics for DEXPI model."""
        stats = {
            "model_type": "dexpi",
            "total_equipment": 0,
            "total_instrumentation": 0,
            "total_piping": 0
        }
        
        if not model.conceptualModel:
            return stats
        
        # Count equipment
        if model.conceptualModel.taggedPlantItems:
            stats["total_equipment"] = len(model.conceptualModel.taggedPlantItems)
            
            if group_by == "type":
                type_counts = {}
                for item in model.conceptualModel.taggedPlantItems:
                    type_name = item.__class__.__name__
                    type_counts[type_name] = type_counts.get(type_name, 0) + 1
                stats["by_type"] = type_counts
            
            elif group_by == "tag_prefix":
                prefix_counts = {}
                for item in model.conceptualModel.taggedPlantItems:
                    tag = getattr(item, 'tagName', '')
                    if tag and '-' in tag:
                        prefix = tag.split('-')[0]
                        prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
                stats["by_tag_prefix"] = prefix_counts
        
        # Count instrumentation
        if model.conceptualModel.processInstrumentationFunctions:
            stats["total_instrumentation"] = len(
                model.conceptualModel.processInstrumentationFunctions
            )
        
        # Count piping
        if model.conceptualModel.pipingNetworkSystems:
            piping_count = 0
            for system in model.conceptualModel.pipingNetworkSystems:
                if hasattr(system, 'segments'):
                    piping_count += len(system.segments) if system.segments else 0
            stats["total_piping"] = piping_count
        
        return stats
    
    def _get_flowsheet_statistics(self, flowsheet: Any, group_by: str) -> Dict:
        """Get statistics for flowsheet."""
        graph = flowsheet.state
        stats = {
            "model_type": "sfiles",
            "total_nodes": graph.number_of_nodes(),
            "total_edges": graph.number_of_edges()
        }
        
        if group_by == "type":
            type_counts = {}
            for node, data in graph.nodes(data=True):
                # SFILES uses 'unit_type' not 'type'
                type_name = data.get('unit_type', 'Unknown')
                type_counts[type_name] = type_counts.get(type_name, 0) + 1
            stats["by_type"] = type_counts
        
        elif group_by == "connection_count":
            connection_counts = {
                "isolated": 0,
                "1_connection": 0,
                "2_connections": 0,
                "3_connections": 0,
                "4_plus_connections": 0
            }
            
            for node in graph.nodes():
                degree = graph.degree(node)
                if degree == 0:
                    connection_counts["isolated"] += 1
                elif degree == 1:
                    connection_counts["1_connection"] += 1
                elif degree == 2:
                    connection_counts["2_connections"] += 1
                elif degree == 3:
                    connection_counts["3_connections"] += 1
                else:
                    connection_counts["4_plus_connections"] += 1
            
            stats["by_connection_count"] = connection_counts

        return stats

    async def _unified_search(self, args: dict) -> dict:
        """
        Unified search handler - dispatches to appropriate search operation.

        Consolidates all search_* tools into a single entry point.
        """
        query_type = args.get("query_type")

        if not query_type:
            return error_response(
                "Missing required parameter: query_type",
                code="MISSING_QUERY_TYPE"
            )

        # Dispatch to appropriate handler based on query type
        query_map = {
            "by_tag": self._search_by_tag,
            "by_type": self._search_by_type,
            "by_attributes": self._search_by_attributes,
            "connected": self._search_connected,
            "statistics": self._query_statistics,
            "by_stream": self._search_by_stream
        }

        handler = query_map.get(query_type)
        if not handler:
            return error_response(
                f"Invalid query_type: {query_type}. Must be one of: {', '.join(query_map.keys())}",
                code="INVALID_QUERY_TYPE"
            )

        # Call the appropriate handler with the full args dict
        try:
            return await handler(args)
        except Exception as e:
            logger.error(f"Error in search_execute query '{query_type}': {e}", exc_info=True)
            return error_response(
                f"Query '{query_type}' failed: {str(e)}",
                code="QUERY_ERROR"
            )