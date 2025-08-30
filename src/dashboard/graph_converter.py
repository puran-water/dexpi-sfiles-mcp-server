"""Convert NetworkX graphs to Cytoscape.js format."""

import json
from typing import Dict, Any, List
import networkx as nx


class CytoscapeConverter:
    """Convert NetworkX graphs to Cytoscape.js format."""
    
    def networkx_to_cytoscape(self, graph: nx.Graph) -> Dict[str, List[Dict[str, Any]]]:
        """Convert NetworkX graph to Cytoscape.js format.
        
        Args:
            graph: NetworkX graph
            
        Returns:
            Dict with 'nodes' and 'edges' lists in Cytoscape format
        """
        elements = {
            "nodes": [],
            "edges": []
        }
        
        # Convert nodes
        for node_id, attrs in graph.nodes(data=True):
            # Clean attributes for JSON serialization
            clean_attrs = self._clean_attributes(attrs)
            
            node_data = {
                "data": {
                    "id": str(node_id),
                    "label": clean_attrs.get("label", str(node_id)),
                    **clean_attrs
                },
                "classes": self._get_node_classes(clean_attrs)
            }
            
            # Add position if available
            if "x" in clean_attrs and "y" in clean_attrs:
                node_data["position"] = {
                    "x": clean_attrs["x"],
                    "y": clean_attrs["y"]
                }
                
            elements["nodes"].append(node_data)
        
        # Convert edges
        for source, target, attrs in graph.edges(data=True):
            # Clean attributes for JSON serialization
            clean_attrs = self._clean_attributes(attrs)
            
            edge_data = {
                "data": {
                    "id": f"{source}-{target}",
                    "source": str(source),
                    "target": str(target),
                    "label": clean_attrs.get("label", ""),
                    **clean_attrs
                },
                "classes": self._get_edge_classes(clean_attrs)
            }
            
            elements["edges"].append(edge_data)
        
        return elements
    
    def _clean_attributes(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Clean attributes for JSON serialization.
        
        Args:
            attrs: Attribute dictionary
            
        Returns:
            Cleaned attributes
        """
        clean = {}
        for key, value in attrs.items():
            # Skip None values
            if value is None:
                continue
                
            # Convert complex types to strings
            if isinstance(value, (list, dict, tuple)):
                clean[key] = json.dumps(value)
            elif isinstance(value, (str, int, float, bool)):
                clean[key] = value
            else:
                clean[key] = str(value)
                
        return clean
    
    def _get_node_classes(self, attrs: Dict[str, Any]) -> str:
        """Get CSS classes for a node based on its attributes.
        
        Args:
            attrs: Node attributes
            
        Returns:
            Space-separated CSS class string
        """
        classes = []
        
        # Add type-based classes
        node_type = attrs.get("type", "").lower()
        if "equipment" in node_type or "tank" in node_type:
            classes.append("equipment")
        elif "pump" in node_type:
            classes.append("pump")
        elif "valve" in node_type:
            classes.append("valve")
        elif "instrument" in node_type:
            classes.append("instrument")
        elif "nozzle" in node_type:
            classes.append("nozzle")
        elif "reactor" in node_type:
            classes.append("reactor")
        elif "distcol" in node_type or "column" in node_type:
            classes.append("column")
        elif "hex" in node_type or "exchanger" in node_type:
            classes.append("heat-exchanger")
            
        # Add tag-based classes for SFILES
        if "tag" in attrs:
            classes.append("tagged")
            
        return " ".join(classes) if classes else "default"
    
    def _get_edge_classes(self, attrs: Dict[str, Any]) -> str:
        """Get CSS classes for an edge based on its attributes.
        
        Args:
            attrs: Edge attributes
            
        Returns:
            Space-separated CSS class string
        """
        classes = []
        
        # Add type-based classes
        edge_type = attrs.get("type", "").lower()
        if "pipe" in edge_type or "piping" in edge_type:
            classes.append("piping")
        elif "signal" in edge_type or "control" in edge_type:
            classes.append("control-signal")
        elif "stream" in edge_type:
            classes.append("process-stream")
            
        return " ".join(classes) if classes else "default"
    
    def create_layout_options(self) -> Dict[str, Any]:
        """Create layout options for Cytoscape.
        
        Returns:
            Layout configuration dictionary
        """
        return {
            "dagre": {
                "name": "dagre",
                "rankDir": "LR",  # Left to right
                "nodeSep": 100,
                "rankSep": 150,
                "animate": True,
                "animationDuration": 500
            },
            "cose": {
                "name": "cose",
                "nodeRepulsion": 4000,
                "idealEdgeLength": 100,
                "edgeElasticity": 100,
                "nestingFactor": 5,
                "gravity": 80,
                "numIter": 1000,
                "animate": True,
                "animationDuration": 500
            },
            "breadthfirst": {
                "name": "breadthfirst",
                "directed": True,
                "spacingFactor": 1.5,
                "animate": True,
                "animationDuration": 500
            }
        }