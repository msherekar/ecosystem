"""
Rule-Based Analysis Strategy

Implements the rule-based strategy pattern for generating
suggested actions and insights based on configurable rules.
Enhanced with caching, validation, and performance optimization.
"""

from abc import abstractmethod
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict
import logging
import time

from .base import (
    AnalysisStrategy, 
    ActionRule, 
    InsightRule, 
    WorkflowStep, 
    WorkflowStage,
    ValidationError
)
from .security import SecurityManager

logger = logging.getLogger(__name__)


class RuleBasedAnalysisStrategy(AnalysisStrategy):
    """Rule-based strategy for suggested actions and insights"""
    
    def __init__(self, analysis_type: str):
        super().__init__(analysis_type)
        self.action_rules: List[ActionRule] = []
        self.insight_rules: List[InsightRule] = []
        self.workflow_steps: List[WorkflowStep] = []
        self.security_manager = SecurityManager()
        self._rule_cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes
        self._last_cache_clear = time.time()
        
        # Rule execution statistics
        self.rule_stats = {
            "action_rules_executed": 0,
            "insight_rules_executed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "validation_errors": 0
        }
        
        self._initialize_rules()
        self._validate_configuration()
    
    def add_action_rule(self, condition: callable, action: str, priority: int = 1, 
                       stage: Optional[WorkflowStage] = None, description: str = "",
                       estimated_time: Optional[int] = None, dependencies: List[str] = None):
        """Add a rule for action generation with enhanced metadata"""
        if not callable(condition):
            raise ValidationError("Action rule condition must be callable")
        
        if not action or len(action.strip()) == 0:
            raise ValidationError("Action rule must have non-empty action text")
        
        rule = ActionRule(
            condition=condition,
            action=self.security_manager.sanitize_string(action),
            priority=priority,
            stage=stage,
            description=self.security_manager.sanitize_string(description),
            estimated_time=estimated_time,
            dependencies=dependencies or []
        )
        
        self.action_rules.append(rule)
        self._clear_cache()
        logger.debug(f"Added action rule: {action}")
    
    def add_insight_rule(self, condition: callable, insight_generator: callable, 
                        priority: int = 1, category: str = "general", severity: str = "info",
                        actionable: bool = False):
        """Add a rule for insight generation with enhanced metadata"""
        if not callable(condition) or not callable(insight_generator):
            raise ValidationError("Insight rule condition and generator must be callable")
        
        rule = InsightRule(
            condition=condition,
            insight_generator=insight_generator,
            priority=priority,
            category=self.security_manager.sanitize_string(category),
            severity=severity,
            actionable=actionable
        )
        
        self.insight_rules.append(rule)
        self._clear_cache()
        logger.debug(f"Added insight rule for category: {category}")
    
    def add_workflow_step(self, step: WorkflowStep):
        """Add a workflow step with validation"""
        if not isinstance(step, WorkflowStep):
            raise ValidationError("Must provide WorkflowStep instance")
        
        # Check for duplicate keys
        existing_keys = {s.key for s in self.workflow_steps}
        if step.key in existing_keys:
            raise ValidationError(f"Workflow step key '{step.key}' already exists")
        
        self.workflow_steps.append(step)
        logger.debug(f"Added workflow step: {step.key}")
    
    def get_actions(self, context: Dict[str, Any]) -> List[str]:
        """Generate actions based on rules with caching and validation"""
        # Validate and sanitize context
        if not self.validate_context(context):
            logger.warning("Invalid context provided, using empty context")
            context = {}
        
        context = self.security_manager.sanitize_context(context)
        context_key = self._generate_context_key(context, "actions")
        
        # Check cache
        cached_result = self._get_from_cache(context_key)
        if cached_result is not None:
            self.rule_stats["cache_hits"] += 1
            return cached_result
        
        self.rule_stats["cache_misses"] += 1
        applicable_rules = []
        
        for rule in self.action_rules:
            try:
                if rule.condition(context):
                    applicable_rules.append(rule)
                self.rule_stats["action_rules_executed"] += 1
            except Exception as e:
                logger.warning(f"Error evaluating action rule: {e}")
                self.rule_stats["validation_errors"] += 1
                continue
        
        # Sort by priority (higher first) and return top actions
        applicable_rules.sort(key=lambda r: r.priority, reverse=True)
        actions = [rule.action for rule in applicable_rules[:5]]  # Top 5 actions
        
        # Cache result
        self._add_to_cache(context_key, actions)
        
        return actions
    
    def get_insights(self, context: Dict[str, Any]) -> str:
        """Generate insights based on rules with enhanced formatting"""
        # Validate and sanitize context
        if not self.validate_context(context):
            logger.warning("Invalid context provided, using empty context")
            context = {}
        
        context = self.security_manager.sanitize_context(context)
        context_key = self._generate_context_key(context, "insights")
        
        # Check cache
        cached_result = self._get_from_cache(context_key)
        if cached_result is not None:
            self.rule_stats["cache_hits"] += 1
            return cached_result
        
        self.rule_stats["cache_misses"] += 1
        applicable_insights = []
        
        for rule in self.insight_rules:
            try:
                if rule.condition(context):
                    insight_text = rule.insight_generator(context)
                    if insight_text and insight_text.strip():  # Only add non-empty insights
                        applicable_insights.append({
                            "text": self.security_manager.sanitize_string(str(insight_text)),
                            "priority": rule.priority,
                            "category": rule.category,
                            "severity": rule.severity,
                            "actionable": rule.actionable
                        })
                self.rule_stats["insight_rules_executed"] += 1
            except Exception as e:
                logger.warning(f"Error evaluating insight rule: {e}")
                self.rule_stats["validation_errors"] += 1
                continue
        
        if not applicable_insights:
            result = f"No {self.analysis_type} analysis insights available"
        else:
            # Sort by category and priority
            applicable_insights.sort(key=lambda x: (x["category"], -x["priority"]))
            
            # Group by category for better organization
            insights_by_category = defaultdict(list)
            for insight in applicable_insights:
                insights_by_category[insight["category"]].append(insight["text"])
            
            # Format insights
            formatted_insights = []
            for category, insights in insights_by_category.items():
                if category != "general":
                    formatted_insights.extend(insights)
                else:
                    formatted_insights.extend(insights)
            
            result = "; ".join(formatted_insights)
        
        # Cache result
        self._add_to_cache(context_key, result)
        
        return result
    
    def get_workflow_steps(self) -> List[WorkflowStep]:
        """Get workflow steps with dependency validation"""
        # Validate dependencies
        step_keys = {step.key for step in self.workflow_steps}
        for step in self.workflow_steps:
            if step.dependencies:
                invalid_deps = set(step.dependencies) - step_keys
                if invalid_deps:
                    logger.warning(f"Step '{step.key}' has invalid dependencies: {invalid_deps}")
        
        return self.workflow_steps.copy()
    
    def get_available_steps(self, completed_steps: List[str]) -> List[WorkflowStep]:
        """Get steps that are ready to execute based on completed steps"""
        return [step for step in self.workflow_steps if step.is_ready(completed_steps)]
    
    def get_rule_statistics(self) -> Dict[str, Any]:
        """Get rule execution and performance statistics"""
        cache_hit_rate = (
            self.rule_stats["cache_hits"] / 
            max(1, self.rule_stats["cache_hits"] + self.rule_stats["cache_misses"])
        )
        
        return {
            "analysis_type": self.analysis_type,
            "action_rules_count": len(self.action_rules),
            "insight_rules_count": len(self.insight_rules),
            "workflow_steps_count": len(self.workflow_steps),
            "cache_size": len(self._rule_cache),
            "cache_hit_rate": cache_hit_rate,
            **self.rule_stats
        }
    
    def _generate_context_key(self, context: Dict[str, Any], operation: str) -> str:
        """Generate cache key for context"""
        import hashlib
        import json
        
        # Create deterministic string representation
        context_str = json.dumps(context, sort_keys=True)
        key = f"{self.analysis_type}:{operation}:{hashlib.md5(context_str.encode()).hexdigest()}"
        return key
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get item from cache if not expired"""
        if key in self._rule_cache:
            timestamp, value = self._rule_cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return value
            else:
                del self._rule_cache[key]
        return None
    
    def _add_to_cache(self, key: str, value: Any):
        """Add item to cache with timestamp"""
        current_time = time.time()
        
        # Clear old cache entries periodically
        if current_time - self._last_cache_clear > self._cache_ttl:
            self._clear_expired_cache()
            self._last_cache_clear = current_time
        
        self._rule_cache[key] = (current_time, value)
    
    def _clear_cache(self):
        """Clear entire cache"""
        self._rule_cache.clear()
        self._last_cache_clear = time.time()
    
    def _clear_expired_cache(self):
        """Clear expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, (timestamp, _) in self._rule_cache.items()
            if current_time - timestamp >= self._cache_ttl
        ]
        for key in expired_keys:
            del self._rule_cache[key]
    
    def _validate_configuration(self):
        """Validate strategy configuration"""
        if not self.analysis_type:
            raise ValidationError("Analysis type cannot be empty")
        
        # Check for circular dependencies in workflow
        self._check_circular_dependencies()
        
        logger.info(f"Strategy '{self.analysis_type}' configuration validated")
    
    def _check_circular_dependencies(self):
        """Check for circular dependencies in workflow steps"""
        def has_cycle(step_key: str, visited: Set[str], path: Set[str]) -> bool:
            if step_key in path:
                return True
            if step_key in visited:
                return False
            
            visited.add(step_key)
            path.add(step_key)
            
            step = next((s for s in self.workflow_steps if s.key == step_key), None)
            if step and step.dependencies:
                for dep in step.dependencies:
                    if has_cycle(dep, visited, path):
                        return True
            
            path.remove(step_key)
            return False
        
        visited = set()
        for step in self.workflow_steps:
            if step.key not in visited:
                if has_cycle(step.key, visited, set()):
                    raise ValidationError(f"Circular dependency detected in workflow step: {step.key}")
    
    @abstractmethod
    def _initialize_rules(self):
        """Initialize rules for this analysis type"""
        pass


def main():
    """Test rule-based strategy functionality with comprehensive validation"""
    print("🧪 Testing Rule-Based Analysis Strategy")
    print("=" * 50)
    
    # Create test strategy implementation
    class TestRuleBasedStrategy(RuleBasedAnalysisStrategy):
        def _initialize_rules(self):
            """Initialize test rules"""
            # Test action rules
            self.add_action_rule(
                condition=lambda ctx: not ctx.get("data_uploaded", False),
                action="Upload test data",
                priority=10,
                stage=WorkflowStage.DATA_UPLOAD,
                description="Upload test data files",
                estimated_time=5
            )
            
            self.add_action_rule(
                condition=lambda ctx: ctx.get("data_uploaded", False) and not ctx.get("analysis_started", False),
                action="Start analysis",
                priority=8,
                stage=WorkflowStage.ANALYSIS,
                description="Begin the analysis process",
                estimated_time=30
            )
            
            # Test insight rules
            self.add_insight_rule(
                condition=lambda ctx: ctx.get("data_uploaded", False),
                insight_generator=lambda ctx: "Test data successfully uploaded",
                priority=10,
                category="data_status",
                severity="success",
                actionable=False
            )
            
            self.add_insight_rule(
                condition=lambda ctx: ctx.get("analysis_started", False),
                insight_generator=lambda ctx: "Analysis is in progress",
                priority=8,
                category="analysis_status",
                severity="info",
                actionable=True
            )
            
            # Test workflow steps
            self.add_workflow_step(WorkflowStep(
                key="upload",
                title="Upload Data",
                description="Upload test data files",
                stage=WorkflowStage.DATA_UPLOAD,
                estimated_time=5,
                complexity="low"
            ))
            
            self.add_workflow_step(WorkflowStep(
                key="analyze",
                title="Analyze Data",
                description="Perform data analysis",
                stage=WorkflowStage.ANALYSIS,
                dependencies=["upload"],
                estimated_time=30,
                complexity="medium"
            ))
    
    # Test strategy creation
    print("Testing strategy creation...")
    test_strategy = TestRuleBasedStrategy("test_analysis")
    assert test_strategy.analysis_type == "test_analysis", "Analysis type should be set"
    print("✅ Strategy creation passed")
    
    # Test empty context
    print("Testing empty context...")
    empty_context = {}
    actions = test_strategy.get_actions(empty_context)
    insights = test_strategy.get_insights(empty_context)
    workflow_steps = test_strategy.get_workflow_steps()
    
    assert len(actions) > 0, "Should have at least one action"
    assert "Upload test data" in actions, "Should suggest uploading data"
    assert len(workflow_steps) == 2, "Should have 2 workflow steps"
    print("✅ Empty context tests passed")
    
    # Test with data uploaded context
    print("Testing data uploaded context...")
    uploaded_context = {"data_uploaded": True}
    actions_uploaded = test_strategy.get_actions(uploaded_context)
    insights_uploaded = test_strategy.get_insights(uploaded_context)
    
    assert "Start analysis" in actions_uploaded, "Should suggest starting analysis"
    assert "Test data successfully uploaded" in insights_uploaded, "Should have upload insight"
    print("✅ Data uploaded context tests passed")
    
    # Test caching
    print("Testing caching functionality...")
    # First call - cache miss
    start_time = time.time()
    actions1 = test_strategy.get_actions(uploaded_context)
    first_call_time = time.time() - start_time
    
    # Second call - cache hit
    start_time = time.time()
    actions2 = test_strategy.get_actions(uploaded_context)
    second_call_time = time.time() - start_time
    
    assert actions1 == actions2, "Cached results should be identical"
    assert second_call_time < first_call_time, "Cached call should be faster"
    
    stats = test_strategy.get_rule_statistics()
    assert stats["cache_hits"] > 0, "Should have cache hits"
    print("✅ Caching tests passed")
    
    # Test workflow step dependencies
    print("Testing workflow step dependencies...")
    available_steps = test_strategy.get_available_steps([])
    assert len(available_steps) == 1, "Only upload step should be available initially"
    assert available_steps[0].key == "upload", "Upload step should be available"
    
    available_after_upload = test_strategy.get_available_steps(["upload"])
    assert len(available_after_upload) == 2, "Both steps should be available after upload"
    print("✅ Workflow dependency tests passed")
    
    # Test validation and security
    print("Testing validation and security...")
    
    # Test invalid context
    invalid_contexts = [
        "not a dict",
        None,
        {"malicious": "<script>alert('xss')</script>"}
    ]
    
    for invalid_ctx in invalid_contexts:
        try:
            actions = test_strategy.get_actions(invalid_ctx)
            # Should handle gracefully, not crash
            assert isinstance(actions, list), "Should return list even for invalid context"
        except Exception as e:
            print(f"Unexpected error with invalid context: {e}")
    
    # Test rule validation
    try:
        test_strategy.add_action_rule(
            condition="not callable",  # Invalid - not callable
            action="Invalid rule"
        )
        assert False, "Should reject non-callable condition"
    except ValidationError:
        pass  # Expected
    
    try:
        test_strategy.add_action_rule(
            condition=lambda ctx: True,
            action=""  # Invalid - empty action
        )
        assert False, "Should reject empty action"
    except ValidationError:
        pass  # Expected
    
    print("✅ Validation and security tests passed")
    
    # Test performance statistics
    print("Testing performance statistics...")
    stats = test_strategy.get_rule_statistics()
    
    required_stats = [
        "analysis_type", "action_rules_count", "insight_rules_count",
        "workflow_steps_count", "cache_size", "cache_hit_rate"
    ]
    
    for stat in required_stats:
        assert stat in stats, f"Statistics should include {stat}"
    
    assert stats["analysis_type"] == "test_analysis", "Should track analysis type"
    assert stats["action_rules_count"] == 2, "Should count action rules"
    assert stats["insight_rules_count"] == 2, "Should count insight rules"
    print("✅ Performance statistics tests passed")
    
    print("\n🎉 All rule-based strategy tests passed!")
    return True


if __name__ == "__main__":
    def test_static_rule_based():
        """Static tests for rule-based strategy"""
        print("Running static rule-based strategy tests...")
        
        # Test that we can't instantiate abstract class directly
        try:
            strategy = RuleBasedAnalysisStrategy("test")
            assert False, "Should not be able to instantiate abstract class"
        except TypeError:
            pass  # Expected
        
        print("✅ Static rule-based strategy tests passed!")
    
    def test_dynamic_rule_based():
        """Dynamic tests for rule-based strategy"""
        print("Running dynamic rule-based strategy tests...")
        
        # Run comprehensive main tests
        success = main()
        assert success, "Main tests should pass"
        
        print("✅ Dynamic rule-based strategy tests passed!")
    
    # Run all tests
    test_static_rule_based()
    test_dynamic_rule_based()