"""
Registry Package

Centralized registry system for managing MCP servers, tools, resources, and prompts.
"""

try:
    # Try relative imports first (when used as a package)
    from .registry import MCPRegistry, MCPServerConfig, mcp_registry, get_mcp_registry
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
        get_auto_prompt_configs
    )
    from .prompt_templates import CommonPromptTemplates
    from .prompt_domain_integration import (
        get_domain_prompts_for_handler,
        get_supported_techniques
    )
except ImportError:
    # Fallback to absolute imports (when testing standalone)
    from registry import MCPRegistry, MCPServerConfig, mcp_registry, get_mcp_registry
    from tool_registry import (
        ToolConfig, 
        ToolParameter, 
        mcp_tool, 
        AutoToolRegistry, 
        get_auto_tool_configs
    )
    from resource_registry import (
        ResourceConfig, 
        mcp_resource, 
        AutoResourceRegistry, 
        get_auto_resource_configs
    )
    from .prompt_registry import (
        PromptConfig, 
        mcp_prompt, 
        AutoPromptRegistry, 
        get_auto_prompt_configs
    )
    from prompt_templates import CommonPromptTemplates
    from prompt_domain_integration import (
        get_domain_prompts_for_handler,
        get_supported_techniques
    )

__all__ = [
    # Main registry
    'MCPRegistry', 'MCPServerConfig', 'mcp_registry', 'get_mcp_registry',
    # Tool registry
    'ToolConfig', 'ToolParameter', 'mcp_tool', 'AutoToolRegistry', 'get_auto_tool_configs',
    # Resource registry
    'ResourceConfig', 'mcp_resource', 'AutoResourceRegistry', 'get_auto_resource_configs',
    # Prompt registry
    'PromptConfig', 'mcp_prompt', 'AutoPromptRegistry', 'get_auto_prompt_configs', 
    # Prompt templates
    'CommonPromptTemplates',
    # Domain integration
    'get_domain_prompts_for_handler', 'get_supported_techniques'
] 