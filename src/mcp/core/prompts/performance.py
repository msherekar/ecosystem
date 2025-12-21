"""
Performance Monitoring for Domain Prompt System

Provides performance tracking, timing, and scalability insights for the system.
Helps identify bottlenecks and optimize system performance.
"""

import asyncio
import functools
import logging
import statistics
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class TimingData:
    """Performance timing data"""
    operation: str
    duration: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "operation": self.operation,
            "duration": self.duration,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class PerformanceMonitor:
    """Performance monitoring and metrics collection"""
    
    def __init__(self, max_history: int = 1000):
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._max_history = max_history
        
        # System statistics
        self._start_time = time.time()
        self._last_reset = datetime.now()
        
        # Operation tracking
        self._active_operations: Dict[str, Dict[str, Any]] = {}
        self._operation_id_counter = 0
    
    def time_operation(self, operation_name: str, include_args: bool = False):
        """
        Decorator to time operations
        
        Args:
            operation_name: Name of the operation to track
            include_args: Whether to include function arguments in metadata
        """
        def decorator(func: Callable):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                operation_id = self._start_operation(operation_name, func, args, kwargs, include_args)
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    self._record_error(operation_name, str(e))
                    raise
                finally:
                    duration = time.time() - start_time
                    self._end_operation(operation_id, operation_name, duration)
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                operation_id = self._start_operation(operation_name, func, args, kwargs, include_args)
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    self._record_error(operation_name, str(e))
                    raise
                finally:
                    duration = time.time() - start_time
                    self._end_operation(operation_id, operation_name, duration)
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    def _start_operation(self, operation_name: str, func: Callable, args: tuple, 
                        kwargs: dict, include_args: bool) -> str:
        """Start tracking an operation"""
        with self._lock:
            self._operation_id_counter += 1
            operation_id = f"{operation_name}_{self._operation_id_counter}"
            
            metadata = {
                "function": func.__name__,
                "start_time": time.time()
            }
            
            if include_args:
                # Safely serialize arguments
                try:
                    metadata["args"] = str(args)[:200]  # Limit length
                    metadata["kwargs"] = {k: str(v)[:100] for k, v in kwargs.items()}
                except Exception:
                    metadata["args"] = "[not serializable]"
                    metadata["kwargs"] = "[not serializable]"
            
            self._active_operations[operation_id] = metadata
            self.increment_counter(f"{operation_name}_started")
            
        return operation_id
    
    def _end_operation(self, operation_id: str, operation_name: str, duration: float):
        """End tracking an operation"""
        with self._lock:
            if operation_id in self._active_operations:
                metadata = self._active_operations.pop(operation_id)
            else:
                metadata = {}
            
            self.record_timing(operation_name, duration, metadata)
            self.increment_counter(f"{operation_name}_completed")
    
    def _record_error(self, operation_name: str, error: str):
        """Record an operation error"""
        self.increment_counter(f"{operation_name}_errors")
        logger.debug(f"Operation error in {operation_name}: {error}")
    
    @contextmanager
    def timer(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Context manager for timing operations
        
        Usage:
            with monitor.timer("my_operation"):
                # do work
                pass
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_timing(operation_name, duration, metadata or {})
    
    def record_timing(self, operation: str, duration: float, 
                     metadata: Optional[Dict[str, Any]] = None):
        """Record operation timing"""
        timing = TimingData(
            operation=operation,
            duration=duration,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        with self._lock:
            self._metrics[operation].append(timing)
            
            # Update performance gauges
            self._gauges[f"{operation}_last_duration"] = duration
            
            # Calculate rolling averages
            recent_timings = list(self._metrics[operation])[-10:]  # Last 10 operations
            if recent_timings:
                avg_duration = sum(t.duration for t in recent_timings) / len(recent_timings)
                self._gauges[f"{operation}_avg_duration"] = avg_duration
        
        logger.debug(f"Recorded timing for {operation}: {duration:.4f}s")
    
    def increment_counter(self, counter_name: str, value: int = 1):
        """Increment a counter"""
        with self._lock:
            self._counters[counter_name] += value
    
    def set_gauge(self, gauge_name: str, value: float):
        """Set a gauge value"""
        with self._lock:
            self._gauges[gauge_name] = value
    
    def get_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance statistics
        
        Args:
            operation: Specific operation to get stats for (None = all)
            
        Returns:
            Dictionary of performance statistics
        """
        with self._lock:
            if operation:
                return self._get_operation_stats(operation)
            
            # Overall system stats
            stats = {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "timings": {},
                "system": {
                    "uptime_seconds": time.time() - self._start_time,
                    "last_reset": self._last_reset.isoformat(),
                    "active_operations": len(self._active_operations),
                    "tracked_operations": len(self._metrics)
                }
            }
            
            # Add timing statistics for each operation
            for operation_name, timings in self._metrics.items():
                stats["timings"][operation_name] = self._calculate_timing_stats(timings)
            
            return stats
    
    def _get_operation_stats(self, operation: str) -> Dict[str, Any]:
        """Get statistics for a specific operation"""
        timings = self._metrics.get(operation, deque())
        
        return {
            "operation": operation,
            "timing_stats": self._calculate_timing_stats(timings),
            "counters": {
                k: v for k, v in self._counters.items() 
                if k.startswith(operation)
            },
            "gauges": {
                k: v for k, v in self._gauges.items() 
                if k.startswith(operation)
            }
        }
    
    def _calculate_timing_stats(self, timings: deque) -> Dict[str, Any]:
        """Calculate statistics from timing data"""
        if not timings:
            return {"count": 0}
        
        durations = [t.duration for t in timings]
        
        stats = {
            "count": len(durations),
            "avg": statistics.mean(durations),
            "min": min(durations),
            "max": max(durations),
            "recent_avg": statistics.mean(durations[-10:]) if len(durations) > 0 else 0
        }
        
        # Add percentiles for larger datasets
        if len(durations) >= 10:
            sorted_durations = sorted(durations)
            stats["median"] = statistics.median(sorted_durations)
            stats["p90"] = sorted_durations[int(0.9 * len(sorted_durations))]
            stats["p95"] = sorted_durations[int(0.95 * len(sorted_durations))]
            stats["p99"] = sorted_durations[int(0.99 * len(sorted_durations))]
        
        return stats
    
    def get_slow_operations(self, threshold: float = 1.0, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get operations that are slower than threshold
        
        Args:
            threshold: Minimum duration in seconds
            limit: Maximum number of results
            
        Returns:
            List of slow operations
        """
        slow_ops = []
        
        with self._lock:
            for operation_name, timings in self._metrics.items():
                slow_timings = [t for t in timings if t.duration >= threshold]
                if slow_timings:
                    avg_duration = sum(t.duration for t in slow_timings) / len(slow_timings)
                    slow_ops.append({
                        "operation": operation_name,
                        "slow_count": len(slow_timings),
                        "total_count": len(timings),
                        "avg_slow_duration": avg_duration,
                        "max_duration": max(t.duration for t in slow_timings)
                    })
        
        # Sort by average slow duration, descending
        slow_ops.sort(key=lambda x: x["avg_slow_duration"], reverse=True)
        return slow_ops[:limit]
    
    def get_recent_activity(self, minutes: int = 5) -> Dict[str, Any]:
        """Get activity from the last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_activity = {"operations": {}, "total_operations": 0}
        
        with self._lock:
            for operation_name, timings in self._metrics.items():
                recent_timings = [t for t in timings if t.timestamp >= cutoff_time]
                if recent_timings:
                    recent_activity["operations"][operation_name] = {
                        "count": len(recent_timings),
                        "avg_duration": sum(t.duration for t in recent_timings) / len(recent_timings),
                        "total_duration": sum(t.duration for t in recent_timings)
                    }
                    recent_activity["total_operations"] += len(recent_timings)
        
        return recent_activity
    
    def reset_stats(self):
        """Reset all performance statistics"""
        with self._lock:
            self._metrics.clear()
            self._counters.clear()
            self._gauges.clear()
            self._active_operations.clear()
            self._last_reset = datetime.now()
            self._operation_id_counter = 0
        
        logger.info("Performance statistics reset")
    
    def export_metrics(self, format: str = "json") -> Union[str, Dict[str, Any]]:
        """
        Export metrics in specified format
        
        Args:
            format: Export format ("json" or "dict")
            
        Returns:
            Exported metrics
        """
        stats = self.get_stats()
        
        if format.lower() == "json":
            import json
            return json.dumps(stats, indent=2, default=str)
        else:
            return stats


# Global performance monitor instance
_global_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance"""
    return _global_monitor


def time_it(operation_name: str, include_args: bool = False):
    """Convenience decorator for timing operations"""
    return _global_monitor.time_operation(operation_name, include_args)


def record_metric(operation: str, duration: float, metadata: Optional[Dict[str, Any]] = None):
    """Convenience function to record a metric"""
    _global_monitor.record_timing(operation, duration, metadata)


def increment_metric(counter_name: str, value: int = 1):
    """Convenience function to increment a counter"""
    _global_monitor.increment_counter(counter_name, value)


if __name__ == "__main__":
    # Test performance monitoring
    print("Testing Performance Monitor")
    
    monitor = PerformanceMonitor()
    
    # Test timing decorator
    @monitor.time_operation("test_operation")
    def test_function(delay: float = 0.1):
        time.sleep(delay)
        return "completed"
    
    # Run test operations
    test_function(0.05)
    test_function(0.1)
    test_function(0.15)
    
    # Test context manager
    with monitor.timer("context_operation"):
        time.sleep(0.05)
    
    # Test manual recording
    monitor.record_timing("manual_operation", 0.25)
    monitor.increment_counter("test_counter", 5)
    
    # Get statistics
    stats = monitor.get_stats()
    print(f"✓ Tracked operations: {len(stats['timings'])}")
    print(f"✓ Total counters: {len(stats['counters'])}")
    
    # Test slow operations detection
    slow_ops = monitor.get_slow_operations(threshold=0.1)
    print(f"✓ Slow operations detected: {len(slow_ops)}")
    
    print("\n✅ Performance monitor test completed!") 