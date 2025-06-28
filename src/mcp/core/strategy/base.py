"""
Base Strategy Components

Contains abstract base classes, enums, and data structures
used across all strategy implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class WorkflowStage(Enum):
    """Standard workflow stages across analysis types"""
    DATA_UPLOAD = "data_upload"
    QUALITY_CONTROL = "quality_control"
    PREPROCESSING = "preprocessing"
    ANALYSIS = "analysis"
    VISUALIZATION = "visualization"
    INTERPRETATION = "interpretation"
    EXPORT = "export"


@dataclass
class ActionRule:
    """Rule for generating suggested actions"""
    condition: callable  # Function that returns bool
    action: str
    priority: int = 1
    stage: Optional[WorkflowStage] = None


@dataclass
class InsightRule:
    """Rule for generating analysis insights"""
    condition: callable  # Function that returns bool
    insight_generator: callable  # Function that returns insight string
    priority: int = 1
    category: str = "general"  # e.g., "data_quality", "analysis_progress", "results"


@dataclass
class WorkflowStep:
    """Configuration for a workflow step"""
    key: str
    title: str
    description: str
    stage: WorkflowStage
    dependencies: List[str] = None
    optional: bool = False


class AnalysisStrategy(ABC):
    """Abstract strategy for analysis-specific behavior"""
    
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


# Test code for independent validation
if __name__ == "__main__":
    # Suppress the RuntimeWarning about module import behavior
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning, 
                          message=".*found in sys.modules.*")
    
    def test_base_components():
        """Test base components functionality"""
        print("Testing base strategy components...")
        
        # Test WorkflowStage enum
        stages = list(WorkflowStage)
        print(f"✅ WorkflowStage enum has {len(stages)} stages")
        assert len(stages) == 7, f"Expected 7 stages, got {len(stages)}"
        
        # Test ActionRule dataclass
        test_rule = ActionRule(
            condition=lambda ctx: True,
            action="Test action",
            priority=5,
            stage=WorkflowStage.DATA_UPLOAD
        )
        print(f"✅ ActionRule created: {test_rule.action}")
        assert test_rule.condition({}), "Condition should return True"
        
        # Test InsightRule dataclass
        insight_rule = InsightRule(
            condition=lambda ctx: True,
            insight_generator=lambda ctx: "Test insight",
            priority=3,
            category="test"
        )
        print(f"✅ InsightRule created: {insight_rule.category}")
        assert insight_rule.insight_generator({}) == "Test insight"
        
        # Test WorkflowStep dataclass
        step = WorkflowStep(
            key="test_step",
            title="Test Step",
            description="A test workflow step",
            stage=WorkflowStage.ANALYSIS,
            dependencies=["previous_step"],
            optional=False
        )
        print(f"✅ WorkflowStep created: {step.title}")
        assert step.key == "test_step"
        assert step.dependencies == ["previous_step"]
        
        # Test AnalysisStrategy is abstract
        try:
            # This should fail because AnalysisStrategy is abstract
            strategy = AnalysisStrategy()
            assert False, "Should not be able to instantiate abstract class"
        except TypeError:
            print("✅ AnalysisStrategy correctly prevents direct instantiation")
        
        print("🎉 All base component tests passed!")
    
    # Run test
    test_base_components() 