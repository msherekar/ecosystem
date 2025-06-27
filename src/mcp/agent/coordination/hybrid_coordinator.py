"""
Hybrid Coordinator
Replaces the monolithic HybridAgent with a modular, scalable architecture.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from src.mcp.agent.providers.external_provider import ExternalLLMProvider
from src.mcp.agent.providers.local_provider import LocalLLMProvider
from src.mcp.agent.decision.provider_selector import ProviderSelector, SelectionStrategy


class HybridCoordinator:
    """
    Modular hybrid agent coordinator.
    
    Orchestrates multiple LLM providers using intelligent selection strategies.
    This replaces the monolithic HybridAgent with a clean, modular architecture.
    """
    
    def __init__(self, api_key: str = None):
        self.logger = logging.getLogger("hybrid_coordinator")
        
        # Initialize providers
        self.providers: Dict[str, Any] = {}
        self.external_provider = ExternalLLMProvider(api_key) if api_key else None
        self.local_provider = LocalLLMProvider()
        
        # Initialize decision engine
        self.provider_selector = ProviderSelector()
        
        # Coordinator configuration
        self.config = {
            "fallback_enabled": True,
            "collect_metrics": True,
            "auto_training": False
        }
        
        # Global usage statistics
        self.global_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "fallback_count": 0,
            "cost_savings": 0.0
        }
    
    async def initialize(self) -> bool:
        """Initialize all providers and components"""
        try:
            self.logger.info("Initializing hybrid coordinator...")
            
            # Initialize external provider
            if self.external_provider:
                external_success = await self.external_provider.initialize()
                if external_success:
                    self.providers["external"] = self.external_provider
                    self.logger.info("External provider initialized")
                else:
                    self.logger.warning("External provider initialization failed")
            
            # Initialize local provider
            local_success = await self.local_provider.initialize()
            if local_success:
                self.providers["local"] = self.local_provider
                self.logger.info("Local provider initialized")
            else:
                self.logger.warning("Local provider initialization failed")
            
            # Check if at least one provider is available
            if not self.providers:
                self.logger.error("No providers available")
                return False
            
            self.logger.info(f"Hybrid coordinator initialized with {len(self.providers)} providers")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize hybrid coordinator: {e}")
            return False
    
    async def chat(self, user_message: str, context: Dict[str, Any] = None) -> Tuple[str, List[str]]:
        """
        Main chat method with intelligent provider selection.
        
        Args:
            user_message: User's input message
            context: Optional context for provider selection
            
        Returns:
            Tuple of (response, flags)
        """
        
        self.global_stats["total_requests"] += 1
        
        try:
            # Select best provider
            selected_provider = self.provider_selector.select_provider(
                user_message=user_message,
                available_providers=self.providers,
                usage_stats=self._get_usage_stats(),
                context=context or {}
            )
            
            if not selected_provider:
                return "No LLM providers available. Please check your configuration.", []
            
            # Execute with selected provider
            provider = self.providers[selected_provider]
            response, flags = await provider.chat(user_message, context)
            
            self.global_stats["successful_requests"] += 1
            self.logger.info(f"Chat completed successfully with {selected_provider} provider")
            
            return response, flags
            
        except Exception as e:
            self.logger.error(f"Chat failed with selected provider: {e}")
            
            # Try fallback if enabled
            if self.config.get("fallback_enabled", True):
                return await self._try_fallback(user_message, context, selected_provider)
            else:
                return f"I encountered an error: {str(e)}", []
    
    async def _try_fallback(
        self, 
        user_message: str, 
        context: Dict[str, Any], 
        failed_provider: str
    ) -> Tuple[str, List[str]]:
        """Try fallback provider when primary fails"""
        
        # Find alternative provider
        alternative_providers = [name for name in self.providers.keys() if name != failed_provider]
        
        for provider_name in alternative_providers:
            try:
                self.logger.info(f"Trying fallback provider: {provider_name}")
                provider = self.providers[provider_name]
                
                if provider.is_available():
                    response, flags = await provider.chat(user_message, context)
                    self.global_stats["fallback_count"] += 1
                    self.global_stats["successful_requests"] += 1
                    return response, flags
                    
            except Exception as e:
                self.logger.warning(f"Fallback provider {provider_name} also failed: {e}")
                continue
        
        return "All LLM providers failed. Please try again later.", []
    
    def configure_selection_strategy(
        self, 
        strategy: SelectionStrategy, 
        **kwargs
    ):
        """Configure provider selection strategy"""
        self.provider_selector.configure_strategy(strategy, **kwargs)
        self.logger.info(f"Selection strategy configured: {strategy.value}")
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        status = {}
        
        for name, provider in self.providers.items():
            provider_metrics = provider.get_metrics()
            capabilities = provider.get_capabilities()
            
            status[name] = {
                "available": provider.is_available(),
                "metrics": provider_metrics,
                "capabilities": capabilities
            }
        
        return status
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get comprehensive usage statistics"""
        provider_stats = {}
        total_cost = 0.0
        
        for name, provider in self.providers.items():
            metrics = provider.get_metrics()
            provider_stats[name] = metrics
            total_cost += metrics.get("total_cost", 0.0)
        
        return {
            "global": self.global_stats,
            "providers": provider_stats,
            "total_cost": total_cost,
            "cost_savings": self._calculate_cost_savings(),
            "provider_distribution": self._get_provider_distribution()
        }
    
    def _get_usage_stats(self) -> Dict[str, int]:
        """Get usage stats for provider selection"""
        stats = {}
        for name, provider in self.providers.items():
            metrics = provider.get_metrics()
            stats[f"{name}_calls"] = metrics["total_requests"]
        return stats
    
    def _calculate_cost_savings(self) -> float:
        """Calculate total cost savings from using local models"""
        if "local" not in self.providers:
            return 0.0
        
        local_metrics = self.providers["local"].get_metrics()
        local_requests = local_metrics["total_requests"]
        
        # Estimate cost if all local requests were external
        estimated_external_cost = local_requests * 0.05  # Rough estimate
        return estimated_external_cost
    
    def _get_provider_distribution(self) -> Dict[str, float]:
        """Get percentage distribution of provider usage"""
        distribution = {}
        total_requests = sum(
            provider.get_metrics()["total_requests"] 
            for provider in self.providers.values()
        )
        
        if total_requests == 0:
            return distribution
        
        for name, provider in self.providers.items():
            requests = provider.get_metrics()["total_requests"]
            distribution[name] = (requests / total_requests) * 100
        
        return distribution
    
    async def train_local_model(self, **kwargs) -> Dict[str, Any]:
        """Train local model if local provider supports it"""
        if "local" not in self.providers:
            return {"success": False, "error": "Local provider not available"}
        
        local_provider = self.providers["local"]
        if hasattr(local_provider, 'train_model'):
            return await local_provider.train_model(**kwargs)
        else:
            return {"success": False, "error": "Local provider doesn't support training"}
    
    def reset_statistics(self):
        """Reset all statistics"""
        self.global_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "fallback_count": 0,
            "cost_savings": 0.0
        }
        
        for provider in self.providers.values():
            provider.reset_metrics()
        
        self.logger.info("All statistics reset")
    
    def configure(self, **kwargs):
        """Configure coordinator settings"""
        self.config.update(kwargs)
        self.logger.info(f"Coordinator configured: {list(kwargs.keys())}")


# Global coordinator instance
hybrid_coordinator = None

async def get_hybrid_coordinator(api_key: str = None) -> HybridCoordinator:
    """Get the global hybrid coordinator instance"""
    global hybrid_coordinator
    
    if hybrid_coordinator is None:
        hybrid_coordinator = HybridCoordinator(api_key)
        await hybrid_coordinator.initialize()
    
    return hybrid_coordinator


if __name__ == "__main__":
    """Test the hybrid coordinator individually"""
    import asyncio
    import os
    
    async def test_hybrid_coordinator():
        print("🧪 Testing HybridCoordinator...")
        
        # Test initialization without API key
        coordinator = HybridCoordinator()
        init_success = await coordinator.initialize()
        print(f"✅ Initialization: {init_success} (may be False if no providers available)")
        
        # Test provider status
        status = coordinator.get_provider_status()
        print(f"✅ Provider status: {len(status)} providers")
        for name, provider_status in status.items():
            print(f"   {name}: available={provider_status['available']}")
        
        # Test configuration
        from src.mcp.agent.decision import SelectionStrategy
        coordinator.configure_selection_strategy(
            SelectionStrategy.COST_OPTIMIZED,
            max_external_calls=3
        )
        print("✅ Strategy configuration successful")
        
        # Test coordinator configuration
        coordinator.configure(
            fallback_enabled=True,
            collect_metrics=True,
            auto_training=False
        )
        print("✅ Coordinator configuration successful")
        
        # Test usage statistics
        stats = coordinator.get_usage_statistics()
        print(f"✅ Usage statistics: {stats['global']['total_requests']} total requests")
        
        # Test chat if any provider is available
        if status:
            try:
                response, flags = await coordinator.chat("Hello, test message")
                print(f"✅ Chat test: {response[:50]}...")
            except Exception as e:
                print(f"⚠️  Chat failed (expected if no providers): {e}")
        else:
            print("ℹ️  Skipping chat test (no providers available)")
        
        # Test with API key if available
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if api_key:
            print("\n🔑 Testing with API key...")
            coordinator_with_key = HybridCoordinator(api_key)
            init_with_key = await coordinator_with_key.initialize()
            print(f"✅ Init with API key: {init_with_key}")
            
            if init_with_key:
                status_with_key = coordinator_with_key.get_provider_status()
                print(f"✅ Providers with API key: {len(status_with_key)}")
                
                try:
                    response, flags = await coordinator_with_key.chat("Say hello briefly")
                    print(f"✅ Chat with API key: {response[:50]}...")
                except Exception as e:
                    print(f"⚠️  Chat with API key failed: {e}")
        else:
            print("ℹ️  No API key found in environment variables")
        
        # Test global coordinator function
        print("\n🌐 Testing global coordinator:")
        global_coordinator = await get_hybrid_coordinator()
        print(f"✅ Global coordinator: {type(global_coordinator).__name__}")
        
        # Test statistics reset
        coordinator.reset_statistics()
        stats_after_reset = coordinator.get_usage_statistics()
        print(f"✅ Statistics reset: {stats_after_reset['global']['total_requests']} requests")
        
        # Test local model training (will likely fail without training data)
        training_result = await coordinator.train_local_model(
            base_model="llama3.1:8b",
            model_name="test-model",
            min_conversations=1  # Low threshold for testing
        )
        print(f"✅ Training test: {training_result.get('success', False)} (expected to fail)")
        
        print("🎉 Hybrid coordinator tests completed!")
    
    # Run tests
    asyncio.run(test_hybrid_coordinator())