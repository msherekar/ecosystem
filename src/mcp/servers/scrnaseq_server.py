"""
scRNA-seq MCP Server - Clean, Modular Version with Automated Tool Discovery

Provides MCP interface for single-cell RNA-seq analysis tools including:
- Data upload and validation
- Quality control and filtering
- Normalization and scaling
- Dimensionality reduction (PCA, UMAP)
- Clustering and cell type identification
- Differential expression analysis
- Trajectory analysis

Now uses automated tool discovery to eliminate manual configuration.
"""

import asyncio
import pandas as pd
import numpy as np
from typing import Any, Dict, Optional, List
import streamlit as st
import logging
from functools import wraps

from ..core.server import MCPServer
from ..core.analysis_interface import get_analysis_provider
from ..core.tool_registry import get_auto_tool_configs
from ..core.resource_registry import get_auto_resource_configs
from ..core.prompt_registry import get_auto_prompt_configs
from src.modules.scrna_seq.workflow import run_scrnaseq_pipeline
from .scrnaseq_handlers import scRNASeqHandlers
from ..core.tool_registry import ToolConfig


def require_data(func):
    """Decorator to check data availability and handle common errors"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        # Check data availability
        data_check = self.handlers._check_data_availability()
        if not data_check["available"]:
            return {
                "success": False,
                "message": data_check["message"],
                "required_action": data_check.get("required_action")
            }
        
        try:
            return await func(self, *args, **kwargs)
        except ImportError as e:
            return {
                "success": False,
                "error_type": "dependency_missing",
                "message": f"Required package missing: {str(e)}",
                "suggestion": "Install required packages: pip install scanpy pandas"
            }
        except ValueError as e:
            return {
                "success": False,
                "error_type": "invalid_data",
                "message": f"Data validation failed: {str(e)}",
                "suggestion": "Check data format and upload valid .h5ad file"
            }
        except Exception as e:
            self.logger.error(f"{func.__name__} failed: {str(e)}")
            return {
                "success": False,
                "error_type": "unknown",
                "message": f"Unexpected error: {str(e)}",
                "suggestion": "Contact support with error details"
            }
    return wrapper


class scRNASeqMCPServer(MCPServer):
    """MCP Server for single-cell RNA-seq analysis tools with automated tool discovery"""
    
    def __init__(self):
        super().__init__("scrnaseq_server", "1.0.0")
        self.logger = logging.getLogger("mcp.scrnaseq")
        self.handlers = scRNASeqHandlers(self.logger)
        self.analysis_provider = get_analysis_provider("scrnaseq")
        
        # 🚀 AUTOMATED TOOL DISCOVERY - No more manual configuration!
        self.tool_configs = get_auto_tool_configs(self.handlers)
        
        # 🚀 AUTOMATED RESOURCE DISCOVERY - No more manual resource registration!
        self.resource_configs = get_auto_resource_configs(self.handlers)
        
        # 🚀 AUTOMATED PROMPT DISCOVERY - No more manual prompt registration!
        self.prompt_configs = get_auto_prompt_configs(self.handlers)
        
        # Add context tools that use centralized analysis provider
        self._add_context_tools()
    
    def _add_context_tools(self):
        """Add context tools that use centralized analysis provider"""
        context_tools = {
            "get_analysis_insights": {
                "description": "Get detailed insights about current scRNA-seq analysis state and results",
                "handler": self._get_analysis_insights_wrapper,
                "properties": {},
                "category": "context"
            },
            "get_pipeline_context": {
                "description": "Get current pipeline context including completed steps and suggested next actions",
                "handler": self._get_pipeline_context_wrapper,
                "properties": {},
                "category": "context"
            }
        }
        
        # Convert to ToolConfig objects and add to tool_configs
        for name, config in context_tools.items():
            tool_config = ToolConfig(
                name=name,
                description=config["description"],
                handler=config["handler"],
                properties=config["properties"],
                required=[],
                category=config["category"]
            )
            self.tool_configs[name] = tool_config
    
    async def initialize(self) -> None:
        """Initialize scRNA-seq server with automated tool discovery"""
        
        # Register all tools from automated discovery
        await self._register_all_tools()
        
        # Register all resources from automated discovery
        await self._register_all_resources()
        
        # Register all prompts from automated discovery
        await self._register_all_prompts()
    
        self.logger.info(f"Initialized scRNA-seq server with {len(self.tool_configs)} auto-discovered tools, {len(self.resource_configs)} auto-discovered resources, and {len(self.prompt_configs)} auto-discovered prompts")
    
    async def _register_all_tools(self):
        """Register all tools from automated discovery"""
        for name, tool_config in self.tool_configs.items():
            self._register_scrnaseq_tool(
                name=name,
                description=tool_config.description,
                handler=tool_config.handler,
                properties=tool_config.properties,
                required=tool_config.required
            )
            
        self.logger.info(f"Registered {len(self.tool_configs)} tools automatically")
    
    async def _register_all_resources(self):
        """Register all resources from automated discovery"""
        for uri, resource_config in self.resource_configs.items():
            self.register_resource(
                uri=resource_config.uri,
                name=resource_config.name,
                description=resource_config.description,
                mime_type=resource_config.mime_type,
                metadata=resource_config.metadata
            )
            
        self.logger.info(f"Registered {len(self.resource_configs)} resources automatically")

    async def _register_all_prompts(self):
        """Register all prompts from automated discovery"""
        for name, prompt_config in self.prompt_configs.items():
            self.register_prompt(
                name=prompt_config.name,
                description=prompt_config.description,
                template=prompt_config.template,
                parameters=prompt_config.parameters
            )
            
        self.logger.info(f"Registered {len(self.prompt_configs)} prompts automatically")
    
    def _get_server_specific_context(self) -> Dict[str, Any]:
        """Get scRNA-seq specific context for MCP registry"""
        # Use centralized analysis provider instead of duplicated logic
        return self.analysis_provider.get_analysis_context()
    
    def _register_scrnaseq_tool(self, name: str, description: str, handler, 
                               properties: Dict = None, required: List = None):
        """Helper to register scRNA-seq tools with consistent schema"""
        self.register_tool(
            name=name,
            description=description,
            input_schema={
                "type": "object",
                "properties": properties or {},
                "required": required or []
            },
            handler=handler
        )
    
    # Wrapper methods for centralized analysis provider
    async def _get_analysis_insights_wrapper(self) -> Dict[str, Any]:
        """Wrapper for centralized analysis insights"""
        try:
            insights = self.analysis_provider.get_analysis_insights()
            return {
                "success": True,
                "message": insights,
                "summary": "Retrieved scRNA-seq analysis insights"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get analysis insights: {str(e)}"
            }
    
    async def _get_pipeline_context_wrapper(self) -> Dict[str, Any]:
        """Wrapper for centralized pipeline context"""
        try:
            context = self.analysis_provider.get_analysis_context()
            return {
                "success": True,
                "context": context,
                "message": f"Current step: {context.get('current_step', 'Unknown')}",
                "summary": "Retrieved pipeline context and suggested actions"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get pipeline context: {str(e)}"
            }


# Test code to verify the module works independently
if __name__ == "__main__":
    import asyncio
    
    async def test_scrnaseq_server():
        """Test scRNASeqMCPServer functionality"""
        print("Testing scRNASeqMCPServer...")
        
        # Test server creation
        server = scRNASeqMCPServer()
        print(f"✅ Created scRNA-seq server: {server.name} v{server.version}")
        
        # Test initialization
        await server.initialize()
        print(f"✅ Server initialized with {len(server.tools)} tools")
        
        # Test auto-discovered tools
        print(f"✅ Auto-discovered {len(server.tool_configs)} tool configs")
        
        # Test auto-discovered resources
        print(f"✅ Auto-discovered {len(server.resource_configs)} resource configs")
        
        # Test auto-discovered prompts
        print(f"✅ Auto-discovered {len(server.prompt_configs)} prompt configs")
        
        # Test context methods
        context = server._get_server_specific_context()
        print(f"✅ Server context: {len(context)} keys")
        
        # Test analysis provider
        insights = server.analysis_provider.get_analysis_insights()
        print(f"✅ Analysis insights: {len(insights)} chars")
        
        # Test suggested actions
        actions = server.analysis_provider.get_suggested_actions()
        print(f"✅ Suggested actions: {len(actions)}")
        
        print("🎉 All scRNASeqMCPServer tests passed!")
    
    # Run test
    asyncio.run(test_scrnaseq_server()) 