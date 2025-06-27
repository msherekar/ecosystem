"""
Registry Package

Centralized registry system for managing MCP servers, tools, resources, and prompts.
"""

from .registry import MCPRegistry, mcp_registry, get_mcp_registry
from .tool_registry import (
    ToolConfig, 
    ToolParameter, 
    mcp_tool, 
    AutoToolRegistry, 
    get_auto_tool_configs
)
from .resource_registry import (
    ResourceConfig, 
    mcp_resource, 
    AutoResourceRegistry, 
    get_auto_resource_configs
)
from .prompt_registry import (
    PromptConfig, 
    mcp_prompt, 
    AutoPromptRegistry, 
    get_auto_prompt_configs,
    CommonPromptTemplates
)

__all__ = [
    # Main registry
    'MCPRegistry', 'mcp_registry', 'get_mcp_registry',
    # Tool registry
    'ToolConfig', 'ToolParameter', 'mcp_tool', 'AutoToolRegistry', 'get_auto_tool_configs',
    # Resource registry
    'ResourceConfig', 'mcp_resource', 'AutoResourceRegistry', 'get_auto_resource_configs',
    # Prompt registry
    'PromptConfig', 'mcp_prompt', 'AutoPromptRegistry', 'get_auto_prompt_configs', 'CommonPromptTemplates'
] 