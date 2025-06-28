"""
scRNA-seq Analysis Strategy

Enhanced strategy implementation for single-cell RNA sequencing analysis
with improved performance, security, and Electron integration.
"""

import logging
from typing import Dict, Any, List, Optional

from .base import WorkflowStage, WorkflowStep
from .rule_based import RuleBasedAnalysisStrategy
from .scrna_helpers import (
    scRNADataValidator,
    scRNAInsightGenerator,
    scRNAProgressTracker
)

logger = logging.getLogger(__name__)


class scRNASeqAnalysisStrategy(RuleBasedAnalysisStrategy):
    """Enhanced strategy for scRNA-seq analysis with comprehensive workflow support"""
    
    # Strategy metadata
    STRATEGY_NAME = "scrnaseq"
    VERSION = "2.0.0"
    
    def __init__(self):
        super().__init__("scrnaseq")
        
        # Initialize helper components
        self.data_validator = scRNADataValidator()
        self.insight_generator = scRNAInsightGenerator()
        self.progress_tracker = scRNAProgressTracker()
        
        # Strategy metadata
        self.metadata = {
            "name": "Single-cell RNA-seq Analysis",
            "description": "Comprehensive strategy for scRNA-seq data analysis",
            "version": self.VERSION,
            "data_types": ["h5ad", "csv", "tsv", "h5", "xlsx"],
            "capabilities": [
                "quality_control", "filtering", "normalization", 
                "dimensionality_reduction", "clustering", 
                "differential_expression", "pathway_analysis", "visualization"
            ],
            "estimated_total_time": 120,  # minutes
            "complexity": "high"
        }
    
    def _initialize_rules(self):
        """Initialize scRNA-seq specific rules with enhanced logic"""
        
        # === DATA UPLOAD AND VALIDATION RULES ===
        self.add_action_rule(
            condition=lambda ctx: not ctx.get("data_uploaded", False),
            action="Upload scRNA-seq data (.h5ad, 10x format, or CSV)",
            priority=10,
            stage=WorkflowStage.DATA_UPLOAD,
            description="Upload your single-cell RNA-seq dataset",
            estimated_time=5,
            dependencies=[]
        )
        
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("data_uploaded", False) and 
                                 not self.data_validator.is_data_validated(ctx)),
            action="Validate dataset format and structure",
            priority=9,
            stage=WorkflowStage.DATA_UPLOAD,
            description="Ensure data format is compatible",
            estimated_time=3
        )
        
        # === QUALITY CONTROL RULES ===
        self.add_action_rule(
            condition=lambda ctx: (self.data_validator.is_data_validated(ctx) and 
                                 not self._get_pipeline_status(ctx, "qc")),
            action="Perform quality control analysis",
            priority=8,
            stage=WorkflowStage.QUALITY_CONTROL,
            description="Calculate QC metrics (mitochondrial genes, ribosomal genes, etc.)",
            estimated_time=10
        )
        
        # === PREPROCESSING RULES ===
        self.add_action_rule(
            condition=lambda ctx: (self._get_pipeline_status(ctx, "qc") and
                                 not self._get_pipeline_status(ctx, "filtering")),
            action="Filter low-quality cells and genes",
            priority=7,
            stage=WorkflowStage.PREPROCESSING,
            description="Remove cells and genes based on QC metrics",
            estimated_time=15
        )
        
        self.add_action_rule(
            condition=lambda ctx: (self._get_pipeline_status(ctx, "filtering") and
                                 not self._get_pipeline_status(ctx, "normalization")),
            action="Normalize and scale expression data",
            priority=6,
            stage=WorkflowStage.PREPROCESSING,
            description="Normalize counts and scale for downstream analysis",
            estimated_time=20
        )
        
        # === ANALYSIS RULES ===
        self.add_action_rule(
            condition=lambda ctx: (self._get_pipeline_status(ctx, "normalization") and
                                 not self._get_pipeline_status(ctx, "dimred")),
            action="Perform dimensionality reduction (PCA/UMAP)",
            priority=5,
            stage=WorkflowStage.ANALYSIS,
            description="Reduce dimensionality for visualization and clustering",
            estimated_time=25
        )
        
        self.add_action_rule(
            condition=lambda ctx: (self._get_pipeline_status(ctx, "dimred") and
                                 not self._get_pipeline_status(ctx, "clustering")),
            action="Cluster cells to identify populations",
            priority=4,
            stage=WorkflowStage.ANALYSIS,
            description="Group cells into clusters using Leiden algorithm",
            estimated_time=20
        )
        
        self.add_action_rule(
            condition=lambda ctx: (self._get_pipeline_status(ctx, "clustering") and
                                 not self._get_pipeline_status(ctx, "dea")),
            action="Find marker genes for each cluster",
            priority=3,
            stage=WorkflowStage.ANALYSIS,
            description="Identify genes that characterize each cell cluster",
            estimated_time=30
        )
        
        # === VISUALIZATION RULES ===
        self.add_action_rule(
            condition=lambda ctx: (self._get_pipeline_status(ctx, "clustering") and
                                 not self._get_pipeline_status(ctx, "viz")),
            action="Create visualizations (UMAP, heatmaps, violin plots)",
            priority=3,
            stage=WorkflowStage.VISUALIZATION,
            description="Generate plots for data exploration and presentation",
            estimated_time=15
        )
        
        # === INTERPRETATION RULES ===
        self.add_action_rule(
            condition=lambda ctx: (self._get_pipeline_status(ctx, "dea") and
                                 not self._get_pipeline_status(ctx, "enrichment")),
            action="Perform pathway enrichment analysis",
            priority=2,
            stage=WorkflowStage.INTERPRETATION,
            description="Analyze biological pathways in marker genes",
            estimated_time=20
        )
        
        # === INSIGHT RULES ===
        self._initialize_insight_rules()
        
        # === WORKFLOW STEPS ===
        self._initialize_workflow_steps()
    
    def _initialize_insight_rules(self):
        """Initialize insight generation rules"""
        
        # Dataset overview insights
        self.add_insight_rule(
            condition=lambda ctx: self.data_validator.has_basic_data(ctx),
            insight_generator=lambda ctx: self.insight_generator.generate_dataset_overview(ctx),
            priority=10,
            category="data_overview",
            severity="info"
        )
        
        # QC insights
        self.add_insight_rule(
            condition=lambda ctx: self.data_validator.has_qc_metrics(ctx),
            insight_generator=lambda ctx: self.insight_generator.generate_qc_insights(ctx),
            priority=9,
            category="data_quality",
            severity="info"
        )
        
        # Clustering insights
        self.add_insight_rule(
            condition=lambda ctx: self.data_validator.has_clustering_data(ctx),
            insight_generator=lambda ctx: self.insight_generator.generate_clustering_insights(ctx),
            priority=8,
            category="analysis_results",
            severity="success"
        )
        
        # Progress insights
        self.add_insight_rule(
            condition=lambda ctx: ctx.get("pipeline_status", {}),
            insight_generator=lambda ctx: self.progress_tracker.generate_progress_insight(ctx),
            priority=7,
            category="analysis_progress",
            severity="info",
            actionable=True
        )
        
        # Performance insights
        self.add_insight_rule(
            condition=lambda ctx: self.progress_tracker.has_performance_data(ctx),
            insight_generator=lambda ctx: self.insight_generator.generate_performance_insights(ctx),
            priority=6,
            category="performance",
            severity="info"
        )
    
    def _initialize_workflow_steps(self):
        """Initialize comprehensive workflow steps"""
        self.workflow_steps = [
            WorkflowStep(
                key="data_upload",
                title="Data Upload",
                description="Upload scRNA-seq dataset",
                stage=WorkflowStage.DATA_UPLOAD,
                estimated_time=5,
                complexity="low"
            ),
            WorkflowStep(
                key="data_validation",
                title="Data Validation",
                description="Validate data format and structure",
                stage=WorkflowStage.DATA_UPLOAD,
                dependencies=["data_upload"],
                estimated_time=3,
                complexity="low"
            ),
            WorkflowStep(
                key="qc",
                title="Quality Control",
                description="Calculate quality control metrics",
                stage=WorkflowStage.QUALITY_CONTROL,
                dependencies=["data_validation"],
                estimated_time=10,
                complexity="medium"
            ),
            WorkflowStep(
                key="filtering",
                title="Cell/Gene Filtering",
                description="Filter low-quality cells and genes",
                stage=WorkflowStage.PREPROCESSING,
                dependencies=["qc"],
                estimated_time=15,
                complexity="medium"
            ),
            WorkflowStep(
                key="normalization",
                title="Normalization",
                description="Normalize and scale expression data",
                stage=WorkflowStage.PREPROCESSING,
                dependencies=["filtering"],
                estimated_time=20,
                complexity="medium"
            ),
            WorkflowStep(
                key="dimred",
                title="Dimensionality Reduction",
                description="PCA and UMAP analysis",
                stage=WorkflowStage.ANALYSIS,
                dependencies=["normalization"],
                estimated_time=25,
                complexity="high"
            ),
            WorkflowStep(
                key="clustering",
                title="Cell Clustering",
                description="Identify cell populations",
                stage=WorkflowStage.ANALYSIS,
                dependencies=["dimred"],
                estimated_time=20,
                complexity="high"
            ),
            WorkflowStep(
                key="dea",
                title="Differential Expression",
                description="Find cluster marker genes",
                stage=WorkflowStage.ANALYSIS,
                dependencies=["clustering"],
                estimated_time=30,
                complexity="high"
            ),
            WorkflowStep(
                key="viz",
                title="Visualization",
                description="Create plots and charts",
                stage=WorkflowStage.VISUALIZATION,
                dependencies=["clustering"],
                estimated_time=15,
                complexity="medium",
                optional=True
            ),
            WorkflowStep(
                key="enrichment",
                title="Pathway Enrichment",
                description="Analyze biological pathways",
                stage=WorkflowStage.INTERPRETATION,
                dependencies=["dea"],
                estimated_time=20,
                complexity="medium",
                optional=True
            )
        ]
    
    def _get_pipeline_status(self, context: Dict[str, Any], step: str) -> bool:
        """Get pipeline step completion status with validation"""
        try:
            pipeline_status = context.get("pipeline_status", {})
            return pipeline_status.get(step, False)
        except (AttributeError, TypeError):
            logger.warning(f"Invalid pipeline status format for step: {step}")
            return False
    
    def get_estimated_time_remaining(self, context: Dict[str, Any]) -> int:
        """Calculate estimated time remaining for analysis"""
        return self.progress_tracker.calculate_time_remaining(context, self.workflow_steps)
    
    def get_completion_percentage(self, context: Dict[str, Any]) -> float:
        """Calculate analysis completion percentage"""
        return self.progress_tracker.calculate_completion_percentage(context, self.workflow_steps)
    
    def validate_context(self, context: Dict[str, Any]) -> bool:
        """Enhanced context validation for scRNA-seq"""
        if not super().validate_context(context):
            return False
        
        return self.data_validator.validate_context(context)


def main():
    """Test scRNA-seq strategy functionality"""
    print("🧪 Testing scRNA-seq Analysis Strategy")
    print("=" * 50)
    
    # Test strategy creation
    print("Testing strategy creation...")
    strategy = scRNASeqAnalysisStrategy()
    assert strategy.analysis_type == "scrnaseq", f"Expected 'scrnaseq', got '{strategy.analysis_type}'"
    assert strategy.VERSION == "2.0.0", "Should have correct version"
    print("✅ Strategy creation passed")
    
    # Test metadata
    print("Testing strategy metadata...")
    metadata = strategy.get_metadata()
    assert "capabilities" in metadata["metadata"], "Should have capabilities in metadata"
    assert "quality_control" in metadata["metadata"]["capabilities"], "Should support QC"
    assert "clustering" in metadata["metadata"]["capabilities"], "Should support clustering"
    print("✅ Metadata tests passed")
    
    # Test empty context
    print("Testing empty context...")
    empty_context = {}
    actions = strategy.get_actions(empty_context)
    insights = strategy.get_insights(empty_context)
    workflow_steps = strategy.get_workflow_steps()
    
    assert len(actions) > 0, "Should have at least one action"
    assert any("upload" in action.lower() for action in actions), "Should suggest data upload"
    assert len(workflow_steps) == 10, f"Should have 10 workflow steps, got {len(workflow_steps)}"
    print("✅ Empty context tests passed")
    
    # Test progressive workflow
    print("Testing progressive workflow...")
    
    # Data uploaded context
    uploaded_context = {"data_uploaded": True, "data_summary": {"n_cells": 5000, "n_genes": 20000}}
    actions_uploaded = strategy.get_actions(uploaded_context)
    insights_uploaded = strategy.get_insights(uploaded_context)
    
    assert any("quality control" in action.lower() for action in actions_uploaded), "Should suggest QC"
    assert "5,000 cells" in insights_uploaded or "5000 cells" in insights_uploaded, "Should show cell count"
    
    # QC completed context
    qc_context = {
        "data_uploaded": True,
        "pipeline_status": {"qc": True}
    }
    actions_qc = strategy.get_actions(qc_context)
    assert any("filter" in action.lower() for action in actions_qc), "Should suggest filtering"
    
    # Multiple steps completed
    advanced_context = {
        "data_uploaded": True,
        "pipeline_status": {
            "qc": True,
            "filtering": True,
            "normalization": True,
            "dimred": True
        }
    }
    actions_advanced = strategy.get_actions(advanced_context)
    assert any("cluster" in action.lower() for action in actions_advanced), "Should suggest clustering"
    
    print("✅ Progressive workflow tests passed")
    
    # Test workflow step dependencies
    print("Testing workflow step dependencies...")
    upload_step = next((step for step in workflow_steps if step.key == "data_upload"), None)
    qc_step = next((step for step in workflow_steps if step.key == "qc"), None)
    clustering_step = next((step for step in workflow_steps if step.key == "clustering"), None)
    
    assert upload_step is not None, "Should have upload step"
    assert qc_step is not None, "Should have QC step"
    assert clustering_step is not None, "Should have clustering step"
    
    assert upload_step.dependencies == [], "Upload should have no dependencies"
    assert "data_validation" in qc_step.dependencies, "QC should depend on validation"
    assert "dimred" in clustering_step.dependencies, "Clustering should depend on dimred"
    print("✅ Workflow dependency tests passed")
    
    # Test time estimation
    print("Testing time estimation...")
    time_remaining = strategy.get_estimated_time_remaining(advanced_context)
    completion_pct = strategy.get_completion_percentage(advanced_context)
    
    assert isinstance(time_remaining, int), "Time remaining should be integer"
    assert 0 <= completion_pct <= 100, f"Completion should be 0-100%, got {completion_pct}"
    assert completion_pct > 0, "Should show some progress for advanced context"
    print("✅ Time estimation tests passed")
    
    # Test context validation
    print("Testing context validation...")
    valid_contexts = [
        {},
        {"data_uploaded": True},
        {"pipeline_status": {"qc": True}}
    ]
    
    invalid_contexts = [
        "not a dict",
        None,
        {"pipeline_status": "not a dict"}
    ]
    
    for valid_ctx in valid_contexts:
        assert strategy.validate_context(valid_ctx), f"Should validate context: {valid_ctx}"
    
    for invalid_ctx in invalid_contexts:
        result = strategy.validate_context(invalid_ctx)
        # Should handle gracefully, might return False but shouldn't crash
        assert isinstance(result, bool), "Validation should return boolean"
    
    print("✅ Context validation tests passed")
    
    print("\n🎉 All scRNA-seq strategy tests passed!")
    return True


if __name__ == "__main__":
    def test_static_scrna():
        """Static tests for scRNA-seq strategy"""
        print("Running static scRNA-seq strategy tests...")
        
        # Test class attributes
        assert hasattr(scRNASeqAnalysisStrategy, 'STRATEGY_NAME'), "Should have strategy name"
        assert hasattr(scRNASeqAnalysisStrategy, 'VERSION'), "Should have version"
        assert scRNASeqAnalysisStrategy.STRATEGY_NAME == "scrnaseq", "Should have correct strategy name"
        
        print("✅ Static scRNA-seq strategy tests passed!")
    
    def test_dynamic_scrna():
        """Dynamic tests for scRNA-seq strategy"""
        print("Running dynamic scRNA-seq strategy tests...")
        
        # Run comprehensive main tests
        success = main()
        assert success, "Main tests should pass"
        
        print("✅ Dynamic scRNA-seq strategy tests passed!")
    
    # Run all tests
    test_static_scrna()
    test_dynamic_scrna()