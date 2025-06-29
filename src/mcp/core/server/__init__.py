"""
Core MCP Server Implementation

Provides the base server functionality for all bioinformatics MCP servers.
Handles tool registration, capability negotiation, and request routing.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass

from .base_server import BaseMCPServer
from .validation_system import ValidationSystem, ValidationBackend
from .template_engine import TemplateEngine, TemplateEngineType
from .resource_manager import ResourceManager
from .capability_manager import CapabilityManager
from .tool_executor import ToolExecutor

# Re-export commonly used classes
from .base_server import MCPTool, MCPResource, MCPPrompt, MCPCapability, MCPMessageType


class MCPServer(BaseMCPServer):
    """
    Main MCP Server class for bioinformatics applications.
    
    Provides standardized interface for:
    - Tool registration and execution
    - Resource management  
    - Prompt templates
    - Context sharing with AI agents
    """
    
    def __init__(self, name: str, version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Initialize subsystems
        self.capability_manager = CapabilityManager()
        self.validation_system = ValidationSystem()
        self.template_engine = TemplateEngine()
        self.resource_manager = ResourceManager()
        self.tool_executor = ToolExecutor(self.validation_system)
        
        # Initialize default capabilities
        self._init_default_capabilities()
    
    def _init_default_capabilities(self):
        """Initialize default MCP capabilities"""
        self.capability_manager.register_capability(
            "tools", "Tool execution support", True
        )
        self.capability_manager.register_capability(
            "resources", "Resource access support", True
        )
        self.capability_manager.register_capability(
            "prompts", "Prompt template support", True
        )
    
    # Tool Management
    def register_tool(self, 
                     name: str,
                     description: str,
                     input_schema: Dict[str, Any],
                     handler: Callable,
                     output_schema: Optional[Dict[str, Any]] = None) -> None:
        """Register a tool with the server"""
        tool = MCPTool(
            name=name,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            handler=handler
        )
        self.tools[name] = tool
        self.logger.info(f"Registered tool: {name}")
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a registered tool"""
        return await self.tool_executor.execute_tool(tool_name, parameters, self.tools)
    
    # Resource Management
    def register_resource(self,
                         uri: str,
                         name: str, 
                         description: str,
                         mime_type: str,
                         metadata: Optional[Dict[str, Any]] = None) -> None:
        """Register a resource with the server"""
        resource = MCPResource(
            uri=uri,
            name=name,
            description=description,
            mime_type=mime_type,
            metadata=metadata
        )
        self.resources[uri] = resource
        self.logger.info(f"Registered resource: {uri}")
    
    async def get_resource(self, uri: str) -> Dict[str, Any]:
        """Get a resource by URI"""
        return await self.resource_manager.get_resource(uri, self.resources)
    
    # Prompt Management
    def register_prompt(self,
                       name: str,
                       description: str,
                       template: str,
                       parameters: Optional[Dict[str, Any]] = None,
                       engine: Optional[TemplateEngineType] = None,
                       template_config: Optional[Dict[str, Any]] = None) -> None:
        """Register a prompt template"""
        prompt = MCPPrompt(
            name=name,
            description=description,
            template=template,
            parameters=parameters,
            engine=engine or TemplateEngineType.SIMPLE,
            template_config=template_config
        )
        self.prompts[name] = prompt
        self.logger.info(f"Registered prompt: {name}")
    
    async def render_prompt(self, prompt_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Render a prompt template"""
        return await self.template_engine.render_prompt(prompt_name, parameters, self.prompts)
    
    # Configuration Methods
    def configure_capabilities(self, 
                             capability_config: Optional[Dict[str, Any]] = None,
                             custom_capabilities: Optional[Dict[str, Any]] = None) -> None:
        """Configure server capabilities"""
        self.capability_manager.configure_capabilities(capability_config, custom_capabilities)
    
    def configure_validation(self,
                           backend: Optional[ValidationBackend] = None,
                           custom_validators: Optional[Dict[str, Callable]] = None,
                           validation_config: Optional[Dict[str, Any]] = None) -> None:
        """Configure validation system"""
        self.validation_system.configure_validation(backend, custom_validators, validation_config)
    
    def configure_templates(self,
                          default_engine: Optional[TemplateEngineType] = None,
                          global_variables: Optional[Dict[str, Any]] = None,
                          custom_filters: Optional[Dict[str, Callable]] = None) -> None:
        """Configure template system"""
        self.template_engine.configure_templates(default_engine, global_variables, custom_filters)
    
    def configure_resources(self,
                          cache_enabled: Optional[bool] = None,
                          auto_discover: Optional[bool] = None,
                          providers: Optional[Dict[str, Any]] = None) -> None:
        """Configure resource system"""
        self.resource_manager.configure_resources(cache_enabled, auto_discover, providers)
    
    def register_capability(self, 
                          name: str,
                          description: str,
                          supported: bool = True,
                          metadata: Optional[Dict[str, Any]] = None) -> None:
        """Register a server capability"""
        self.capability_manager.register_capability(name, description, supported, metadata)
    
    # Utility Methods
    def get_capabilities(self) -> Dict[str, Any]:
        """Get server capabilities in the expected format for tests"""
        # Get capabilities from capability manager
        cap_data = self.capability_manager.get_capabilities()
        
        # Return format expected by tests - includes tools, resources, prompts lists
        return {
            "capabilities": cap_data["capabilities"],
            "server_info": cap_data["server_info"],
            "protocol_version": cap_data["protocol_version"],
            "tools": list(self.tools.keys()),
            "resources": list(self.resources.keys()),
            "prompts": list(self.prompts.keys())
        }
    
    def clear_resource_cache(self, uri: Optional[str] = None) -> None:
        """Clear resource cache"""
        self.resource_manager.clear_cache(uri)
    
    # Access Methods for Registered Components
    def get_tools(self) -> Dict[str, MCPTool]:
        """Get all registered tools"""
        return self.tools.copy()
    
    def get_resources(self) -> Dict[str, MCPResource]:
        """Get all registered resources"""
        return self.resources.copy()
    
    def get_prompts(self) -> Dict[str, MCPPrompt]:
        """Get all registered prompts"""
        return self.prompts.copy()
    
    def get_tool(self, name: str) -> Optional[MCPTool]:
        """Get a specific tool by name"""
        return self.tools.get(name)
    
    def get_resource_by_uri(self, uri: str) -> Optional[MCPResource]:
        """Get a specific resource by URI"""
        return self.resources.get(uri)
    
    def get_prompt(self, name: str) -> Optional[MCPPrompt]:
        """Get a specific prompt by name"""
        return self.prompts.get(name)


__all__ = [
    'MCPServer',
    'MCPTool', 
    'MCPResource',
    'MCPPrompt',
    'MCPCapability',
    'MCPMessageType',
    'ValidationBackend',
    'TemplateEngineType'
] 