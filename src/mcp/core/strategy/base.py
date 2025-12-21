"""
Base Strategy Components

Contains abstract base classes, enums, and data structures
used across all strategy implementations.
Enhanced for scalability, security, and Electron integration.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import json


class WorkflowStage(Enum):
    """Standard workflow stages across analysis types"""
    DATA_UPLOAD = "data_upload"
    QUALITY_CONTROL = "quality_control"
    PREPROCESSING = "preprocessing"
    ANALYSIS = "analysis"
    VISUALIZATION = "visualization"
    INTERPRETATION = "interpretation"
    EXPORT = "export"
    
    @classmethod
    def get_ordered_stages(cls) -> List['WorkflowStage']:
        """Get stages in typical execution order"""
        return [
            cls.DATA_UPLOAD,
            cls.QUALITY_CONTROL,
            cls.PREPROCESSING,
            cls.ANALYSIS,
            cls.VISUALIZATION,
            cls.INTERPRETATION,
            cls.EXPORT
        ]
    
    def get_display_name(self) -> str:
        """Get human-readable display name"""
        return self.value.replace('_', ' ').title()


@dataclass
class ActionRule:
    """Rule for generating suggested actions"""
    condition: callable  # Function that returns bool
    action: str
    priority: int = 1
    stage: Optional[WorkflowStage] = None
    description: str = ""
    estimated_time: Optional[int] = None  # Estimated time in minutes
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "action": self.action,
            "priority": self.priority,
            "stage": self.stage.value if self.stage else None,
            "description": self.description,
            "estimated_time": self.estimated_time,
            "dependencies": self.dependencies
        }


@dataclass
class InsightRule:
    """Rule for generating analysis insights"""
    condition: callable  # Function that returns bool
    insight_generator: callable  # Function that returns insight string
    priority: int = 1
    category: str = "general"  # e.g., "data_quality", "analysis_progress", "results"
    severity: str = "info"  # "info", "warning", "error", "success"
    actionable: bool = False  # Whether insight suggests specific action
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "priority": self.priority,
            "category": self.category,
            "severity": self.severity,
            "actionable": self.actionable
        }


@dataclass
class WorkflowStep:
    """Configuration for a workflow step"""
    key: str
    title: str
    description: str
    stage: WorkflowStage
    dependencies: Optional[List[str]] = None
    optional: bool = False
    estimated_time: Optional[int] = None  # Minutes
    complexity: str = "medium"  # "low", "medium", "high"
    
    def __post_init__(self):
        """Validate step configuration"""
        if not self.key or not self.title:
            raise ValueError("WorkflowStep requires key and title")
        
        if self.dependencies is None:
            self.dependencies = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "key": self.key,
            "title": self.title,
            "description": self.description,
            "stage": self.stage.value,
            "dependencies": self.dependencies or [],
            "optional": self.optional,
            "estimated_time": self.estimated_time,
            "complexity": self.complexity
        }
    
    def is_ready(self, completed_steps: List[str]) -> bool:
        """Check if step is ready to execute based on dependencies"""
        if not self.dependencies:
            return True
        return all(dep in completed_steps for dep in self.dependencies)


class AnalysisStrategy(ABC):
    """Abstract strategy for analysis-specific behavior"""
    
    def __init__(self, analysis_type: str):
        self.analysis_type = analysis_type
        self.version = "1.0.0"
        self.metadata = {}
    
    @abstractmethod
    def get_actions(self, context: Dict[str, Any]) -> List[str]:
        """Generate suggested actions based on context"""
        pass
    
    @abstractmethod
    def get_insights(self, context: Dict[str, Any]) -> str:
        """Generate analysis insights based on context"""
        pass
    
    @abstractmethod
    def get_workflow_steps(self) -> List[WorkflowStep]:
        """Get workflow steps for this analysis type"""
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get strategy metadata"""
        return {
            "analysis_type": self.analysis_type,
            "version": self.version,
            "metadata": self.metadata
        }
    
    def validate_context(self, context: Dict[str, Any]) -> bool:
        """Validate context data (can be overridden)"""
        return isinstance(context, dict)
    
    def get_next_actions(self, context: Dict[str, Any], current_step: str) -> List[str]:
        """Get next actions based on current workflow step"""
        all_actions = self.get_actions(context)
        workflow_steps = self.get_workflow_steps()
        
        # Find current step
        current_step_obj = next((step for step in workflow_steps if step.key == current_step), None)
        if not current_step_obj:
            return all_actions
        
        # Filter actions by stage
        return [action for action in all_actions if self._action_matches_stage(action, current_step_obj.stage)]
    
    def _action_matches_stage(self, action: str, stage: WorkflowStage) -> bool:
        """Check if action matches workflow stage (basic implementation)"""
        stage_keywords = {
            WorkflowStage.DATA_UPLOAD: ["upload", "load", "import"],
            WorkflowStage.QUALITY_CONTROL: ["quality", "qc", "check"],
            WorkflowStage.PREPROCESSING: ["filter", "normalize", "preprocess"],
            WorkflowStage.ANALYSIS: ["analyze", "cluster", "differential"],
            WorkflowStage.VISUALIZATION: ["plot", "visualize", "chart"],
            WorkflowStage.INTERPRETATION: ["interpret", "enrich", "annotate"],
            WorkflowStage.EXPORT: ["export", "save", "download"]
        }
        
        keywords = stage_keywords.get(stage, [])
        return any(keyword in action.lower() for keyword in keywords)


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class StrategyError(Exception):
    """Custom exception for strategy-related errors"""
    pass


def main():
    """Test base components functionality with comprehensive validation"""
    print("🧪 Testing Base Strategy Components")
    print("=" * 50)
    
    # Test WorkflowStage enum
    print("Testing WorkflowStage enum...")
    stages = list(WorkflowStage)
    assert len(stages) == 7, f"Expected 7 stages, got {len(stages)}"
    
    ordered_stages = WorkflowStage.get_ordered_stages()
    assert len(ordered_stages) == 7, "Should have 7 ordered stages"
    assert ordered_stages[0] == WorkflowStage.DATA_UPLOAD, "First stage should be DATA_UPLOAD"
    
    display_name = WorkflowStage.DATA_UPLOAD.get_display_name()
    assert display_name == "Data Upload", f"Expected 'Data Upload', got '{display_name}'"
    print("✅ WorkflowStage enum tests passed")
    
    # Test ActionRule dataclass
    print("Testing ActionRule dataclass...")
    action_rule = ActionRule(
        condition=lambda ctx: ctx.get("test", False),
        action="Test action",
        priority=5,
        stage=WorkflowStage.DATA_UPLOAD,
        description="A test action",
        estimated_time=30,
        dependencies=["dep1", "dep2"]
    )
    
    assert action_rule.condition({"test": True}), "Condition should return True"
    assert not action_rule.condition({"test": False}), "Condition should return False"
    
    rule_dict = action_rule.to_dict()
    assert rule_dict["action"] == "Test action", "Should serialize action"
    assert rule_dict["stage"] == "data_upload", "Should serialize stage"
    print("✅ ActionRule tests passed")
    
    # Test InsightRule dataclass
    print("Testing InsightRule dataclass...")
    insight_rule = InsightRule(
        condition=lambda ctx: ctx.get("ready", False),
        insight_generator=lambda ctx: f"Status: {ctx.get('status', 'unknown')}",
        priority=3,
        category="test_category",
        severity="warning",
        actionable=True
    )
    
    assert insight_rule.condition({"ready": True}), "Condition should work"
    assert insight_rule.insight_generator({"status": "good"}) == "Status: good", "Generator should work"
    
    insight_dict = insight_rule.to_dict()
    assert insight_dict["severity"] == "warning", "Should serialize severity"
    print("✅ InsightRule tests passed")
    
    # Test WorkflowStep dataclass
    print("Testing WorkflowStep dataclass...")
    step = WorkflowStep(
        key="test_step",
        title="Test Step",
        description="A test workflow step",
        stage=WorkflowStage.ANALYSIS,
        dependencies=["prev_step"],
        optional=True,
        estimated_time=45,
        complexity="high"
    )
    
    assert step.key == "test_step", "Key should be set"
    assert step.dependencies == ["prev_step"], "Dependencies should be set"
    assert step.is_ready(["prev_step"]), "Should be ready when dependencies met"
    assert not step.is_ready([]), "Should not be ready when dependencies not met"
    
    step_dict = step.to_dict()
    assert step_dict["complexity"] == "high", "Should serialize complexity"
    
    # Test step without dependencies
    simple_step = WorkflowStep("simple", "Simple", "Simple step", WorkflowStage.DATA_UPLOAD)
    assert simple_step.is_ready([]), "Step without dependencies should always be ready"
    print("✅ WorkflowStep tests passed")
    
    # Test AnalysisStrategy abstract class
    print("Testing AnalysisStrategy abstract class...")
    try:
        # This should fail because AnalysisStrategy is abstract
        strategy = AnalysisStrategy("test")
        assert False, "Should not be able to instantiate abstract class"
    except TypeError:
        print("✅ AnalysisStrategy correctly prevents direct instantiation")
    
    # Test concrete implementation
    class TestStrategy(AnalysisStrategy):
        def get_actions(self, context):
            return ["test action"]
        
        def get_insights(self, context):
            return "test insight"
        
        def get_workflow_steps(self):
            return [WorkflowStep("test", "Test", "Test step", WorkflowStage.DATA_UPLOAD)]
    
    test_strategy = TestStrategy("test_analysis")
    assert test_strategy.analysis_type == "test_analysis", "Analysis type should be set"
    
    metadata = test_strategy.get_metadata()
    assert metadata["analysis_type"] == "test_analysis", "Metadata should include analysis type"
    
    actions = test_strategy.get_actions({})
    assert len(actions) == 1, "Should return test action"
    
    assert test_strategy.validate_context({}), "Should validate empty dict"
    assert not test_strategy.validate_context("invalid"), "Should reject non-dict"
    print("✅ AnalysisStrategy concrete implementation tests passed")
    
    # Test error classes
    print("Testing custom error classes...")
    try:
        raise ValidationError("Test validation error")
    except ValidationError as e:
        assert str(e) == "Test validation error", "ValidationError should work"
    
    try:
        raise StrategyError("Test strategy error")
    except StrategyError as e:
        assert str(e) == "Test strategy error", "StrategyError should work"
    print("✅ Custom error classes tests passed")
    
    print("\n🎉 All base component tests passed!")
    return True


if __name__ == "__main__":
    def test_static_base():
        """Static tests for base components"""
        print("Running static base component tests...")
        
        # Test enum values
        assert len(WorkflowStage) == 7, "Should have 7 workflow stages"
        
        # Test dataclass creation
        rule = ActionRule(lambda x: True, "test")
        assert rule.action == "test", "ActionRule should be created"
        
        insight = InsightRule(lambda x: True, lambda x: "test")
        assert insight.category == "general", "InsightRule should have default category"
        
        step = WorkflowStep("key", "title", "desc", WorkflowStage.DATA_UPLOAD)
        assert step.key == "key", "WorkflowStep should be created"
        
        print("✅ Static base component tests passed!")
    
    def test_dynamic_base():
        """Dynamic tests for base components"""
        print("Running dynamic base component tests...")
        
        # Run comprehensive main tests
        success = main()
        assert success, "Main tests should pass"
        
        print("✅ Dynamic base component tests passed!")
    
    # Run all tests
    test_static_base()
    test_dynamic_base()