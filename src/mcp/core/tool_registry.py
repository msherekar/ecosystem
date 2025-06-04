"""
Automated Tool Registry

Automatically generates tool configurations from handler methods using decorators
and function introspection. This eliminates the need for manual tool configuration.
"""

import inspect
from typing import Dict, List, Any, Optional, Callable, get_type_hints
from functools import wraps
from dataclasses import dataclass


@dataclass
class ToolConfig:
    """Configuration for a single tool"""
    name: str
    description: str
    handler: Callable
    properties: Dict[str, Any]
    required: List[str]
    dependencies: Optional[List[str]] = None
    category: str = "general"


class ToolParameter:
    """Decorator to define tool parameters with automatic schema generation"""
    
    def __init__(self, description: str, default: Any = None, 
                 min_val: Optional[float] = None, max_val: Optional[float] = None,
                 enum: Optional[List[str]] = None, required: bool = None):
        self.description = description
        self.default = default
        self.min_val = min_val
        self.max_val = max_val
        self.enum = enum
        self.required = required if required is not None else (default is None)


def mcp_tool(description: str, category: str = "general", 
             dependencies: Optional[List[str]] = None):
    """
    Decorator to automatically register a method as an MCP tool.
    
    Uses function introspection to generate JSON schema automatically.
    """
    def decorator(func):
        # Store metadata on the function
        func._mcp_tool = True
        func._mcp_description = description
        func._mcp_category = category
        func._mcp_dependencies = dependencies
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        # Copy metadata to wrapper
        wrapper._mcp_tool = True
        wrapper._mcp_description = description
        wrapper._mcp_category = category
        wrapper._mcp_dependencies = dependencies
        
        return wrapper
    return decorator


class AutoToolRegistry:
    """Automatically discovers and configures tools from handler classes"""
    
    def __init__(self):
        self.type_mapping = {
            int: "integer",
            float: "number", 
            str: "string",
            bool: "boolean",
            list: "array",
            dict: "object"
        }
    
    def discover_tools(self, handlers_instance) -> Dict[str, ToolConfig]:
        """
        Automatically discover tools from a handlers instance using introspection.
        
        Looks for methods decorated with @mcp_tool and generates configurations.
        """
        tools = {}
        
        # Get all methods from the handlers instance
        for method_name in dir(handlers_instance):
            method = getattr(handlers_instance, method_name)
            
            # Skip private methods and non-callable attributes
            if method_name.startswith('_') or not callable(method):
                continue
            
            # Check if method is decorated as an MCP tool
            if hasattr(method, '_mcp_tool') and method._mcp_tool:
                tool_config = self._generate_tool_config(method_name, method)
                tools[tool_config.name] = tool_config
        
        return tools
    
    def _generate_tool_config(self, method_name: str, method: Callable) -> ToolConfig:
        """Generate tool configuration from method introspection"""
        
        # Get method signature and type hints
        sig = inspect.signature(method)
        type_hints = get_type_hints(method)
        
        properties = {}
        required = []
        
        # Process each parameter
        for param_name, param in sig.parameters.items():
            # Skip 'self' parameter
            if param_name == 'self':
                continue
            
            # Get parameter type from type hints
            param_type = type_hints.get(param_name, str)
            
            # Generate JSON schema for parameter
            param_schema = self._generate_parameter_schema(
                param_name, param, param_type
            )
            
            properties[param_name] = param_schema
            
            # Check if parameter is required
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
        
        return ToolConfig(
            name=method_name,
            description=getattr(method, '_mcp_description', f"Execute {method_name}"),
            handler=method,
            properties=properties,
            required=required,
            dependencies=getattr(method, '_mcp_dependencies', None),
            category=getattr(method, '_mcp_category', 'general')
        )
    
    def _generate_parameter_schema(self, param_name: str, param: inspect.Parameter, 
                                 param_type: type) -> Dict[str, Any]:
        """Generate JSON schema for a single parameter"""
        
        # Map Python type to JSON schema type
        json_type = self._get_json_type(param_type)
        
        schema = {
            "type": json_type,
            "description": self._generate_description(param_name, param_type)
        }
        
        # Add default value if present
        if param.default != inspect.Parameter.empty:
            schema["default"] = param.default
        
        # Handle special types
        if json_type == "array":
            schema["items"] = {"type": "string"}  # Default to string array
        
        # Add enum for specific parameters
        if param_name == "method" and "method" in param_name.lower():
            schema["enum"] = ["wilcoxon", "t-test", "logreg"]
        
        return schema
    
    def _get_json_type(self, python_type: type) -> str:
        """Map Python type to JSON schema type"""
        
        # Handle generic types (List, Dict, etc.)
        origin = getattr(python_type, '__origin__', None)
        if origin is not None:
            if origin is list:
                return "array"
            elif origin is dict:
                return "object"
        
        # Handle basic types
        return self.type_mapping.get(python_type, "string")
    
    def _generate_description(self, param_name: str, param_type: type) -> str:
        """Generate human-readable description for parameter"""
        
        descriptions = {
            # Common parameter patterns
            "force_rerun": "Force rerun of analysis even if results exist",
            "min_genes": "Minimum number of genes per cell",
            "max_genes": "Maximum number of genes per cell", 
            "min_cells": "Minimum number of cells per gene",
            "max_mito_pct": "Maximum mitochondrial gene percentage",
            "target_sum": "Target sum for normalization",
            "log_transform": "Apply log transformation",
            "scale": "Scale data to unit variance",
            "resolution": "Clustering resolution",
            "n_neighbors": "Number of neighbors for graph construction",
            "n_pcs": "Number of principal components to use",
            "method": "Statistical method for analysis",
            "min_logfc": "Minimum log fold change",
            "min_pct": "Minimum percentage of cells expressing gene",
            "color_by": "Variable to color cells by",
            "min_dist": "UMAP min_dist parameter",
            "spread": "UMAP spread parameter",
            "genes": "List of genes to analyze",
            "groupby": "Variable to group by",
            "n_genes": "Number of top genes per group"
        }
        
        # Return specific description if available
        if param_name in descriptions:
            return descriptions[param_name]
        
        # Generate generic description based on name and type
        type_desc = {
            int: "integer value",
            float: "numeric value", 
            str: "string value",
            bool: "boolean flag",
            list: "list of values",
            dict: "object with key-value pairs"
        }.get(param_type, "value")
        
        # Convert snake_case to human readable
        human_name = param_name.replace('_', ' ').title()
        
        return f"{human_name} ({type_desc})"


# Global registry instance
auto_tool_registry = AutoToolRegistry()


def get_auto_tool_configs(handlers_instance) -> Dict[str, ToolConfig]:
    """Get automatically generated tool configurations for a handlers instance"""
    return auto_tool_registry.discover_tools(handlers_instance) 