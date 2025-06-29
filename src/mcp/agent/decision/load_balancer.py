"""
Load Balancer with Circuit Breakers
Advanced load balancing for multiple providers with health monitoring.
"""

import time
import asyncio
import random
from collections import defaultdict, deque
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import structlog


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ProviderMetrics:
    """Real-time provider metrics."""
    success_rate: float = 1.0
    avg_response_time: float = 0.0
    current_load: int = 0
    error_count: int = 0
    last_error_time: float = 0.0
    circuit_breaker_state: CircuitBreakerState = CircuitBreakerState.CLOSED
    
    # Rolling windows for metrics
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    success_history: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def update_response_time(self, response_time: float):
        """Update response time metrics."""
        self.response_times.append(response_time)
        if self.response_times:
            self.avg_response_time = sum(self.response_times) / len(self.response_times)
    
    def update_success_rate(self, success: bool):
        """Update success rate metrics."""
        self.success_history.append(success)
        if self.success_history:
            self.success_rate = sum(self.success_history) / len(self.success_history)


class CircuitBreaker:
    """Circuit breaker for provider health management."""
    
    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0, 
                 success_threshold: int = 3):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.state = CircuitBreakerState.CLOSED
        
        self.logger = structlog.get_logger("circuit_breaker")
    
    def call_succeeded(self):
        """Record successful call."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._close_circuit()
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0
    
    def call_failed(self):
        """Record failed call."""
        self.failure_count += 1
        self.success_count = 0
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self._open_circuit()
    
    def can_execute(self) -> bool:
        """Check if calls are allowed."""
        current_time = time.time()
        
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if current_time - self.last_failure_time >= self.timeout:
                self._half_open_circuit()
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def _open_circuit(self):
        """Open the circuit breaker."""
        self.state = CircuitBreakerState.OPEN
        self.logger.warning("Circuit breaker opened", failure_count=self.failure_count)
    
    def _close_circuit(self):
        """Close the circuit breaker."""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.logger.info("Circuit breaker closed")
    
    def _half_open_circuit(self):
        """Half-open the circuit breaker."""
        self.state = CircuitBreakerState.HALF_OPEN
        self.success_count = 0
        self.logger.info("Circuit breaker half-opened")
    
    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self.state


class LoadBalancingStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RESPONSE_TIME = "response_time"
    RANDOM = "random"
    INTELLIGENT = "intelligent"


class LoadBalancer:
    """
    Advanced load balancer with circuit breakers and health monitoring.
    
    Features:
    - Multiple load balancing strategies
    - Circuit breaker pattern for fault tolerance
    - Real-time health monitoring
    - Provider metrics collection
    - Automatic failover
    - Security controls
    """
    
    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.INTELLIGENT):
        self.logger = structlog.get_logger("load_balancer")
        
        # Configuration
        self.strategy = strategy
        self.max_connections_per_provider = 10
        self.health_check_interval = 30.0
        self.response_time_threshold = 5.0
        
        # State tracking
        self.provider_metrics: Dict[str, ProviderMetrics] = defaultdict(ProviderMetrics)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.active_requests: Dict[str, Set[str]] = defaultdict(set)
        self.request_queue = asyncio.Queue()
        
        # Round robin state
        self.round_robin_index = 0
        
        # Health monitoring
        self.health_monitor_task = None
        self.is_monitoring = False
    
    async def filter_healthy_providers(
        self, 
        available_providers: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Filter providers based on health status."""
        healthy_providers = {}
        
        for name, provider in available_providers.items():
            if not provider.is_available():
                continue
            
            # Check circuit breaker
            if not self._is_provider_healthy(name):
                self.logger.warning("Provider unhealthy, skipping", provider=name)
                continue
            
            # Check load limits
            current_load = self.provider_metrics[name].current_load
            if current_load >= self.max_connections_per_provider:
                self.logger.warning("Provider at capacity, skipping", 
                                  provider=name, load=current_load)
                continue
            
            healthy_providers[name] = provider
        
        return healthy_providers
    
    async def select_provider_with_load_balancing(
        self,
        healthy_providers: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> Optional[str]:
        """Select provider using configured load balancing strategy."""
        
        if not healthy_providers:
            return None
        
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_selection(healthy_providers)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_selection(healthy_providers)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_selection(healthy_providers)
        elif self.strategy == LoadBalancingStrategy.RESPONSE_TIME:
            return self._response_time_selection(healthy_providers)
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            return self._random_selection(healthy_providers)
        else:  # INTELLIGENT
            return self._intelligent_selection(healthy_providers, context)
    
    def _is_provider_healthy(self, provider_name: str) -> bool:
        """Check if provider is healthy based on circuit breaker."""
        if provider_name not in self.circuit_breakers:
            self.circuit_breakers[provider_name] = CircuitBreaker()
        
        circuit_breaker = self.circuit_breakers[provider_name]
        is_healthy = circuit_breaker.can_execute()
        
        # Update metrics
        metrics = self.provider_metrics[provider_name]
        metrics.circuit_breaker_state = circuit_breaker.get_state()
        
        return is_healthy
    
    def _round_robin_selection(self, providers: Dict[str, Any]) -> str:
        """Round robin provider selection."""
        provider_names = list(providers.keys())
        if not provider_names:
            return None
        
        selected = provider_names[self.round_robin_index % len(provider_names)]
        self.round_robin_index += 1
        
        self.logger.debug("Round robin selection", provider=selected)
        return selected
    
    def _least_connections_selection(self, providers: Dict[str, Any]) -> str:
        """Select provider with least active connections."""
        if not providers:
            return None
        
        selected = min(
            providers.keys(),
            key=lambda p: self.provider_metrics[p].current_load
        )
        
        self.logger.debug("Least connections selection", 
                         provider=selected, 
                         load=self.provider_metrics[selected].current_load)
        return selected
    
    def _weighted_round_robin_selection(self, providers: Dict[str, Any]) -> str:
        """Weighted selection based on provider performance."""
        if not providers:
            return None
        
        weights = {}
        for provider_name in providers:
            metrics = self.provider_metrics[provider_name]
            # Higher success rate and lower response time = higher weight
            weight = metrics.success_rate / max(metrics.avg_response_time, 0.1)
            weights[provider_name] = weight
        
        # Weighted random selection
        total_weight = sum(weights.values())
        if total_weight == 0:
            return random.choice(list(providers.keys()))
        
        r = random.uniform(0, total_weight)
        cumulative = 0
        for provider_name, weight in weights.items():
            cumulative += weight
            if r <= cumulative:
                self.logger.debug("Weighted selection", 
                                provider=provider_name, weight=weight)
                return provider_name
        
        return list(providers.keys())[-1]
    
    def _response_time_selection(self, providers: Dict[str, Any]) -> str:
        """Select provider with best response time."""
        if not providers:
            return None
        
        selected = min(
            providers.keys(),
            key=lambda p: self.provider_metrics[p].avg_response_time or 0.1
        )
        
        self.logger.debug("Response time selection", 
                         provider=selected,
                         response_time=self.provider_metrics[selected].avg_response_time)
        return selected
    
    def _random_selection(self, providers: Dict[str, Any]) -> str:
        """Random provider selection."""
        if not providers:
            return None
        
        selected = random.choice(list(providers.keys()))
        self.logger.debug("Random selection", provider=selected)
        return selected
    
    def _intelligent_selection(
        self, 
        providers: Dict[str, Any], 
        context: Dict[str, Any] = None
    ) -> str:
        """Intelligent selection considering multiple factors."""
        if not providers:
            return None
        
        context = context or {}
        scores = {}
        
        for provider_name in providers:
            metrics = self.provider_metrics[provider_name]
            
            # Calculate composite score
            success_score = metrics.success_rate * 0.4
            response_time_score = max(0, 1.0 - metrics.avg_response_time / 5.0) * 0.3
            load_score = max(0, 1.0 - metrics.current_load / self.max_connections_per_provider) * 0.2
            
            # Context-based adjustments
            context_score = 0.1
            if context.get('requires_high_quality') and 'external' in provider_name.lower():
                context_score = 0.15
            elif context.get('cost_sensitive') and 'local' in provider_name.lower():
                context_score = 0.15
            
            total_score = success_score + response_time_score + load_score + context_score
            scores[provider_name] = total_score
        
        selected = max(scores, key=scores.get)
        
        self.logger.debug("Intelligent selection", 
                         provider=selected, 
                         score=scores[selected],
                         all_scores=scores)
        return selected
    
    async def record_request_start(self, provider_name: str, request_id: str):
        """Record the start of a request."""
        self.active_requests[provider_name].add(request_id)
        self.provider_metrics[provider_name].current_load = len(
            self.active_requests[provider_name]
        )
        
        self.logger.debug("Request started", 
                         provider=provider_name, 
                         request_id=request_id,
                         load=self.provider_metrics[provider_name].current_load)
    
    async def record_request_result(
        self,
        provider_name: str,
        request_id: str,
        success: bool,
        response_time: float
    ):
        """Record request completion result."""
        
        # Remove from active requests
        if request_id in self.active_requests[provider_name]:
            self.active_requests[provider_name].remove(request_id)
        
        # Update metrics
        metrics = self.provider_metrics[provider_name]
        metrics.current_load = len(self.active_requests[provider_name])
        metrics.update_response_time(response_time)
        metrics.update_success_rate(success)
        
        # Update circuit breaker
        circuit_breaker = self.circuit_breakers.get(provider_name)
        if circuit_breaker:
            if success:
                circuit_breaker.call_succeeded()
            else:
                circuit_breaker.call_failed()
                metrics.error_count += 1
                metrics.last_error_time = time.time()
        
        self.logger.debug("Request completed", 
                         provider=provider_name,
                         request_id=request_id,
                         success=success,
                         response_time=response_time,
                         load=metrics.current_load)
    
    def get_provider_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all providers."""
        health_status = {}
        
        for provider_name, metrics in self.provider_metrics.items():
            circuit_breaker = self.circuit_breakers.get(provider_name)
            
            health_status[provider_name] = {
                'success_rate': metrics.success_rate,
                'avg_response_time': metrics.avg_response_time,
                'current_load': metrics.current_load,
                'error_count': metrics.error_count,
                'circuit_breaker_state': metrics.circuit_breaker_state.value,
                'is_healthy': self._is_provider_healthy(provider_name),
                'last_error_time': metrics.last_error_time
            }
        
        return health_status
    
    async def start_health_monitoring(self):
        """Start continuous health monitoring."""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.health_monitor_task = asyncio.create_task(self._health_monitor_loop())
        self.logger.info("Health monitoring started")
    
    async def stop_health_monitoring(self):
        """Stop health monitoring."""
        self.is_monitoring = False
        if self.health_monitor_task:
            self.health_monitor_task.cancel()
            try:
                await self.health_monitor_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Health monitoring stopped")
    
    async def _health_monitor_loop(self):
        """Continuous health monitoring loop."""
        while self.is_monitoring:
            try:
                await self._check_provider_health()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Health monitoring error", error=str(e))
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def _check_provider_health(self):
        """Check health of all providers."""
        for provider_name, metrics in self.provider_metrics.items():
            # Check for stale providers (no recent activity)
            if (time.time() - metrics.last_error_time > 300 and 
                metrics.error_count > 0):
                # Reset error count for stale providers
                metrics.error_count = 0
                self.logger.debug("Reset error count for stale provider", 
                                provider=provider_name)
            
            # Log health status
            if metrics.success_rate < 0.8:
                self.logger.warning("Provider health degraded",
                                  provider=provider_name,
                                  success_rate=metrics.success_rate,
                                  avg_response_time=metrics.avg_response_time)
    
    def configure_strategy(self, strategy: LoadBalancingStrategy):
        """Configure load balancing strategy."""
        self.strategy = strategy
        self.logger.info("Load balancing strategy configured", strategy=strategy.value)
    
    def reset_metrics(self, provider_name: str = None):
        """Reset metrics for a provider or all providers."""
        if provider_name:
            if provider_name in self.provider_metrics:
                self.provider_metrics[provider_name] = ProviderMetrics()
                self.logger.info("Reset metrics for provider", provider=provider_name)
        else:
            self.provider_metrics.clear()
            self.circuit_breakers.clear()
            self.active_requests.clear()
            self.logger.info("Reset all provider metrics")


def main():
    """Main function for testing load balancer."""
    import asyncio
    import uuid
    
    async def test_load_balancer():
        print("🧪 Testing Load Balancer...")
        
        # Create load balancer
        lb = LoadBalancer(LoadBalancingStrategy.INTELLIGENT)
        
        # Mock providers
        class MockProvider:
            def __init__(self, name, available=True):
                self.name = name
                self._available = available
            
            def is_available(self):
                return self._available
        
        providers = {
            'external': MockProvider('external', True),
            'local': MockProvider('local', True),
            'backup': MockProvider('backup', True)
        }
        
        print("✅ Load balancer created")
        
        # Test health filtering
        healthy = await lb.filter_healthy_providers(providers)
        print(f"🏥 Healthy providers: {list(healthy.keys())}")
        
        # Test different selection strategies
        strategies = [
            LoadBalancingStrategy.ROUND_ROBIN,
            LoadBalancingStrategy.LEAST_CONNECTIONS,
            LoadBalancingStrategy.RANDOM,
            LoadBalancingStrategy.INTELLIGENT
        ]
        
        for strategy in strategies:
            lb.configure_strategy(strategy)
            selected = await lb.select_provider_with_load_balancing(healthy)
            print(f"📋 {strategy.value}: {selected}")
        
        # Test request tracking
        print("\n📊 Testing request tracking:")
        
        # Simulate requests
        request_ids = [str(uuid.uuid4()) for _ in range(5)]
        
        for i, req_id in enumerate(request_ids):
            provider = 'external' if i % 2 == 0 else 'local'
            await lb.record_request_start(provider, req_id)
            
            # Simulate processing time
            await asyncio.sleep(0.1)
            
            # Record completion
            success = random.choice([True, True, True, False])  # 75% success rate
            response_time = random.uniform(0.5, 2.0)
            
            await lb.record_request_result(provider, req_id, success, response_time)
            
            print(f"   Request {i+1}: {provider} - {'✅' if success else '❌'} ({response_time:.2f}s)")
        
        # Test health monitoring
        print("\n🏥 Provider health status:")
        health = lb.get_provider_health()
        for provider, status in health.items():
            print(f"   {provider}: {status['success_rate']:.2%} success, "
                  f"{status['avg_response_time']:.2f}s avg, "
                  f"{status['current_load']} load, "
                  f"CB: {status['circuit_breaker_state']}")
        
        # Test circuit breaker
        print("\n⚡ Testing circuit breaker:")
        
        # Simulate failures to trigger circuit breaker
        for i in range(6):
            req_id = str(uuid.uuid4())
            await lb.record_request_start('external', req_id)
            await lb.record_request_result('external', req_id, False, 1.0)
        
        # Check if circuit breaker opened
        health = lb.get_provider_health()
        cb_state = health['external']['circuit_breaker_state']
        print(f"   Circuit breaker state after failures: {cb_state}")
        
        print("\n🎉 Load balancer tests completed!")
    
    asyncio.run(test_load_balancer())


if __name__ == "__main__":
    main() 