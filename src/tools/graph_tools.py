"""Graph analytics tools for engineering models."""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx
from collections import defaultdict

from mcp import Tool
from ..utils.response import success_response, error_response, create_issue
from ..converters.graph_converter import UnifiedGraphConverter

logger = logging.getLogger(__name__)


class GraphTools:
    """Provides graph analytics for engineering models."""
    
    def __init__(self, dexpi_models: Dict[str, Any], flowsheets: Dict[str, Any]):
        """Initialize with model stores."""
        self.dexpi_models = dexpi_models
        self.flowsheets = flowsheets
        self.converter = UnifiedGraphConverter()
    
    def get_tools(self) -> List[Tool]:
        """Return graph analytics tools."""
        return [
            Tool(
                name="graph_analyze_topology",
                description="Analyze graph topology including paths, cycles, bottlenecks, and connectivity",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {
                            "type": "string",
                            "description": "Model ID to analyze"
                        },
                        "model_type": {
                            "type": "string",
                            "enum": ["dexpi", "sfiles", "auto"],
                            "description": "Model type",
                            "default": "auto"
                        },
                        "analyses": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["paths", "cycles", "bottlenecks", "clustering", "centrality", "all"]
                            },
                            "description": "Which analyses to perform",
                            "default": ["all"]
                        }
                    },
                    "required": ["model_id"]
                }
            ),
            Tool(
                name="graph_find_paths",
                description="Find paths between nodes in the graph",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {
                            "type": "string",
                            "description": "Model ID to analyze"
                        },
                        "source": {
                            "type": "string",
                            "description": "Source node ID or tag"
                        },
                        "target": {
                            "type": "string",
                            "description": "Target node ID or tag"
                        },
                        "path_type": {
                            "type": "string",
                            "enum": ["shortest", "all_simple", "all"],
                            "description": "Type of paths to find",
                            "default": "shortest"
                        },
                        "max_length": {
                            "type": "integer",
                            "description": "Maximum path length for all_simple paths",
                            "default": 10
                        }
                    },
                    "required": ["model_id", "source", "target"]
                }
            ),
            Tool(
                name="graph_detect_patterns",
                description="Detect common patterns like heat integration, recycle loops, parallel trains",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {
                            "type": "string",
                            "description": "Model ID to analyze"
                        },
                        "patterns": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["heat_integration", "recycle_loops", "parallel_trains", "feed_forward", "cascade", "all"]
                            },
                            "description": "Patterns to detect",
                            "default": ["all"]
                        }
                    },
                    "required": ["model_id"]
                }
            ),
            Tool(
                name="graph_calculate_metrics",
                description="Calculate graph metrics like diameter, density, clustering coefficient",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {
                            "type": "string",
                            "description": "Model ID to analyze"
                        },
                        "metrics": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["basic", "centrality", "clustering", "efficiency", "all"]
                            },
                            "description": "Which metrics to calculate",
                            "default": ["all"]
                        }
                    },
                    "required": ["model_id"]
                }
            ),
            Tool(
                name="graph_compare_models",
                description="Compare graph structures of two models",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model1_id": {
                            "type": "string",
                            "description": "First model ID"
                        },
                        "model2_id": {
                            "type": "string",
                            "description": "Second model ID"
                        },
                        "comparison_type": {
                            "type": "string",
                            "enum": ["structural", "topological", "both"],
                            "description": "Type of comparison",
                            "default": "both"
                        }
                    },
                    "required": ["model1_id", "model2_id"]
                }
            )
        ]
    
    async def handle_tool(self, name: str, arguments: dict) -> dict:
        """Route tool call to appropriate handler."""
        handlers = {
            "graph_analyze_topology": self._analyze_topology,
            "graph_find_paths": self._find_paths,
            "graph_detect_patterns": self._detect_patterns,
            "graph_calculate_metrics": self._calculate_metrics,
            "graph_compare_models": self._compare_models
        }
        
        handler = handlers.get(name)
        if not handler:
            return error_response(f"Unknown graph tool: {name}", code="UNKNOWN_TOOL")
        
        try:
            return await handler(arguments)
        except Exception as e:
            logger.error(f"Error in {name}: {e}")
            return error_response(str(e), code="TOOL_ERROR")
    
    def _get_graph(self, model_id: str, model_type: str = "auto") -> Tuple[nx.DiGraph, str]:
        """Get graph from model."""
        # Auto-detect type
        if model_type == "auto":
            if model_id in self.dexpi_models:
                model_type = "dexpi"
            elif model_id in self.flowsheets:
                model_type = "sfiles"
            else:
                raise ValueError(f"Model {model_id} not found")
        
        if model_type == "dexpi":
            model = self.dexpi_models.get(model_id)
            if not model:
                raise ValueError(f"DEXPI model {model_id} not found")
            graph = self.converter.dexpi_to_networkx(model)
        else:  # sfiles
            flowsheet = self.flowsheets.get(model_id)
            if not flowsheet:
                raise ValueError(f"SFILES flowsheet {model_id} not found")
            graph = flowsheet.state
        
        return graph, model_type
    
    async def _analyze_topology(self, args: dict) -> dict:
        """Analyze graph topology."""
        model_id = args["model_id"]
        analyses = args.get("analyses", ["all"])
        
        graph, model_type = self._get_graph(model_id, args.get("model_type", "auto"))
        
        if "all" in analyses:
            analyses = ["paths", "cycles", "bottlenecks", "clustering", "centrality"]
        
        results = {
            "model_id": model_id,
            "model_type": model_type,
            "node_count": graph.number_of_nodes(),
            "edge_count": graph.number_of_edges()
        }
        
        if "paths" in analyses:
            results["paths"] = self._analyze_paths(graph)
        
        if "cycles" in analyses:
            results["cycles"] = self._analyze_cycles(graph)
        
        if "bottlenecks" in analyses:
            results["bottlenecks"] = self._find_bottlenecks(graph)
        
        if "clustering" in analyses:
            results["clustering"] = self._analyze_clustering(graph)
        
        if "centrality" in analyses:
            results["centrality"] = self._analyze_centrality(graph)
        
        return success_response(results)
    
    async def _find_paths(self, args: dict) -> dict:
        """Find paths between nodes."""
        model_id = args["model_id"]
        source = args["source"]
        target = args["target"]
        path_type = args.get("path_type", "shortest")
        max_length = args.get("max_length", 10)
        
        graph, model_type = self._get_graph(model_id, args.get("model_type", "auto"))
        
        # Find nodes by ID or tag
        source_node = self._find_node(graph, source)
        target_node = self._find_node(graph, target)
        
        if not source_node:
            return error_response(f"Source node {source} not found", code="NODE_NOT_FOUND")
        if not target_node:
            return error_response(f"Target node {target} not found", code="NODE_NOT_FOUND")
        
        paths = []
        
        if path_type == "shortest":
            try:
                path = nx.shortest_path(graph, source_node, target_node)
                paths = [path]
            except nx.NetworkXNoPath:
                paths = []
        
        elif path_type == "all_simple":
            paths = list(nx.all_simple_paths(graph, source_node, target_node, cutoff=max_length))
        
        else:  # all
            paths = list(nx.all_simple_paths(graph, source_node, target_node))
        
        return success_response({
            "source": source_node,
            "target": target_node,
            "path_count": len(paths),
            "paths": paths[:100],  # Limit to 100 paths
            "shortest_length": len(paths[0]) - 1 if paths else None
        })
    
    async def _detect_patterns(self, args: dict) -> dict:
        """Detect common process patterns."""
        model_id = args["model_id"]
        patterns = args.get("patterns", ["all"])
        
        graph, model_type = self._get_graph(model_id, args.get("model_type", "auto"))
        
        if "all" in patterns:
            patterns = ["heat_integration", "recycle_loops", "parallel_trains", "feed_forward", "cascade"]
        
        detected = {}
        
        if "heat_integration" in patterns:
            detected["heat_integration"] = self._detect_heat_integration(graph)
        
        if "recycle_loops" in patterns:
            detected["recycle_loops"] = self._detect_recycle_loops(graph)
        
        if "parallel_trains" in patterns:
            detected["parallel_trains"] = self._detect_parallel_trains(graph)
        
        if "feed_forward" in patterns:
            detected["feed_forward"] = self._detect_feed_forward(graph)
        
        if "cascade" in patterns:
            detected["cascade"] = self._detect_cascade(graph)
        
        return success_response({
            "model_id": model_id,
            "patterns_detected": detected
        })
    
    async def _calculate_metrics(self, args: dict) -> dict:
        """Calculate graph metrics."""
        model_id = args["model_id"]
        metrics = args.get("metrics", ["all"])
        
        graph, model_type = self._get_graph(model_id, args.get("model_type", "auto"))
        
        if "all" in metrics:
            metrics = ["basic", "centrality", "clustering", "efficiency"]
        
        results = {}
        
        if "basic" in metrics:
            results["basic"] = {
                "nodes": graph.number_of_nodes(),
                "edges": graph.number_of_edges(),
                "density": nx.density(graph),
                "is_connected": nx.is_weakly_connected(graph),
                "is_dag": nx.is_directed_acyclic_graph(graph),
                "number_of_components": nx.number_weakly_connected_components(graph)
            }
            
            if nx.is_weakly_connected(graph):
                results["basic"]["diameter"] = nx.diameter(graph.to_undirected())
        
        if "centrality" in metrics:
            results["centrality"] = {
                "degree": self._top_nodes(dict(graph.degree()), 5),
                "betweenness": self._top_nodes(nx.betweenness_centrality(graph), 5),
                "closeness": self._top_nodes(nx.closeness_centrality(graph), 5)
            }
        
        if "clustering" in metrics:
            undirected = graph.to_undirected()
            results["clustering"] = {
                "average_clustering": nx.average_clustering(undirected),
                "transitivity": nx.transitivity(undirected)
            }
        
        if "efficiency" in metrics:
            results["efficiency"] = {
                "global_efficiency": nx.global_efficiency(graph),
                "local_efficiency": nx.local_efficiency(graph)
            }
        
        return success_response(results)
    
    async def _compare_models(self, args: dict) -> dict:
        """Compare two model graphs."""
        model1_id = args["model1_id"]
        model2_id = args["model2_id"]
        comparison_type = args.get("comparison_type", "both")
        
        graph1, type1 = self._get_graph(model1_id)
        graph2, type2 = self._get_graph(model2_id)
        
        comparison = {
            "model1": {"id": model1_id, "type": type1},
            "model2": {"id": model2_id, "type": type2}
        }
        
        if comparison_type in ["structural", "both"]:
            comparison["structural"] = {
                "node_difference": graph1.number_of_nodes() - graph2.number_of_nodes(),
                "edge_difference": graph1.number_of_edges() - graph2.number_of_edges(),
                "density_difference": nx.density(graph1) - nx.density(graph2),
                "common_nodes": len(set(graph1.nodes()) & set(graph2.nodes())),
                "unique_to_model1": len(set(graph1.nodes()) - set(graph2.nodes())),
                "unique_to_model2": len(set(graph2.nodes()) - set(graph1.nodes()))
            }
        
        if comparison_type in ["topological", "both"]:
            comparison["topological"] = {
                "model1_is_dag": nx.is_directed_acyclic_graph(graph1),
                "model2_is_dag": nx.is_directed_acyclic_graph(graph2),
                "model1_components": nx.number_weakly_connected_components(graph1),
                "model2_components": nx.number_weakly_connected_components(graph2),
                "model1_cycles": len(list(nx.simple_cycles(graph1))) if graph1.number_of_nodes() < 100 else "Too large",
                "model2_cycles": len(list(nx.simple_cycles(graph2))) if graph2.number_of_nodes() < 100 else "Too large"
            }
        
        return success_response(comparison)
    
    # Helper methods
    
    def _find_node(self, graph: nx.DiGraph, identifier: str) -> Optional[str]:
        """Find node by ID or tag."""
        if identifier in graph.nodes():
            return identifier
        
        # Search by tag attribute
        for node, data in graph.nodes(data=True):
            if data.get('tag') == identifier or data.get('tagName') == identifier:
                return node
        
        return None
    
    def _analyze_paths(self, graph: nx.DiGraph) -> Dict:
        """Analyze path characteristics."""
        if not nx.is_weakly_connected(graph):
            return {"connected": False}
        
        # Find longest path (for DAGs)
        if nx.is_directed_acyclic_graph(graph):
            longest_path = nx.dag_longest_path(graph)
            return {
                "is_dag": True,
                "longest_path_length": len(longest_path) - 1,
                "longest_path_nodes": longest_path[:10]  # First 10 nodes
            }
        else:
            return {
                "is_dag": False,
                "has_cycles": True
            }
    
    def _analyze_cycles(self, graph: nx.DiGraph) -> Dict:
        """Analyze cycles in the graph."""
        if graph.number_of_nodes() > 100:
            return {"status": "Graph too large for cycle analysis"}
        
        cycles = list(nx.simple_cycles(graph))
        
        return {
            "cycle_count": len(cycles),
            "cycles": cycles[:20],  # Limit to 20 cycles
            "max_cycle_length": max(len(c) for c in cycles) if cycles else 0,
            "min_cycle_length": min(len(c) for c in cycles) if cycles else 0
        }
    
    def _find_bottlenecks(self, graph: nx.DiGraph) -> Dict:
        """Find bottleneck nodes."""
        betweenness = nx.betweenness_centrality(graph)
        bottlenecks = self._top_nodes(betweenness, 10)
        
        # Find articulation points (for undirected version)
        undirected = graph.to_undirected()
        articulation_points = list(nx.articulation_points(undirected))
        
        return {
            "high_betweenness_nodes": bottlenecks,
            "articulation_points": articulation_points[:20]
        }
    
    def _analyze_clustering(self, graph: nx.DiGraph) -> Dict:
        """Analyze clustering in the graph."""
        # Convert to undirected for clustering analysis
        undirected = graph.to_undirected()
        
        # Find communities
        communities = list(nx.community.greedy_modularity_communities(undirected))
        
        return {
            "number_of_communities": len(communities),
            "community_sizes": [len(c) for c in communities],
            "largest_community": list(communities[0])[:20] if communities else []
        }
    
    def _analyze_centrality(self, graph: nx.DiGraph) -> Dict:
        """Analyze node centrality."""
        return {
            "highest_degree": self._top_nodes(dict(graph.degree()), 5),
            "highest_in_degree": self._top_nodes(dict(graph.in_degree()), 5),
            "highest_out_degree": self._top_nodes(dict(graph.out_degree()), 5)
        }
    
    def _detect_heat_integration(self, graph: nx.DiGraph) -> List[Dict]:
        """Detect heat integration patterns."""
        patterns = []
        
        # Look for heat exchanger nodes
        for node, data in graph.nodes(data=True):
            node_type = data.get('type', '').lower()
            if 'heat' in node_type or 'hex' in node_type or 'exchanger' in node_type:
                # Check connections
                predecessors = list(graph.predecessors(node))
                successors = list(graph.successors(node))
                
                if len(predecessors) >= 2 or len(successors) >= 2:
                    patterns.append({
                        "node": node,
                        "type": "heat_exchanger",
                        "connections": len(predecessors) + len(successors)
                    })
        
        return patterns[:10]  # Limit results
    
    def _detect_recycle_loops(self, graph: nx.DiGraph) -> List[List]:
        """Detect recycle loops."""
        if graph.number_of_nodes() > 100:
            return []
        
        cycles = list(nx.simple_cycles(graph))
        # Filter for likely recycle loops (longer cycles)
        recycle_loops = [c for c in cycles if len(c) > 2]
        
        return recycle_loops[:10]  # Limit results
    
    def _detect_parallel_trains(self, graph: nx.DiGraph) -> List[Dict]:
        """Detect parallel processing trains."""
        patterns = []
        
        # Look for nodes with same predecessors and successors
        node_connections = {}
        for node in graph.nodes():
            pred = frozenset(graph.predecessors(node))
            succ = frozenset(graph.successors(node))
            key = (pred, succ)
            
            if key not in node_connections:
                node_connections[key] = []
            node_connections[key].append(node)
        
        # Find parallel trains
        for (pred, succ), nodes in node_connections.items():
            if len(nodes) > 1 and len(pred) > 0 and len(succ) > 0:
                patterns.append({
                    "parallel_nodes": nodes,
                    "common_inputs": list(pred),
                    "common_outputs": list(succ)
                })
        
        return patterns[:5]  # Limit results
    
    def _detect_feed_forward(self, graph: nx.DiGraph) -> Dict:
        """Detect feed-forward patterns."""
        if not nx.is_directed_acyclic_graph(graph):
            return {"is_feed_forward": False, "reason": "Graph contains cycles"}
        
        # Find topological levels
        try:
            topo_order = list(nx.topological_sort(graph))
            levels = {}
            for node in topo_order:
                pred_levels = [levels[p] for p in graph.predecessors(node) if p in levels]
                levels[node] = max(pred_levels) + 1 if pred_levels else 0
            
            # Group by level
            level_groups = defaultdict(list)
            for node, level in levels.items():
                level_groups[level].append(node)
            
            return {
                "is_feed_forward": True,
                "number_of_levels": len(level_groups),
                "nodes_per_level": {k: len(v) for k, v in level_groups.items()}
            }
        except:
            return {"is_feed_forward": False}
    
    def _detect_cascade(self, graph: nx.DiGraph) -> List[List]:
        """Detect cascade patterns (sequential processing)."""
        cascades = []
        
        # Find linear paths
        for node in graph.nodes():
            if graph.in_degree(node) == 0:  # Start node
                # Follow linear path
                path = [node]
                current = node
                
                while graph.out_degree(current) == 1:
                    successors = list(graph.successors(current))
                    if successors and graph.in_degree(successors[0]) == 1:
                        current = successors[0]
                        path.append(current)
                    else:
                        break
                
                if len(path) > 2:  # Cascade of at least 3 units
                    cascades.append(path)
        
        return cascades[:5]  # Limit results
    
    def _top_nodes(self, scores: Dict, n: int) -> List[Tuple[str, float]]:
        """Get top n nodes by score."""
        sorted_nodes = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_nodes[:n]