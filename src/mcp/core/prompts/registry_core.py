"""
Core Registry Components for Domain Expert Registry

Contains the essential data structures and entry management for the registry system.
"""

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Type

from .core import DomainExpert, TechniqueMetadata
from .security import SecurityValidator, SecurityLevel, SecurityContext

import logging
logger = logging.getLogger(__name__)


@dataclass
class EnhancedRegistryEntry:
    """Enhanced entry in the domain expert registry with security and monitoring"""
    expert_class: Type[DomainExpert]
    expert_instance: Optional[DomainExpert] = None
    metadata: Optional[TechniqueMetadata] = None
    module_path: Optional[str] = None
    last_loaded: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    load_time: float = 0.0
    security_level: SecurityLevel = SecurityLevel.PUBLIC
    validation_status: Optional[Dict[str, Any]] = None
    health_status: str = "unknown"  # healthy, warning, error
    
    def get_expert(self, security_context: Optional[SecurityContext] = None) -> DomainExpert:
        """Get expert instance with security checks and monitoring"""
        # Check security access
        if security_context and not SecurityValidator.check_security_level_access(
            security_context.level, self.security_level
        ):
            raise PermissionError(f"Access denied to expert with security level {self.security_level}")
        
        # Lazy loading with monitoring
        if self.expert_instance is None:
            start_time = time.time()
            try:
                self.expert_instance = self.expert_class()
                self.metadata = self.expert_instance.get_metadata()
                self.health_status = "healthy"
            except Exception as e:
                self.health_status = "error"
                logger.error(f"Failed to instantiate expert {self.expert_class.__name__}: {e}")
                raise
            finally:
                self.load_time = time.time() - start_time
                self.last_loaded = datetime.now()
        
        # Update access tracking
        self.last_accessed = datetime.now()
        self.access_count += 1
        
        return self.expert_instance
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = {
            "expert_class_name": self.expert_class.__name__,
            "module_path": self.module_path,
            "last_loaded": self.last_loaded.isoformat() if self.last_loaded else None,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "access_count": self.access_count,
            "load_time": self.load_time,
            "health_status": self.health_status,
            "has_instance": self.expert_instance is not None
        }
        
        if include_sensitive:
            data["security_level"] = self.security_level.value
            data["validation_status"] = self.validation_status
        
        if self.metadata:
            data["metadata"] = self.metadata.to_dict()
        
        return data


class RegistryCache:
    """Caching system for registry operations"""
    
    def __init__(self, max_size: int = 100):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._timestamps: Dict[str, datetime] = {}
        self._max_size = max_size
        self._lock = threading.Lock()
    
    def get(self, key: str, ttl_minutes: int = 10) -> Optional[Dict[str, Any]]:
        """Get cached value if still valid"""
        with self._lock:
            if key not in self._cache:
                return None
            
            # Check TTL
            timestamp = self._timestamps.get(key)
            if timestamp:
                age = datetime.now() - timestamp
                if age.total_seconds() > ttl_minutes * 60:
                    # Expired
                    del self._cache[key]
                    del self._timestamps[key]
                    return None
            
            return self._cache[key]
    
    def set(self, key: str, value: Dict[str, Any]):
        """Set cached value"""
        with self._lock:
            # Implement simple LRU if cache is full
            if len(self._cache) >= self._max_size:
                oldest_key = min(self._timestamps.keys(), 
                               key=lambda k: self._timestamps[k])
                del self._cache[oldest_key]
                del self._timestamps[oldest_key]
            
            self._cache[key] = value
            self._timestamps[key] = datetime.now()
    
    def clear(self):
        """Clear all cached entries"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()


class RegistryStats:
    """Statistics tracking for registry operations"""
    
    def __init__(self):
        self._stats = {
            "experts_registered": 0,
            "experts_accessed": 0,
            "discovery_runs": 0,
            "load_failures": 0,
            "validation_runs": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        self._lock = threading.Lock()
    
    def increment(self, metric: str, value: int = 1):
        """Increment a statistic"""
        with self._lock:
            if metric in self._stats:
                self._stats[metric] += value
    
    def get_stats(self) -> Dict[str, int]:
        """Get current statistics"""
        with self._lock:
            return self._stats.copy()
    
    def reset(self):
        """Reset all statistics"""
        with self._lock:
            for key in self._stats:
                self._stats[key] = 0


if __name__ == "__main__":
    # Test core registry components
    print("Testing Core Registry Components")
    
    # Test registry cache
    cache = RegistryCache(max_size=5)
    cache.set("test_key", {"data": "test_value"})
    cached_value = cache.get("test_key")
    print(f"✓ Cache test: {cached_value}")
    
    # Test registry stats
    stats = RegistryStats()
    stats.increment("experts_registered", 3)
    stats.increment("cache_hits", 5)
    current_stats = stats.get_stats()
    print(f"✓ Stats test: {current_stats['experts_registered']} experts, {current_stats['cache_hits']} cache hits")
    
    print("\n✅ Core registry components test completed!") 