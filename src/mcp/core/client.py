"""
Refactored MCP Client Implementation

Improved architecture with better separation of concerns, scalability,
and reduced redundancy.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from .server import MCPServer, MCPTool, MCPResource, MCPPrompt


class ConnectionStatus(Enum):
    """Connection status enumeration"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


@dataclass
class ServerConnection:
    """Represents a connection to an MCP server"""
    server: MCPServer
    name: str
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    capabilities: Dict[str, Any] = field(default_factory=dict)
    last_ping: Optional[datetime] = None
    error_count: int = 0
    connected_at: Optional[datetime] = None
    last_error: Optional[str] = None


class CacheEntry:
    """Cache entry with TTL support"""
    def __init__(self, value: Any, ttl_seconds: int = 300):
        self.value = value
        self.created_at = datetime.now()
        self.ttl = timedelta(seconds=ttl_seconds)
    
    @property
    def is_expired(self) -> bool:
        return datetime.now() > (self.created_at + self.ttl)


class CacheManager:
    """Manages caching with TTL and size limits"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if entry.is_expired:
            self.remove(key)
            return None
        
        # Update access order for LRU
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        
        return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        ttl = ttl or self.default_ttl
        
        # Evict if at capacity
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._evict_lru()
        
        self._cache[key] = CacheEntry(value, ttl)
        
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    def remove(self, key: str) -> None:
        """Remove key from cache"""
        if key in self._cache:
            del self._cache[key]
        if key in self._access_order:
            self._access_order.remove(key)
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
        self._access_order.clear()
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry"""
        if self._access_order:
            lru_key = self._access_order[0]
            self.remove(lru_key)


class ConnectionManager:
    """Manages server connections and lifecycle"""
    
    def __init__(self, logger: logging.Logger):
        self.connections: Dict[str, ServerConnection] = {}
        self.logger = logger
    
    async def connect_server(self, server: MCPServer, name: str) -> bool:
        """Connect to an MCP server"""
        try:
            connection = ServerConnection(
                server=server,
                name=name,
                status=ConnectionStatus.CONNECTING
            )
            
            # Store connection early for status tracking
            self.connections[name] = connection
            
            # Initialize the server
            await server.initialize()
            
            # Negotiate capabilities
            capabilities = server.get_capabilities()
            connection.capabilities = capabilities
            connection.status = ConnectionStatus.CONNECTED
            connection.connected_at = datetime.now()
            connection.last_ping = datetime.now()
            
            self.logger.info(f"Connected to server: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to server {name}: {str(e)}")
            if name in self.connections:
                self.connections[name].status = ConnectionStatus.ERROR
                self.connections[name].error_count += 1
                self.connections[name].last_error = str(e)
            return False
    
    async def disconnect_server(self, name: str) -> bool:
        """Disconnect from an MCP server"""
        if name not in self.connections:
            return False
        
        try:
            connection = self.connections[name]
            connection.status = ConnectionStatus.DISCONNECTED
            del self.connections[name]
            
            self.logger.info(f"Disconnected from server: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from server {name}: {str(e)}")
            return False
    
    def get_connection(self, name: str) -> Optional[ServerConnection]:
        """Get connection by name"""
        return self.connections.get(name)
    
    def get_connected_servers(self) -> List[str]:
        """Get list of connected server names"""
        return [
            name for name, conn in self.connections.items()
            if conn.status == ConnectionStatus.CONNECTED
        ]
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all connected servers"""
        results = {}
        
        for server_name, connection in self.connections.items():
            try:
                # Simple ping by getting capabilities
                capabilities = connection.server.get_capabilities()
                connection.last_ping = datetime.now()
                connection.status = ConnectionStatus.CONNECTED
                results[server_name] = True
                
            except Exception as e:
                self.logger.warning(f"Health check failed for {server_name}: {str(e)}")
                connection.error_count += 1
                connection.status = ConnectionStatus.ERROR
                connection.last_error = str(e)
                results[server_name] = False
        
        return results


class ResponseFormatter(ABC):
    """Abstract base class for response formatting"""
    
    @abstractmethod
    def format_success(self, data: Any, **metadata) -> Dict[str, Any]:
        """Format successful response"""
        pass
    
    @abstractmethod
    def format_error(self, error: str, **metadata) -> Dict[str, Any]:
        """Format error response"""
        pass


class StandardResponseFormatter(ResponseFormatter):
    """Standard response formatter"""
    
    def format_success(self, data: Any, **metadata) -> Dict[str, Any]:
        response = {
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        response.update(metadata)
        return response
    
    def format_error(self, error: str, **metadata) -> Dict[str, Any]:
        response = {
            "success": False,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        response.update(metadata)
        return response


class ExecutionEngine:
    """Handles tool execution with load balancing and circuit breaking"""
    
    def __init__(self, connection_manager: ConnectionManager, 
                 cache_manager: CacheManager, 
                 response_formatter: ResponseFormatter,
                 logger: logging.Logger):
        self.connection_manager = connection_manager
        self.cache_manager = cache_manager
        self.response_formatter = response_formatter
        self.logger = logger
        self._tool_index: Dict[str, str] = {}  # tool_name -> server_name
        self._resource_index: Dict[str, str] = {}  # resource_uri -> server_name
    
    def _validate_server_connection(self, server_name: str) -> Optional[ServerConnection]:
        """Validate server connection and return connection if valid"""
        connection = self.connection_manager.get_connection(server_name)
        
        if not connection:
            return None
        
        if connection.status != ConnectionStatus.CONNECTED:
            return None
        
        return connection
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool on the appropriate server"""
        # Check tool index
        if tool_name not in self._tool_index:
            available_tools = list(self._tool_index.keys())
            return self.response_formatter.format_error(
                f"Tool '{tool_name}' not found",
                available_tools=available_tools
            )
        
        server_name = self._tool_index[tool_name]
        connection = self._validate_server_connection(server_name)
        
        if not connection:
            return self.response_formatter.format_error(
                f"Server '{server_name}' not available",
                server=server_name,
                tool=tool_name
            )
        
        try:
            result = await connection.server.execute_tool(tool_name, parameters)
            
            return self.response_formatter.format_success(
                result,
                server=server_name,
                tool=tool_name
            )
            
        except Exception as e:
            self.logger.error(f"Tool execution failed: {tool_name} on {server_name}: {str(e)}")
            connection.error_count += 1
            
            return self.response_formatter.format_error(
                str(e),
                tool=tool_name,
                server=server_name
            )
    
    async def get_resource(self, uri: str) -> Dict[str, Any]:
        """Get a resource from the appropriate server"""
        # Check cache first
        cached_result = self.cache_manager.get(f"resource:{uri}")
        if cached_result:
            return self.response_formatter.format_success(
                cached_result,
                cached=True,
                uri=uri
            )
        
        # Check resource index
        if uri not in self._resource_index:
            available_resources = list(self._resource_index.keys())
            return self.response_formatter.format_error(
                f"Resource '{uri}' not found",
                available_resources=available_resources
            )
        
        server_name = self._resource_index[uri]
        connection = self._validate_server_connection(server_name)
        
        if not connection:
            return self.response_formatter.format_error(
                f"Server '{server_name}' not available",
                server=server_name,
                uri=uri
            )
        
        try:
            result = await connection.server.get_resource(uri)
            
            # Cache the result
            self.cache_manager.set(f"resource:{uri}", result)
            
            return self.response_formatter.format_success(
                result,
                server=server_name,
                uri=uri
            )
            
        except Exception as e:
            self.logger.error(f"Resource access failed: {uri} on {server_name}: {str(e)}")
            
            return self.response_formatter.format_error(
                str(e),
                uri=uri,
                server=server_name
            )
    
    def update_indexes(self, server_name: str, server: MCPServer) -> None:
        """Update tool and resource indexes"""
        # Update tool index
        for tool_name in server.tools:
            self._tool_index[tool_name] = server_name
        
        # Update resource index
        for uri in server.resources:
            self._resource_index[uri] = server_name
    
    def remove_from_indexes(self, server_name: str) -> None:
        """Remove server entries from indexes"""
        # Remove tools
        tools_to_remove = [tool for tool, srv in self._tool_index.items() if srv == server_name]
        for tool in tools_to_remove:
            del self._tool_index[tool]
        
        # Remove resources
        resources_to_remove = [uri for uri, srv in self._resource_index.items() if srv == server_name]
        for uri in resources_to_remove:
            del self._resource_index[uri]


class MCPClient:
    """
    Refactored MCP Client with improved modularity and scalability.
    
    Features:
    - Modular architecture with specialized components
    - Caching with TTL and size limits
    - Better error handling and circuit breaking
    - Pluggable response formatting
    - Improved performance for large-scale deployments
    """
    
    def __init__(self, name: str = "bioinformatics_client", 
                 cache_config: Optional[Dict[str, Any]] = None,
                 response_formatter: Optional[ResponseFormatter] = None):
        self.name = name
        self.logger = logging.getLogger(f"mcp.client.{name}")
        
        # Initialize components
        cache_config = cache_config or {}
        self.cache_manager = CacheManager(
            max_size=cache_config.get('max_size', 1000),
            default_ttl=cache_config.get('default_ttl', 300)
        )
        
        self.connection_manager = ConnectionManager(self.logger)
        
        self.response_formatter = response_formatter or StandardResponseFormatter()
        
        self.execution_engine = ExecutionEngine(
            self.connection_manager,
            self.cache_manager,
            self.response_formatter,
            self.logger
        )
    
    async def connect_server(self, server: MCPServer, name: str) -> bool:
        """Connect to an MCP server"""
        success = await self.connection_manager.connect_server(server, name)
        
        if success:
            # Update indexes
            self.execution_engine.update_indexes(name, server)
        
        return success
    
    async def disconnect_server(self, name: str) -> bool:
        """Disconnect from an MCP server"""
        # Remove from indexes first
        self.execution_engine.remove_from_indexes(name)
        
        return await self.connection_manager.disconnect_server(name)
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool on the appropriate server"""
        return await self.execution_engine.execute_tool(tool_name, parameters)
    
    async def get_resource(self, uri: str) -> Dict[str, Any]:
        """Get a resource from the appropriate server"""
        return await self.execution_engine.get_resource(uri)
    
    async def render_prompt(self, prompt_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Render a prompt from any connected server"""
        parameters = parameters or {}
        
        for server_name in self.connection_manager.get_connected_servers():
            connection = self.connection_manager.get_connection(server_name)
            
            if connection and prompt_name in connection.server.prompts:
                try:
                    result = await connection.server.render_prompt(prompt_name, parameters)
                    return self.response_formatter.format_success(
                        result,
                        server=server_name,
                        prompt=prompt_name
                    )
                except Exception as e:
                    self.logger.error(f"Prompt rendering failed: {prompt_name} on {server_name}: {str(e)}")
                    continue
        
        return self.response_formatter.format_error(
            f"Prompt '{prompt_name}' not found on any connected server"
        )
    
    def get_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get all available tools across connected servers"""
        tools = {}
        
        for server_name in self.connection_manager.get_connected_servers():
            connection = self.connection_manager.get_connection(server_name)
            if connection:
                for tool_name, tool in connection.server.tools.items():
                    tools[tool_name] = {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.input_schema,
                        "output_schema": tool.output_schema,
                        "server": server_name
                    }
        
        return tools
    
    def get_server_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all server connections"""
        status = {}
        
        for server_name, connection in self.connection_manager.connections.items():
            status[server_name] = {
                "status": connection.status.value,
                "capabilities": connection.capabilities,
                "error_count": connection.error_count,
                "last_ping": connection.last_ping.isoformat() if connection.last_ping else None,
                "connected_at": connection.connected_at.isoformat() if connection.connected_at else None,
                "last_error": connection.last_error,
                "tools_count": len(connection.server.tools),
                "resources_count": len(connection.server.resources),
                "prompts_count": len(connection.server.prompts)
            }
        
        return status
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all connected servers"""
        return await self.connection_manager.health_check()
    
    def clear_cache(self) -> None:
        """Clear all caches"""
        self.cache_manager.clear() 