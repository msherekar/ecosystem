"""
Advanced Load Balancer with Circuit Breakers
Provides intelligent provider selection and fault tolerance.
"""

import time
import random
import asyncio
import logging
from enum import Enum
from collections import defaultdict, deque
from typing import Dict, List, Any, Optional, Callable, Awaitable, Type
from dataclasses import dataclass


class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class LoadBalancerConfig:
    """Configuration for load balancer."""
    default_strategy: str = "weighted_round_robin"
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout: float = 60.0
    metrics_window_size: int = 100
    connection_tracking: bool = True


class CircuitBreaker:
    """Circuit breaker for provider fault tolerance."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
        self.logger = logging.getLogger("circuit_breaker")
        
    async def call(self, func: Callable[..., Awaitable], *args, **kwargs):
        """Execute function with circuit breaker protection."""
        
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                self.logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (
            self.last_failure_time and 
            time.time() - self.last_failure_time >= self.timeout
        )
    
    def _on_success(self):
        """Handle successful execution."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.logger.info("Circuit breaker reset to CLOSED after successful call")
        
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
    
    def _on_failure(self):
        """Handle failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'last_failure_time': self.last_failure_time,
            'failure_threshold': self.failure_threshold,
            'timeout': self.timeout
        }


class AdvancedLoadBalancer:
    """Advanced load balancer with multiple strategies and circuit breakers."""
    
    def __init__(self, config: LoadBalancerConfig = None):
        self.config = config or LoadBalancerConfig()
        self.logger = logging.getLogger("load_balancer")
        
        # Circuit breakers per provider
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Performance metrics
        self.provider_metrics: Dict[str, Dict[str, deque]] = defaultdict(
            lambda: {
                'response_times': deque(maxlen=self.config.metrics_window_size),
                'success_rates': deque(maxlen=self.config.metrics_window_size),
                'load_levels': deque(maxlen=50)
            }
        )
        
        # Connection tracking
        self.active_connections: Dict[str, int] = defaultdict(int)
        
        # Round robin state
        self._round_robin_index = 0
        
    def get_circuit_breaker(self, provider_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for provider."""
        if provider_name not in self.circuit_breakers:
            self.circuit_breakers[provider_name] = CircuitBreaker(
                failure_threshold=self.config.circuit_breaker_failure_threshold,
                timeout=self.config.circuit_breaker_timeout
            )
        return self.circuit_breakers[provider_name]
    
    async def select_provider(
        self, 
        available_providers: Dict[str, Any],
        strategy: str = None,
        context: Dict[str, Any] = None
    ) -> Optional[str]:
        """Select provider using specified strategy."""
        
        if not available_providers:
            return None
        
        strategy = strategy or self.config.default_strategy
        context = context or {}
        
        # Filter out providers with open circuit breakers
        healthy_providers = {}
        for name, provider in available_providers.items():
            circuit_breaker = self.get_circuit_breaker(name)
            if circuit_breaker.state != CircuitBreakerState.OPEN:
                healthy_providers[name] = provider
        
        if not healthy_providers:
            self.logger.warning("No healthy providers available")
            return None
        
        # Apply selection strategy
        try:
            if strategy == "round_robin":
                return self._round_robin_selection(healthy_providers)
            elif strategy == "weighted_round_robin":
                return self._weighted_round_robin_selection(healthy_providers)
            elif strategy == "least_connections":
                return self._least_connections_selection(healthy_providers)
            elif strategy == "response_time":
                return self._response_time_selection(healthy_providers)
            elif strategy == "random":
                return random.choice(list(healthy_providers.keys()))
            elif strategy == "priority":
                return self._priority_selection(healthy_providers, context)
            else:
                self.logger.warning(f"Unknown strategy {strategy}, using first available")
                return list(healthy_providers.keys())[0]
                
        except Exception as e:
            self.logger.error(f"Provider selection failed: {e}")
            return list(healthy_providers.keys())[0] if healthy_providers else None
    
    def _round_robin_selection(self, providers: Dict[str, Any]) -> str:
        """Simple round robin selection."""
        provider_list = list(providers.keys())
        selected = provider_list[self._round_robin_index % len(provider_list)]
        self._round_robin_index += 1
        return selected
    
    def _weighted_round_robin_selection(self, providers: Dict[str, Any]) -> str:
        """Weighted selection based on provider performance."""
        weights = {}
        
        for name in providers:
            metrics = self.provider_metrics[name]
            
            # Calculate weight based on success rate and response time
            success_rates = metrics['success_rates']
            response_times = metrics['response_times']
            
            if success_rates and response_times:
                avg_success_rate = sum(success_rates) / len(success_rates)
                avg_response_time = sum(response_times) / len(response_times)
                
                # Higher success rate and lower response time = higher weight
                weight = avg_success_rate / max(avg_response_time, 0.1)
            else:
                weight = 1.0  # Default weight for new providers
            
            weights[name] = max(weight, 0.1)  # Minimum weight
        
        # Weighted random selection
        total_weight = sum(weights.values())
        if total_weight == 0:
            return random.choice(list(providers.keys()))
        
        r = random.uniform(0, total_weight)
        cumulative = 0
        
        for name, weight in weights.items():
            cumulative += weight
            if r <= cumulative:
                return name
        
        return list(providers.keys())[-1]  # Fallback
    
    def _least_connections_selection(self, providers: Dict[str, Any]) -> str:
        """Select provider with least active connections."""
        return min(providers.keys(), key=lambda p: self.active_connections[p])
    
    def _response_time_selection(self, providers: Dict[str, Any]) -> str:
        """Select provider with best average response time."""
        best_provider = None
        best_response_time = float('inf')
        
        for name in providers:
            response_times = self.provider_metrics[name]['response_times']
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                if avg_response_time < best_response_time:
                    best_response_time = avg_response_time
                    best_provider = name
        
        return best_provider or list(providers.keys())[0]
    
    def _priority_selection(self, providers: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Select provider based on priority and context."""
        # This could be enhanced with context-aware logic
        priorities = context.get('provider_priorities', {})
        
        # Sort by priority (higher values first)
        sorted_providers = sorted(
            providers.keys(),
            key=lambda p: priorities.get(p, 0),
            reverse=True
        )
        
        # Return highest priority available provider
        return sorted_providers[0]
    
    async def execute_with_load_balancing(
        self,
        providers: Dict[str, Any],
        func_name: str,
        *args,
        strategy: str = None,
        context: Dict[str, Any] = None,
        **kwargs
    ):
        """Execute function with load balancing and circuit breaker protection."""
        
        selected_provider_name = await self.select_provider(
            providers, strategy, context
        )
        
        if not selected_provider_name:
            raise Exception("No healthy providers available")
        
        provider = providers[selected_provider_name]
        circuit_breaker = self.get_circuit_breaker(selected_provider_name)
        
        # Track active connections
        if self.config.connection_tracking:
            self.active_connections[selected_provider_name] += 1
        
        try:
            start_time = time.time()
            
            # Execute with circuit breaker protection
            func = getattr(provider, func_name)
            result = await circuit_breaker.call(func, *args, **kwargs)
            
            # Record successful execution
            execution_time = time.time() - start_time
            self._record_success(selected_provider_name, execution_time)
            
            return result, selected_provider_name
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._record_failure(selected_provider_name, execution_time)
            raise e
            
        finally:
            if self.config.connection_tracking:
                self.active_connections[selected_provider_name] -= 1
    
    def _record_success(self, provider_name: str, execution_time: float):
        """Record successful execution metrics."""
        metrics = self.provider_metrics[provider_name]
        metrics['response_times'].append(execution_time)
        metrics['success_rates'].append(1.0)
        if self.config.connection_tracking:
            metrics['load_levels'].append(self.active_connections[provider_name])
    
    def _record_failure(self, provider_name: str, execution_time: float):
        """Record failed execution metrics."""
        metrics = self.provider_metrics[provider_name]
        metrics['response_times'].append(execution_time)
        metrics['success_rates'].append(0.0)
        if self.config.connection_tracking:
            metrics['load_levels'].append(self.active_connections[provider_name])
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive load balancer metrics."""
        metrics = {}
        
        for provider_name, provider_metrics in self.provider_metrics.items():
            response_times = list(provider_metrics['response_times'])
            success_rates = list(provider_metrics['success_rates'])
            
            metrics[provider_name] = {
                'avg_response_time': sum(response_times) / len(response_times) if response_times else 0,
                'success_rate': sum(success_rates) / len(success_rates) if success_rates else 0,
                'active_connections': self.active_connections[provider_name],
                'circuit_breaker': self.circuit_breakers.get(provider_name, {}).get_status() if provider_name in self.circuit_breakers else None,
                'total_requests': len(response_times)
            }
        
        return metrics
    
    def reset_metrics(self):
        """Reset all metrics and circuit breakers."""
        self.provider_metrics.clear()
        self.active_connections.clear()
        self.circuit_breakers.clear()
        self._round_robin_index = 0
        self.logger.info("Load balancer metrics reset")


def main():
    """Test the load balancer individually."""
    import asyncio
    
    class MockProvider:
        def __init__(self, name: str, fail_rate: float = 0.0, response_time: float = 1.0):
            self.name = name
            self.fail_rate = fail_rate
            self.response_time = response_time
        
        async def test_method(self, *args, **kwargs):
            await asyncio.sleep(self.response_time)
            if random.random() < self.fail_rate:
                raise Exception(f"Mock failure from {self.name}")
            return f"Success from {self.name}"
        
        def is_available(self):
            return True
    
    async def test_load_balancer():
        print("🧪 Testing AdvancedLoadBalancer...")
        
        # Create load balancer
        config = LoadBalancerConfig(
            circuit_breaker_failure_threshold=3,
            circuit_breaker_timeout=5.0
        )
        lb = AdvancedLoadBalancer(config)
        print("✅ Load balancer initialized")
        
        # Create mock providers
        providers = {
            'fast': MockProvider('fast', fail_rate=0.1, response_time=0.1),
            'slow': MockProvider('slow', fail_rate=0.2, response_time=0.5),
            'unreliable': MockProvider('unreliable', fail_rate=0.8, response_time=0.2)
        }
        
        # Test different strategies
        strategies = ['round_robin', 'weighted_round_robin', 'least_connections', 'response_time', 'random']
        
        for strategy in strategies:
            print(f"\n🔄 Testing {strategy} strategy:")
            
            for i in range(5):
                try:
                    result, selected = await lb.execute_with_load_balancing(
                        providers, 'test_method', strategy=strategy
                    )
                    print(f"  Request {i+1}: {selected} -> {result}")
                except Exception as e:
                    print(f"  Request {i+1}: Failed -> {e}")
        
        # Test circuit breaker
        print(f"\n⚡ Testing circuit breaker:")
        for i in range(10):
            try:
                result, selected = await lb.execute_with_load_balancing(
                    {'unreliable': providers['unreliable']}, 'test_method'
                )
                print(f"  Attempt {i+1}: {selected} -> Success")
            except Exception as e:
                print(f"  Attempt {i+1}: Failed -> {str(e)[:50]}")
        
        # Show metrics
        print(f"\n📊 Load balancer metrics:")
        metrics = lb.get_metrics()
        for provider, stats in metrics.items():
            print(f"  {provider}: success_rate={stats['success_rate']:.2f}, "
                  f"avg_time={stats['avg_response_time']:.3f}s")
        
        print("🎉 Load balancer tests completed!")
    
    # Run tests
    asyncio.run(test_load_balancer())


if __name__ == "__main__":
    main() 