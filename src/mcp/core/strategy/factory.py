"""
Strategy Factory and Generic Strategy

Contains the factory for creating analysis strategies and
a generic fallback strategy for unknown analysis types.
"""

from typing import List, Dict, Type
from .base import AnalysisStrategy
from .rule_based import RuleBasedAnalysisStrategy
from .scrna_strategy import scRNASeqAnalysisStrategy
from .rna_strategy import RNASeqAnalysisStrategy
from .atac_strategy import ATACSeqAnalysisStrategy


class GenericAnalysisStrategy(RuleBasedAnalysisStrategy):
    """Generic strategy for unknown analysis types"""
    
    def _initialize_rules(self):
        """Initialize generic rules"""
        # Basic action rules
        self.add_action_rule(
            condition=lambda ctx: not ctx.get("data_uploaded", False),
            action="Upload data files for analysis",
            priority=10
        )
        
        self.add_action_rule(
            condition=lambda ctx: ctx.get("data_uploaded", False),
            action="Begin analysis workflow",
            priority=5
        )
        
        self.add_action_rule(
            condition=lambda ctx: ctx.get("data_uploaded", False) and not ctx.get("analysis_started", False),
            action="Configure analysis parameters",
            priority=4
        )
        
        self.add_action_rule(
            condition=lambda ctx: ctx.get("analysis_started", False) and not ctx.get("analysis_complete", False),
            action="Review analysis progress",
            priority=3
        )
        
        # Basic insight rules
        self.add_insight_rule(
            condition=lambda ctx: ctx.get("data_uploaded", False),
            insight_generator=lambda ctx: "Data uploaded and ready for analysis",
            priority=5,
            category="general"
        )
        
        self.add_insight_rule(
            condition=lambda ctx: ctx.get("analysis_started", False),
            insight_generator=lambda ctx: "Analysis workflow initiated",
            priority=4,
            category="general"
        )
        
        self.add_insight_rule(
            condition=lambda ctx: ctx.get("analysis_complete", False),
            insight_generator=lambda ctx: "Analysis workflow completed",
            priority=8,
            category="general"
        )


class StrategyFactory:
    """Factory for creating analysis strategies"""
    
    _strategies: Dict[str, Type[AnalysisStrategy]] = {
        "scrnaseq": scRNASeqAnalysisStrategy,
        "rnaseq": RNASeqAnalysisStrategy,
        "atacseq": ATACSeqAnalysisStrategy
    }
    
    @classmethod
    def create_strategy(cls, analysis_type: str) -> AnalysisStrategy:
        """Create strategy for analysis type"""
        strategy_class = cls._strategies.get(analysis_type.lower())
        if strategy_class:
            return strategy_class()
        
        # Return generic strategy for unknown types
        return GenericAnalysisStrategy(analysis_type)
    
    @classmethod
    def register_strategy(cls, analysis_type: str, strategy_class: Type[AnalysisStrategy]):
        """Register new strategy"""
        cls._strategies[analysis_type.lower()] = strategy_class
    
    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """Get list of available strategies"""
        return list(cls._strategies.keys())
    
    @classmethod
    def unregister_strategy(cls, analysis_type: str):
        """Unregister a strategy"""
        analysis_type_lower = analysis_type.lower()
        if analysis_type_lower in cls._strategies:
            del cls._strategies[analysis_type_lower]
    
    @classmethod
    def is_strategy_registered(cls, analysis_type: str) -> bool:
        """Check if a strategy is registered"""
        return analysis_type.lower() in cls._strategies


# Global strategy registry instance
strategy_registry = StrategyFactory()


# Test code for independent validation
if __name__ == "__main__":
    # Suppress the RuntimeWarning about module import behavior
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning, 
                          message=".*found in sys.modules.*")
    
    def test_strategy_factory():
        """Test StrategyFactory functionality"""
        print("Testing StrategyFactory...")
        
        # Test available strategies
        available = StrategyFactory.get_available_strategies()
        print(f"✅ Available strategies: {available}")
        assert len(available) >= 3, f"Should have at least 3 strategies, got {len(available)}"
        assert "scrnaseq" in available, "Should include scrnaseq"
        assert "rnaseq" in available, "Should include rnaseq"
        assert "atacseq" in available, "Should include atacseq"
        
        # Test strategy creation for each registered type
        for strategy_type in available:
            strategy = StrategyFactory.create_strategy(strategy_type)
            print(f"✅ Created {strategy_type} strategy: {strategy.__class__.__name__}")
            
            # Test basic functionality
            empty_context = {}
            actions = strategy.get_actions(empty_context)
            insights = strategy.get_insights(empty_context)
            workflow_steps = strategy.get_workflow_steps()
            
            assert len(actions) > 0, f"{strategy_type} should have at least one action"
            assert isinstance(insights, str), f"{strategy_type} should return string insights"
            assert len(workflow_steps) > 0, f"{strategy_type} should have workflow steps"
        
        # Test generic strategy for unknown type
        unknown_strategy = StrategyFactory.create_strategy("unknown_type")
        print(f"✅ Generic strategy: {unknown_strategy.__class__.__name__}")
        assert isinstance(unknown_strategy, GenericAnalysisStrategy), "Should return GenericAnalysisStrategy"
        assert unknown_strategy.analysis_type == "unknown_type", "Should preserve analysis type"
        
        # Test case insensitivity
        scrna_upper = StrategyFactory.create_strategy("SCRNASEQ")
        scrna_lower = StrategyFactory.create_strategy("scrnaseq")
        assert type(scrna_upper) == type(scrna_lower), "Should be case insensitive"
        
        # Test strategy registration
        class TestCustomStrategy(RuleBasedAnalysisStrategy):
            def __init__(self):
                super().__init__("custom_test")
            
            def _initialize_rules(self):
                self.add_action_rule(
                    condition=lambda ctx: True,
                    action="Custom test action",
                    priority=1
                )
        
        initial_count = len(StrategyFactory.get_available_strategies())
        StrategyFactory.register_strategy("custom_test", TestCustomStrategy)
        
        new_count = len(StrategyFactory.get_available_strategies())
        assert new_count == initial_count + 1, "Should increase strategy count"
        assert "custom_test" in StrategyFactory.get_available_strategies(), "Should include new strategy"
        assert StrategyFactory.is_strategy_registered("custom_test"), "Should confirm registration"
        
        # Test custom strategy creation
        custom_strategy = StrategyFactory.create_strategy("custom_test")
        assert isinstance(custom_strategy, TestCustomStrategy), "Should create custom strategy"
        
        # Test strategy unregistration
        StrategyFactory.unregister_strategy("custom_test")
        final_count = len(StrategyFactory.get_available_strategies())
        assert final_count == initial_count, "Should decrease strategy count"
        assert not StrategyFactory.is_strategy_registered("custom_test"), "Should confirm unregistration"
        
        # Test global registry instance
        registry_available = strategy_registry.get_available_strategies()
        factory_available = StrategyFactory.get_available_strategies()
        assert registry_available == factory_available, "Registry should match factory"
        
        print("🎉 All factory tests passed!")
    
    def test_generic_strategy():
        """Test GenericAnalysisStrategy functionality"""
        print("Testing GenericAnalysisStrategy...")
        
        # Create generic strategy
        generic = GenericAnalysisStrategy("test_generic")
        print(f"✅ Created generic strategy: {generic.analysis_type}")
        
        # Test empty context
        empty_context = {}
        actions = generic.get_actions(empty_context)
        insights = generic.get_insights(empty_context)
        workflow_steps = generic.get_workflow_steps()
        
        print(f"✅ Empty context - Actions: {actions}")
        print(f"✅ Empty context - Insights: {insights}")
        print(f"✅ Workflow steps: {len(workflow_steps)}")
        
        assert len(actions) > 0, "Should have at least one action"
        assert any("Upload data files" in action for action in actions), "Should suggest data upload"
        assert "No test_generic analysis insights available" in insights, "Should indicate no insights"
        
        # Test with data uploaded context
        uploaded_context = {"data_uploaded": True}
        actions_uploaded = generic.get_actions(uploaded_context)
        insights_uploaded = generic.get_insights(uploaded_context)
        
        print(f"✅ Uploaded context - Actions: {actions_uploaded}")
        print(f"✅ Uploaded context - Insights: {insights_uploaded}")
        
        assert any("Begin analysis workflow" in action for action in actions_uploaded), "Should suggest starting analysis"
        assert "Data uploaded and ready for analysis" in insights_uploaded, "Should have upload insight"
        
        # Test progressive workflow
        analysis_context = {"data_uploaded": True, "analysis_started": True}
        actions_analysis = generic.get_actions(analysis_context)
        insights_analysis = generic.get_insights(analysis_context)
        
        print(f"✅ Analysis context - Actions: {actions_analysis}")
        print(f"✅ Analysis context - Insights: {insights_analysis}")
        
        assert any("Review analysis progress" in action for action in actions_analysis), "Should suggest progress review"
        assert "Analysis workflow initiated" in insights_analysis, "Should have progress insight"
        
        # Test completed workflow
        complete_context = {"data_uploaded": True, "analysis_started": True, "analysis_complete": True}
        insights_complete = generic.get_insights(complete_context)
        
        print(f"✅ Complete context - Insights: {insights_complete}")
        assert "Analysis workflow completed" in insights_complete, "Should have completion insight"
        
        print("🎉 All generic strategy tests passed!")
    
    # Run tests
    test_strategy_factory()
    test_generic_strategy() 