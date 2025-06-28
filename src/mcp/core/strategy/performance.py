"""
Performance Monitoring Module

Tracks system performance, memory usage, and operation timing
for optimization and debugging purposes.
"""

import time
import psutil
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    name: str
    value: float
    timestamp: float
    unit: str = "seconds"
    category: str = "general"


@dataclass
class OperationStats:
    """Statistics for a specific operation"""
    name: str
    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    recent_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def add_timing(self, duration: float):
        """Add a timing measurement"""
        self.call_count += 1
        self.total_time += duration
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)
        self.avg_time = self.total_time / self.call_count
        self.recent_times.append(duration)


class PerformanceMonitor:
    """Performance monitoring and profiling system"""
    
    def __init__(self, max_metrics: int = 1000):
        self.max_metrics = max_metrics
        self.metrics: List[PerformanceMetric] = []
        self.operation_stats: Dict[str, OperationStats] = {}
        self.start_time = time.time()
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.system_stats: Dict[str, Any] = {}
        self.alert_thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "response_time": 5.0
        }
        self.alerts: List[Dict[str, Any]] = []
    
    def start(self):
        """Start performance monitoring"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_system, daemon=True)
            self.monitor_thread.start()
            logger.info("Performance monitoring started")
    
    def stop(self):
        """Stop performance monitoring"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        logger.info("Performance monitoring stopped")
    
    def _monitor_system(self):
        """Monitor system metrics in background"""
        while self.is_monitoring:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.add_metric("cpu_usage", cpu_percent, "percent", "system")
                
                # Memory usage
                memory = psutil.virtual_memory()
                self.add_metric("memory_usage", memory.percent, "percent", "system")
                self.add_metric("memory_available", memory.available / (1024**3), "GB", "system")
                
                # Disk usage
                disk = psutil.disk_usage('/')
                self.add_metric("disk_usage", disk.percent, "percent", "system")
                
                # Network I/O
                network = psutil.net_io_counters()
                self.add_metric("network_bytes_sent", network.bytes_sent, "bytes", "network")
                self.add_metric("network_bytes_recv", network.bytes_recv, "bytes", "network")
                
                # Check alerts
                self._check_alerts(cpu_percent, memory.percent)
                
                # Store system stats
                self.system_stats = {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_gb": memory.available / (1024**3),
                    "disk_percent": disk.percent,
                    "timestamp": time.time()
                }
                
            except Exception as e:
                logger.error(f"Error in system monitoring: {e}")
            
            time.sleep(5)  # Monitor every 5 seconds
    
    def add_metric(self, name: str, value: float, unit: str = "seconds", category: str = "general"):
        """Add a performance metric"""
        metric = PerformanceMetric(name, value, time.time(), unit, category)
        self.metrics.append(metric)
        
        # Keep only recent metrics
        if len(self.metrics) > self.max_metrics:
            self.metrics = self.metrics[-self.max_metrics:]
    
    @contextmanager
    def measure(self, operation_name: str):
        """Context manager for measuring operation timing"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_operation(operation_name, duration)
    
    def record_operation(self, operation_name: str, duration: float):
        """Record operation timing"""
        if operation_name not in self.operation_stats:
            self.operation_stats[operation_name] = OperationStats(operation_name)
        
        self.operation_stats[operation_name].add_timing(duration)
        
        # Add as metric
        self.add_metric(f"operation_{operation_name}", duration, "seconds", "operations")
        
        # Check for slow operations
        if duration > self.alert_thresholds.get("response_time", 5.0):
            self._add_alert("slow_operation", f"Operation {operation_name} took {duration:.2f}s")
    
    def _check_alerts(self, cpu_percent: float, memory_percent: float):
        """Check for performance alerts"""
        if cpu_percent > self.alert_thresholds["cpu_percent"]:
            self._add_alert("high_cpu", f"CPU usage: {cpu_percent:.1f}%")
        
        if memory_percent > self.alert_thresholds["memory_percent"]:
            self._add_alert("high_memory", f"Memory usage: {memory_percent:.1f}%")
    
    def _add_alert(self, alert_type: str, message: str):
        """Add performance alert"""
        alert = {
            "type": alert_type,
            "message": message,
            "timestamp": time.time(),
            "severity": "warning"
        }
        self.alerts.append(alert)
        
        # Keep only recent alerts
        if len(self.alerts) > 50:
            self.alerts = self.alerts[-50:]
        
        logger.warning(f"Performance alert: {message}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        current_time = time.time()
        uptime = current_time - self.start_time
        
        # Operation statistics
        op_stats = {}
        for name, stats in self.operation_stats.items():
            op_stats[name] = {
                "call_count": stats.call_count,
                "avg_time": stats.avg_time,
                "min_time": stats.min_time,
                "max_time": stats.max_time,
                "recent_avg": sum(stats.recent_times) / len(stats.recent_times) if stats.recent_times else 0
            }
        
        # Recent metrics summary
        recent_metrics = [m for m in self.metrics if current_time - m.timestamp < 300]  # Last 5 minutes
        metrics_by_category = defaultdict(list)
        for metric in recent_metrics:
            metrics_by_category[metric.category].append(metric.value)
        
        return {
            "uptime_seconds": uptime,
            "total_metrics": len(self.metrics),
            "operation_stats": op_stats,
            "system_stats": self.system_stats,
            "recent_alerts": self.alerts[-10:] if self.alerts else [],
            "metrics_summary": {
                category: {
                    "count": len(values),
                    "avg": sum(values) / len(values) if values else 0,
                    "min": min(values) if values else 0,
                    "max": max(values) if values else 0
                }
                for category, values in metrics_by_category.items()
            }
        }
    
    def get_uptime(self) -> float:
        """Get system uptime in seconds"""
        return time.time() - self.start_time
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage information"""
        try:
            memory = psutil.virtual_memory()
            return {
                "total_gb": memory.total / (1024**3),
                "available_gb": memory.available / (1024**3),
                "used_gb": memory.used / (1024**3),
                "percent": memory.percent
            }
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return {}
    
    def is_running(self) -> bool:
        """Check if monitoring is running"""
        return self.is_monitoring
    
    def reset_stats(self):
        """Reset all performance statistics"""
        self.metrics.clear()
        self.operation_stats.clear()
        self.alerts.clear()
        self.start_time = time.time()
        logger.info("Performance statistics reset")
    
    def export_metrics(self, filepath: str, format: str = "json"):
        """Export metrics to file"""
        import json
        import csv
        
        try:
            if format.lower() == "json":
                data = {
                    "metrics": [
                        {
                            "name": m.name,
                            "value": m.value,
                            "timestamp": m.timestamp,
                            "unit": m.unit,
                            "category": m.category
                        }
                        for m in self.metrics
                    ],
                    "stats": self.get_stats()
                }
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)
            
            elif format.lower() == "csv":
                with open(filepath, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["name", "value", "timestamp", "unit", "category"])
                    for metric in self.metrics:
                        writer.writerow([metric.name, metric.value, metric.timestamp, metric.unit, metric.category])
            
            logger.info(f"Metrics exported to {filepath}")
            
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")


class CacheManager:
    """LRU cache manager for performance optimization"""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache: Dict[str, Any] = {}
        self.access_order: List[str] = []
        self.hit_count = 0
        self.miss_count = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        if key in self.cache:
            # Move to end (most recently used)
            self.access_order.remove(key)
            self.access_order.append(key)
            self.hit_count += 1
            return self.cache[key]
        
        self.miss_count += 1
        return None
    
    def put(self, key: str, value: Any):
        """Put item in cache"""
        if key in self.cache:
            # Update existing
            self.cache[key] = value
            self.access_order.remove(key)
            self.access_order.append(key)
        else:
            # Add new
            if len(self.cache) >= self.max_size:
                # Remove least recently used
                lru_key = self.access_order.pop(0)
                del self.cache[lru_key]
            
            self.cache[key] = value
            self.access_order.append(key)
    
    def clear(self):
        """Clear cache"""
        self.cache.clear()
        self.access_order.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total_requests if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": hit_rate
        }


def main():
    """Test performance monitoring functionality"""
    print("Testing Performance Monitor...")
    
    monitor = PerformanceMonitor()
    
    # Test basic functionality
    monitor.start()
    assert monitor.is_running(), "Monitor should be running"
    print("✅ Monitor start/stop passed")
    
    # Test metric recording
    monitor.add_metric("test_metric", 1.5, "seconds", "test")
    stats = monitor.get_stats()
    assert stats["total_metrics"] > 0, "Should have metrics"
    print("✅ Metric recording passed")
    
    # Test operation timing
    with monitor.measure("test_operation"):
        time.sleep(0.1)  # Simulate work
    
    assert "test_operation" in monitor.operation_stats, "Operation should be recorded"
    op_stats = monitor.operation_stats["test_operation"]
    assert op_stats.call_count == 1, "Should have one call"
    assert op_stats.avg_time > 0.05, "Should record timing"
    print("✅ Operation timing passed")
    
    # Test cache manager
    cache = CacheManager(max_size=3)
    cache.put("key1", "value1")
    cache.put("key2", "value2")
    
    assert cache.get("key1") == "value1", "Should retrieve cached value"
    assert cache.get("nonexistent") is None, "Should return None for missing key"
    
    cache_stats = cache.get_stats()
    assert cache_stats["hit_count"] == 1, "Should have one hit"
    assert cache_stats["miss_count"] == 1, "Should have one miss"
    print("✅ Cache management passed")
    
    # Test memory usage
    memory_usage = monitor.get_memory_usage()
    assert "total_gb" in memory_usage, "Should include memory info"
    print("✅ Memory usage monitoring passed")
    
    monitor.stop()
    print("🎉 All performance monitoring tests passed!")


if __name__ == "__main__":
    def test_static_performance():
        """Static performance tests"""
        print("Running static performance tests...")
        
        monitor = PerformanceMonitor()
        
        # Test initial state
        assert not monitor.is_monitoring, "Should not be monitoring initially"
        assert len(monitor.metrics) == 0, "Should have no metrics initially"
        assert len(monitor.operation_stats) == 0, "Should have no operation stats"
        
        # Test metric creation
        metric = PerformanceMetric("test", 1.0, time.time(), "unit", "category")
        assert metric.name == "test", "Metric name should be set"
        assert metric.value == 1.0, "Metric value should be set"
        
        print("✅ Static performance tests passed!")
    
    def test_dynamic_performance():
        """Dynamic performance tests"""
        print("Running dynamic performance tests...")
        
        # Run main tests
        main()
        
        print("✅ Dynamic performance tests passed!")
    
    # Run tests
    test_static_performance()
    test_dynamic_performance()