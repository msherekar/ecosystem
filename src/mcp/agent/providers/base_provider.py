"""
Base Provider Interface
Defines the contract that all LLM providers must implement.
Enhanced with health checks, validation, and structured logging.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import logging
import time
import structlog
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field, ValidationError


class ProviderType(Enum):
    """Types of LLM providers"""
    EXTERNAL = "external"
    LOCAL = "local"
    HYBRID = "hybrid"


class ProviderStatus(Enum):
    """Provider availability status"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    INITIALIZING = "initializing"
    ERROR = "error"
    DEGRADED = "degraded"


class ProviderConfig(BaseModel):
    """Base configuration for all providers"""
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout: float = Field(default=30.0, gt=0, le=300)
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=4096, gt=0)
    collect_metrics: bool = True
    enable_logging: bool = True


class BaseLLMProvider(ABC):
    """
    Abstract base class for all LLM providers.
    Enhanced with health monitoring, validation, and structured logging.
    """
    
    def __init__(self, provider_type: ProviderType, config: Dict[str, Any] = None):
        self.provider_type = provider_type
        self.status = ProviderStatus.UNAVAILABLE
        
        # Initialize structured logging
        self.logger = structlog.get_logger(f"provider_{provider_type.value}")
        
        # Validate and set configuration
        try:
            self.config = self._get_config_class()(**config or {})
        except ValidationError as e:
            self.logger.error("Invalid configuration", error=str(e))
            self.config = self._get_config_class()()
        
        # Performance metrics
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0,
            "total_cost": 0.0,
            "last_request_time": 0.0,
            "health_check_failures": 0
        }
        
        # Health monitoring
        self._last_health_check = 0.0
        self._health_check_interval = 60.0  # seconds
    
    def _get_config_class(self):
        """Override in subclasses for specific config types"""
        return ProviderConfig
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the provider. Returns True if successful."""
        pass
    
    @abstractmethod
    async def chat(self, user_message: str, context: Dict[str, Any] = None) -> Tuple[str, List[str]]:
        """Generate response to user message."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is currently available."""
        pass
    
    @abstractmethod
    def estimate_cost(self, user_message: str, response: str = "") -> float:
        """Estimate the cost of processing this message."""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Return provider capabilities and limitations."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform provider-specific health check."""
        pass
    
    async def cleanup(self):
        """Clean up provider resources."""
        self.logger.info("Provider cleanup completed", provider=self.provider_type.value)
    
    def update_metrics(self, success: bool, response_time: float, cost: float = 0.0):
        """Update provider performance metrics with validation."""
        if response_time < 0:
            raise ValueError("Response time cannot be negative")
        if cost < 0:
            raise ValueError("Cost cannot be negative")
        
        self.metrics["total_requests"] += 1
        self.metrics["last_request_time"] = time.time()
        
        if success:
            self.metrics["successful_requests"] += 1
        else:
            self.metrics["failed_requests"] += 1
        
        # Update average response time for successful requests only
        total_successful = self.metrics["successful_requests"]
        if total_successful > 0 and success:
            current_avg = self.metrics["average_response_time"]
            self.metrics["average_response_time"] = (
                (current_avg * (total_successful - 1) + response_time) / total_successful
            )
        
        self.metrics["total_cost"] += cost
        
        # Log metrics if enabled
        if self.config.collect_metrics:
            self.logger.info(
                "Request completed",
                success=success,
                response_time=response_time,
                cost=cost,
                provider=self.provider_type.value
            )
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        try:
            current_time = time.time()
            
            # Perform health check if needed
            if current_time - self._last_health_check > self._health_check_interval:
                health_data = await self.health_check()
                self._last_health_check = current_time
            else:
                health_data = {"cached": True}
            
            return {
                "status": self.status.value,
                "provider_type": self.provider_type.value,
                "last_check": self._last_health_check,
                "available": self.is_available(),
                "metrics": self.get_metrics(),
                **health_data
            }
        except Exception as e:
            self.metrics["health_check_failures"] += 1
            self.logger.error("Health check failed", error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "last_check": time.time(),
                "provider_type": self.provider_type.value
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get provider performance metrics."""
        success_rate = 0.0
        if self.metrics["total_requests"] > 0:
            success_rate = self.metrics["successful_requests"] / self.metrics["total_requests"]
        
        return {
            **self.metrics,
            "success_rate": success_rate,
            "provider_type": self.provider_type.value,
            "status": self.status.value
        }
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []
        try:
            self._get_config_class()(**self.config.model_dump())
        except ValidationError as e:
            issues = [str(error) for error in e.errors()]
        return issues
    
    def reset_metrics(self):
        """Reset performance metrics."""
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0,
            "total_cost": 0.0,
            "last_request_time": 0.0,
            "health_check_failures": 0
        }
        self.logger.info("Metrics reset", provider=self.provider_type.value)
    
    @asynccontextmanager
    async def conversation_context(self, context_id: str):
        """Manage conversation context lifecycle."""
        self.logger.info("Starting conversation context", context_id=context_id)
        try:
            yield context_id
        finally:
            self.logger.info("Ending conversation context", context_id=context_id)
    
    def get_electron_bridge_data(self) -> Dict[str, Any]:
        """Get data formatted for Electron bridge communication."""
        return {
            "providerId": f"{self.provider_type.value}",
            "status": self.status.value,
            "capabilities": self.get_capabilities(),
            "metrics": self.get_metrics(),
            "config": self.config.model_dump() if hasattr(self.config, 'model_dump') else {}
        }


async def main():
    """Main function for testing and demonstration."""
    print("🧪 Testing Enhanced BaseLLMProvider...")
    
    # Create a mock provider for testing
    class MockProvider(BaseLLMProvider):
        def __init__(self):
            super().__init__(ProviderType.LOCAL, {})
        
        async def initialize(self) -> bool:
            self.status = ProviderStatus.AVAILABLE
            return True
        
        async def chat(self, user_message: str, context=None):
            return f"Mock response to: {user_message}", []
        
        def is_available(self) -> bool:
            return self.status == ProviderStatus.AVAILABLE
        
        def estimate_cost(self, user_message: str, response: str = "") -> float:
            return 0.01
        
        def get_capabilities(self):
            return {"provider_type": "mock", "test": True}
        
        async def health_check(self):
            return {"healthy": True, "uptime": 100}
    
    # Test enhanced provider
    provider = MockProvider()
    
    # Test initialization
    init_success = await provider.initialize()
    print(f"✅ Initialization: {init_success}")
    
    # Test configuration validation
    issues = provider.validate_config()
    print(f"✅ Config validation: {len(issues)} issues")
    
    # Test health status
    health = await provider.get_health_status()
    print(f"✅ Health status: {health['status']}")
    
    # Test chat with metrics
    response, flags = await provider.chat("Hello test")
    provider.update_metrics(success=True, response_time=0.5, cost=0.01)
    print(f"✅ Chat response: {response}")
    
    # Test metrics
    metrics = provider.get_metrics()
    print(f"✅ Metrics - Success rate: {metrics['success_rate']:.2%}")
    
    # Test Electron bridge data
    bridge_data = provider.get_electron_bridge_data()
    print(f"✅ Electron bridge data keys: {list(bridge_data.keys())}")
    
    # Test conversation context
    async with provider.conversation_context("test-context"):
        print("✅ Conversation context managed")
    
    # Cleanup
    await provider.cleanup()
    
    print("🎉 All enhanced base provider tests passed!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())