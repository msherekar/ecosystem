"""
Rule-Based Analysis Strategy

Implements the rule-based strategy pattern for generating
suggested actions and insights based on configurable rules.
"""

from abc import abstractmethod
from typing import Dict, List, Any, Optional
from .base import AnalysisStrategy, ActionRule, InsightRule, WorkflowStep, WorkflowStage


class RuleBasedAnalysisStrategy(AnalysisStrategy):
    """Rule-based strategy for suggested actions and insights"""
    
    def __init__(self, analysis_type: str):
        self.analysis_type = analysis_type
        self.action_rules: List[ActionRule] = []
        self.insight_rules: List[InsightRule] = []
        self.workflow_steps: List[WorkflowStep] = []
        self._initialize_rules()
    
    def add_action_rule(self, condition: callable, action: str, priority: int = 1, 
                       stage: Optional[WorkflowStage] = None):
        """Add a rule for action generation"""
        self.action_rules.append(ActionRule(condition, action, priority, stage))
    
    def add_insight_rule(self, condition: callable, insight_generator: callable, 
                        priority: int = 1, category: str = "general"):
        """Add a rule for insight generation"""
        self.insight_rules.append(InsightRule(condition, insight_generator, priority, category))
    
    def add_workflow_step(self, step: WorkflowStep):
        """Add a workflow step"""
        self.workflow_steps.append(step)
    
    def get_actions(self, context: Dict[str, Any]) -> List[str]:
        """Generate actions based on rules"""
        applicable_rules = []
        
        for rule in self.action_rules:
            try:
                if rule.condition(context):
                    applicable_rules.append(rule)
            except Exception:
                # Skip rules that fail evaluation
                continue
        
        # Sort by priority and return actions
        applicable_rules.sort(key=lambda r: r.priority, reverse=True)
        return [rule.action for rule in applicable_rules[:5]]  # Top 5 actions
    
    def get_insights(self, context: Dict[str, Any]) -> str:
        """Generate insights based on rules"""
        applicable_insights = []
        
        for rule in self.insight_rules:
            try:
                if rule.condition(context):
                    insight = rule.insight_generator(context)
                    if insight:  # Only add non-empty insights
                        applicable_insights.append((insight, rule.priority, rule.category))
            except Exception:
                # Skip rules that fail evaluation
                continue
        
        if not applicable_insights:
            return f"No {self.analysis_type} analysis insights available"
        
        # Sort by priority and category
        applicable_insights.sort(key=lambda x: (x[2], -x[1]))  # Category first, then priority desc
        
        # Group by category and format
        insights_by_category = {}
        for insight, priority, category in applicable_insights:
            if category not in insights_by_category:
                insights_by_category[category] = []
            insights_by_category[category].append(insight)
        
        # Format insights
        formatted_insights = []
        for category, insights in insights_by_category.items():
            if category != "general":
                formatted_insights.extend(insights)
            else:
                formatted_insights.extend(insights)
        
        return "; ".join(formatted_insights)
    
    def get_workflow_steps(self) -> List[WorkflowStep]:
        """Get workflow steps"""
        return self.workflow_steps
    
    @abstractmethod
    def _initialize_rules(self):
        """Initialize rules for this analysis type"""
        pass


# Test code for independent validation
if __name__ == "__main__":
    from .base import WorkflowStage, WorkflowStep
    
    class TestRuleBasedStrategy(RuleBasedAnalysisStrategy):
        """Test implementation of rule-based strategy"""
        
        def _initialize_rules(self):
            """Initialize test rules"""
            # Test action rules
            self.add_action_rule(
                condition=lambda ctx: not ctx.get("data_uploaded", False),
                action="Upload test data",
                priority=10,
                stage=WorkflowStage.DATA_UPLOAD
            )
            
            self.add_action_rule(
                condition=lambda ctx: ctx.get("data_uploaded", False),
                action="Process test data",
                priority=5,
                stage=WorkflowStage.ANALYSIS
            )
            
            # Test insight rules
            self.add_insight_rule(
                condition=lambda ctx: ctx.get("data_uploaded", False),
                insight_generator=lambda ctx: "Test data successfully uploaded",
                priority=10,
                category="data_status"
            )
            
            self.add_insight_rule(
                condition=lambda ctx: ctx.get("processing_complete", False),
                insight_generator=lambda ctx: "Processing completed successfully",
                priority=8,
                category="analysis_status"
            )
            
            # Test workflow steps
            self.add_workflow_step(WorkflowStep(
                key="upload",
                title="Upload Data",
                description="Upload test data",
                stage=WorkflowStage.DATA_UPLOAD
            ))
            
            self.add_workflow_step(WorkflowStep(
                key="process",
                title="Process Data", 
                description="Process uploaded data",
                stage=WorkflowStage.ANALYSIS,
                dependencies=["upload"]
            ))
    
    def test_rule_based_strategy():
        """Test RuleBasedAnalysisStrategy functionality"""
        print("Testing rule-based analysis strategy...")
        
        # Create test strategy
        test_strategy = TestRuleBasedStrategy("test")
        print(f"✅ Created test strategy: {test_strategy.analysis_type}")
        
        # Test with empty context
        empty_context = {}
        actions = test_strategy.get_actions(empty_context)
        insights = test_strategy.get_insights(empty_context)
        workflow_steps = test_strategy.get_workflow_steps()
        
        print(f"✅ Empty context - Actions: {actions}")
        print(f"✅ Empty context - Insights: {insights}")
        print(f"✅ Workflow steps: {len(workflow_steps)}")
        
        assert len(actions) > 0, "Should have at least one action"
        assert "Upload test data" in actions, "Should suggest uploading data"
        assert len(workflow_steps) == 2, "Should have 2 workflow steps"
        
        # Test with data uploaded context
        uploaded_context = {"data_uploaded": True}
        actions_uploaded = test_strategy.get_actions(uploaded_context)
        insights_uploaded = test_strategy.get_insights(uploaded_context)
        
        print(f"✅ Uploaded context - Actions: {actions_uploaded}")
        print(f"✅ Uploaded context - Insights: {insights_uploaded}")
        
        assert "Process test data" in actions_uploaded, "Should suggest processing data"
        assert "Test data successfully uploaded" in insights_uploaded, "Should have upload insight"
        
        # Test with processing complete context
        complete_context = {"data_uploaded": True, "processing_complete": True}
        insights_complete = test_strategy.get_insights(complete_context)
        
        print(f"✅ Complete context - Insights: {insights_complete}")
        assert "Processing completed successfully" in insights_complete, "Should have completion insight"
        
        # Test rule addition methods
        initial_action_count = len(test_strategy.action_rules)
        initial_insight_count = len(test_strategy.insight_rules)
        
        test_strategy.add_action_rule(
            condition=lambda ctx: True,
            action="Additional test action",
            priority=1
        )
        
        test_strategy.add_insight_rule(
            condition=lambda ctx: True,
            insight_generator=lambda ctx: "Additional test insight",
            priority=1,
            category="test"
        )
        
        assert len(test_strategy.action_rules) == initial_action_count + 1, "Should add action rule"
        assert len(test_strategy.insight_rules) == initial_insight_count + 1, "Should add insight rule"
        
        print("🎉 All rule-based strategy tests passed!")
    
    # Run test
    test_rule_based_strategy() 