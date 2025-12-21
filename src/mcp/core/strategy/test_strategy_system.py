"""
Comprehensive Strategy System Test

Tests the entire strategy system as an integrated unit,
validating all components work together correctly.
"""

import sys
import traceback
from typing import Dict, Any, List

# Import all strategy components
from .base import WorkflowStage, ActionRule, InsightRule, WorkflowStep, AnalysisStrategy
from .rule_based import RuleBasedAnalysisStrategy
from .scrna_strategy import scRNASeqAnalysisStrategy
from .rna_strategy import RNASeqAnalysisStrategy
from .atac_strategy import ATACSeqAnalysisStrategy
from .factory import StrategyFactory, GenericAnalysisStrategy, strategy_registry


class StrategySystemTester:
    """Comprehensive tester for the strategy system"""
    
    def __init__(self):
        self.test_results = []
        self.failed_tests = []
    
    def run_test(self, test_name: str, test_func):
        """Run a single test and track results"""
        try:
            print(f"\n🧪 Running {test_name}...")
            test_func()
            print(f"✅ {test_name} PASSED")
            self.test_results.append((test_name, True, None))
        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"❌ {test_name} FAILED: {str(e)}")
            self.test_results.append((test_name, False, error_msg))
            self.failed_tests.append(test_name)
    
    def test_base_components_integration(self):
        """Test base components work together"""
        # Test WorkflowStage enum values
        stages = list(WorkflowStage)
        assert len(stages) == 7, f"Expected 7 workflow stages, got {len(stages)}"
        assert WorkflowStage.DATA_UPLOAD in stages
        assert WorkflowStage.ANALYSIS in stages
        
        # Test ActionRule creation and functionality
        rule = ActionRule(
            condition=lambda ctx: ctx.get("test", False),
            action="Test action",
            priority=5,
            stage=WorkflowStage.DATA_UPLOAD
        )
        assert rule.condition({"test": True}), "ActionRule condition should work"
        assert not rule.condition({"test": False}), "ActionRule condition should work"
        assert rule.action == "Test action"
        assert rule.priority == 5
        assert rule.stage == WorkflowStage.DATA_UPLOAD
        
        # Test InsightRule creation and functionality
        insight_rule = InsightRule(
            condition=lambda ctx: ctx.get("ready", False),
            insight_generator=lambda ctx: f"Status: {ctx.get('status', 'unknown')}",
            priority=3,
            category="test_category"
        )
        assert insight_rule.condition({"ready": True})
        assert insight_rule.insight_generator({"status": "good"}) == "Status: good"
        
        # Test WorkflowStep creation
        step = WorkflowStep(
            key="test_step",
            title="Test Step",
            description="A test workflow step",
            stage=WorkflowStage.ANALYSIS,
            dependencies=["prev_step"],
            optional=True
        )
        assert step.key == "test_step"
        assert step.stage == WorkflowStage.ANALYSIS
        assert step.dependencies == ["prev_step"]
        assert step.optional is True
    
    def test_rule_based_strategy_functionality(self):
        """Test rule-based strategy base class"""
        
        class TestStrategy(RuleBasedAnalysisStrategy):
            def _initialize_rules(self):
                self.add_action_rule(
                    condition=lambda ctx: not ctx.get("started", False),
                    action="Start the process",
                    priority=10
                )
                self.add_insight_rule(
                    condition=lambda ctx: ctx.get("started", False),
                    insight_generator=lambda ctx: "Process has started",
                    priority=8,
                    category="status"
                )
        
        strategy = TestStrategy("test")
        
        # Test action generation
        actions = strategy.get_actions({})
        assert len(actions) > 0, "Should generate actions"
        assert "Start the process" in actions
        
        # Test insight generation
        insights = strategy.get_insights({"started": True})
        assert "Process has started" in insights
        
        # Test empty insights
        empty_insights = strategy.get_insights({})
        assert "No test analysis insights" in empty_insights
    
    def test_specific_strategies(self):
        """Test all specific strategy implementations"""
        
        # Test scRNA-seq strategy
        scrna = scRNASeqAnalysisStrategy()
        assert scrna.analysis_type == "scrnaseq"
        
        actions = scrna.get_actions({})
        assert any("scRNA-seq data" in action for action in actions)
        
        workflow_steps = scrna.get_workflow_steps()
        assert len(workflow_steps) == 9
        upload_step = next(s for s in workflow_steps if s.key == "data_upload")
        assert upload_step.stage == WorkflowStage.DATA_UPLOAD
        
        # Test RNA-seq strategy
        rnaseq = RNASeqAnalysisStrategy()
        assert rnaseq.analysis_type == "rnaseq"
        
        actions = rnaseq.get_actions({})
        assert any("RNA-seq counts" in action for action in actions)
        
        workflow_steps = rnaseq.get_workflow_steps()
        assert len(workflow_steps) == 4
        deseq_step = next(s for s in workflow_steps if s.key == "deseq2")
        assert deseq_step.stage == WorkflowStage.ANALYSIS
        
        # Test ATAC-seq strategy
        atacseq = ATACSeqAnalysisStrategy()
        assert atacseq.analysis_type == "atacseq"
        
        actions = atacseq.get_actions({})
        assert any("ATAC-seq" in action for action in actions)
        
        workflow_steps = atacseq.get_workflow_steps()
        assert len(workflow_steps) == 6
        peak_step = next(s for s in workflow_steps if s.key == "peak_calling")
        assert peak_step.stage == WorkflowStage.ANALYSIS
    
    def test_factory_functionality(self):
        """Test strategy factory operations"""
        
        # Test available strategies
        available = StrategyFactory.get_available_strategies()
        assert "scrnaseq" in available
        assert "rnaseq" in available
        assert "atacseq" in available
        
        # Test strategy creation
        for strategy_type in available:
            strategy = StrategyFactory.create_strategy(strategy_type)
            assert strategy is not None
            assert hasattr(strategy, 'get_actions')
            assert hasattr(strategy, 'get_insights')
            assert hasattr(strategy, 'get_workflow_steps')
        
        # Test unknown strategy fallback
        unknown = StrategyFactory.create_strategy("unknown_analysis_type")
        assert isinstance(unknown, GenericAnalysisStrategy)
        assert unknown.analysis_type == "unknown_analysis_type"
        
        # Test strategy registration
        class CustomStrategy(RuleBasedAnalysisStrategy):
            def __init__(self):
                super().__init__("custom")
            
            def _initialize_rules(self):
                self.add_action_rule(
                    condition=lambda ctx: True,
                    action="Custom action",
                    priority=1
                )
        
        StrategyFactory.register_strategy("custom", CustomStrategy)
        assert "custom" in StrategyFactory.get_available_strategies()
        
        custom_strategy = StrategyFactory.create_strategy("custom")
        assert isinstance(custom_strategy, CustomStrategy)
        
        # Clean up
        StrategyFactory.unregister_strategy("custom")
        assert "custom" not in StrategyFactory.get_available_strategies()
    
    def test_workflow_simulation(self):
        """Test complete workflow simulation for each strategy"""
        
        strategies_to_test = [
            ("scrnaseq", scRNASeqAnalysisStrategy()),
            ("rnaseq", RNASeqAnalysisStrategy()),
            ("atacseq", ATACSeqAnalysisStrategy())
        ]
        
        for strategy_name, strategy in strategies_to_test:
            print(f"  Testing {strategy_name} workflow...")
            
            # Initial state
            context = {}
            actions = strategy.get_actions(context)
            assert len(actions) > 0, f"{strategy_name} should have initial actions"
            assert any("upload" in action.lower() for action in actions), f"{strategy_name} should suggest upload"
            
            # After data upload
            context["data_uploaded"] = True
            actions_uploaded = strategy.get_actions(context)
            insights_uploaded = strategy.get_insights(context)
            
            assert len(actions_uploaded) > 0, f"{strategy_name} should have post-upload actions"
            assert isinstance(insights_uploaded, str), f"{strategy_name} should provide insights"
            
            # Verify workflow steps are properly ordered
            workflow_steps = strategy.get_workflow_steps()
            upload_steps = [s for s in workflow_steps if s.stage == WorkflowStage.DATA_UPLOAD]
            analysis_steps = [s for s in workflow_steps if s.stage == WorkflowStage.ANALYSIS]
            
            assert len(upload_steps) > 0, f"{strategy_name} should have upload steps"
            assert len(analysis_steps) > 0, f"{strategy_name} should have analysis steps"
            
            # Check dependencies are valid
            all_step_keys = {s.key for s in workflow_steps}
            for step in workflow_steps:
                if step.dependencies:
                    for dep in step.dependencies:
                        assert dep in all_step_keys, f"Dependency {dep} should exist in {strategy_name}"
    
    def test_error_handling(self):
        """Test error handling in various scenarios"""
        
        # Test rule evaluation errors
        class ErrorProneStrategy(RuleBasedAnalysisStrategy):
            def _initialize_rules(self):
                # Rule that will fail
                self.add_action_rule(
                    condition=lambda ctx: ctx["nonexistent_key"],  # Will raise KeyError
                    action="Should not execute",
                    priority=1
                )
                # Rule that should work
                self.add_action_rule(
                    condition=lambda ctx: True,
                    action="Should execute",
                    priority=2
                )
        
        strategy = ErrorProneStrategy("error_test")
        
        # Should not crash and should return the working rule
        actions = strategy.get_actions({})
        assert "Should execute" in actions
        assert "Should not execute" not in actions
        
        # Test insight generation errors
        class ErrorInsightStrategy(RuleBasedAnalysisStrategy):
            def _initialize_rules(self):
                self.add_insight_rule(
                    condition=lambda ctx: ctx["missing_key"],  # Will fail
                    insight_generator=lambda ctx: "Should not generate",
                    priority=1
                )
                self.add_insight_rule(
                    condition=lambda ctx: True,
                    insight_generator=lambda ctx: "Should generate",
                    priority=2
                )
        
        insight_strategy = ErrorInsightStrategy("insight_test")
        insights = insight_strategy.get_insights({})
        assert "Should generate" in insights
        assert "Should not generate" not in insights
    
    def test_legacy_compatibility(self):
        """Test that legacy interfaces still work"""
        from . import (
            SuggestedActionStrategy,
            RuleBasedActionStrategy,
            scRNASeqActionStrategy,
            RNASeqActionStrategy,
            ATACSeqActionStrategy,
            GenericActionStrategy
        )
        
        # Test legacy aliases point to correct classes
        assert SuggestedActionStrategy is AnalysisStrategy
        assert RuleBasedActionStrategy is RuleBasedAnalysisStrategy
        assert scRNASeqActionStrategy is scRNASeqAnalysisStrategy
        assert RNASeqActionStrategy is RNASeqAnalysisStrategy
        assert ATACSeqActionStrategy is ATACSeqAnalysisStrategy
        assert GenericActionStrategy is GenericAnalysisStrategy
        
        # Test that old interface works
        legacy_strategy = scRNASeqActionStrategy()
        actions = legacy_strategy.get_actions({})
        assert len(actions) > 0
    
    def test_performance_characteristics(self):
        """Test performance characteristics of the system"""
        import time
        
        # Test strategy creation performance
        start_time = time.time()
        for _ in range(100):
            StrategyFactory.create_strategy("scrnaseq")
        creation_time = time.time() - start_time
        assert creation_time < 1.0, "Strategy creation should be fast"
        
        # Test action generation performance
        strategy = StrategyFactory.create_strategy("scrnaseq")
        context = {"data_uploaded": True, "pipeline_status": {"qc": True, "filtering": False}}
        
        start_time = time.time()
        for _ in range(1000):
            strategy.get_actions(context)
        action_time = time.time() - start_time
        assert action_time < 1.0, "Action generation should be fast"
    
    def run_all_tests(self):
        """Run all system tests"""
        print("🚀 Starting Comprehensive Strategy System Tests")
        print("=" * 60)
        
        # Define all tests
        tests = [
            ("Base Components Integration", self.test_base_components_integration),
            ("Rule-Based Strategy Functionality", self.test_rule_based_strategy_functionality),
            ("Specific Strategies", self.test_specific_strategies),
            ("Factory Functionality", self.test_factory_functionality),
            ("Workflow Simulation", self.test_workflow_simulation),
            ("Error Handling", self.test_error_handling),
            ("Legacy Compatibility", self.test_legacy_compatibility),
            ("Performance Characteristics", self.test_performance_characteristics),
        ]
        
        # Run all tests
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, passed, _ in self.test_results if passed)
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        
        if failed_tests == 0:
            print("\n🎉 ALL TESTS PASSED! Strategy system is working correctly.")
            return True
        else:
            print(f"\n💥 {failed_tests} TESTS FAILED")
            print("\nFailed tests:")
            for test_name in self.failed_tests:
                print(f"  - {test_name}")
            return False


# Test code for independent validation
if __name__ == "__main__":
    def test_strategy_system():
        """Main test function"""
        tester = StrategySystemTester()
        success = tester.run_all_tests()
        
        if not success:
            sys.exit(1)
        
        print("\n🏆 Strategy system is fully functional!")
    
    # Run comprehensive test
    test_strategy_system() 