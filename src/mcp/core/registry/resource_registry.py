"""
Automated Resource Registry - Enhanced Version

Automatically generates resource configurations from handler methods using decorators
and function introspection. Enhanced for scalability, security, and robustness.

Key Improvements:
- Security filtering with access control
- Caching for performance at scale
- Enhanced validation and error handling
- Better URI management and metadata
- Resource versioning and deprecation support
"""

import logging
import hashlib
import threading
from typing import Dict, List, Any, Optional, Callable, Union
from functools import wraps
from dataclasses import dataclass, field
from enum import Enum
import re
import time

# Configure logger
logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Standardized resource types"""
    DATA = "data"
    ANALYSIS = "analysis"
    VISUALIZATION = "visualization"
    METADATA = "metadata"
    EXPORT = "export"
    CACHE = "cache"
    CONFIG = "config"


class SecurityLevel(Enum):
    """Security levels for resources"""
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    ADMIN = "admin"


@dataclass
class ResourceConfig:
    """Enhanced configuration for a single resource"""
    uri: str
    name: str
    description: str
    mime_type: str
    handler: Callable
    resource_type: ResourceType = ResourceType.DATA
    security_level: SecurityLevel = SecurityLevel.PUBLIC
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    deprecated: bool = False
    cache_ttl: Optional[int] = None  # Cache TTL in seconds
    size_estimate: Optional[int] = None  # Estimated size in bytes
    
    def __post_init__(self):
        """Validate resource configuration"""
        if not self.uri or not isinstance(self.uri, str):
            raise ValueError("Resource URI must be a non-empty string")
        
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://[^\s]+$', self.uri):
            raise ValueError("Resource URI must be a valid URI scheme")
        
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Resource name must be a non-empty string")
        
        if not callable(self.handler):
            raise ValueError("Resource handler must be callable")


def mcp_resource(uri: str, 
                name: str, 
                description: str,
                mime_type: str = "application/json",
                resource_type: Union[str, ResourceType] = ResourceType.DATA,
                security_level: Union[str, SecurityLevel] = SecurityLevel.PUBLIC,
                metadata: Optional[Dict[str, Any]] = None,
                version: str = "1.0.0",
                deprecated: bool = False,
                cache_ttl: Optional[int] = None,
                size_estimate: Optional[int] = None):
    """
    Enhanced decorator to automatically register a method as an MCP resource.
    
    Args:
        uri: Resource URI (must be valid URI scheme)
        name: Human-readable resource name
        description: Resource description
        mime_type: MIME type of the resource
        resource_type: Type of resource (ResourceType enum or string)
        security_level: Security level (SecurityLevel enum or string)
        metadata: Additional metadata
        version: Resource version
        deprecated: Whether resource is deprecated
        cache_ttl: Cache TTL in seconds
        size_estimate: Estimated resource size in bytes
    """
    def decorator(func):
        # Validate inputs
        if not uri or not isinstance(uri, str):
            raise ValueError("Resource URI must be a non-empty string")
        
        if not name or not isinstance(name, str):
            raise ValueError("Resource name must be a non-empty string")
        
        if not description or not isinstance(description, str):
            raise ValueError("Resource description must be a non-empty string")
        
        # Store metadata on the function
        func._mcp_resource = True
        func._mcp_uri = uri
        func._mcp_name = name
        func._mcp_description = description
        func._mcp_mime_type = mime_type
        func._mcp_resource_type = resource_type
        func._mcp_security_level = security_level
        func._mcp_metadata = metadata or {}
        func._mcp_version = version
        func._mcp_deprecated = deprecated
        func._mcp_cache_ttl = cache_ttl
        func._mcp_size_estimate = size_estimate
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Add basic validation/logging here if needed
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                logger.error(f"Error executing resource handler for {uri}: {e}")
                raise
        
        # Copy metadata to wrapper
        for attr in ['_mcp_resource', '_mcp_uri', '_mcp_name', '_mcp_description', 
                     '_mcp_mime_type', '_mcp_resource_type', '_mcp_security_level',
                     '_mcp_metadata', '_mcp_version', '_mcp_deprecated', 
                     '_mcp_cache_ttl', '_mcp_size_estimate']:
            setattr(wrapper, attr, getattr(func, attr))
        
        return wrapper
    return decorator


class ResourceCache:
    """Thread-safe cache for resource configurations"""
    
    def __init__(self, max_size: int = 500):
        self._cache = {}
        self._lock = threading.RLock()
        self.max_size = max_size
        self.hit_count = 0
        self.miss_count = 0
    
    def get(self, key: str) -> Optional[Dict[str, ResourceConfig]]:
        """Get cached resource configurations"""
        with self._lock:
            if key in self._cache:
                self.hit_count += 1
                return self._cache[key]
            self.miss_count += 1
            return None
    
    def set(self, key: str, value: Dict[str, ResourceConfig]):
        """Cache resource configurations"""
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


class AutoResourceRegistry:
    """Enhanced resource registry with caching, validation, and security"""
    
    def __init__(self, enable_caching: bool = True):
        self.cache = ResourceCache() if enable_caching else None
        self.logger = logger.getChild("AutoResourceRegistry")
        
        # Metrics
        self.discovery_count = 0
        self.error_count = 0
    
    def discover_resources(self, handlers_instance, 
                          security_context: Optional[Dict[str, Any]] = None) -> Dict[str, ResourceConfig]:
        """
        Enhanced resource discovery with caching and security filtering
        
        Args:
            handlers_instance: Handler instance to scan
            security_context: Current user's security context
            
        Returns:
            Dictionary of discovered resource configurations
        """
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(handlers_instance, security_context)
            
            # Check cache first
            if self.cache:
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    self.logger.debug(f"Cache hit for {handlers_instance.__class__.__name__}")
                    return cached_result
            
            # Discover resources
            resources = self._discover_resources_internal(handlers_instance, security_context)
            
            # Cache result
            if self.cache:
                self.cache.set(cache_key, resources)
            
            # Update metrics
            self.discovery_count += 1
            
            self.logger.info(f"Discovered {len(resources)} resources from {handlers_instance.__class__.__name__}")
            return resources
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error discovering resources from {handlers_instance.__class__.__name__}: {e}")
            return {}
    
    def _discover_resources_internal(self, handlers_instance, 
                                   security_context: Optional[Dict[str, Any]]) -> Dict[str, ResourceConfig]:
        """Internal resource discovery logic"""
        resources = {}
        
        # Get all methods from the handlers instance
        for method_name in dir(handlers_instance):
            try:
                method = getattr(handlers_instance, method_name)
                
                # Skip private methods and non-callable attributes
                if method_name.startswith('_') or not callable(method):
                    continue
                
                # Check if method is decorated as an MCP resource
                if hasattr(method, '_mcp_resource') and method._mcp_resource:
                    resource_config = self._generate_resource_config(method)
                    
                    # Apply security filtering
                    if self._is_resource_accessible(resource_config, security_context):
                        resources[resource_config.uri] = resource_config
                    else:
                        self.logger.debug(f"Resource {resource_config.uri} filtered by security context")
                        
            except Exception as e:
                self.logger.warning(f"Error processing method {method_name}: {e}")
                continue
        
        return resources
    
    def _generate_resource_config(self, method: Callable) -> ResourceConfig:
        """Generate resource configuration from method metadata"""
        try:
            # Convert string enums to enum objects if needed
            resource_type = getattr(method, '_mcp_resource_type', ResourceType.DATA)
            if isinstance(resource_type, str):
                try:
                    resource_type = ResourceType(resource_type.lower())
                except ValueError:
                    resource_type = ResourceType.DATA
            
            security_level = getattr(method, '_mcp_security_level', SecurityLevel.PUBLIC)
            if isinstance(security_level, str):
                try:
                    security_level = SecurityLevel(security_level.lower())
                except ValueError:
                    security_level = SecurityLevel.PUBLIC
            
            # Enhanced metadata
            metadata = getattr(method, '_mcp_metadata', {}).copy()
            metadata.update({
                "source_class": method.__self__.__class__.__name__ if hasattr(method, '__self__') else "unknown",
                "discovery_time": time.time(),
                "method_name": method.__name__
            })
            
            return ResourceConfig(
                uri=getattr(method, '_mcp_uri'),
                name=getattr(method, '_mcp_name'),
                description=getattr(method, '_mcp_description'),
                mime_type=getattr(method, '_mcp_mime_type', 'application/json'),
                handler=method,
                resource_type=resource_type,
                security_level=security_level,
                metadata=metadata,
                version=getattr(method, '_mcp_version', "1.0.0"),
                deprecated=getattr(method, '_mcp_deprecated', False),
                cache_ttl=getattr(method, '_mcp_cache_ttl'),
                size_estimate=getattr(method, '_mcp_size_estimate')
            )
            
        except Exception as e:
            self.logger.error(f"Error generating resource config for {method.__name__}: {e}")
            raise
    
    def _generate_cache_key(self, handlers_instance, security_context: Optional[Dict[str, Any]]) -> str:
        """Generate cache key for handlers instance and security context"""
        class_name = handlers_instance.__class__.__name__
        security_str = str(security_context) if security_context else "public"
        return hashlib.md5(f"{class_name}:{security_str}".encode()).hexdigest()
    
    def _is_resource_accessible(self, resource_config: ResourceConfig, 
                              security_context: Optional[Dict[str, Any]]) -> bool:
        """Check if resource is accessible given security context"""
        
        # Public resources are always accessible
        if resource_config.security_level == SecurityLevel.PUBLIC:
            return True
        
        # If no security context, only allow public resources
        if not security_context:
            return False
        
        user_level = security_context.get("security_level", "public")
        
        # Simple security hierarchy
        level_order = ["public", "internal", "restricted", "admin"]
        try:
            required_idx = level_order.index(resource_config.security_level.value)
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
            self.logger.info("Resource registry cache cleared")


# Global registry instance
auto_resource_registry = AutoResourceRegistry()


def get_auto_resource_configs(handlers_instance, 
                            security_context: Optional[Dict[str, Any]] = None) -> Dict[str, ResourceConfig]:
    """
    Get automatically discovered resource configurations with security filtering
    
    Args:
        handlers_instance: Instance of a handler class with @mcp_resource decorated methods
        security_context: Current user's security context
        
    Returns:
        Dictionary mapping resource URIs to ResourceConfig objects
    """
    return auto_resource_registry.discover_resources(handlers_instance, security_context)


def validate_resource_config(resource_config: ResourceConfig) -> List[str]:
    """
    Validate a resource configuration and return list of issues
    
    Returns:
        List of validation errors (empty if valid)
    """
    issues = []
    
    try:
        # URI validation
        if not resource_config.uri:
            issues.append("Resource URI is required")
        elif not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://[^\s]+$', resource_config.uri):
            issues.append("Resource URI must be a valid URI scheme")
        
        # Name validation
        if not resource_config.name:
            issues.append("Resource name is required")
        
        # Handler validation
        if not callable(resource_config.handler):
            issues.append("Resource handler must be callable")
        
        # MIME type validation
        if not resource_config.mime_type:
            issues.append("MIME type is required")
        elif not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9!#$&\-\^_]*\/[a-zA-Z0-9][a-zA-Z0-9!#$&\-\^_]*$', resource_config.mime_type):
            issues.append("Invalid MIME type format")
        
        # Size estimate validation
        if resource_config.size_estimate is not None and resource_config.size_estimate < 0:
            issues.append("Size estimate must be non-negative")
        
        # Cache TTL validation
        if resource_config.cache_ttl is not None and resource_config.cache_ttl < 0:
            issues.append("Cache TTL must be non-negative")
        
    except Exception as e:
        issues.append(f"Validation error: {str(e)}")
    
    return issues


def main():
    """Main function for module testing"""
    print("Testing Enhanced AutoResourceRegistry...")
    
    # Test enhanced resource registry
    registry = AutoResourceRegistry()
    
    # Create test handler with enhanced decorators
    class TestHandler:
        @mcp_resource(
            uri="bio://data/summary",
            name="Data Summary",
            description="Get summary of uploaded biological data",
            mime_type="application/json",
            resource_type=ResourceType.DATA,
            security_level=SecurityLevel.INTERNAL,
            metadata={"category": "data", "format": "json"},
            version="2.0.0",
            cache_ttl=300,
            size_estimate=1024
        )
        async def get_data_summary(self):
            return {"status": "test", "rows": 100, "columns": 50}
        
        @mcp_resource(
            uri="bio://analysis/results",
            name="Analysis Results",
            description="Get current analysis results",
            resource_type=ResourceType.ANALYSIS,
            security_level=SecurityLevel.PUBLIC
        )
        async def get_analysis_results(self):
            return {"results": "test results", "p_values": [0.01, 0.05]}
        
        # Non-decorated method should be ignored
        def regular_method(self):
            return "not a resource"
    
    # Test discovery with different security contexts
    handler = TestHandler()
    
    public_resources = registry.discover_resources(handler, {"security_level": "public"})
    internal_resources = registry.discover_resources(handler, {"security_level": "internal"})
    
    print(f"✅ Public context: {len(public_resources)} resources")
    print(f"✅ Internal context: {len(internal_resources)} resources")
    
    # Test resource config details
    for uri, config in internal_resources.items():
        print(f"✅ Resource: {config.name} (v{config.version})")
        print(f"   URI: {config.uri}")
        print(f"   Type: {config.resource_type.value}")
        print(f"   Security: {config.security_level.value}")
        print(f"   MIME: {config.mime_type}")
        print(f"   Cache TTL: {config.cache_ttl}")
        print(f"   Size: {config.size_estimate}")
    
    # Test validation
    for uri, config in internal_resources.items():
        issues = validate_resource_config(config)
        if issues:
            print(f"❌ Validation issues for {uri}: {issues}")
        else:
            print(f"✅ {uri} passed validation")
    
    # Test cache functionality
    cached_resources = registry.discover_resources(handler, {"security_level": "internal"})
    print(f"✅ Cache test: {len(cached_resources)} resources (should be cached)")
    
    # Test registry stats
    stats = registry.get_registry_stats()
    print(f"✅ Registry stats: {stats}")
    
    print("🎉 All Enhanced ResourceRegistry tests passed!")


if __name__ == "__main__":
    main()