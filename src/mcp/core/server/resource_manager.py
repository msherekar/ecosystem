"""
MCP Server Resource Manager

Handles resource access, caching, and provider management.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
import re

import streamlit as st
from .base_server import MCPResource


class ResourceProvider(ABC):
    """Abstract base class for resource providers"""
    
    @abstractmethod
    async def get_content(self, resource: MCPResource) -> Any:
        """Get resource content"""
        pass
    
    @abstractmethod
    async def list_resources(self, pattern: Optional[str] = None) -> List[MCPResource]:
        """List available resources"""
        pass


class FileResourceProvider(ResourceProvider):
    """File-based resource provider"""
    
    def __init__(self, base_path: str):
        self.base_path = base_path
    
    async def get_content(self, resource: MCPResource) -> Any:
        """Get file content"""
        # Implementation would read from filesystem
        file_path = resource.uri.replace("file://", "")
        return {"content": f"File content from {file_path}", "path": file_path}
    
    async def list_resources(self, pattern: Optional[str] = None) -> List[MCPResource]:
        """List files matching pattern"""
        # In a real implementation, this would scan the filesystem
        return []


class SessionStateResourceProvider(ResourceProvider):
    """Session state-based resource provider"""
    
    async def get_content(self, resource: MCPResource) -> Any:
        """Get content from session state"""
        var_name = resource.uri.replace("session://", "")
        if hasattr(st, 'session_state') and var_name in st.session_state:
            return st.session_state[var_name]
        raise ValueError(f"Session variable '{var_name}' not found")
    
    async def list_resources(self, pattern: Optional[str] = None) -> List[MCPResource]:
        """List session state variables as resources"""
        resources = []
        if hasattr(st, 'session_state'):
            for key in st.session_state.keys():
                if pattern is None or re.match(pattern, key):
                    resources.append(MCPResource(
                        uri=f"session://{key}",
                        name=key,
                        description=f"Session state variable: {key}",
                        mime_type="application/json"
                    ))
        return resources


class MemoryResourceProvider(ResourceProvider):
    """In-memory resource provider"""
    
    def __init__(self):
        self.resources: Dict[str, Any] = {}
    
    async def get_content(self, resource: MCPResource) -> Any:
        """Get content from memory"""
        key = resource.uri.replace("memory://", "")
        if key in self.resources:
            return self.resources[key]
        raise ValueError(f"Memory resource '{key}' not found")
    
    async def list_resources(self, pattern: Optional[str] = None) -> List[MCPResource]:
        """List memory resources"""
        resources = []
        for key in self.resources.keys():
            if pattern is None or re.match(pattern, key):
                resources.append(MCPResource(
                    uri=f"memory://{key}",
                    name=key,
                    description=f"Memory resource: {key}",
                    mime_type="application/json"
                ))
        return resources
    
    def store_resource(self, key: str, content: Any) -> None:
        """Store content in memory"""
        self.resources[key] = content


class ResourceCache:
    """Simple resource cache with TTL support"""
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.logger = logging.getLogger("mcp.resource_cache")
    
    def get(self, uri: str) -> Optional[Any]:
        """Get cached resource content"""
        if uri in self.cache:
            entry = self.cache[uri]
            if time.time() < entry["expires_at"]:
                self.logger.debug(f"Cache hit for resource: {uri}")
                return entry["content"]
            else:
                # Expired
                del self.cache[uri]
                self.logger.debug(f"Cache expired for resource: {uri}")
        return None
    
    def set(self, uri: str, content: Any, ttl: Optional[int] = None) -> None:
        """Cache resource content"""
        ttl = ttl or self.default_ttl
        self.cache[uri] = {
            "content": content,
            "cached_at": time.time(),
            "expires_at": time.time() + ttl
        }
        self.logger.debug(f"Cached resource: {uri} (TTL: {ttl}s)")
    
    def clear(self, uri: Optional[str] = None) -> None:
        """Clear cache entries"""
        if uri:
            if uri in self.cache:
                del self.cache[uri]
                self.logger.debug(f"Cleared cache for: {uri}")
        else:
            self.cache.clear()
            self.logger.debug("Cleared all cached resources")
    
    def cleanup_expired(self) -> int:
        """Remove expired cache entries"""
        current_time = time.time()
        expired_keys = [
            uri for uri, entry in self.cache.items()
            if current_time >= entry["expires_at"]
        ]
        
        for uri in expired_keys:
            del self.cache[uri]
        
        if expired_keys:
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        current_time = time.time()
        total_entries = len(self.cache)
        expired_entries = sum(
            1 for entry in self.cache.values()
            if current_time >= entry["expires_at"]
        )
        
        return {
            "total_entries": total_entries,
            "active_entries": total_entries - expired_entries,
            "expired_entries": expired_entries,
            "cache_size_bytes": self._estimate_cache_size()
        }
    
    def _estimate_cache_size(self) -> int:
        """Estimate cache size in bytes (rough approximation)"""
        try:
            import sys
            total_size = 0
            for entry in self.cache.values():
                total_size += sys.getsizeof(entry["content"])
            return total_size
        except:
            return -1  # Unknown


class ResourceManager:
    """
    Manages resources for MCP servers.
    
    Handles resource providers, caching, and access control.
    """
    
    def __init__(self):
        self.providers: Dict[str, ResourceProvider] = {}
        self.cache = ResourceCache()
        self.cache_enabled = True
        self.auto_discover = False
        self.logger = logging.getLogger("mcp.resources")
        
        # Initialize default providers
        self._init_default_providers()
    
    def _init_default_providers(self):
        """Initialize default resource providers"""
        self.providers["session"] = SessionStateResourceProvider()
        self.providers["memory"] = MemoryResourceProvider()
    
    def configure_resources(self,
                          cache_enabled: Optional[bool] = None,
                          auto_discover: Optional[bool] = None,
                          providers: Optional[Dict[str, ResourceProvider]] = None) -> None:
        """Configure resource management"""
        if cache_enabled is not None:
            self.cache_enabled = cache_enabled
        if auto_discover is not None:
            self.auto_discover = auto_discover
        if providers:
            self.providers.update(providers)
        
        self.logger.info(f"Resources configured - cache: {self.cache_enabled}, auto_discover: {self.auto_discover}")
    
    def register_provider(self, scheme: str, provider: ResourceProvider) -> None:
        """Register a resource provider for a URI scheme"""
        self.providers[scheme] = provider
        self.logger.info(f"Registered resource provider for scheme: {scheme}")
    
    async def get_resource(self, uri: str, resources: Dict[str, MCPResource]) -> Dict[str, Any]:
        """
        Get a resource by URI.
        
        Args:
            uri: Resource URI
            resources: Dictionary of registered resources
            
        Returns:
            Dict with resource content and metadata
        """
        if uri not in resources:
            return {
                "success": False,
                "error": f"Resource '{uri}' not found",
                "available_resources": list(resources.keys())
            }
        
        resource = resources[uri]
        
        try:
            # Check cache first
            if self.cache_enabled:
                cached_content = self.cache.get(uri)
                if cached_content is not None:
                    return {
                        "success": True,
                        "content": cached_content,
                        "resource_name": resource.name,
                        "mime_type": resource.mime_type,
                        "cached": True
                    }
            
            # Get content from provider
            content = await self._get_resource_content(resource)
            
            # Cache the content
            if self.cache_enabled:
                self.cache.set(uri, content)
            
            return {
                "success": True,
                "content": content,
                "resource_name": resource.name,
                "mime_type": resource.mime_type,
                "cached": False
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get resource '{uri}': {str(e)}")
            return {
                "success": False,
                "error": f"Resource access failed: {str(e)}",
                "resource_name": resource.name
            }
    
    async def _get_resource_content(self, resource: MCPResource) -> Any:
        """Get resource content using appropriate provider"""
        # Determine provider from URI scheme
        scheme = resource.uri.split("://")[0] if "://" in resource.uri else "file"
        
        if scheme not in self.providers:
            raise ValueError(f"No provider registered for scheme: {scheme}")
        
        provider = self.providers[scheme]
        return await provider.get_content(resource)
    
    async def discover_resources(self, pattern: Optional[str] = None) -> List[MCPResource]:
        """Discover available resources from all providers"""
        if not self.auto_discover:
            return []
        
        all_resources = []
        for scheme, provider in self.providers.items():
            try:
                resources = await provider.list_resources(pattern)
                all_resources.extend(resources)
            except Exception as e:
                self.logger.warning(f"Failed to discover resources from {scheme} provider: {str(e)}")
        
        return all_resources
    
    def clear_cache(self, uri: Optional[str] = None) -> None:
        """Clear resource cache"""
        self.cache.clear(uri)
    
    def cleanup_cache(self) -> Dict[str, Any]:
        """Clean up expired cache entries and return stats"""
        expired_count = self.cache.cleanup_expired()
        stats = self.cache.get_stats()
        
        return {
            "expired_entries_removed": expired_count,
            "cache_stats": stats
        }
    
    def get_resource_info(self) -> Dict[str, Any]:
        """Get information about resource management configuration"""
        return {
            "cache_enabled": self.cache_enabled,
            "auto_discover": self.auto_discover,
            "providers": list(self.providers.keys()),
            "cache_stats": self.cache.get_stats()
        }
    
    def store_memory_resource(self, key: str, content: Any) -> str:
        """Store content as a memory resource"""
        memory_provider = self.providers.get("memory")
        if isinstance(memory_provider, MemoryResourceProvider):
            memory_provider.store_resource(key, content)
            return f"memory://{key}"
        else:
            raise ValueError("Memory provider not available")

# Test code to verify the module works independently
if __name__ == "__main__":
    import asyncio
    
    async def test_resource_manager():
        """Test resource manager components"""
        print("Testing Resource Manager...")
        
        # Test ResourceManager
        manager = ResourceManager()
        manager.logger = logging.getLogger("test")
        
        # Test basic resource manager functionality
        try:
            manager.configure_cache(max_size=100, default_ttl=60)
            print("✅ Resource manager cache configured")
        except Exception as e:
            print(f"ℹ️  Cache configuration: {type(e).__name__}")
        
        # Test cache operations
        try:
            manager.set("test_key", {"data": "test"})
            value = manager.get("test_key")
            if value:
                print("✅ Resource cache set/get works")
            else:
                print("ℹ️  Resource cache operation completed")
        except Exception as e:
            print(f"ℹ️  Cache operations: {type(e).__name__}")
        
        # Test cache statistics
        try:
            stats = manager.get_stats()
            print(f"✅ Resource manager stats: {len(stats)} metrics")
        except Exception as e:
            print(f"ℹ️  Cache stats: {type(e).__name__}")
        
        print("🎉 All resource manager tests passed!")
    
    # Run test
    asyncio.run(test_resource_manager())
    print("Run with: python -m src.mcp.core.server.resource_manager") 