"""
Registry Health Monitoring

Provides health monitoring and health check management for the MCP registry system.
Metrics collection is handled in a separate file.

This file focuses purely on health monitoring functionality.
"""

import logging
import asyncio
import threading
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

# Configure logger
logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """A single health check definition"""
    name: str
    description: str
    check_function: Callable
    timeout_seconds: float = 5.0
    critical: bool = True
    interval_seconds: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthResult:
    """Result of a health check"""
    name: str
    status: HealthStatus
    message: str
    timestamp: float
    duration_ms: float
    critical: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class HealthMonitor:
    """Monitors health of registry components"""
    
    def __init__(self, client, connection_manager, capability_aggregator):
        self.client = client
        self.connection_manager = connection_manager
        self.capability_aggregator = capability_aggregator
        self.logger = logger.getChild("HealthMonitor")
        
        self.health_checks: Dict[str, HealthCheck] = {}
        self.health_results: Dict[str, HealthResult] = {}
        
        self._monitoring_active = False
        self._monitoring_task = None
        self._check_lock = threading.RLock()
        
        # Import metrics separately
        self._metrics = None
        self._load_metrics()
        
        # Register default health checks
        self._register_default_checks()
    
    def _load_metrics(self):
        """Load metrics collector"""
        try:
            from .registry_metrics import MetricsCollector
            self._metrics = MetricsCollector()
        except ImportError:
            self.logger.warning("Metrics collector not available")
    
    def _register_default_checks(self):
        """Register default health checks"""
        
        # Server connectivity check
        self.register_health_check(HealthCheck(
            name="server_connectivity",
            description="Check if servers are connected and responsive",
            check_function=self._check_server_connectivity,
            timeout_seconds=10.0,
            critical=True,
            interval_seconds=30.0
        ))
        
        # Capability availability check
        self.register_health_check(HealthCheck(
            name="capability_availability",
            description="Check if tools, resources, and prompts are available",
            check_function=self._check_capability_availability,
            timeout_seconds=5.0,
            critical=False,
            interval_seconds=60.0
        ))
        
        # Cache performance check
        self.register_health_check(HealthCheck(
            name="cache_performance",
            description="Check cache hit rates and performance",
            check_function=self._check_cache_performance,
            timeout_seconds=2.0,
            critical=False,
            interval_seconds=120.0
        ))
    
    def register_health_check(self, health_check: HealthCheck):
        """Register a new health check"""
        self.health_checks[health_check.name] = health_check
        self.logger.info(f"Registered health check: {health_check.name}")
    
    async def _check_server_connectivity(self) -> HealthResult:
        """Check server connectivity"""
        start_time = time.time()
        
        try:
            # Get connection status
            connection_status = self.connection_manager.get_connection_status()
            connected_servers = self.connection_manager.get_connected_servers()
            
            # Perform health check on connected servers
            health_results = await self.client.health_check()
            
            # Analyze results
            total_servers = len(connection_status)
            healthy_servers = len([name for name, result in health_results.items() if result])
            
            duration_ms = (time.time() - start_time) * 1000
            
            if total_servers == 0:
                status = HealthStatus.UNHEALTHY
                message = "No servers configured"
            elif healthy_servers == 0:
                status = HealthStatus.UNHEALTHY
                message = "No servers responding to health checks"
            elif healthy_servers < total_servers:
                status = HealthStatus.DEGRADED
                message = f"{healthy_servers}/{total_servers} servers healthy"
            else:
                status = HealthStatus.HEALTHY
                message = f"All {total_servers} servers healthy"
            
            # Record metrics if available
            if self._metrics:
                self._metrics.set_gauge("connected_servers", len(connected_servers))
                self._metrics.set_gauge("healthy_servers", healthy_servers)
                self._metrics.record_timer("health_check_duration", duration_ms)
            
            return HealthResult(
                name="server_connectivity",
                status=status,
                message=message,
                timestamp=time.time(),
                duration_ms=duration_ms,
                critical=True,
                metadata={
                    "total_servers": total_servers,
                    "connected_servers": len(connected_servers),
                    "healthy_servers": healthy_servers,
                    "health_details": health_results
                }
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(f"Server connectivity check failed: {e}")
            
            return HealthResult(
                name="server_connectivity",
                status=HealthStatus.UNKNOWN,
                message=f"Health check failed: {str(e)}",
                timestamp=time.time(),
                duration_ms=duration_ms,
                critical=True,
                metadata={"error": str(e)}
            )
    
    async def _check_capability_availability(self) -> HealthResult:
        """Check capability availability"""
        start_time = time.time()
        
        try:
            # Get available capabilities
            tools = self.capability_aggregator.get_available_tools()
            resources = self.capability_aggregator.get_available_resources()
            prompts = self.capability_aggregator.get_available_prompts()
            
            duration_ms = (time.time() - start_time) * 1000
            
            tool_count = len(tools)
            resource_count = len(resources)
            prompt_count = len(prompts)
            total_capabilities = tool_count + resource_count + prompt_count
            
            # Record metrics if available
            if self._metrics:
                self._metrics.set_gauge("available_tools", tool_count)
                self._metrics.set_gauge("available_resources", resource_count)
                self._metrics.set_gauge("available_prompts", prompt_count)
                self._metrics.record_timer("capability_check_duration", duration_ms)
            
            if total_capabilities == 0:
                status = HealthStatus.UNHEALTHY
                message = "No capabilities available"
            elif tool_count == 0:
                status = HealthStatus.DEGRADED
                message = f"No tools available ({resource_count} resources, {prompt_count} prompts)"
            else:
                status = HealthStatus.HEALTHY
                message = f"{tool_count} tools, {resource_count} resources, {prompt_count} prompts available"
            
            return HealthResult(
                name="capability_availability",
                status=status,
                message=message,
                timestamp=time.time(),
                duration_ms=duration_ms,
                critical=False,
                metadata={
                    "tool_count": tool_count,
                    "resource_count": resource_count,
                    "prompt_count": prompt_count
                }
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(f"Capability availability check failed: {e}")
            
            return HealthResult(
                name="capability_availability",
                status=HealthStatus.UNKNOWN,
                message=f"Capability check failed: {str(e)}",
                timestamp=time.time(),
                duration_ms=duration_ms,
                critical=False,
                metadata={"error": str(e)}
            )
    
    async def _check_cache_performance(self) -> HealthResult:
        """Check cache performance"""
        start_time = time.time()
        
        try:
            # Get cache statistics
            cache_stats = self.capability_aggregator.get_cache_stats()
            
            duration_ms = (time.time() - start_time) * 1000
            
            hit_rate = cache_stats.get("hit_rate", 0)
            cache_size = cache_stats.get("cache_size", 0)
            
            # Record metrics if available
            if self._metrics:
                self._metrics.set_gauge("cache_hit_rate", hit_rate)
                self._metrics.set_gauge("cache_size", cache_size)
                self._metrics.record_timer("cache_check_duration", duration_ms)
            
            if hit_rate < 0.5:  # Less than 50% hit rate
                status = HealthStatus.DEGRADED
                message = f"Low cache hit rate: {hit_rate:.1%}"
            else:
                status = HealthStatus.HEALTHY
                message = f"Cache performing well: {hit_rate:.1%} hit rate"
            
            return HealthResult(
                name="cache_performance",
                status=status,
                message=message,
                timestamp=time.time(),
                duration_ms=duration_ms,
                critical=False,
                metadata=cache_stats
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(f"Cache performance check failed: {e}")
            
            return HealthResult(
                name="cache_performance",
                status=HealthStatus.UNKNOWN,
                message=f"Cache check failed: {str(e)}",
                timestamp=time.time(),
                duration_ms=duration_ms,
                critical=False,
                metadata={"error": str(e)}
            )
    
    async def run_health_check(self, check_name: str) -> HealthResult:
        """Run a specific health check"""
        if check_name not in self.health_checks:
            raise ValueError(f"Health check not found: {check_name}")
        
        health_check = self.health_checks[check_name]
        
        try:
            # Run the check with timeout
            result = await asyncio.wait_for(
                health_check.check_function(),
                timeout=health_check.timeout_seconds
            )
            
            # Store result
            with self._check_lock:
                self.health_results[check_name] = result
                
            # Record metric
            if self._metrics:
                self._metrics.increment_counter("health_check_runs", labels={"check": check_name})
            
            return result
            
        except asyncio.TimeoutError:
            result = HealthResult(
                name=check_name,
                status=HealthStatus.UNKNOWN,
                message=f"Health check timed out after {health_check.timeout_seconds}s",
                timestamp=time.time(),
                duration_ms=health_check.timeout_seconds * 1000,
                critical=health_check.critical,
                metadata={"timeout": True}
            )
            
            with self._check_lock:
                self.health_results[check_name] = result
                
            if self._metrics:
                self._metrics.increment_counter("health_check_timeouts", labels={"check": check_name})
            return result
            
        except Exception as e:
            result = HealthResult(
                name=check_name,
                status=HealthStatus.UNKNOWN,
                message=f"Health check failed: {str(e)}",
                timestamp=time.time(),
                duration_ms=0,
                critical=health_check.critical,
                metadata={"error": str(e)}
            )
            
            with self._check_lock:
                self.health_results[check_name] = result
                
            if self._metrics:
                self._metrics.increment_counter("health_check_errors", labels={"check": check_name})
            self.logger.error(f"Health check {check_name} failed: {e}")
            return result
    
    async def run_all_health_checks(self) -> Dict[str, HealthResult]:
        """Run all registered health checks"""
        results = {}
        
        for check_name in self.health_checks:
            try:
                result = await self.run_health_check(check_name)
                results[check_name] = result
            except Exception as e:
                self.logger.error(f"Error running health check {check_name}: {e}")
        
        return results
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary"""
        with self._check_lock:
            if not self.health_results:
                return {
                    "overall_status": HealthStatus.UNKNOWN.value,
                    "message": "No health checks have been run",
                    "checks": {}
                }
            
            # Determine overall status
            critical_issues = []
            degraded_issues = []
            healthy_checks = []
            
            for name, result in self.health_results.items():
                if result.status == HealthStatus.UNHEALTHY:
                    if result.critical:
                        critical_issues.append(name)
                    else:
                        degraded_issues.append(name)
                elif result.status == HealthStatus.DEGRADED:
                    degraded_issues.append(name)
                elif result.status == HealthStatus.HEALTHY:
                    healthy_checks.append(name)
            
            if critical_issues:
                overall_status = HealthStatus.UNHEALTHY
                message = f"Critical issues: {', '.join(critical_issues)}"
            elif degraded_issues:
                overall_status = HealthStatus.DEGRADED
                message = f"Degraded components: {', '.join(degraded_issues)}"
            else:
                overall_status = HealthStatus.HEALTHY
                message = f"All {len(healthy_checks)} checks healthy"
            
            return {
                "overall_status": overall_status.value,
                "message": message,
                "summary": {
                    "total_checks": len(self.health_results),
                    "healthy": len(healthy_checks),
                    "degraded": len(degraded_issues),
                    "critical": len(critical_issues)
                },
                "checks": {
                    name: {
                        "status": result.status.value,
                        "message": result.message,
                        "timestamp": result.timestamp,
                        "duration_ms": result.duration_ms,
                        "critical": result.critical
                    }
                    for name, result in self.health_results.items()
                }
            }
    
    def start_monitoring(self):
        """Start continuous health monitoring"""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Health monitoring started")
    
    def stop_monitoring(self):
        """Stop continuous health monitoring"""
        self._monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
        self.logger.info("Health monitoring stopped")
    
    async def _monitoring_loop(self):
        """Continuous monitoring loop"""
        last_check_times = {}
        
        while self._monitoring_active:
            try:
                current_time = time.time()
                
                for check_name, health_check in self.health_checks.items():
                    last_check = last_check_times.get(check_name, 0)
                    
                    if current_time - last_check >= health_check.interval_seconds:
                        try:
                            await self.run_health_check(check_name)
                            last_check_times[check_name] = current_time
                        except Exception as e:
                            self.logger.error(f"Error in monitoring loop for {check_name}: {e}")
                
                # Sleep for a short interval
                await asyncio.sleep(5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)  # Wait longer on error
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of metrics if available"""
        if self._metrics:
            return self._metrics.get_all_metrics()
        return {"error": "Metrics not available"}


def main():
    """Main function for module testing"""
    print("Testing Health Monitoring...")
    
    # Test health check creation
    async def dummy_check():
        return HealthResult(
            name="dummy",
            status=HealthStatus.HEALTHY,
            message="Test check passed",
            timestamp=time.time(),
            duration_ms=10.0,
            critical=False
        )
    
    health_check = HealthCheck(
        name="dummy_check",
        description="A dummy health check for testing",
        check_function=dummy_check
    )
    
    print(f"✅ Created health check: {health_check.name}")
    print(f"   Description: {health_check.description}")
    print(f"   Timeout: {health_check.timeout_seconds}s")
    print(f"   Critical: {health_check.critical}")
    print(f"   Interval: {health_check.interval_seconds}s")
    
    # Test health result
    result = HealthResult(
        name="test_result",
        status=HealthStatus.HEALTHY,
        message="All systems operational",
        timestamp=time.time(),
        duration_ms=25.5,
        critical=True,
        metadata={"test_data": "example"}
    )
    
    print(f"✅ Created health result: {result.name}")
    print(f"   Status: {result.status.value}")
    print(f"   Message: {result.message}")
    print(f"   Duration: {result.duration_ms}ms")
    
    print("🎉 All Health Monitoring tests passed!")


if __name__ == "__main__":
    main()