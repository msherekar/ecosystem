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
    # Suppress the RuntimeWarning about module import behavior
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning, 
                          message=".*found in sys.modules.*")
    
    """Test the hybrid coordinator individually"""
    import asyncio
    import os
    import sys
    
    async def run_static_tests():
        """Run the original static test suite"""
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
            
            return coordinator_with_key if init_with_key else coordinator
        else:
            print("ℹ️  No API key found in environment variables")
            return coordinator
        
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
        
        print("\n🎉 Static hybrid coordinator tests completed!")
        return coordinator
    
    async def run_dynamic_tests(coordinator):
        """Run interactive dynamic testing"""
        print("\n" + "="*70)
        print("🚀 DYNAMIC HYBRID COORDINATOR TESTING")
        print("="*70)
        print("Test the hybrid coordinator with real chat interactions!")
        print("Commands:")
        print("  'quit' or 'exit' - Exit dynamic testing")
        print("  'help' - Show example queries and commands")
        print("  'status' - Show provider status and metrics")
        print("  'strategy:<name>' - Change selection strategy")
        print("  'config:<key>=<value>' - Configure coordinator settings")
        print("  'reset' - Reset all statistics")
        print("  'providers' - List available providers")
        print("  'simulate:fail:<provider>' - Simulate provider failure")
        print("  'train' - Attempt local model training")
        print("-" * 70)
        
        # Available strategies for dynamic switching
        from src.mcp.agent.decision import SelectionStrategy
        available_strategies = {
            "cost": SelectionStrategy.COST_OPTIMIZED,
            "performance": SelectionStrategy.PERFORMANCE_BASED,
            "balanced": SelectionStrategy.BALANCED,
            "local_first": SelectionStrategy.LOCAL_FIRST,
            "external_first": SelectionStrategy.EXTERNAL_FIRST
        }
        
        # Current strategy tracking
        current_strategy = "balanced"
        
        # Simulated provider failures
        simulated_failures = set()
        
        while True:
            try:
                # Get user input
                user_input = input("\n💬 Enter your query or command: ").strip()
                
                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Exiting dynamic testing...")
                    break
                
                elif user_input.lower() == 'help':
                    print("\n📚 Example queries to try:")
                    examples = [
                        "Hello, how are you?",
                        "Explain machine learning in simple terms",
                        "Write a Python function to sort a list",
                        "What is the meaning of life?",
                        "Help me debug this code: print('hello world')",
                        "Summarize the key points of quantum computing",
                        "Create a simple web scraping script",
                        "Explain the differences between SQL and NoSQL",
                        "Write a haiku about programming",
                        "How do I optimize database queries?"
                    ]
                    for i, example in enumerate(examples, 1):
                        print(f"   {i:2}. {example}")
                    
                    print("\n🔧 Strategy commands:")
                    for name, strategy in available_strategies.items():
                        print(f"   strategy:{name} - {strategy.value}")
                    
                    print("\n⚙️  Configuration commands:")
                    print("   config:fallback_enabled=true/false")
                    print("   config:collect_metrics=true/false")
                    print("   config:auto_training=true/false")
                    continue
                
                elif user_input.lower() == 'status':
                    # Show comprehensive status
                    status = coordinator.get_provider_status()
                    stats = coordinator.get_usage_statistics()
                    
                    print("\n" + "─" * 50)
                    print("📊 HYBRID COORDINATOR STATUS")
                    print("─" * 50)
                    
                    # Provider status
                    print("🔌 Provider Status:")
                    for name, provider_status in status.items():
                        availability = "🟢 Available" if provider_status['available'] else "🔴 Unavailable"
                        if name in simulated_failures:
                            availability += " (🎭 Simulated failure)"
                        print(f"   {name}: {availability}")
                        
                        metrics = provider_status.get('metrics', {})
                        if metrics:
                            print(f"     └─ Requests: {metrics.get('total_requests', 0)}")
                            print(f"     └─ Success rate: {metrics.get('success_rate', 0):.1%}")
                            if 'total_cost' in metrics:
                                print(f"     └─ Cost: ${metrics['total_cost']:.4f}")
                    
                    # Global statistics
                    global_stats = stats['global']
                    print(f"\n📈 Global Statistics:")
                    print(f"   Total requests: {global_stats['total_requests']}")
                    print(f"   Successful: {global_stats['successful_requests']}")
                    print(f"   Fallbacks: {global_stats['fallback_count']}")
                    print(f"   Cost savings: ${global_stats['cost_savings']:.4f}")
                    
                    # Provider distribution
                    distribution = stats.get('provider_distribution', {})
                    if distribution:
                        print(f"\n🎯 Usage Distribution:")
                        for provider, percentage in distribution.items():
                            print(f"   {provider}: {percentage:.1f}%")
                    
                    print(f"\n🧠 Current Strategy: {current_strategy}")
                    print("─" * 50)
                    continue
                
                elif user_input.lower() == 'providers':
                    # List available providers
                    print("\n🔌 Available Providers:")
                    for name, provider in coordinator.providers.items():
                        capabilities = provider.get_capabilities()
                        print(f"   {name}:")
                        print(f"     └─ Available: {provider.is_available()}")
                        print(f"     └─ Capabilities: {capabilities}")
                    continue
                
                elif user_input.lower() == 'reset':
                    coordinator.reset_statistics()
                    simulated_failures.clear()
                    print("🧹 All statistics and simulations reset!")
                    continue
                
                elif user_input.lower() == 'train':
                    print("🎓 Attempting local model training...")
                    training_result = await coordinator.train_local_model(
                        base_model="llama3.1:8b",
                        model_name="dynamic-test-model",
                        min_conversations=1
                    )
                    if training_result.get('success'):
                        print("✅ Local model training successful!")
                    else:
                        print(f"❌ Training failed: {training_result.get('error', 'Unknown error')}")
                    continue
                
                elif user_input.startswith('strategy:'):
                    # Change selection strategy
                    strategy_name = user_input[9:].lower()
                    if strategy_name in available_strategies:
                        coordinator.configure_selection_strategy(available_strategies[strategy_name])
                        current_strategy = strategy_name
                        print(f"✅ Strategy changed to: {strategy_name}")
                    else:
                        print(f"❌ Unknown strategy: {strategy_name}")
                        print(f"Available: {list(available_strategies.keys())}")
                    continue
                
                elif user_input.startswith('config:'):
                    # Configure coordinator settings
                    try:
                        config_part = user_input[7:]
                        if '=' in config_part:
                            key, value = config_part.split('=', 1)
                            key = key.strip()
                            value = value.strip().lower()
                            
                            # Convert string values to appropriate types
                            if value in ['true', 'false']:
                                value = value == 'true'
                            elif value.isdigit():
                                value = int(value)
                            elif value.replace('.', '').isdigit():
                                value = float(value)
                            
                            coordinator.configure(**{key: value})
                            print(f"✅ Configuration updated: {key} = {value}")
                        else:
                            print("❌ Invalid config format. Use: config:key=value")
                    except Exception as e:
                        print(f"❌ Configuration error: {e}")
                    continue
                
                elif user_input.startswith('simulate:fail:'):
                    # Simulate provider failure
                    provider_name = user_input[14:].strip()
                    if provider_name in coordinator.providers:
                        simulated_failures.add(provider_name)
                        print(f"🎭 Simulating failure for {provider_name} (note: actual failure simulation would require provider modification)")
                    else:
                        print(f"❌ Unknown provider: {provider_name}")
                    continue
                
                elif not user_input:
                    continue
                
                # Regular chat query - analyze and execute
                print(f"\n🔍 Processing: '{user_input}'")
                
                # Show pre-chat status
                pre_stats = coordinator.get_usage_statistics()
                print(f"📊 Pre-chat stats: {pre_stats['global']['total_requests']} total requests")
                
                # Execute chat
                start_time = asyncio.get_event_loop().time()
                try:
                    response, flags = await coordinator.chat(user_input)
                    end_time = asyncio.get_event_loop().time()
                    response_time = end_time - start_time
                    
                    # Show results
                    print("\n" + "─" * 60)
                    print("🤖 CHAT RESPONSE")
                    print("─" * 60)
                    print(f"Response: {response}")
                    if flags:
                        print(f"Flags: {flags}")
                    print(f"⏱️  Response time: {response_time:.2f}s")
                    
                    # Show post-chat metrics
                    post_stats = coordinator.get_usage_statistics()
                    requests_delta = post_stats['global']['total_requests'] - pre_stats['global']['total_requests']
                    
                    if requests_delta > 0:
                        print(f"📈 Request processed (+{requests_delta} total requests)")
                        
                        # Try to identify which provider was used (simple heuristic)
                        provider_used = "unknown"
                        for name, provider in coordinator.providers.items():
                            current_requests = provider.get_metrics()['total_requests']
                            previous_requests = pre_stats['providers'].get(name, {}).get('total_requests', 0)
                            if current_requests > previous_requests:
                                provider_used = name
                                break
                        
                        print(f"🎯 Provider used: {provider_used}")
                    
                    print("─" * 60)
                    
                except Exception as e:
                    print(f"❌ Chat failed: {e}")
                    
                    # Show fallback information if it occurred
                    post_stats = coordinator.get_usage_statistics()
                    if post_stats['global']['fallback_count'] > pre_stats['global']['fallback_count']:
                        print("🔄 Fallback mechanism was triggered")
                
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Exiting dynamic testing...")
                break
            except Exception as e:
                print(f"❌ Error during dynamic testing: {e}")
                print("Please try again with a different input.")
    
    async def main():
        """Main test runner with options"""
        print("🤖 HybridCoordinator Test Suite")
        print("=" * 50)
        
        # Check for API key availability
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("⚠️  No API key found. External provider will not be available.")
            print("   Set OPENROUTER_API_KEY or OPENAI_API_KEY for full functionality.")
        
        # Check command line arguments
        if len(sys.argv) > 1:
            mode = sys.argv[1].lower()
            if mode == 'dynamic':
                print("🚀 Running DYNAMIC testing only...")
                coordinator = HybridCoordinator(api_key)
                if await coordinator.initialize():
                    await run_dynamic_tests(coordinator)
                else:
                    print("❌ Failed to initialize coordinator")
                return
            elif mode == 'static':
                print("🧪 Running STATIC testing only...")
                await run_static_tests()
                return
        
        # Default: Run both
        print("🔄 Running BOTH static and dynamic tests...")
        
        # Run static tests first
        coordinator = await run_static_tests()
        
        # Ask user if they want to continue to dynamic testing
        print("\n" + "="*70)
        try:
            choice = input("🤔 Continue to dynamic testing? (y/n): ").strip().lower()
            if choice in ['y', 'yes', '']:
                await run_dynamic_tests(coordinator)
            else:
                print("👋 Skipping dynamic testing. Done!")
        except KeyboardInterrupt:
            print("\n👋 Exiting...")
    
    # Run the main test function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Testing interrupted. Goodbye!")
    except Exception as e:
        print(f"❌ Error running tests: {e}")