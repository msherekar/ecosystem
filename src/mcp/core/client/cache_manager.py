"""
MCP Client Cache Manager

Handles caching with TTL support and size limits.
"""

import logging
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
from collections import OrderedDict


class CacheEntry:
    """
    Cache entry with TTL support and metadata.
    """
    
    def __init__(self, 
                 value: Any, 
                 ttl_seconds: int = 300,
                 tags: Optional[Set[str]] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize cache entry.
        
        Args:
            value: The cached value
            ttl_seconds: Time-to-live in seconds
            tags: Tags for grouping/invalidation
            metadata: Additional metadata
        """
        self.value = value
        self.created_at = datetime.now()
        self.ttl = timedelta(seconds=ttl_seconds)
        self.access_count = 0
        self.last_accessed = self.created_at
        self.tags = tags or set()
        self.metadata = metadata or {}
    
    @property
    def is_expired(self) -> bool:
        """Check if entry is expired"""
        return datetime.now() > (self.created_at + self.ttl)
    
    @property
    def age_seconds(self) -> float:
        """Get age in seconds"""
        return (datetime.now() - self.created_at).total_seconds()
    
    @property
    def remaining_ttl_seconds(self) -> float:
        """Get remaining TTL in seconds"""
        if self.is_expired:
            return 0.0
        return self.ttl.total_seconds() - self.age_seconds
    
    def access(self) -> Any:
        """Access the entry and update statistics"""
        self.access_count += 1
        self.last_accessed = datetime.now()
        return self.value


class CacheManager:
    """
    Manages caching with TTL, size limits, and advanced features.
    
    Features:
    - TTL-based expiration
    - LRU eviction
    - Tag-based invalidation
    - Size limits
    - Access statistics
    """
    
    def __init__(self, 
                 max_size: int = 1000, 
                 default_ttl: int = 300,
                 cleanup_interval: int = 60):
        """
        Initialize cache manager.
        
        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds
            cleanup_interval: Cleanup interval in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        
        # Use OrderedDict for LRU ordering
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._tag_index: Dict[str, Set[str]] = {}  # tag -> set of keys
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0,
            'sets': 0,
            'deletes': 0
        }
        
        self.logger = logging.getLogger("mcp.cache")
        self.logger.info(f"Cache manager initialized - max_size: {max_size}, default_ttl: {default_ttl}s")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            self.stats['misses'] += 1
            return None
        
        entry = self._cache[key]
        
        # Check expiration
        if entry.is_expired:
            self.remove(key)
            self.stats['misses'] += 1
            self.stats['expirations'] += 1
            return None
        
        # Move to end for LRU
        self._cache.move_to_end(key)
        
        # Update statistics and return value
        self.stats['hits'] += 1
        return entry.access()
    
    def set(self, 
            key: str, 
            value: Any, 
            ttl: Optional[int] = None,
            tags: Optional[Set[str]] = None,
            metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if None)
            tags: Tags for grouping
            metadata: Additional metadata
        """
        ttl = ttl or self.default_ttl
        tags = tags or set()
        
        # Remove old entry if exists
        if key in self._cache:
            self.remove(key)
        
        # Evict if at capacity
        if len(self._cache) >= self.max_size:
            self._evict_lru()
        
        # Create and store entry
        entry = CacheEntry(value, ttl, tags, metadata)
        self._cache[key] = entry
        
        # Update tag index
        for tag in tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(key)
        
        self.stats['sets'] += 1
        self.logger.debug(f"Cached key: {key} (TTL: {ttl}s, tags: {tags})")
    
    def remove(self, key: str) -> bool:
        """
        Remove key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was removed, False if not found
        """
        if key not in self._cache:
            return False
        
        entry = self._cache[key]
        
        # Remove from tag index
        for tag in entry.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(key)
                if not self._tag_index[tag]:
                    del self._tag_index[tag]
        
        # Remove from cache
        del self._cache[key]
        self.stats['deletes'] += 1
        self.logger.debug(f"Removed key: {key}")
        return True
    
    def clear(self, tags: Optional[Set[str]] = None) -> int:
        """
        Clear cache entries.
        
        Args:
            tags: If provided, only clear entries with these tags
            
        Returns:
            Number of entries cleared
        """
        if tags is None:
            # Clear everything
            count = len(self._cache)
            self._cache.clear()
            self._tag_index.clear()
            self.logger.info(f"Cleared all cache entries: {count}")
            return count
        
        # Clear by tags
        keys_to_remove = set()
        for tag in tags:
            if tag in self._tag_index:
                keys_to_remove.update(self._tag_index[tag])
        
        count = 0
        for key in keys_to_remove:
            if self.remove(key):
                count += 1
        
        self.logger.info(f"Cleared {count} cache entries with tags: {tags}")
        return count
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries.
        
        Returns:
            Number of expired entries removed
        """
        current_time = datetime.now()
        expired_keys = []
        
        for key, entry in self._cache.items():
            if current_time > (entry.created_at + entry.ttl):
                expired_keys.append(key)
        
        count = 0
        for key in expired_keys:
            if self.remove(key):
                count += 1
                self.stats['expirations'] += 1
        
        if count > 0:
            self.logger.debug(f"Cleaned up {count} expired cache entries")
        
        return count
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry"""
        if not self._cache:
            return
        
        # OrderedDict maintains insertion/access order
        lru_key = next(iter(self._cache))
        self.remove(lru_key)
        self.stats['evictions'] += 1
        self.logger.debug(f"Evicted LRU key: {lru_key}")
    
    def contains(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        if key not in self._cache:
            return False
        
        entry = self._cache[key]
        if entry.is_expired:
            self.remove(key)
            self.stats['expirations'] += 1
            return False
        
        return True
    
    def get_ttl(self, key: str) -> Optional[float]:
        """Get remaining TTL for a key"""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if entry.is_expired:
            return 0.0
        
        return entry.remaining_ttl_seconds
    
    def extend_ttl(self, key: str, additional_seconds: int) -> bool:
        """
        Extend TTL for a key.
        
        Args:
            key: Cache key
            additional_seconds: Additional seconds to add to TTL
            
        Returns:
            True if TTL was extended, False if key not found
        """
        if key not in self._cache:
            return False
        
        entry = self._cache[key]
        entry.ttl += timedelta(seconds=additional_seconds)
        self.logger.debug(f"Extended TTL for key: {key} by {additional_seconds}s")
        return True
    
    def get_by_tag(self, tag: str) -> Dict[str, Any]:
        """
        Get all entries with a specific tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            Dict of key-value pairs
        """
        result = {}
        
        if tag in self._tag_index:
            for key in self._tag_index[tag].copy():  # Copy to avoid modification during iteration
                value = self.get(key)
                if value is not None:
                    result[key] = value
        
        return result
    
    def get_keys_by_pattern(self, pattern: str) -> List[str]:
        """
        Get keys matching a pattern.
        
        Args:
            pattern: Pattern to match (supports * wildcard)
            
        Returns:
            List of matching keys
        """
        import fnmatch
        
        matching_keys = []
        for key in self._cache.keys():
            if fnmatch.fnmatch(key, pattern):
                # Check if not expired
                if self.contains(key):
                    matching_keys.append(key)
        
        return matching_keys
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        hit_rate = 0.0
        total_requests = self.stats['hits'] + self.stats['misses']
        if total_requests > 0:
            hit_rate = self.stats['hits'] / total_requests * 100
        
        return {
            **self.stats,
            'hit_rate_percent': round(hit_rate, 2),
            'current_size': len(self._cache),
            'max_size': self.max_size,
            'fill_percentage': round(len(self._cache) / self.max_size * 100, 2) if self.max_size > 0 else 0,
            'unique_tags': len(self._tag_index)
        }
    
    def get_entry_info(self, key: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a cache entry"""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        return {
            'key': key,
            'created_at': entry.created_at.isoformat(),
            'last_accessed': entry.last_accessed.isoformat(),
            'access_count': entry.access_count,
            'ttl_seconds': entry.ttl.total_seconds(),
            'remaining_ttl_seconds': entry.remaining_ttl_seconds,
            'age_seconds': entry.age_seconds,
            'is_expired': entry.is_expired,
            'tags': list(entry.tags),
            'metadata': entry.metadata,
            'value_type': type(entry.value).__name__
        }
    
    def reset_stats(self) -> None:
        """Reset cache statistics"""
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0,
            'sets': 0,
            'deletes': 0
        }
        self.logger.info("Cache statistics reset")
    
    def get_size_info(self) -> Dict[str, Any]:
        """Get cache size information"""
        try:
            import sys
            total_size = 0
            for entry in self._cache.values():
                total_size += sys.getsizeof(entry.value)
            
            return {
                'entry_count': len(self._cache),
                'estimated_size_bytes': total_size,
                'average_entry_size_bytes': total_size // len(self._cache) if self._cache else 0
            }
        except Exception:
            return {
                'entry_count': len(self._cache),
                'estimated_size_bytes': -1,  # Unknown
                'average_entry_size_bytes': -1
            }

# Test code to verify the module works independently
if __name__ == "__main__":
    import asyncio
    import time
    
    async def test_cache_manager():
        """Test cache manager components"""
        print("Testing Cache Manager...")
        
        # Test TTLCache
        cache = CacheManager(max_size=100, default_ttl=60)
        
        # Test basic set/get
        cache.set("key1", "value1")
        value = cache.get("key1")
        assert value == "value1"
        print("✅ Basic cache set/get works")
        
        # Test TTL expiration
        cache.set("key2", "value2", ttl=0.1)  # 100ms TTL
        await asyncio.sleep(0.2)  # Wait for expiration
        value = cache.get("key2")
        assert value is None
        print("✅ TTL expiration works")
        
        # Test cache with tags
        cache.set("key3", "value3", tags=["group1", "test"])
        cache.set("key4", "value4", tags=["group1"])
        cache.set("key5", "value5", tags=["group2"])
        
        # Invalidate by tag
        cache.clear(["group1"])
        
        assert cache.get("key3") is None
        assert cache.get("key4") is None
        assert cache.get("key5") == "value5"  # Different tag, should remain
        print("✅ Tag-based invalidation works")
        
        # Test cache statistics
        stats = cache.get_stats()
        assert "hits" in stats
        assert "misses" in stats
        assert "evictions" in stats
        print(f"✅ Cache statistics: {stats}")
        
        # Test LRU eviction
        small_cache = CacheManager(max_size=2, default_ttl=60)
        small_cache.set("a", "1")
        small_cache.set("b", "2")
        small_cache.set("c", "3")  # Should evict "a"
        
        assert small_cache.get("a") is None
        assert small_cache.get("b") == "2"
        assert small_cache.get("c") == "3"
        print("✅ LRU eviction works")
        
        # Test advanced cache features
        advanced_cache = CacheManager(max_size=50, default_ttl=30)
        
        # Test metadata storage
        advanced_cache.set(
            "metadata_key", 
            {"value": "test"}, 
            metadata={"source": "test", "priority": "high"}
        )
        
        entry_info = advanced_cache.get_entry_info("metadata_key")
        assert entry_info is not None
        assert entry_info["metadata"]["source"] == "test"
        print("✅ Metadata storage works")
        
        # Test TTL extension
        advanced_cache.set("extend_key", "extend_value", ttl=1)
        time.sleep(0.5)  # Wait half the TTL
        
        extended = advanced_cache.extend_ttl("extend_key", 10)
        assert extended
        print("✅ TTL extension works")
        
        # Test pattern matching
        advanced_cache.set("user:1:profile", {"name": "Alice"})
        advanced_cache.set("user:2:profile", {"name": "Bob"})
        advanced_cache.set("post:1", {"title": "Hello"})
        
        user_keys = advanced_cache.get_keys_by_pattern("user:*")
        assert len(user_keys) == 2
        print("✅ Pattern matching works")
        
        # Test cache size information
        size_info = advanced_cache.get_size_info()
        assert "entry_count" in size_info
        print(f"✅ Size info: {size_info['entry_count']} entries")
        
        # Test cache cleanup
        advanced_cache.set("expire_key", "expire_value", ttl=0.1)
        time.sleep(0.2)
        
        cleaned = advanced_cache.cleanup_expired()
        assert cleaned >= 1
        print("✅ Expired entry cleanup works")
        
        # Test statistics reset
        advanced_cache.reset_stats()
        stats_after_reset = advanced_cache.get_stats()
        assert stats_after_reset["hits"] == 0
        assert stats_after_reset["misses"] == 0
        print("✅ Statistics reset works")
        
        print("🎉 All cache manager tests passed!")
    
    # Run test
    asyncio.run(test_cache_manager())
    print("Run with: python -m src.mcp.core.client.cache_manager") 