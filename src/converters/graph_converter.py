"""Unified graph converter for DEXPI and SFILES models."""

import logging
from io import StringIO
from typing import Any, Dict, Optional

import networkx as nx
from pydexpi.dexpi_classes.dexpiModel import DexpiModel
from pydexpi.loaders.ml_graph_loader import MLGraphLoader
from Flowsheet_Class.flowsheet import Flowsheet

logger = logging.getLogger(__name__)


class UnifiedGraphConverter:
    """Converts between DEXPI, NetworkX, and GraphML representations."""
    
    def __init__(self):
        """Initialize the converter."""
        self.ml_loader = MLGraphLoader()
    
    def dexpi_to_networkx(self, dexpi_model: DexpiModel) -> nx.DiGraph:
        """Convert DEXPI model to NetworkX graph.
        
        Args:
            dexpi_model: The DEXPI model to convert
            
        Returns:
            NetworkX directed graph representation
        """
        try:
            # Use pyDEXPI's MLGraphLoader to convert
            nx_graph = self.ml_loader.dexpi_to_graph(dexpi_model)
            return nx_graph
        except Exception as e:
            logger.error(f"Error converting DEXPI to NetworkX: {e}")
            # Return empty graph on error
            return nx.DiGraph()
    
    def dexpi_to_graphml(
        self, 
        dexpi_model: DexpiModel, 
        include_msr: bool = True
    ) -> str:
        """Convert DEXPI model to GraphML string.
        
        Args:
            dexpi_model: The DEXPI model to convert
            include_msr: Whether to include measurement/control/regulation units
            
        Returns:
            GraphML string representation
        """
        # Convert to NetworkX first
        nx_graph = self.dexpi_to_networkx(dexpi_model)
        
        # Filter MSR units if requested
        if not include_msr:
            nx_graph = self._filter_msr_nodes(nx_graph)
        
        # Convert to GraphML
        return self.networkx_to_graphml(nx_graph)
    
    def sfiles_to_networkx(self, flowsheet: Flowsheet) -> nx.DiGraph:
        """Extract NetworkX graph from SFILES flowsheet.
        
        Args:
            flowsheet: The SFILES2 Flowsheet object
            
        Returns:
            NetworkX directed graph representation
        """
        # SFILES2 already uses NetworkX internally
        return flowsheet.state
    
    def sfiles_to_graphml(self, flowsheet: Flowsheet) -> str:
        """Convert SFILES flowsheet to GraphML string.
        
        Args:
            flowsheet: The SFILES2 Flowsheet object
            
        Returns:
            GraphML string representation
        """
        nx_graph = self.sfiles_to_networkx(flowsheet)
        return self.networkx_to_graphml(nx_graph)
    
    def networkx_to_graphml(self, graph: nx.Graph) -> str:
        """Convert NetworkX graph to GraphML string with sanitization.
        
        Args:
            graph: NetworkX graph to convert
            
        Returns:
            GraphML string representation
        """
        # Import sanitizer
        from .graph_sanitizer import GraphMLSanitizer
        
        # Sanitize graph before export to ensure GraphML compatibility
        clean_graph = GraphMLSanitizer.sanitize_graph_for_export(graph)
        
        # Some NetworkX versions don't write to StringIO reliably; use a temp file
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w+b", suffix=".graphml", delete=False) as f:
            tmp_path = f.name
        try:
            nx.write_graphml(clean_graph, tmp_path, prettyprint=True)
            with open(tmp_path, "r", encoding="utf-8") as rf:
                return rf.read()
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    
    def graphml_to_networkx(self, graphml_string: str) -> nx.Graph:
        """Parse GraphML string to NetworkX graph.
        
        Args:
            graphml_string: GraphML string to parse
            
        Returns:
            NetworkX graph
        """
        graphml_buffer = StringIO(graphml_string)
        graph = nx.read_graphml(graphml_buffer)
        graphml_buffer.close()
        
        return graph
    
    def _filter_msr_nodes(self, graph: nx.DiGraph) -> nx.DiGraph:
        """Filter out measurement/control/regulation nodes from graph.
        
        Args:
            graph: NetworkX graph to filter
            
        Returns:
            Filtered NetworkX graph
        """
        filtered_graph = graph.copy()
        
        # Find MSR nodes (based on DEXPI class)
        msr_nodes = []
        for node, data in graph.nodes(data=True):
            dexpi_class = data.get("dexpi_class", "")
            if "ProcessInstrumentationFunction" in str(dexpi_class):
                msr_nodes.append(node)
        
        # Remove MSR nodes
        filtered_graph.remove_nodes_from(msr_nodes)
        
        return filtered_graph
    
    def compare_graphs(
        self, 
        graph1: nx.Graph, 
        graph2: nx.Graph
    ) -> Dict[str, Any]:
        """Compare two graphs and return differences.
        
        Args:
            graph1: First graph to compare
            graph2: Second graph to compare
            
        Returns:
            Dictionary with comparison results
        """
        result = {
            "graph1_nodes": set(graph1.nodes()),
            "graph2_nodes": set(graph2.nodes()),
            "graph1_edges": set(graph1.edges()),
            "graph2_edges": set(graph2.edges()),
            "nodes_only_in_graph1": set(graph1.nodes()) - set(graph2.nodes()),
            "nodes_only_in_graph2": set(graph2.nodes()) - set(graph1.nodes()),
            "edges_only_in_graph1": set(graph1.edges()) - set(graph2.edges()),
            "edges_only_in_graph2": set(graph2.edges()) - set(graph1.edges()),
            "common_nodes": set(graph1.nodes()) & set(graph2.nodes()),
            "common_edges": set(graph1.edges()) & set(graph2.edges()),
        }
        
        # Add statistics
        result["statistics"] = {
            "graph1_node_count": graph1.number_of_nodes(),
            "graph1_edge_count": graph1.number_of_edges(),
            "graph2_node_count": graph2.number_of_nodes(),
            "graph2_edge_count": graph2.number_of_edges(),
            "node_difference": abs(graph1.number_of_nodes() - graph2.number_of_nodes()),
            "edge_difference": abs(graph1.number_of_edges() - graph2.number_of_edges()),
        }
        
        return result
    
    def extract_topology_summary(self, graph: nx.Graph) -> Dict[str, Any]:
        """Extract topology summary from a graph.
        
        Args:
            graph: NetworkX graph to analyze
            
        Returns:
            Dictionary with topology metrics
        """
        summary = {
            "num_nodes": graph.number_of_nodes(),
            "num_edges": graph.number_of_edges(),
            "is_directed": graph.is_directed(),
            "is_connected": nx.is_weakly_connected(graph) if graph.is_directed() else nx.is_connected(graph),
            "density": nx.density(graph),
        }
        
        # Add degree statistics
        degrees = dict(graph.degree())
        if degrees:
            summary["avg_degree"] = sum(degrees.values()) / len(degrees)
            summary["max_degree"] = max(degrees.values())
            summary["min_degree"] = min(degrees.values())
        
        # Check for cycles
        if graph.is_directed():
            summary["is_acyclic"] = nx.is_directed_acyclic_graph(graph)
            summary["num_strongly_connected_components"] = nx.number_strongly_connected_components(graph)
            summary["num_weakly_connected_components"] = nx.number_weakly_connected_components(graph)
        else:
            summary["num_connected_components"] = nx.number_connected_components(graph)
        
        # Identify isolated nodes
        isolated = list(nx.isolates(graph))
        summary["num_isolated_nodes"] = len(isolated)
        summary["isolated_nodes"] = isolated
        
        return summary
