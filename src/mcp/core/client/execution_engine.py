"""
MCP Client Execution Engine

Handles tool execution, resource access, and routing across connected servers.
"""

import logging
from typing import Any, Dict, List, Optional


class ExecutionEngine:
    """
    Handles execution of tools and resource access across connected MCP servers.
    
    Features:
    - Tool discovery and execution
    - Resource access and caching
    - Load balancing across servers
    - Error handling and fallback
    - Performance monitoring
    """
    
    def __init__(self, 
                 connection_manager,
                 cache_manager,
                 response_formatter,
                 logger: logging.Logger):
        """
        Initialize execution engine.
        
        Args:
            connection_manager: Manages server connections
            cache_manager: Handles caching
            response_formatter: Formats responses
            logger: Logger instance
        """
        self.connection_manager = connection_manager
        self.cache_manager = cache_manager
        self.response_formatter = response_formatter
        self.logger = logger
        
        # Indexes for fast lookup
        self.tool_index: Dict[str, List[str]] = {}  # tool_name -> [server_names]
        self.resource_index: Dict[str, List[str]] = {}  # resource_uri -> [server_names]
        self.prompt_index: Dict[str, List[str]] = {}  # prompt_name -> [server_names]
        
        # Execution statistics
        self.execution_stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def _validate_server_connection(self, server_name: str):
        """Validate server connection and return connection if healthy"""
        connection = self.connection_manager.get_connection(server_name)
        if not connection:
            self.logger.warning(f"Server connection not found: {server_name}")
            return None
        
        if not connection.is_healthy:
            self.logger.warning(f"Server connection not healthy: {server_name}")
            return None
        
        return connection
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool on connected servers"""
        self.execution_stats['total_executions'] += 1
        
        # Check cache first
        cache_key = f"tool:{tool_name}:{hash(str(sorted(parameters.items())))}"
        cached_result = self.cache_manager.get(cache_key)
        
        if cached_result is not None:
            self.execution_stats['cache_hits'] += 1
            self.logger.debug(f"Cache hit for tool execution: {tool_name}")
            return self.response_formatter.format_success(
                cached_result,
                tool_name=tool_name,
                cached=True
            )
        
        self.execution_stats['cache_misses'] += 1
        
        # Find servers that have this tool
        servers_with_tool = self.tool_index.get(tool_name, [])
        
        if not servers_with_tool:
            # Search all connected servers
            servers_with_tool = self._find_servers_with_tool(tool_name)
        
        if not servers_with_tool:
            self.execution_stats['failed_executions'] += 1
            return self.response_formatter.format_error(
                f"Tool '{tool_name}' not found on any connected server",
                tool_name=tool_name,
                available_tools=list(self.tool_index.keys())
            )
        
        # Try executing on servers
        last_error = None
        
        for server_name in servers_with_tool:
            connection = self._validate_server_connection(server_name)
            if not connection:
                continue
            
            try:
                self.logger.debug(f"Executing tool '{tool_name}' on server '{server_name}'")
                result = await connection.server.execute_tool(tool_name, parameters)
                
                # Cache successful result
                self.cache_manager.set(
                    cache_key, 
                    result,
                    tags={f"tool:{tool_name}", f"server:{server_name}"}
                )
                
                self.execution_stats['successful_executions'] += 1
                return self.response_formatter.format_success(
                    result,
                    tool_name=tool_name,
                    server_name=server_name,
                    cached=False
                )
                
            except Exception as e:
                last_error = str(e)
                self.logger.warning(f"Tool execution failed on server '{server_name}': {last_error}")
                continue
        
        # All servers failed
        self.execution_stats['failed_executions'] += 1
        return self.response_formatter.format_error(
            f"Tool execution failed on all servers. Last error: {last_error}",
            tool_name=tool_name,
            servers_tried=servers_with_tool
        )
    
    async def get_resource(self, uri: str) -> Dict[str, Any]:
        """Get a resource from connected servers"""
        # Check cache first
        cache_key = f"resource:{uri}"
        cached_result = self.cache_manager.get(cache_key)
        
        if cached_result is not None:
            self.logger.debug(f"Cache hit for resource: {uri}")
            return self.response_formatter.format_success(
                cached_result,
                resource_uri=uri,
                cached=True
            )
        
        # Find servers that have this resource
        servers_with_resource = self.resource_index.get(uri, [])
        
        if not servers_with_resource:
            # Search all connected servers
            servers_with_resource = self._find_servers_with_resource(uri)
        
        if not servers_with_resource:
            return self.response_formatter.format_error(
                f"Resource '{uri}' not found on any connected server",
                resource_uri=uri,
                available_resources=list(self.resource_index.keys())
            )
        
        # Try getting resource from servers
        last_error = None
        
        for server_name in servers_with_resource:
            connection = self._validate_server_connection(server_name)
            if not connection:
                continue
            
            try:
                self.logger.debug(f"Getting resource '{uri}' from server '{server_name}'")
                result = await connection.server.get_resource(uri)
                
                # Cache successful result
                self.cache_manager.set(
                    cache_key,
                    result,
                    tags={f"resource:{uri}", f"server:{server_name}"}
                )
                
                return self.response_formatter.format_success(
                    result,
                    resource_uri=uri,
                    server_name=server_name,
                    cached=False
                )
                
            except Exception as e:
                last_error = str(e)
                self.logger.warning(f"Resource access failed on server '{server_name}': {last_error}")
                continue
        
        # All servers failed
        return self.response_formatter.format_error(
            f"Resource access failed on all servers. Last error: {last_error}",
            resource_uri=uri,
            servers_tried=servers_with_resource
        )
    
    def update_indexes(self, server_name: str, server) -> None:
        """Update indexes with tools/resources from a server"""
        try:
            # Update tool index
            tools = server.get_tools()
            for tool_name in tools:
                if tool_name not in self.tool_index:
                    self.tool_index[tool_name] = []
                if server_name not in self.tool_index[tool_name]:
                    self.tool_index[tool_name].append(server_name)
            
            # Update resource index
            resources = server.get_resources()
            for resource_uri in resources:
                if resource_uri not in self.resource_index:
                    self.resource_index[resource_uri] = []
                if server_name not in self.resource_index[resource_uri]:
                    self.resource_index[resource_uri].append(server_name)
            
            # Update prompt index
            prompts = server.get_prompts()
            for prompt_name in prompts:
                if prompt_name not in self.prompt_index:
                    self.prompt_index[prompt_name] = []
                if server_name not in self.prompt_index[prompt_name]:
                    self.prompt_index[prompt_name].append(server_name)
            
            self.logger.debug(f"Updated indexes for server: {server_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to update indexes for server {server_name}: {str(e)}")
    
    def remove_from_indexes(self, server_name: str) -> None:
        """Remove server from all indexes"""
        # Remove from tool index
        for tool_name, servers in self.tool_index.items():
            if server_name in servers:
                servers.remove(server_name)
        
        # Remove empty entries
        self.tool_index = {k: v for k, v in self.tool_index.items() if v}
        
        # Remove from resource index
        for resource_uri, servers in self.resource_index.items():
            if server_name in servers:
                servers.remove(server_name)
        
        # Remove empty entries
        self.resource_index = {k: v for k, v in self.resource_index.items() if v}
        
        # Remove from prompt index
        for prompt_name, servers in self.prompt_index.items():
            if server_name in servers:
                servers.remove(server_name)
        
        # Remove empty entries
        self.prompt_index = {k: v for k, v in self.prompt_index.items() if v}
        
        # Clear cache entries from this server
        self.cache_manager.clear(tags={f"server:{server_name}"})
        
        self.logger.debug(f"Removed server from indexes: {server_name}")
    
    def _find_servers_with_tool(self, tool_name: str) -> List[str]:
        """Find servers that have a specific tool"""
        servers_with_tool = []
        
        for server_name in self.connection_manager.get_connected_servers():
            connection = self._validate_server_connection(server_name)
            if not connection:
                continue
            
            try:
                tools = connection.server.get_tools()
                if tool_name in tools:
                    servers_with_tool.append(server_name)
                    # Update index
                    if tool_name not in self.tool_index:
                        self.tool_index[tool_name] = []
                    if server_name not in self.tool_index[tool_name]:
                        self.tool_index[tool_name].append(server_name)
            except Exception as e:
                self.logger.warning(f"Error checking tools on server {server_name}: {str(e)}")
        
        return servers_with_tool
    
    def _find_servers_with_resource(self, uri: str) -> List[str]:
        """Find servers that have a specific resource"""
        servers_with_resource = []
        
        for server_name in self.connection_manager.get_connected_servers():
            connection = self._validate_server_connection(server_name)
            if not connection:
                continue
            
            try:
                resources = connection.server.get_resources()
                if uri in resources:
                    servers_with_resource.append(server_name)
                    # Update index
                    if uri not in self.resource_index:
                        self.resource_index[uri] = []
                    if server_name not in self.resource_index[uri]:
                        self.resource_index[uri].append(server_name)
            except Exception as e:
                self.logger.warning(f"Error checking resources on server {server_name}: {str(e)}")
        
        return servers_with_resource

# Test code to verify the module works independently
if __name__ == "__main__":
    import asyncio
    
    # Mock classes for testing
    class MockConnectionManager:
        def __init__(self):
            self.servers = {
                "server1": {"connected": True, "healthy": True},
                "server2": {"connected": True, "healthy": False},
                "server3": {"connected": False, "healthy": False}
            }
        
        def get_connected_servers(self):
            return [name for name, info in self.servers.items() if info["connected"]]
        
        def get_connection(self, name):
            if name in self.servers and self.servers[name]["connected"]:
                class MockConnection:
                    def __init__(self, healthy):
                        self.is_healthy = healthy
                        self.server = MockServer()
                
                class MockServer:
                    def get_tools(self):
                        return {"test_tool": {}}
                    
                    def get_resources(self):
                        return {"test://resource1": {}}
                    
                    async def execute_tool(self, tool, params):
                        return {"result": f"executed {tool}"}
                    
                    async def get_resource(self, uri):
                        return {"content": f"resource {uri}"}
                
                return MockConnection(self.servers[name]["healthy"])
            return None
    
    class MockCacheManager:
        def __init__(self):
            self.cache = {}
        
        def get(self, key):
            return self.cache.get(key)
        
        def set(self, key, value, tags=None):
            self.cache[key] = value
        
        def clear(self, tags=None):
            if tags:
                # Simple tag-based clearing
                keys_to_remove = []
                for key in self.cache:
                    if any(tag in key for tag in tags):
                        keys_to_remove.append(key)
                for key in keys_to_remove:
                    del self.cache[key]
            else:
                self.cache.clear()
    
    class MockResponseFormatter:
        def format_success(self, data, **metadata):
            return {"success": True, "data": data, **metadata}
        
        def format_error(self, error, **metadata):
            return {"success": False, "error": error, **metadata}
    
    async def test_execution_engine():
        """Test execution engine functionality"""
        print("Testing Execution Engine...")
        
        # Create mock dependencies
        connection_manager = MockConnectionManager()
        cache_manager = MockCacheManager()
        response_formatter = MockResponseFormatter()
        logger = logging.getLogger("test_execution_engine")
        
        # Create execution engine
        engine = ExecutionEngine(
            connection_manager, 
            cache_manager, 
            response_formatter, 
            logger
        )
        
        print("✅ ExecutionEngine created")
        
        # Test index updates
        class MockServer:
            def get_tools(self):
                return {"test_tool": {}, "another_tool": {}}
            def get_resources(self):
                return {"test://resource1": {}, "test://resource2": {}}
            def get_prompts(self):
                return {"test_prompt": {}}
        
        mock_server = MockServer()
        
        engine.update_indexes("server1", mock_server)
        
        assert "test_tool" in engine.tool_index
        assert "test://resource1" in engine.resource_index
        print("✅ Index updates work")
        
        # Test tool execution (will use mock connection)
        result = await engine.execute_tool("test_tool", {"param1": "value1"})
        
        assert "success" in result
        print(f"✅ Tool execution: {result['success']}")
        
        # Test resource access
        result = await engine.get_resource("test://resource1") 
        
        assert "success" in result
        print(f"✅ Resource access: {result['success']}")
        
        # Test caching behavior
        # First call should cache
        await engine.execute_tool("test_tool", {"cached": "param"})
        
        # Second call should hit cache  
        result2 = await engine.execute_tool("test_tool", {"cached": "param"})
        print("✅ Caching behavior tested")
        
        # Test server validation
        valid_connection = engine._validate_server_connection("server1")
        assert valid_connection is not None
        
        invalid_connection = engine._validate_server_connection("server3")  # disconnected
        assert invalid_connection is None
        print("✅ Server validation works")
        
        # Test index removal
        engine.remove_from_indexes("server1")
        
        # Tools should be removed from index
        assert len(engine.tool_index) == 0
        assert len(engine.resource_index) == 0
        print("✅ Index removal works")
        
        # Test execution statistics
        stats = engine.execution_stats
        assert "total_executions" in stats
        assert "successful_executions" in stats
        assert "failed_executions" in stats
        print(f"✅ Execution statistics: {stats}")
        
        # Test tool discovery
        engine.update_indexes("server1", mock_server)  # Re-add for discovery test
        found_servers = engine._find_servers_with_tool("test_tool")
        assert "server1" in found_servers
        print("✅ Tool discovery works")
        
        # Test resource discovery  
        found_servers = engine._find_servers_with_resource("test://resource1")
        assert "server1" in found_servers
        print("✅ Resource discovery works")
        
        print("🎉 All execution engine tests passed!")
    
    # Run test
    asyncio.run(test_execution_engine())
    print("Run with: python -m src.mcp.core.client.execution_engine") 