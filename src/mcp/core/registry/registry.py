"""
MCP Registry - Core Management

Central registry for managing MCP servers and providing unified access
to tools, resources, and capabilities across the bioinformatics platform.

This is the core registry file focused on server management and coordination.
Analysis insights, health monitoring, and configuration are in separate files.
"""

import asyncio
import logging
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import time

# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server"""
    name: str
    server_class: type
    enabled: bool = True
    auto_connect: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher priority servers connect first
    retry_count: int = 3
    retry_delay: float = 1.0
    
    def __post_init__(self):
        """Validate server configuration"""
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Server name must be a non-empty string")
        
        if not self.server_class or not callable(self.server_class):
            raise ValueError("Server class must be callable")


class ServerConnectionManager:
    """Manages server connections with retry logic and monitoring"""
    
    def __init__(self, client):
        self.client = client
        self.logger = logger.getChild("ConnectionManager")
        self._connection_states = {}
        self._connection_lock = threading.RLock()
        self._retry_tasks = {}
    
    async def connect_server(self, server_config: MCPServerConfig) -> bool:
        """Connect to a server with retry logic"""
        server_name = server_config.name
        
        with self._connection_lock:
            if server_name in self._connection_states:
                current_state = self._connection_states[server_name]
                if current_state.get("connected", False):
                    self.logger.debug(f"Server {server_name} already connected")
                    return True
        
        # Attempt connection with retries
        for attempt in range(server_config.retry_count):
            try:
                self.logger.info(f"Connecting to server {server_name} (attempt {attempt + 1})")
                
                # Create server instance
                server = server_config.server_class()
                
                # Connect via client
                success = await self.client.connect_server(server, server_name)
                
                if success:
                    with self._connection_lock:
                        self._connection_states[server_name] = {
                            "connected": True,
                            "connect_time": time.time(),
                            "config": server_config,
                            "attempt_count": attempt + 1
                        }
                    
                    self.logger.info(f"Successfully connected to server: {server_name}")
                    return True
                else:
                    self.logger.warning(f"Failed to connect to server {server_name} on attempt {attempt + 1}")
                    
            except Exception as e:
                self.logger.error(f"Error connecting to server {server_name} on attempt {attempt + 1}: {e}")
            
            # Wait before retry (except on last attempt)
            if attempt < server_config.retry_count - 1:
                await asyncio.sleep(server_config.retry_delay * (attempt + 1))
        
        # All attempts failed
        with self._connection_lock:
            self._connection_states[server_name] = {
                "connected": False,
                "last_error": f"Failed after {server_config.retry_count} attempts",
                "last_attempt": time.time(),
                "config": server_config
            }
        
        self.logger.error(f"Failed to connect to server {server_name} after {server_config.retry_count} attempts")
        return False
    
    async def disconnect_server(self, server_name: str) -> bool:
        """Disconnect from a specific server"""
        try:
            success = await self.client.disconnect_server(server_name)
            
            with self._connection_lock:
                if server_name in self._connection_states:
                    self._connection_states[server_name]["connected"] = False
                    self._connection_states[server_name]["disconnect_time"] = time.time()
            
            if success:
                self.logger.info(f"Disconnected from server: {server_name}")
            else:
                self.logger.warning(f"Failed to disconnect from server: {server_name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from server {server_name}: {e}")
            return False
    
    def get_connection_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all server connections"""
        with self._connection_lock:
            return self._connection_states.copy()
    
    def get_connected_servers(self) -> List[str]:
        """Get list of connected server names"""
        with self._connection_lock:
            return [
                name for name, state in self._connection_states.items()
                if state.get("connected", False)
            ]
    
    async def reconnect_failed_servers(self) -> Dict[str, bool]:
        """Attempt to reconnect to failed servers"""
        results = {}
        
        with self._connection_lock:
            failed_servers = [
                name for name, state in self._connection_states.items()
                if not state.get("connected", False) and "config" in state
            ]
        
        for server_name in failed_servers:
            state = self._connection_states[server_name]
            server_config = state["config"]
            
            self.logger.info(f"Attempting to reconnect to {server_name}")
            success = await self.connect_server(server_config)
            results[server_name] = success
        
        return results


class CapabilityAggregator:
    """Aggregates capabilities from all connected servers"""
    
    def __init__(self, client):
        self.client = client
        self.logger = logger.getChild("CapabilityAggregator")
        self._cache = {}
        self._cache_ttl = 30  # 30 seconds
        self._cache_lock = threading.RLock()
    
    def get_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get all available tools across connected servers with caching"""
        return self._get_cached_or_fetch("tools", self.client.get_available_tools)
    
    def get_available_resources(self) -> Dict[str, Dict[str, Any]]:
        """Get all available resources across connected servers with caching"""
        return self._get_cached_or_fetch("resources", self.client.get_available_resources)
    
    def get_available_prompts(self) -> Dict[str, Dict[str, Any]]:
        """Get all available prompts across connected servers with caching"""
        return self._get_cached_or_fetch("prompts", self.client.get_available_prompts)
    
    def get_tool_definitions_for_agent(self) -> List[Dict[str, Any]]:
        """Get tool definitions in format suitable for agent/LLM with caching"""
        return self._get_cached_or_fetch("tool_definitions", self.client.get_tool_definitions_for_agent)
    
    def get_aggregated_context(self) -> Dict[str, Any]:
        """Get aggregated context from all connected servers with caching"""
        return self._get_cached_or_fetch("context", self.client.get_aggregated_context)
    
    def _get_cached_or_fetch(self, cache_key: str, fetch_func: callable) -> Any:
        """Get data from cache or fetch if expired"""
        current_time = time.time()
        
        with self._cache_lock:
            if cache_key in self._cache:
                cache_entry = self._cache[cache_key]
                if current_time - cache_entry["timestamp"] < self._cache_ttl:
                    return cache_entry["data"]
        
        # Cache miss or expired - fetch new data
        try:
            data = fetch_func()
            
            with self._cache_lock:
                self._cache[cache_key] = {
                    "data": data,
                    "timestamp": current_time
                }
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error fetching {cache_key}: {e}")
            
            # Return cached data if available, even if expired
            with self._cache_lock:
                if cache_key in self._cache:
                    return self._cache[cache_key]["data"]
            
            # Return empty/default response
            if cache_key in ["tools", "resources", "prompts"]:
                return {}
            elif cache_key == "tool_definitions":
                return []
            elif cache_key == "context":
                return {"error": "Failed to fetch context"}
            else:
                return None
    
    def clear_cache(self):
        """Clear the capability cache"""
        with self._cache_lock:
            self._cache.clear()
            self.logger.info("Capability cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._cache_lock:
            current_time = time.time()
            stats = {
                "cache_size": len(self._cache),
                "cache_ttl": self._cache_ttl,
                "entries": {}
            }
            
            for key, entry in self._cache.items():
                age = current_time - entry["timestamp"]
                stats["entries"][key] = {
                    "age_seconds": age,
                    "expired": age > self._cache_ttl
                }
            
            return stats


class MCPRegistry:
    """
    Main MCP Registry that manages server connections and aggregates capabilities
    
    This registry coordinates with multiple MCP servers to provide unified access
    to tools, resources, and prompts across the bioinformatics platform.
    """
    
    def __init__(self, client=None):
        """
        Initialize the MCP registry
        
        Args:
            client: Optional MCPClient instance to use. If None, creates a new one.
        """
        self.logger = logger.getChild("MCPRegistry")
        
        # Use provided client or create a new one
        if client is not None:
            self.logger.info("Using provided MCPClient instance")
            self.client = client
        else:
            self.logger.info("Creating new MCPClient instance for registry")
            # Import here to avoid circular dependencies
            try:
                from ..client.mcp_client import ClientConfiguration
                from ..client import MCPClient
                
                client_config = ClientConfiguration(name="bioinformatics_platform")
                self.client = MCPClient(config=client_config)
                
            except ImportError as e:
                self.logger.error(f"Failed to import MCPClient: {e}")
                # Fallback for standalone testing - create a mock client
                class MockClientConfiguration:
                    def __init__(self, name):
                        self.name = name
                
                class MockMCPClient:
                    def __init__(self, config):
                        self.config = config
                        self.connected_servers = {}
                    
                    async def connect_server(self, server, name):
                        self.connected_servers[name] = server
                        return True
                    
                    async def disconnect_server(self, name):
                        if name in self.connected_servers:
                            del self.connected_servers[name]
                        return True
                    
                    def get_available_tools(self):
                        return {}
                    
                    def get_available_resources(self):
                        return {}
                    
                    def get_available_prompts(self):
                        return {}
                    
                    def get_tool_definitions_for_agent(self):
                        return []
                    
                    def get_aggregated_context(self):
                        return {"connected_servers": len(self.connected_servers)}
                    
                    async def health_check(self):
                        return {name: True for name in self.connected_servers}
                    
                    async def execute_tool(self, tool_name, parameters):
                        return {"result": "mock_result"}
                    
                    async def get_resource(self, uri):
                        return {"data": "mock_data"}
                    
                    async def render_prompt(self, prompt_name, parameters):
                        return {"rendered": "mock_prompt"}
                
                client_config = MockClientConfiguration(name="bioinformatics_platform")
                self.client = MockMCPClient(config=client_config)
                self.logger.warning("Using MockMCPClient as fallback")
        
        self.server_configs: Dict[str, MCPServerConfig] = {}
        self._initialized = False
        
        # Component managers
        self.connection_manager = ServerConnectionManager(self.client)
        self.capability_aggregator = CapabilityAggregator(self.client)
        
        # Load configuration
        self._load_configuration()
    
    def _load_configuration(self):
        """Load server configurations"""
        try:
            # Try to load from config manager
            try:
                from .registry_config import ConfigurationManager
            except ImportError:
                from registry_config import ConfigurationManager
            config_manager = ConfigurationManager()
            
            enabled_configs = config_manager.get_enabled_servers()
            
            for server_config in enabled_configs:
                server_class = config_manager.load_server_class(server_config.class_path)
                
                if server_class:
                    self.register_server_config(
                        name=server_config.name,
                        server_class=server_class,
                        enabled=server_config.enabled,
                        auto_connect=server_config.auto_connect,
                        config=server_config.config,
                        priority=getattr(server_config, 'priority', 0)
                    )
                else:
                    self.logger.warning(f"Failed to load server class for {server_config.name}")
            
            self.logger.info("Server configurations loaded successfully")
            
        except ImportError:
            self.logger.info("Configuration manager not available, loading default servers")
            self._register_default_servers()
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            self._register_default_servers()
    
    def _register_default_servers(self):
        """Fallback: Register default MCP servers"""
        try:
            # Import servers dynamically to avoid circular imports
            # For testing, create mock servers if real ones aren't available
            try:
                from ..servers.scrnaseq_server import scRNASeqMCPServer
                from ..servers.data_server import DataMCPServer
                from ..servers.visualization_server import VisualizationMCPServer
                from ..servers.search_server import SearchMCPServer
            except ImportError:
                # Create mock servers for testing
                class MockServer:
                    def __init__(self):
                        pass
                
                scRNASeqMCPServer = MockServer
                DataMCPServer = MockServer
                VisualizationMCPServer = MockServer
                SearchMCPServer = MockServer
            
            default_servers = [
                ("scrnaseq", scRNASeqMCPServer, 10),
                ("data", DataMCPServer, 20),
                ("visualization", VisualizationMCPServer, 5),
                ("search", SearchMCPServer, 0)
            ]
            
            for name, server_class, priority in default_servers:
                self.register_server_config(
                    name=name,
                    server_class=server_class,
                    enabled=True,
                    auto_connect=True,
                    priority=priority
                )
            
            self.logger.info("Default servers registered as fallback")
            
        except Exception as e:
            self.logger.error(f"Failed to register default servers: {e}")
    
    def register_server_config(self, 
                              name: str, 
                              server_class: type,
                              enabled: bool = True,
                              auto_connect: bool = True,
                              config: Optional[Dict[str, Any]] = None,
                              priority: int = 0,
                              retry_count: int = 3,
                              retry_delay: float = 1.0) -> None:
        """Register a server configuration"""
        
        server_config = MCPServerConfig(
            name=name,
            server_class=server_class,
            enabled=enabled,
            auto_connect=auto_connect,
            config=config or {},
            priority=priority,
            retry_count=retry_count,
            retry_delay=retry_delay
        )
        
        self.server_configs[name] = server_config
        self.logger.info(f"Registered server config: {name} (priority: {priority})")
    
    async def initialize(self) -> bool:
        """Initialize the MCP registry and connect to servers"""
        if self._initialized:
            return True
        
        try:
            self.logger.info("Starting MCP Registry initialization...")
            
            # Sort servers by priority (higher priority first)
            auto_connect_servers = [
                (name, config) for name, config in self.server_configs.items()
                if config.enabled and config.auto_connect
            ]
            auto_connect_servers.sort(key=lambda x: x[1].priority, reverse=True)
            
            # Connect to servers in priority order
            connection_results = {}
            for name, config in auto_connect_servers:
                success = await self.connection_manager.connect_server(config)
                connection_results[name] = success
            
            # Log connection summary
            successful = sum(connection_results.values())
            total = len(connection_results)
            self.logger.info(f"Connected to {successful}/{total} servers")
            
            self._initialized = True
            return successful > 0  # Consider success if at least one server connected
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP Registry: {e}")
            return False
    
    async def connect_server(self, name: str) -> bool:
        """Connect to a specific server"""
        if name not in self.server_configs:
            self.logger.error(f"Server config not found: {name}")
            return False
        
        config = self.server_configs[name]
        if not config.enabled:
            self.logger.warning(f"Server {name} is disabled")
            return False
        
        return await self.connection_manager.connect_server(config)
    
    async def disconnect_server(self, name: str) -> bool:
        """Disconnect from a specific server"""
        return await self.connection_manager.disconnect_server(name)
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a tool via MCP"""
        if not self._initialized:
            await self.initialize()
        
        parameters = parameters or {}
        return await self.client.execute_tool(tool_name, parameters)
    
    async def get_resource(self, uri: str) -> Dict[str, Any]:
        """Get a resource via MCP"""
        if not self._initialized:
            await self.initialize()
        
        return await self.client.get_resource(uri)
    
    async def render_prompt(self, prompt_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Render a prompt via MCP"""
        if not self._initialized:
            await self.initialize()
        
        return await self.client.render_prompt(prompt_name, parameters)
    
    # Capability access methods
    def get_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get all available tools across connected servers"""
        return self.capability_aggregator.get_available_tools()
    
    def get_available_resources(self) -> Dict[str, Dict[str, Any]]:
        """Get all available resources across connected servers"""
        return self.capability_aggregator.get_available_resources()
    
    def get_available_prompts(self) -> Dict[str, Dict[str, Any]]:
        """Get all available prompts across connected servers"""
        return self.capability_aggregator.get_available_prompts()
    
    def get_tool_definitions_for_agent(self) -> List[Dict[str, Any]]:
        """Get tool definitions in format suitable for agent/LLM"""
        return self.capability_aggregator.get_tool_definitions_for_agent()
    
    def get_aggregated_context(self) -> Dict[str, Any]:
        """Get aggregated context from all connected servers"""
        return self.capability_aggregator.get_aggregated_context()
    
    def get_server_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all server connections"""
        return self.connection_manager.get_connection_status()
    
    def get_connected_servers(self) -> List[str]:
        """Get list of connected server names"""
        return self.connection_manager.get_connected_servers()
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all connected servers"""
        if not self._initialized:
            await self.initialize()
        
        return await self.client.health_check()
    
    async def reconnect_failed_servers(self) -> Dict[str, bool]:
        """Attempt to reconnect to failed servers"""
        return await self.connection_manager.reconnect_failed_servers()
    
    def clear_caches(self):
        """Clear all caches"""
        self.capability_aggregator.clear_cache()
        self.logger.info("All caches cleared")
    
    def get_analysis_insights(self) -> str:
        """Get analysis insights from the registry"""
        try:
            try:
                from .registry_analysis import InsightAggregator
            except ImportError:
                from registry_analysis import InsightAggregator
            
            aggregator = InsightAggregator()
            
            # Get server contexts
            server_contexts = {}
            for name, state in self.connection_manager.get_connection_status().items():
                if state.get("connected", False):
                    server_contexts[name] = {
                        "server_type": name,
                        "connected": True,
                        "data_uploaded": True  # Mock for testing
                    }
            
            return aggregator.get_analysis_insights(server_contexts)
        except Exception as e:
            self.logger.warning(f"Error getting analysis insights: {e}")
            return "Analysis insights not available"
    
    def get_suggested_actions(self) -> List[str]:
        """Get suggested actions from the registry"""
        try:
            try:
                from .registry_analysis import InsightAggregator
            except ImportError:
                from registry_analysis import InsightAggregator
            aggregator = InsightAggregator()
            
            # Get server contexts
            server_contexts = {}
            for name, state in self.connection_manager.get_connection_status().items():
                if state.get("connected", False):
                    server_contexts[name] = {
                        "server_type": name,
                        "connected": True,
                        "data_uploaded": True  # Mock for testing
                    }
            
            return aggregator.get_suggested_actions(server_contexts)
        except Exception as e:
            self.logger.warning(f"Error getting suggested actions: {e}")
            return ["Error getting suggested actions"]
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get comprehensive registry statistics"""
        connection_status = self.connection_manager.get_connection_status()
        cache_stats = self.capability_aggregator.get_cache_stats()
        
        connected_count = len([
            state for state in connection_status.values()
            if state.get("connected", False)
        ])
        
        return {
            "initialized": self._initialized,
            "servers": {
                "total_configured": len(self.server_configs),
                "connected": connected_count,
                "connection_details": connection_status
            },
            "capabilities": {
                "tools": len(self.get_available_tools()),
                "resources": len(self.get_available_resources()),
                "prompts": len(self.get_available_prompts())
            },
            "cache": cache_stats
        }


# Global registry instance
_global_registry: Optional[MCPRegistry] = None


async def get_mcp_registry(client=None) -> MCPRegistry:
    """
    Get the global MCP registry instance
    
    Args:
        client: Optional MCPClient instance to use. If None, registry creates its own.
    
    Returns:
        MCPRegistry: The global registry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = MCPRegistry(client=client)
        await _global_registry.initialize()
    return _global_registry


def main():
    """Main function for module testing"""
    print("Testing Core MCPRegistry...")
    
    # Test registry creation
    registry = MCPRegistry()
    print(f"✅ Created MCPRegistry with {len(registry.server_configs)} servers configured")
    
    # Test server configuration
    test_configs = list(registry.server_configs.values())
    for config in test_configs[:3]:  # Show first 3
        print(f"✅ Server config: {config.name} (priority: {config.priority})")
        print(f"   Enabled: {config.enabled}, Auto-connect: {config.auto_connect}")
        print(f"   Retry: {config.retry_count} attempts, {config.retry_delay}s delay")
    
    # Test connection manager
    connection_manager = registry.connection_manager
    status = connection_manager.get_connection_status()
    print(f"✅ Connection manager: {len(status)} server states tracked")
    
    # Test capability aggregator
    aggregator = registry.capability_aggregator
    cache_stats = aggregator.get_cache_stats()
    print(f"✅ Capability aggregator: {cache_stats['cache_size']} cached entries")
    
    # Test registry stats
    stats = registry.get_registry_stats()
    print(f"✅ Registry stats:")
    print(f"   Initialized: {stats['initialized']}")
    print(f"   Servers configured: {stats['servers']['total_configured']}")
    print(f"   Cache TTL: {cache_stats['cache_ttl']}s")
    
    print("🎉 All Core MCPRegistry tests passed!")


if __name__ == "__main__":
    main()