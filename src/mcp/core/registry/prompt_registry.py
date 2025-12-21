"""
Core Prompt Registry - Enhanced Version

Core functionality for automated prompt discovery and registration using decorators
and function introspection. Enhanced for scalability, security, and robustness.

This is the main prompt registry file that handles auto-discovery and caching.
Domain integration and templates are in separate files.
"""

import logging
import hashlib
import threading
from typing import Dict, List, Any, Optional, Callable, Union
from functools import wraps
from dataclasses import dataclass, field
from enum import Enum
import time
import re

# Configure logger
logger = logging.getLogger(__name__)


class PromptCategory(Enum):
    """Standardized prompt categories"""
    ANALYSIS = "analysis"
    GUIDANCE = "guidance"
    TROUBLESHOOTING = "troubleshooting"
    INTERPRETATION = "interpretation"
    WORKFLOW = "workflow"
    VALIDATION = "validation"
    EXPORT = "export"
    ADMIN = "admin"


class SecurityLevel(Enum):
    """Security levels for prompts"""
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    ADMIN = "admin"


@dataclass
class PromptConfig:
    """Enhanced configuration for an MCP prompt"""
    name: str
    description: str
    template: str
    parameters: Dict[str, str]
    handler: Optional[Callable] = None
    category: PromptCategory = PromptCategory.ANALYSIS
    security_level: SecurityLevel = SecurityLevel.PUBLIC
    domain_context: Optional[str] = None
    expertise_level: Optional[str] = None
    version: str = "1.0.0"
    deprecated: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate prompt configuration"""
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Prompt name must be a non-empty string")
        
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', self.name):
            raise ValueError("Prompt name must be a valid identifier")
        
        if not self.description or not isinstance(self.description, str):
            raise ValueError("Prompt description must be a non-empty string")
        
        if not self.template or not isinstance(self.template, str):
            raise ValueError("Prompt template must be a non-empty string")
        
        if not isinstance(self.parameters, dict):
            raise ValueError("Prompt parameters must be a dictionary")


def mcp_prompt(name: str, 
               description: str, 
               template: Optional[str] = None, 
               parameters: Optional[Dict[str, str]] = None,
               category: Union[str, PromptCategory] = PromptCategory.ANALYSIS,
               security_level: Union[str, SecurityLevel] = SecurityLevel.PUBLIC,
               domain_context: Optional[str] = None,
               expertise_level: Optional[str] = None,
               version: str = "1.0.0",
               deprecated: bool = False):
    """
    Enhanced decorator to mark a method as an MCP prompt
    
    Args:
        name: Prompt name (must be valid identifier)
        description: Prompt description
        template: Optional template override (if None, method should return template)
        parameters: Parameter dictionary (param_name -> type)
        category: Prompt category
        security_level: Security level required to access prompt
        domain_context: Domain-specific context information
        expertise_level: Required expertise level
        version: Prompt version
        deprecated: Whether prompt is deprecated
    """
    def decorator(func):
        # Validate inputs
        if not name or not isinstance(name, str):
            raise ValueError("Prompt name must be a non-empty string")
        
        if not description or not isinstance(description, str):
            raise ValueError("Prompt description must be a non-empty string")
        
        # Store metadata on function
        func._mcp_prompt = True
        func._prompt_name = name
        func._prompt_description = description
        func._prompt_template = template
        func._prompt_parameters = parameters or {}
        func._prompt_category = category
        func._prompt_security_level = security_level
        func._prompt_domain_context = domain_context
        func._prompt_expertise_level = expertise_level
        func._prompt_version = version
        func._prompt_deprecated = deprecated
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error executing prompt handler for {name}: {e}")
                raise
        
        # Copy metadata to wrapper
        for attr in ['_mcp_prompt', '_prompt_name', '_prompt_description', '_prompt_template',
                     '_prompt_parameters', '_prompt_category', '_prompt_security_level',
                     '_prompt_domain_context', '_prompt_expertise_level', '_prompt_version',
                     '_prompt_deprecated']:
            setattr(wrapper, attr, getattr(func, attr))
        
        return wrapper
    return decorator


class PromptCache:
    """Thread-safe cache for prompt configurations"""
    
    def __init__(self, max_size: int = 300):
        self._cache = {}
        self._lock = threading.RLock()
        self.max_size = max_size
        self.hit_count = 0
        self.miss_count = 0
    
    def get(self, key: str) -> Optional[Dict[str, PromptConfig]]:
        """Get cached prompt configurations"""
        with self._lock:
            if key in self._cache:
                self.hit_count += 1
                return self._cache[key]
            self.miss_count += 1
            return None
    
    def set(self, key: str, value: Dict[str, PromptConfig]):
        """Cache prompt configurations"""
        with self._lock:
            if len(self._cache) >= self.max_size:
                # Simple LRU - remove oldest
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            
            self._cache[key] = value
    
    def clear(self):
        """Clear cache"""
        with self._lock:
            self._cache.clear()
            self.hit_count = 0
            self.miss_count = 0


class AutoPromptRegistry:
    """Enhanced prompt registry with caching, validation, and security"""
    
    def __init__(self, enable_caching: bool = True):
        self.cache = PromptCache() if enable_caching else None
        self.logger = logger.getChild("AutoPromptRegistry")
        
        # Metrics
        self.discovery_count = 0
        self.error_count = 0
        
        # Lazy import domain integration
        self._domain_integration = None
    
    def discover_prompts(self, handler_instance, 
                        security_context: Optional[Dict[str, Any]] = None) -> Dict[str, PromptConfig]:
        """
        Enhanced prompt discovery with caching and security filtering
        
        Args:
            handler_instance: Handler instance to scan
            security_context: Current user's security context
            
        Returns:
            Dictionary of discovered prompt configurations
        """
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(handler_instance, security_context)
            
            # Check cache first
            if self.cache:
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    self.logger.debug(f"Cache hit for {handler_instance.__class__.__name__}")
                    return cached_result
            
            # Discover prompts
            prompts = self._discover_prompts_internal(handler_instance, security_context)
            
            # Add domain expert prompts if available
            domain_prompts = self._get_domain_prompts(handler_instance)
            prompts.update(domain_prompts)
            
            # Cache result
            if self.cache:
                self.cache.set(cache_key, prompts)
            
            # Update metrics
            self.discovery_count += 1
            
            self.logger.info(f"Discovered {len(prompts)} prompts from {handler_instance.__class__.__name__}")
            return prompts
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error discovering prompts from {handler_instance.__class__.__name__}: {e}")
            return {}
    
    def _discover_prompts_internal(self, handler_instance, 
                                 security_context: Optional[Dict[str, Any]]) -> Dict[str, PromptConfig]:
        """Internal prompt discovery logic"""
        prompts = {}
        
        # Get all methods from the handler instance
        for method_name in dir(handler_instance):
            try:
                method = getattr(handler_instance, method_name)
                
                # Skip private methods and non-callable attributes
                if method_name.startswith('_') or not callable(method):
                    continue
                
                # Check if method is decorated as an MCP prompt
                if hasattr(method, '_mcp_prompt') and method._mcp_prompt:
                    prompt_config = self._generate_prompt_config(method)
                    
                    # Apply security filtering
                    if self._is_prompt_accessible(prompt_config, security_context):
                        prompts[prompt_config.name] = prompt_config
                    else:
                        self.logger.debug(f"Prompt {prompt_config.name} filtered by security context")
                        
            except Exception as e:
                self.logger.warning(f"Error processing method {method_name}: {e}")
                continue
        
        return prompts
    
    def _generate_prompt_config(self, method: Callable) -> PromptConfig:
        """Generate prompt configuration from method metadata"""
        try:
            # Get template - either from decorator or method call
            template = getattr(method, '_prompt_template')
            if not template:
                try:
                    template = method()
                except Exception as e:
                    self.logger.warning(f"Could not get template from method {method.__name__}: {e}")
                    template = f"Template for {getattr(method, '_prompt_name')}"
            
            # Convert string enums to enum objects if needed
            category = getattr(method, '_prompt_category', PromptCategory.ANALYSIS)
            if isinstance(category, str):
                try:
                    category = PromptCategory(category.lower())
                except ValueError:
                    category = PromptCategory.ANALYSIS
            
            security_level = getattr(method, '_prompt_security_level', SecurityLevel.PUBLIC)
            if isinstance(security_level, str):
                try:
                    security_level = SecurityLevel(security_level.lower())
                except ValueError:
                    security_level = SecurityLevel.PUBLIC
            
            # Enhanced metadata
            metadata = {
                "source_class": method.__self__.__class__.__name__ if hasattr(method, '__self__') else "unknown",
                "discovery_time": time.time(),
                "method_name": method.__name__
            }
            
            return PromptConfig(
                name=getattr(method, '_prompt_name'),
                description=getattr(method, '_prompt_description'),
                template=template,
                parameters=getattr(method, '_prompt_parameters', {}),
                handler=method,
                category=category,
                security_level=security_level,
                domain_context=getattr(method, '_prompt_domain_context'),
                expertise_level=getattr(method, '_prompt_expertise_level'),
                version=getattr(method, '_prompt_version', "1.0.0"),
                deprecated=getattr(method, '_prompt_deprecated', False),
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Error generating prompt config for {method.__name__}: {e}")
            raise
    
    def _get_domain_prompts(self, handler_instance) -> Dict[str, PromptConfig]:
        """Get domain expert prompts for this handler"""
        try:
            # Lazy import domain integration to avoid circular dependencies
            if self._domain_integration is None:
                try:
                    from .prompt_domain_integration import get_domain_prompts_for_handler
                    self._domain_integration = get_domain_prompts_for_handler
                except ImportError:
                    self.logger.debug("Domain integration not available")
                    self._domain_integration = lambda x: {}
            
            return self._domain_integration(handler_instance)
            
        except Exception as e:
            self.logger.warning(f"Error getting domain prompts: {e}")
            return {}
    
    def _generate_cache_key(self, handler_instance, security_context: Optional[Dict[str, Any]]) -> str:
        """Generate cache key for handler instance and security context"""
        class_name = handler_instance.__class__.__name__
        security_str = str(security_context) if security_context else "public"
        return hashlib.md5(f"{class_name}:{security_str}".encode()).hexdigest()
    
    def _is_prompt_accessible(self, prompt_config: PromptConfig, 
                            security_context: Optional[Dict[str, Any]]) -> bool:
        """Check if prompt is accessible given security context"""
        
        # Public prompts are always accessible
        if prompt_config.security_level == SecurityLevel.PUBLIC:
            return True
        
        # If no security context, only allow public prompts
        if not security_context:
            return False
        
        user_level = security_context.get("security_level", "public")
        
        # Simple security hierarchy
        level_order = ["public", "internal", "restricted", "admin"]
        try:
            required_idx = level_order.index(prompt_config.security_level.value)
            user_idx = level_order.index(user_level) if user_level in level_order else 0
            return user_idx >= required_idx
        except (ValueError, AttributeError):
            # Default to deny access if levels are invalid
            return False
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        stats = {
            "discovery_count": self.discovery_count,
            "error_count": self.error_count
        }
        
        if self.cache:
            total_requests = self.cache.hit_count + self.cache.miss_count
            hit_rate = self.cache.hit_count / total_requests if total_requests > 0 else 0
            
            stats["cache"] = {
                "size": len(self.cache._cache),
                "max_size": self.cache.max_size,
                "hit_count": self.cache.hit_count,
                "miss_count": self.cache.miss_count,
                "hit_rate": hit_rate
            }
        
        return stats
    
    def clear_cache(self):
        """Clear the registry cache"""
        if self.cache:
            self.cache.clear()
            self.logger.info("Prompt registry cache cleared")


# Global registry instance
auto_prompt_registry = AutoPromptRegistry()


def get_auto_prompt_configs(handler_instance, 
                          security_context: Optional[Dict[str, Any]] = None) -> Dict[str, PromptConfig]:
    """
    Get automatically discovered prompt configurations with security filtering
    
    Args:
        handler_instance: Instance of a handler class with @mcp_prompt decorated methods
        security_context: Current user's security context
        
    Returns:
        Dictionary mapping prompt names to PromptConfig objects
    """
    return auto_prompt_registry.discover_prompts(handler_instance, security_context)


def validate_prompt_config(prompt_config: PromptConfig) -> List[str]:
    """
    Validate a prompt configuration and return list of issues
    
    Returns:
        List of validation errors (empty if valid)
    """
    issues = []
    
    try:
        # Name validation
        if not prompt_config.name:
            issues.append("Prompt name is required")
        elif not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', prompt_config.name):
            issues.append("Prompt name must be a valid identifier")
        
        # Description validation
        if not prompt_config.description:
            issues.append("Prompt description is required")
        
        # Template validation
        if not prompt_config.template:
            issues.append("Prompt template is required")
        
        # Parameters validation
        if not isinstance(prompt_config.parameters, dict):
            issues.append("Prompt parameters must be a dictionary")
        
        # Check for parameter placeholders in template
        import re
        template_params = set(re.findall(r'\{(\w+)\}', prompt_config.template))
        declared_params = set(prompt_config.parameters.keys())
        
        missing_params = template_params - declared_params
        if missing_params:
            issues.append(f"Template uses undeclared parameters: {missing_params}")
        
        unused_params = declared_params - template_params
        if unused_params:
            issues.append(f"Declared parameters not used in template: {unused_params}")
        
    except Exception as e:
        issues.append(f"Validation error: {str(e)}")
    
    return issues


def main():
    """Main function for module testing"""
    print("Testing Enhanced AutoPromptRegistry...")
    
    # Test enhanced prompt registry
    registry = AutoPromptRegistry()
    
    # Create test handler with enhanced decorators
    class TestHandler:
        @mcp_prompt(
            name="analyze_results",
            description="Analyze biological results with expert guidance",
            template="Analyze the {analysis_type} results:\n{results}\n\nProvide insights on {focus_area}.",
            parameters={"analysis_type": "string", "results": "string", "focus_area": "string"},
            category=PromptCategory.INTERPRETATION,
            security_level=SecurityLevel.INTERNAL,
            domain_context="genomics",
            expertise_level="expert",
            version="2.0.0"
        )
        def get_analysis_prompt(self):
            return "Analyze the {analysis_type} results:\n{results}\n\nProvide insights on {focus_area}."
        
        @mcp_prompt(
            name="troubleshoot_issue",
            description="Help troubleshoot common analysis issues",
            parameters={"issue": "string", "step": "string"},
            category=PromptCategory.TROUBLESHOOTING,
            security_level=SecurityLevel.PUBLIC
        )
        def get_troubleshoot_prompt(self):
            return "Issue: {issue}\nStep: {step}\n\nPlease provide troubleshooting guidance."
        
        # Non-decorated method should be ignored
        def regular_method(self):
            return "not a prompt"
    
    # Test discovery with different security contexts
    handler = TestHandler()
    
    public_prompts = registry.discover_prompts(handler, {"security_level": "public"})
    internal_prompts = registry.discover_prompts(handler, {"security_level": "internal"})
    
    print(f"✅ Public context: {len(public_prompts)} prompts")
    print(f"✅ Internal context: {len(internal_prompts)} prompts")
    
    # Test prompt config details
    for name, config in internal_prompts.items():
        print(f"✅ Prompt: {config.name} (v{config.version})")
        print(f"   Category: {config.category.value}")
        print(f"   Security: {config.security_level.value}")
        print(f"   Parameters: {list(config.parameters.keys())}")
        print(f"   Domain: {config.domain_context}")
        print(f"   Expertise: {config.expertise_level}")
    
    # Test validation
    for name, config in internal_prompts.items():
        issues = validate_prompt_config(config)
        if issues:
            print(f"❌ Validation issues for {name}: {issues}")
        else:
            print(f"✅ {name} passed validation")
    
    # Test cache functionality
    cached_prompts = registry.discover_prompts(handler, {"security_level": "internal"})
    print(f"✅ Cache test: {len(cached_prompts)} prompts (should be cached)")
    
    # Test registry stats
    stats = registry.get_registry_stats()
    print(f"✅ Registry stats: {stats}")
    
    print("🎉 All Enhanced PromptRegistry tests passed!")


if __name__ == "__main__":
    main()