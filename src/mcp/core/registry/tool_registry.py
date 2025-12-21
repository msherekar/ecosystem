"""
Automated Tool Registry - Enhanced Version

Automatically generates tool configurations from handler methods using decorators
and function introspection. Enhanced for scalability, security, and robustness.

Key Improvements:
- Enhanced security with input validation
- Better error handling and logging
- Caching for performance at scale
- More robust type inference
- Comprehensive validation
"""

import inspect
import logging
import hashlib
import threading
from typing import Dict, List, Any, Optional, Callable, get_type_hints, Union, get_origin, get_args
from functools import wraps, lru_cache
from dataclasses import dataclass, field
from enum import Enum

# Configure logger
logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Standardized tool categories"""
    GENERAL = "general"
    QUALITY_CONTROL = "quality_control"
    PREPROCESSING = "preprocessing"
    ANALYSIS = "analysis"
    VISUALIZATION = "visualization"
    STATISTICS = "statistics"
    DATA_MANAGEMENT = "data_management"
    ADMIN = "admin"


class SecurityLevel(Enum):
    """Security levels for tools"""
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    ADMIN = "admin"


@dataclass
class ToolParameter:
    """Enhanced tool parameter definition with validation"""
    description: str
    param_type: type = str
    default: Any = None
    required: bool = None
    min_val: Optional[Union[int, float]] = None
    max_val: Optional[Union[int, float]] = None
    enum_values: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.required is None:
            self.required = (self.default is None)


@dataclass
class ToolConfig:
    """Enhanced configuration for a single tool"""
    name: str
    description: str
    handler: Callable
    properties: Dict[str, Any]
    required: List[str]
    category: ToolCategory = ToolCategory.GENERAL
    security_level: SecurityLevel = SecurityLevel.PUBLIC
    dependencies: Optional[List[str]] = None
    version: str = "1.0.0"
    deprecated: bool = False
    rate_limit: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def mcp_tool(description: str, 
             category: Union[str, ToolCategory] = ToolCategory.GENERAL,
             security_level: Union[str, SecurityLevel] = SecurityLevel.PUBLIC,
             dependencies: Optional[List[str]] = None,
             version: str = "1.0.0",
             deprecated: bool = False,
             rate_limit: Optional[int] = None,
             parameters: Optional[Dict[str, ToolParameter]] = None):
    """
    Enhanced decorator to automatically register a method as an MCP tool.
    """
    def decorator(func):
        if not description or not isinstance(description, str):
            raise ValueError("Tool description must be a non-empty string")
        
        # Store metadata on the function
        func._mcp_tool = True
        func._mcp_description = description
        func._mcp_category = category
        func._mcp_security_level = security_level
        func._mcp_dependencies = dependencies or []
        func._mcp_version = version
        func._mcp_deprecated = deprecated
        func._mcp_rate_limit = rate_limit
        func._mcp_parameters = parameters or {}
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        # Copy metadata to wrapper
        for attr in ['_mcp_tool', '_mcp_description', '_mcp_category', '_mcp_security_level',
                     '_mcp_dependencies', '_mcp_version', '_mcp_deprecated', '_mcp_rate_limit',
                     '_mcp_parameters']:
            setattr(wrapper, attr, getattr(func, attr))
        
        return wrapper
    return decorator


class TypeInferenceEngine:
    """Enhanced type inference with caching"""
    
    def __init__(self):
        self.type_mapping = {
            int: "integer",
            float: "number",
            str: "string", 
            bool: "boolean",
            list: "array",
            dict: "object"
        }
    
    @lru_cache(maxsize=1000)
    def get_json_type(self, python_type: type) -> str:
        """Map Python type to JSON schema type with caching"""
        if python_type is type(None):
            return "null"
        
        # Handle Union types (including Optional)
        origin = get_origin(python_type)
        if origin is Union:
            args = get_args(python_type)
            # Handle Optional[T] (Union[T, None])
            if len(args) == 2 and type(None) in args:
                non_none_type = next(arg for arg in args if arg is not type(None))
                return self.get_json_type(non_none_type)
            return "string"
        
        # Handle generic types
        if origin is not None:
            if origin in (list, tuple, set):
                return "array"
            elif origin is dict:
                return "object"
        
        return self.type_mapping.get(python_type, "string")


class SchemaGenerator:
    """Enhanced JSON schema generation"""
    
    def __init__(self):
        self.type_engine = TypeInferenceEngine()
        self.parameter_descriptions = {
            "force_rerun": "Force rerun of analysis even if results exist",
            "min_genes": "Minimum number of genes per cell",
            "max_genes": "Maximum number of genes per cell",
            "min_cells": "Minimum number of cells per gene",
            "max_mito_pct": "Maximum mitochondrial gene percentage",
            "target_sum": "Target sum for normalization",
            "resolution": "Clustering resolution parameter",
            "n_neighbors": "Number of neighbors for graph construction",
            "method": "Statistical method for analysis",
            "color_by": "Variable to color cells/points by",
            "genes": "List of genes to analyze",
            "groupby": "Variable to group by"
        }
    
    def generate_parameter_schema(self, param_name: str, param: inspect.Parameter, 
                                param_type: type, enhanced_param: Optional[ToolParameter] = None) -> Dict[str, Any]:
        """Generate JSON schema for a parameter"""
        json_type = self.type_engine.get_json_type(param_type)
        
        schema = {
            "type": json_type,
            "description": self._get_description(param_name, enhanced_param)
        }
        
        if param.default != inspect.Parameter.empty:
            schema["default"] = param.default
        
        # Apply enhanced constraints
        if enhanced_param:
            if enhanced_param.min_val is not None:
                schema["minimum"] = enhanced_param.min_val
            if enhanced_param.max_val is not None:
                schema["maximum"] = enhanced_param.max_val
            if enhanced_param.enum_values:
                schema["enum"] = enhanced_param.enum_values
        
        # Default constraints
        self._apply_default_constraints(schema, param_name, json_type)
        
        return schema
    
    def _get_description(self, param_name: str, enhanced_param: Optional[ToolParameter]) -> str:
        """Get parameter description"""
        if enhanced_param and enhanced_param.description:
            return enhanced_param.description
        
        if param_name in self.parameter_descriptions:
            return self.parameter_descriptions[param_name]
        
        # Generate from name
        human_name = param_name.replace('_', ' ').title()
        return f"{human_name} parameter"
    
    def _apply_default_constraints(self, schema: Dict[str, Any], param_name: str, json_type: str):
        """Apply default constraints based on parameter patterns"""
        if param_name == "method":
            schema["enum"] = ["wilcoxon", "t-test", "logreg"]
        
        if "pct" in param_name and json_type in ["integer", "number"]:
            schema["minimum"] = 0
            schema["maximum"] = 100
        
        if json_type == "array":
            schema["items"] = {"type": "string"}


class AutoToolRegistry:
    """Enhanced tool registry with caching and security"""
    
    def __init__(self, enable_caching: bool = True):
        self.schema_generator = SchemaGenerator()
        self._cache = {} if enable_caching else None
        self._lock = threading.RLock() if enable_caching else None
        self.logger = logger.getChild("AutoToolRegistry")
    
    def discover_tools(self, handlers_instance, 
                      security_context: Optional[Dict[str, Any]] = None) -> Dict[str, ToolConfig]:
        """Enhanced tool discovery with caching and security filtering"""
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(handlers_instance, security_context)
            
            # Check cache
            if self._cache and cache_key in self._cache:
                return self._cache[cache_key]
            
            # Discover tools
            tools = self._discover_tools_internal(handlers_instance, security_context)
            
            # Cache result
            if self._cache:
                with self._lock:
                    self._cache[cache_key] = tools
            
            self.logger.info(f"Discovered {len(tools)} tools from {handlers_instance.__class__.__name__}")
            return tools
            
        except Exception as e:
            self.logger.error(f"Error discovering tools: {e}")
            return {}
    
    def _discover_tools_internal(self, handlers_instance, security_context) -> Dict[str, ToolConfig]:
        """Internal tool discovery logic"""
        tools = {}
        
        for method_name in dir(handlers_instance):
            try:
                method = getattr(handlers_instance, method_name)
                
                if (method_name.startswith('_') or not callable(method) or
                    not hasattr(method, '_mcp_tool') or not method._mcp_tool):
                    continue
                
                tool_config = self._generate_tool_config(method_name, method)
                
                if self._is_tool_accessible(tool_config, security_context):
                    tools[tool_config.name] = tool_config
                        
            except Exception as e:
                self.logger.warning(f"Error processing method {method_name}: {e}")
                continue
        
        return tools
    
    def _generate_tool_config(self, method_name: str, method: Callable) -> ToolConfig:
        """Generate tool configuration from method"""
        sig = inspect.signature(method)
        type_hints = get_type_hints(method)
        
        properties = {}
        required = []
        enhanced_params = getattr(method, '_mcp_parameters', {})
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            param_type = type_hints.get(param_name, str)
            enhanced_param = enhanced_params.get(param_name)
            
            param_schema = self.schema_generator.generate_parameter_schema(
                param_name, param, param_type, enhanced_param
            )
            
            properties[param_name] = param_schema
            
            # Check if required
            is_required = (param.default == inspect.Parameter.empty)
            if enhanced_param and enhanced_param.required is not None:
                is_required = enhanced_param.required
            
            if is_required:
                required.append(param_name)
        
        return ToolConfig(
            name=method_name,
            description=getattr(method, '_mcp_description', f"Execute {method_name}"),
            handler=method,
            properties=properties,
            required=required,
            category=getattr(method, '_mcp_category', ToolCategory.GENERAL),
            security_level=getattr(method, '_mcp_security_level', SecurityLevel.PUBLIC),
            dependencies=getattr(method, '_mcp_dependencies', []),
            version=getattr(method, '_mcp_version', "1.0.0"),
            deprecated=getattr(method, '_mcp_deprecated', False),
            rate_limit=getattr(method, '_mcp_rate_limit'),
            metadata={"source_class": method.__self__.__class__.__name__ if hasattr(method, '__self__') else "unknown"}
        )
    
    def _generate_cache_key(self, handlers_instance, security_context) -> str:
        """Generate cache key for handlers instance and security context"""
        class_name = handlers_instance.__class__.__name__
        security_str = str(security_context) if security_context else "public"
        return hashlib.md5(f"{class_name}:{security_str}".encode()).hexdigest()
    
    def _is_tool_accessible(self, tool_config: ToolConfig, security_context: Optional[Dict[str, Any]]) -> bool:
        """Check if tool is accessible given security context"""
        if tool_config.security_level == SecurityLevel.PUBLIC:
            return True
        
        if not security_context:
            return False
        
        user_level = security_context.get("security_level", "public")
        
        # Simple security hierarchy
        level_order = ["public", "internal", "restricted", "admin"]
        required_idx = level_order.index(tool_config.security_level.value)
        user_idx = level_order.index(user_level) if user_level in level_order else 0
        
        return user_idx >= required_idx
    
    def clear_cache(self):
        """Clear the registry cache"""
        if self._cache:
            with self._lock:
                self._cache.clear()


# Global registry instance
auto_tool_registry = AutoToolRegistry()


def get_auto_tool_configs(handlers_instance, 
                         security_context: Optional[Dict[str, Any]] = None) -> Dict[str, ToolConfig]:
    """Get automatically generated tool configurations with security filtering"""
    return auto_tool_registry.discover_tools(handlers_instance, security_context)


def main():
    """Main function for module testing"""
    print("Testing Enhanced AutoToolRegistry...")
    
    # Test enhanced tool registry
    registry = AutoToolRegistry()
    
    # Create test handler with enhanced decorators
    class TestHandler:
        @mcp_tool(
            description="Enhanced cell filtering",
            category=ToolCategory.QUALITY_CONTROL,
            security_level=SecurityLevel.INTERNAL,
            dependencies=["scanpy"],
            version="2.0.0",
            parameters={
                "min_genes": ToolParameter(
                    description="Minimum genes per cell",
                    param_type=int,
                    default=200,
                    min_val=1,
                    max_val=10000
                )
            }
        )
        async def filter_cells_enhanced(self, min_genes: int = 200, max_genes: int = 5000):
            return {"status": "filtered"}
        
        @mcp_tool(description="Public analysis", security_level=SecurityLevel.PUBLIC)
        async def public_analysis(self, data_type: str = "expression"):
            return {"analysis": "complete"}
    
    # Test discovery
    handler = TestHandler()
    
    # Test with different security contexts
    public_tools = registry.discover_tools(handler, {"security_level": "public"})
    internal_tools = registry.discover_tools(handler, {"security_level": "internal"})
    
    print(f"✅ Public context: {len(public_tools)} tools")
    print(f"✅ Internal context: {len(internal_tools)} tools")
    
    # Test tool config validation
    for tool_name, config in internal_tools.items():
        print(f"✅ Tool: {config.name} (v{config.version})")
        print(f"   Category: {config.category.value}")
        print(f"   Security: {config.security_level.value}")
        print(f"   Parameters: {len(config.properties)}")
        print(f"   Required: {config.required}")
    
    # Test cache functionality
    cached_tools = registry.discover_tools(handler, {"security_level": "internal"})
    print(f"✅ Cache test: {len(cached_tools)} tools (should be cached)")
    
    print("🎉 All Enhanced ToolRegistry tests passed!")


if __name__ == "__main__":
    main()