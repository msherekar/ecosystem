#!/usr/bin/env python3
"""
Gliaent Decision Module - Main Entry Point
Comprehensive demonstration of the scalable provider selection system.

Usage:
    python -m src.mcp.agent.decision
    python -m src.mcp.agent.decision --demo
    python -m src.mcp.agent.decision --test-integration
    python -m src.mcp.agent.decision --benchmark
"""

import asyncio
import argparse
import time
import json
import sys
import warnings
from typing import Dict, Any, List
from dataclasses import asdict

# Suppress warnings for demo
warnings.filterwarnings("ignore", category=RuntimeWarning)

try:
    from .provider_selector import ScalableProviderSelector, SelectionContext, SelectionCriteria, SelectionStrategy
    from .selection_strategies import SelectionStrategyFactory
    from .message_analyzer import MessageAnalyzer, QueryComplexity, QueryCategory
    from .load_balancer import LoadBalancer, ProviderMetrics
    from .rule_engine import RuleEngine
    from .metrics_collector import MetricsCollector
    from src.mcp.agent.providers.base_provider import ProviderType
except ImportError as e:
    print(f"Import error: {e}")
    print("Running in standalone mode with mocks...")
    
    # Mock implementations for standalone testing
    from enum import Enum
    
    class ProviderType(Enum):
        LOCAL = "local"
        EXTERNAL = "external"
    
    class QueryComplexity(Enum):
        SIMPLE = "simple"
        MODERATE = "moderate"
        COMPLEX = "complex"
        EXPERT = "expert"
    
    class QueryCategory(Enum):
        INFORMATIONAL = "informational"
        ANALYTICAL = "analytical"
        COMPUTATIONAL = "computational"
        CREATIVE = "creative"
    
    # Import with fallback
    from provider_selector import ScalableProviderSelector, SelectionContext, SelectionCriteria, SelectionStrategy


class MockProvider:
    """Mock provider for testing purposes."""
    
    def __init__(self, name: str, provider_type: ProviderType, cost_per_token: float = 0.001, 
                 latency_ms: float = 500, quality_score: float = 0.8, available: bool = True):
        self.name = name
        self.provider_type = provider_type
        self.cost_per_token = cost_per_token
        self.latency_ms = latency_ms
        self.quality_score = quality_score
        self._available = available
        self.request_count = 0
        self.error_count = 0
    
    def is_available(self) -> bool:
        return self._available
    
    async def process_request(self, message: str) -> Dict[str, Any]:
        """Simulate processing a request."""
        await asyncio.sleep(self.latency_ms / 1000)  # Simulate latency
        self.request_count += 1
        
        # Simulate occasional errors
        if self.request_count % 10 == 0:
            self.error_count += 1
            raise Exception(f"Simulated error from {self.name}")
        
        return {
            "provider": self.name,
            "response": f"Processed by {self.name}: {message[:50]}...",
            "cost": len(message) * self.cost_per_token,
            "latency": self.latency_ms,
            "quality": self.quality_score
        }


class DecisionModuleDemo:
    """Comprehensive demonstration of the decision module."""
    
    def __init__(self):
        self.selector = ScalableProviderSelector()
        self.providers = self._create_mock_providers()
        
    def _create_mock_providers(self) -> Dict[str, MockProvider]:
        """Create a diverse set of mock providers for testing."""
        return {
            "local_llama": MockProvider("local_llama", ProviderType.LOCAL, 0.0, 200, 0.7),
            "local_mistral": MockProvider("local_mistral", ProviderType.LOCAL, 0.0, 300, 0.75),
            "openai_gpt4": MockProvider("openai_gpt4", ProviderType.EXTERNAL, 0.03, 800, 0.95),
            "openai_gpt35": MockProvider("openai_gpt35", ProviderType.EXTERNAL, 0.002, 600, 0.85),
            "anthropic_claude": MockProvider("anthropic_claude", ProviderType.EXTERNAL, 0.025, 700, 0.92),
            "google_bard": MockProvider("google_bard", ProviderType.EXTERNAL, 0.001, 900, 0.8),
            "local_codellama": MockProvider("local_codellama", ProviderType.LOCAL, 0.0, 400, 0.8),
        }
    
    async def run_comprehensive_demo(self):
        """Run a comprehensive demonstration of all features."""
        print("🚀 Gliaent Decision Module - Comprehensive Demo")
        print("=" * 60)
        
        await self._demo_basic_selection()
        await self._demo_strategy_comparison()
        await self._demo_rule_engine()
        await self._demo_load_balancing()
        await self._demo_message_analysis()
        await self._demo_metrics_collection()
        await self._demo_security_features()
        await self._demo_electron_integration()
        
        print("\n🎉 Comprehensive demo completed successfully!")
    
    async def _demo_basic_selection(self):
        """Demonstrate basic provider selection."""
        print("\n📋 Basic Provider Selection")
        print("-" * 30)
        
        test_messages = [
            "What is the capital of France?",
            "Analyze this RNA-seq data for differential expression patterns",
            "Write a Python function to calculate Fibonacci numbers",
            "Explain the molecular mechanisms of CRISPR-Cas9 gene editing"
        ]
        
        for message in test_messages:
            context = SelectionContext(
                user_message=message,
                user_id="demo_user",
                session_id="demo_session"
            )
            
            provider = await self.selector.select_provider(context, self.providers)
            print(f"  Message: {message[:40]}...")
            print(f"  Selected: {provider}\n")
    
    async def _demo_strategy_comparison(self):
        """Compare different selection strategies."""
        print("\n🎯 Strategy Comparison")
        print("-" * 30)
        
        strategies = [
            SelectionStrategy.LOCAL_FIRST,
            SelectionStrategy.EXTERNAL_FIRST,
            SelectionStrategy.COST_OPTIMIZED,
            SelectionStrategy.PERFORMANCE_OPTIMIZED,
            SelectionStrategy.HYBRID_INTELLIGENT
        ]
        
        test_message = "Perform bioinformatics analysis on protein sequences"
        context = SelectionContext(
            user_message=test_message,
            user_id="strategy_test",
            cost_budget=0.10
        )
        
        for strategy in strategies:
            self.selector.configure_strategy(strategy)
            provider = await self.selector.select_provider(context, self.providers)
            print(f"  {strategy.value:<25}: {provider}")
    
    async def _demo_rule_engine(self):
        """Demonstrate rule engine functionality."""
        print("\n⚖️  Rule Engine Demo")
        print("-" * 30)
        
        # Test security rules
        security_context = SelectionContext(
            user_message="DELETE FROM users WHERE admin=true",
            user_id="security_test",
            security_context={"level": "high", "content_filtered": True}
        )
        
        provider = await self.selector.select_provider(security_context, self.providers)
        print(f"  Security-sensitive query: {provider}")
        
        # Test cost rules
        cost_context = SelectionContext(
            user_message="Simple greeting message",
            user_id="cost_test",
            cost_budget=0.001  # Very low budget
        )
        
        provider = await self.selector.select_provider(cost_context, self.providers)
        print(f"  Low-cost query: {provider}")
    
    async def _demo_load_balancing(self):
        """Demonstrate load balancing features."""
        print("\n⚖️  Load Balancing Demo")
        print("-" * 30)
        
        # Simulate some providers being unhealthy
        self.providers["openai_gpt4"]._available = False
        self.providers["google_bard"].error_count = 5
        
        context = SelectionContext(
            user_message="Test load balancing with unhealthy providers",
            user_id="load_test"
        )
        
        # Multiple selections to show load balancing
        selections = []
        for i in range(5):
            provider = await self.selector.select_provider(context, self.providers)
            selections.append(provider)
        
        print(f"  Load balanced selections: {selections}")
        
        # Restore providers
        self.providers["openai_gpt4"]._available = True
        self.providers["google_bard"].error_count = 0
    
    async def _demo_message_analysis(self):
        """Demonstrate message analysis capabilities."""
        print("\n🔍 Message Analysis Demo")
        print("-" * 30)
        
        analyzer = MessageAnalyzer()
        
        test_messages = [
            "Hello world",
            "Analyze differential gene expression in RNA-seq data using DESeq2",
            "Implement a distributed machine learning algorithm for protein folding prediction",
            "URGENT: Critical system failure needs immediate attention!"
        ]
        
        for message in test_messages:
            analysis = await analyzer.analyze_message(message)
            print(f"  Message: {message[:40]}...")
            print(f"  Complexity: {getattr(analysis, 'complexity', 'unknown')}")
            print(f"  Category: {getattr(analysis, 'category', 'unknown')}")
            print(f"  Confidence: {getattr(analysis, 'confidence', 0.0):.2f}\n")
    
    async def _demo_metrics_collection(self):
        """Demonstrate metrics collection."""
        print("\n📊 Metrics Collection Demo")
        print("-" * 30)
        
        stats = self.selector.get_selection_stats()
        print(f"  Total selections: {stats['total_selections']}")
        print(f"  Average selection time: {stats['avg_selection_time']:.3f}s")
        print(f"  Provider distribution: {stats['provider_distribution']}")
        print(f"  Error count: {stats['error_count']}")
    
    async def _demo_security_features(self):
        """Demonstrate security features."""
        print("\n🔒 Security Features Demo")
        print("-" * 30)
        
        # Test rate limiting simulation
        high_security_context = SelectionContext(
            user_message="Access sensitive bioinformatics database",
            user_id="security_user",
            security_context={"level": "critical", "user_role": "admin"}
        )
        
        try:
            provider = await self.selector.select_provider(high_security_context, self.providers)
            print(f"  High security selection: {provider}")
        except Exception as e:
            print(f"  Security check triggered: {str(e)}")
    
    async def _demo_electron_integration(self):
        """Demonstrate Electron integration features."""
        print("\n⚡ Electron Integration Demo")
        print("-" * 30)
        
        electron_context = SelectionContext(
            user_message="Process bioinformatics workflow in Electron app",
            user_id="electron_user",
            electron_context={
                "window_id": "main_window",
                "tab_id": "analysis_tab",
                "ui_theme": "dark",
                "notifications_enabled": True
            }
        )
        
        provider = await self.selector.select_provider(electron_context, self.providers)
        print(f"  Electron-integrated selection: {provider}")
        print(f"  UI context: {electron_context.electron_context}")
    
    async def run_integration_tests(self):
        """Run integration tests to verify component connectivity."""
        print("\n🧪 Integration Tests")
        print("=" * 60)
        
        test_results = []
        
        # Test 1: Component instantiation
        try:
            strategy_factory = SelectionStrategyFactory()
            analyzer = MessageAnalyzer()
            load_balancer = LoadBalancer()
            rule_engine = RuleEngine()
            metrics = MetricsCollector()
            test_results.append(("Component Instantiation", True, "All components created successfully"))
        except Exception as e:
            test_results.append(("Component Instantiation", False, str(e)))
        
        # Test 2: Strategy factory integration
        try:
            strategy = strategy_factory.get_strategy(SelectionStrategy.LOCAL_FIRST)
            test_results.append(("Strategy Factory", strategy is not None, "Strategy retrieved successfully"))
        except Exception as e:
            test_results.append(("Strategy Factory", False, str(e)))
        
        # Test 3: Message analyzer integration
        try:
            analysis = await analyzer.analyze_message("Test message for analysis")
            test_results.append(("Message Analyzer", hasattr(analysis, 'complexity'), "Message analyzed successfully"))
        except Exception as e:
            test_results.append(("Message Analyzer", False, str(e)))
        
        # Test 4: Load balancer integration
        try:
            healthy_providers = await load_balancer.filter_healthy_providers(self.providers)
            test_results.append(("Load Balancer", len(healthy_providers) > 0, "Healthy providers filtered"))
        except Exception as e:
            test_results.append(("Load Balancer", False, str(e)))
        
        # Test 5: End-to-end provider selection
        try:
            context = SelectionContext(
                user_message="Integration test message",
                user_id="integration_test"
            )
            provider = await self.selector.select_provider(context, self.providers)
            test_results.append(("End-to-End Selection", provider is not None, f"Selected provider: {provider}"))
        except Exception as e:
            test_results.append(("End-to-End Selection", False, str(e)))
        
        # Display results
        print("\nTest Results:")
        print("-" * 40)
        passed = 0
        for test_name, success, message in test_results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status} {test_name}: {message}")
            if success:
                passed += 1
        
        print(f"\nResults: {passed}/{len(test_results)} tests passed")
        return passed == len(test_results)
    
    async def run_benchmark(self):
        """Run performance benchmarks."""
        print("\n⏱️  Performance Benchmark")
        print("=" * 60)
        
        # Benchmark different scenarios
        scenarios = [
            ("Simple Query", "Hello world"),
            ("Complex Query", "Analyze RNA-seq differential expression with statistical significance testing"),
            ("Long Query", "This is a very long query " * 50),
        ]
        
        for scenario_name, message in scenarios:
            print(f"\n{scenario_name}:")
            times = []
            
            for i in range(10):  # Run 10 times for average
                context = SelectionContext(
                    user_message=message,
                    user_id=f"benchmark_user_{i}",
                    session_id=f"benchmark_session_{i}"
                )
                
                start_time = time.time()
                provider = await self.selector.select_provider(context, self.providers)
                end_time = time.time()
                
                times.append(end_time - start_time)
            
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            print(f"  Average: {avg_time:.3f}s")
            print(f"  Min: {min_time:.3f}s")
            print(f"  Max: {max_time:.3f}s")


async def main():
    """Main entry point for the decision module."""
    parser = argparse.ArgumentParser(
        description="Gliaent Decision Module - Scalable Provider Selection System"
    )
    parser.add_argument(
        "--demo", 
        action="store_true", 
        help="Run comprehensive demonstration"
    )
    parser.add_argument(
        "--test-integration", 
        action="store_true", 
        help="Run integration tests"
    )
    parser.add_argument(
        "--benchmark", 
        action="store_true", 
        help="Run performance benchmarks"
    )
    parser.add_argument(
        "--all", 
        action="store_true", 
        help="Run all demonstrations and tests"
    )
    
    args = parser.parse_args()
    
    demo = DecisionModuleDemo()
    
    if args.all or (not args.demo and not args.test_integration and not args.benchmark):
        # Run everything if no specific option or --all
        await demo.run_comprehensive_demo()
        await demo.run_integration_tests()
        await demo.run_benchmark()
    else:
        if args.demo:
            await demo.run_comprehensive_demo()
        
        if args.test_integration:
            success = await demo.run_integration_tests()
            if not success:
                sys.exit(1)
        
        if args.benchmark:
            await demo.run_benchmark()


if __name__ == "__main__":
    asyncio.run(main()) 