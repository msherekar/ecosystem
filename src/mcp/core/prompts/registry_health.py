"""
Health Monitoring for Registry System

Provides health monitoring, performance tracking, and system diagnostics.
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List
from dataclasses import dataclass, field

from .events import get_event_emitter, emit_system_event

import logging
logger = logging.getLogger(__name__)


@dataclass
class HealthMetric:
    """Individual health metric data point"""
    name: str
    value: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class HealthMonitor:
    """Monitor registry health and performance"""
    
    def __init__(self, max_history: int = 1000):
        self._metrics = {
            "discovery_runs": 0,
            "experts_loaded": 0,
            "load_failures": 0,
            "validation_failures": 0,
            "last_discovery": None,
            "avg_load_time": 0.0,
            "error_rate": 0.0,
            "memory_usage": 0.0,
            "cpu_usage": 0.0
        }
        self._metric_history: List[HealthMetric] = []
        self._max_history = max_history
        self._lock = threading.Lock()
        self._events = get_event_emitter()
        
        # Health thresholds
        self._thresholds = {
            "error_rate_warning": 10.0,  # %
            "error_rate_critical": 25.0,  # %
            "load_time_warning": 2.0,  # seconds
            "load_time_critical": 5.0,  # seconds
        }
    
    def record_discovery(self, experts_found: int, duration: float):
        """Record discovery operation metrics"""
        with self._lock:
            self._metrics["discovery_runs"] += 1
            self._metrics["experts_loaded"] += experts_found
            self._metrics["last_discovery"] = datetime.now().isoformat()
            
            # Update average load time
            if experts_found > 0:
                current_avg = self._metrics["avg_load_time"]
                total_runs = self._metrics["discovery_runs"]
                self._metrics["avg_load_time"] = (
                    (current_avg * (total_runs - 1) + duration) / total_runs
                )
            
            # Add to history
            self._add_metric("discovery_duration", duration, {
                "experts_found": experts_found
            })
        
        # Check health and emit events
        self._check_health_thresholds("discovery", duration)
        
        logger.info(f"Discovery completed: {experts_found} experts in {duration:.2f}s")
    
    def record_load_failure(self, error_details: str = ""):
        """Record expert load failure"""
        with self._lock:
            self._metrics["load_failures"] += 1
            
            # Calculate error rate
            total_attempts = self._metrics["experts_loaded"] + self._metrics["load_failures"]
            if total_attempts > 0:
                self._metrics["error_rate"] = (
                    self._metrics["load_failures"] / total_attempts
                ) * 100
            
            # Add to history
            self._add_metric("load_failure", 1, {
                "error_details": error_details
            })
        
        # Emit error event
        if self._events:
            emit_system_event("registry_load_failure", {
                "error_details": error_details,
                "total_failures": self._metrics["load_failures"],
                "error_rate": self._metrics["error_rate"]
            })
        
        logger.error(f"Expert load failure: {error_details}")
    
    def record_validation_failure(self, expert_name: str = "", error_count: int = 1):
        """Record validation failure"""
        with self._lock:
            self._metrics["validation_failures"] += error_count
            
            # Add to history
            self._add_metric("validation_failure", error_count, {
                "expert_name": expert_name
            })
        
        logger.warning(f"Validation failure for {expert_name}: {error_count} errors")
    
    def record_system_metric(self, metric_name: str, value: float, metadata: Dict[str, Any] = None):
        """Record generic system metric"""
        with self._lock:
            self._metrics[metric_name] = value
            self._add_metric(metric_name, value, metadata or {})
    
    def _add_metric(self, name: str, value: float, metadata: Dict[str, Any]):
        """Add metric to history"""
        metric = HealthMetric(
            name=name,
            value=value,
            timestamp=datetime.now(),
            metadata=metadata
        )
        
        self._metric_history.append(metric)
        
        # Trim history if needed
        if len(self._metric_history) > self._max_history:
            self._metric_history = self._metric_history[-self._max_history:]
    
    def _check_health_thresholds(self, operation: str, value: float):
        """Check if metrics exceed health thresholds"""
        health_issues = []
        
        # Check error rate
        error_rate = self._metrics["error_rate"]
        if error_rate >= self._thresholds["error_rate_critical"]:
            health_issues.append(f"Critical error rate: {error_rate:.1f}%")
        elif error_rate >= self._thresholds["error_rate_warning"]:
            health_issues.append(f"High error rate: {error_rate:.1f}%")
        
        # Check load time for discovery operations
        if operation == "discovery" and value >= self._thresholds["load_time_critical"]:
            health_issues.append(f"Critical discovery time: {value:.1f}s")
        elif operation == "discovery" and value >= self._thresholds["load_time_warning"]:
            health_issues.append(f"Slow discovery time: {value:.1f}s")
        
        # Emit health events if issues found
        if health_issues and self._events:
            emit_system_event("registry_health_warning", {
                "issues": health_issues,
                "operation": operation,
                "value": value,
                "timestamp": datetime.now().isoformat()
            })
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        with self._lock:
            # Calculate overall status
            error_rate = self._metrics["error_rate"]
            avg_load_time = self._metrics["avg_load_time"]
            
            if error_rate >= self._thresholds["error_rate_critical"] or \
               avg_load_time >= self._thresholds["load_time_critical"]:
                status = "critical"
            elif error_rate >= self._thresholds["error_rate_warning"] or \
                 avg_load_time >= self._thresholds["load_time_warning"]:
                status = "warning"
            else:
                status = "healthy"
            
            return {
                **self._metrics.copy(),
                "overall_status": status,
                "health_score": self._calculate_health_score(),
                "last_check": datetime.now().isoformat(),
                "metric_history_size": len(self._metric_history)
            }
    
    def _calculate_health_score(self) -> float:
        """Calculate health score (0-100)"""
        score = 100.0
        
        # Deduct for error rate
        error_rate = self._metrics["error_rate"]
        if error_rate > 0:
            score -= min(error_rate * 2, 50)  # Max 50 point deduction
        
        # Deduct for slow performance
        avg_load_time = self._metrics["avg_load_time"]
        if avg_load_time > 1.0:
            score -= min((avg_load_time - 1.0) * 10, 30)  # Max 30 point deduction
        
        return max(score, 0.0)
    
    def get_recent_metrics(self, minutes: int = 15) -> List[Dict[str, Any]]:
        """Get metrics from recent time period"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self._lock:
            recent_metrics = [
                metric.to_dict() for metric in self._metric_history
                if metric.timestamp >= cutoff_time
            ]
        
        return recent_metrics
    
    def reset_metrics(self):
        """Reset all metrics and history"""
        with self._lock:
            self._metrics = {
                "discovery_runs": 0,
                "experts_loaded": 0,
                "load_failures": 0,
                "validation_failures": 0,
                "last_discovery": None,
                "avg_load_time": 0.0,
                "error_rate": 0.0,
                "memory_usage": 0.0,
                "cpu_usage": 0.0
            }
            self._metric_history.clear()
        
        logger.info("Health metrics reset")


if __name__ == "__main__":
    # Test health monitoring
    print("Testing Health Monitor")
    
    monitor = HealthMonitor()
    
    # Test recording discovery
    monitor.record_discovery(experts_found=5, duration=1.2)
    
    # Test recording failures
    monitor.record_load_failure("Test error")
    monitor.record_validation_failure("test_expert", 2)
    
    # Test health status
    health = monitor.get_health_status()
    print(f"✓ Health status: {health['overall_status']}")
    print(f"✓ Health score: {health['health_score']:.1f}")
    print(f"✓ Error rate: {health['error_rate']:.1f}%")
    
    # Test recent metrics
    recent = monitor.get_recent_metrics(60)
    print(f"✓ Recent metrics: {len(recent)} entries")
    
    print("\n✅ Health monitor test completed!") 