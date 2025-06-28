"""
Registry Metrics Collection and Management

Provides comprehensive metrics collection, storage, and analysis
for the MCP registry system performance monitoring.

This file is separate from health monitoring to keep metrics
management focused and easily extensible.
"""

import logging
import threading
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

# Configure logger
logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricData:
    """A single metric data point"""
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


class MetricsCollector:
    """Collects and manages metrics for the registry system"""
    
    def __init__(self, max_history: int = 1000):
        self.metrics = defaultdict(lambda: deque(maxlen=max_history))
        self.counters = defaultdict(float)
        self.gauges = defaultdict(float)
        self.timers = defaultdict(list)
        self._lock = threading.RLock()
        self.logger = logger.getChild("MetricsCollector")
        self.max_history = max_history
        
        # Track collection stats
        self._collection_start_time = time.time()
        self._total_metrics_collected = 0
    
    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric"""
        with self._lock:
            self.counters[name] += value
            self._total_metrics_collected += 1
            
            metric = MetricData(
                name=name,
                value=self.counters[name],
                timestamp=time.time(),
                labels=labels or {},
                metric_type=MetricType.COUNTER
            )
            self.metrics[name].append(metric)
            
        self.logger.debug(f"Counter {name} incremented by {value} to {self.counters[name]}")
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric value"""
        with self._lock:
            self.gauges[name] = value
            self._total_metrics_collected += 1
            
            metric = MetricData(
                name=name,
                value=value,
                timestamp=time.time(),
                labels=labels or {},
                metric_type=MetricType.GAUGE
            )
            self.metrics[name].append(metric)
            
        self.logger.debug(f"Gauge {name} set to {value}")
    
    def record_timer(self, name: str, duration_ms: float, labels: Optional[Dict[str, str]] = None):
        """Record a timer metric"""
        with self._lock:
            self.timers[name].append(duration_ms)
            self._total_metrics_collected += 1
            
            # Keep only last 100 timer values per metric
            if len(self.timers[name]) > 100:
                self.timers[name] = self.timers[name][-100:]
            
            metric = MetricData(
                name=name,
                value=duration_ms,
                timestamp=time.time(),
                labels=labels or {},
                metric_type=MetricType.TIMER
            )
            self.metrics[name].append(metric)
            
        self.logger.debug(f"Timer {name} recorded: {duration_ms}ms")
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a histogram metric"""
        with self._lock:
            self._total_metrics_collected += 1
            
            metric = MetricData(
                name=name,
                value=value,
                timestamp=time.time(),
                labels=labels or {},
                metric_type=MetricType.HISTOGRAM
            )
            self.metrics[name].append(metric)
            
        self.logger.debug(f"Histogram {name} recorded: {value}")
    
    def get_metric_summary(self, name: str) -> Dict[str, Any]:
        """Get summary statistics for a metric"""
        with self._lock:
            if name not in self.metrics:
                return {"error": f"Metric {name} not found"}
            
            metric_data = list(self.metrics[name])
            if not metric_data:
                return {"error": f"No data for metric {name}"}
            
            latest = metric_data[-1]
            values = [m.value for m in metric_data]
            
            summary = {
                "name": name,
                "type": latest.metric_type.value,
                "latest_value": latest.value,
                "latest_timestamp": latest.timestamp,
                "data_points": len(metric_data),
                "min_value": min(values),
                "max_value": max(values),
                "avg_value": sum(values) / len(values)
            }
            
            # Add type-specific metrics
            if latest.metric_type == MetricType.TIMER and name in self.timers:
                timer_values = self.timers[name]
                if timer_values:
                    sorted_values = sorted(timer_values)
                    summary.update({
                        "timer_count": len(timer_values),
                        "timer_avg_ms": sum(timer_values) / len(timer_values),
                        "timer_min_ms": min(timer_values),
                        "timer_max_ms": max(timer_values),
                        "timer_p50_ms": self._percentile(sorted_values, 50),
                        "timer_p95_ms": self._percentile(sorted_values, 95),
                        "timer_p99_ms": self._percentile(sorted_values, 99)
                    })
            
            elif latest.metric_type == MetricType.COUNTER:
                # Calculate rate for counters
                if len(metric_data) > 1:
                    time_span = metric_data[-1].timestamp - metric_data[0].timestamp
                    if time_span > 0:
                        rate = (metric_data[-1].value - metric_data[0].value) / time_span
                        summary["rate_per_second"] = rate
            
            elif latest.metric_type == MetricType.HISTOGRAM:
                # Calculate histogram statistics
                sorted_values = sorted(values)
                summary.update({
                    "p50": self._percentile(sorted_values, 50),
                    "p75": self._percentile(sorted_values, 75),
                    "p90": self._percentile(sorted_values, 90),
                    "p95": self._percentile(sorted_values, 95),
                    "p99": self._percentile(sorted_values, 99)
                })
            
            return summary
    
    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile from sorted values"""
        if not sorted_values:
            return 0.0
        
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of all metrics"""
        with self._lock:
            return {name: self.get_metric_summary(name) for name in self.metrics.keys()}
    
    def get_metrics_by_type(self, metric_type: MetricType) -> Dict[str, Dict[str, Any]]:
        """Get all metrics of a specific type"""
        all_metrics = self.get_all_metrics()
        return {
            name: summary for name, summary in all_metrics.items()
            if summary.get("type") == metric_type.value
        }
    
    def get_recent_metrics(self, name: str, seconds: int = 300) -> List[MetricData]:
        """Get recent metrics for a specific metric name within time window"""
        with self._lock:
            if name not in self.metrics:
                return []
            
            cutoff_time = time.time() - seconds
            recent_metrics = [
                metric for metric in self.metrics[name]
                if metric.timestamp >= cutoff_time
            ]
            
            return list(recent_metrics)
    
    def calculate_rate(self, name: str, window_seconds: int = 60) -> float:
        """Calculate rate for a counter metric over a time window"""
        recent_metrics = self.get_recent_metrics(name, window_seconds)
        
        if len(recent_metrics) < 2:
            return 0.0
        
        # For counters, calculate the difference over time
        if recent_metrics[0].metric_type == MetricType.COUNTER:
            value_diff = recent_metrics[-1].value - recent_metrics[0].value
            time_diff = recent_metrics[-1].timestamp - recent_metrics[0].timestamp
            
            if time_diff > 0:
                return value_diff / time_diff
        
        return 0.0
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-level metrics about the metrics collector itself"""
        with self._lock:
            uptime = time.time() - self._collection_start_time
            
            return {
                "collector_uptime_seconds": uptime,
                "total_metrics_collected": self._total_metrics_collected,
                "unique_metric_names": len(self.metrics),
                "collection_rate": self._total_metrics_collected / uptime if uptime > 0 else 0,
                "memory_usage": {
                    "counters": len(self.counters),
                    "gauges": len(self.gauges),
                    "timers": len(self.timers),
                    "total_data_points": sum(len(deque_data) for deque_data in self.metrics.values())
                }
            }
    
    def clear_metrics(self, metric_name: Optional[str] = None):
        """Clear metrics (all or specific metric)"""
        with self._lock:
            if metric_name:
                # Clear specific metric
                if metric_name in self.metrics:
                    self.metrics[metric_name].clear()
                if metric_name in self.counters:
                    del self.counters[metric_name]
                if metric_name in self.gauges:
                    del self.gauges[metric_name]
                if metric_name in self.timers:
                    del self.timers[metric_name]
                self.logger.info(f"Cleared metrics for {metric_name}")
            else:
                # Clear all metrics
                self.metrics.clear()
                self.counters.clear()
                self.gauges.clear()
                self.timers.clear()
                self._total_metrics_collected = 0
                self._collection_start_time = time.time()
                self.logger.info("All metrics cleared")
    
    def export_metrics(self, format_type: str = "json") -> str:
        """Export metrics in various formats"""
        all_metrics = self.get_all_metrics()
        system_metrics = self.get_system_metrics()
        
        export_data = {
            "timestamp": time.time(),
            "system": system_metrics,
            "metrics": all_metrics
        }
        
        if format_type.lower() == "json":
            import json
            return json.dumps(export_data, indent=2)
        elif format_type.lower() == "prometheus":
            return self._export_prometheus_format(all_metrics)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    def _export_prometheus_format(self, metrics: Dict[str, Dict[str, Any]]) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        lines.append("# MCP Registry Metrics")
        lines.append(f"# Generated at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        for name, summary in metrics.items():
            if "error" in summary:
                continue
                
            metric_type = summary.get("type", "gauge")
            latest_value = summary.get("latest_value", 0)
            
            # Add metric type comment
            lines.append(f"# TYPE {name} {metric_type}")
            
            # Add metric value
            lines.append(f"{name} {latest_value}")
            
            # Add additional timer metrics if available
            if metric_type == "timer":
                for suffix in ["_avg", "_min", "_max", "_p95", "_p99"]:
                    key = f"timer{suffix}_ms"
                    if key in summary:
                        lines.append(f"{name}{suffix}_milliseconds {summary[key]}")
        
        return "\n".join(lines)


class MetricsAggregator:
    """Aggregates metrics from multiple collectors and provides analysis"""
    
    def __init__(self):
        self.collectors: Dict[str, MetricsCollector] = {}
        self.logger = logger.getChild("MetricsAggregator")
    
    def register_collector(self, name: str, collector: MetricsCollector):
        """Register a metrics collector"""
        self.collectors[name] = collector
        self.logger.info(f"Registered metrics collector: {name}")
    
    def get_aggregated_summary(self) -> Dict[str, Any]:
        """Get aggregated summary from all collectors"""
        aggregated = {
            "collectors": {},
            "global_summary": {
                "total_collectors": len(self.collectors),
                "total_unique_metrics": 0,
                "total_data_points": 0
            }
        }
        
        for name, collector in self.collectors.items():
            collector_metrics = collector.get_all_metrics()
            system_metrics = collector.get_system_metrics()
            
            aggregated["collectors"][name] = {
                "metrics": collector_metrics,
                "system": system_metrics
            }
            
            # Update global summary
            aggregated["global_summary"]["total_unique_metrics"] += len(collector_metrics)
            aggregated["global_summary"]["total_data_points"] += system_metrics.get("memory_usage", {}).get("total_data_points", 0)
        
        return aggregated
    
    def find_performance_issues(self) -> List[Dict[str, Any]]:
        """Analyze metrics to find potential performance issues"""
        issues = []
        
        for collector_name, collector in self.collectors.items():
            metrics = collector.get_all_metrics()
            
            for metric_name, summary in metrics.items():
                if "error" in summary:
                    continue
                
                # Check for high timer values
                if summary.get("type") == "timer":
                    avg_ms = summary.get("timer_avg_ms", 0)
                    p95_ms = summary.get("timer_p95_ms", 0)
                    
                    if avg_ms > 1000:  # Average over 1 second
                        issues.append({
                            "type": "high_latency",
                            "collector": collector_name,
                            "metric": metric_name,
                            "severity": "high" if avg_ms > 5000 else "medium",
                            "message": f"High average latency: {avg_ms:.1f}ms",
                            "value": avg_ms
                        })
                    
                    if p95_ms > 2000:  # P95 over 2 seconds
                        issues.append({
                            "type": "latency_spikes",
                            "collector": collector_name,
                            "metric": metric_name,
                            "severity": "medium",
                            "message": f"High P95 latency: {p95_ms:.1f}ms",
                            "value": p95_ms
                        })
                
                # Check for low cache hit rates
                if "cache_hit_rate" in metric_name:
                    hit_rate = summary.get("latest_value", 1.0)
                    if hit_rate < 0.5:  # Less than 50% hit rate
                        issues.append({
                            "type": "low_cache_performance",
                            "collector": collector_name,
                            "metric": metric_name,
                            "severity": "medium",
                            "message": f"Low cache hit rate: {hit_rate:.1%}",
                            "value": hit_rate
                        })
                
                # Check for error rate increases
                if "error" in metric_name and summary.get("type") == "counter":
                    rate = collector.calculate_rate(metric_name, 300)  # 5 minute window
                    if rate > 0.1:  # More than 0.1 errors per second
                        issues.append({
                            "type": "high_error_rate",
                            "collector": collector_name,
                            "metric": metric_name,
                            "severity": "high",
                            "message": f"High error rate: {rate:.2f} errors/sec",
                            "value": rate
                        })
        
        # Sort by severity
        severity_order = {"high": 0, "medium": 1, "low": 2}
        issues.sort(key=lambda x: severity_order.get(x["severity"], 3))
        
        return issues
    
    def get_health_indicators(self) -> Dict[str, Any]:
        """Get key health indicators from metrics"""
        indicators = {
            "overall_health": "healthy",
            "indicators": {}
        }
        
        issues = self.find_performance_issues()
        high_severity_issues = [i for i in issues if i["severity"] == "high"]
        medium_severity_issues = [i for i in issues if i["severity"] == "medium"]
        
        if high_severity_issues:
            indicators["overall_health"] = "unhealthy"
        elif medium_severity_issues:
            indicators["overall_health"] = "degraded"
        
        # Collect key indicators
        for collector_name, collector in self.collectors.items():
            metrics = collector.get_all_metrics()
            
            # Response time indicator
            response_times = [
                summary.get("timer_avg_ms", 0) for summary in metrics.values()
                if summary.get("type") == "timer" and "response" in summary.get("name", "")
            ]
            if response_times:
                indicators["indicators"]["avg_response_time_ms"] = sum(response_times) / len(response_times)
            
            # Throughput indicator
            throughput_metrics = [
                collector.calculate_rate(name, 60) for name in metrics.keys()
                if "request" in name or "operation" in name
            ]
            if throughput_metrics:
                indicators["indicators"]["operations_per_second"] = sum(throughput_metrics)
            
            # Error rate indicator
            error_rates = [
                collector.calculate_rate(name, 300) for name in metrics.keys()
                if "error" in name and metrics[name].get("type") == "counter"
            ]
            if error_rates:
                indicators["indicators"]["errors_per_second"] = sum(error_rates)
        
        indicators["issues_summary"] = {
            "high_severity": len(high_severity_issues),
            "medium_severity": len(medium_severity_issues),
            "total_issues": len(issues)
        }
        
        return indicators


# Global metrics instance
global_metrics = MetricsCollector()
metrics_aggregator = MetricsAggregator()

# Register global collector
metrics_aggregator.register_collector("global", global_metrics)


def get_global_metrics() -> MetricsCollector:
    """Get the global metrics collector instance"""
    return global_metrics


def get_metrics_aggregator() -> MetricsAggregator:
    """Get the metrics aggregator instance"""
    return metrics_aggregator


def main():
    """Main function for module testing"""
    print("Testing Metrics Collection...")
    
    # Test metrics collector
    metrics = MetricsCollector()
    print("✅ Created MetricsCollector")
    
    # Test metric operations
    metrics.increment_counter("test_counter", 5)
    metrics.increment_counter("test_counter", 3)  # Should be 8 total
    metrics.set_gauge("test_gauge", 42.5)
    metrics.record_timer("test_timer", 123.4)
    metrics.record_timer("test_timer", 98.7)
    metrics.record_histogram("test_histogram", 15.2)
    
    # Test metric summaries
    counter_summary = metrics.get_metric_summary("test_counter")
    gauge_summary = metrics.get_metric_summary("test_gauge")
    timer_summary = metrics.get_metric_summary("test_timer")
    
    print(f"✅ Counter: {counter_summary['latest_value']} (rate: {counter_summary.get('rate_per_second', 'N/A')})")
    print(f"✅ Gauge: {gauge_summary['latest_value']}")
    print(f"✅ Timer: avg={timer_summary.get('timer_avg_ms', 0):.1f}ms, count={timer_summary.get('timer_count', 0)}")
    
    # Test percentile calculation
    test_values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    p50 = metrics._percentile(test_values, 50)
    p95 = metrics._percentile(test_values, 95)
    print(f"✅ Percentile test: P50={p50}, P95={p95}")
    
    # Test system metrics
    system_metrics = metrics.get_system_metrics()
    print(f"✅ System metrics: {system_metrics['total_metrics_collected']} collected")
    
    # Test metrics aggregator
    aggregator = MetricsAggregator()
    aggregator.register_collector("test", metrics)
    
    aggregated = aggregator.get_aggregated_summary()
    print(f"✅ Aggregated metrics: {aggregated['global_summary']['total_unique_metrics']} unique metrics")
    
    # Test performance issue detection
    issues = aggregator.find_performance_issues()
    print(f"✅ Performance analysis: {len(issues)} issues found")
    
    # Test export functionality
    try:
        json_export = metrics.export_metrics("json")
        print(f"✅ JSON export: {len(json_export)} characters")
        
        prometheus_export = metrics.export_metrics("prometheus")
        print(f"✅ Prometheus export: {len(prometheus_export)} characters")
    except Exception as e:
        print(f"⚠️  Export test failed: {e}")
    
    print("🎉 All Metrics Collection tests passed!")


if __name__ == "__main__":
    main()