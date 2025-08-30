"""MCP resource provider for graph data exposure."""

import json
import logging
from typing import Any, Dict, List

from mcp import Resource
from mcp.types import TextContent
from pydexpi.dexpi_classes.dexpiModel import DexpiModel
from pydexpi.loaders import JsonSerializer
from Flowsheet_Class.flowsheet import Flowsheet

from ..converters.graph_converter import UnifiedGraphConverter

logger = logging.getLogger(__name__)


class GraphResourceProvider:
    """Expose graphs as MCP resources for direct consumption."""
    
    def __init__(
        self,
        dexpi_models: Dict[str, DexpiModel],
        flowsheets: Dict[str, Flowsheet],
        graph_converter: UnifiedGraphConverter
    ):
        """Initialize the resource provider.
        
        Args:
            dexpi_models: Store of DEXPI models
            flowsheets: Store of SFILES flowsheets
            graph_converter: Graph conversion utility
        """
        self.dexpi_models = dexpi_models
        self.flowsheets = flowsheets
        self.converter = graph_converter
        self.json_serializer = JsonSerializer()
    
    async def list_resources(self) -> List[Resource]:
        """List all available resources.
        
        Returns:
            List of available MCP resources
        """
        resources = []
        
        # Add DEXPI model resources
        for model_id, model in self.dexpi_models.items():
            # JSON resource
            resources.append(Resource(
                uri=f"dexpi/{model_id}/json",
                name=f"P&ID {model_id} (JSON)",
                mimeType="application/json",
                description="Full DEXPI semantic model in JSON format"
            ))
            
            # GraphML resource
            resources.append(Resource(
                uri=f"dexpi/{model_id}/graphml",
                name=f"P&ID {model_id} (GraphML)",
                mimeType="application/graphml+xml",
                description="P&ID topology for ML/analysis"
            ))
            
            # NetworkX resource
            resources.append(Resource(
                uri=f"dexpi/{model_id}/networkx",
                name=f"P&ID {model_id} (NetworkX)",
                mimeType="application/json",
                description="NetworkX graph representation"
            ))
        
        # Add SFILES flowsheet resources
        for fs_id, flowsheet in self.flowsheets.items():
            # SFILES string resource
            resources.append(Resource(
                uri=f"sfiles/{fs_id}/string",
                name=f"Flowsheet {fs_id} (SFILES)",
                mimeType="text/plain",
                description="Compact SFILES string representation"
            ))
            
            # GraphML resource
            resources.append(Resource(
                uri=f"sfiles/{fs_id}/graphml",
                name=f"Flowsheet {fs_id} (GraphML)",
                mimeType="application/graphml+xml",
                description="Flowsheet topology graph"
            ))
            
            # NetworkX resource
            resources.append(Resource(
                uri=f"sfiles/{fs_id}/networkx",
                name=f"Flowsheet {fs_id} (NetworkX)",
                mimeType="application/json",
                description="NetworkX graph representation"
            ))
        
        return resources
    
    async def read_resource(self, uri: str) -> List[TextContent]:
        """Read a specific resource by URI.
        
        Returns list of TextContent for MCP protocol compliance.
        
        Args:
            uri: Resource URI to read
            
        Returns:
            List of TextContent with resource data
            
        Raises:
            ValueError: If resource not found
        """
        parts = uri.split("/")
        
        if len(parts) < 3:
            raise ValueError(f"Invalid resource URI: {uri}")
        
        resource_type = parts[0]
        model_id = parts[1]
        format_type = parts[2]
        
        # Get content as string
        if resource_type == "dexpi":
            content = await self._read_dexpi_resource(model_id, format_type)
        elif resource_type == "sfiles":
            content = await self._read_sfiles_resource(model_id, format_type)
        else:
            raise ValueError(f"Unknown resource type: {resource_type}")
        
        # Return as MCP-compliant TextContent list
        return [TextContent(type="text", text=content)]
    
    async def _read_dexpi_resource(self, model_id: str, format_type: str) -> str:
        """Read DEXPI model resource.
        
        Args:
            model_id: ID of the DEXPI model
            format_type: Format to return (json, graphml, networkx)
            
        Returns:
            Resource content as string
            
        Raises:
            ValueError: If model not found or format not supported
        """
        if model_id not in self.dexpi_models:
            raise ValueError(f"DEXPI model {model_id} not found")
        
        model = self.dexpi_models[model_id]
        
        if format_type == "json":
            # Export as JSON
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                self.json_serializer.save(model, f.name)
                temp_path = f.name
            
            with open(temp_path, 'r') as f:
                content = f.read()
            
            os.unlink(temp_path)
            return content
        
        elif format_type == "graphml":
            # Export as GraphML
            return self.converter.dexpi_to_graphml(model)
        
        elif format_type == "networkx":
            # Export as NetworkX JSON
            import networkx as nx
            graph = self.converter.dexpi_to_networkx(model)
            graph_data = nx.node_link_data(graph)
            return json.dumps(graph_data, indent=2)
        
        else:
            raise ValueError(f"Unsupported format for DEXPI: {format_type}")
    
    async def _read_sfiles_resource(self, flowsheet_id: str, format_type: str) -> str:
        """Read SFILES flowsheet resource.
        
        Args:
            flowsheet_id: ID of the flowsheet
            format_type: Format to return (string, graphml, networkx)
            
        Returns:
            Resource content as string
            
        Raises:
            ValueError: If flowsheet not found or format not supported
        """
        if flowsheet_id not in self.flowsheets:
            raise ValueError(f"Flowsheet {flowsheet_id} not found")
        
        flowsheet = self.flowsheets[flowsheet_id]
        
        if format_type == "string":
            # Export as SFILES string
            return flowsheet.convert_to_sfiles(version="v2", canonical=True)
        
        elif format_type == "graphml":
            # Export as GraphML
            return self.converter.sfiles_to_graphml(flowsheet)
        
        elif format_type == "networkx":
            # Export as NetworkX JSON
            import networkx as nx
            graph = self.converter.sfiles_to_networkx(flowsheet)
            graph_data = nx.node_link_data(graph)
            return json.dumps(graph_data, indent=2)
        
        else:
            raise ValueError(f"Unsupported format for SFILES: {format_type}")
    
    def get_resource_metadata(self, uri: str) -> Dict[str, Any]:
        """Get metadata about a resource.
        
        Args:
            uri: Resource URI
            
        Returns:
            Dictionary with resource metadata
        """
        parts = uri.split("/")
        
        if len(parts) < 3:
            return {"error": "Invalid URI"}
        
        resource_type = parts[0]
        model_id = parts[1]
        format_type = parts[2]
        
        metadata = {
            "uri": uri,
            "type": resource_type,
            "id": model_id,
            "format": format_type
        }
        
        # Add model-specific metadata
        if resource_type == "dexpi" and model_id in self.dexpi_models:
            model = self.dexpi_models[model_id]
            if model.metaData:
                metadata["project_name"] = model.metaData.projectName
                metadata["drawing_number"] = model.metaData.drawingNumber
                metadata["revision"] = model.metaData.revision
        
        elif resource_type == "sfiles" and model_id in self.flowsheets:
            flowsheet = self.flowsheets[model_id]
            metadata["num_units"] = flowsheet.state.number_of_nodes()
            metadata["num_streams"] = flowsheet.state.number_of_edges()
            if hasattr(flowsheet, 'name'):
                metadata["name"] = flowsheet.name
            if hasattr(flowsheet, 'type'):
                metadata["flowsheet_type"] = flowsheet.type
        
        return metadata
