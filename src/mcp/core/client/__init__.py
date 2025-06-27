"""
Core MCP Client Implementation

Provides client functionality for connecting to and interacting with MCP servers.
Handles connection management, caching, and request routing.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from .connection_manager import ConnectionManager, ServerConnection, ConnectionStatus
from .cache_manager import CacheManager
from .execution_engine import ExecutionEngine
from .response_formatter import ResponseFormatter, StandardResponseFormatter

# Re-export commonly used classes
from .connection_manager import ConnectionStatus
from .response_formatter import ResponseFormatter, StandardResponseFormatter


class MCPClient:
    """
    Main MCP Client for connecting to and interacting with MCP servers.
    
    Provides high-level interface for:
    - Server connection management
    - Tool execution
    - Resource access
    - Prompt rendering
    - Caching and performance optimization
    """
    
    def __init__(self, 
                 name: str = "bioinformatics_client",
                 cache_config: Optional[Dict[str, Any]] = None,
                 response_formatter: Optional[ResponseFormatter] = None):
        """
        Initialize MCP Client.
        
        Args:
            name: Client identifier
            cache_config: Cache configuration options
            response_formatter: Custom response formatter
        """
        self.name = name
        self.logger = logging.getLogger(f"mcp.client.{name}")
        
        # Initialize cache configuration
        cache_config = cache_config or {}
        max_cache_size = cache_config.get('max_size', 1000)
        default_ttl = cache_config.get('default_ttl', 300)
        
        # Initialize components
        self.cache_manager = CacheManager(max_cache_size, default_ttl)
        self.connection_manager = ConnectionManager(self.logger)
        self.response_formatter = response_formatter or StandardResponseFormatter()
        self.execution_engine = ExecutionEngine(
            self.connection_manager,
            self.cache_manager,
            self.response_formatter,
            self.logger
        )
        
        self.logger.info(f"Initialized MCP Client: {name}")
    
    async def connect_server(self, server, name: str) -> bool:
        """Connect to an MCP server"""
        success = await self.connection_manager.connect_server(server, name)
        if success:
            # Update execution engine indexes
            self.execution_engine.update_indexes(name, server)
        return success
    
    async def disconnect_server(self, name: str) -> bool:
        """Disconnect from an MCP server"""
        success = await self.connection_manager.disconnect_server(name)
        if success:
            self.execution_engine.remove_from_indexes(name)
        return success
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool on connected servers"""
        return await self.execution_engine.execute_tool(tool_name, parameters)
    
    async def get_resource(self, uri: str) -> Dict[str, Any]:
        """Get a resource from connected servers"""
        return await self.execution_engine.get_resource(uri)
    
    async def render_prompt(self, prompt_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Render a prompt template with parameters"""
        parameters = parameters or {}
        
        # Find server with this prompt
        for server_name in self.connection_manager.get_connected_servers():
            connection = self.connection_manager.get_connection(server_name)
            if connection:
                try:
                    prompts = connection.server.get_prompts()
                    if prompt_name in prompts:
                        result = await connection.server.render_prompt(prompt_name, parameters)
                        return self.response_formatter.format_success(
                            result,
                            server_name=server_name,
                            prompt_name=prompt_name
                        )
                except Exception as e:
                    self.logger.error(f"Error rendering prompt {prompt_name} on {server_name}: {str(e)}")
        
        return self.response_formatter.format_error(
            f"Prompt '{prompt_name}' not found on any connected server"
        )
    
    def get_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get all available tools from connected servers"""
        all_tools = {}
        
        for server_name in self.connection_manager.get_connected_servers():
            connection = self.connection_manager.get_connection(server_name)
            if connection:
                try:
                    server_tools = connection.server.get_tools()
                    for tool_name, tool in server_tools.items():
                        all_tools[tool_name] = {
                            "name": tool.name,
                            "description": tool.description,
                            "input_schema": tool.input_schema,
                            "server": server_name
                        }
                except Exception as e:
                    self.logger.error(f"Error getting tools from {server_name}: {str(e)}")
        
        return all_tools
    
    def get_server_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all server connections"""
        status = {}
        
        for server_name, connection in self.connection_manager.connections.items():
            status[server_name] = {
                "status": connection.status.value,
                "connected_at": connection.connected_at.isoformat() if connection.connected_at else None,
                "last_ping": connection.last_ping.isoformat() if connection.last_ping else None,
                "error_count": connection.error_count,
                "last_error": connection.last_error,
                "capabilities": list(connection.capabilities.keys()) if connection.capabilities else []
            }
        
        return status
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all connected servers"""
        return await self.connection_manager.health_check()
    
    def clear_cache(self) -> None:
        """Clear the client cache"""
        self.cache_manager.clear()
        self.logger.info("Cache cleared")
    
    def get_available_resources(self) -> Dict[str, Dict[str, Any]]:
        """Get all available resources from connected servers"""
        all_resources = {}
        
        for server_name in self.connection_manager.get_connected_servers():
            connection = self.connection_manager.get_connection(server_name)
            if connection:
                try:
                    server_resources = connection.server.get_resources()
                    for resource_uri, resource in server_resources.items():
                        all_resources[resource_uri] = {
                            "uri": resource.uri,
                            "name": resource.name,
                            "description": resource.description,
                            "mime_type": resource.mime_type,
                            "server": server_name
                        }
                except Exception as e:
                    self.logger.error(f"Error getting resources from {server_name}: {str(e)}")
        
        return all_resources
    
    def get_available_prompts(self) -> Dict[str, Dict[str, Any]]:
        """Get all available prompts from connected servers"""
        all_prompts = {}
        
        for server_name in self.connection_manager.get_connected_servers():
            connection = self.connection_manager.get_connection(server_name)
            if connection:
                try:
                    server_prompts = connection.server.get_prompts()
                    for prompt_name, prompt in server_prompts.items():
                        all_prompts[prompt_name] = {
                            "name": prompt.name,
                            "description": prompt.description,
                            "arguments": prompt.schema,
                            "server": server_name
                        }
                except Exception as e:
                    self.logger.error(f"Error getting prompts from {server_name}: {str(e)}")
        
        return all_prompts
    
    def get_tool_definitions_for_agent(self) -> List[Dict[str, Any]]:
        """Get tool definitions in a format suitable for agent systems"""
        tools = self.get_available_tools()
        
        return [
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_info["description"],
                    "parameters": tool_info["input_schema"]
                }
            }
            for tool_name, tool_info in tools.items()
        ]
    
    def get_aggregated_context(self) -> Dict[str, Any]:
        """Get aggregated context information about all connected servers"""
        return {
            "client_name": self.name,
            "connected_servers": self.connection_manager.get_connected_servers(),
            "server_status": self.get_server_status(),
            "available_tools": list(self.get_available_tools().keys()),
            "available_resources": list(self.get_available_resources().keys()),
            "available_prompts": list(self.get_available_prompts().keys()),
            "cache_stats": {
                "size": len(self.cache_manager._cache),
                "max_size": self.cache_manager.max_size
            }
        }


# Example usage function
async def test_mcp_client():
    """Example usage of MCPClient"""
    client = MCPClient("test_client")
    
    # Example server would be connected here
    # await client.connect_server(server_instance, "example_server")
    
    # Example tool execution
    # result = await client.execute_tool("analyze_data", {"data": "example"})
    
    print("MCP Client test completed") 