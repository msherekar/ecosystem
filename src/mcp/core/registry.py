"""
MCP Registry

Central registry for managing MCP servers and providing unified access
to tools, resources, and capabilities across the bioinformatics platform.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

import streamlit as st
from .client import MCPClient
from .server import MCPServer
from .strategy import strategy_registry
from .config import config_manager
from .analysis_interface import get_analysis_provider


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server"""
    name: str
    server_class: type
    enabled: bool = True
    auto_connect: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


class MCPRegistry:
    """
    Central registry for MCP servers in the bioinformatics platform.
    
    Manages:
    - Server registration and lifecycle
    - Tool discovery and execution
    - Context aggregation for agent awareness
    - Health monitoring
    """
    
    def __init__(self):
        self.client = MCPClient("bioinformatics_platform")
        self.server_configs: Dict[str, MCPServerConfig] = {}
        self.logger = logging.getLogger("mcp.registry")
        self._initialized = False
        
        # Load configuration and register servers
        self._load_configuration()
    
    def _load_configuration(self):
        """Load server configurations from config manager"""
        try:
            # Get enabled servers from configuration
            enabled_configs = config_manager.get_enabled_servers()
            
            for server_config in enabled_configs:
                # Load server class dynamically
                server_class = config_manager.load_server_class(server_config.class_path)
                
                if server_class:
                    self.register_server_config(
                        name=server_config.name,
                        server_class=server_class,
                        enabled=server_config.enabled,
                        auto_connect=server_config.auto_connect,
                        config=server_config.config
                    )
                else:
                    self.logger.warning(f"Failed to load server class for {server_config.name}")
            
            self.logger.info("Server configurations loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            # Fallback to default servers
            self._register_default_servers()
    
    def _register_default_servers(self):
        """Fallback: Register default MCP servers when configuration fails"""
        try:
            # Import servers dynamically to avoid circular imports
            from ..servers.scrnaseq_server import scRNASeqMCPServer
            from ..servers.data_server import DataMCPServer
            from ..servers.visualization_server import VisualizationMCPServer
            
            # scRNA-seq server
            self.register_server_config(
                name="scrnaseq",
                server_class=scRNASeqMCPServer,
                enabled=True,
                auto_connect=True
            )
            
            # Data management server
            self.register_server_config(
                name="data",
                server_class=DataMCPServer,
                enabled=True,
                auto_connect=True
            )
            
            # Visualization server
            self.register_server_config(
                name="visualization",
                server_class=VisualizationMCPServer,
                enabled=True,
                auto_connect=True
            )
            
            self.logger.info("Default servers registered as fallback")
            
        except Exception as e:
            self.logger.error(f"Failed to register default servers: {e}")
    
    def register_server_config(self, 
                              name: str, 
                              server_class: type,
                              enabled: bool = True,
                              auto_connect: bool = True,
                              config: Optional[Dict[str, Any]] = None) -> None:
        """Register a server configuration"""
        
        server_config = MCPServerConfig(
            name=name,
            server_class=server_class,
            enabled=enabled,
            auto_connect=auto_connect,
            config=config or {}
        )
        
        self.server_configs[name] = server_config
        self.logger.info(f"Registered server config: {name}")
    
    async def initialize(self) -> bool:
        """Initialize the MCP registry and connect to servers"""
        if self._initialized:
            return True
        
        try:
            # Connect to auto-connect servers
            for name, config in self.server_configs.items():
                if config.enabled and config.auto_connect:
                    await self.connect_server(name)
            
            self._initialized = True
            self.logger.info("MCP Registry initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP Registry: {str(e)}")
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
        
        try:
            # Create server instance
            server = config.server_class()
            
            # Connect via client
            success = await self.client.connect_server(server, name)
            
            if success:
                self.logger.info(f"Connected to server: {name}")
            else:
                self.logger.error(f"Failed to connect to server: {name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error connecting to server {name}: {str(e)}")
            return False
    
    async def disconnect_server(self, name: str) -> bool:
        """Disconnect from a specific server"""
        return await self.client.disconnect_server(name)
    
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
    
    def get_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get all available tools across connected servers"""
        if not self._initialized:
            return {}
        
        return self.client.get_available_tools()
    
    def get_available_resources(self) -> Dict[str, Dict[str, Any]]:
        """Get all available resources across connected servers"""
        if not self._initialized:
            return {}
        
        return self.client.get_available_resources()
    
    def get_available_prompts(self) -> Dict[str, Dict[str, Any]]:
        """Get all available prompts across connected servers"""
        if not self._initialized:
            return {}
        
        return self.client.get_available_prompts()
    
    def get_tool_definitions_for_agent(self) -> List[Dict[str, Any]]:
        """Get tool definitions in format suitable for agent/LLM"""
        if not self._initialized:
            return []
        
        return self.client.get_tool_definitions_for_agent()
    
    def get_aggregated_context(self) -> Dict[str, Any]:
        """Get aggregated context from all connected servers"""
        if not self._initialized:
            return {"error": "Registry not initialized"}
        
        return self.client.get_aggregated_context()
    
    def get_server_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all server connections"""
        if not self._initialized:
            return {}
        
        return self.client.get_server_status()
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all connected servers"""
        if not self._initialized:
            await self.initialize()
        
        return await self.client.health_check()
    
    def get_analysis_insights(self, analysis_type: str = "all") -> str:
        """Get analysis insights using centralized analysis providers"""
        context = self.get_aggregated_context()
        
        if "error" in context:
            return "MCP system not available"
        
        all_insights = []
        server_contexts = context.get("server_contexts", {})
        
        # Use centralized analysis providers for each server
        for server_name, server_context in server_contexts.items():
            server_analysis_type = server_context.get("server_type", "")
            
            # Filter by analysis type if specified
            if analysis_type != "all" and server_analysis_type != analysis_type:
                continue
            
            if server_analysis_type:
                try:
                    # Get centralized analysis provider
                    provider = get_analysis_provider(server_analysis_type)
                    insights = provider.get_analysis_insights()
                    
                    if insights and insights != f"No {server_analysis_type} analysis insights available":
                        all_insights.append(f"{server_name.upper()}: {insights}")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to get insights for {server_analysis_type}: {e}")
                    # Fallback to basic insight
                    if server_context.get("data_uploaded", False):
                        all_insights.append(f"{server_name.upper()}: Data uploaded and available")
        
        # Add general status if no specific insights
        if not all_insights:
            connected_servers = context.get("connected_servers", [])
            if connected_servers:
                return f"Connected MCP servers: {', '.join(connected_servers)} - Ready for analysis"
            else:
                return "No MCP servers connected"
        
        return " | ".join(all_insights)
    
    def get_suggested_actions(self) -> List[str]:
        """Get suggested next actions using centralized analysis providers"""
        context = self.get_aggregated_context()
        
        if "error" in context:
            return ["Initialize MCP system"]
        
        all_suggestions = []
        server_contexts = context.get("server_contexts", {})
        
        # Use centralized analysis providers for each server
        for server_name, server_context in server_contexts.items():
            analysis_type = server_context.get("server_type", "")
            
            if analysis_type:
                try:
                    # Get centralized analysis provider
                    provider = get_analysis_provider(analysis_type)
                    suggestions = provider.get_suggested_actions()
                    all_suggestions.extend(suggestions)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to get suggestions for {analysis_type}: {e}")
                    # Fallback to generic suggestions
                    if not server_context.get("data_uploaded", False):
                        all_suggestions.append(f"Upload data for {analysis_type} analysis")
                    else:
                        all_suggestions.append(f"Continue {analysis_type} analysis workflow")
        
        # Remove duplicates while preserving order
        unique_suggestions = []
        seen = set()
        for suggestion in all_suggestions:
            if suggestion not in seen:
                unique_suggestions.append(suggestion)
                seen.add(suggestion)
        
        # Return top suggestions or default
        if unique_suggestions:
            return unique_suggestions[:5]  # Top 5 suggestions
        else:
            return ["All analyses appear complete - explore results or start new analysis"]
    
    def format_context_for_agent(self) -> str:
        """Format context information for agent consumption"""
        insights = self.get_analysis_insights()
        suggestions = self.get_suggested_actions()
        
        context_text = f"""
Current Analysis State:
{insights}

Suggested Next Actions:
{chr(10).join(f"• {action}" for action in suggestions)}

Available Tools: {len(self.get_available_tools())}
Available Resources: {len(self.get_available_resources())}
"""
        
        return context_text.strip()
    
    def register_analysis_strategy(self, analysis_type: str, strategy_class: type):
        """Register a new analysis strategy"""
        strategy_registry.register_strategy(analysis_type, strategy_class)
        self.logger.info(f"Registered strategy for {analysis_type}")
    
    def add_server_from_config(self, server_name: str):
        """Add a server from configuration"""
        server_config = config_manager.get_server_config(server_name)
        
        if server_config:
            server_class = config_manager.load_server_class(server_config.class_path)
            
            if server_class:
                self.register_server_config(
                    name=server_config.name,
                    server_class=server_class,
                    enabled=server_config.enabled,
                    auto_connect=server_config.auto_connect,
                    config=server_config.config
                )
                return True
        
        return False


# Global registry instance
mcp_registry = MCPRegistry()


async def get_mcp_registry() -> MCPRegistry:
    """Get the global MCP registry instance"""
    if not mcp_registry._initialized:
        await mcp_registry.initialize()
    return mcp_registry 