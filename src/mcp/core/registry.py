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
from ..servers.rnaseq_server import RNASeqMCPServer
from ..servers.scrnaseq_server import scRNASeqMCPServer
from ..servers.data_server import DataMCPServer
from ..servers.visualization_server import VisualizationMCPServer


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
        
        # Register default servers
        self._register_default_servers()
    
    def _register_default_servers(self):
        """Register default MCP servers"""
        
        # RNA-seq server
        self.register_server_config(
            name="rnaseq",
            server_class=RNASeqMCPServer,
            enabled=True,
            auto_connect=True
        )
        
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
        """Get analysis insights for agent context"""
        context = self.get_aggregated_context()
        
        if "error" in context:
            return "MCP system not available"
        
        insights = []
        
        # Add general status
        connected_servers = context.get("connected_servers", [])
        if connected_servers:
            insights.append(f"Connected MCP servers: {', '.join(connected_servers)}")
        else:
            insights.append("No MCP servers connected")
        
        # Add server-specific insights
        server_contexts = context.get("server_contexts", {})
        
        for server_name, server_context in server_contexts.items():
            if analysis_type == "all" or server_context.get("analysis_type") == analysis_type:
                insights.append(f"\n{server_name.upper()} Server Status:")
                
                # Data status
                if server_context.get("data_uploaded"):
                    insights.append("✅ Data uploaded and available")
                    
                    # Add data summary if available
                    data_summary = server_context.get("data_summary", {})
                    if data_summary:
                        if "genes" in data_summary and "samples" in data_summary:
                            insights.append(f"📊 Data: {data_summary['genes']} genes × {data_summary['samples']} samples")
                else:
                    insights.append("❌ No data uploaded")
                
                # Pipeline status
                pipeline_status = server_context.get("pipeline_status", {})
                if pipeline_status:
                    for step, completed in pipeline_status.items():
                        if isinstance(completed, bool):
                            status = "✅" if completed else "⏳"
                            insights.append(f"{status} {step.replace('_', ' ').title()}")
                        elif isinstance(completed, (int, float)):
                            insights.append(f"📈 {step.replace('_', ' ').title()}: {completed}")
                
                # Available tools
                available_tools = len(server_context.get("available_tools", []))
                if available_tools > 0:
                    insights.append(f"🔧 {available_tools} tools available")
        
        return "\n".join(insights) if insights else "No analysis insights available"
    
    def get_suggested_actions(self) -> List[str]:
        """Get suggested next actions based on current state"""
        context = self.get_aggregated_context()
        suggestions = []
        
        if "error" in context:
            suggestions.append("Initialize MCP system")
            return suggestions
        
        server_contexts = context.get("server_contexts", {})
        
        for server_name, server_context in server_contexts.items():
            analysis_type = server_context.get("analysis_type", "")
            
            if analysis_type == "rnaseq":
                if not server_context.get("data_uploaded"):
                    suggestions.append("Upload RNA-seq counts and metadata files")
                else:
                    pipeline_status = server_context.get("pipeline_status", {})
                    
                    if not pipeline_status.get("deseq2_completed"):
                        suggestions.append("Run differential expression analysis (DESeq2)")
                    elif not pipeline_status.get("go_enrichment_completed"):
                        suggestions.append("Perform Gene Ontology enrichment analysis")
                    else:
                        suggestions.append("Create visualizations (PCA, volcano plot, heatmap)")
                        suggestions.append("Explore results and interpret findings")
        
        if not suggestions:
            suggestions.append("All analyses appear complete - explore results or start new analysis")
        
        return suggestions
    
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


# Global registry instance
mcp_registry = MCPRegistry()


async def get_mcp_registry() -> MCPRegistry:
    """Get the global MCP registry instance"""
    if not mcp_registry._initialized:
        await mcp_registry.initialize()
    return mcp_registry 