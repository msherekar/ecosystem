"""
Hybrid Coordinator
Lightweight wrapper around ScalableHybridCoordinator for backward compatibility.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from .scalable_coordinator import ScalableHybridCoordinator, CoordinatorConfig
from src.mcp.agent.decision.provider_selector import ScalableProviderSelector, SelectionStrategy


class HybridCoordinator:
    """
    Modular hybrid agent coordinator (backward compatibility wrapper).
    
    This is now a lightweight wrapper around ScalableHybridCoordinator
    maintaining backward compatibility while providing all enhanced features.
    """
    
    def __init__(self, api_key: str = None):
        self.logger = logging.getLogger("hybrid_coordinator")
        
        # Create coordinator configuration
        coordinator_config = CoordinatorConfig(
            fallback_enabled=True,
            caching_enabled=True,
            metrics_collection=True,
            load_balancing_strategy="weighted_round_robin"
        )
        
        # Initialize scalable coordinator
        self.coordinator = ScalableHybridCoordinator(coordinator_config)
        
        # Initialize decision engine for backward compatibility
        self.provider_selector = ScalableProviderSelector()
        
        # Setup API key if provided
        if api_key:
            self._setup_external_provider(api_key)
        self._setup_local_provider()
        
        # Backward compatibility properties
        self.config = {
            "fallback_enabled": True,
            "collect_metrics": True,
            "auto_training": False
        }
        
        # Global usage statistics (proxied to coordinator)
        self.global_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "fallback_count": 0,
            "cost_savings": 0.0
        }
    
    def _setup_external_provider(self, api_key: str):
        """Setup external provider with API key."""
        from .provider_registry import ProviderConfig
        
        external_config = ProviderConfig(
            provider_type="external",
            provider_class="external",
            initialization_params={"api_key": api_key},
            priority=1,
            enabled=True
        )
        
        # This will be registered during initialization
        self._external_config = external_config
    
    def _setup_local_provider(self):
        """Setup local provider."""
        from .provider_registry import ProviderConfig
        
        local_config = ProviderConfig(
            provider_type="local", 
            provider_class="local",
            initialization_params={},
            priority=0,
            enabled=True
        )
        
        # This will be registered during initialization
        self._local_config = local_config
    
    async def initialize(self) -> bool:
        """Initialize all providers and components"""
        try:
            self.logger.info("Initializing hybrid coordinator...")
            
            # Initialize the scalable coordinator
            success = await self.coordinator.initialize()
            if not success:
                return False
            
            # Register providers if configured
            if hasattr(self, '_external_config'):
                await self.coordinator.provider_registry.register_provider(
                    "external", self._external_config
                )
            
            if hasattr(self, '_local_config'):
                await self.coordinator.provider_registry.register_provider(
                    "local", self._local_config
                )
            
            self.logger.info("Hybrid coordinator initialized successfully")
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
        
        try:
            # Delegate to scalable coordinator
            response, flags, metadata = await self.coordinator.chat(
                user_message=user_message,
                context=context
            )
            
            # Update backward compatibility stats
            self.global_stats["total_requests"] += 1
            if metadata.get('fallback_used', False):
                self.global_stats["fallback_count"] += 1
            if response and not response.startswith("I encountered an error"):
                self.global_stats["successful_requests"] += 1
            
            return response, flags
            
        except Exception as e:
            self.logger.error(f"Chat failed: {e}")
            return f"I encountered an error: {str(e)}", []
    
    @property
    def providers(self) -> Dict[str, Any]:
        """Get available providers (backward compatibility)."""
        return self.coordinator.provider_registry.get_available_providers()
    
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
        return self.coordinator.provider_registry.get_provider_health()
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get comprehensive usage statistics"""
        # Get full status from coordinator
        coordinator_status = self.coordinator.get_status()
        
        # Add backward compatibility stats
        return {
            "global": self.global_stats,
            "providers": coordinator_status.get("providers", {}),
            "load_balancer": coordinator_status.get("load_balancer", {}),
            "cache": coordinator_status.get("cache", {}),
            "coordinator_metrics": coordinator_status.get("metrics", {}),
            "total_cost": self._estimate_total_cost(),
            "cost_savings": self._calculate_cost_savings(),
            "provider_distribution": self._get_provider_distribution()
        }
    
    def _estimate_total_cost(self) -> float:
        """Estimate total cost from provider usage"""
        # This is a rough estimate - could be enhanced with actual provider cost data
        coordinator_metrics = self.coordinator.get_status().get("metrics", {})
        successful_requests = coordinator_metrics.get("successful_requests", 0)
        return successful_requests * 0.01  # Rough estimate of $0.01 per request
    
    def _calculate_cost_savings(self) -> float:
        """Calculate total cost savings from using local models"""
        # Get load balancer metrics to see provider usage
        lb_metrics = self.coordinator.load_balancer.get_metrics()
        local_requests = lb_metrics.get("local", {}).get("total_requests", 0)
        
        # Estimate cost if all local requests were external
        estimated_external_cost = local_requests * 0.05  # Rough estimate
        return estimated_external_cost
    
    def _get_provider_distribution(self) -> Dict[str, float]:
        """Get percentage distribution of provider usage"""
        distribution = {}
        lb_metrics = self.coordinator.load_balancer.get_metrics()
        
        total_requests = sum(
            metrics.get("total_requests", 0)
            for metrics in lb_metrics.values()
            if isinstance(metrics, dict)
        )
        
        if total_requests == 0:
            return distribution
        
        for provider_name, metrics in lb_metrics.items():
            if isinstance(metrics, dict):
                requests = metrics.get("total_requests", 0)
                distribution[provider_name] = (requests / total_requests) * 100
        
        return distribution
    
    async def train_local_model(self, **kwargs) -> Dict[str, Any]:
        """Train local model if local provider supports it"""
        available_providers = self.providers
        if "local" not in available_providers:
            return {"success": False, "error": "Local provider not available"}
        
        local_provider = available_providers["local"]
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
        
        # Reset coordinator metrics
        self.coordinator.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'rate_limited_requests': 0,
            'fallback_requests': 0,
            'avg_response_time': 0.0,
            'uptime_start': time.time()
        }
        
        # Reset load balancer metrics
        self.coordinator.load_balancer.reset_metrics()
        
        # Reset cache stats
        if self.coordinator.cache:
            self.coordinator.cache.reset_stats()
        
        self.logger.info("All statistics reset")
    
    def configure(self, **kwargs):
        """Configure coordinator settings"""
        self.config.update(kwargs)
        
        # Apply configuration to scalable coordinator
        for key, value in kwargs.items():
            if hasattr(self.coordinator.config, key):
                setattr(self.coordinator.config, key, value)
        
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


def main():
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

if __name__ == "__main__":
    main()