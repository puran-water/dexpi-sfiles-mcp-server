"""Main MCP server implementation for engineering drawings."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from mcp import Resource, Tool, server
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import TextContent

from .tools.dexpi_tools import DexpiTools
from .tools.sfiles_tools import SfilesTools
from .tools.project_tools import ProjectTools
from .tools.validation_tools import ValidationTools
from .tools.schema_tools import SchemaTools
from .tools.graph_tools import GraphTools
from .tools.search_tools import SearchTools
from .resources.graph_resources import GraphResourceProvider
from .converters.graph_converter import UnifiedGraphConverter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EngineeringDrawingMCPServer:
    """MCP Server for engineering drawing generation and manipulation."""
    
    def __init__(self):
        """Initialize the MCP server with empty model stores."""
        self.dexpi_models: Dict[str, Any] = {}
        self.flowsheets: Dict[str, Any] = {}
        
        # Initialize tool handlers with both stores for cross-conversion
        self.dexpi_tools = DexpiTools(self.dexpi_models, self.flowsheets)
        self.sfiles_tools = SfilesTools(self.flowsheets, self.dexpi_models)
        self.project_tools = ProjectTools(self.dexpi_models, self.flowsheets)
        self.validation_tools = ValidationTools(self.dexpi_models, self.flowsheets)
        self.schema_tools = SchemaTools()
        self.graph_tools = GraphTools(self.dexpi_models, self.flowsheets)
        self.search_tools = SearchTools(self.dexpi_models, self.flowsheets)
        
        # Initialize converters and resources
        self.graph_converter = UnifiedGraphConverter()
        self.resource_provider = GraphResourceProvider(
            self.dexpi_models, 
            self.flowsheets,
            self.graph_converter
        )
        
        # Create MCP server instance
        self.server = Server("engineering-mcp")
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all MCP handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """List all available tools."""
            tools = []
            tools.extend(self.dexpi_tools.get_tools())
            tools.extend(self.sfiles_tools.get_tools())
            tools.extend(self.project_tools.get_tools())
            tools.extend(self.validation_tools.get_tools())
            tools.extend(self.schema_tools.get_tools())
            tools.extend(self.graph_tools.get_tools())
            tools.extend(self.search_tools.get_tools())
            return tools
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Route tool calls to appropriate handlers."""
            try:
                if name.startswith("dexpi_"):
                    result = await self.dexpi_tools.handle_tool(name, arguments)
                elif name.startswith("sfiles_"):
                    result = await self.sfiles_tools.handle_tool(name, arguments)
                elif name.startswith("project_"):
                    result = await self.project_tools.handle_tool(name, arguments)
                elif name.startswith("validate_"):
                    result = await self.validation_tools.handle_tool(name, arguments)
                elif name.startswith("schema_"):
                    result = await self.schema_tools.handle_tool(name, arguments)
                elif name.startswith("graph_"):
                    result = await self.graph_tools.handle_tool(name, arguments)
                elif name.startswith("search_") or name == "query_model_statistics":
                    result = await self.search_tools.handle_tool(name, arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                error_result = {
                    "error": str(e),
                    "tool": name,
                    "arguments": arguments
                }
                return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
        
        @self.server.list_resources()
        async def handle_list_resources() -> list[Resource]:
            """List all available resources."""
            return await self.resource_provider.list_resources()
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> list:
            """Read a specific resource."""
            return await self.resource_provider.read_resource(uri)
    
    async def run(self):
        """Run the MCP server."""
        from mcp.server.stdio import stdio_server
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="engineering-mcp",
                    server_version="0.1.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )


def main():
    """Main entry point for the MCP server."""
    server = EngineeringDrawingMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()