#!/usr/bin/env python3
"""
Comprehensive Integration Tests for Gliaent Decision Module
Tests connectivity and functionality between all components.

Usage:
    python src/mcp/agent/decision/test_integration.py
    python -m pytest src/mcp/agent/decision/test_integration.py -v
"""

import asyncio
import time
import warnings
from typing import Dict, Any
import sys
import os

# Add the project root to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..'))

# Suppress warnings for testing
warnings.filterwarnings("ignore", category=RuntimeWarning)

# Test imports - this verifies that all modules can be imported successfully
try:
    from src.mcp.agent.decision.provider_selector import (
        ScalableProviderSelector, SelectionContext, SelectionCriteria, 
        SelectionStrategy
    )
    from src.mcp.agent.decision.selection_strategies import SelectionStrategyFactory
    from src.mcp.agent.decision.message_analyzer import MessageAnalyzer
    from src.mcp.agent.decision.load_balancer import LoadBalancer
    from src.mcp.agent.decision.rule_engine import RuleEngine
    from src.mcp.agent.decision.metrics_collector import MetricsCollector
    from src.mcp.agent.providers.base_provider import ProviderType
    
    IMPORTS_SUCCESSFUL = True
    IMPORT_ERROR = None
except ImportError as e:
    IMPORTS_SUCCESSFUL = False
    IMPORT_ERROR = str(e)
    
    # Create mock classes for testing when imports fail
    from enum import Enum
    from dataclasses import dataclass
    
    class ProviderType(Enum):
        LOCAL = "local"
        EXTERNAL = "external"
    
    @dataclass
    class SelectionContext:
        user_message: str
        user_id: str = "test_user"


class TestProvider:
    """Test provider for integration testing."""
    
    def __init__(self, name: str, provider_type: ProviderType, available: bool = True):
        self.name = name
        self.provider_type = provider_type
        self._available = available
        self.request_count = 0
        self.error_count = 0
    
    def is_available(self) -> bool:
        return self._available
    
    async def process_request(self, message: str) -> Dict[str, Any]:
        """Simulate processing a request."""
        self.request_count += 1
        await asyncio.sleep(0.01)  # Small delay to simulate processing
        
        return {
            "provider": self.name,
            "response": f"Response from {self.name}",
            "cost": 0.001,
            "latency": 10
        }


class ComponentConnectivityTests:
    """Test connectivity between all decision module components."""
    
    def __init__(self):
        self.test_results = []
        self.providers = self._create_test_providers()
    
    def _create_test_providers(self) -> Dict[str, TestProvider]:
        """Create test providers for integration testing."""
        return {
            "local_test": TestProvider("local_test", ProviderType.LOCAL),
            "external_test": TestProvider("external_test", ProviderType.EXTERNAL),
            "local_backup": TestProvider("local_backup", ProviderType.LOCAL),
            "external_backup": TestProvider("external_backup", ProviderType.EXTERNAL),
        }
    
    def log_result(self, test_name: str, success: bool, message: str):
        """Log test results."""
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message
        })
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {test_name}: {message}")
    
    async def test_import_connections(self):
        """Test that all modules can be imported and instantiated."""
        print("\n🔗 Testing Import Connections")
        print("-" * 40)
        
        if not IMPORTS_SUCCESSFUL:
            self.log_result("Module Imports", False, f"Import failed: {IMPORT_ERROR}")
            return False
        
        try:
            # Test instantiation of all major components
            selector = ScalableProviderSelector()
            strategy_factory = SelectionStrategyFactory()
            analyzer = MessageAnalyzer()
            load_balancer = LoadBalancer()
            rule_engine = RuleEngine()
            metrics = MetricsCollector()
            
            self.log_result("Module Imports", True, "All modules imported and instantiated successfully")
            return True
            
        except Exception as e:
            self.log_result("Module Imports", False, f"Failed to instantiate components: {str(e)}")
            return False
    
    async def test_provider_selector_to_strategies(self):
        """Test connection between provider selector and selection strategies."""
        print("\n🎯 Testing Provider Selector <-> Strategies Connection")
        print("-" * 40)
        
        try:
            selector = ScalableProviderSelector()
            
            # Test different strategies
            strategies = [
                SelectionStrategy.LOCAL_FIRST,
                SelectionStrategy.EXTERNAL_FIRST,
                SelectionStrategy.COST_OPTIMIZED,
                SelectionStrategy.PERFORMANCE_OPTIMIZED,
                SelectionStrategy.HYBRID_INTELLIGENT
            ]
            
            for strategy in strategies:
                try:
                    selector.configure_strategy(strategy)
                    context = SelectionContext(
                        user_message=f"Test strategy {strategy.value}",
                        user_id="strategy_test"
                    )
                    
                    result = await selector.select_provider(context, self.providers)
                    self.log_result(f"Strategy {strategy.value}", result is not None, f"Selected: {result}")
                    
                except Exception as e:
                    self.log_result(f"Strategy {strategy.value}", False, str(e))
                    return False
            
            return True
            
        except Exception as e:
            self.log_result("Selector-Strategy Connection", False, str(e))
            return False
    
    async def test_message_analyzer_integration(self):
        """Test message analyzer integration with the main selector."""
        print("\n🔍 Testing Message Analyzer Integration")
        print("-" * 40)
        
        try:
            analyzer = MessageAnalyzer()
            
            test_messages = [
                "Simple hello world",
                "Complex bioinformatics analysis of RNA-seq differential expression",
                "URGENT system alert requiring immediate attention"
            ]
            
            for message in test_messages:
                try:
                    analysis = await analyzer.analyze_message(message)
                    
                    # Check that analysis has expected attributes
                    has_complexity = hasattr(analysis, 'complexity')
                    has_category = hasattr(analysis, 'category') 
                    has_confidence = hasattr(analysis, 'confidence')
                    
                    if has_complexity and has_category and has_confidence:
                        self.log_result(f"Analysis: {message[:30]}...", True, 
                                      f"Complexity: {getattr(analysis.complexity, 'name', analysis.complexity)}")
                    else:
                        self.log_result(f"Analysis: {message[:30]}...", False, "Missing analysis attributes")
                        
                except Exception as e:
                    self.log_result(f"Analysis: {message[:30]}...", False, str(e))
            
            return True
            
        except Exception as e:
            self.log_result("Message Analyzer Integration", False, str(e))
            return False
    
    async def test_load_balancer_integration(self):
        """Test load balancer integration with provider selection."""
        print("\n⚖️  Testing Load Balancer Integration")
        print("-" * 40)
        
        try:
            load_balancer = LoadBalancer()
            
            # Test healthy provider filtering
            healthy_providers = await load_balancer.filter_healthy_providers(self.providers)
            self.log_result("Healthy Provider Filtering", 
                          len(healthy_providers) > 0, 
                          f"Found {len(healthy_providers)} healthy providers")
            
            # Test with some providers unavailable
            self.providers["external_test"]._available = False
            filtered_providers = await load_balancer.filter_healthy_providers(self.providers)
            
            if len(filtered_providers) < len(self.providers):
                self.log_result("Unhealthy Provider Filtering", True, 
                              f"Filtered to {len(filtered_providers)} providers")
            else:
                self.log_result("Unhealthy Provider Filtering", False, 
                              "Failed to filter unhealthy providers")
            
            # Restore provider
            self.providers["external_test"]._available = True
            
            return True
            
        except Exception as e:
            self.log_result("Load Balancer Integration", False, str(e))
            return False
    
    async def test_rule_engine_integration(self):
        """Test rule engine integration with provider selection."""
        print("\n⚖️  Testing Rule Engine Integration")
        print("-" * 40)
        
        try:
            rule_engine = RuleEngine()
            
            # Test rule evaluation with different contexts
            test_contexts = [
                SelectionContext(
                    user_message="Simple test message",
                    user_id="normal_user"
                ),
                SelectionContext(
                    user_message="Analyze bioinformatics data for research",
                    user_id="researcher"
                )
            ]
            
            for i, context in enumerate(test_contexts):
                try:
                    result = rule_engine.evaluate_rules(context, self.providers)
                    self.log_result(f"Rule Evaluation {i+1}", True, 
                                  f"Result: {result if result else 'No rule matched'}")
                except Exception as e:
                    self.log_result(f"Rule Evaluation {i+1}", False, str(e))
            
            return True
            
        except Exception as e:
            self.log_result("Rule Engine Integration", False, str(e))
            return False
    
    async def test_metrics_collector_integration(self):
        """Test metrics collector integration."""
        print("\n📊 Testing Metrics Collector Integration")
        print("-" * 40)
        
        try:
            metrics = MetricsCollector()
            
            # Test recording metrics
            context = SelectionContext(
                user_message="Test metrics recording",
                user_id="metrics_user"
            )
            
            await metrics.record_selection(context, "local_test", "test_strategy", 0.1)
            self.log_result("Metrics Recording", True, "Metrics recorded successfully")
            
            # Test retrieving metrics
            try:
                aggregated_metrics = metrics.get_aggregated_metrics()
                self.log_result("Metrics Retrieval", True, f"Retrieved aggregated metrics successfully")
            except Exception as e:
                self.log_result("Metrics Retrieval", False, str(e))
            
            return True
            
        except Exception as e:
            self.log_result("Metrics Collector Integration", False, str(e))
            return False
    
    async def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow with all components."""
        print("\n🔄 Testing End-to-End Workflow")
        print("-" * 40)
        
        try:
            selector = ScalableProviderSelector()
            
            # Test different workflow scenarios
            scenarios = [
                {
                    "name": "Simple Selection",
                    "context": SelectionContext(
                        user_message="What is the weather today?",
                        user_id="simple_user"
                    )
                },
                {
                    "name": "Complex Analysis",
                    "context": SelectionContext(
                        user_message="Perform differential gene expression analysis on RNA-seq data",
                        user_id="researcher"
                    )
                },
                {
                    "name": "Cost-Conscious Query",
                    "context": SelectionContext(
                        user_message="Simple calculation task",
                        user_id="budget_user"
                    )
                }
            ]
            
            for scenario in scenarios:
                try:
                    result = await selector.select_provider(scenario["context"], self.providers)
                    self.log_result(scenario["name"], result is not None, f"Selected: {result}")
                except Exception as e:
                    self.log_result(scenario["name"], False, str(e))
            
            # Test statistics collection
            stats = selector.get_selection_stats()
            self.log_result("Statistics Collection", 
                          stats['total_selections'] > 0,
                          f"Recorded {stats['total_selections']} selections")
            
            return True
            
        except Exception as e:
            self.log_result("End-to-End Workflow", False, str(e))
            return False
    
    async def test_error_handling_connections(self):
        """Test error handling across component connections."""
        print("\n🛡️  Testing Error Handling Connections")
        print("-" * 40)
        
        try:
            selector = ScalableProviderSelector()
            
            # Test with no providers
            result = await selector.select_provider(
                SelectionContext(user_message="Test with no providers"),
                {}
            )
            self.log_result("No Providers Handling", result is None, 
                          "Correctly handled no providers scenario")
            
            # Test with all providers unavailable
            unavailable_providers = {name: provider for name, provider in self.providers.items()}
            for provider in unavailable_providers.values():
                provider._available = False
            
            result = await selector.select_provider(
                SelectionContext(user_message="Test with unavailable providers"),
                unavailable_providers
            )
            
            # Restore providers
            for provider in self.providers.values():
                provider._available = True
            
            self.log_result("Unavailable Providers", True, 
                          f"Handled unavailable providers: {result}")
            
            return True
            
        except Exception as e:
            self.log_result("Error Handling Connections", False, str(e))
            return False
    
    def generate_test_report(self):
        """Generate comprehensive test report."""
        print("\n📋 Integration Test Report")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {passed_tests/total_tests*100:.1f}%" if total_tests > 0 else "No tests run")
        
        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        return passed_tests == total_tests
    
    async def run_all_tests(self):
        """Run all integration tests."""
        print("🧪 Decision Module Component Connectivity Tests")
        print("=" * 60)
        
        # Execute all tests
        tests = [
            self.test_import_connections(),
            self.test_provider_selector_to_strategies(),
            self.test_message_analyzer_integration(),
            self.test_load_balancer_integration(),
            self.test_rule_engine_integration(),
            self.test_metrics_collector_integration(),
            self.test_end_to_end_workflow(),
            self.test_error_handling_connections()
        ]
        
        # Run tests sequentially for clear output
        for test in tests:
            await test
        
        # Generate final report
        success = self.generate_test_report()
        
        if success:
            print("\n🎉 All connectivity tests passed! Components are properly integrated.")
        else:
            print("\n⚠️  Some connectivity tests failed. Check component integration.")
        
        return success


async def main():
    """Main function for running connectivity tests."""
    tester = ComponentConnectivityTests()
    return await tester.run_all_tests()


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1) 