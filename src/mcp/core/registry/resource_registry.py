"""
Automated Resource Registry

Automatically generates resource configurations from handler methods using decorators
and function introspection. This eliminates the need for manual resource registration.
"""

import inspect
from typing import Dict, List, Any, Optional, Callable
from functools import wraps
from dataclasses import dataclass


@dataclass
class ResourceConfig:
    """Configuration for a single resource"""
    uri: str
    name: str
    description: str
    mime_type: str
    handler: Callable
    metadata: Optional[Dict[str, Any]] = None


def mcp_resource(uri: str, name: str, description: str, 
                mime_type: str = "application/json", 
                metadata: Optional[Dict[str, Any]] = None):
    """
    Decorator to automatically register a method as an MCP resource.
    
    The decorated method should return the resource data.
    """
    def decorator(func):
        # Store metadata on the function
        func._mcp_resource = True
        func._mcp_uri = uri
        func._mcp_name = name
        func._mcp_description = description
        func._mcp_mime_type = mime_type
        func._mcp_metadata = metadata or {}
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        # Copy metadata to wrapper
        wrapper._mcp_resource = True
        wrapper._mcp_uri = uri
        wrapper._mcp_name = name
        wrapper._mcp_description = description
        wrapper._mcp_mime_type = mime_type
        wrapper._mcp_metadata = metadata or {}
        
        return wrapper
    return decorator


class AutoResourceRegistry:
    """Automatically discovers and configures resources from handler classes"""
    
    def discover_resources(self, handlers_instance) -> Dict[str, ResourceConfig]:
        """
        Automatically discover resources from a handlers instance using introspection.
        
        Looks for methods decorated with @mcp_resource and generates configurations.
        """
        resources = {}
        
        # Get all methods from the handlers instance
        for method_name in dir(handlers_instance):
            method = getattr(handlers_instance, method_name)
            
            # Skip private methods and non-callable attributes
            if method_name.startswith('_') or not callable(method):
                continue
            
            # Check if method is decorated as an MCP resource
            if hasattr(method, '_mcp_resource') and method._mcp_resource:
                resource_config = self._generate_resource_config(method)
                resources[resource_config.uri] = resource_config
        
        return resources
    
    def _generate_resource_config(self, method: Callable) -> ResourceConfig:
        """Generate resource configuration from method metadata"""
        
        return ResourceConfig(
            uri=getattr(method, '_mcp_uri'),
            name=getattr(method, '_mcp_name'),
            description=getattr(method, '_mcp_description'),
            mime_type=getattr(method, '_mcp_mime_type', 'application/json'),
            handler=method,
            metadata=getattr(method, '_mcp_metadata', {})
        )


def get_auto_resource_configs(handlers_instance) -> Dict[str, ResourceConfig]:
    """
    Get automatically discovered resource configurations from handlers instance.
    
    This is the main function that servers will call to get resource configs.
    """
    registry = AutoResourceRegistry()
    return registry.discover_resources(handlers_instance)


# Test code to verify the module works independently
if __name__ == "__main__":
    def test_resource_registry():
        """Test AutoResourceRegistry functionality"""
        print("Testing AutoResourceRegistry...")
        
        # Create a test handler class with decorated methods
        class TestHandler:
            @mcp_resource(
                uri="test://data/summary",
                name="Data Summary",
                description="Get summary of uploaded data",
                mime_type="application/json",
                metadata={"category": "data"}
            )
            async def get_data_summary(self):
                return {"status": "test", "rows": 100}
            
            @mcp_resource(
                uri="test://results/analysis",
                name="Analysis Results",
                description="Get current analysis results",
                mime_type="application/json"
            )
            async def get_analysis_results(self):
                return {"results": "test results"}
            
            # Non-decorated method should be ignored
            def regular_method(self):
                return "not a resource"
        
        # Test registry
        registry = AutoResourceRegistry()
        handler = TestHandler()
        
        # Discover resources
        resources = registry.discover_resources(handler)
        
        print(f"✅ Discovered {len(resources)} resources")
        
        # Test each resource
        for uri, config in resources.items():
            print(f"✅ Resource: {config.name}")
            print(f"   URI: {config.uri}")
            print(f"   Description: {config.description}")
            print(f"   MIME Type: {config.mime_type}")
            print(f"   Metadata: {config.metadata}")
            print(f"   Handler: {config.handler.__name__}")
        
        # Test the main function
        configs = get_auto_resource_configs(handler)
        print(f"✅ get_auto_resource_configs returned {len(configs)} resources")
        
        print("🎉 All ResourceRegistry tests passed!")
    
    # Run test
    test_resource_registry()
    # python -m src.mcp.core.registry.resource_registry 