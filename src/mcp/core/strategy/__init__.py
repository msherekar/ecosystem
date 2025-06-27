"""
Strategy Module

Provides analysis strategy patterns for configurable behavior
across different analysis types and workflow stages.

This module exports all strategy components while maintaining
backward compatibility with the original monolithic design.
"""

# Core components
from .base import (
    WorkflowStage,
    ActionRule, 
    InsightRule,
    WorkflowStep,
    AnalysisStrategy
)

# Rule-based strategy base
from .rule_based import RuleBasedAnalysisStrategy

# Specific strategy implementations
from .scrna_strategy import scRNASeqAnalysisStrategy
from .rna_strategy import RNASeqAnalysisStrategy
from .atac_strategy import ATACSeqAnalysisStrategy

# Factory and generic strategy
from .factory import (
    StrategyFactory,
    GenericAnalysisStrategy,
    strategy_registry
)

# Legacy compatibility - maintain old interface names
SuggestedActionStrategy = AnalysisStrategy
RuleBasedActionStrategy = RuleBasedAnalysisStrategy
scRNASeqActionStrategy = scRNASeqAnalysisStrategy
RNASeqActionStrategy = RNASeqAnalysisStrategy
ATACSeqActionStrategy = ATACSeqAnalysisStrategy
GenericActionStrategy = GenericAnalysisStrategy

# Module version
__version__ = "2.0.0"

# Public API
__all__ = [
    # Core components
    "WorkflowStage",
    "ActionRule",
    "InsightRule", 
    "WorkflowStep",
    "AnalysisStrategy",
    
    # Strategy implementations
    "RuleBasedAnalysisStrategy",
    "scRNASeqAnalysisStrategy",
    "RNASeqAnalysisStrategy", 
    "ATACSeqAnalysisStrategy",
    "GenericAnalysisStrategy",
    
    # Factory
    "StrategyFactory",
    "strategy_registry",
    
    # Legacy compatibility
    "SuggestedActionStrategy",
    "RuleBasedActionStrategy",
    "scRNASeqActionStrategy",
    "RNASeqActionStrategy",
    "ATACSeqActionStrategy",
    "GenericActionStrategy",
]


# Test code for module validation
if __name__ == "__main__":
    def test_module_imports():
        """Test that all imports work correctly"""
        print("Testing strategy module imports...")
        
        # Test core components
        assert WorkflowStage is not None, "WorkflowStage should be importable"
        assert ActionRule is not None, "ActionRule should be importable"
        assert InsightRule is not None, "InsightRule should be importable"
        assert WorkflowStep is not None, "WorkflowStep should be importable"
        assert AnalysisStrategy is not None, "AnalysisStrategy should be importable"
        print("✅ Core components imported successfully")
        
        # Test strategy implementations
        assert RuleBasedAnalysisStrategy is not None, "RuleBasedAnalysisStrategy should be importable"
        assert scRNASeqAnalysisStrategy is not None, "scRNASeqAnalysisStrategy should be importable"
        assert RNASeqAnalysisStrategy is not None, "RNASeqAnalysisStrategy should be importable"
        assert ATACSeqAnalysisStrategy is not None, "ATACSeqAnalysisStrategy should be importable"
        print("✅ Strategy implementations imported successfully")
        
        # Test factory
        assert StrategyFactory is not None, "StrategyFactory should be importable"
        assert GenericAnalysisStrategy is not None, "GenericAnalysisStrategy should be importable"
        assert strategy_registry is not None, "strategy_registry should be importable"
        print("✅ Factory components imported successfully")
        
        # Test legacy compatibility
        assert SuggestedActionStrategy is AnalysisStrategy, "Legacy alias should work"
        assert RuleBasedActionStrategy is RuleBasedAnalysisStrategy, "Legacy alias should work"
        assert scRNASeqActionStrategy is scRNASeqAnalysisStrategy, "Legacy alias should work"
        assert RNASeqActionStrategy is RNASeqAnalysisStrategy, "Legacy alias should work"
        assert ATACSeqActionStrategy is ATACSeqAnalysisStrategy, "Legacy alias should work"
        assert GenericActionStrategy is GenericAnalysisStrategy, "Legacy alias should work"
        print("✅ Legacy compatibility aliases work correctly")
        
        # Test __all__ completeness
        expected_exports = len(__all__)
        actual_exports = sum(1 for name in dir() if not name.startswith('_') and name != 'test_module_imports')
        print(f"✅ Module exports {expected_exports} items in __all__")
        
        # Test basic functionality through factory
        available_strategies = StrategyFactory.get_available_strategies()
        print(f"✅ Available strategies: {available_strategies}")
        assert len(available_strategies) >= 3, "Should have at least 3 strategies"
        
        # Test strategy creation
        for strategy_type in available_strategies:
            strategy = StrategyFactory.create_strategy(strategy_type)
            assert strategy is not None, f"Should create {strategy_type} strategy"
            assert hasattr(strategy, 'get_actions'), f"{strategy_type} should have get_actions method"
            assert hasattr(strategy, 'get_insights'), f"{strategy_type} should have get_insights method"
            assert hasattr(strategy, 'get_workflow_steps'), f"{strategy_type} should have get_workflow_steps method"
        
        print("✅ Strategy creation works correctly")
        
        print("🎉 All module import tests passed!")
    
    # Run test
    test_module_imports() 