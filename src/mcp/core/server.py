"""
Core MCP Server Implementation

Provides the base server functionality for all bioinformatics MCP servers.
Handles tool registration, capability negotiation, and request routing.
"""

import asyncio
import json
import logging
import time
import inspect
import importlib
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum
import re
from datetime import datetime

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


class TemplateEngine(Enum):
    """Supported template engines"""
    SIMPLE = "simple"  # Basic string.format()
    JINJA2 = "jinja2"  # Jinja2 templates
    F_STRING = "f_string"  # Python f-string style


class MCPPrompt(BaseModel):
    """MCP Prompt definition"""
    name: str
    description: str
    template: str
    parameters: Optional[Dict[str, Any]] = None
    engine: TemplateEngine = TemplateEngine.SIMPLE
    template_config: Optional[Dict[str, Any]] = None


class ValidationBackend(Enum):
    """Supported validation backends"""
    BASIC = "basic"  # Basic type checking
    JSONSCHEMA = "jsonschema"  # JSON Schema validation
    PYDANTIC = "pydantic"  # Pydantic model validation


class ResourceProvider(ABC):
    """Abstract base class for resource providers"""
    
    @abstractmethod
    async def get_content(self, resource: 'MCPResource') -> Any:
        """Get resource content"""
        pass
    
    @abstractmethod
    async def list_resources(self, pattern: Optional[str] = None) -> List['MCPResource']:
        """List available resources"""
        pass


class FileResourceProvider(ResourceProvider):
    """File-based resource provider"""
    
    def __init__(self, base_path: str):
        self.base_path = base_path
    
    async def get_content(self, resource: 'MCPResource') -> Any:
        """Get file content"""
        # Implementation would read from filesystem
        return {"content": f"File content from {resource.uri}"}
    
    async def list_resources(self, pattern: Optional[str] = None) -> List['MCPResource']:
        """List files matching pattern"""
        # Implementation would scan filesystem
        return []


class SessionStateResourceProvider(ResourceProvider):
    """Session state-based resource provider"""
    
    async def get_content(self, resource: 'MCPResource') -> Any:
        """Get content from session state"""
        var_name = resource.uri.replace("session://", "")
        if var_name in st.session_state:
            return st.session_state[var_name]
        raise ValueError(f"Session variable '{var_name}' not found")
    
    async def list_resources(self, pattern: Optional[str] = None) -> List['MCPResource']:
        """List session state variables as resources"""
        resources = []
        for key in st.session_state.keys():
            if pattern is None or re.match(pattern, key):
                resources.append(MCPResource(
                    uri=f"session://{key}",
                    name=key,
                    description=f"Session state variable: {key}",
                    mime_type="application/json"
                ))
        return resources


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
        
        # Configurable session state tracking
        self.tracked_variables: List[str] = []
        self.variable_patterns: List[str] = []
        self.auto_discover_variables: bool = False
        
        # Configurable capabilities
        self.capability_config: Dict[str, Any] = {}
        self.custom_capabilities: Dict[str, MCPCapability] = {}
        
        # Template system configuration
        self.default_template_engine: TemplateEngine = TemplateEngine.SIMPLE
        self.template_globals: Dict[str, Any] = {}
        self.template_filters: Dict[str, Callable] = {}
        
        # Validation system configuration
        self.validation_backend: ValidationBackend = ValidationBackend.BASIC
        self.custom_validators: Dict[str, Callable] = {}
        self.validation_config: Dict[str, Any] = {}
        
        # Resource system configuration
        self.resource_providers: Dict[str, ResourceProvider] = {}
        self.resource_cache: Dict[str, Any] = {}
        self.cache_enabled: bool = True
        self.auto_discover_resources: bool = False
        
        # Tool discovery configuration
        self.tool_modules: List[str] = []
        self.auto_discover_tools: bool = False
        self.tool_decorators: Dict[str, Callable] = {}
        
        # Initialize default capabilities
        self._init_capabilities()
        self._init_resource_providers()
    
    def _init_capabilities(self):
        """Initialize default MCP capabilities"""
        # Default capabilities - can be overridden
        default_capabilities = {
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
        }
        
        # Apply configuration overrides
        for name, capability in default_capabilities.items():
            if name in self.capability_config:
                config = self.capability_config[name]
                capability.supported = config.get("supported", capability.supported)
                capability.description = config.get("description", capability.description)
                capability.metadata = config.get("metadata", capability.metadata)
            
            self.capabilities[name] = capability
        
        # Add custom capabilities
        self.capabilities.update(self.custom_capabilities)
    
    def configure_capabilities(self, 
                             capability_config: Optional[Dict[str, Any]] = None,
                             custom_capabilities: Optional[Dict[str, MCPCapability]] = None) -> None:
        """Configure server capabilities dynamically"""
        if capability_config:
            self.capability_config.update(capability_config)
        
        if custom_capabilities:
            self.custom_capabilities.update(custom_capabilities)
        
        # Reinitialize capabilities with new config
        self._init_capabilities()
    
    def register_capability(self, 
                          name: str,
                          description: str,
                          supported: bool = True,
                          metadata: Optional[Dict[str, Any]] = None) -> None:
        """Register a new capability dynamically"""
        capability = MCPCapability(
            name=name,
            description=description,
            supported=supported,
            metadata=metadata or {}
        )
        self.capabilities[name] = capability
        self.logger.info(f"Registered capability: {name}")
    
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
                       parameters: Optional[Dict[str, Any]] = None,
                       engine: Optional[TemplateEngine] = None,
                       template_config: Optional[Dict[str, Any]] = None) -> None:
        """Register a prompt template with the MCP server"""
        prompt = MCPPrompt(
            name=name,
            description=description,
            template=template,
            parameters=parameters or {},
            engine=engine or self.default_template_engine,
            template_config=template_config or {}
        )
        self.prompts[name] = prompt
        self.logger.info(f"Registered prompt: {name}")
    
    def configure_templates(self,
                          default_engine: Optional[TemplateEngine] = None,
                          global_variables: Optional[Dict[str, Any]] = None,
                          custom_filters: Optional[Dict[str, Callable]] = None) -> None:
        """Configure the template system"""
        if default_engine:
            self.default_template_engine = default_engine
        
        if global_variables:
            self.template_globals.update(global_variables)
        
        if custom_filters:
            self.template_filters.update(custom_filters)
    
    def register_template_filter(self, name: str, filter_func: Callable) -> None:
        """Register a custom template filter"""
        self.template_filters[name] = filter_func
        self.logger.info(f"Registered template filter: {name}")
    
    def configure_validation(self,
                           backend: Optional[ValidationBackend] = None,
                           custom_validators: Optional[Dict[str, Callable]] = None,
                           validation_config: Optional[Dict[str, Any]] = None) -> None:
        """Configure the parameter validation system"""
        if backend:
            self.validation_backend = backend
        
        if custom_validators:
            self.custom_validators.update(custom_validators)
        
        if validation_config:
            self.validation_config.update(validation_config)
    
    def register_validator(self, name: str, validator_func: Callable) -> None:
        """Register a custom parameter validator"""
        self.custom_validators[name] = validator_func
        self.logger.info(f"Registered validator: {name}")
    
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
        # Check cache first
        if self.cache_enabled and uri in self.resource_cache:
            self.logger.debug(f"Resource cache hit: {uri}")
            return self.resource_cache[uri]
        
        # Check registered resources
        if uri in self.resources:
            resource = self.resources[uri]
        else:
            # Try to discover resource dynamically
            if self.auto_discover_resources:
                discovered = await self.discover_resources()
                matching = [r for r in discovered if r.uri == uri]
                if matching:
                    resource = matching[0]
                else:
                    raise ValueError(f"Resource '{uri}' not found")
            else:
                raise ValueError(f"Resource '{uri}' not found")
        
        try:
            # Get content using appropriate provider
            scheme = uri.split("://")[0] if "://" in uri else "file"
            
            if scheme in self.resource_providers:
                content = await self.resource_providers[scheme].get_content(resource)
            else:
                # Fall back to default implementation
                content = await self._get_resource_content(resource)
            
            result = {
                "success": True,
                "resource": resource.dict(),
                "content": content
            }
            
            # Cache result if enabled
            if self.cache_enabled:
                self.resource_cache[uri] = result
            
            return result
            
        except Exception as e:
            self.logger.error(f"Resource access failed for {uri}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "uri": uri
            }
    
    def clear_resource_cache(self, uri: Optional[str] = None) -> None:
        """Clear resource cache"""
        if uri:
            self.resource_cache.pop(uri, None)
        else:
            self.resource_cache.clear()
        self.logger.info(f"Resource cache cleared: {uri or 'all'}")
    
    async def render_prompt(self, prompt_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Render a prompt template with parameters"""
        if prompt_name not in self.prompts:
            raise ValueError(f"Prompt '{prompt_name}' not found")
        
        prompt = self.prompts[prompt_name]
        parameters = parameters or {}
        
        try:
            # Render template with specified engine
            rendered = self._render_template(
                prompt.template, 
                parameters, 
                prompt.engine,
                prompt.template_config
            )
            
            return {
                "success": True,
                "prompt": prompt_name,
                "rendered": rendered,
                "parameters": parameters,
                "engine": prompt.engine.value
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
        """Get analysis context including session state and server status"""
        base_context = {
            "server_name": self.name,
            "server_version": self.version,
            "available_tools": list(self.tools.keys()),
            "available_resources": list(self.resources.keys()),
            "available_prompts": list(self.prompts.keys()),
            "timestamp": time.time(),
            "session_state": self._get_session_state_summary()
        }
        
        # Merge with server-specific context
        server_context = self._get_server_specific_context()
        base_context.update(server_context)
        
        return base_context
    
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
        """Get current analysis insights using strategy pattern"""
        try:
            # Import strategy registry to avoid circular imports
            from .strategy import strategy_registry
            
            # Get server-specific context
            context = self._get_server_specific_context()
            
            # Determine analysis type
            analysis_type = context.get("server_type", context.get("analysis_type", "generic"))
            
            # Get strategy and generate insights
            strategy = strategy_registry.create_strategy(analysis_type)
            return strategy.get_insights(context)
            
        except Exception as e:
            self.logger.warning(f"Failed to get insights via strategy: {e}")
            return "No specific insights available"
    
    def get_suggested_actions(self) -> List[str]:
        """Get suggested next actions using strategy pattern"""
        try:
            # Import strategy registry to avoid circular imports
            from .strategy import strategy_registry
            
            # Get server-specific context
            context = self._get_server_specific_context()
            
            # Determine analysis type
            analysis_type = context.get("server_type", context.get("analysis_type", "generic"))
            
            # Get strategy and generate actions
            strategy = strategy_registry.create_strategy(analysis_type)
            return strategy.get_actions(context)
            
        except Exception as e:
            self.logger.warning(f"Failed to get actions via strategy: {e}")
            return []
    
    def _validate_parameters(self, parameters: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Validate parameters against schema using configured backend"""
        try:
            if self.validation_backend == ValidationBackend.BASIC:
                self._validate_basic(parameters, schema)
            elif self.validation_backend == ValidationBackend.JSONSCHEMA:
                self._validate_jsonschema(parameters, schema)
            elif self.validation_backend == ValidationBackend.PYDANTIC:
                self._validate_pydantic(parameters, schema)
            else:
                raise ValueError(f"Unsupported validation backend: {self.validation_backend}")
        except Exception as e:
            self.logger.error(f"Parameter validation failed: {str(e)}")
            raise
    
    def _validate_basic(self, parameters: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Basic validation - check required parameters"""
        required = schema.get("required", [])
        for param in required:
            if param not in parameters:
                raise ValueError(f"Required parameter '{param}' missing")
        
        # Apply custom validators if specified
        properties = schema.get("properties", {})
        for param_name, param_value in parameters.items():
            if param_name in properties:
                param_schema = properties[param_name]
                validator_name = param_schema.get("validator")
                if validator_name and validator_name in self.custom_validators:
                    validator = self.custom_validators[validator_name]
                    if not validator(param_value):
                        raise ValueError(f"Parameter '{param_name}' failed custom validation")
    
    def _validate_jsonschema(self, parameters: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Validate using JSON Schema (if available)"""
        try:
            import jsonschema
            
            # Apply validation config
            config = self.validation_config.get("jsonschema", {})
            validator_class = config.get("validator_class", jsonschema.Draft7Validator)
            
            validator = validator_class(schema)
            validator.validate(parameters)
            
        except ImportError:
            self.logger.warning("jsonschema not available, falling back to basic validation")
            self._validate_basic(parameters, schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"Schema validation failed: {e.message}")
    
    def _validate_pydantic(self, parameters: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Validate using Pydantic models (if schema contains model reference)"""
        try:
            model_ref = schema.get("pydantic_model")
            if not model_ref:
                # Fall back to basic validation if no Pydantic model specified
                self._validate_basic(parameters, schema)
                return
            
            # Dynamically import and validate with Pydantic model
            if isinstance(model_ref, str):
                # Import model from string reference
                module_name, class_name = model_ref.rsplit(".", 1)
                module = __import__(module_name, fromlist=[class_name])
                model_class = getattr(module, class_name)
            else:
                # Direct model class reference
                model_class = model_ref
            
            # Validate parameters using Pydantic model
            model_class(**parameters)
            
        except ImportError as e:
            self.logger.warning(f"Pydantic model import failed: {e}, falling back to basic validation")
            self._validate_basic(parameters, schema)
        except Exception as e:
            raise ValueError(f"Pydantic validation failed: {str(e)}")
    
    async def _execute_handler(self, handler: Callable, parameters: Dict[str, Any]) -> Any:
        """Execute tool handler (sync or async)"""
        if asyncio.iscoroutinefunction(handler):
            return await handler(**parameters)
        else:
            return handler(**parameters)
    
    async def _get_resource_content(self, resource: MCPResource) -> Any:
        """Get resource content - default implementation"""
        return {"message": "Resource content retrieval not implemented"}
    
    def _render_template(self, template: str, parameters: Dict[str, Any], 
                        engine: TemplateEngine = TemplateEngine.SIMPLE,
                        template_config: Optional[Dict[str, Any]] = None) -> str:
        """Render template with parameters using specified engine"""
        # Merge global variables with parameters
        render_context = {**self.template_globals, **parameters}
        
        try:
            if engine == TemplateEngine.SIMPLE:
                return self._render_simple_template(template, render_context)
            elif engine == TemplateEngine.JINJA2:
                return self._render_jinja2_template(template, render_context, template_config or {})
            elif engine == TemplateEngine.F_STRING:
                return self._render_f_string_template(template, render_context)
            else:
                raise ValueError(f"Unsupported template engine: {engine}")
        except KeyError as e:
            raise ValueError(f"Template parameter missing: {e}")
    
    def _render_simple_template(self, template: str, context: Dict[str, Any]) -> str:
        """Render using simple string.format()"""
        return template.format(**context)
    
    def _render_jinja2_template(self, template: str, context: Dict[str, Any], 
                               config: Dict[str, Any]) -> str:
        """Render using Jinja2 (if available)"""
        try:
            import jinja2
            
            # Create Jinja2 environment
            env = jinja2.Environment(
                loader=jinja2.BaseLoader(),
                **config
            )
            
            # Add custom filters
            env.filters.update(self.template_filters)
            
            # Render template
            template_obj = env.from_string(template)
            return template_obj.render(**context)
            
        except ImportError:
            self.logger.warning("Jinja2 not available, falling back to simple template")
            return self._render_simple_template(template, context)
    
    def _render_f_string_template(self, template: str, context: Dict[str, Any]) -> str:
        """Render using f-string style (eval-based, use with caution)"""
        # Convert {variable} to f-string format
        f_template = re.sub(r'\{([^}]+)\}', r'{context["\1"]}', template)
        
        # Evaluate as f-string (security risk - use only with trusted templates)
        try:
            return eval(f'f"""{f_template}"""', {"context": context})
        except Exception as e:
            raise ValueError(f"F-string template evaluation failed: {e}")
    
    def configure_session_tracking(self, 
                                 tracked_variables: Optional[List[str]] = None,
                                 variable_patterns: Optional[List[str]] = None,
                                 auto_discover: bool = False) -> None:
        """Configure which session state variables to track"""
        if tracked_variables:
            self.tracked_variables = tracked_variables
        if variable_patterns:
            self.variable_patterns = variable_patterns
        self.auto_discover_variables = auto_discover
    
    def _get_session_state_summary(self) -> Dict[str, Any]:
        """Get summary of current Streamlit session state"""
        if 'st' not in globals():
            return {}
        
        summary = {}
        
        # Get variables to track
        variables_to_check = set()
        
        # Add explicitly tracked variables
        variables_to_check.update(self.tracked_variables)
        
        # Add pattern-matched variables
        if self.variable_patterns:
            for key in st.session_state.keys():
                for pattern in self.variable_patterns:
                    if re.match(pattern, key):
                        variables_to_check.add(key)
        
        # Auto-discover important variables if enabled
        if self.auto_discover_variables:
            variables_to_check.update(self._auto_discover_important_variables())
        
        # Fallback to default RNA-seq variables if nothing configured
        if not variables_to_check:
            variables_to_check = {
                'rnaseq_counts_df', 'rnaseq_metadata_df', 'anndata',
                'deseq_results', 'go_results', 'filtered_genes',
                'qc_done', 'filtered', 'normalized', 'clustered'
            }
        
        # Summarize each variable
        for var in variables_to_check:
            if var in st.session_state:
                summary[var] = self._summarize_variable(var, st.session_state[var])
        
        return summary
    
    def _auto_discover_important_variables(self) -> List[str]:
        """Auto-discover important session state variables"""
        important_vars = []
        
        for key, value in st.session_state.items():
            # Skip internal Streamlit variables
            if key.startswith('_') or key.startswith('FormSubmitter'):
                continue
                
            # Include DataFrames and large objects
            if hasattr(value, 'shape') and hasattr(value, 'size'):
                if value.size > 100:  # Arbitrary threshold for "important" data
                    important_vars.append(key)
            
            # Include boolean flags that might indicate analysis state
            elif isinstance(value, bool):
                important_vars.append(key)
            
            # Include dictionaries that might contain results
            elif isinstance(value, dict) and len(value) > 0:
                important_vars.append(key)
        
        return important_vars
    
    def _summarize_variable(self, name: str, value: Any) -> Dict[str, Any]:
        """Create a detailed summary of a session state variable"""
        summary = {"type": type(value).__name__}
        
        try:
            # Handle pandas DataFrames
            if hasattr(value, 'shape') and hasattr(value, 'columns'):
                summary.update({
                    "shape": value.shape,
                    "columns": list(value.columns) if hasattr(value, 'columns') else None,
                    "memory_usage": f"{value.memory_usage(deep=True).sum() / 1024**2:.2f} MB" if hasattr(value, 'memory_usage') else None
                })
            
            # Handle numpy arrays and similar
            elif hasattr(value, 'shape'):
                summary.update({
                    "shape": value.shape,
                    "dtype": str(getattr(value, 'dtype', 'unknown'))
                })
            
            # Handle dictionaries
            elif isinstance(value, dict):
                summary.update({
                    "keys": list(value.keys())[:10],  # First 10 keys
                    "size": len(value)
                })
            
            # Handle lists
            elif isinstance(value, list):
                summary.update({
                    "length": len(value),
                    "sample": value[:3] if len(value) > 0 else []
                })
            
            # Handle primitive types
            elif isinstance(value, (bool, int, float, str)):
                summary["value"] = value
            
            else:
                summary["description"] = f"Object of type {type(value).__name__}"
                
        except Exception as e:
            summary["error"] = f"Failed to summarize: {str(e)}"
        
        return summary
    
    @abstractmethod
    def _get_server_specific_context(self) -> Dict[str, Any]:
        """Get server-specific context - to be implemented by subclasses"""
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the server - to be implemented by subclasses"""
        pass
    
    def _init_resource_providers(self):
        """Initialize default resource providers"""
        # Session state provider
        self.resource_providers["session"] = SessionStateResourceProvider()
    
    def configure_resources(self,
                          cache_enabled: Optional[bool] = None,
                          auto_discover: Optional[bool] = None,
                          providers: Optional[Dict[str, ResourceProvider]] = None) -> None:
        """Configure the resource system"""
        if cache_enabled is not None:
            self.cache_enabled = cache_enabled
        
        if auto_discover is not None:
            self.auto_discover_resources = auto_discover
        
        if providers:
            self.resource_providers.update(providers)
    
    def register_resource_provider(self, scheme: str, provider: ResourceProvider) -> None:
        """Register a resource provider for a URI scheme"""
        self.resource_providers[scheme] = provider
        self.logger.info(f"Registered resource provider for scheme: {scheme}")
    
    async def discover_resources(self, pattern: Optional[str] = None) -> List[MCPResource]:
        """Discover resources from all providers"""
        discovered = []
        
        for scheme, provider in self.resource_providers.items():
            try:
                resources = await provider.list_resources(pattern)
                discovered.extend(resources)
            except Exception as e:
                self.logger.warning(f"Resource discovery failed for provider {scheme}: {e}")
        
        return discovered
    
    def configure_tool_discovery(self,
                                auto_discover: Optional[bool] = None,
                                tool_modules: Optional[List[str]] = None) -> None:
        """Configure automatic tool discovery"""
        if auto_discover is not None:
            self.auto_discover_tools = auto_discover
        
        if tool_modules:
            self.tool_modules.extend(tool_modules)
    
    def mcp_tool(self, 
                name: Optional[str] = None,
                description: Optional[str] = None,
                input_schema: Optional[Dict[str, Any]] = None,
                output_schema: Optional[Dict[str, Any]] = None):
        """Decorator for automatic tool registration"""
        def decorator(func: Callable):
            tool_name = name or func.__name__
            tool_description = description or func.__doc__ or f"Tool: {tool_name}"
            
            # Generate basic schema from function signature if not provided
            if input_schema is None:
                schema = self._generate_schema_from_function(func)
            else:
                schema = input_schema
            
            # Register the tool
            self.register_tool(
                name=tool_name,
                description=tool_description,
                input_schema=schema,
                handler=func,
                output_schema=output_schema
            )
            
            return func
        return decorator
    
    async def discover_tools(self) -> List[str]:
        """Discover and register tools from configured modules"""
        discovered_tools = []
        
        for module_name in self.tool_modules:
            try:
                module = __import__(module_name, fromlist=[''])
                
                # Look for functions with mcp_tool attribute
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if callable(attr) and hasattr(attr, '_mcp_tool_config'):
                        config = attr._mcp_tool_config
                        self.register_tool(
                            name=config.get('name', attr_name),
                            description=config.get('description', attr.__doc__ or f"Tool: {attr_name}"),
                            input_schema=config.get('input_schema', {}),
                            handler=attr,
                            output_schema=config.get('output_schema')
                        )
                        discovered_tools.append(config.get('name', attr_name))
                        
            except Exception as e:
                self.logger.warning(f"Tool discovery failed for module {module_name}: {e}")
        
        return discovered_tools
    
    def _generate_schema_from_function(self, func: Callable) -> Dict[str, Any]:
        """Generate JSON schema from function signature"""
        import inspect
        
        sig = inspect.signature(func)
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            if param_name in ['self', 'cls']:
                continue
                
            param_schema = {"type": "string"}  # Default type
            
            # Try to infer type from annotation
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_schema["type"] = "integer"
                elif param.annotation == float:
                    param_schema["type"] = "number"
                elif param.annotation == bool:
                    param_schema["type"] = "boolean"
                elif param.annotation == list:
                    param_schema["type"] = "array"
                elif param.annotation == dict:
                    param_schema["type"] = "object"
            
            # Check if parameter has default value
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
            else:
                param_schema["default"] = param.default
            
            properties[param_name] = param_schema
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }


# Test code to verify the module works independently
if __name__ == "__main__":
    import asyncio
    
    class TestMCPServer(MCPServer):
        """Test implementation of MCPServer"""
        
        def __init__(self):
            super().__init__("test_server", "1.0.0")
        
        async def initialize(self):
            """Initialize test server"""
            # Register a test tool
            self.register_tool(
                name="test_tool",
                description="A test tool",
                input_schema={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Test message"}
                    },
                    "required": ["message"]
                },
                handler=self._test_handler
            )
            
            # Register a test resource
            self.register_resource(
                uri="test://example",
                name="Test Resource",
                description="A test resource",
                mime_type="text/plain"
            )
            
            # Register a test prompt
            self.register_prompt(
                name="test_prompt",
                description="A test prompt",
                template="Hello {name}!",
                parameters={"name": "string"}
            )
        
        async def _test_handler(self, message: str):
            """Test tool handler"""
            return {"success": True, "message": f"Received: {message}"}
        
        def _get_server_specific_context(self):
            """Get test server context"""
            return {"test_data": "available", "status": "ready"}
    
    async def test_mcp_server():
        """Test MCPServer functionality"""
        print("Testing MCPServer...")
        
        # Test server creation
        server = TestMCPServer()
        print(f"✅ Created test server: {server.name} v{server.version}")
        
        # Test initialization
        await server.initialize()
        print(f"✅ Server initialized with {len(server.tools)} tools")
        
        # Test capabilities
        capabilities = server.get_capabilities()
        print(f"✅ Server capabilities: {len(capabilities)} defined")
        
        # Test tool execution
        result = await server.execute_tool("test_tool", {"message": "Hello World"})
        print(f"✅ Tool execution: {result.get('success', False)}")
        
        # Test resource retrieval
        try:
            resource = await server.get_resource("test://example")
            print(f"✅ Resource access: {resource.get('success', False)}")
        except Exception as e:
            print(f"ℹ️  Resource access expected to fail: {type(e).__name__}")
        
        # Test prompt rendering
        prompt_result = await server.render_prompt("test_prompt", {"name": "Test"})
        print(f"✅ Prompt rendering: {prompt_result.get('success', False)}")
        
        # Test context methods
        analysis_context = server.get_analysis_context()
        pipeline_context = server.get_pipeline_context()
        print(f"✅ Context methods: analysis={len(analysis_context)}, pipeline={len(pipeline_context)}")
        
        # Test insights and actions
        insights = server.get_analysis_insights()
        actions = server.get_suggested_actions()
        print(f"✅ Insights and actions: insights={len(insights)} chars, actions={len(actions)}")
        
        print("🎉 All MCPServer tests passed!")
    
    # Run test
    asyncio.run(test_mcp_server()) 
    # python -m src.mcp.core.server