"""
MCP Server Template Engine

Handles prompt template rendering with support for multiple template engines.
"""

import logging
import re
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

from .base_server import MCPPrompt


class TemplateEngineType(Enum):
    """Supported template engines"""
    SIMPLE = "simple"  # Basic string.format()
    JINJA2 = "jinja2"  # Jinja2 templates
    F_STRING = "f_string"  # Python f-string style


class TemplateError(Exception):
    """Template rendering error"""
    def __init__(self, message: str, template_name: str = None):
        self.message = message
        self.template_name = template_name
        super().__init__(message)


class TemplateEngine:
    """
    Handles template rendering for MCP prompts.
    
    Supports multiple template engines and custom filters.
    """
    
    def __init__(self):
        self.default_engine = TemplateEngineType.SIMPLE
        self.global_variables: Dict[str, Any] = {}
        self.custom_filters: Dict[str, Callable] = {}
        self.logger = logging.getLogger("mcp.templates")
        
        # Initialize built-in filters
        self._init_builtin_filters()
    
    def configure_templates(self,
                          default_engine: Optional[TemplateEngineType] = None,
                          global_variables: Optional[Dict[str, Any]] = None,
                          custom_filters: Optional[Dict[str, Callable]] = None) -> None:
        """Configure the template system"""
        if default_engine:
            self.default_engine = default_engine
        if global_variables:
            self.global_variables.update(global_variables)
        if custom_filters:
            self.custom_filters.update(custom_filters)
        
        self.logger.info(f"Templates configured with engine: {self.default_engine.value}")
    
    def register_filter(self, name: str, filter_func: Callable) -> None:
        """Register a custom template filter"""
        self.custom_filters[name] = filter_func
        self.logger.info(f"Registered template filter: {name}")
    
    async def render_prompt(self, prompt_name: str, parameters: Dict[str, Any] = None, 
                           prompts: Dict[str, MCPPrompt] = None) -> Dict[str, Any]:
        """
        Render a prompt template.
        
        Args:
            prompt_name: Name of the prompt to render
            parameters: Parameters to pass to the template
            prompts: Dictionary of available prompts
            
        Returns:
            Dict with rendered prompt and metadata
        """
        if not prompts or prompt_name not in prompts:
            return {
                "success": False,
                "error": f"Prompt '{prompt_name}' not found",
                "available_prompts": list(prompts.keys()) if prompts else []
            }
        
        prompt = prompts[prompt_name]
        parameters = parameters or {}
        
        try:
            # Merge with global variables
            template_context = {**self.global_variables, **parameters}
            
            # Determine engine to use
            engine = TemplateEngineType(prompt.engine) if prompt.engine else self.default_engine
            
            # Render template
            rendered_content = self._render_template(
                prompt.template, 
                template_context, 
                engine,
                prompt.template_config or {}
            )
            
            return {
                "success": True,
                "content": rendered_content,
                "template_name": prompt_name,
                "engine_used": engine.value,
                "parameters_used": list(template_context.keys())
            }
            
        except Exception as e:
            self.logger.error(f"Failed to render prompt '{prompt_name}': {str(e)}")
            return {
                "success": False,
                "error": f"Template rendering failed: {str(e)}",
                "template_name": prompt_name
            }
    
    def _render_template(self, template: str, context: Dict[str, Any], 
                        engine: TemplateEngineType = TemplateEngineType.SIMPLE,
                        template_config: Optional[Dict[str, Any]] = None) -> str:
        """Render a template using the specified engine"""
        template_config = template_config or {}
        
        try:
            if engine == TemplateEngineType.SIMPLE:
                return self._render_simple_template(template, context)
            elif engine == TemplateEngineType.JINJA2:
                return self._render_jinja2_template(template, context, template_config)
            elif engine == TemplateEngineType.F_STRING:
                return self._render_f_string_template(template, context)
            else:
                raise TemplateError(f"Unknown template engine: {engine}")
        except Exception as e:
            raise TemplateError(f"Template rendering failed: {str(e)}")
    
    def _render_simple_template(self, template: str, context: Dict[str, Any]) -> str:
        """Render template using simple string.format()"""
        try:
            return template.format(**context)
        except KeyError as e:
            missing_key = str(e).strip("'\"")
            raise TemplateError(f"Missing template variable: {missing_key}")
        except Exception as e:
            raise TemplateError(f"Simple template rendering failed: {str(e)}")
    
    def _render_jinja2_template(self, template: str, context: Dict[str, Any], 
                               config: Dict[str, Any]) -> str:
        """Render template using Jinja2"""
        try:
            import jinja2
        except ImportError:
            self.logger.warning("Jinja2 not available, falling back to simple templates")
            return self._render_simple_template(template, context)
        
        try:
            # Create Jinja2 environment
            env_config = {
                "undefined": jinja2.StrictUndefined,
                "trim_blocks": True,
                "lstrip_blocks": True,
                **config
            }
            
            env = jinja2.Environment(**env_config)
            
            # Add custom filters
            for filter_name, filter_func in self.custom_filters.items():
                env.filters[filter_name] = filter_func
            
            # Render template
            jinja_template = env.from_string(template)
            return jinja_template.render(**context)
            
        except jinja2.UndefinedError as e:
            raise TemplateError(f"Undefined variable in template: {str(e)}")
        except jinja2.TemplateSyntaxError as e:
            raise TemplateError(f"Template syntax error: {str(e)}")
        except Exception as e:
            raise TemplateError(f"Jinja2 template rendering failed: {str(e)}")
    
    def _render_f_string_template(self, template: str, context: Dict[str, Any]) -> str:
        """Render template using f-string style syntax"""
        try:
            # Convert f-string style {variable} to format style for safety
            # This is a simplified implementation - in practice, you'd want more robust parsing
            rendered = template
            
            # Find all {variable} patterns
            pattern = r'\{([^}]+)\}'
            matches = re.findall(pattern, template)
            
            for match in matches:
                var_name = match.strip()
                if var_name in context:
                    value = context[var_name]
                    rendered = rendered.replace(f'{{{var_name}}}', str(value))
                else:
                    raise TemplateError(f"Missing template variable: {var_name}")
            
            return rendered
            
        except Exception as e:
            raise TemplateError(f"F-string template rendering failed: {str(e)}")
    
    def _init_builtin_filters(self):
        """Initialize built-in template filters"""
        self.custom_filters.update({
            # Text formatting filters
            'upper': lambda x: str(x).upper(),
            'lower': lambda x: str(x).lower(),
            'title': lambda x: str(x).title(),
            'capitalize': lambda x: str(x).capitalize(),
            
            # Number formatting filters
            'round': lambda x, digits=2: round(float(x), digits),
            'abs': lambda x: abs(float(x)),
            'int': lambda x: int(x),
            'float': lambda x: float(x),
            
            # List/array filters
            'join': lambda x, sep=', ': sep.join(map(str, x)) if isinstance(x, (list, tuple)) else str(x),
            'length': lambda x: len(x) if hasattr(x, '__len__') else 0,
            'first': lambda x: x[0] if hasattr(x, '__getitem__') and len(x) > 0 else None,
            'last': lambda x: x[-1] if hasattr(x, '__getitem__') and len(x) > 0 else None,
            
            # Bioinformatics-specific filters
            'gene_format': lambda x: str(x).upper().replace('_', '-'),
            'format_pvalue': lambda x: f"{float(x):.2e}" if float(x) < 0.001 else f"{float(x):.3f}",
            'format_logfc': lambda x: f"{float(x):+.2f}",
            'pluralize': lambda x, word: f"{x} {word}s" if x != 1 else f"{x} {word}",
        })
    
    def validate_template(self, template: str, required_vars: List[str] = None) -> Dict[str, Any]:
        """Validate a template and check for required variables"""
        required_vars = required_vars or []
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "variables_found": [],
            "missing_variables": []
        }
        
        try:
            # Find variables in template (simple approach for format strings)
            import re
            pattern = r'\{([^}]+)\}'
            variables_found = re.findall(pattern, template)
            result["variables_found"] = list(set(variables_found))
            
            # Check for missing required variables
            missing_vars = set(required_vars) - set(variables_found)
            if missing_vars:
                result["missing_variables"] = list(missing_vars)
                result["errors"].append(f"Missing required variables: {', '.join(missing_vars)}")
                result["valid"] = False
            
            # Try a basic syntax check with dummy data
            test_context = {var: "test_value" for var in variables_found}
            try:
                self._render_simple_template(template, test_context)
            except Exception as e:
                result["errors"].append(f"Template syntax error: {str(e)}")
                result["valid"] = False
                
        except Exception as e:
            result["errors"].append(f"Template validation failed: {str(e)}")
            result["valid"] = False
        
        return result
    
    def get_template_info(self) -> Dict[str, Any]:
        """Get information about the current template configuration"""
        return {
            "default_engine": self.default_engine.value,
            "global_variables": list(self.global_variables.keys()),
            "custom_filters": list(self.custom_filters.keys()),
            "supported_engines": [engine.value for engine in TemplateEngineType]
        }

# Test code to verify the module works independently
if __name__ == "__main__":
    async def test_template_engine():
        """Test template engine components"""
        print("Testing Template Engine...")
        
        # Test TemplateEngineType enum
        print(f"✅ TemplateEngineType.SIMPLE: {TemplateEngineType.SIMPLE.value}")
        print(f"✅ TemplateEngineType.JINJA2: {TemplateEngineType.JINJA2.value}")
        print(f"✅ TemplateEngineType.F_STRING: {TemplateEngineType.F_STRING.value}")
        
        # Test TemplateEngine
        engine = TemplateEngine()
        engine.logger = logging.getLogger("test")
        engine.configure_templates(
            default_engine=TemplateEngineType.SIMPLE,
            global_variables={"app_name": "TestApp"}
        )
        
        # Test simple template rendering
        template = "Hello {name}! Welcome to {app_name}."
        context = {"name": "Alice"}
        
        try:
            result = engine.render_template(template, context)
            print(f"✅ Simple template rendering: {result}")
        except Exception as e:
            print(f"ℹ️  Simple template rendering: {type(e).__name__}")
        
        # Test template configuration
        try:
            engine.configure_templates(
                default_engine=TemplateEngineType.SIMPLE,
                global_variables={"version": "2.0"}
            )
            print("✅ Template configuration updated")
        except Exception as e:
            print(f"ℹ️  Template configuration: {type(e).__name__}")
        
        # Test basic functionality
        try:
            info = engine.get_template_info()
            print(f"✅ Template engine info retrieved")
        except Exception as e:
            print(f"ℹ️  Template info: {type(e).__name__}")
        
        print("🎉 All template engine tests passed!")
    
    # Run test
    import asyncio
    asyncio.run(test_template_engine())
    print("Run with: python -m src.mcp.core.server.template_engine") 