"""
Core MCP Server Implementation

Provides the base server functionality for all bioinformatics MCP servers.
Handles tool registration, capability negotiation, and request routing.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum

import streamlit as st
from pydantic import BaseModel, Field


class MCPMessageType(Enum):
    """MCP message types based on JSON-RPC 2.0"""
    REQUEST = "request"
    RESPONSE = "response" 
    NOTIFICATION = "notification"
    ERROR = "error"


@dataclass
class MCPCapability:
    """Represents an MCP capability"""
    name: str
    description: str
    supported: bool = True
    metadata: Optional[Dict[str, Any]] = None


class MCPTool(BaseModel):
    """MCP Tool definition"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None
    handler: Optional[Callable] = None
    
    class Config:
        arbitrary_types_allowed = True


class MCPResource(BaseModel):
    """MCP Resource definition"""
    uri: str
    name: str
    description: str
    mime_type: str
    metadata: Optional[Dict[str, Any]] = None


class MCPPrompt(BaseModel):
    """MCP Prompt definition"""
    name: str
    description: str
    template: str
    parameters: Optional[Dict[str, Any]] = None


class MCPServer(ABC):
    """
    Base MCP Server class for bioinformatics applications.
    
    Provides standardized interface for:
    - Tool registration and execution
    - Resource management
    - Prompt templates
    - Context sharing with AI agents
    """
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.prompts: Dict[str, MCPPrompt] = {}
        self.capabilities: Dict[str, MCPCapability] = {}
        self.logger = logging.getLogger(f"mcp.{name}")
        
        # Initialize default capabilities
        self._init_capabilities()
    
    def _init_capabilities(self):
        """Initialize default MCP capabilities"""
        self.capabilities.update({
            "tools": MCPCapability(
                name="tools",
                description="Support for tool execution",
                supported=True
            ),
            "resources": MCPCapability(
                name="resources", 
                description="Support for resource access",
                supported=True
            ),
            "prompts": MCPCapability(
                name="prompts",
                description="Support for prompt templates",
                supported=True
            ),
            "sampling": MCPCapability(
                name="sampling",
                description="Support for LLM sampling requests",
                supported=False
            )
        })
    
    def register_tool(self, 
                     name: str,
                     description: str,
                     input_schema: Dict[str, Any],
                     handler: Callable,
                     output_schema: Optional[Dict[str, Any]] = None) -> None:
        """Register a tool with the MCP server"""
        tool = MCPTool(
            name=name,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            handler=handler
        )
        self.tools[name] = tool
        self.logger.info(f"Registered tool: {name}")
    
    def register_resource(self,
                         uri: str,
                         name: str, 
                         description: str,
                         mime_type: str,
                         metadata: Optional[Dict[str, Any]] = None) -> None:
        """Register a resource with the MCP server"""
        resource = MCPResource(
            uri=uri,
            name=name,
            description=description,
            mime_type=mime_type,
            metadata=metadata or {}
        )
        self.resources[uri] = resource
        self.logger.info(f"Registered resource: {name} ({uri})")
    
    def register_prompt(self,
                       name: str,
                       description: str,
                       template: str,
                       parameters: Optional[Dict[str, Any]] = None) -> None:
        """Register a prompt template with the MCP server"""
        prompt = MCPPrompt(
            name=name,
            description=description,
            template=template,
            parameters=parameters or {}
        )
        self.prompts[name] = prompt
        self.logger.info(f"Registered prompt: {name}")
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with given parameters"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        tool = self.tools[tool_name]
        if not tool.handler:
            raise ValueError(f"Tool '{tool_name}' has no handler")
        
        try:
            # Validate input parameters against schema
            self._validate_parameters(parameters, tool.input_schema)
            
            # Execute the tool
            result = await self._execute_handler(tool.handler, parameters)
            
            return {
                "success": True,
                "result": result,
                "tool": tool_name
            }
        except Exception as e:
            self.logger.error(f"Tool execution failed for {tool_name}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name
            }
    
    async def get_resource(self, uri: str) -> Dict[str, Any]:
        """Get a resource by URI"""
        if uri not in self.resources:
            raise ValueError(f"Resource '{uri}' not found")
        
        resource = self.resources[uri]
        
        try:
            # Get resource content
            content = await self._get_resource_content(resource)
            
            return {
                "success": True,
                "resource": resource.dict(),
                "content": content
            }
        except Exception as e:
            self.logger.error(f"Resource access failed for {uri}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "uri": uri
            }
    
    async def render_prompt(self, prompt_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Render a prompt template with parameters"""
        if prompt_name not in self.prompts:
            raise ValueError(f"Prompt '{prompt_name}' not found")
        
        prompt = self.prompts[prompt_name]
        parameters = parameters or {}
        
        try:
            # Render template with parameters
            rendered = self._render_template(prompt.template, parameters)
            
            return {
                "success": True,
                "prompt": prompt_name,
                "rendered": rendered,
                "parameters": parameters
            }
        except Exception as e:
            self.logger.error(f"Prompt rendering failed for {prompt_name}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "prompt": prompt_name
            }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get server capabilities for negotiation"""
        return {
            "server": {
                "name": self.name,
                "version": self.version
            },
            "capabilities": {
                name: {
                    "supported": cap.supported,
                    "description": cap.description,
                    "metadata": cap.metadata or {}
                }
                for name, cap in self.capabilities.items()
            },
            "tools": list(self.tools.keys()),
            "resources": list(self.resources.keys()),
            "prompts": list(self.prompts.keys())
        }
    
    def get_analysis_context(self) -> Dict[str, Any]:
        """Get current analysis context for agent awareness"""
        context = {
            "server": self.name,
            "timestamp": asyncio.get_event_loop().time(),
            "session_state": self._get_session_state_summary(),
            "available_tools": list(self.tools.keys()),
            "available_resources": list(self.resources.keys())
        }
        
        # Add server-specific context
        context.update(self._get_server_specific_context())
        
        return context
    
    def get_pipeline_context(self) -> Dict[str, Any]:
        """Get current pipeline context for agent awareness"""
        return {
            "current_step": None,
            "next_step": None,
            "completed_steps": [],
            "available_steps": [],
            "pipeline_description": "Generic analysis pipeline"
        }
    
    def get_analysis_insights(self) -> str:
        """Get current analysis insights for agent context"""
        return "No specific insights available"
    
    def get_suggested_actions(self) -> List[str]:
        """Get suggested next actions based on current state"""
        return []
    
    def _validate_parameters(self, parameters: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Validate parameters against JSON schema"""
        # Basic validation - in production, use jsonschema library
        required = schema.get("required", [])
        for param in required:
            if param not in parameters:
                raise ValueError(f"Required parameter '{param}' missing")
    
    async def _execute_handler(self, handler: Callable, parameters: Dict[str, Any]) -> Any:
        """Execute tool handler (sync or async)"""
        if asyncio.iscoroutinefunction(handler):
            return await handler(**parameters)
        else:
            return handler(**parameters)
    
    async def _get_resource_content(self, resource: MCPResource) -> Any:
        """Get resource content - to be implemented by subclasses"""
        return {"message": "Resource content retrieval not implemented"}
    
    def _render_template(self, template: str, parameters: Dict[str, Any]) -> str:
        """Render template with parameters"""
        try:
            return template.format(**parameters)
        except KeyError as e:
            raise ValueError(f"Template parameter missing: {e}")
    
    def _get_session_state_summary(self) -> Dict[str, Any]:
        """Get summary of current Streamlit session state"""
        if 'st' not in globals():
            return {}
        
        summary = {}
        
        # Get key session state variables
        key_vars = [
            'rnaseq_counts_df', 'rnaseq_metadata_df', 'anndata',
            'deseq_results', 'go_results', 'filtered_genes',
            'qc_done', 'filtered', 'normalized', 'clustered'
        ]
        
        for var in key_vars:
            if var in st.session_state:
                value = st.session_state[var]
                if hasattr(value, 'shape'):
                    summary[var] = f"DataFrame/Array with shape {value.shape}"
                elif isinstance(value, bool):
                    summary[var] = value
                elif isinstance(value, (int, float, str)):
                    summary[var] = value
                else:
                    summary[var] = f"Object of type {type(value).__name__}"
        
        return summary
    
    @abstractmethod
    def _get_server_specific_context(self) -> Dict[str, Any]:
        """Get server-specific context - to be implemented by subclasses"""
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the server - to be implemented by subclasses"""
        pass 