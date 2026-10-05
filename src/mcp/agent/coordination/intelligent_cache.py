"""
Intelligent Caching System
Multi-level cache with semantic similarity and optimization.
"""

import hashlib
import pickle
import sys
from pathlib import Path as _Path

_SRC = _Path(__file__).resolve().parents[3]
if str(_SRC) not in sys.path:  # pragma: no cover - import plumbing
    sys.path.insert(0, str(_SRC))

from gliaent.io.secure_pickle import (  # noqa: E402
    IntegrityError,
    dumps_signed,
    loads_signed,
)
import time
import asyncio
import logging
from typing import Any, Optional, Union, Dict, List, Tuple
from dataclasses import dataclass
from collections import defaultdict, OrderedDict
from threading import RLock
import weakref


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    value: Any
    created_at: float
    access_count: int = 0
    last_accessed: float = 0.0
    ttl: float = 3600.0  # 1 hour default
    size_bytes: int = 0
    semantic_hash: Optional[str] = None


@dataclass 
class CacheConfig:
    """Configuration for intelligent cache."""
    local_cache_size: int = 1000
    similarity_threshold: float = 0.8
    default_ttl: float = 3600.0
    enable_semantic_cache: bool = True
    enable_compression: bool = False
    memory_limit_mb: int = 100
    cleanup_interval: int = 300  # 5 minutes


class IntelligentCache:
    """Multi-level intelligent cache with semantic similarity."""
    
    def __init__(self, config: CacheConfig = None, redis_client=None):
        self.config = config or CacheConfig()
        self.redis_client = redis_client
        self.logger = logging.getLogger("intelligent_cache")
        
        # Local cache with LRU eviction
        self.local_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.cache_lock = RLock()  # Thread-safe access
        
        # Cache statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'semantic_hits': 0,
            'redis_hits': 0,
            'redis_misses': 0,
            'total_size_bytes': 0
        }
        
        # Semantic cache for similar queries (if enabled)
        self.semantic_cache: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
        
        # Background cleanup task
        self.cleanup_task: Optional[asyncio.Task] = None
        self.shutdown_event = asyncio.Event()
        
        # Start background cleanup
        if self.config.cleanup_interval > 0:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
    def _generate_cache_key(self, namespace: str = "default", *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = f"{namespace}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _calculate_size(self, value: Any) -> int:
        """Estimate size of value in bytes."""
        try:
            return len(pickle.dumps(value))
        except:
            return 1024  # Rough estimate if serialization fails
    
    async def get(
        self, 
        key: str, 
        use_semantic_similarity: bool = None
    ) -> Optional[Any]:
        """Get value from cache with semantic similarity fallback."""
        
        use_semantic = (
            use_semantic_similarity if use_semantic_similarity is not None 
            else self.config.enable_semantic_cache
        )
        
        # Try exact match first
        entry = await self._get_exact(key)
        if entry:
            self.stats['hits'] += 1
            with self.cache_lock:
                entry.access_count += 1
                entry.last_accessed = time.time()
                # Move to end (most recently used)
                if key in self.local_cache:
                    self.local_cache.move_to_end(key)
            return entry.value
        
        # Try semantic similarity if enabled
        if use_semantic:
            similar_entry = await self._get_similar(key)
            if similar_entry:
                self.stats['semantic_hits'] += 1
                return similar_entry.value
        
        self.stats['misses'] += 1
        return None
    
    async def _get_exact(self, key: str) -> Optional[CacheEntry]:
        """Get exact cache entry."""
        
        # Try local cache first
        with self.cache_lock:
            if key in self.local_cache:
                entry = self.local_cache[key]
                if not self._is_expired(entry):
                    return entry
                else:
                    # Remove expired entry
                    del self.local_cache[key]
                    self.stats['total_size_bytes'] -= entry.size_bytes
        
        # Try Redis cache
        if self.redis_client:
            try:
                data = await self._redis_get(key)
                if data:
                    # A shared or compromised Redis is untrusted input, so the
                    # payload is verified before it reaches the unpickler.
                    try:
                        entry = loads_signed(data)
                    except IntegrityError as exc:
                        self.logger.error(
                            "discarding Redis cache entry %s: %s", key, exc
                        )
                        await self._redis_delete(key)
                        return None
                    if not self._is_expired(entry):
                        # Promote to local cache
                        self._add_to_local_cache(key, entry)
                        self.stats['redis_hits'] += 1
                        return entry
                    else:
                        # Remove expired entry from Redis
                        await self._redis_delete(key)
                else:
                    self.stats['redis_misses'] += 1
            except Exception as e:
                self.logger.warning(f"Redis get failed for key {key}: {e}")
        
        return None
    
    async def _get_similar(self, key: str) -> Optional[CacheEntry]:
        """Get semantically similar cache entry."""
        
        if not self.config.enable_semantic_cache:
            return None
        
        best_match = None
        best_similarity = 0.0
        
        # Limit search to avoid performance issues
        search_keys = list(self.local_cache.keys())[:100]
        
        for cached_key in search_keys:
            similarity = self._calculate_similarity(key, cached_key)
            if similarity > best_similarity and similarity >= self.config.similarity_threshold:
                best_similarity = similarity
                best_match = cached_key
        
        if best_match:
            with self.cache_lock:
                if best_match in self.local_cache:
                    return self.local_cache[best_match]
        
        return None
    
    def _calculate_similarity(self, key1: str, key2: str) -> float:
        """Calculate similarity between cache keys."""
        if key1 == key2:
            return 1.0
        
        # Simple implementation - could be enhanced with embeddings
        # Jaccard similarity of words
        words1 = set(key1.lower().split())
        words2 = set(key2.lower().split())
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: float = None,
        semantic_hash: str = None
    ):
        """Set value in cache."""
        
        ttl = ttl or self.config.default_ttl
        size_bytes = self._calculate_size(value)
        
        entry = CacheEntry(
            value=value,
            created_at=time.time(),
            last_accessed=time.time(),
            ttl=ttl,
            size_bytes=size_bytes,
            semantic_hash=semantic_hash
        )
        
        # Add to local cache
        self._add_to_local_cache(key, entry)
        
        # Add to Redis cache
        if self.redis_client:
            try:
                await self._redis_set(key, dumps_signed(entry), int(ttl))
            except Exception as e:
                self.logger.warning(f"Redis set failed for key {key}: {e}")
    
    def _add_to_local_cache(self, key: str, entry: CacheEntry):
        """Add entry to local cache with memory management."""
        
        with self.cache_lock:
            # Check memory limit
            memory_limit_bytes = self.config.memory_limit_mb * 1024 * 1024
            
            # Evict entries if necessary
            while (self.stats['total_size_bytes'] + entry.size_bytes > memory_limit_bytes and 
                   len(self.local_cache) > 0):
                self._evict_lru()
            
            # Add entry
            if key in self.local_cache:
                # Update existing entry
                old_entry = self.local_cache[key]
                self.stats['total_size_bytes'] -= old_entry.size_bytes
            
            self.local_cache[key] = entry
            self.stats['total_size_bytes'] += entry.size_bytes
            
            # Move to end (most recently used)
            self.local_cache.move_to_end(key)
    
    def _evict_lru(self):
        """Evict least recently used entry."""
        if not self.local_cache:
            return
        
        # Remove oldest entry
        lru_key, lru_entry = self.local_cache.popitem(last=False)
        self.stats['total_size_bytes'] -= lru_entry.size_bytes
        self.stats['evictions'] += 1
        
        self.logger.debug(f"Evicted LRU entry: {lru_key}")
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired."""
        return time.time() - entry.created_at > entry.ttl
    
    async def _redis_get(self, key: str) -> Optional[bytes]:
        """Get from Redis asynchronously."""
        if hasattr(self.redis_client, 'get'):
            return self.redis_client.get(key)
        return None
    
    async def _redis_set(self, key: str, value: bytes, ttl: int):
        """Set in Redis asynchronously."""
        if hasattr(self.redis_client, 'setex'):
            self.redis_client.setex(key, ttl, value)
    
    async def _redis_delete(self, key: str):
        """Delete from Redis asynchronously."""
        if hasattr(self.redis_client, 'delete'):
            self.redis_client.delete(key)
    
    async def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        deleted = False
        
        # Delete from local cache
        with self.cache_lock:
            if key in self.local_cache:
                entry = self.local_cache.pop(key)
                self.stats['total_size_bytes'] -= entry.size_bytes
                deleted = True
        
        # Delete from Redis cache
        if self.redis_client:
            try:
                await self._redis_delete(key)
                deleted = True
            except Exception as e:
                self.logger.warning(f"Redis delete failed for key {key}: {e}")
        
        return deleted
    
    async def clear(self):
        """Clear all cache entries."""
        with self.cache_lock:
            self.local_cache.clear()
            self.stats['total_size_bytes'] = 0
        
        if self.redis_client:
            try:
                if hasattr(self.redis_client, 'flushdb'):
                    self.redis_client.flushdb()
            except Exception as e:
                self.logger.warning(f"Redis clear failed: {e}")
        
        self.logger.info("Cache cleared")
    
    async def _cleanup_loop(self):
        """Background cleanup loop for expired entries."""
        while not self.shutdown_event.is_set():
            try:
                await self._cleanup_expired()
                await asyncio.sleep(self.config.cleanup_interval)
            except Exception as e:
                self.logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(self.config.cleanup_interval)
    
    async def _cleanup_expired(self):
        """Remove expired entries from local cache."""
        expired_keys = []
        
        with self.cache_lock:
            for key, entry in self.local_cache.items():
                if self._is_expired(entry):
                    expired_keys.append(key)
        
        # Remove expired entries
        for key in expired_keys:
            await self.delete(key)
        
        if expired_keys:
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0
        
        with self.cache_lock:
            local_cache_info = {
                'size': len(self.local_cache),
                'max_size': self.config.local_cache_size,
                'memory_usage_mb': self.stats['total_size_bytes'] / (1024 * 1024),
                'memory_limit_mb': self.config.memory_limit_mb
            }
        
        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate': hit_rate,
            'semantic_hits': self.stats['semantic_hits'],
            'redis_hits': self.stats['redis_hits'],
            'redis_misses': self.stats['redis_misses'],
            'evictions': self.stats['evictions'],
            'local_cache': local_cache_info,
            'config': {
                'similarity_threshold': self.config.similarity_threshold,
                'default_ttl': self.config.default_ttl,
                'semantic_cache_enabled': self.config.enable_semantic_cache
            }
        }
    
    def reset_stats(self):
        """Reset cache statistics."""
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'semantic_hits': 0,
            'redis_hits': 0,
            'redis_misses': 0,
            'total_size_bytes': self.stats['total_size_bytes']  # Keep memory usage
        }
        self.logger.info("Cache statistics reset")
    
    async def shutdown(self):
        """Shutdown cache and cleanup background tasks."""
        self.shutdown_event.set()
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Intelligent cache shutdown complete")


def main():
    """Test the intelligent cache individually."""
    import asyncio
    
    async def test_intelligent_cache():
        print("🧪 Testing IntelligentCache...")
        
        # Create cache with small limits for testing
        config = CacheConfig(
            local_cache_size=5,
            memory_limit_mb=1,
            similarity_threshold=0.5,
            cleanup_interval=2
        )
        cache = IntelligentCache(config)
        print("✅ Cache initialized")
        
        # Test basic set/get
        await cache.set("test_key", "test_value", ttl=10)
        value = await cache.get("test_key")
        print(f"✅ Basic set/get: {value}")
        
        # Test cache miss
        missing = await cache.get("nonexistent_key")
        print(f"✅ Cache miss: {missing is None}")
        
        # Test semantic similarity
        await cache.set("hello world", "greeting", ttl=10)
        await cache.set("goodbye world", "farewell", ttl=10)
        
        # This should find semantic similarity
        similar = await cache.get("hello earth", use_semantic_similarity=True)
        print(f"✅ Semantic similarity: {similar}")
        
        # Test cache eviction by filling beyond limit
        for i in range(10):
            await cache.set(f"large_key_{i}", "x" * 1000, ttl=10)
        
        stats_after_eviction = cache.get_stats()
        print(f"✅ Cache eviction: {stats_after_eviction['evictions']} evictions")
        
        # Test expiration (short TTL)
        await cache.set("expire_test", "will_expire", ttl=0.1)
        await asyncio.sleep(0.2)
        expired = await cache.get("expire_test")
        print(f"✅ Expiration test: {expired is None}")
        
        # Test statistics
        stats = cache.get_stats()
        print(f"✅ Statistics: hit_rate={stats['hit_rate']:.2f}, "
              f"memory_usage={stats['local_cache']['memory_usage_mb']:.2f}MB")
        
        # Test cleanup
        await cache._cleanup_expired()
        print("✅ Manual cleanup executed")
        
        # Test cache clearing
        await cache.clear()
        stats_after_clear = cache.get_stats()
        print(f"✅ Cache clear: size={stats_after_clear['local_cache']['size']}")
        
        # Test shutdown
        await cache.shutdown()
        print("✅ Cache shutdown complete")
        
        print("🎉 Intelligent cache tests completed!")
    
    # Run tests
    asyncio.run(test_intelligent_cache())


if __name__ == "__main__":
    main() 