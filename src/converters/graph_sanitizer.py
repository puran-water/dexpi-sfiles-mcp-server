"""GraphML sanitizer following DEXPI2graphML's proven pattern."""

import logging
from typing import Any, Dict

import networkx as nx

logger = logging.getLogger(__name__)


class GraphMLSanitizer:
    """Sanitize attributes using DEXPI2graphML's proven pattern.
    
    DEXPI2graphML avoids complex types by:
    - Using only primitive types (str, int, float, bool)
    - Splitting compound values into separate attributes
    - Converting everything else to strings
    """
    
    @staticmethod
    def sanitize_attributes(attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Convert to GraphML-safe primitives, following DEXPI2graphML pattern.
        
        Args:
            attrs: Dictionary of attributes to sanitize
            
        Returns:
            Dictionary with GraphML-safe attributes
        """
        sanitized = {}
        
        for key, value in attrs.items():
            # Already safe primitive types
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            
            # Handle None
            elif value is None:
                sanitized[key] = ""  # Empty string for None
            
            # Handle dictionaries by flattening
            elif isinstance(value, dict):
                # DEXPI2graphML pattern: Split into multiple flat attributes
                for k, v in value.items():
                    new_key = f"{key}_{k}"
                    if isinstance(v, (str, int, float, bool)):
                        sanitized[new_key] = v
                    elif v is None:
                        sanitized[new_key] = ""
                    else:
                        sanitized[new_key] = str(v)
            
            # Handle lists and sets
            elif isinstance(value, (list, tuple, set)):
                # Store count for analysis
                sanitized[f"{key}_count"] = len(value)
                
                # For small lists of primitives, expand them
                if len(value) <= 5 and all(isinstance(v, (str, int, float, bool)) for v in value):
                    for i, item in enumerate(value):
                        sanitized[f"{key}_{i}"] = item
                else:
                    # For complex lists, just stringify
                    sanitized[f"{key}_items"] = str(list(value))
            
            # Default: convert to string
            else:
                sanitized[key] = str(value)
        
        return sanitized
    
    @staticmethod
    def sanitize_graph_for_export(graph: nx.Graph) -> nx.Graph:
        """Create sanitized copy of graph for GraphML export.
        
        Following DEXPI2graphML pattern:
        - Ensure all node IDs are strings
        - Sanitize all attributes to primitives
        - Preserve graph structure
        
        Args:
            graph: NetworkX graph to sanitize
            
        Returns:
            New graph with sanitized attributes safe for GraphML export
        """
        # Create new graph of same type
        if isinstance(graph, nx.DiGraph):
            clean_graph = nx.DiGraph()
        else:
            clean_graph = nx.Graph()
        
        # Sanitize and copy graph-level attributes
        clean_graph.graph.update(
            GraphMLSanitizer.sanitize_attributes(graph.graph)
        )
        
        # Sanitize and copy nodes
        for node, attrs in graph.nodes(data=True):
            # Ensure node ID is string (GraphML requirement)
            node_id = str(node)
            clean_attrs = GraphMLSanitizer.sanitize_attributes(attrs)
            clean_graph.add_node(node_id, **clean_attrs)
        
        # Sanitize and copy edges
        if isinstance(graph, nx.DiGraph):
            edge_iter = graph.edges(data=True)
        else:
            edge_iter = graph.edges(data=True)
            
        for u, v, attrs in edge_iter:
            # Ensure node IDs are strings
            u_id, v_id = str(u), str(v)
            clean_attrs = GraphMLSanitizer.sanitize_attributes(attrs)
            clean_graph.add_edge(u_id, v_id, **clean_attrs)
        
        logger.debug(
            f"Sanitized graph: {graph.number_of_nodes()} nodes, "
            f"{graph.number_of_edges()} edges"
        )
        
        return clean_graph