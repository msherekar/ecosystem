"""
Plugin-based Selection Strategies
Modular strategies for intelligent provider selection.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import structlog

try:
    from .provider_selector import SelectionStrategy, SelectionContext, SelectionCriteria
except ImportError:
    # For standalone testing
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))


class SelectionResult:
    """Result from a selection strategy."""
    def __init__(self, provider: str, confidence: float, reasoning: str):
        self.provider = provider
        self.confidence = confidence
        self.reasoning = reasoning


class BaseSelectionStrategy(ABC):
    """Abstract base class for all selection strategies."""
    
    def __init__(self):
        self.logger = structlog.get_logger(f"strategy.{self.get_strategy_name()}")
    
    @abstractmethod
    async def select_provider(
        self,
        context: 'SelectionContext',
        available_providers: Dict[str, Any],
        criteria: 'SelectionCriteria',
        message_analysis: Any = None
    ) -> Optional[str]:
        """Select the best provider based on this strategy."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the strategy identifier."""
        pass
    
    def get_selection_confidence(self, context: 'SelectionContext') -> float:
        """Return confidence score for this strategy (0-1)."""
        return 1.0
    
    def _is_provider_available(self, providers: Dict[str, Any], provider_name: str) -> bool:
        """Check if a specific provider is available."""
        provider = providers.get(provider_name)
        return provider is not None and provider.is_available()


class LocalFirstStrategy(BaseSelectionStrategy):
    """Always prefer local providers when available."""
    
    async def select_provider(
        self,
        context: 'SelectionContext',
        available_providers: Dict[str, Any],
        criteria: 'SelectionCriteria',
        message_analysis: Any = None
    ) -> Optional[str]:
        
        # First try local providers
        for name, provider in available_providers.items():
            if (hasattr(provider, 'provider_type') and 
                'local' in name.lower() and provider.is_available()):
                self.logger.info("Selected local provider", provider=name)
                return name
        
        # Fallback to any available provider
        for name, provider in available_providers.items():
            if provider.is_available():
                self.logger.info("Fallback to non-local provider", provider=name)
                return name
        
        return None
    
    def get_strategy_name(self) -> str:
        return "local_first"


class ExternalFirstStrategy(BaseSelectionStrategy):
    """Always prefer external providers when available."""
    
    async def select_provider(
        self,
        context: 'SelectionContext',
        available_providers: Dict[str, Any],
        criteria: 'SelectionCriteria',
        message_analysis: Any = None
    ) -> Optional[str]:
        
        # First try external providers
        for name, provider in available_providers.items():
            if (hasattr(provider, 'provider_type') and 
                'external' in name.lower() and provider.is_available()):
                self.logger.info("Selected external provider", provider=name)
                return name
        
        # Fallback to any available provider
        for name, provider in available_providers.items():
            if provider.is_available():
                self.logger.info("Fallback to non-external provider", provider=name)
                return name
        
        return None
    
    def get_strategy_name(self) -> str:
        return "external_first"


class CostOptimizedStrategy(BaseSelectionStrategy):
    """Select provider optimized for cost efficiency."""
    
    def __init__(self):
        super().__init__()
        self.cost_threshold = 0.10  # Max cost per request
        self.external_call_limit = 10  # Per session limit
    
    async def select_provider(
        self,
        context: 'SelectionContext',
        available_providers: Dict[str, Any],
        criteria: 'SelectionCriteria',
        message_analysis: Any = None
    ) -> Optional[str]:
        
        # Check budget constraints
        if context.cost_budget and context.cost_budget < self.cost_threshold:
            self.logger.info("Budget constraint: selecting cheapest option")
            return self._select_cheapest_provider(available_providers)
        
        # Check external call limits
        external_calls = context.usage_stats.get('external_calls', 0)
        if external_calls >= self.external_call_limit:
            self.logger.info("External call limit reached, preferring local")
            return self._select_local_provider(available_providers)
        
        # For simple queries, prefer local (cheaper)
        if (message_analysis and 
            hasattr(message_analysis, 'complexity') and 
            message_analysis.complexity.value <= 2):
            local_provider = self._select_local_provider(available_providers)
            if local_provider:
                return local_provider
        
        # Default to cost-effective choice
        return self._select_cost_effective_provider(available_providers, criteria)
    
    def _select_cheapest_provider(self, providers: Dict[str, Any]) -> Optional[str]:
        """Select the cheapest available provider."""
        # Assume local providers are cheaper
        for name, provider in providers.items():
            if 'local' in name.lower() and provider.is_available():
                return name
        
        # Fallback to first available
        for name, provider in providers.items():
            if provider.is_available():
                return name
        
        return None
    
    def _select_local_provider(self, providers: Dict[str, Any]) -> Optional[str]:
        """Select a local provider if available."""
        for name, provider in providers.items():
            if 'local' in name.lower() and provider.is_available():
                return name
        return None
    
    def _select_cost_effective_provider(
        self, 
        providers: Dict[str, Any], 
        criteria: 'SelectionCriteria'
    ) -> Optional[str]:
        """Select the most cost-effective provider."""
        # Simple heuristic: prefer local unless external is specifically needed
        local_provider = self._select_local_provider(providers)
        if local_provider:
            return local_provider
        
        # Fallback to any available
        for name, provider in providers.items():
            if provider.is_available():
                return name
        
        return None
    
    def get_strategy_name(self) -> str:
        return "cost_optimized"


class PerformanceOptimizedStrategy(BaseSelectionStrategy):
    """Select provider optimized for performance and quality."""
    
    async def select_provider(
        self,
        context: 'SelectionContext',
        available_providers: Dict[str, Any],
        criteria: 'SelectionCriteria',
        message_analysis: Any = None
    ) -> Optional[str]:
        
        # For complex analysis, prefer external (higher quality)
        if (message_analysis and 
            hasattr(message_analysis, 'complexity') and 
            message_analysis.complexity.value >= 3):
            external_provider = self._select_external_provider(available_providers)
            if external_provider:
                self.logger.info("Complex query: selected external provider")
                return external_provider
        
        # For bioinformatics queries, prefer external
        if (message_analysis and 
            hasattr(message_analysis, 'domain_specificity') and 
            message_analysis.domain_specificity > 0.7):
            external_provider = self._select_external_provider(available_providers)
            if external_provider:
                self.logger.info("Domain-specific query: selected external provider")
                return external_provider
        
        # For production context, prefer higher quality
        if context.session_context.get('type') == 'production':
            external_provider = self._select_external_provider(available_providers)
            if external_provider:
                return external_provider
        
        # Default to fastest available
        return self._select_fastest_provider(available_providers)
    
    def _select_external_provider(self, providers: Dict[str, Any]) -> Optional[str]:
        """Select an external provider if available."""
        for name, provider in providers.items():
            if 'external' in name.lower() and provider.is_available():
                return name
        return None
    
    def _select_fastest_provider(self, providers: Dict[str, Any]) -> Optional[str]:
        """Select the fastest provider (assume local is faster)."""
        # Local providers are typically faster
        for name, provider in providers.items():
            if 'local' in name.lower() and provider.is_available():
                return name
        
        # Fallback to any available
        for name, provider in providers.items():
            if provider.is_available():
                return name
        
        return None
    
    def get_strategy_name(self) -> str:
        return "performance_optimized"


class SelectionStrategyFactory:
    """Factory for creating selection strategy instances."""
    
    def __init__(self):
        self._strategies = {
            'local_first': LocalFirstStrategy,
            'external_first': ExternalFirstStrategy,
            'cost_optimized': CostOptimizedStrategy,
            'performance_optimized': PerformanceOptimizedStrategy,
            'hybrid_intelligent': PerformanceOptimizedStrategy,  # Use performance as fallback
            'load_balanced': CostOptimizedStrategy,  # Use cost as fallback
        }
        self._instances = {}
    
    def get_strategy(self, strategy_name: str) -> BaseSelectionStrategy:
        """Get strategy instance by name."""
        if hasattr(strategy_name, 'value'):
            strategy_name = strategy_name.value
        
        if strategy_name not in self._instances:
            strategy_class = self._strategies.get(strategy_name)
            if not strategy_class:
                raise ValueError(f"Unknown strategy: {strategy_name}")
            self._instances[strategy_name] = strategy_class()
        
        return self._instances[strategy_name]
    
    def register_strategy(self, name: str, strategy_class: type):
        """Register a custom strategy."""
        self._strategies[name] = strategy_class
        # Clear instance cache for this strategy
        if name in self._instances:
            del self._instances[name]
    
    def list_strategies(self) -> List[str]:
        """List all available strategies."""
        return list(self._strategies.keys())


def main():
    """Main function for testing selection strategies."""
    import asyncio
    from dataclasses import dataclass
    
    @dataclass
    class MockAnalysis:
        complexity: Any
        domain_specificity: float = 0.5
        
    class MockComplexity:
        def __init__(self, value):
            self.value = value
    
    async def test_strategies():
        print("🧪 Testing Selection Strategies...")
        
        factory = SelectionStrategyFactory()
        
        # Mock context and providers
        context_data = {
            'user_message': "Analyze my RNA-seq data",
            'user_id': "test_user",
            'session_id': "test_session",
            'usage_stats': {'external_calls': 5, 'local_calls': 10},
            'cost_budget': 0.25,
            'session_context': {'type': 'production'},
            'user_preferences': {'preferred_provider': 'external'},
            'provider_metrics': {
                'external': {'success_rate': 0.95, 'avg_response_time': 2.0},
                'local': {'success_rate': 0.85, 'avg_response_time': 0.5}
            }
        }
        
        class MockProvider:
            def is_available(self):
                return True
        
        providers = {
            'external': MockProvider(),
            'local': MockProvider()
        }
        
        # Mock message analysis
        analysis = MockAnalysis(
            complexity=MockComplexity(3),
            domain_specificity=0.8
        )
        
        # Test each strategy
        strategies = factory.list_strategies()
        
        for strategy_name in strategies:
            strategy = factory.get_strategy(strategy_name)
            
            # We need to mock the context object properly for testing
            # In real implementation, this would be a proper SelectionContext instance
            mock_context = type('MockContext', (), context_data)
            mock_criteria = type('MockCriteria', (), {
                'min_quality_score': 0.7,
                'max_cost_per_request': 0.20
            })
            
            try:
                selected = await strategy.select_provider(
                    mock_context, providers, mock_criteria, analysis
                )
                print(f"✅ {strategy_name}: {selected}")
            except Exception as e:
                print(f"❌ {strategy_name}: Error - {e}")
        
        print("🎉 Strategy testing completed!")
    
    asyncio.run(test_strategies())


if __name__ == "__main__":
    main() 