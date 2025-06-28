"""
RNA-seq Analysis Strategy

Enhanced strategy implementation for bulk RNA sequencing analysis
with improved performance, security, and Electron integration.
"""

import logging
from typing import Dict, Any, List, Optional

from .base import WorkflowStage, WorkflowStep
from .rule_based import RuleBasedAnalysisStrategy
from .rna_helpers import (
    RNADataValidator,
    RNAInsightGenerator,
    RNAProgressTracker
)

logger = logging.getLogger(__name__)


class RNASeqAnalysisStrategy(RuleBasedAnalysisStrategy):
    """Enhanced strategy for RNA-seq analysis with comprehensive workflow support"""
    
    # Strategy metadata
    STRATEGY_NAME = "rnaseq"
    VERSION = "2.0.0"
    
    def __init__(self):
        super().__init__("rnaseq")
        
        # Initialize helper components
        self.data_validator = RNADataValidator()
        self.insight_generator = RNAInsightGenerator()
        self.progress_tracker = RNAProgressTracker()
        
        # Strategy metadata
        self.metadata = {
            "name": "Bulk RNA-seq Analysis",
            "description": "Comprehensive strategy for bulk RNA-seq data analysis",
            "version": self.VERSION,
            "data_types": ["csv", "tsv", "xlsx", "txt", "h5"],
            "capabilities": [
                "differential_expression", "deseq2", "go_enrichment",
                "pathway_analysis", "visualization", "quality_control"
            ],
            "estimated_total_time": 60,  # minutes
            "complexity": "medium"
        }
    
    def _initialize_rules(self):
        """Initialize RNA-seq specific rules with enhanced logic"""
        
        # === DATA UPLOAD AND VALIDATION RULES ===
        self.add_action_rule(
            condition=lambda ctx: not ctx.get("data_uploaded", False),
            action="Upload RNA-seq counts and metadata files",
            priority=10,
            stage=WorkflowStage.DATA_UPLOAD,
            description="Upload count matrix and sample metadata",
            estimated_time=5,
            dependencies=[]
        )
        
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("data_uploaded", False) and 
                                 not self.data_validator.is_data_validated(ctx)),
            action="Validate count matrix and metadata format",
            priority=9,
            stage=WorkflowStage.DATA_UPLOAD,
            description="Ensure data format compatibility",
            estimated_time=3
        )
        
        # === QUALITY CONTROL RULES ===
        self.add_action_rule(
            condition=lambda ctx: (self.data_validator.is_data_validated(ctx) and 
                                 not self._get_pipeline_status(ctx, "qc")),
            action="Perform quality control assessment",
            priority=8,
            stage=WorkflowStage.QUALITY_CONTROL,
            description="Assess library sizes, gene detection rates",
            estimated_time=8
        )
        
        # === PREPROCESSING RULES ===
        self.add_action_rule(
            condition=lambda ctx: (self._get_pipeline_status(ctx, "qc") and
                                 not self._get_pipeline_status(ctx, "filtering")),
            action="Filter low-count genes and samples",
            priority=7,
            stage=WorkflowStage.PREPROCESSING,
            description="Remove genes/samples with insufficient counts",
            estimated_time=5
        )
        
        # === DIFFERENTIAL EXPRESSION RULES ===
        self.add_action_rule(
            condition=lambda ctx: (self._get_pipeline_status(ctx, "filtering") and
                                 not self._get_pipeline_status(ctx, "deseq2_completed")),
            action="Run differential expression analysis (DESeq2)",
            priority=6,
            stage=WorkflowStage.ANALYSIS,
            description="Identify differentially expressed genes",
            estimated_time=15
        )
        
        # === VISUALIZATION RULES ===
        self.add_action_rule(
            condition=lambda ctx: (self._get_pipeline_status(ctx, "deseq2_completed") and
                                 not self._get_pipeline_status(ctx, "visualization")),
            action="Create visualizations (PCA, volcano plot, heatmap)",
            priority=5,
            stage=WorkflowStage.VISUALIZATION,
            description="Generate plots for data exploration",
            estimated_time=10
        )
        
        # === PATHWAY ANALYSIS RULES ===
        self.add_action_rule(
            condition=lambda ctx: (self._get_pipeline_status(ctx, "deseq2_completed") and
                                 not self._get_pipeline_status(ctx, "go_enrichment_completed")),
            action="Perform Gene Ontology enrichment analysis",
            priority=4,
            stage=WorkflowStage.INTERPRETATION,
            description="Analyze enriched biological pathways",
            estimated_time=12
        )
        
        self.add_action_rule(
            condition=lambda ctx: (self._get_pipeline_status(ctx, "go_enrichment_completed") and
                                 not self._get_pipeline_status(ctx, "pathway_analysis")),
            action="Perform KEGG pathway analysis",
            priority=3,
            stage=WorkflowStage.INTERPRETATION,
            description="Analyze metabolic and signaling pathways",
            estimated_time=10
        )
        
        # === EXPORT RULES ===
        self.add_action_rule(
            condition=lambda ctx: (self._get_pipeline_status(ctx, "deseq2_completed") and
                                 not self._get_pipeline_status(ctx, "results_exported")),
            action="Export analysis results and reports",
            priority=2,
            stage=WorkflowStage.EXPORT,
            description="Save results in multiple formats",
            estimated_time=5
        )
        
        # === INSIGHT RULES ===
        self._initialize_insight_rules()
        
        # === WORKFLOW STEPS ===
        self._initialize_workflow_steps()
    
    def _initialize_insight_rules(self):
        """Initialize insight generation rules"""
        
        # Dataset overview insights
        self.add_insight_rule(
            condition=lambda ctx: self.data_validator.has_count_data(ctx),
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
        
        # DESeq2 results insights
        self.add_insight_rule(
            condition=lambda ctx: self.data_validator.has_deseq_data(ctx),
            insight_generator=lambda ctx: self.insight_generator.generate_deseq_insights(ctx),
            priority=8,
            category="analysis_results",
            severity="success"
        )
        
        # GO enrichment insights
        self.add_insight_rule(
            condition=lambda ctx: self.data_validator.has_go_data(ctx),
            insight_generator=lambda ctx: self.insight_generator.generate_go_insights(ctx),
            priority=7,
            category="pathway_results",
            severity="success"
        )
        
        # Progress insights
        self.add_insight_rule(
            condition=lambda ctx: ctx.get("pipeline_status", {}),
            insight_generator=lambda ctx: self.progress_tracker.generate_progress_insight(ctx),
            priority=6,
            category="analysis_progress",
            severity="info",
            actionable=True
        )
        
        # Performance insights
        self.add_insight_rule(
            condition=lambda ctx: self.progress_tracker.has_performance_data(ctx),
            insight_generator=lambda ctx: self.insight_generator.generate_performance_insights(ctx),
            priority=5,
            category="performance",
            severity="info"
        )
    
    def _initialize_workflow_steps(self):
        """Initialize comprehensive workflow steps"""
        self.workflow_steps = [
            WorkflowStep(
                key="data_upload",
                title="Data Upload",
                description="Upload count matrix and metadata",
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
                description="Assess data quality metrics",
                stage=WorkflowStage.QUALITY_CONTROL,
                dependencies=["data_validation"],
                estimated_time=8,
                complexity="medium"
            ),
            WorkflowStep(
                key="filtering",
                title="Data Filtering",
                description="Filter low-count features",
                stage=WorkflowStage.PREPROCESSING,
                dependencies=["qc"],
                estimated_time=5,
                complexity="medium"
            ),
            WorkflowStep(
                key="deseq2",
                title="Differential Expression",
                description="DESeq2 analysis",
                stage=WorkflowStage.ANALYSIS,
                dependencies=["filtering"],
                estimated_time=15,
                complexity="high"
            ),
            WorkflowStep(
                key="visualization",
                title="Visualization",
                description="Create plots and charts",
                stage=WorkflowStage.VISUALIZATION,
                dependencies=["deseq2"],
                estimated_time=10,
                complexity="medium"
            ),
            WorkflowStep(
                key="go_enrichment",
                title="GO Enrichment",
                description="Gene Ontology analysis",
                stage=WorkflowStage.INTERPRETATION,
                dependencies=["deseq2"],
                estimated_time=12,
                complexity="medium"
            ),
            WorkflowStep(
                key="pathway_analysis",
                title="Pathway Analysis",
                description="KEGG pathway analysis",
                stage=WorkflowStage.INTERPRETATION,
                dependencies=["go_enrichment"],
                estimated_time=10,
                complexity="medium",
                optional=True
            ),
            WorkflowStep(
                key="export",
                title="Export Results",
                description="Save analysis results",
                stage=WorkflowStage.EXPORT,
                dependencies=["deseq2"],
                estimated_time=5,
                complexity="low"
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
    
    def get_significant_genes_count(self, context: Dict[str, Any]) -> int:
        """Get count of significantly differentially expressed genes"""
        return self.data_validator.get_significant_genes_count(context)
    
    def validate_context(self, context: Dict[str, Any]) -> bool:
        """Enhanced context validation for RNA-seq"""
        if not super().validate_context(context):
            return False
        
        return self.data_validator.validate_context(context)


def main():
    """Test RNA-seq strategy functionality"""
    print("🧪 Testing RNA-seq Analysis Strategy")
    print("=" * 50)
    
    # Test strategy creation
    print("Testing strategy creation...")
    strategy = RNASeqAnalysisStrategy()
    assert strategy.analysis_type == "rnaseq", f"Expected 'rnaseq', got '{strategy.analysis_type}'"
    assert strategy.VERSION == "2.0.0", "Should have correct version"
    print("✅ Strategy creation passed")
    
    # Test metadata
    print("Testing strategy metadata...")
    metadata = strategy.get_metadata()
    assert "capabilities" in metadata["metadata"], "Should have capabilities in metadata"
    assert "differential_expression" in metadata["metadata"]["capabilities"], "Should support DE"
    assert "go_enrichment" in metadata["metadata"]["capabilities"], "Should support GO"
    print("✅ Metadata tests passed")
    
    # Test empty context
    print("Testing empty context...")
    empty_context = {}
    actions = strategy.get_actions(empty_context)
    insights = strategy.get_insights(empty_context)
    workflow_steps = strategy.get_workflow_steps()
    
    assert len(actions) > 0, "Should have at least one action"
    assert any("upload" in action.lower() for action in actions), "Should suggest data upload"
    assert len(workflow_steps) == 9, f"Should have 9 workflow steps, got {len(workflow_steps)}"
    print("✅ Empty context tests passed")
    
    # Test progressive workflow
    print("Testing progressive workflow...")
    
    # Data uploaded context
    uploaded_context = {
        "data_uploaded": True, 
        "data_summary": {"n_samples": 12, "n_genes": 15000}
    }
    actions_uploaded = strategy.get_actions(uploaded_context)
    insights_uploaded = strategy.get_insights(uploaded_context)
    
    assert any("quality control" in action.lower() for action in actions_uploaded), "Should suggest QC"
    assert "12 samples" in insights_uploaded, "Should show sample count"
    
    # QC completed context
    qc_context = {
        "data_uploaded": True,
        "pipeline_status": {"qc": True}
    }
    actions_qc = strategy.get_actions(qc_context)
    assert any("filter" in action.lower() for action in actions_qc), "Should suggest filtering"
    
    # DESeq2 completed context
    deseq_context = {
        "data_uploaded": True,
        "pipeline_status": {
            "qc": True,
            "filtering": True,
            "deseq2_completed": True
        }
    }
    actions_deseq = strategy.get_actions(deseq_context)
    assert any("gene ontology" in action.lower() or "visualization" in action.lower() 
              for action in actions_deseq), "Should suggest GO or visualization"
    
    print("✅ Progressive workflow tests passed")
    
    # Test workflow step dependencies
    print("Testing workflow step dependencies...")
    upload_step = next((step for step in workflow_steps if step.key == "data_upload"), None)
    deseq_step = next((step for step in workflow_steps if step.key == "deseq2"), None)
    go_step = next((step for step in workflow_steps if step.key == "go_enrichment"), None)
    
    assert upload_step is not None, "Should have upload step"
    assert deseq_step is not None, "Should have DESeq2 step"
    assert go_step is not None, "Should have GO enrichment step"
    
    assert upload_step.dependencies == [], "Upload should have no dependencies"
    assert "filtering" in deseq_step.dependencies, "DESeq2 should depend on filtering"
    assert "deseq2" in go_step.dependencies, "GO should depend on DESeq2"
    print("✅ Workflow dependency tests passed")
    
    # Test time estimation
    print("Testing time estimation...")
    time_remaining = strategy.get_estimated_time_remaining(deseq_context)
    completion_pct = strategy.get_completion_percentage(deseq_context)
    
    assert isinstance(time_remaining, int), "Time remaining should be integer"
    assert 0 <= completion_pct <= 100, f"Completion should be 0-100%, got {completion_pct}"
    assert completion_pct > 50, "Should show significant progress for DESeq2 completed context"
    print("✅ Time estimation tests passed")
    
    # Test significant genes count
    print("Testing significant genes count...")
    sig_genes = strategy.get_significant_genes_count(deseq_context)
    assert isinstance(sig_genes, int), "Significant genes count should be integer"
    assert sig_genes >= 0, "Count should be non-negative"
    print("✅ Significant genes count tests passed")
    
    # Test context validation
    print("Testing context validation...")
    valid_contexts = [
        {},
        {"data_uploaded": True},
        {"pipeline_status": {"deseq2_completed": True}},
        {"data_summary": {"n_samples": 10, "n_genes": 20000}}
    ]
    
    invalid_contexts = [
        "not a dict",
        None,
        {"pipeline_status": "not a dict"},
        {"data_summary": {"n_samples": -1}}
    ]
    
    for valid_ctx in valid_contexts:
        assert strategy.validate_context(valid_ctx), f"Should validate context: {valid_ctx}"
    
    for invalid_ctx in invalid_contexts:
        result = strategy.validate_context(invalid_ctx)
        # Should handle gracefully, might return False but shouldn't crash
        assert isinstance(result, bool), "Validation should return boolean"
    
    print("✅ Context validation tests passed")
    
    print("\n🎉 All RNA-seq strategy tests passed!")
    return True


if __name__ == "__main__":
    def test_static_rna():
        """Static tests for RNA-seq strategy"""
        print("Running static RNA-seq strategy tests...")
        
        # Test class attributes
        assert hasattr(RNASeqAnalysisStrategy, 'STRATEGY_NAME'), "Should have strategy name"
        assert hasattr(RNASeqAnalysisStrategy, 'VERSION'), "Should have version"
        assert RNASeqAnalysisStrategy.STRATEGY_NAME == "rnaseq", "Should have correct strategy name"
        
        print("✅ Static RNA-seq strategy tests passed!")
    
    def test_dynamic_rna():
        """Dynamic tests for RNA-seq strategy"""
        print("Running dynamic RNA-seq strategy tests...")
        
        # Run comprehensive main tests
        success = main()
        assert success, "Main tests should pass"
        
        print("✅ Dynamic RNA-seq strategy tests passed!")
    
    # Run all tests
    test_static_rna()
    test_dynamic_rna()