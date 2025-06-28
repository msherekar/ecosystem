"""
Provider Selection Engine
Intelligent decision making for LLM provider selection.
"""

from typing import Dict, List, Any, Optional
from enum import Enum
import logging

# Handle both relative and absolute imports for standalone testing
try:
    from src.mcp.agent.providers.base_provider import ProviderType
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
    from src.mcp.agent.providers.base_provider import ProviderType


class SelectionStrategy(Enum):
    """Provider selection strategies"""
    LOCAL_FIRST = "local_first"
    EXTERNAL_FIRST = "external_first"
    COST_OPTIMIZED = "cost_optimized"
    PERFORMANCE_OPTIMIZED = "performance_optimized"
    HYBRID_INTELLIGENT = "hybrid_intelligent"


class ProviderSelector:
    """
    Intelligent provider selection engine.
    
    Determines which LLM provider to use based on:
    - Message complexity
    - Cost optimization
    - Provider availability
    - Usage patterns
    - Performance metrics
    """
    
    def __init__(self):
        self.logger = logging.getLogger("provider_selector")
        
        # Selection configuration
        self.strategy = SelectionStrategy.HYBRID_INTELLIGENT
        self.cost_optimization_enabled = True
        self.max_external_calls_per_session = 10
        
        # Message analysis patterns
        self.simple_keywords = [
            "what is", "explain", "define", "how to", "show me",
            "summarize", "describe", "list", "compare", "help"
        ]
        
        self.complex_keywords = [
            "interpret results", "biological significance", "pathway analysis",
            "statistical significance", "recommend next steps", "troubleshoot",
            "comprehensive analysis", "detailed interpretation"
        ]
        
        self.bioinformatics_keywords = [
            "scrna", "rna-seq", "differential expression", "pathway",
            "gene ontology", "clustering", "pca", "umap", "volcano plot"
        ]
    
    def select_provider(
        self,
        user_message: str,
        available_providers: Dict[str, Any],
        usage_stats: Dict[str, int],
        context: Dict[str, Any] = None
    ) -> str:
        """
        Select the best provider for the given message and context.
        
        Args:
            user_message: User's input message
            available_providers: Dict of provider_name -> provider_object
            usage_stats: Current usage statistics
            context: Additional context for decision making
            
        Returns:
            Selected provider name (external, local, etc.)
        """
        
        # Check provider availability
        external_available = self._is_provider_available(available_providers, "external")
        local_available = self._is_provider_available(available_providers, "local")
        
        # If only one provider available, use it
        if external_available and not local_available:
            self.logger.info("Only external provider available")
            return "external"
        elif local_available and not external_available:
            self.logger.info("Only local provider available")
            return "local"
        elif not external_available and not local_available:
            self.logger.warning("No providers available")
            return None
        
        # Both providers available - apply selection strategy
        return self._apply_selection_strategy(
            user_message, usage_stats, context or {}
        )
    
    def _is_provider_available(self, providers: Dict[str, Any], provider_name: str) -> bool:
        """Check if a specific provider is available"""
        provider = providers.get(provider_name)
        return provider is not None and provider.is_available()
    
    def _apply_selection_strategy(
        self,
        user_message: str,
        usage_stats: Dict[str, int],
        context: Dict[str, Any]
    ) -> str:
        """Apply the configured selection strategy"""
        
        if self.strategy == SelectionStrategy.LOCAL_FIRST:
            return "local"
        elif self.strategy == SelectionStrategy.EXTERNAL_FIRST:
            return "external"
        elif self.strategy == SelectionStrategy.COST_OPTIMIZED:
            return self._cost_optimized_selection(user_message, usage_stats)
        elif self.strategy == SelectionStrategy.PERFORMANCE_OPTIMIZED:
            return self._performance_optimized_selection(user_message, context)
        else:  # HYBRID_INTELLIGENT
            return self._intelligent_selection(user_message, usage_stats, context)
    
    def _cost_optimized_selection(self, user_message: str, usage_stats: Dict[str, int]) -> str:
        """Select provider optimized for cost"""
        
        # Always prefer local for cost optimization
        if self._is_simple_query(user_message):
            return "local"
        
        # For complex queries, check if we've exceeded external call limit
        external_calls = usage_stats.get("external_calls", 0)
        if external_calls >= self.max_external_calls_per_session:
            self.logger.info(f"External call limit reached ({external_calls}), using local")
            return "local"
        
        # Use external for complex queries within limit
        return "external"
    
    def _performance_optimized_selection(self, user_message: str, context: Dict[str, Any]) -> str:
        """Select provider optimized for performance/quality"""
        
        # For complex biological analysis, prefer external
        if self._is_complex_query(user_message) or self._is_bioinformatics_query(user_message):
            return "external"
        
        # For simple queries, local is fine and faster
        return "local"
    
    def _intelligent_selection(
        self,
        user_message: str,
        usage_stats: Dict[str, int],
        context: Dict[str, Any]
    ) -> str:
        """Intelligent hybrid selection combining multiple factors"""
        
        # Analyze message complexity
        is_simple = self._is_simple_query(user_message)
        is_complex = self._is_complex_query(user_message)
        is_bio_specific = self._is_bioinformatics_query(user_message)
        
        # Factor 1: Message complexity
        complexity_score = 0
        if is_simple:
            complexity_score -= 2  # Favor local
        if is_complex:
            complexity_score += 3  # Favor external
        if is_bio_specific:
            complexity_score += 1  # Slight favor to external
        
        # Factor 2: Cost optimization
        cost_score = 0
        if self.cost_optimization_enabled:
            external_calls = usage_stats.get("external_calls", 0)
            if external_calls >= self.max_external_calls_per_session:
                cost_score -= 4  # Strong favor to local
            elif external_calls >= self.max_external_calls_per_session * 0.7:
                cost_score -= 2  # Moderate favor to local
        
        # Factor 3: Context analysis
        context_score = 0
        if context.get("analysis_type") == "exploratory":
            context_score -= 1  # Slight favor to local
        elif context.get("analysis_type") == "production":
            context_score += 1  # Slight favor to external
        
        # Factor 4: Session state
        session_score = 0
        if context.get("has_analysis_results"):
            session_score += 1  # Favor external for interpretation
        
        # Calculate final score
        total_score = complexity_score + cost_score + context_score + session_score
        
        # Make decision
        if total_score > 0:
            selected = "external"
        else:
            selected = "local"
        
        self.logger.info(
            f"Intelligent selection: {selected} "
            f"(complexity: {complexity_score}, cost: {cost_score}, "
            f"context: {context_score}, session: {session_score}, total: {total_score})"
        )
        
        return selected
    
    def _is_simple_query(self, message: str) -> bool:
        """Check if message is a simple query suitable for local LLM"""
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in self.simple_keywords)
    
    def _is_complex_query(self, message: str) -> bool:
        """Check if message is a complex query that might need external LLM"""
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in self.complex_keywords)
    
    def _is_bioinformatics_query(self, message: str) -> bool:
        """Check if message is bioinformatics-specific"""
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in self.bioinformatics_keywords)
    
    def configure_strategy(
        self,
        strategy: SelectionStrategy,
        cost_optimization: bool = True,
        max_external_calls: int = 10
    ):
        """Configure the selection strategy"""
        self.strategy = strategy
        self.cost_optimization_enabled = cost_optimization
        self.max_external_calls_per_session = max_external_calls
        
        self.logger.info(
            f"Strategy configured: {strategy.value}, "
            f"cost_opt: {cost_optimization}, max_calls: {max_external_calls}"
        )
    
    def get_selection_explanation(self, provider: str, factors: Dict[str, Any]) -> str:
        """Generate human-readable explanation for provider selection"""
        if provider == "local":
            return "Using local model for cost efficiency and fast response."
        elif provider == "external":
            return "Using external model for enhanced analysis capabilities."
        else:
            return "No suitable provider available."


if __name__ == "__main__":
    # Suppress the RuntimeWarning about module import behavior
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning, 
                          message=".*found in sys.modules.*")
    """Test the provider selector individually"""
    
    def test_provider_selector():
        print("🧪 Testing ProviderSelector...")
        
        # Create selector
        selector = ProviderSelector()
        
        # Test configuration
        selector.configure_strategy(
            SelectionStrategy.HYBRID_INTELLIGENT,
            cost_optimization=True,
            max_external_calls=5
        )
        print("✅ Strategy configuration successful")
        
        # Create mock providers
        class MockProvider:
            def __init__(self, available=True):
                self._available = available
            def is_available(self):
                return self._available
        
        mock_providers = {
            "external": MockProvider(True),
            "local": MockProvider(True)
        }
        
        # Test different query types
        test_queries = [
            ("what is RNA-seq?", "simple query"),
            ("interpret my differential expression results", "complex query"),
            ("cluster my scRNA-seq data", "bioinformatics query"),
            ("show me the data", "simple query"),
            ("comprehensive pathway analysis needed", "complex query")
        ]
        
        print("\n🔍 Testing query classification:")
        for query, expected_type in test_queries:
            is_simple = selector._is_simple_query(query)
            is_complex = selector._is_complex_query(query)
            is_bio = selector._is_bioinformatics_query(query)
            
            print(f"   '{query[:30]}...'")
            print(f"     Simple: {is_simple}, Complex: {is_complex}, Bio: {is_bio}")
        
        # Test provider selection
        print("\n🎯 Testing provider selection:")
        
        test_cases = [
            {
                "query": "what is RNA-seq?",
                "usage_stats": {"external_calls": 0, "local_calls": 5},
                "context": {}
            },
            {
                "query": "interpret my pathway analysis results",
                "usage_stats": {"external_calls": 8, "local_calls": 2},
                "context": {"analysis_type": "production"}
            },
            {
                "query": "show me the data",
                "usage_stats": {"external_calls": 12, "local_calls": 1},
                "context": {"analysis_type": "exploratory"}
            }
        ]
        
        for i, case in enumerate(test_cases, 1):
            selected = selector.select_provider(
                user_message=case["query"],
                available_providers=mock_providers,
                usage_stats=case["usage_stats"],
                context=case["context"]
            )
            explanation = selector.get_selection_explanation(selected, {})
            print(f"   Test {i}: '{case['query'][:30]}...' → {selected}")
            print(f"     Reason: {explanation}")
        
        # Test different strategies
        print("\n⚙️  Testing different strategies:")
        strategies = [
            SelectionStrategy.LOCAL_FIRST,
            SelectionStrategy.EXTERNAL_FIRST,
            SelectionStrategy.COST_OPTIMIZED,
            SelectionStrategy.PERFORMANCE_OPTIMIZED
        ]
        
        for strategy in strategies:
            selector.configure_strategy(strategy)
            selected = selector.select_provider(
                user_message="analyze my data",
                available_providers=mock_providers,
                usage_stats={"external_calls": 3, "local_calls": 2},
                context={}
            )
            print(f"   {strategy.value}: {selected}")
        
        # Test edge cases
        print("\n🚨 Testing edge cases:")
        
        # No providers available
        empty_providers = {
            "external": MockProvider(False),
            "local": MockProvider(False)
        }
        
        selected = selector.select_provider(
            user_message="test",
            available_providers=empty_providers,
            usage_stats={},
            context={}
        )
        print(f"   No providers available: {selected}")
        
        # Only one provider available
        external_only = {
            "external": MockProvider(True),
            "local": MockProvider(False)
        }
        
        selected = selector.select_provider(
            user_message="test",
            available_providers=external_only,
            usage_stats={},
            context={}
        )
        print(f"   External only: {selected}")
        
        print("🎉 Provider selector tests completed!")
    
    # Run tests
    test_provider_selector()