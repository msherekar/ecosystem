"""
External LLM Provider
Handles external LLM services with connection pooling, retry logic, and rate limiting.
Enhanced for scalability, security, and Electron integration.
"""

import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from collections import deque
from functools import wraps
from contextlib import asynccontextmanager
import aiohttp
from pydantic import Field

from .base_provider import BaseLLMProvider, ProviderType, ProviderStatus, ProviderConfig
from src.mcp.agent.core import Agent


class ExternalProviderConfig(ProviderConfig):
    """Configuration for external LLM providers"""
    api_key: str = Field(default="", min_length=0)
    model_preference: str = "auto"
    rate_limit_rpm: int = Field(default=60, gt=0)
    connection_pool_size: int = Field(default=10, gt=0)
    circuit_breaker_threshold: int = Field(default=5, gt=0)
    circuit_breaker_timeout: float = Field(default=60.0, gt=0)


class RateLimiter:
    """Async rate limiter for API requests"""
    
    def __init__(self, max_requests: int, time_window: float):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make a request"""
        async with self._lock:
            now = time.time()
            # Remove old requests outside the time window
            while self.requests and self.requests[0] <= now - self.time_window:
                self.requests.popleft()
            
            if len(self.requests) >= self.max_requests:
                wait_time = self.time_window - (now - self.requests[0])
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    return await self.acquire()
            
            self.requests.append(now)


class CircuitBreaker:
    """Circuit breaker for handling external service failures"""
    
    def __init__(self, failure_threshold: int, timeout: float):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open
    
    def record_success(self):
        """Record a successful request"""
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self):
        """Record a failed request"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
    
    def can_proceed(self) -> bool:
        """Check if request can proceed"""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
                return True
            return False
        
        # half-open state
        return True


def with_retry(max_retries: int = 3, backoff_factor: float = 1.0):
    """Decorator for adding retry logic to async methods"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(self, *args, **kwargs)
                except Exception as e:
                    last_exception = e
                    self.circuit_breaker.record_failure()
                    
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor * (2 ** attempt)
                        self.logger.warning(
                            "Request failed, retrying",
                            attempt=attempt + 1,
                            wait_time=wait_time,
                            error=str(e)
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        self.logger.error("All retry attempts failed", error=str(e))
            
            raise last_exception
        return wrapper
    return decorator


class ExternalLLMProvider(BaseLLMProvider):
    """Enhanced external LLM provider with connection management and resilience"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(ProviderType.EXTERNAL, config or {})
        self.agent: Optional[Agent] = None
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Initialize rate limiter and circuit breaker
        self.rate_limiter = RateLimiter(
            max_requests=self.config.rate_limit_rpm,
            time_window=60.0
        )
        
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=self.config.circuit_breaker_threshold,
            timeout=self.config.circuit_breaker_timeout
        )
    
    def _get_config_class(self):
        return ExternalProviderConfig
    
    async def initialize(self) -> bool:
        """Initialize external LLM provider with connection pooling"""
        try:
            self.status = ProviderStatus.INITIALIZING
            
            if not self.config.api_key or self.config.api_key.strip() == "":
                self.logger.warning("No API key provided for external LLM")
                self.status = ProviderStatus.UNAVAILABLE
                return False
            
            # Initialize HTTP session with connection pooling
            connector = aiohttp.TCPConnector(
                limit=self.config.connection_pool_size,
                ttl_dns_cache=300,
                use_dns_cache=True,
                enable_cleanup_closed=True
            )
            
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"User-Agent": "Gliaent-External-Provider/1.0"}
            )
            
            # Initialize agent
            self.agent = Agent(self.config.api_key)
            
            # Test connectivity
            if await self._test_connectivity():
                self.status = ProviderStatus.AVAILABLE
                self.logger.info("External LLM provider initialized successfully")
                return True
            else:
                self.status = ProviderStatus.UNAVAILABLE
                self.logger.warning("External LLM connectivity test failed")
                return False
                
        except Exception as e:
            self.status = ProviderStatus.ERROR
            self.logger.error("Failed to initialize external LLM provider", error=str(e))
            return False
    
    @with_retry(max_retries=3, backoff_factor=1.0)
    async def chat(self, user_message: str, context: Dict[str, Any] = None) -> Tuple[str, List[str]]:
        """Generate response using external LLM with resilience patterns"""
        if not self.is_available():
            raise RuntimeError("External LLM provider not available")
        
        if not self.circuit_breaker.can_proceed():
            raise RuntimeError("Circuit breaker is open - external service unavailable")
        
        # Apply rate limiting
        await self.rate_limiter.acquire()
        
        start_time = time.time()
        
        try:
            # Use existing agent implementation
            response, flags = await self.agent.chat(user_message)
            
            # Record success
            self.circuit_breaker.record_success()
            
            # Calculate metrics
            response_time = time.time() - start_time
            cost = self.estimate_cost(user_message, response)
            
            # Update metrics
            self.update_metrics(success=True, response_time=response_time, cost=cost)
            
            return response, flags
            
        except Exception as e:
            response_time = time.time() - start_time
            self.update_metrics(success=False, response_time=response_time)
            self.logger.error("External LLM chat failed", error=str(e))
            raise
    
    def is_available(self) -> bool:
        """Check if external provider is available"""
        return (self.status == ProviderStatus.AVAILABLE and 
                self.agent is not None and 
                self.config.api_key and
                self.config.api_key.strip() != "" and
                self.circuit_breaker.can_proceed())
    
    def estimate_cost(self, user_message: str, response: str = "") -> float:
        """Estimate cost for external LLM usage"""
        # Enhanced cost estimation with different model rates
        input_tokens = len(user_message.split()) * 1.3
        output_tokens = len(response.split()) * 1.3 if response else 0
        
        # Model-specific pricing (example rates)
        model_rates = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "claude-3": {"input": 0.015, "output": 0.075}
        }
        
        # Default to GPT-4 rates
        rates = model_rates.get("gpt-4", {"input": 0.03, "output": 0.06})
        
        input_cost = (input_tokens / 1000) * rates["input"]
        output_cost = (output_tokens / 1000) * rates["output"]
        
        return input_cost + output_cost
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return external provider capabilities"""
        return {
            "provider_type": self.provider_type.value,
            "supports_streaming": False,
            "max_context_length": 128000,
            "supports_function_calling": True,
            "supports_vision": True,
            "cost_per_request": "variable",
            "latency": "medium",
            "quality": "high",
            "specialized_domains": ["general", "coding", "analysis"],
            "rate_limit_rpm": self.config.rate_limit_rpm,
            "circuit_breaker_status": self.circuit_breaker.state
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        try:
            # Test simple connectivity
            test_start = time.time()
            test_response, _ = await self.agent.chat("Hello")
            test_time = time.time() - test_start
            
            return {
                "healthy": True,
                "test_response_time": test_time,
                "circuit_breaker_state": self.circuit_breaker.state,
                "failure_count": self.circuit_breaker.failure_count,
                "rate_limiter_requests": len(self.rate_limiter.requests)
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "circuit_breaker_state": self.circuit_breaker.state
            }
    
    async def _test_connectivity(self) -> bool:
        """Test connection to external LLM service"""
        try:
            response, _ = await self.agent.chat("Test")
            return len(response) > 0
        except Exception as e:
            self.logger.warning("Connectivity test failed", error=str(e))
            return False
    
    async def cleanup(self):
        """Clean up external provider resources"""
        if self.session:
            await self.session.close()
            self.logger.info("HTTP session closed")
        await super().cleanup()
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get comprehensive usage summary"""
        metrics = self.get_metrics()
        
        return {
            "provider": "external",
            "total_cost": metrics["total_cost"],
            "requests": metrics["total_requests"],
            "avg_cost_per_request": (
                metrics["total_cost"] / metrics["total_requests"] 
                if metrics["total_requests"] > 0 else 0
            ),
            "success_rate": metrics["success_rate"],
            "avg_response_time": metrics["average_response_time"],
            "circuit_breaker_state": self.circuit_breaker.state,
            "rate_limit_rpm": self.config.rate_limit_rpm
        }
    
    def get_electron_bridge_data(self) -> Dict[str, Any]:
        """Get data for Electron bridge with external-specific info"""
        base_data = super().get_electron_bridge_data()
        base_data.update({
            "connectionStatus": "connected" if self.is_available() else "disconnected",
            "circuitBreakerState": self.circuit_breaker.state,
            "rateLimitRpm": self.config.rate_limit_rpm,
            "costPerRequest": "variable"
        })
        return base_data


async def main():
    """Main function for testing external provider enhancements"""
    print("🧪 Testing Enhanced ExternalLLMProvider...")
    
    # Test without API key (should fail gracefully)
    provider = ExternalLLMProvider()
    init_success = await provider.initialize()
    print(f"✅ Init without API key: {not init_success} (expected to fail)")
    
    # Test with mock configuration
    config = {
        "api_key": "test-key-12345",
        "rate_limit_rpm": 30,
        "circuit_breaker_threshold": 3,
        "timeout": 15.0
    }
    
    provider_with_config = ExternalLLMProvider(config)
    print(f"✅ Configuration: {provider_with_config.config.rate_limit_rpm} RPM")
    
    # Test capabilities
    capabilities = provider_with_config.get_capabilities()
    print(f"✅ Capabilities: {capabilities['provider_type']}")
    print(f"   - Rate limit: {capabilities['rate_limit_rpm']} RPM")
    print(f"   - Circuit breaker: {capabilities['circuit_breaker_status']}")
    
    # Test cost estimation
    cost = provider_with_config.estimate_cost("Hello world", "Hi there!")
    print(f"✅ Cost estimation: ${cost:.4f}")
    
    # Test rate limiter
    rate_limiter = RateLimiter(max_requests=5, time_window=10.0)
    start_time = time.time()
    for i in range(3):
        await rate_limiter.acquire()
    elapsed = time.time() - start_time
    print(f"✅ Rate limiter: {elapsed:.2f}s for 3 requests")
    
    # Test circuit breaker
    circuit_breaker = CircuitBreaker(failure_threshold=2, timeout=5.0)
    print(f"✅ Circuit breaker initial state: {circuit_breaker.state}")
    
    circuit_breaker.record_failure()
    circuit_breaker.record_failure()
    print(f"✅ Circuit breaker after failures: {circuit_breaker.state}")
    
    # Test usage summary
    summary = provider_with_config.get_usage_summary()
    print(f"✅ Usage summary: {summary['provider']}")
    
    # Test Electron bridge data
    bridge_data = provider_with_config.get_electron_bridge_data()
    print(f"✅ Electron bridge keys: {list(bridge_data.keys())}")
    
    # Cleanup
    await provider_with_config.cleanup()
    
    print("🎉 Enhanced external provider tests completed!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())