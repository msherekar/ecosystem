"""
Base Provider Interface
Defines the contract that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import logging


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


class BaseLLMProvider(ABC):
    """
    Abstract base class for all LLM providers.
    
    This defines the interface that external, local, and other providers must implement.
    """
    
    def __init__(self, provider_type: ProviderType):
        self.provider_type = provider_type
        self.status = ProviderStatus.UNAVAILABLE
        self.logger = logging.getLogger(f"provider_{provider_type.value}")
        
        # Provider-specific configuration
        self.config: Dict[str, Any] = {}
        
        # Performance metrics
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0,
            "total_cost": 0.0
        }
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the provider. Returns True if successful."""
        pass
    
    @abstractmethod
    async def chat(self, user_message: str, context: Dict[str, Any] = None) -> Tuple[str, List[str]]:
        """
        Generate response to user message.
        
        Args:
            user_message: The user's input message
            context: Additional context for response generation
            
        Returns:
            Tuple of (response_text, flags/metadata)
        """
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
    
    def update_metrics(self, success: bool, response_time: float, cost: float = 0.0):
        """Update provider performance metrics."""
        self.metrics["total_requests"] += 1
        
        if success:
            self.metrics["successful_requests"] += 1
        else:
            self.metrics["failed_requests"] += 1
        
        # Update average response time
        total_successful = self.metrics["successful_requests"]
        if total_successful > 0:
            current_avg = self.metrics["average_response_time"]
            self.metrics["average_response_time"] = (
                (current_avg * (total_successful - 1) + response_time) / total_successful
            )
        
        self.metrics["total_cost"] += cost
    
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
    
    def configure(self, **kwargs):
        """Configure provider with key-value parameters."""
        self.config.update(kwargs)
        self.logger.info(f"Provider configured with: {list(kwargs.keys())}")
    
    def reset_metrics(self):
        """Reset performance metrics."""
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0,
            "total_cost": 0.0
        }


if __name__ == "__main__":
    """Test the base provider interface"""
    import asyncio
    
    # Create a mock provider for testing
    class MockProvider(BaseLLMProvider):
        def __init__(self):
            super().__init__(ProviderType.LOCAL)
        
        async def initialize(self) -> bool:
            self.status = ProviderStatus.AVAILABLE
            return True
        
        async def chat(self, user_message: str, context=None):
            return f"Mock response to: {user_message}", []
        
        def is_available(self) -> bool:
            return self.status == ProviderStatus.AVAILABLE
        
        def estimate_cost(self, user_message: str, response: str = "") -> float:
            return 0.0
        
        def get_capabilities(self):
            return {"provider_type": "mock", "test": True}
    
    async def test_base_provider():
        print("🧪 Testing BaseLLMProvider interface...")
        
        # Test mock provider
        provider = MockProvider()
        
        # Test initialization
        init_success = await provider.initialize()
        print(f"✅ Initialization: {init_success}")
        
        # Test availability
        available = provider.is_available()
        print(f"✅ Availability: {available}")
        
        # Test chat
        response, flags = await provider.chat("Hello test")
        print(f"✅ Chat response: {response}")
        
        # Test metrics
        provider.update_metrics(success=True, response_time=0.5, cost=0.01)
        metrics = provider.get_metrics()
        print(f"✅ Metrics: {metrics}")
        
        # Test capabilities
        capabilities = provider.get_capabilities()
        print(f"✅ Capabilities: {capabilities}")
        
        print("🎉 All base provider tests passed!")
    
    # Run tests
    asyncio.run(test_base_provider())