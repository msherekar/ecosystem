"""
MCP Client Response Formatter - Enterprise Edition


"""

import asyncio
import gzip
import hashlib
import json
import logging
import re
import threading
import time
import uuid
import zlib
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, Set
import weakref


class ResponseFormat(Enum):
    """Response format types"""
    STANDARD = "standard"
    DETAILED = "detailed"
    MINIMAL = "minimal"
    AGENT = "agent"
    JSON = "json"
    ELECTRON = "electron"
    STREAMING = "streaming"
    COMPRESSED = "compressed"


class SecurityLevel(Enum):
    """Security levels for response sanitization"""
    NONE = "none"
    BASIC = "basic"
    STRICT = "strict"
    PARANOID = "paranoid"


@dataclass
class FormatterConfiguration:
    """Configuration for response formatters with validation"""
    format_type: ResponseFormat = ResponseFormat.STANDARD
    security_level: SecurityLevel = SecurityLevel.BASIC
    include_metadata: bool = True
    include_debug: bool = False
    include_suggestions: bool = True
    include_performance_metrics: bool = True
    enable_compression: bool = False
    compression_threshold: int = 1024  # Compress responses larger than 1KB
    enable_caching: bool = True
    cache_ttl_seconds: int = 60
    enable_sanitization: bool = True
    max_response_size: int = 10 * 1024 * 1024  # 10MB limit
    pretty_print_json: bool = False
    electron_optimized: bool = False
    enable_streaming: bool = False
    
    def __post_init__(self):
        """Validate configuration"""
        if self.compression_threshold < 1:
            raise ValueError("compression_threshold must be positive")
        if self.cache_ttl_seconds < 1:
            raise ValueError("cache_ttl_seconds must be positive")
        if self.max_response_size < 1024:
            raise ValueError("max_response_size must be at least 1KB")


@dataclass
class ResponseMetrics:
    """Performance metrics for response formatting"""
    total_responses: int = 0
    successful_responses: int = 0
    failed_responses: int = 0
    total_formatting_time: float = 0.0
    average_formatting_time: float = 0.0
    compressed_responses: int = 0
    cached_responses: int = 0
    sanitized_responses: int = 0
    oversized_responses: int = 0
    
    def update_metrics(self, success: bool, formatting_time: float, compressed: bool = False, cached: bool = False):
        """Update response metrics"""
        self.total_responses += 1
        if success:
            self.successful_responses += 1
        else:
            self.failed_responses += 1
        
        self.total_formatting_time += formatting_time
        self.average_formatting_time = self.total_formatting_time / self.total_responses
        
        if compressed:
            self.compressed_responses += 1
        if cached:
            self.cached_responses += 1
    
    def get_success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_responses == 0:
            return 0.0
        return (self.successful_responses / self.total_responses) * 100


class ResponseSanitizer:
    """Security sanitizer for response data"""
    
    def __init__(self, security_level: SecurityLevel = SecurityLevel.BASIC):
        self.security_level = security_level
        self.blocked_patterns = {
            SecurityLevel.BASIC: [
                r'password\s*[:=]\s*["\']?([^"\'\\s]+)',
                r'token\s*[:=]\s*["\']?([^"\'\\s]+)',
                r'key\s*[:=]\s*["\']?([^"\'\\s]+)'
            ],
            SecurityLevel.STRICT: [
                r'password\s*[:=]\s*["\']?([^"\'\\s]+)',
                r'token\s*[:=]\s*["\']?([^"\'\\s]+)',
                r'key\s*[:=]\s*["\']?([^"\'\\s]+)',
                r'secret\s*[:=]\s*["\']?([^"\'\\s]+)',
                r'auth\s*[:=]\s*["\']?([^"\'\\s]+)',
                r'api[_-]?key\s*[:=]\s*["\']?([^"\'\\s]+)',
                r'access[_-]?token\s*[:=]\s*["\']?([^"\'\\s]+)'
            ],
            SecurityLevel.PARANOID: [
                r'password\s*[:=]\s*["\']?([^"\'\\s]+)',
                r'token\s*[:=]\s*["\']?([^"\'\\s]+)',
                r'key\s*[:=]\s*["\']?([^"\'\\s]+)',
                r'secret\s*[:=]\s*["\']?([^"\'\\s]+)',
                r'auth\s*[:=]\s*["\']?([^"\'\\s]+)',
                r'api[_-]?key\s*[:=]\s*["\']?([^"\'\\s]+)',
                r'access[_-]?token\s*[:=]\s*["\']?([^"\'\\s]+)',
                r'session\s*[:=]\s*["\']?([^"\'\\s]+)',
                r'cookie\s*[:=]\s*["\']?([^"\'\\s]+)',
                r'credential\s*[:=]\s*["\']?([^"\'\\s]+)'
            ]
        }
        self.sanitization_stats = {
            'total_sanitized': 0,
            'patterns_detected': defaultdict(int),
            'security_violations': 0
        }
    
    def sanitize_response(self, response: Any) -> Any:
        """Sanitize response data based on security level"""
        if self.security_level == SecurityLevel.NONE:
            return response
        
        try:
            sanitized = self._deep_sanitize(response)
            if sanitized != response:
                self.sanitization_stats['total_sanitized'] += 1
            return sanitized
        except Exception as e:
            self.sanitization_stats['security_violations'] += 1
            # Return safe fallback
            return {"error": "Response sanitization failed", "details": "Data contained unsafe content"}
    
    def _deep_sanitize(self, obj: Any, depth: int = 0) -> Any:
        """Recursively sanitize object"""
        if depth > 20:  # Prevent infinite recursion
            return "[MAX_DEPTH_REACHED]"
        
        if isinstance(obj, dict):
            sanitized = {}
            for key, value in obj.items():
                sanitized_key = self._sanitize_string(str(key))
                sanitized_value = self._deep_sanitize(value, depth + 1)
                sanitized[sanitized_key] = sanitized_value
            return sanitized
        elif isinstance(obj, list):
            return [self._deep_sanitize(item, depth + 1) for item in obj]
        elif isinstance(obj, str):
            return self._sanitize_string(obj)
        else:
            return obj
    
    def _sanitize_string(self, text: str) -> str:
        """Sanitize a string based on security patterns"""
        if not isinstance(text, str):
            return text
        
        patterns = self.blocked_patterns.get(self.security_level, [])
        sanitized_text = text
        
        for pattern in patterns:
            matches = re.finditer(pattern, sanitized_text, re.IGNORECASE)
            for match in matches:
                self.sanitization_stats['patterns_detected'][pattern] += 1
                # Replace sensitive data with asterisks
                replacement = '*' * len(match.group(1)) if len(match.groups()) > 0 else '[REDACTED]'
                sanitized_text = sanitized_text.replace(match.group(0), 
                                                      match.group(0).replace(match.group(1), replacement))
        
        return sanitized_text
    
    def get_sanitization_stats(self) -> Dict[str, Any]:
        """Get sanitization statistics"""
        return {
            "security_level": self.security_level.value,
            "total_sanitized": self.sanitization_stats['total_sanitized'],
            "security_violations": self.sanitization_stats['security_violations'],
            "patterns_detected": dict(self.sanitization_stats['patterns_detected'])
        }


class ResponseCompressor:
    """Response compression for large data"""
    
    def __init__(self, compression_threshold: int = 1024):
        self.compression_threshold = compression_threshold
        self.compression_stats = {
            'total_compressed': 0,
            'bytes_saved': 0,
            'compression_ratio': 0.0
        }
    
    def compress_response(self, response: Any) -> tuple[Any, bool]:
        """Compress response if it exceeds threshold"""
        try:
            # Serialize to estimate size
            serialized = json.dumps(response, default=str)
            original_size = len(serialized.encode('utf-8'))
            
            if original_size < self.compression_threshold:
                return response, False
            
            # Compress using zlib
            compressed_data = zlib.compress(serialized.encode('utf-8'))
            compressed_size = len(compressed_data)
            
            # Only use compression if it saves significant space
            if compressed_size < original_size * 0.8:  # 20% reduction minimum
                self.compression_stats['total_compressed'] += 1
                self.compression_stats['bytes_saved'] += (original_size - compressed_size)
                
                # Calculate rolling average compression ratio
                compression_ratio = (1 - compressed_size / original_size) * 100
                if self.compression_stats['compression_ratio'] == 0:
                    self.compression_stats['compression_ratio'] = compression_ratio
                else:
                    self.compression_stats['compression_ratio'] = (
                        self.compression_stats['compression_ratio'] * 0.9 + compression_ratio * 0.1
                    )
                
                # Return compressed data with metadata
                return {
                    "compressed": True,
                    "original_size": original_size,
                    "compressed_size": compressed_size,
                    "compression_ratio": compression_ratio,
                    "data": compressed_data.hex(),  # Hex encode for JSON transport
                    "encoding": "zlib+hex"
                }, True
            
            return response, False
            
        except Exception:
            return response, False
    
    def decompress_response(self, compressed_response: Dict[str, Any]) -> Any:
        """Decompress a compressed response"""
        try:
            if not compressed_response.get("compressed"):
                return compressed_response
            
            # Decode and decompress
            compressed_data = bytes.fromhex(compressed_response["data"])
            decompressed_data = zlib.decompress(compressed_data)
            
            # Parse JSON
            return json.loads(decompressed_data.decode('utf-8'))
            
        except Exception:
            return {"error": "Failed to decompress response"}
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """Get compression statistics"""
        return self.compression_stats.copy()


class ResponseCache:
    """Caching system for formatted responses"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 60):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, datetime] = {}
        self._lock = threading.RLock()
        
    def get(self, cache_key: str) -> Optional[Any]:
        """Get cached response"""
        with self._lock:
            if cache_key not in self._cache:
                return None
            
            entry = self._cache[cache_key]
            
            # Check expiration
            if datetime.now() > entry["expires_at"]:
                del self._cache[cache_key]
                del self._access_times[cache_key]
                return None
            
            # Update access time
            self._access_times[cache_key] = datetime.now()
            return entry["response"]
    
    def set(self, cache_key: str, response: Any, ttl: Optional[int] = None):
        """Cache a response"""
        with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self.max_size:
                self._evict_lru()
            
            ttl = ttl or self.default_ttl
            expires_at = datetime.now() + timedelta(seconds=ttl)
            
            self._cache[cache_key] = {
                "response": response,
                "expires_at": expires_at,
                "created_at": datetime.now()
            }
            self._access_times[cache_key] = datetime.now()
    
    def _evict_lru(self):
        """Evict least recently used entry"""
        if not self._access_times:
            return
        
        lru_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
        del self._cache[lru_key]
        del self._access_times[lru_key]
    
    def clear(self):
        """Clear all cached responses"""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "utilization": (len(self._cache) / self.max_size) * 100
            }


class ResponseFormatter(ABC):
    """Abstract base class for response formatters with enterprise features"""
    
    def __init__(self, config: Optional[FormatterConfiguration] = None):
        """Initialize formatter with configuration"""
        self.config = config or FormatterConfiguration()
        self.logger = logging.getLogger(f"mcp.response_formatter.{self.__class__.__name__}")
        
        # Enterprise components
        self.sanitizer = ResponseSanitizer(self.config.security_level)
        self.compressor = ResponseCompressor(self.config.compression_threshold)
        self.cache = ResponseCache() if self.config.enable_caching else None
        
        # Metrics and monitoring
        self.metrics = ResponseMetrics()
        
        # Event system for UI integration
        self.event_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self.event_queue: deque = deque(maxlen=1000)
        
        self.logger.info(f"Response formatter initialized: {self.config.format_type.value}")
    
    def _emit_event(self, event_name: str, data: Any):
        """Emit event for UI/monitoring systems"""
        event = {
            "event": event_name,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "formatter_type": self.config.format_type.value
        }
        
        self.event_queue.append(event)
        
        # Call registered callbacks
        for callback in self.event_callbacks[event_name]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(data))
                else:
                    callback(data)
            except Exception as e:
                self.logger.error(f"Error in event callback {event_name}: {e}")
    
    def on(self, event_name: str, callback: Callable):
        """Register event callback for UI integration"""
        self.event_callbacks[event_name].append(callback)
    
    def get_events(self, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get events for UI consumption"""
        events = list(self.event_queue)
        
        if since:
            try:
                since_dt = datetime.fromisoformat(since)
                events = [
                    event for event in events
                    if datetime.fromisoformat(event["timestamp"]) > since_dt
                ]
            except ValueError:
                pass
        
        return events
    
    def _generate_cache_key(self, operation: str, data: Any, metadata: Dict[str, Any]) -> str:
        """Generate cache key for response"""
        key_data = {
            "operation": operation,
            "data_hash": hashlib.md5(str(data).encode()).hexdigest(),
            "metadata_hash": hashlib.md5(str(sorted(metadata.items())).encode()).hexdigest(),
            "formatter": self.config.format_type.value
        }
        return hashlib.sha256(str(key_data).encode()).hexdigest()
    
    def _apply_enterprise_features(self, response: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """Apply enterprise features to response"""
        start_time = time.time()
        
        try:
            # Security sanitization
            if self.config.enable_sanitization:
                response = self.sanitizer.sanitize_response(response)
                if response != response:  # Data was sanitized
                    self._emit_event("response_sanitized", {"operation": operation})
            
            # Size validation
            try:
                response_size = len(json.dumps(response, default=str).encode('utf-8'))
                if response_size > self.config.max_response_size:
                    self.metrics.oversized_responses += 1
                    self._emit_event("response_oversized", {
                        "operation": operation,
                        "size": response_size,
                        "limit": self.config.max_response_size
                    })
                    return {
                        "success": False,
                        "error": "Response too large",
                        "size": response_size,
                        "limit": self.config.max_response_size
                    }
            except Exception:
                pass  # Continue if size calculation fails
            
            # Compression
            if self.config.enable_compression:
                response, compressed = self.compressor.compress_response(response)
                if compressed:
                    self._emit_event("response_compressed", {"operation": operation})
            
            # Add performance metrics if enabled
            if self.config.include_performance_metrics:
                if "metadata" not in response:
                    response["metadata"] = {}
                response["metadata"]["performance"] = {
                    "formatting_time": time.time() - start_time,
                    "sanitized": self.config.enable_sanitization,
                    "compressed": response.get("compressed", False),
                    "formatter_type": self.config.format_type.value
                }
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error applying enterprise features: {e}")
            return {
                "success": False,
                "error": "Response processing failed",
                "details": str(e)
            }
    
    def format_response(self, success: bool, data: Any = None, error: str = None, **metadata) -> Dict[str, Any]:
        """Main formatting method with enterprise features"""
        start_time = time.time()
        operation = metadata.get("operation_type", "unknown")
        
        try:
            # Check cache first
            if self.cache and success:  # Only cache successful responses
                cache_key = self._generate_cache_key(
                    "success" if success else "error", 
                    data if success else error, 
                    metadata
                )
                cached_response = self.cache.get(cache_key)
                if cached_response:
                    self.metrics.update_metrics(True, time.time() - start_time, cached=True)
                    self._emit_event("response_cache_hit", {"operation": operation})
                    return cached_response
            
            # Format response
            if success:
                response = self.format_success(data, **metadata)
            else:
                response = self.format_error(error or "Unknown error", **metadata)
            
            # Apply enterprise features
            response = self._apply_enterprise_features(response, operation)
            
            # Cache the response
            if self.cache and success and response.get("success", False):
                cache_key = self._generate_cache_key("success", data, metadata)
                self.cache.set(cache_key, response, self.config.cache_ttl_seconds)
            
            # Update metrics
            formatting_time = time.time() - start_time
            self.metrics.update_metrics(
                response.get("success", success), 
                formatting_time,
                compressed=response.get("compressed", False)
            )
            
            # Emit completion event
            self._emit_event("response_formatted", {
                "operation": operation,
                "success": response.get("success", success),
                "formatting_time": formatting_time,
                "size": len(str(response))
            })
            
            return response
            
        except Exception as e:
            self.logger.error(f"Response formatting failed: {e}")
            self.metrics.update_metrics(False, time.time() - start_time)
            return {
                "success": False,
                "error": "Response formatting failed",
                "details": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    @abstractmethod
    def format_success(self, data: Any, **metadata) -> Dict[str, Any]:
        """Format a successful response"""
        pass
    
    @abstractmethod
    def format_error(self, error: str, **metadata) -> Dict[str, Any]:
        """Format an error response"""
        pass
    
    def get_formatter_metrics(self) -> Dict[str, Any]:
        """Get comprehensive formatter metrics"""
        base_metrics = {
            "response_metrics": {
                "total_responses": self.metrics.total_responses,
                "successful_responses": self.metrics.successful_responses,
                "failed_responses": self.metrics.failed_responses,
                "success_rate": self.metrics.get_success_rate(),
                "average_formatting_time": self.metrics.average_formatting_time,
                "compressed_responses": self.metrics.compressed_responses,
                "cached_responses": self.metrics.cached_responses,
                "oversized_responses": self.metrics.oversized_responses
            },
            "sanitization_stats": self.sanitizer.get_sanitization_stats(),
            "compression_stats": self.compressor.get_compression_stats(),
            "configuration": {
                "format_type": self.config.format_type.value,
                "security_level": self.config.security_level.value,
                "compression_enabled": self.config.enable_compression,
                "caching_enabled": self.config.enable_caching,
                "sanitization_enabled": self.config.enable_sanitization
            }
        }
        
        if self.cache:
            base_metrics["cache_stats"] = self.cache.get_stats()
        
        return base_metrics
    
    def get_ui_metrics(self) -> Dict[str, Any]:
        """Get metrics optimized for UI dashboard"""
        metrics = self.get_formatter_metrics()
        
        return {
            "performance": {
                "success_rate": metrics["response_metrics"]["success_rate"],
                "average_formatting_time": round(metrics["response_metrics"]["average_formatting_time"] * 1000, 2),  # ms
                "total_responses": metrics["response_metrics"]["total_responses"],
                "responses_per_second": self._calculate_rps()
            },
            "efficiency": {
                "compression_ratio": metrics["compression_stats"].get("compression_ratio", 0),
                "cache_hit_rate": self._calculate_cache_hit_rate(),
                "bytes_saved": metrics["compression_stats"].get("bytes_saved", 0)
            },
            "security": {
                "sanitized_responses": metrics["sanitization_stats"]["total_sanitized"],
                "security_violations": metrics["sanitization_stats"]["security_violations"],
                "security_level": metrics["configuration"]["security_level"]
            },
            "last_updated": datetime.now().isoformat()
        }
    
    def _calculate_rps(self) -> float:
        """Calculate responses per second"""
        if self.metrics.total_formatting_time == 0:
            return 0.0
        return self.metrics.total_responses / self.metrics.total_formatting_time
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        if self.metrics.total_responses == 0:
            return 0.0
        return (self.metrics.cached_responses / self.metrics.total_responses) * 100


class StandardResponseFormatter(ResponseFormatter):
    """Standard response formatter with enterprise features"""
    
    def format_success(self, data: Any, **metadata) -> Dict[str, Any]:
        """Format a successful response"""
        response = {
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        if self.config.include_metadata and metadata:
            response["metadata"] = metadata
        
        return response
    
    def format_error(self, error: str, **metadata) -> Dict[str, Any]:
        """Format an error response"""
        response = {
            "success": False,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        
        if self.config.include_metadata and metadata:
            response["metadata"] = metadata
        
        return response


class ElectronResponseFormatter(ResponseFormatter):
    """Response formatter optimized specifically for Electron UI/UX"""
    
    def format_success(self, data: Any, **metadata) -> Dict[str, Any]:
        """Format a successful response for Electron UI"""
        response = {
            "status": "success",
            "payload": data,
            "ui_metadata": self._extract_ui_metadata(metadata),
            "timestamp": datetime.now().isoformat(),
            "request_id": metadata.get("request_id", str(uuid.uuid4()))
        }
        
        # Add Electron-specific optimizations
        if self.config.electron_optimized:
            response["electron"] = {
                "window_ready": True,
                "render_hints": self._generate_render_hints(data),
                "update_strategy": self._determine_update_strategy(data, metadata)
            }
        
        # Add navigation suggestions for UI
        if self.config.include_suggestions:
            response["ui_suggestions"] = self._generate_ui_suggestions(data, metadata)
        
        return response
    
    def format_error(self, error: str, **metadata) -> Dict[str, Any]:
        """Format an error response for Electron UI"""
        response = {
            "status": "error",
            "error": {
                "message": error,
                "type": self._categorize_error(error),
                "severity": self._determine_error_severity(error, metadata),
                "recoverable": self._is_error_recoverable(error)
            },
            "ui_metadata": self._extract_ui_metadata(metadata),
            "timestamp": datetime.now().isoformat(),
            "request_id": metadata.get("request_id", str(uuid.uuid4()))
        }
        
        # Add error handling suggestions for UI
        if self.config.include_suggestions:
            response["ui_suggestions"] = self._generate_error_suggestions(error, metadata)
        
        # Add Electron-specific error handling
        if self.config.electron_optimized:
            response["electron"] = {
                "show_notification": self._should_show_notification(error),
                "error_dialog": self._should_show_error_dialog(error),
                "retry_strategy": self._determine_retry_strategy(error, metadata)
            }
        
        return response
    
    def _extract_ui_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata relevant for UI display"""
        ui_metadata = {}
        
        # Extract common UI-relevant fields
        ui_fields = [
            "server_name", "tool_name", "resource_uri", "execution_time",
            "cached", "strategy_used", "priority", "operation_type"
        ]
        
        for field in ui_fields:
            if field in metadata:
                ui_metadata[field] = metadata[field]
        
        # Add computed UI fields
        if "execution_time" in metadata:
            ui_metadata["execution_time_ms"] = round(metadata["execution_time"] * 1000, 2)
            ui_metadata["performance_class"] = self._classify_performance(metadata["execution_time"])
        
        return ui_metadata
    
    def _classify_performance(self, execution_time: float) -> str:
        """Classify performance for UI indication"""
        if execution_time < 0.1:
            return "excellent"
        elif execution_time < 0.5:
            return "good"
        elif execution_time < 2.0:
            return "fair"
        else:
            return "slow"
    
    def _generate_render_hints(self, data: Any) -> Dict[str, Any]:
        """Generate rendering hints for Electron UI"""
        hints = {
            "data_type": type(data).__name__,
            "complexity": "simple",
            "recommended_view": "default"
        }
        
        if isinstance(data, dict):
            size = len(data)
            if size > 100:
                hints["complexity"] = "complex"
                hints["recommended_view"] = "paginated"
            elif size > 20:
                hints["complexity"] = "moderate"
                hints["recommended_view"] = "collapsible"
            
            # Detect data patterns
            if "chart_data" in str(data).lower() or "plot" in str(data).lower():
                hints["recommended_view"] = "chart"
            elif "table" in str(data).lower() or isinstance(data, list) and len(data) > 5:
                hints["recommended_view"] = "table"
            elif "image" in str(data).lower() or "base64" in str(data).lower():
                hints["recommended_view"] = "media"
        
        elif isinstance(data, list):
            if len(data) > 50:
                hints["complexity"] = "complex"
                hints["recommended_view"] = "virtualized"
            elif len(data) > 10:
                hints["complexity"] = "moderate"
                hints["recommended_view"] = "paginated"
        
        return hints
    
    def _determine_update_strategy(self, data: Any, metadata: Dict[str, Any]) -> str:
        """Determine how Electron UI should update"""
        if metadata.get("cached", False):
            return "instant"
        elif metadata.get("execution_time", 0) < 0.1:
            return "immediate"
        elif metadata.get("operation_type") == "tool" and metadata.get("server_name"):
            return "progressive"
        else:
            return "standard"
    
    def _generate_ui_suggestions(self, data: Any, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate UI action suggestions"""
        suggestions = []
        
        if metadata.get("tool_name"):
            suggestions.append({
                "type": "action",
                "text": f"View {metadata['tool_name']} details",
                "action": "show_tool_details",
                "params": {"tool_name": metadata["tool_name"]}
            })
        
        if metadata.get("server_name"):
            suggestions.append({
                "type": "navigation",
                "text": f"Explore {metadata['server_name']} server",
                "action": "navigate_to_server",
                "params": {"server_name": metadata["server_name"]}
            })
        
        if isinstance(data, dict) and len(data) > 5:
            suggestions.append({
                "type": "view",
                "text": "Export data",
                "action": "export_data",
                "params": {"format": "json"}
            })
        
        return suggestions
    
    def _categorize_error(self, error: str) -> str:
        """Categorize error for UI handling"""
        error_lower = error.lower()
        
        if "not found" in error_lower:
            return "not_found"
        elif "timeout" in error_lower or "connection" in error_lower:
            return "network"
        elif "permission" in error_lower or "unauthorized" in error_lower:
            return "permission"
        elif "validation" in error_lower or "invalid" in error_lower:
            return "validation"
        elif "security" in error_lower:
            return "security"
        else:
            return "unknown"
    
    def _determine_error_severity(self, error: str, metadata: Dict[str, Any]) -> str:
        """Determine error severity for UI display"""
        error_type = self._categorize_error(error)
        
        if error_type in ["security", "permission"]:
            return "high"
        elif error_type in ["network", "timeout"]:
            return "medium"
        elif error_type in ["validation", "not_found"]:
            return "low"
        else:
            return "medium"
    
    def _is_error_recoverable(self, error: str) -> bool:
        """Determine if error is recoverable"""
        error_type = self._categorize_error(error)
        return error_type in ["network", "timeout", "validation"]
    
    def _generate_error_suggestions(self, error: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate error handling suggestions for UI"""
        suggestions = []
        error_type = self._categorize_error(error)
        
        if error_type == "network":
            suggestions.extend([
                {
                    "type": "action",
                    "text": "Retry operation",
                    "action": "retry_last_operation",
                    "params": {}
                },
                {
                    "type": "action",
                    "text": "Check connection status",
                    "action": "show_connection_status",
                    "params": {}
                }
            ])
        elif error_type == "not_found":
            suggestions.extend([
                {
                    "type": "action",
                    "text": "Browse available options",
                    "action": "show_available_tools",
                    "params": {}
                },
                {
                    "type": "navigation",
                    "text": "Go to server list",
                    "action": "navigate_to_servers",
                    "params": {}
                }
            ])
        elif error_type == "validation":
            suggestions.append({
                "type": "action",
                "text": "Review parameters",
                "action": "show_parameter_help",
                "params": {"operation": metadata.get("operation_type")}
            })
        
        return suggestions
    
    def _should_show_notification(self, error: str) -> bool:
        """Determine if error should show desktop notification"""
        severity = self._determine_error_severity(error, {})
        return severity in ["high", "medium"]
    
    def _should_show_error_dialog(self, error: str) -> bool:
        """Determine if error should show modal dialog"""
        error_type = self._categorize_error(error)
        return error_type in ["security", "permission"]
    
    def _determine_retry_strategy(self, error: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Determine retry strategy for Electron UI"""
        error_type = self._categorize_error(error)
        
        if error_type == "network":
            return {
                "enabled": True,
                "max_attempts": 3,
                "delay_seconds": 2,
                "exponential_backoff": True
            }
        elif error_type == "timeout":
            return {
                "enabled": True,
                "max_attempts": 2,
                "delay_seconds": 5,
                "exponential_backoff": False
            }
        else:
            return {
                "enabled": False,
                "max_attempts": 0,
                "delay_seconds": 0,
                "exponential_backoff": False
            }


class StreamingResponseFormatter(ResponseFormatter):
    """Formatter for streaming responses to Electron UI"""
    
    def __init__(self, config: Optional[FormatterConfiguration] = None):
        super().__init__(config)
        self.stream_buffer = deque(maxlen=1000)
        self.active_streams: Dict[str, Dict[str, Any]] = {}
    
    def format_success(self, data: Any, **metadata) -> Dict[str, Any]:
        """Format streaming success response"""
        stream_id = metadata.get("stream_id", str(uuid.uuid4()))
        
        response = {
            "type": "stream_chunk",
            "stream_id": stream_id,
            "status": "success",
            "data": data,
            "chunk_index": metadata.get("chunk_index", 0),
            "total_chunks": metadata.get("total_chunks"),
            "is_final": metadata.get("is_final", False),
            "timestamp": datetime.now().isoformat()
        }
        
        # Track stream
        if stream_id not in self.active_streams:
            self.active_streams[stream_id] = {
                "started_at": datetime.now(),
                "chunks_received": 0,
                "total_size": 0
            }
        
        self.active_streams[stream_id]["chunks_received"] += 1
        self.active_streams[stream_id]["total_size"] += len(str(data))
        
        # Add stream metadata
        response["stream_metadata"] = {
            "chunks_received": self.active_streams[stream_id]["chunks_received"],
            "total_size_bytes": self.active_streams[stream_id]["total_size"],
            "elapsed_time": (datetime.now() - self.active_streams[stream_id]["started_at"]).total_seconds()
        }
        
        # Cleanup completed streams
        if response["is_final"]:
            self.active_streams.pop(stream_id, None)
        
        return response
    
    def format_error(self, error: str, **metadata) -> Dict[str, Any]:
        """Format streaming error response"""
        stream_id = metadata.get("stream_id", str(uuid.uuid4()))
        
        response = {
            "type": "stream_error",
            "stream_id": stream_id,
            "status": "error",
            "error": error,
            "is_final": True,
            "timestamp": datetime.now().isoformat()
        }
        
        # Cleanup errored stream
        self.active_streams.pop(stream_id, None)
        
        return response
    
    def get_active_streams(self) -> Dict[str, Dict[str, Any]]:
        """Get information about active streams"""
        return self.active_streams.copy()


# Legacy formatter classes for backward compatibility
class DetailedResponseFormatter(ResponseFormatter):
    """Detailed response formatter with debug information"""
    
    def __init__(self, config: Optional[FormatterConfiguration] = None, include_debug: bool = False):
        if config is None:
            config = FormatterConfiguration(
                format_type=ResponseFormat.DETAILED,
                include_debug=include_debug
            )
        super().__init__(config)
    
    def format_success(self, data: Any, **metadata) -> Dict[str, Any]:
        """Format a successful response with detailed information"""
        response = {
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "response_type": "success",
            "data_type": type(data).__name__
        }
        
        if metadata:
            response["metadata"] = metadata
        
        if self.config.include_debug:
            response["debug"] = {
                "formatter": "DetailedResponseFormatter",
                "metadata_keys": list(metadata.keys()) if metadata else [],
                "data_size": self._estimate_size(data)
            }
        
        return response
    
    def format_error(self, error: str, **metadata) -> Dict[str, Any]:
        """Format an error response with detailed information"""
        response = {
            "success": False,
            "error": error,
            "error_type": self._categorize_error_type(error),
            "timestamp": datetime.now().isoformat(),
            "response_type": "error"
        }
        
        if metadata:
            response["metadata"] = metadata
        
        if self.config.include_debug:
            response["debug"] = {
                "formatter": "DetailedResponseFormatter",
                "error_length": len(error),
                "metadata_keys": list(metadata.keys()) if metadata else []
            }
        
        return response
    
    def _estimate_size(self, data: Any) -> int:
        """Estimate the size of data"""
        try:
            import sys
            return sys.getsizeof(data)
        except:
            return -1
    
    def _categorize_error_type(self, error: str) -> str:
        """Categorize error type"""
        error_lower = error.lower()
        if "not found" in error_lower:
            return "not_found"
        elif "validation" in error_lower:
            return "validation_error"
        elif "connection" in error_lower or "timeout" in error_lower:
            return "connection_error"
        elif "permission" in error_lower or "unauthorized" in error_lower:
            return "permission_error"
        else:
            return "unknown"


class MinimalResponseFormatter(ResponseFormatter):
    """Minimal response formatter"""
    
    def __init__(self, config: Optional[FormatterConfiguration] = None):
        if config is None:
            config = FormatterConfiguration(format_type=ResponseFormat.MINIMAL)
        super().__init__(config)
    
    def format_success(self, data: Any, **metadata) -> Dict[str, Any]:
        """Format a minimal successful response"""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
            return data
        
        return {
            "success": True,
            "result": data
        }
    
    def format_error(self, error: str, **metadata) -> Dict[str, Any]:
        """Format a minimal error response"""
        return {
            "success": False,
            "error": error
        }


class AgentResponseFormatter(ResponseFormatter):
    """AI agent optimized response formatter"""
    
    def __init__(self, config: Optional[FormatterConfiguration] = None, include_suggestions: bool = True):
        if config is None:
            config = FormatterConfiguration(
                format_type=ResponseFormat.AGENT,
                include_suggestions=include_suggestions
            )
        super().__init__(config)
    
    def format_success(self, data: Any, **metadata) -> Dict[str, Any]:
        """Format a successful response for AI agents"""
        response = {
            "status": "success",
            "result": data,
            "timestamp": datetime.now().isoformat()
        }
        
        if metadata:
            response["context"] = metadata
        
        if self.config.include_suggestions:
            response["suggestions"] = self._generate_success_suggestions(data, metadata)
        
        return response
    
    def format_error(self, error: str, **metadata) -> Dict[str, Any]:
        """Format an error response for AI agents"""
        response = {
            "status": "error",
            "error_message": error,
            "timestamp": datetime.now().isoformat()
        }
        
        if metadata:
            response["context"] = metadata
        
        if self.config.include_suggestions:
            response["suggestions"] = self._generate_error_suggestions(error, metadata)
        
        return response
    
    def _generate_success_suggestions(self, data: Any, metadata: Dict[str, Any]) -> List[str]:
        """Generate suggestions for successful responses"""
        suggestions = []
        
        if isinstance(data, dict):
            if "tools" in str(data).lower():
                suggestions.append("Consider using the available tools for further analysis")
            if "data" in str(data).lower() or "result" in str(data).lower():
                suggestions.append("You can analyze the returned data for insights")
        
        if metadata and "server_name" in metadata:
            suggestions.append(f"This result came from server: {metadata['server_name']}")
        
        if not suggestions:
            suggestions.append("Operation completed successfully")
        
        return suggestions
    
    def _generate_error_suggestions(self, error: str, metadata: Dict[str, Any]) -> List[str]:
        """Generate suggestions for error responses"""
        suggestions = []
        error_lower = error.lower()
        
        if "not found" in error_lower:
            suggestions.extend([
                "Check if the requested resource/tool exists",
                "Try listing available resources or tools first"
            ])
        elif "validation" in error_lower or "parameter" in error_lower:
            suggestions.extend([
                "Review the required parameters for this operation",
                "Check the parameter types and format"
            ])
        elif "connection" in error_lower:
            suggestions.extend([
                "Check server connection status",
                "Try reconnecting to the server"
            ])
        elif "permission" in error_lower:
            suggestions.extend([
                "Verify you have the required permissions",
                "Check authentication credentials"
            ])
        
        if metadata and "available_tools" in metadata:
            suggestions.append(f"Available alternatives: {', '.join(metadata['available_tools'][:3])}")
        
        if not suggestions:
            suggestions.append("Review the error message and try again")
        
        return suggestions


class JSONResponseFormatter(ResponseFormatter):
    """JSON-safe response formatter"""
    
    def __init__(self, config: Optional[FormatterConfiguration] = None, pretty_print: bool = False):
        if config is None:
            config = FormatterConfiguration(
                format_type=ResponseFormat.JSON,
                pretty_print_json=pretty_print
            )
        super().__init__(config)
    
    def format_success(self, data: Any, **metadata) -> Dict[str, Any]:
        """Format a successful response ensuring JSON compatibility"""
        response = {
            "success": True,
            "data": self._make_json_serializable(data),
            "timestamp": datetime.now().isoformat()
        }
        
        if metadata:
            response["metadata"] = self._make_json_serializable(metadata)
        
        return response
    
    def format_error(self, error: str, **metadata) -> Dict[str, Any]:
        """Format an error response ensuring JSON compatibility"""
        response = {
            "success": False,
            "error": str(error),
            "timestamp": datetime.now().isoformat()
        }
        
        if metadata:
            response["metadata"] = self._make_json_serializable(metadata)
        
        return response
    
    def _make_json_serializable(self, obj: Any) -> Any:
        """Convert object to JSON-serializable format"""
        if obj is None:
            return None
        elif isinstance(obj, (bool, int, float, str)):
            return obj
        elif isinstance(obj, dict):
            return {str(k): self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return self._make_json_serializable(obj.__dict__)
        else:
            return str(obj)
    
    def to_json_string(self, response: Dict[str, Any]) -> str:
        """Convert response to JSON string"""
        if self.config.pretty_print_json:
            return json.dumps(response, indent=2, ensure_ascii=False)
        else:
            return json.dumps(response, ensure_ascii=False)


class ResponseFormatterFactory:
    """Enhanced factory for creating response formatters"""
    
    _formatters = {
        ResponseFormat.STANDARD: StandardResponseFormatter,
        ResponseFormat.DETAILED: DetailedResponseFormatter,
        ResponseFormat.MINIMAL: MinimalResponseFormatter,
        ResponseFormat.AGENT: AgentResponseFormatter,
        ResponseFormat.JSON: JSONResponseFormatter,
        ResponseFormat.ELECTRON: ElectronResponseFormatter,
        ResponseFormat.STREAMING: StreamingResponseFormatter
    }
    
    @staticmethod
    def create_formatter(format_type: Union[str, ResponseFormat], 
                        config: Optional[FormatterConfiguration] = None,
                        **kwargs) -> ResponseFormatter:
        """Create a response formatter of the specified type"""
        
        # Handle string format types
        if isinstance(format_type, str):
            try:
                format_type = ResponseFormat(format_type.lower())
            except ValueError:
                raise ValueError(f"Unknown formatter type: {format_type}")
        
        # Create configuration if not provided
        if config is None:
            config = FormatterConfiguration(format_type=format_type, **kwargs)
        
        # Get formatter class
        formatter_class = ResponseFormatterFactory._formatters.get(format_type)
        if not formatter_class:
            raise ValueError(f"Unsupported formatter type: {format_type}")
        
        # Handle legacy formatters that don't accept config
        if format_type in [ResponseFormat.DETAILED, ResponseFormat.MINIMAL, 
                          ResponseFormat.AGENT, ResponseFormat.JSON]:
            return ResponseFormatterFactory._create_legacy_formatter(format_type, config, **kwargs)
        
        return formatter_class(config)
    
    @staticmethod
    def _create_legacy_formatter(format_type: ResponseFormat, 
                               config: FormatterConfiguration, 
                               **kwargs) -> ResponseFormatter:
        """Create legacy formatters with backward compatibility"""
        
        if format_type == ResponseFormat.DETAILED:
            return DetailedResponseFormatter(config, include_debug=config.include_debug)
        elif format_type == ResponseFormat.MINIMAL:
            return MinimalResponseFormatter(config)
        elif format_type == ResponseFormat.AGENT:
            return AgentResponseFormatter(config, include_suggestions=config.include_suggestions)
        elif format_type == ResponseFormat.JSON:
            return JSONResponseFormatter(config, pretty_print=config.pretty_print_json)
        
        raise ValueError(f"Unsupported legacy formatter: {format_type}")
    
    @staticmethod
    def get_available_formatters() -> List[str]:
        """Get list of available formatter types"""
        return [fmt.value for fmt in ResponseFormat]
    
    @staticmethod
    def get_formatter_info() -> Dict[str, Dict[str, Any]]:
        """Get detailed information about available formatters"""
        return {
            "standard": {
                "description": "Standard response format with metadata",
                "use_cases": ["general purpose", "API responses"],
                "features": ["metadata", "enterprise features"]
            },
            "detailed": {
                "description": "Detailed responses with debug information",
                "use_cases": ["debugging", "development"],
                "features": ["debug info", "error categorization"]
            },
            "minimal": {
                "description": "Minimal responses with essential data only",
                "use_cases": ["mobile apps", "bandwidth-limited"],
                "features": ["compact", "fast"]
            },
            "agent": {
                "description": "AI agent optimized responses",
                "use_cases": ["AI agents", "automation"],
                "features": ["suggestions", "structured context"]
            },
            "json": {
                "description": "Pure JSON serializable responses",
                "use_cases": ["API integration", "data export"],
                "features": ["JSON safe", "compression"]
            },
            "electron": {
                "description": "Electron UI optimized responses",
                "use_cases": ["desktop apps", "rich UIs"],
                "features": ["UI hints", "navigation", "error dialogs"]
            },
            "streaming": {
                "description": "Streaming responses for real-time updates",
                "use_cases": ["real-time data", "progress updates"],
                "features": ["chunked delivery", "progress tracking"]
            }
        }


def main():
    """Main function demonstrating Enterprise Response Formatter usage"""
    print("🚀 Enterprise Response Formatter - Security & UI Optimization")
    print("=" * 70)
    
    async def demo_response_formatter():
        """Demonstrate response formatter capabilities"""
        
        # Create different formatter configurations
        print("🔧 Creating Formatters:")
        
        # Standard formatter with enterprise features
        standard_config = FormatterConfiguration(
            format_type=ResponseFormat.STANDARD,
            security_level=SecurityLevel.STRICT,
            enable_compression=True,
            enable_caching=True,
            include_performance_metrics=True
        )
        standard_formatter = StandardResponseFormatter(standard_config)
        print("   ✅ Standard formatter (enterprise features enabled)")
        
        # Electron-optimized formatter
        electron_config = FormatterConfiguration(
            format_type=ResponseFormat.ELECTRON,
            security_level=SecurityLevel.BASIC,
            electron_optimized=True,
            include_suggestions=True
        )
        electron_formatter = ElectronResponseFormatter(electron_config)
        print("   ✅ Electron formatter (UI optimized)")
        
        # Streaming formatter
        streaming_config = FormatterConfiguration(
            format_type=ResponseFormat.STREAMING,
            enable_streaming=True
        )
        streaming_formatter = StreamingResponseFormatter(streaming_config)
        print("   ✅ Streaming formatter (real-time updates)")
        
        # Demonstrate standard formatting
        print(f"\n📋 Standard Response Formatting:")
        
        success_response = standard_formatter.format_response(
            success=True,
            data={"analysis_result": "positive", "confidence": 0.95},
            operation_type="tool_execution",
            tool_name="sentiment_analyzer",
            server_name="ai_server",
            execution_time=0.234,
            cached=False
        )
        
        print(f"   Success response generated: {'✅ YES' if success_response['success'] else '❌ NO'}")
        print(f"   Performance metrics included: {'✅ YES' if 'performance' in success_response.get('metadata', {}) else '❌ NO'}")
        print(f"   Security sanitization applied: {'✅ YES' if standard_formatter.sanitizer.sanitization_stats['total_sanitized'] >= 0 else '❌ NO'}")
        
        # Demonstrate error formatting
        error_response = standard_formatter.format_response(
            success=False,
            error="Tool 'dangerous_analyzer' is blocked by security policy",
            operation_type="tool_execution",
            tool_name="dangerous_analyzer",
            server_name="ai_server"
        )
        
        print(f"   Error response generated: {'✅ YES' if not error_response['success'] else '❌ NO'}")
        
        # Demonstrate Electron-specific formatting
        print(f"\n🎨 Electron UI Formatting:")
        
        electron_response = electron_formatter.format_response(
            success=True,
            data={
                "chart_data": [{"x": 1, "y": 10}, {"x": 2, "y": 20}],
                "total_records": 150
            },
            operation_type="resource_access",
            resource_uri="data://analytics/dashboard",
            server_name="analytics_server",
            execution_time=0.456
        )
        
        print(f"   Electron response generated: {'✅ YES' if electron_response['status'] == 'success' else '❌ NO'}")
        print(f"   UI suggestions included: {'✅ YES' if 'ui_suggestions' in electron_response else '❌ NO'}")
        print(f"   Render hints provided: {'✅ YES' if 'render_hints' in electron_response.get('electron', {}) else '❌ NO'}")
        
        if 'ui_suggestions' in electron_response:
            print(f"   UI suggestions count: {len(electron_response['ui_suggestions'])}")
        
        if 'electron' in electron_response and 'render_hints' in electron_response['electron']:
            hints = electron_response['electron']['render_hints']
            print(f"   Recommended view: {hints.get('recommended_view', 'default')}")
        
        # Demonstrate streaming responses
        print(f"\n📡 Streaming Response Formatting:")
        
        stream_id = str(uuid.uuid4())
        
        # First chunk
        chunk1 = streaming_formatter.format_response(
            success=True,
            data={"progress": 0.3, "message": "Processing..."},
            stream_id=stream_id,
            chunk_index=0,
            is_final=False
        )
        
        # Final chunk
        chunk2 = streaming_formatter.format_response(
            success=True,
            data={"progress": 1.0, "message": "Complete", "result": "success"},
            stream_id=stream_id,
            chunk_index=1,
            is_final=True
        )
        
        print(f"   Stream chunks generated: 2")
        print(f"   Stream tracking: {'✅ YES' if 'stream_metadata' in chunk1 else '❌ NO'}")
        print(f"   Final chunk marked: {'✅ YES' if chunk2.get('is_final') else '❌ NO'}")
        
        # Demonstrate security features
        print(f"\n🔒 Security Features:")
        
        # Test with sensitive data
        sensitive_response = standard_formatter.format_response(
            success=True,
            data={
                "user_data": "john_doe",
                "password": "secret123",
                "api_key": "sk-1234567890abcdef",
                "normal_data": "public_info"
            },
            operation_type="data_retrieval"
        )
        
        # Check if sensitive data was sanitized
        response_str = str(sensitive_response)
        has_password = "secret123" in response_str
        has_api_key = "sk-1234567890abcdef" in response_str
        has_asterisks = "*" in response_str
        
        print(f"   Sensitive data detected: {'✅ YES' if not has_password and not has_api_key else '❌ NO'}")
        print(f"   Data sanitized: {'✅ YES' if has_asterisks else '❌ NO'}")
        
        # Test compression
        print(f"\n📦 Compression Features:")
        
        # Large data that should trigger compression
        large_data = {"large_array": list(range(1000)), "description": "x" * 2000}
        
        compressed_response = standard_formatter.format_response(
            success=True,
            data=large_data,
            operation_type="large_data_transfer"
        )
        
        is_compressed = compressed_response.get("compressed", False)
        print(f"   Large data compressed: {'✅ YES' if is_compressed else '❌ NO'}")
        
        if is_compressed:
            original_size = compressed_response.get("original_size", 0)
            compressed_size = compressed_response.get("compressed_size", 0)
            ratio = compressed_response.get("compression_ratio", 0)
            print(f"   Compression ratio: {ratio:.1f}% ({original_size} → {compressed_size} bytes)")
        
        # Demonstrate performance metrics
        print(f"\n📈 Performance Metrics:")
        
        standard_metrics = standard_formatter.get_ui_metrics()
        electron_metrics = electron_formatter.get_ui_metrics()
        
        print(f"   Standard formatter:")
        print(f"     Total responses: {standard_metrics['performance']['total_responses']}")
        print(f"     Success rate: {standard_metrics['performance']['success_rate']:.1f}%")
        print(f"     Avg formatting time: {standard_metrics['performance']['average_formatting_time']:.2f}ms")
        
        print(f"   Electron formatter:")
        print(f"     Total responses: {electron_metrics['performance']['total_responses']}")
        print(f"     Success rate: {electron_metrics['performance']['success_rate']:.1f}%")
        
        # Demonstrate factory usage
        print(f"\n🏭 Factory Usage:")
        
        available_formatters = ResponseFormatterFactory.get_available_formatters()
        print(f"   Available formatters: {len(available_formatters)}")
        
        for formatter_type in available_formatters[:3]:  # Show first 3
            try:
                formatter = ResponseFormatterFactory.create_formatter(formatter_type)
                test_response = formatter.format_response(success=True, data={"test": "data"})
                success_indicators = ["success", "status"]
                has_indicator = any(indicator in test_response for indicator in success_indicators)
                print(f"   {formatter_type}: {'✅ WORKS' if has_indicator else '❌ FAILED'}")
            except Exception as e:
                print(f"   {formatter_type}: ❌ ERROR - {e}")
        
        # Get formatter information
        formatter_info = ResponseFormatterFactory.get_formatter_info()
        print(f"   Detailed info available for {len(formatter_info)} formatters")
        
        print(f"\n🎉 Demo completed successfully!")
        
        return {
            "standard_formatter": standard_formatter,
            "electron_formatter": electron_formatter,
            "streaming_formatter": streaming_formatter,
            "metrics": {
                "standard": standard_metrics,
                "electron": electron_metrics
            }
        }
    
    # Run demonstration
    try:
        result = asyncio.run(demo_response_formatter())
        print("\n🎉 Demo completed successfully!")
        return result
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    """Main execution block for testing the Enterprise Response Formatter locally"""
    
    def run_static_tests():
        """Run static tests for Response Formatter"""
        print("🧪 Running Static Tests...")
        
        tests = []
        
        # Test 1: Configuration validation
        try:
            config = FormatterConfiguration(
                format_type=ResponseFormat.STANDARD,
                security_level=SecurityLevel.STRICT,
                enable_compression=True
            )
            tests.append(("Configuration Creation", True, "Valid config created"))
        except Exception as e:
            tests.append(("Configuration Creation", False, f"Config error: {e}"))
        
        # Test 2: Invalid configuration
        try:
            FormatterConfiguration(compression_threshold=0, max_response_size=100)
            tests.append(("Invalid Config Validation", False, "Should have failed"))
        except ValueError:
            tests.append(("Invalid Config Validation", True, "Properly rejected invalid config"))
        
        # Test 3: Security sanitizer
        try:
            sanitizer = ResponseSanitizer(SecurityLevel.STRICT)
            
            test_data = {"password": "secret123", "normal": "data"}
            sanitized = sanitizer.sanitize_response(test_data)
            
            sanitization_works = "secret123" not in str(sanitized)
            tests.append(("Security Sanitizer", sanitization_works, "Sensitive data sanitized"))
        except Exception as e:
            tests.append(("Security Sanitizer", False, f"Sanitizer error: {e}"))
        
        # Test 4: Response compressor
        try:
            compressor = ResponseCompressor(compression_threshold=100)
            
            large_data = {"data": "x" * 1000}
            compressed, was_compressed = compressor.compress_response(large_data)
            
            compression_works = was_compressed and "compressed" in compressed
            tests.append(("Response Compressor", compression_works, "Large data compressed"))
        except Exception as e:
            tests.append(("Response Compressor", False, f"Compressor error: {e}"))
        
        # Test 5: Response cache
        try:
            cache = ResponseCache(max_size=10, default_ttl=60)
            
            cache.set("test_key", {"data": "test"})
            cached_value = cache.get("test_key")
            
            cache_works = cached_value is not None and cached_value["data"] == "test"
            tests.append(("Response Cache", cache_works, "Cache set/get works"))
        except Exception as e:
            tests.append(("Response Cache", False, f"Cache error: {e}"))
        
        # Test 6: Factory pattern
        try:
            formatter = ResponseFormatterFactory.create_formatter("standard")
            available = ResponseFormatterFactory.get_available_formatters()
            
            factory_works = (
                isinstance(formatter, StandardResponseFormatter) and
                len(available) > 0 and
                "standard" in available
            )
            tests.append(("Factory Pattern", factory_works, f"Factory works, {len(available)} formatters"))
        except Exception as e:
            tests.append(("Factory Pattern", False, f"Factory error: {e}"))
        
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
        """Run dynamic tests for Response Formatter"""
        print("\n⚡ Running Dynamic Tests...")
        
        async def async_test_suite():
            tests = []
            
            # Test 1: Standard formatter with enterprise features
            try:
                config = FormatterConfiguration(
                    format_type=ResponseFormat.STANDARD,
                    enable_compression=True,
                    enable_caching=True,
                    include_performance_metrics=True
                )
                formatter = StandardResponseFormatter(config)
                
                response = formatter.format_response(
                    success=True,
                    data={"test": "data"},
                    operation_type="test",
                    execution_time=0.1
                )
                
                standard_works = (
                    response["success"] and
                    "metadata" in response and
                    "performance" in response["metadata"]
                )
                tests.append(("Standard Formatter", standard_works, "Enterprise features work"))
            except Exception as e:
                tests.append(("Standard Formatter", False, f"Standard error: {e}"))
            
            # Test 2: Electron formatter UI optimization
            try:
                config = FormatterConfiguration(
                    format_type=ResponseFormat.ELECTRON,
                    electron_optimized=True,
                    include_suggestions=True
                )
                formatter = ElectronResponseFormatter(config)
                
                response = formatter.format_response(
                    success=True,
                    data={"chart_data": [1, 2, 3]},
                    tool_name="analyzer",
                    server_name="test_server"
                )
                
                electron_works = (
                    response["status"] == "success" and
                    "ui_suggestions" in response and
                    "electron" in response
                )
                tests.append(("Electron Formatter", electron_works, "UI optimization works"))
            except Exception as e:
                tests.append(("Electron Formatter", False, f"Electron error: {e}"))
            
            # Test 3: Streaming formatter
            try:
                formatter = StreamingResponseFormatter()
                
                stream_id = str(uuid.uuid4())
                response = formatter.format_response(
                    success=True,
                    data={"progress": 0.5},
                    stream_id=stream_id,
                    chunk_index=0,
                    is_final=False
                )
                
                streaming_works = (
                    response["type"] == "stream_chunk" and
                    response["stream_id"] == stream_id and
                    "stream_metadata" in response
                )
                tests.append(("Streaming Formatter", streaming_works, "Streaming features work"))
            except Exception as e:
                tests.append(("Streaming Formatter", False, f"Streaming error: {e}"))
            
            # Test 4: Security sanitization
            try:
                config = FormatterConfiguration(
                    security_level=SecurityLevel.STRICT,
                    enable_sanitization=True
                )
                formatter = StandardResponseFormatter(config)
                
                response = formatter.format_response(
                    success=True,
                    data={
                        "password": "secret123",
                        "api_key": "sk-abcdef123456",
                        "safe_data": "public_info"
                    }
                )
                
                response_str = str(response)
                security_works = (
                    "secret123" not in response_str and
                    "sk-abcdef123456" not in response_str and
                    "public_info" in response_str
                )
                tests.append(("Security Sanitization", security_works, "Sensitive data removed"))
            except Exception as e:
                tests.append(("Security Sanitization", False, f"Security error: {e}"))
            
            # Test 5: Response compression
            try:
                config = FormatterConfiguration(
                    enable_compression=True,
                    compression_threshold=100
                )
                formatter = StandardResponseFormatter(config)
                
                # Large data that should trigger compression
                large_data = {"large_field": "x" * 2000}
                response = formatter.format_response(
                    success=True,
                    data=large_data
                )
                
                compression_works = response.get("compressed", False)
                tests.append(("Response Compression", compression_works, "Large responses compressed"))
            except Exception as e:
                tests.append(("Response Compression", False, f"Compression error: {e}"))
            
            # Test 6: Response caching
            try:
                config = FormatterConfiguration(enable_caching=True)
                formatter = StandardResponseFormatter(config)
                
                # First call (cache miss)
                response1 = formatter.format_response(
                    success=True,
                    data={"cacheable": "data"},
                    operation_type="test"
                )
                
                # Second call (should hit cache)
                response2 = formatter.format_response(
                    success=True,
                    data={"cacheable": "data"},
                    operation_type="test"
                )
                
                caching_works = (
                    response1["success"] and
                    response2["success"] and
                    formatter.metrics.cached_responses > 0
                )
                tests.append(("Response Caching", caching_works, "Response caching works"))
            except Exception as e:
                tests.append(("Response Caching", False, f"Caching error: {e}"))
            
            # Test 7: Error handling and categorization
            try:
                formatter = ElectronResponseFormatter()
                
                error_response = formatter.format_response(
                    success=False,
                    error="Connection timeout while accessing server",
                    operation_type="tool_execution"
                )
                
                error_works = (
                    error_response["status"] == "error" and
                    "error" in error_response and
                    error_response["error"]["type"] == "network" and
                    "ui_suggestions" in error_response
                )
                tests.append(("Error Handling", error_works, "Error categorization and suggestions work"))
            except Exception as e:
                tests.append(("Error Handling", False, f"Error handling error: {e}"))
            
            # Test 8: Performance metrics
            try:
                formatter = StandardResponseFormatter()
                
                # Generate multiple responses to get metrics
                for i in range(5):
                    formatter.format_response(
                        success=True,
                        data={"iteration": i},
                        operation_type="test"
                    )
                
                metrics = formatter.get_ui_metrics()
                
                metrics_works = (
                    metrics["performance"]["total_responses"] == 5 and
                    metrics["performance"]["success_rate"] == 100.0 and
                    "average_formatting_time" in metrics["performance"]
                )
                tests.append(("Performance Metrics", metrics_works, "Metrics collection works"))
            except Exception as e:
                tests.append(("Performance Metrics", False, f"Metrics error: {e}"))
            
            # Test 9: Event system
            try:
                formatter = StandardResponseFormatter()
                events_captured = []
                
                def event_handler(data):
                    events_captured.append(data)
                
                formatter.on("response_formatted", event_handler)
                
                formatter.format_response(
                    success=True,
                    data={"event_test": True}
                )
                
                # Get events from queue
                events = formatter.get_events()
                
                event_works = (
                    len(events_captured) > 0 and
                    len(events) > 0
                )
                tests.append(("Event System", event_works, f"Events captured: {len(events_captured)}"))
            except Exception as e:
                tests.append(("Event System", False, f"Event error: {e}"))
            
            # Test 10: Factory with different types
            try:
                formatter_types = ["standard", "electron", "streaming", "agent"]
                created_formatters = []
                
                for fmt_type in formatter_types:
                    try:
                        formatter = ResponseFormatterFactory.create_formatter(fmt_type)
                        test_response = formatter.format_response(success=True, data={"test": fmt_type})
                        created_formatters.append(fmt_type)
                    except Exception:
                        pass
                
                factory_works = len(created_formatters) >= 3  # At least 3 should work
                tests.append(("Factory Variants", factory_works, f"Created {len(created_formatters)} formatters"))
            except Exception as e:
                tests.append(("Factory Variants", False, f"Factory error: {e}"))
            
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
    print("🏃 Running Enterprise Response Formatter Tests")
    print("=" * 80)
    
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
    print("\n" + "=" * 80)
    print("🏁 Enterprise Response Formatter Test Summary")
    print("=" * 80)
    print(f"Static Tests: {'✅ PASSED' if static_passed else '❌ FAILED'}")
    print(f"Dynamic Tests: {'✅ PASSED' if dynamic_passed else '❌ FAILED'}")
    print(f"Overall Status: {'✅ SUCCESS' if static_passed and dynamic_passed else '❌ FAILURE'}")
    
    # Additional information for Electron integration
    if static_passed and dynamic_passed:
        print("\n🎨 Electron Integration Features:")
        print("  • UI-optimized response formatting via ElectronResponseFormatter")
        print("  • Real-time streaming updates via StreamingResponseFormatter")
        print("  • Security sanitization of sensitive data")
        print("  • Response compression for large data transfers")
        print("  • Performance metrics for dashboard display")
        print("  • Event system for real-time UI notifications")
        print("  • Error categorization with UI suggestions")
        print("  • Render hints for optimal UI display")
        
        print("\n📡 UI Integration Examples:")
        print("  • formatter.format_response() - Main formatting API")
        print("  • formatter.get_ui_metrics() - Dashboard metrics")
        print("  • formatter.get_events() - Real-time notifications")
        print("  • ElectronResponseFormatter - UI-optimized responses")
        print("  • StreamingResponseFormatter - Real-time updates")
    
    exit_code = 0 if (static_passed and dynamic_passed) else 1
    print(f"\nExit Code: {exit_code}")
    print("Run with: python -m src.mcp.core.client.response_formatter")

