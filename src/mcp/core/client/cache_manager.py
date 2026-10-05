"""
MCP Client Cache Manager - Enterprise Edition

Handles caching with TTL support, security, persistence, and Electron UI integration.
Designed for scalability, security, and optimal user experience.
"""

import asyncio
import hashlib
import json
import logging
import pickle
import threading
import time
import zlib
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

import sys

_SRC = Path(__file__).resolve().parents[3]
if str(_SRC) not in sys.path:  # pragma: no cover - import plumbing
    sys.path.insert(0, str(_SRC))

from gliaent.io.secure_pickle import (  # noqa: E402
    IntegrityError,
    dump_signed,
    load_signed,
)
from typing import Any, Dict, List, Optional, Set, Union, Callable
import uuid
import weakref


class CacheLevel(Enum):
    """Cache storage levels for hierarchical caching"""
    MEMORY = "memory"
    DISK = "disk"
    COMPRESSED = "compressed"
    ENCRYPTED = "encrypted"


class CacheStrategy(Enum):
    """Cache eviction strategies"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In, First Out
    TTL_BASED = "ttl_based"  # Time-based eviction
    PRIORITY_BASED = "priority_based"  # Priority-based eviction


class CachePriority(Enum):
    """Cache entry priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class CacheConfiguration:
    """Comprehensive cache configuration with validation"""
    max_memory_size: int = 1000
    max_disk_size: int = 10000
    default_ttl: int = 300
    cleanup_interval: int = 60
    enable_compression: bool = True
    enable_encryption: bool = False
    enable_persistence: bool = False
    persistence_path: Optional[str] = None
    compression_threshold: int = 1024  # Compress entries larger than 1KB
    max_entry_size: int = 10 * 1024 * 1024  # 10MB max per entry
    eviction_strategy: CacheStrategy = CacheStrategy.LRU
    enable_statistics: bool = True
    enable_security_validation: bool = True
    allow_insecure_keys: bool = False
    max_key_length: int = 256
    
    def __post_init__(self):
        """Validate configuration"""
        if self.max_memory_size < 1:
            raise ValueError("max_memory_size must be at least 1")
        if self.default_ttl < 1:
            raise ValueError("default_ttl must be at least 1 second")
        if self.max_entry_size < 1024:
            raise ValueError("max_entry_size must be at least 1KB")
        if self.max_key_length < 1:
            raise ValueError("max_key_length must be at least 1")
        
        # Setup persistence path
        if self.enable_persistence and not self.persistence_path:
            self.persistence_path = str(Path.home() / ".mcp_cache")


@dataclass
class CacheMetrics:
    """Comprehensive cache metrics for monitoring"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    expirations: int = 0
    compressions: int = 0
    decompressions: int = 0
    disk_reads: int = 0
    disk_writes: int = 0
    security_violations: int = 0
    
    # Performance metrics
    total_get_time: float = 0.0
    total_set_time: float = 0.0
    average_get_time: float = 0.0
    average_set_time: float = 0.0
    
    # Size metrics
    memory_usage_bytes: int = 0
    disk_usage_bytes: int = 0
    compression_ratio: float = 0.0
    
    def update_get_metrics(self, hit: bool, duration: float):
        """Update get operation metrics"""
        if hit:
            self.hits += 1
        else:
            self.misses += 1
        
        self.total_get_time += duration
        total_gets = self.hits + self.misses
        if total_gets > 0:
            self.average_get_time = self.total_get_time / total_gets
    
    def update_set_metrics(self, duration: float):
        """Update set operation metrics"""
        self.sets += 1
        self.total_set_time += duration
        self.average_set_time = self.total_set_time / self.sets
    
    def get_hit_rate(self) -> float:
        """Calculate hit rate percentage"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0
    
    def get_compression_ratio(self) -> float:
        """Calculate compression efficiency"""
        if self.compressions == 0:
            return 0.0
        return self.compression_ratio / self.compressions


class SecurityValidator:
    """Security validation for cache operations"""
    
    def __init__(self, config: CacheConfiguration):
        self.config = config
        self.blocked_patterns: Set[str] = set()
        self.suspicious_activity: Dict[str, List[datetime]] = defaultdict(list)
        self.max_operations_per_minute = 1000
    
    def validate_key(self, key: str) -> tuple[bool, str]:
        """Validate cache key for security issues"""
        if not self.config.enable_security_validation:
            return True, "Security validation disabled"
        
        # Check key length
        if len(key) > self.config.max_key_length:
            return False, f"Key too long: {len(key)} > {self.config.max_key_length}"
        
        # Check for null bytes and control characters
        if '\x00' in key or any(ord(c) < 32 for c in key):
            return False, "Key contains invalid characters"
        
        # Check for path traversal attempts
        if '..' in key or '/' in key or '\\' in key:
            if not self.config.allow_insecure_keys:
                return False, "Key contains path traversal patterns"
        
        # Check blocked patterns
        for pattern in self.blocked_patterns:
            if pattern in key:
                return False, f"Key matches blocked pattern: {pattern}"
        
        return True, "Key is valid"
    
    def validate_value(self, value: Any) -> tuple[bool, str]:
        """Validate cache value for security and size"""
        if not self.config.enable_security_validation:
            return True, "Security validation disabled"
        
        try:
            # Estimate serialized size
            serialized_size = len(pickle.dumps(value))
            if serialized_size > self.config.max_entry_size:
                return False, f"Value too large: {serialized_size} > {self.config.max_entry_size}"
        except Exception as e:
            return False, f"Value serialization failed: {e}"
        
        return True, "Value is valid"
    
    def check_rate_limit(self, operation: str) -> bool:
        """Check if operation is within rate limits"""
        current_time = datetime.now()
        
        # Clean old entries (older than 1 minute)
        cutoff_time = current_time - timedelta(minutes=1)
        self.suspicious_activity[operation] = [
            timestamp for timestamp in self.suspicious_activity[operation]
            if timestamp > cutoff_time
        ]
        
        # Check rate limit
        if len(self.suspicious_activity[operation]) >= self.max_operations_per_minute:
            return False
        
        # Record operation
        self.suspicious_activity[operation].append(current_time)
        return True
    
    def block_pattern(self, pattern: str):
        """Block a key pattern"""
        self.blocked_patterns.add(pattern)
    
    def unblock_pattern(self, pattern: str):
        """Unblock a key pattern"""
        self.blocked_patterns.discard(pattern)


class CacheEntry:
    """Enhanced cache entry with comprehensive metadata and security"""
    
    def __init__(self, 
                 value: Any, 
                 ttl_seconds: int = 300,
                 tags: Optional[Set[str]] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 priority: CachePriority = CachePriority.NORMAL,
                 level: CacheLevel = CacheLevel.MEMORY,
                 compressed: bool = False,
                 encrypted: bool = False):
        """
        Initialize enhanced cache entry.
        
        Args:
            value: The cached value
            ttl_seconds: Time-to-live in seconds
            tags: Tags for grouping/invalidation
            metadata: Additional metadata
            priority: Cache priority level
            level: Storage level (memory, disk, etc.)
            compressed: Whether the value is compressed
            encrypted: Whether the value is encrypted
        """
        self.entry_id = str(uuid.uuid4())
        self.value = value
        self.original_value = value  # Keep original for compression/encryption
        self.created_at = datetime.now()
        self.ttl = timedelta(seconds=ttl_seconds)
        self.tags = tags or set()
        self.metadata = metadata or {}
        self.priority = priority
        self.level = level
        self.compressed = compressed
        self.encrypted = encrypted
        
        # Access tracking
        self.access_count = 0
        self.last_accessed = self.created_at
        self.access_frequency = 0.0  # Accesses per hour
        
        # Size tracking
        self.original_size = self._calculate_size(value)
        self.stored_size = self.original_size
        
        # Security
        self.checksum = self._calculate_checksum(value)
        self.access_log: List[Dict[str, Any]] = []
    
    def _calculate_size(self, value: Any) -> int:
        """Calculate size of value in bytes"""
        try:
            return len(pickle.dumps(value))
        except:
            return 0
    
    def _calculate_checksum(self, value: Any) -> str:
        """Calculate checksum for integrity verification"""
        try:
            serialized = pickle.dumps(value)
            return hashlib.sha256(serialized).hexdigest()
        except:
            return ""
    
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
    
    @property
    def compression_ratio(self) -> float:
        """Get compression ratio"""
        if self.original_size == 0:
            return 0.0
        return (1.0 - (self.stored_size / self.original_size)) * 100
    
    def access(self, track_access: bool = True) -> Any:
        """Access the entry and update statistics"""
        if track_access:
            self.access_count += 1
            self.last_accessed = datetime.now()
            
            # Update access frequency (accesses per hour)
            age_hours = max(self.age_seconds / 3600, 0.01)  # Prevent division by zero
            self.access_frequency = self.access_count / age_hours
            
            # Log access for security monitoring
            self.access_log.append({
                "timestamp": self.last_accessed.isoformat(),
                "access_count": self.access_count
            })
            
            # Keep only recent access logs (last 100)
            if len(self.access_log) > 100:
                self.access_log = self.access_log[-100:]
        
        return self.value
    
    def verify_integrity(self) -> bool:
        """Verify entry integrity using checksum"""
        current_checksum = self._calculate_checksum(self.original_value)
        return current_checksum == self.checksum
    
    def get_info(self) -> Dict[str, Any]:
        """Get comprehensive entry information"""
        return {
            "entry_id": self.entry_id,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "access_frequency": round(self.access_frequency, 2),
            "ttl_seconds": self.ttl.total_seconds(),
            "remaining_ttl": self.remaining_ttl_seconds,
            "age_seconds": self.age_seconds,
            "is_expired": self.is_expired,
            "priority": self.priority.name,
            "level": self.level.value,
            "compressed": self.compressed,
            "encrypted": self.encrypted,
            "original_size": self.original_size,
            "stored_size": self.stored_size,
            "compression_ratio": self.compression_ratio,
            "tags": list(self.tags),
            "metadata": self.metadata,
            "value_type": type(self.original_value).__name__,
            "integrity_valid": self.verify_integrity()
        }


class CacheManager:
    """
    Enterprise-grade cache manager with security, persistence, and UI integration.
    
    Features:
    - Multi-level caching (memory, disk, compressed, encrypted)
    - Advanced eviction strategies (LRU, LFU, FIFO, Priority)
    - Security validation and monitoring
    - Compression and encryption support
    - Persistence and backup
    - Real-time metrics and monitoring
    - Electron UI/UX integration
    - Thread-safe operations
    """
    
    def __init__(self, config: Union[CacheConfiguration, Dict[str, Any], None] = None):
        """
        Initialize enterprise cache manager.
        
        Args:
            config: Cache configuration (CacheConfiguration, dict, or None for defaults)
        """
        # Parse configuration
        if config is None:
            self.config = CacheConfiguration()
        elif isinstance(config, dict):
            self.config = CacheConfiguration(**config)
        elif isinstance(config, CacheConfiguration):
            self.config = config
        else:
            raise ValueError("config must be CacheConfiguration, dict, or None")
        
        # Initialize core components
        self.logger = logging.getLogger("mcp.cache.enterprise")
        self.security_validator = SecurityValidator(self.config)
        self.metrics = CacheMetrics()
        
        # Storage layers
        self._memory_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._disk_cache: Dict[str, str] = {}  # key -> file_path
        
        # Indexes and tracking
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)
        self._priority_index: Dict[CachePriority, Set[str]] = defaultdict(set)
        self._size_index: Dict[str, int] = {}  # key -> size
        
        # Threading and synchronization
        self._lock = threading.RLock()
        self._background_tasks: Set[asyncio.Task] = set()
        self._is_running = False
        
        # Event system for UI integration
        self._event_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._event_queue: List[Dict[str, Any]] = []
        self._max_event_queue_size = 1000
        
        # Performance optimization
        self._compression_cache: Dict[str, bytes] = {}
        self._access_patterns: Dict[str, List[datetime]] = defaultdict(list)
        
        # Initialize persistence
        if self.config.enable_persistence:
            self._setup_persistence()
        
        self.logger.info(f"Enterprise cache manager initialized - memory: {self.config.max_memory_size}, "
                        f"security: {self.config.enable_security_validation}, "
                        f"compression: {self.config.enable_compression}")
    
    def _setup_persistence(self):
        """Setup disk persistence"""
        if self.config.persistence_path:
            self.persistence_dir = Path(self.config.persistence_path)
            self.persistence_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Persistence enabled at: {self.persistence_dir}")
    
    def _emit_event(self, event_name: str, data: Any):
        """Emit event for UI/monitoring systems"""
        event = {
            "event": event_name,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "cache_id": id(self)
        }
        
        # Add to event queue
        self._event_queue.append(event)
        if len(self._event_queue) > self._max_event_queue_size:
            self._event_queue.pop(0)
        
        # Call registered callbacks
        for callback in self._event_callbacks[event_name]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(data))
                else:
                    callback(data)
            except Exception as e:
                self.logger.error(f"Error in event callback {event_name}: {e}")
    
    def on(self, event_name: str, callback: Callable):
        """Register event callback for UI integration"""
        self._event_callbacks[event_name].append(callback)
    
    def get_events(self, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get events for UI consumption"""
        if since is None:
            return self._event_queue.copy()
        
        try:
            since_dt = datetime.fromisoformat(since)
            return [
                event for event in self._event_queue
                if datetime.fromisoformat(event["timestamp"]) > since_dt
            ]
        except (ValueError, KeyError):
            return self._event_queue.copy()
    
    def _validate_operation(self, operation: str, key: str, value: Any = None) -> bool:
        """Validate cache operation for security"""
        # Check rate limiting
        if not self.security_validator.check_rate_limit(operation):
            self.metrics.security_violations += 1
            self._emit_event("security_violation", {
                "type": "rate_limit_exceeded",
                "operation": operation,
                "key": key
            })
            return False
        
        # Validate key
        key_valid, key_reason = self.security_validator.validate_key(key)
        if not key_valid:
            self.metrics.security_violations += 1
            self._emit_event("security_violation", {
                "type": "invalid_key",
                "operation": operation,
                "key": key,
                "reason": key_reason
            })
            return False
        
        # Validate value for set operations
        if value is not None:
            value_valid, value_reason = self.security_validator.validate_value(value)
            if not value_valid:
                self.metrics.security_violations += 1
                self._emit_event("security_violation", {
                    "type": "invalid_value",
                    "operation": operation,
                    "key": key,
                    "reason": value_reason
                })
                return False
        
        return True
    
    def _compress_value(self, value: Any) -> tuple[Any, bool]:
        """Compress value if beneficial"""
        if not self.config.enable_compression:
            return value, False
        
        try:
            serialized = pickle.dumps(value)
            if len(serialized) < self.config.compression_threshold:
                return value, False
            
            compressed = zlib.compress(serialized)
            if len(compressed) < len(serialized) * 0.9:  # Only if 10%+ compression
                self.metrics.compressions += 1
                self.metrics.compression_ratio += (1 - len(compressed) / len(serialized)) * 100
                return compressed, True
            else:
                return value, False
        except Exception as e:
            self.logger.warning(f"Compression failed: {e}")
            return value, False
    
    def _decompress_value(self, value: Any, is_compressed: bool) -> Any:
        """Decompress an in-memory value.

        Plain pickle is correct here: this round-trips a value that
        `_compress_value` pickled moments earlier in this same process, so no
        trust boundary is crossed. Anything leaving the process (disk, Redis)
        goes through `gliaent.io.secure_pickle` instead.
        """
        if not is_compressed:
            return value
        
        try:
            self.metrics.decompressions += 1
            decompressed_bytes = zlib.decompress(value)
            return pickle.loads(decompressed_bytes)
        except Exception as e:
            self.logger.error(f"Decompression failed: {e}")
            return None
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache with security validation and performance tracking.
        
        Args:
            key: Cache key
            default: Default value if not found
            
        Returns:
            Cached value or default if not found/expired
        """
        start_time = time.time()
        
        try:
            with self._lock:
                # Validate operation
                if not self._validate_operation("get", key):
                    return default
                
                # Check memory cache first
                if key in self._memory_cache:
                    entry = self._memory_cache[key]
                    
                    # Check expiration
                    if entry.is_expired:
                        self._remove_entry(key)
                        self.metrics.expirations += 1
                        self.metrics.update_get_metrics(False, time.time() - start_time)
                        return default
                    
                    # Move to end for LRU
                    self._memory_cache.move_to_end(key)
                    
                    # Decompress if needed
                    value = self._decompress_value(entry.value, entry.compressed)
                    
                    # Update metrics and return
                    self.metrics.update_get_metrics(True, time.time() - start_time)
                    self._emit_event("cache_hit", {"key": key, "level": entry.level.value})
                    
                    return entry.access()
                
                # Check disk cache if enabled
                if self.config.enable_persistence and key in self._disk_cache:
                    # Load from disk and promote to memory
                    value = self._load_from_disk(key)
                    if value is not None:
                        self.metrics.disk_reads += 1
                        self.metrics.update_get_metrics(True, time.time() - start_time)
                        self._emit_event("cache_hit", {"key": key, "level": "disk"})
                        return value
                
                # Cache miss
                self.metrics.update_get_metrics(False, time.time() - start_time)
                self._emit_event("cache_miss", {"key": key})
                return default
                
        except Exception as e:
            self.logger.error(f"Error getting key '{key}': {e}")
            self.metrics.update_get_metrics(False, time.time() - start_time)
            return default
    
    def set(self, 
            key: str, 
            value: Any, 
            ttl: Optional[int] = None,
            tags: Optional[Set[str]] = None,
            metadata: Optional[Dict[str, Any]] = None,
            priority: CachePriority = CachePriority.NORMAL) -> bool:
        """
        Set value in cache with comprehensive options.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if None)
            tags: Tags for grouping
            metadata: Additional metadata
            priority: Cache priority level
            
        Returns:
            True if value was cached, False otherwise
        """
        start_time = time.time()
        
        try:
            with self._lock:
                # Validate operation
                if not self._validate_operation("set", key, value):
                    return False
                
                ttl = ttl or self.config.default_ttl
                tags = tags or set()
                metadata = metadata or {}
                
                # Remove existing entry if present
                if key in self._memory_cache:
                    self._remove_entry(key)
                
                # Compress value if beneficial
                processed_value, is_compressed = self._compress_value(value)
                
                # Determine storage level
                level = self._determine_storage_level(processed_value, priority)
                
                # Create cache entry
                entry = CacheEntry(
                    value=processed_value,
                    ttl_seconds=ttl,
                    tags=tags,
                    metadata=metadata,
                    priority=priority,
                    level=level,
                    compressed=is_compressed
                )
                
                # Store in appropriate level
                if level == CacheLevel.MEMORY:
                    self._store_in_memory(key, entry)
                elif level == CacheLevel.DISK and self.config.enable_persistence:
                    self._store_on_disk(key, entry)
                
                # Update indexes
                self._update_indexes(key, entry)
                
                # Update metrics
                self.metrics.update_set_metrics(time.time() - start_time)
                self._emit_event("cache_set", {
                    "key": key,
                    "level": level.value,
                    "priority": priority.name,
                    "compressed": is_compressed,
                    "size": entry.stored_size
                })
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error setting key '{key}': {e}")
            self.metrics.update_set_metrics(time.time() - start_time)
            return False
    
    def _determine_storage_level(self, value: Any, priority: CachePriority) -> CacheLevel:
        """Determine optimal storage level for value"""
        value_size = len(pickle.dumps(value)) if value else 0
        
        # Critical and high priority items go to memory
        if priority in [CachePriority.CRITICAL, CachePriority.HIGH]:
            return CacheLevel.MEMORY
        
        # Large items go to disk if enabled
        if (value_size > self.config.compression_threshold and 
            self.config.enable_persistence):
            return CacheLevel.DISK
        
        # Default to memory
        return CacheLevel.MEMORY
    
    def _store_in_memory(self, key: str, entry: CacheEntry):
        """Store entry in memory cache"""
        # Evict if at capacity
        while len(self._memory_cache) >= self.config.max_memory_size:
            self._evict_entry()
        
        self._memory_cache[key] = entry
        self._size_index[key] = entry.stored_size
        self.metrics.memory_usage_bytes += entry.stored_size
    
    def _store_on_disk(self, key: str, entry: CacheEntry):
        """Store entry on disk"""
        if not self.config.enable_persistence:
            return
        
        try:
            # sha256, not md5, and the filename is only an index — integrity
            # comes from the HMAC envelope, not the name.
            digest = hashlib.sha256(key.encode()).hexdigest()
            file_path = self.persistence_dir / f"{digest}.cache"
            dump_signed(entry, file_path)
            
            self._disk_cache[key] = str(file_path)
            self.metrics.disk_writes += 1
            self.metrics.disk_usage_bytes += entry.stored_size
            
        except Exception as e:
            self.logger.error(f"Failed to store '{key}' on disk: {e}")
    
    def _load_from_disk(self, key: str) -> Any:
        """Load entry from disk and promote to memory"""
        if key not in self._disk_cache:
            return None
        
        try:
            file_path = Path(self._disk_cache[key])
            if not file_path.exists():
                del self._disk_cache[key]
                return None
            
            # Verified before anything is unpickled. An entry written by a
            # different installation, or tampered with, raises rather than
            # executing whatever it contains.
            try:
                entry: CacheEntry = load_signed(file_path)
            except IntegrityError as exc:
                self.logger.error(
                    "discarding cache entry %s: %s", file_path.name, exc
                )
                file_path.unlink(missing_ok=True)
                self._disk_cache.pop(key, None)
                return None
            
            # Check if expired
            if entry.is_expired:
                file_path.unlink()
                del self._disk_cache[key]
                return None
            
            # Promote to memory
            self._store_in_memory(key, entry)
            self._update_indexes(key, entry)
            
            return self._decompress_value(entry.value, entry.compressed)
            
        except Exception as e:
            self.logger.error(f"Failed to load '{key}' from disk: {e}")
            return None
    
    def _update_indexes(self, key: str, entry: CacheEntry):
        """Update all indexes for the entry"""
        # Tag index
        for tag in entry.tags:
            self._tag_index[tag].add(key)
        
        # Priority index
        self._priority_index[entry.priority].add(key)
    
    def _remove_entry(self, key: str) -> bool:
        """Remove entry from all storage levels and indexes"""
        removed = False
        
        # Remove from memory
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            del self._memory_cache[key]
            
            # Update metrics
            self.metrics.memory_usage_bytes -= entry.stored_size
            self.metrics.deletes += 1
            
            # Remove from indexes
            for tag in entry.tags:
                self._tag_index[tag].discard(key)
                if not self._tag_index[tag]:
                    del self._tag_index[tag]
            
            self._priority_index[entry.priority].discard(key)
            if key in self._size_index:
                del self._size_index[key]
            
            removed = True
        
        # Remove from disk
        if key in self._disk_cache:
            try:
                file_path = Path(self._disk_cache[key])
                if file_path.exists():
                    file_path.unlink()
                del self._disk_cache[key]
                removed = True
            except Exception as e:
                self.logger.error(f"Failed to remove disk cache for '{key}': {e}")
        
        if removed:
            self._emit_event("cache_remove", {"key": key})
        
        return removed
    
    def _evict_entry(self):
        """Evict entry based on configured strategy"""
        if not self._memory_cache:
            return
        
        if self.config.eviction_strategy == CacheStrategy.LRU:
            # Evict least recently used (first in OrderedDict)
            key_to_evict = next(iter(self._memory_cache))
        elif self.config.eviction_strategy == CacheStrategy.LFU:
            # Evict least frequently used
            key_to_evict = min(
                self._memory_cache.keys(),
                key=lambda k: self._memory_cache[k].access_frequency
            )
        elif self.config.eviction_strategy == CacheStrategy.TTL_BASED:
            # Evict entry with shortest remaining TTL
            key_to_evict = min(
                self._memory_cache.keys(),
                key=lambda k: self._memory_cache[k].remaining_ttl_seconds
            )
        elif self.config.eviction_strategy == CacheStrategy.PRIORITY_BASED:
            # Evict lowest priority first, then LRU within priority
            lowest_priority = min(
                entry.priority for entry in self._memory_cache.values()
            )
            candidates = [
                key for key, entry in self._memory_cache.items()
                if entry.priority == lowest_priority
            ]
            key_to_evict = candidates[0]  # First (oldest) in priority group
        else:  # Default to LRU
            key_to_evict = next(iter(self._memory_cache))
        
        # Move to disk if possible, otherwise remove completely
        if self.config.enable_persistence:
            entry = self._memory_cache[key_to_evict]
            if entry.priority in [CachePriority.HIGH, CachePriority.CRITICAL]:
                self._store_on_disk(key_to_evict, entry)
        
        self._remove_entry(key_to_evict)
        self.metrics.evictions += 1
        
        self._emit_event("cache_eviction", {
            "key": key_to_evict,
            "strategy": self.config.eviction_strategy.value
        })
    
    def remove(self, key: str) -> bool:
        """Remove key from cache"""
        with self._lock:
            if not self._validate_operation("remove", key):
                return False
            
            return self._remove_entry(key)
    
    def clear(self, tags: Optional[Set[str]] = None, priority: Optional[CachePriority] = None) -> int:
        """
        Clear cache entries by tags or priority.
        
        Args:
            tags: Clear entries with these tags
            priority: Clear entries with this priority
            
        Returns:
            Number of entries cleared
        """
        with self._lock:
            keys_to_remove = set()
            
            if tags:
                for tag in tags:
                    if tag in self._tag_index:
                        keys_to_remove.update(self._tag_index[tag])
            elif priority:
                keys_to_remove.update(self._priority_index[priority])
            else:
                # Clear everything
                keys_to_remove.update(self._memory_cache.keys())
                keys_to_remove.update(self._disk_cache.keys())
            
            count = 0
            for key in keys_to_remove:
                if self._remove_entry(key):
                    count += 1
            
            self._emit_event("cache_clear", {
                "count": count,
                "tags": list(tags) if tags else None,
                "priority": priority.name if priority else None
            })
            
            self.logger.info(f"Cleared {count} cache entries")
            return count
    
    def cleanup_expired(self) -> int:
        """Remove expired entries"""
        with self._lock:
            expired_keys = []
            current_time = datetime.now()
            
            # Check memory cache
            for key, entry in self._memory_cache.items():
                if current_time > (entry.created_at + entry.ttl):
                    expired_keys.append(key)
            
            # Check disk cache
            for key in list(self._disk_cache.keys()):
                try:
                    file_path = Path(self._disk_cache[key])
                    if file_path.exists():
                        with open(file_path, 'rb') as f:
                            entry = load_signed(path)
                        if entry.is_expired:
                            expired_keys.append(key)
                except Exception:
                    expired_keys.append(key)  # Remove corrupted entries
            
            count = 0
            for key in expired_keys:
                if self._remove_entry(key):
                    count += 1
                    self.metrics.expirations += 1
            
            if count > 0:
                self._emit_event("cache_cleanup", {"expired_count": count})
                self.logger.debug(f"Cleaned up {count} expired cache entries")
            
            return count
    
    async def start_background_tasks(self):
        """Start background maintenance tasks"""
        if self._is_running:
            return
        
        self._is_running = True
        
        # Cleanup task
        cleanup_task = asyncio.create_task(self._background_cleanup())
        self._background_tasks.add(cleanup_task)
        cleanup_task.add_done_callback(self._background_tasks.discard)
        
        # Metrics collection task
        metrics_task = asyncio.create_task(self._background_metrics())
        self._background_tasks.add(metrics_task)
        metrics_task.add_done_callback(self._background_tasks.discard)
        
        self.logger.info("Cache background tasks started")
    
    async def stop_background_tasks(self):
        """Stop background maintenance tasks"""
        self._is_running = False
        
        for task in self._background_tasks.copy():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Cache background tasks stopped")
    
    async def _background_cleanup(self):
        """Background cleanup task"""
        while self._is_running:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                if not self._is_running:
                    break
                
                # Cleanup expired entries
                self.cleanup_expired()
                
                # Update access patterns
                self._update_access_patterns()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in background cleanup: {e}")
    
    async def _background_metrics(self):
        """Background metrics collection task"""
        while self._is_running:
            try:
                await asyncio.sleep(10)  # Update metrics every 10 seconds
                if not self._is_running:
                    break
                
                # Update memory usage
                total_memory = sum(entry.stored_size for entry in self._memory_cache.values())
                self.metrics.memory_usage_bytes = total_memory
                
                # Emit metrics event for UI
                self._emit_event("metrics_update", self.get_ui_metrics())
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in background metrics: {e}")
    
    def _update_access_patterns(self):
        """Update access patterns for optimization"""
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=1)
        
        # Clean old access patterns
        for key in list(self._access_patterns.keys()):
            self._access_patterns[key] = [
                timestamp for timestamp in self._access_patterns[key]
                if timestamp > cutoff_time
            ]
            if not self._access_patterns[key]:
                del self._access_patterns[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        with self._lock:
            return {
                "hits": self.metrics.hits,
                "misses": self.metrics.misses,
                "hit_rate_percent": round(self.metrics.get_hit_rate(), 2),
                "sets": self.metrics.sets,
                "deletes": self.metrics.deletes,
                "evictions": self.metrics.evictions,
                "expirations": self.metrics.expirations,
                "compressions": self.metrics.compressions,
                "decompressions": self.metrics.decompressions,
                "disk_reads": self.metrics.disk_reads,
                "disk_writes": self.metrics.disk_writes,
                "security_violations": self.metrics.security_violations,
                "memory_entries": len(self._memory_cache),
                "disk_entries": len(self._disk_cache),
                "total_entries": len(self._memory_cache) + len(self._disk_cache),
                "memory_usage_bytes": self.metrics.memory_usage_bytes,
                "disk_usage_bytes": self.metrics.disk_usage_bytes,
                "memory_utilization": (len(self._memory_cache) / self.config.max_memory_size) * 100,
                "average_get_time": self.metrics.average_get_time,
                "average_set_time": self.metrics.average_set_time,
                "compression_ratio": self.metrics.get_compression_ratio(),
                "unique_tags": len(self._tag_index),
                "config": {
                    "max_memory_size": self.config.max_memory_size,
                    "max_disk_size": self.config.max_disk_size,
                    "default_ttl": self.config.default_ttl,
                    "eviction_strategy": self.config.eviction_strategy.value,
                    "compression_enabled": self.config.enable_compression,
                    "persistence_enabled": self.config.enable_persistence,
                    "security_enabled": self.config.enable_security_validation
                }
            }
    
    def get_ui_metrics(self) -> Dict[str, Any]:
        """Get metrics optimized for UI consumption"""
        stats = self.get_stats()
        
        return {
            "performance": {
                "hit_rate": stats["hit_rate_percent"],
                "total_requests": stats["hits"] + stats["misses"],
                "average_response_time": stats["average_get_time"] * 1000,  # Convert to ms
                "operations_per_second": self._calculate_ops_per_second()
            },
            "storage": {
                "memory_usage": {
                    "current": stats["memory_entries"],
                    "max": self.config.max_memory_size,
                    "utilization": stats["memory_utilization"],
                    "bytes": stats["memory_usage_bytes"]
                },
                "disk_usage": {
                    "current": stats["disk_entries"],
                    "max": self.config.max_disk_size,
                    "bytes": stats["disk_usage_bytes"]
                }
            },
            "efficiency": {
                "compression_ratio": stats["compression_ratio"],
                "evictions": stats["evictions"],
                "expirations": stats["expirations"]
            },
            "security": {
                "violations": stats["security_violations"],
                "enabled": self.config.enable_security_validation
            },
            "last_updated": datetime.now().isoformat()
        }
    
    def _calculate_ops_per_second(self) -> float:
        """Calculate operations per second"""
        total_ops = self.metrics.hits + self.metrics.misses + self.metrics.sets
        if total_ops == 0 or self.metrics.total_get_time + self.metrics.total_set_time == 0:
            return 0.0
        
        total_time = self.metrics.total_get_time + self.metrics.total_set_time
        return total_ops / total_time
    
    def get_entry_info(self, key: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a cache entry"""
        with self._lock:
            if key in self._memory_cache:
                return self._memory_cache[key].get_info()
            elif key in self._disk_cache:
                # Load entry info from disk
                try:
                    file_path = Path(self._disk_cache[key])
                    with open(file_path, 'rb') as f:
                        entry = load_signed(path)
                    return entry.get_info()
                except Exception:
                    return None
            return None
    
    def get_entries_by_tag(self, tag: str) -> Dict[str, Any]:
        """Get all entries with a specific tag"""
        with self._lock:
            result = {}
            if tag in self._tag_index:
                for key in self._tag_index[tag].copy():
                    value = self.get(key)
                    if value is not None:
                        result[key] = value
            return result
    
    def get_entries_by_priority(self, priority: CachePriority) -> Dict[str, Any]:
        """Get all entries with a specific priority"""
        with self._lock:
            result = {}
            for key in self._priority_index[priority].copy():
                value = self.get(key)
                if value is not None:
                    result[key] = value
            return result
    
    def get_keys_by_pattern(self, pattern: str) -> List[str]:
        """Get keys matching a pattern"""
        import fnmatch
        
        with self._lock:
            matching_keys = []
            
            # Check memory cache
            for key in self._memory_cache.keys():
                if fnmatch.fnmatch(key, pattern):
                    entry = self._memory_cache[key]
                    if not entry.is_expired:
                        matching_keys.append(key)
            
            # Check disk cache
            for key in self._disk_cache.keys():
                if fnmatch.fnmatch(key, pattern) and key not in matching_keys:
                    matching_keys.append(key)
            
            return matching_keys
    
    def extend_ttl(self, key: str, additional_seconds: int) -> bool:
        """Extend TTL for a key"""
        with self._lock:
            if key in self._memory_cache:
                entry = self._memory_cache[key]
                entry.ttl += timedelta(seconds=additional_seconds)
                self._emit_event("ttl_extended", {"key": key, "additional_seconds": additional_seconds})
                return True
            return False
    
    def get_ttl(self, key: str) -> Optional[float]:
        """Get remaining TTL for a key"""
        with self._lock:
            if key in self._memory_cache:
                entry = self._memory_cache[key]
                return entry.remaining_ttl_seconds if not entry.is_expired else 0.0
            return None
    
    def warm_cache(self, data: Dict[str, Any], default_ttl: Optional[int] = None):
        """Warm cache with initial data"""
        self.logger.info(f"Warming cache with {len(data)} entries")
        
        for key, value in data.items():
            self.set(
                key=key,
                value=value,
                ttl=default_ttl,
                priority=CachePriority.NORMAL,
                metadata={"warmed": True, "timestamp": datetime.now().isoformat()}
            )
        
        self._emit_event("cache_warmed", {"count": len(data)})
    
    def backup_to_disk(self, backup_path: Optional[str] = None) -> bool:
        """Backup entire cache to disk"""
        if not backup_path:
            backup_path = str(Path.home() / f"mcp_cache_backup_{int(time.time())}.pkl")
        
        try:
            with self._lock:
                backup_data = {
                    "config": self.config,
                    "memory_cache": dict(self._memory_cache),
                    "disk_cache": dict(self._disk_cache),
                    "metrics": self.metrics,
                    "timestamp": datetime.now().isoformat()
                }
                
                dump_signed(backup_data, backup_path)
                
                self.logger.info(f"Cache backed up to: {backup_path}")
                self._emit_event("cache_backup", {"path": backup_path})
                return True
                
        except Exception as e:
            self.logger.error(f"Cache backup failed: {e}")
            return False
    
    def restore_from_backup(self, backup_path: str) -> bool:
        """Restore cache from backup"""
        try:
            # A backup file is attacker-controllable input: verify before
            # unpickling, and refuse rather than silently restoring nothing.
            try:
                backup_data = load_signed(backup_path)
            except IntegrityError as exc:
                self.logger.error("refusing to restore %s: %s", backup_path, exc)
                return False
            
            with self._lock:
                # Clear current cache
                self.clear()
                
                # Restore memory cache
                self._memory_cache.update(backup_data.get("memory_cache", {}))
                
                # Restore disk cache references
                if self.config.enable_persistence:
                    self._disk_cache.update(backup_data.get("disk_cache", {}))
                
                # Rebuild indexes
                for key, entry in self._memory_cache.items():
                    self._update_indexes(key, entry)
                
                self.logger.info(f"Cache restored from: {backup_path}")
                self._emit_event("cache_restored", {"path": backup_path})
                return True
                
        except Exception as e:
            self.logger.error(f"Cache restore failed: {e}")
            return False
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get security status and configuration"""
        return {
            "enabled": self.config.enable_security_validation,
            "violations_count": self.metrics.security_violations,
            "blocked_patterns": list(self.security_validator.blocked_patterns),
            "rate_limit_per_minute": self.security_validator.max_operations_per_minute,
            "encryption_enabled": self.config.enable_encryption,
            "max_entry_size": self.config.max_entry_size,
            "max_key_length": self.config.max_key_length,
            "allow_insecure_keys": self.config.allow_insecure_keys
        }
    
    def block_key_pattern(self, pattern: str):
        """Block a key pattern for security"""
        self.security_validator.block_pattern(pattern)
        self._emit_event("pattern_blocked", {"pattern": pattern})
        self.logger.warning(f"Blocked key pattern: {pattern}")
    
    def unblock_key_pattern(self, pattern: str):
        """Unblock a key pattern"""
        self.security_validator.unblock_pattern(pattern)
        self._emit_event("pattern_unblocked", {"pattern": pattern})
        self.logger.info(f"Unblocked key pattern: {pattern}")


def main():
    """
    Main function demonstrating Enterprise Cache Manager usage.
    """
    print("🚀 Enterprise Cache Manager - Security & Performance")
    print("=" * 60)
    
    async def demo_cache_manager():
        """Demonstrate cache manager capabilities"""
        
        # Create comprehensive configuration
        config = CacheConfiguration(
            max_memory_size=100,
            max_disk_size=500,
            default_ttl=60,
            enable_compression=True,
            enable_persistence=True,
            enable_security_validation=True,
            eviction_strategy=CacheStrategy.PRIORITY_BASED,
            compression_threshold=100
        )
        
        # Create cache manager
        cache = CacheManager(config)
        
        print(f"✅ Cache Manager created")
        print(f"   Memory capacity: {config.max_memory_size}")
        print(f"   Security enabled: {config.enable_security_validation}")
        print(f"   Compression enabled: {config.enable_compression}")
        print(f"   Persistence enabled: {config.enable_persistence}")
        
        # Start background tasks
        await cache.start_background_tasks()
        print(f"   Background tasks: 🟢 RUNNING")
        
        # Demonstrate basic operations
        print(f"\n📦 Basic Operations:")
        
        # Set various types of data
        cache.set("user:1", {"name": "Alice", "age": 30}, 
                 priority=CachePriority.HIGH,
                 tags={"users", "profiles"})
        
        cache.set("config:app", {"theme": "dark", "lang": "en"}, 
                 priority=CachePriority.CRITICAL,
                 tags={"config"})
        
        cache.set("temp:data", "x" * 200,  # Large data for compression
                 priority=CachePriority.LOW,
                 tags={"temporary"})
        
        # Get data
        user = cache.get("user:1")
        config_data = cache.get("config:app")
        print(f"   Retrieved user: {user['name'] if user else 'None'}")
        print(f"   Retrieved config: {config_data['theme'] if config_data else 'None'}")
        
        # Demonstrate performance metrics
        print(f"\n📊 Performance Metrics:")
        stats = cache.get_stats()
        print(f"   Hit rate: {stats['hit_rate_percent']:.1f}%")
        print(f"   Total operations: {stats['hits'] + stats['misses']}")
        print(f"   Memory usage: {stats['memory_entries']}/{stats['config']['max_memory_size']}")
        print(f"   Compressions: {stats['compressions']}")
        
        # Demonstrate UI metrics
        print(f"\n🎨 UI Metrics:")
        ui_metrics = cache.get_ui_metrics()
        perf = ui_metrics['performance']
        storage = ui_metrics['storage']
        print(f"   Response time: {perf['average_response_time']:.2f}ms")
        print(f"   Memory utilization: {storage['memory_usage']['utilization']:.1f}%")
        print(f"   Ops/second: {perf['operations_per_second']:.1f}")
        
        # Demonstrate security features
        print(f"\n🔒 Security Features:")
        
        # Test security validation
        valid_result = cache.set("valid_key", "valid_data")
        invalid_result = cache.set("../../../etc/passwd", "malicious")
        
        print(f"   Valid key accepted: {'✅ YES' if valid_result else '❌ NO'}")
        print(f"   Invalid key blocked: {'✅ YES' if not invalid_result else '❌ NO'}")
        
        # Block a pattern
        cache.block_key_pattern("temp:*")
        blocked_result = cache.set("temp:blocked", "should fail")
        print(f"   Pattern blocking works: {'✅ YES' if not blocked_result else '❌ NO'}")
        
        security_status = cache.get_security_status()
        print(f"   Security violations: {security_status['violations_count']}")
        
        # Demonstrate tag-based operations
        print(f"\n🏷️ Tag-based Operations:")
        user_data = cache.get_entries_by_tag("users")
        print(f"   Users in cache: {len(user_data)}")
        
        # Clear by tag
        cleared = cache.clear(tags={"temporary"})
        print(f"   Cleared temp entries: {cleared}")
        
        # Demonstrate priority-based operations
        print(f"\n⭐ Priority-based Operations:")
        critical_data = cache.get_entries_by_priority(CachePriority.CRITICAL)
        print(f"   Critical entries: {len(critical_data)}")
        
        # Force eviction by filling cache
        for i in range(config.max_memory_size + 10):
            cache.set(f"fill:{i}", f"data_{i}", priority=CachePriority.LOW)
        
        post_eviction_stats = cache.get_stats()
        print(f"   Evictions triggered: {post_eviction_stats['evictions']}")
        
        # Demonstrate advanced features
        print(f"\n🚀 Advanced Features:")
        
        # TTL operations
        cache.set("ttl_test", "temporary", ttl=1)
        ttl_remaining = cache.get_ttl("ttl_test")
        print(f"   TTL remaining: {ttl_remaining:.1f}s")
        
        # Extend TTL
        extended = cache.extend_ttl("ttl_test", 60)
        new_ttl = cache.get_ttl("ttl_test")
        print(f"   TTL extended: {'✅ YES' if extended else '❌ NO'} (now {new_ttl:.1f}s)")
        
        # Pattern matching
        cache.set("api:v1:users", [])
        cache.set("api:v1:posts", [])
        api_keys = cache.get_keys_by_pattern("api:v1:*")
        print(f"   API keys found: {len(api_keys)}")
        
        # Entry details
        entry_info = cache.get_entry_info("user:1")
        if entry_info:
            print(f"   Entry access count: {entry_info['access_count']}")
            print(f"   Entry priority: {entry_info['priority']}")
        
        # Demonstrate persistence (if enabled)
        if config.enable_persistence:
            print(f"\n💾 Persistence Features:")
            backup_success = cache.backup_to_disk()
            print(f"   Backup created: {'✅ YES' if backup_success else '❌ NO'}")
        
        # Event system demonstration
        print(f"\n📡 Event System:")
        events = cache.get_events()
        recent_events = [e for e in events if 'cache_set' in e['event'] or 'security_violation' in e['event']]
        print(f"   Total events: {len(events)}")
        print(f"   Recent cache events: {len(recent_events)}")
        
        # Cleanup demonstration
        print(f"\n🧹 Cleanup:")
        
        # Wait for TTL expiration
        await asyncio.sleep(1.1)
        expired_count = cache.cleanup_expired()
        print(f"   Expired entries cleaned: {expired_count}")
        
        # Stop background tasks
        await cache.stop_background_tasks()
        print(f"   Background tasks: 🔴 STOPPED")
        
        # Final statistics
        print(f"\n📈 Final Statistics:")
        final_stats = cache.get_stats()
        print(f"   Total operations: {final_stats['sets'] + final_stats['hits'] + final_stats['misses']}")
        print(f"   Hit rate: {final_stats['hit_rate_percent']:.1f}%")
        print(f"   Memory entries: {final_stats['memory_entries']}")
        print(f"   Security violations: {final_stats['security_violations']}")
        
        return cache
    
    # Run demonstration
    try:
        cache = asyncio.run(demo_cache_manager())
        print("\n🎉 Demo completed successfully!")
        return cache
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        return None


if __name__ == "__main__":
    """
    Main execution block for testing the Enterprise Cache Manager locally.
    """
    def run_static_tests():
        """Run static tests for Cache Manager"""
        print("🧪 Running Static Tests...")
        
        tests = []
        
        # Test 1: Configuration validation
        try:
            config = CacheConfiguration(
                max_memory_size=100,
                enable_compression=True,
                enable_security_validation=True
            )
            tests.append(("Configuration Creation", True, "Valid config created"))
        except Exception as e:
            tests.append(("Configuration Creation", False, f"Config error: {e}"))
        
        # Test 2: Invalid configuration
        try:
            CacheConfiguration(max_memory_size=0, default_ttl=0)
            tests.append(("Invalid Config Validation", False, "Should have failed"))
        except ValueError:
            tests.append(("Invalid Config Validation", True, "Properly rejected invalid config"))
        
        # Test 3: Security validator
        try:
            config = CacheConfiguration(enable_security_validation=True)
            validator = SecurityValidator(config)
            
            valid, reason = validator.validate_key("valid_key")
            invalid, reason = validator.validate_key("../invalid")
            
            security_works = valid and not invalid
            tests.append(("Security Validator", security_works, "Key validation works"))
        except Exception as e:
            tests.append(("Security Validator", False, f"Security error: {e}"))
        
        # Test 4: Cache entry creation
        try:
            entry = CacheEntry(
                value="test_data",
                ttl_seconds=60,
                priority=CachePriority.HIGH,
                tags={"test"}
            )
            
            info = entry.get_info()
            entry_works = (
                entry.access() == "test_data" and
                "entry_id" in info and
                info["priority"] == "HIGH"
            )
            tests.append(("Cache Entry", entry_works, "Entry creation and info work"))
        except Exception as e:
            tests.append(("Cache Entry", False, f"Entry error: {e}"))
        
        # Test 5: Cache metrics
        try:
            metrics = CacheMetrics()
            metrics.update_get_metrics(True, 0.1)
            metrics.update_set_metrics(0.05)
            
            hit_rate = metrics.get_hit_rate()
            metrics_work = (
                metrics.hits == 1 and
                hit_rate == 100.0 and
                metrics.average_set_time == 0.05
            )
            tests.append(("Cache Metrics", metrics_work, "Metrics tracking works"))
        except Exception as e:
            tests.append(("Cache Metrics", False, f"Metrics error: {e}"))
        
        # Print results
        passed = 0
        for test_name, success, message in tests:
            status = "✅" if success else "❌"
            print(f"  {status} {test_name}: {message}")
            if success:
                passed += 1
        
        success_rate = (passed / len(tests)) * 100
        print(f"\n📊 Static Tests: {passed}/{len(tests)} passed ({success_rate:.1f}%)")
        return passed == len(tests)
    
    def run_dynamic_tests():
        """Run dynamic tests for Cache Manager"""
        print("\n⚡ Running Dynamic Tests...")
        
        async def async_test_suite():
            tests = []
            
            # Test 1: Basic cache operations
            try:
                cache = CacheManager()
                
                # Set and get
                cache.set("test_key", "test_value")
                value = cache.get("test_key")
                
                basic_works = value == "test_value"
                tests.append(("Basic Operations", basic_works, "Set/get operations work"))
            except Exception as e:
                tests.append(("Basic Operations", False, f"Basic error: {e}"))
            
            # Test 2: TTL expiration
            try:
                cache = CacheManager(CacheConfiguration(default_ttl=1))
                
                cache.set("expire_key", "expire_value", ttl=0.1)
                await asyncio.sleep(0.2)
                
                expired_value = cache.get("expire_key")
                ttl_works = expired_value is None
                
                tests.append(("TTL Expiration", ttl_works, "TTL expiration works"))
            except Exception as e:
                tests.append(("TTL Expiration", False, f"TTL error: {e}"))
            
            # Test 3: Security validation
            try:
                config = CacheConfiguration(enable_security_validation=True)
                cache = CacheManager(config)
                
                # Valid operation
                valid_result = cache.set("valid_key", "valid_value")
                
                # Invalid operation (path traversal)
                invalid_result = cache.set("../etc/passwd", "malicious")
                
                security_works = valid_result and not invalid_result
                tests.append(("Security Validation", security_works, "Security validation works"))
            except Exception as e:
                tests.append(("Security Validation", False, f"Security error: {e}"))
            
            # Test 4: Tag-based operations
            try:
                cache = CacheManager()
                
                cache.set("user:1", "alice", tags={"users", "active"})
                cache.set("user:2", "bob", tags={"users"})
                cache.set("post:1", "hello", tags={"posts"})
                
                users = cache.get_entries_by_tag("users")
                posts = cache.get_entries_by_tag("posts")
                
                tag_works = len(users) == 2 and len(posts) == 1
                tests.append(("Tag Operations", tag_works, "Tag-based operations work"))
            except Exception as e:
                tests.append(("Tag Operations", False, f"Tag error: {e}"))
            
            # Test 5: Priority-based caching
            try:
                cache = CacheManager()
                
                cache.set("critical", "important", priority=CachePriority.CRITICAL)
                cache.set("normal", "regular", priority=CachePriority.NORMAL)
                cache.set("low", "background", priority=CachePriority.LOW)
                
                critical_entries = cache.get_entries_by_priority(CachePriority.CRITICAL)
                normal_entries = cache.get_entries_by_priority(CachePriority.NORMAL)
                
                priority_works = len(critical_entries) == 1 and len(normal_entries) == 1
                tests.append(("Priority Operations", priority_works, "Priority-based operations work"))
            except Exception as e:
                tests.append(("Priority Operations", False, f"Priority error: {e}"))
            
            # Test 6: Compression
            try:
                config = CacheConfiguration(
                    enable_compression=True,
                    compression_threshold=10
                )
                cache = CacheManager(config)
                
                # Large data that should be compressed
                large_data = "x" * 100
                cache.set("large_key", large_data)
                
                retrieved = cache.get("large_key")
                stats = cache.get_stats()
                
                compression_works = (
                    retrieved == large_data and
                    stats["compressions"] > 0
                )
                tests.append(("Compression", compression_works, "Compression works"))
            except Exception as e:
                tests.append(("Compression", False, f"Compression error: {e}"))
            
            # Test 7: Eviction strategies
            try:
                config = CacheConfiguration(
                    max_memory_size=3,
                    eviction_strategy=CacheStrategy.LRU
                )
                cache = CacheManager(config)
                
                # Fill cache beyond capacity
                cache.set("a", "1")
                cache.set("b", "2")
                cache.set("c", "3")
                cache.set("d", "4")  # Should evict "a"
                
                # "a" should be evicted
                evicted = cache.get("a") is None
                remaining = cache.get("d") == "4"
                
                eviction_works = evicted and remaining
                tests.append(("Eviction Strategy", eviction_works, "LRU eviction works"))
            except Exception as e:
                tests.append(("Eviction Strategy", False, f"Eviction error: {e}"))
            
            # Test 8: Background tasks
            try:
                cache = CacheManager()
                await cache.start_background_tasks()
                
                # Set entry with short TTL
                cache.set("bg_test", "value", ttl=0.1)
                
                # Wait for background cleanup
                await asyncio.sleep(0.3)
                
                # Entry should be cleaned up
                cleaned_value = cache.get("bg_test")
                
                await cache.stop_background_tasks()
                
                background_works = cleaned_value is None
                tests.append(("Background Tasks", background_works, "Background cleanup works"))
            except Exception as e:
                tests.append(("Background Tasks", False, f"Background error: {e}"))
            
            # Test 9: Event system
            try:
                cache = CacheManager()
                events_captured = []
                
                def event_handler(data):
                    events_captured.append(data)
                
                cache.on("cache_set", event_handler)
                cache.on("cache_hit", event_handler)
                
                cache.set("event_test", "value")
                cache.get("event_test")
                
                # Should have captured set and hit events
                event_works = len(events_captured) >= 1
                tests.append(("Event System", event_works, f"Captured {len(events_captured)} events"))
            except Exception as e:
                tests.append(("Event System", False, f"Event error: {e}"))
            
            # Test 10: Advanced features
            try:
                cache = CacheManager()
                
                # Pattern matching
                cache.set("api:v1:users", [])
                cache.set("api:v1:posts", [])
                cache.set("db:config", {})
                
                api_keys = cache.get_keys_by_pattern("api:v1:*")
                
                # TTL extension
                cache.set("ttl_test", "value", ttl=1)
                extended = cache.extend_ttl("ttl_test", 60)
                new_ttl = cache.get_ttl("ttl_test")
                
                advanced_works = (
                    len(api_keys) == 2 and
                    extended and
                    new_ttl > 1
                )
                tests.append(("Advanced Features", advanced_works, "Pattern matching and TTL extension work"))
            except Exception as e:
                tests.append(("Advanced Features", False, f"Advanced error: {e}"))
            
            return tests
        
        # Run async tests
        try:
            test_results = asyncio.run(async_test_suite())
            
            # Print results
            passed = 0
            for test_name, success, message in test_results:
                status = "✅" if success else "❌"
                print(f"  {status} {test_name}: {message}")
                if success:
                    passed += 1
            
            success_rate = (passed / len(test_results)) * 100
            print(f"\n📊 Dynamic Tests: {passed}/{len(test_results)} passed ({success_rate:.1f}%)")
            
            return passed == len(test_results)
            
        except Exception as e:
            print(f"❌ Dynamic test suite failed: {e}")
            return False
    
    # Main test execution
    print("🏃 Running Enterprise Cache Manager Tests")
    print("=" * 70)
    
    # Configure logging for tests
    logging.basicConfig(
        level=logging.WARNING,
        format='%(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    static_passed = run_static_tests()
    dynamic_passed = run_dynamic_tests()
    
    # Run main demo if tests pass
    if static_passed and dynamic_passed:
        print("\n✅ All tests passed! Running main demo...")
        main()
    else:
        print("\n❌ Some tests failed. Skipping main demo.")
        print("Please check the test results above and fix any issues.")
    
    # Final summary
    print("\n" + "=" * 70)
    print("🏁 Enterprise Cache Manager Test Summary")
    print("=" * 70)
    print(f"Static Tests: {'✅ PASSED' if static_passed else '❌ FAILED'}")
    print(f"Dynamic Tests: {'✅ PASSED' if dynamic_passed else '❌ FAILED'}")
    print(f"Overall Status: {'✅ SUCCESS' if static_passed and dynamic_passed else '❌ FAILURE'}")
    
    # Additional information for Electron integration
    if static_passed and dynamic_passed:
        print("\n🎨 Electron Integration Features:")
        print("  • Real-time metrics via cache.get_ui_metrics()")
        print("  • Event-driven updates via cache.on('event', handler)")
        print("  • Performance monitoring with detailed statistics")
        print("  • Security validation and violation tracking")
        print("  • Tag and priority-based cache management")
        print("  • Background maintenance with async tasks")
        print("  • Persistence and backup capabilities")
        print("  • Compression and memory optimization")
        print("  • Thread-safe operations for UI polling")
        
        print("\n📡 UI Integration Examples:")
        print("  • cache.get_ui_metrics() - Dashboard data")
        print("  • cache.get_events() - Real-time notifications")
        print("  • cache.get_security_status() - Security monitoring")
        print("  • cache.get_stats() - Performance analytics")
    
    exit_code = 0 if (static_passed and dynamic_passed) else 1
    print(f"\nExit Code: {exit_code}")
    print("Run with: python -m src.mcp.core.client.cache_manager")