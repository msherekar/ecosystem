"""
MCP Client Implementation

Handles communication with MCP servers and provides a unified interface
for the agent system to discover and use tools across multiple servers.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field

import streamlit as st
from .server import MCPServer, MCPTool, MCPResource, MCPPrompt


@dataclass
class ServerConnection:
    """Represents a connection to an MCP server"""
    server: MCPServer
    name: str
    status: str = "disconnected"
    capabilities: Dict[str, Any] = field(default_factory=dict)
    last_ping: Optional[float] = None
    error_count: int = 0


class MCPClient:
    """
    MCP Client for connecting to and managing multiple MCP servers.
    
    Provides unified interface for:
    - Server discovery and connection
    - Tool execution across servers
    - Resource access
    - Context aggregation for agent awareness
    """
    
    def __init__(self, name: str = "bioinformatics_client"):
        self.name = name
        self.connections: Dict[str, ServerConnection] = {}
        self.logger = logging.getLogger(f"mcp.client.{name}")
        self._tool_cache: Dict[str, str] = {}  # tool_name -> server_name
        self._resource_cache: Dict[str, str] = {}  # resource_uri -> server_name
        
    async def connect_server(self, server: MCPServer, name: str) -> bool:
        """Connect to an MCP server"""
        try:
            # Initialize the server
            await server.initialize()
            
            # Create connection
            connection = ServerConnection(
                server=server,
                name=name,
                status="connecting"
            )
            
            # Negotiate capabilities
            capabilities = server.get_capabilities()
            connection.capabilities = capabilities
            connection.status = "connected"
            
            # Store connection
            self.connections[name] = connection
            
            # Update caches
            await self._update_caches(name, server)
            
            self.logger.info(f"Connected to server: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to server {name}: {str(e)}")
            if name in self.connections:
                self.connections[name].status = "error"
                self.connections[name].error_count += 1
            return False
    
    async def disconnect_server(self, name: str) -> bool:
        """Disconnect from an MCP server"""
        if name not in self.connections:
            return False
        
        try:
            connection = self.connections[name]
            connection.status = "disconnected"
            
            # Remove from caches
            self._remove_from_caches(name)
            
            # Remove connection
            del self.connections[name]
            
            self.logger.info(f"Disconnected from server: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from server {name}: {str(e)}")
            return False
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool on the appropriate server"""
        if tool_name not in self._tool_cache:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found",
                "available_tools": list(self._tool_cache.keys())
            }
        
        server_name = self._tool_cache[tool_name]
        
        if server_name not in self.connections:
            return {
                "success": False,
                "error": f"Server '{server_name}' not connected"
            }
        
        connection = self.connections[server_name]
        
        if connection.status != "connected":
            return {
                "success": False,
                "error": f"Server '{server_name}' not available (status: {connection.status})"
            }
        
        try:
            result = await connection.server.execute_tool(tool_name, parameters)
            
            # Add server context to result
            result["server"] = server_name
            result["timestamp"] = asyncio.get_event_loop().time()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Tool execution failed: {tool_name} on {server_name}: {str(e)}")
            connection.error_count += 1
            
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name,
                "server": server_name
            }
    
    async def get_resource(self, uri: str) -> Dict[str, Any]:
        """Get a resource from the appropriate server"""
        if uri not in self._resource_cache:
            return {
                "success": False,
                "error": f"Resource '{uri}' not found",
                "available_resources": list(self._resource_cache.keys())
            }
        
        server_name = self._resource_cache[uri]
        
        if server_name not in self.connections:
            return {
                "success": False,
                "error": f"Server '{server_name}' not connected"
            }
        
        connection = self.connections[server_name]
        
        try:
            result = await connection.server.get_resource(uri)
            result["server"] = server_name
            return result
            
        except Exception as e:
            self.logger.error(f"Resource access failed: {uri} on {server_name}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "uri": uri,
                "server": server_name
            }
    
    async def render_prompt(self, prompt_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Render a prompt from any connected server"""
        for server_name, connection in self.connections.items():
            if connection.status == "connected" and prompt_name in connection.server.prompts:
                try:
                    result = await connection.server.render_prompt(prompt_name, parameters)
                    result["server"] = server_name
                    return result
                except Exception as e:
                    self.logger.error(f"Prompt rendering failed: {prompt_name} on {server_name}: {str(e)}")
                    continue
        
        return {
            "success": False,
            "error": f"Prompt '{prompt_name}' not found on any connected server"
        }
    
    def get_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get all available tools across connected servers"""
        tools = {}
        
        for server_name, connection in self.connections.items():
            if connection.status == "connected":
                for tool_name, tool in connection.server.tools.items():
                    tools[tool_name] = {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.input_schema,
                        "output_schema": tool.output_schema,
                        "server": server_name
                    }
        
        return tools
    
    def get_available_resources(self) -> Dict[str, Dict[str, Any]]:
        """Get all available resources across connected servers"""
        resources = {}
        
        for server_name, connection in self.connections.items():
            if connection.status == "connected":
                for uri, resource in connection.server.resources.items():
                    resources[uri] = {
                        "uri": resource.uri,
                        "name": resource.name,
                        "description": resource.description,
                        "mime_type": resource.mime_type,
                        "metadata": resource.metadata,
                        "server": server_name
                    }
        
        return resources
    
    def get_available_prompts(self) -> Dict[str, Dict[str, Any]]:
        """Get all available prompts across connected servers"""
        prompts = {}
        
        for server_name, connection in self.connections.items():
            if connection.status == "connected":
                for prompt_name, prompt in connection.server.prompts.items():
                    prompts[prompt_name] = {
                        "name": prompt.name,
                        "description": prompt.description,
                        "template": prompt.template,
                        "parameters": prompt.parameters,
                        "server": server_name
                    }
        
        return prompts
    
    def get_aggregated_context(self) -> Dict[str, Any]:
        """Get aggregated context from all connected servers"""
        context = {
            "client": self.name,
            "timestamp": asyncio.get_event_loop().time(),
            "connected_servers": [],
            "total_tools": 0,
            "total_resources": 0,
            "total_prompts": 0,
            "server_contexts": {}
        }
        
        for server_name, connection in self.connections.items():
            if connection.status == "connected":
                server_context = connection.server.get_analysis_context()
                context["server_contexts"][server_name] = server_context
                context["connected_servers"].append(server_name)
                context["total_tools"] += len(connection.server.tools)
                context["total_resources"] += len(connection.server.resources)
                context["total_prompts"] += len(connection.server.prompts)
        
        return context
    
    def get_server_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all server connections"""
        status = {}
        
        for server_name, connection in self.connections.items():
            status[server_name] = {
                "status": connection.status,
                "capabilities": connection.capabilities,
                "error_count": connection.error_count,
                "last_ping": connection.last_ping,
                "tools_count": len(connection.server.tools),
                "resources_count": len(connection.server.resources),
                "prompts_count": len(connection.server.prompts)
            }
        
        return status
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all connected servers"""
        results = {}
        
        for server_name, connection in self.connections.items():
            try:
                # Simple ping by getting capabilities
                capabilities = connection.server.get_capabilities()
                connection.last_ping = asyncio.get_event_loop().time()
                connection.status = "connected"
                results[server_name] = True
                
            except Exception as e:
                self.logger.warning(f"Health check failed for {server_name}: {str(e)}")
                connection.error_count += 1
                connection.status = "error"
                results[server_name] = False
        
        return results
    
    async def _update_caches(self, server_name: str, server: MCPServer) -> None:
        """Update tool and resource caches"""
        # Update tool cache
        for tool_name in server.tools:
            self._tool_cache[tool_name] = server_name
        
        # Update resource cache
        for uri in server.resources:
            self._resource_cache[uri] = server_name
    
    def _remove_from_caches(self, server_name: str) -> None:
        """Remove server entries from caches"""
        # Remove tools
        tools_to_remove = [tool for tool, srv in self._tool_cache.items() if srv == server_name]
        for tool in tools_to_remove:
            del self._tool_cache[tool]
        
        # Remove resources
        resources_to_remove = [uri for uri, srv in self._resource_cache.items() if srv == server_name]
        for uri in resources_to_remove:
            del self._resource_cache[uri]
    
    def get_tool_definitions_for_agent(self) -> List[Dict[str, Any]]:
        """Get tool definitions in format suitable for agent/LLM"""
        tools = []
        
        for tool_name, tool_info in self.get_available_tools().items():
            tool_def = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_info["description"],
                    "parameters": tool_info["input_schema"]
                }
            }
            tools.append(tool_def)
        
        return tools 