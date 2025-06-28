"""
External LLM Provider
Handles external LLM services (OpenRouter, OpenAI, etc.)
"""

import time
from typing import Dict, List, Any, Optional, Tuple
from .base_provider import BaseLLMProvider, ProviderType, ProviderStatus
from src.mcp.agent.core import Agent


class ExternalLLMProvider(BaseLLMProvider):
    """Provider for external LLM services (OpenRouter, OpenAI, etc.)"""
    
    def __init__(self, api_key: str = None):
        super().__init__(ProviderType.EXTERNAL)
        self.api_key = api_key
        self.agent: Optional[Agent] = None
        
        # External provider specific configuration
        self.config.update({
            "max_retries": 3,
            "timeout": 30.0,
            "model_preference": "auto"
        })
    
    async def initialize(self) -> bool:
        """Initialize external LLM provider"""
        try:
            self.status = ProviderStatus.INITIALIZING
            
            if not self.api_key:
                self.logger.warning("No API key provided for external LLM")
                self.status = ProviderStatus.UNAVAILABLE
                return False
            
            # Initialize the external agent (import from core.py)
            self.agent = Agent(self.api_key)
            
            # Test connectivity (optional)
            # await self._test_connectivity()
            
            self.status = ProviderStatus.AVAILABLE
            self.logger.info("External LLM provider initialized successfully")
            return True
            
        except Exception as e:
            self.status = ProviderStatus.ERROR
            self.logger.error(f"Failed to initialize external LLM provider: {e}")
            return False
    
    async def chat(self, user_message: str, context: Dict[str, Any] = None) -> Tuple[str, List[str]]:
        """Generate response using external LLM"""
        if not self.is_available():
            raise RuntimeError("External LLM provider not available")
        
        start_time = time.time()
        
        try:
            # Use existing agent implementation
            response, flags = await self.agent.chat(user_message)
            
            # Calculate metrics
            response_time = time.time() - start_time
            cost = self.estimate_cost(user_message, response)
            
            # Update metrics
            self.update_metrics(success=True, response_time=response_time, cost=cost)
            
            return response, flags
            
        except Exception as e:
            response_time = time.time() - start_time
            self.update_metrics(success=False, response_time=response_time)
            
            self.logger.error(f"External LLM chat failed: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if external provider is available"""
        return (self.status == ProviderStatus.AVAILABLE and 
                self.agent is not None and 
                self.api_key is not None)
    
    def estimate_cost(self, user_message: str, response: str = "") -> float:
        """Estimate cost for external LLM usage"""
        # Rough estimation based on token count
        # GPT-4: ~$0.03/1K input tokens, ~$0.06/1K output tokens
        
        input_tokens = len(user_message.split()) * 1.3  # Rough token estimation
        output_tokens = len(response.split()) * 1.3 if response else 0
        
        input_cost = (input_tokens / 1000) * 0.03
        output_cost = (output_tokens / 1000) * 0.06
        
        return input_cost + output_cost
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return external provider capabilities"""
        return {
            "provider_type": self.provider_type.value,
            "supports_streaming": False,
            "max_context_length": 128000,  # Typical for GPT-4
            "supports_function_calling": True,
            "supports_vision": True,
            "cost_per_request": "variable",
            "latency": "medium",
            "quality": "high",
            "specialized_domains": ["general", "coding", "analysis"]
        }
    
    async def _test_connectivity(self) -> bool:
        """Test connection to external LLM service"""
        try:
            # Simple test message
            test_response, _ = await self.agent.chat("Hello")
            return len(test_response) > 0
        except Exception as e:
            self.logger.warning(f"Connectivity test failed: {e}")
            return False
    
    def configure_model(self, model_name: str, **kwargs):
        """Configure specific model settings"""
        self.config.update({
            "model_name": model_name,
            **kwargs
        })
        self.logger.info(f"External provider configured for model: {model_name}")
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get usage summary for external provider"""
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
            "avg_response_time": metrics["average_response_time"]
        }


if __name__ == "__main__":
    # Suppress the RuntimeWarning about module import behavior
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning, 
                          message=".*found in sys.modules.*")
    """Test the external provider individually"""
    import asyncio
    import os
    
    async def test_external_provider():
        print("🧪 Testing ExternalLLMProvider...")
        
        # Test without API key (should fail gracefully)
        provider = ExternalLLMProvider()
        
        # Test initialization without API key
        init_success = await provider.initialize()
        print(f"✅ Init without API key: {not init_success} (expected to fail)")
        
        # Test availability
        available = provider.is_available()
        print(f"✅ Availability without API key: {not available} (expected false)")
        
        # Test capabilities
        capabilities = provider.get_capabilities()
        print(f"✅ Capabilities: {capabilities['provider_type']}")
        
        # Test cost estimation
        cost = provider.estimate_cost("Hello world", "Hi there!")
        print(f"✅ Cost estimation: ${cost:.4f}")
        
        # Test with API key if available
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if api_key:
            print("\n🔑 Testing with API key...")
            provider_with_key = ExternalLLMProvider(api_key)
            init_with_key = await provider_with_key.initialize()
            print(f"✅ Init with API key: {init_with_key}")
            
            if init_with_key:
                try:
                    response, flags = await provider_with_key.chat("Say hello")
                    print(f"✅ Chat response: {response[:50]}...")
                except Exception as e:
                    print(f"⚠️  Chat failed (expected if no internet): {e}")
        else:
            print("ℹ️  No API key found in environment variables")
        
        # Test usage summary
        summary = provider.get_usage_summary()
        print(f"✅ Usage summary: {summary}")
        
        print("🎉 External provider tests completed!")
    
    # Run tests
    asyncio.run(test_external_provider())