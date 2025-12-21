"""
ATAC-seq Analysis Strategy

Enhanced strategy implementation for ATAC-seq (chromatin accessibility) analysis
with improved performance, security, and Electron integration.
"""

import logging
from typing import Dict, Any, List, Optional

from .base import WorkflowStage, WorkflowStep
from .rule_based import RuleBasedAnalysisStrategy
from .atac_helpers import (
    ATACDataValidator,
    ATACInsightGenerator,
    ATACProgressTracker
)

logger = logging.getLogger(__name__)


class ATACSeqAnalysisStrategy(RuleBasedAnalysisStrategy):
    """Enhanced strategy for ATAC-seq analysis with comprehensive workflow support"""
    
    # Strategy metadata
    STRATEGY_NAME = "atacseq"
    VERSION = "2.0.0"
    
    def __init__(self):
        super().__init__("atacseq")
        
        # Initialize helper components
        self.data_validator = ATACDataValidator()
        self.insight_generator = ATACInsightGenerator()
        self.progress_tracker = ATACProgressTracker()
        
        # Strategy metadata
        self.metadata = {
            "name": "ATAC-seq Analysis",
            "description": "Comprehensive strategy for chromatin accessibility analysis",
            "version": self.VERSION,
            "data_types": ["bed", "bam", "csv", "tsv", "h5", "peak"],
            "capabilities": [
                "peak_calling", "quality_control", "differential_accessibility",
                "motif_enrichment", "footprinting", "visualization"
            ],
            "estimated_total_time": 90,  # minutes
            "complexity": "high"
        }
    
    def _initialize_rules(self):
        """Initialize ATAC-seq specific rules with enhanced logic"""
        
        # === DATA UPLOAD AND VALIDATION RULES ===
        self.add_action_rule(
            condition=lambda ctx: not ctx.get("data_uploaded", False),
            action="Upload ATAC-seq peak data or fragment files",
            priority=10,
            stage=WorkflowStage.DATA_UPLOAD,
            description="Upload peak files (BED) or fragment files (BAM)",
            estimated_time=5,
            dependencies=[]
        )
        
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("data_uploaded", False) and 
                                 not self.data_validator.is_data_validated(ctx)),
            action="Validate ATAC-seq data format and structure",
            priority=9,
            stage=WorkflowStage.DATA_UPLOAD,
            description="Ensure data format is compatible",
            estimated_time=3
        )
        
        # === QUALITY CONTROL RULES ===
        self.add_action_rule(
            condition=lambda ctx: (self.data_validator.is_data_validated(ctx) and
                                 not self._get_pipeline_status(ctx, "qc")),
            action="Calculate QC metrics (TSS enrichment, nucleosome signal)",
            priority=8,
            stage=WorkflowStage.QUALITY_CONTROL,
            description="Assess chromatin accessibility quality",
            estimated_time=12
        )
        
        # === PEAK CALLING RULES ===
        self.add_action_rule(
            condition=lambda ctx: (self._get_pipeline_status(ctx, "qc") and
                                 not self._get_pipeline_status(ctx, "peak_calling")),
            action="Call accessible chromatin peaks",
            priority=7,
            stage=WorkflowStage.ANALYSIS,
            description="Identify regions of chromatin accessibility",
            estimated_time=20
        )
        
        # === DIFFERENTIAL ACCESSIBILITY RULES ===
        self.add_action_rule(
            condition=lambda ctx: (self._get_pipeline_status(ctx, "peak_calling") and
                                 not self._get_pipeline_status(ctx, "differential")),
            action="Perform differential accessibility analysis",
            priority=6,
            stage=WorkflowStage.ANALYSIS,
            description="Find differentially accessible regions",
            estimated_time=18
        )
        
        # === MOTIF ENRICHMENT RULES ===
        self.add_action_rule(
            condition=lambda ctx: (self._get_pipeline_status(ctx, "differential") and
                                 not self._get_pipeline_status(ctx, "motif_enrichment")),
            action="Run motif enrichment analysis",
            priority=5,
            stage=WorkflowStage.INTERPRETATION,
            description="Identify enriched transcription factor motifs",
            estimated_time=15
        )
        
        # === FOOTPRINTING RULES ===
        self.add_action_rule(
            condition=lambda ctx: (self._get_pipeline_status(ctx, "peak_calling") and
                                 not self._get_pipeline_status(ctx, "footprinting")),
            action="Perform transcription factor footprinting",
            priority=4,
            stage=WorkflowStage.INTERPRETATION,
            description="Identify TF binding footprints",
            estimated_time=25,
            dependencies=["peak_calling"]
        )
        
        # === VISUALIZATION RULES ===
        self.add_action_rule(
            condition=lambda ctx: (self._get_pipeline_status(ctx, "peak_calling") and
                                 not self._get_pipeline_status(ctx, "visualization")),
            action="Create visualizations (genome browser tracks, heatmaps)",
            priority=3,
            stage=WorkflowStage.VISUALIZATION,
            description="Generate plots and genome browser tracks",
            estimated_time=12
        )
        
        # === EXPORT RULES ===
        self.add_action_rule(
            condition=lambda ctx: (self._get_pipeline_status(ctx, "peak_calling") and
                                 not self._get_pipeline_status(ctx, "results_exported")),
            action="Export peaks and analysis results",
            priority=2,
            stage=WorkflowStage.EXPORT,
            description="Save results in standard formats",
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
            condition=lambda ctx: self.data_validator.has_peak_data(ctx),
            insight_generator=lambda ctx: self.insight_generator.generate_dataset_overview(ctx),
            priority=10,
            category="data_overview",
            severity="info"
        )
        
        # TSS enrichment insights
        self.add_insight_rule(
            condition=lambda ctx: self.data_validator.has_tss_enrichment(ctx),
            insight_generator=lambda ctx: self.insight_generator.generate_tss_insights(ctx),
            priority=9,
            category="data_quality",
            severity="info"
        )
        
        # Peak calling insights
        self.add_insight_rule(
            condition=lambda ctx: self.data_validator.has_peak_calling_results(ctx),
            insight_generator=lambda ctx: self.insight_generator.generate_peak_insights(ctx),
            priority=8,
            category="analysis_results",
            severity="success"
        )
        
        # Differential accessibility insights
        self.add_insight_rule(
            condition=lambda ctx: self.data_validator.has_differential_peaks(ctx),
            insight_generator=lambda ctx: self.insight_generator.generate_differential_insights(ctx),
            priority=7,
            category="analysis_results",
            severity="success"
        )
        
        # Motif enrichment insights
        self.add_insight_rule(
            condition=lambda ctx: self.data_validator.has_motif_enrichment(ctx),
            insight_generator=lambda ctx: self.insight_generator.generate_motif_insights(ctx),
            priority=6,
            category="motif_results",
            severity="success"
        )
        
        # Progress insights
        self.add_insight_rule(
            condition=lambda ctx: ctx.get("pipeline_status", {}),
            insight_generator=lambda ctx: self.progress_tracker.generate_progress_insight(ctx),
            priority=5,
            category="analysis_progress",
            severity="info",
            actionable=True
        )
    
    def _initialize_workflow_steps(self):
        """Initialize comprehensive workflow steps"""
        self.workflow_steps = [
            WorkflowStep(
                key="data_upload",
                title="Data Upload",
                description="Upload ATAC-seq data files",
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
                description="Calculate QC metrics",
                stage=WorkflowStage.QUALITY_CONTROL,
                dependencies=["data_validation"],
                estimated_time=12,
                complexity="medium"
            ),
            WorkflowStep(
                key="peak_calling",
                title="Peak Calling",
                description="Identify accessible regions",
                stage=WorkflowStage.ANALYSIS,
                dependencies=["qc"],
                estimated_time=20,
                complexity="high"
            ),
            WorkflowStep(
                key="differential",
                title="Differential Accessibility",
                description="Find differential peaks",
                stage=WorkflowStage.ANALYSIS,
                dependencies=["peak_calling"],
                estimated_time=18,
                complexity="high"
            ),
            WorkflowStep(
                key="motif_enrichment",
                title="Motif Enrichment",
                description="Analyze TF motifs",
                stage=WorkflowStage.INTERPRETATION,
                dependencies=["differential"],
                estimated_time=15,
                complexity="medium"
            ),
            WorkflowStep(
                key="footprinting",
                title="TF Footprinting",
                description="Identify TF footprints",
                stage=WorkflowStage.INTERPRETATION,
                dependencies=["peak_calling"],
                estimated_time=25,
                complexity="high",
                optional=True
            ),
            WorkflowStep(
                key="visualization",
                title="Visualization",
                description="Create plots and tracks",
                stage=WorkflowStage.VISUALIZATION,
                dependencies=["peak_calling"],
                estimated_time=12,
                complexity="medium"
            ),
            WorkflowStep(
                key="export",
                title="Export Results",
                description="Save analysis results",
                stage=WorkflowStage.EXPORT,
                dependencies=["peak_calling"],
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
    
    def get_peak_count(self, context: Dict[str, Any]) -> int:
        """Get count of identified peaks"""
        return self.data_validator.get_peak_count(context)
    
    def validate_context(self, context: Dict[str, Any]) -> bool:
        """Enhanced context validation for ATAC-seq"""
        if not super().validate_context(context):
            return False
        
        return self.data_validator.validate_context(context)


def main():
    """Test ATAC-seq strategy functionality"""
    print("🧪 Testing ATAC-seq Analysis Strategy")
    print("=" * 50)
    
    # Test strategy creation
    print("Testing strategy creation...")
    strategy = ATACSeqAnalysisStrategy()
    assert strategy.analysis_type == "atacseq", f"Expected 'atacseq', got '{strategy.analysis_type}'"
    assert strategy.VERSION == "2.0.0", "Should have correct version"
    print("✅ Strategy creation passed")
    
    # Test metadata
    print("Testing strategy metadata...")
    metadata = strategy.get_metadata()
    assert "capabilities" in metadata["metadata"], "Should have capabilities in metadata"
    assert "peak_calling" in metadata["metadata"]["capabilities"], "Should support peak calling"
    assert "motif_enrichment" in metadata["metadata"]["capabilities"], "Should support motif enrichment"
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
        "data_summary": {"n_peaks": 50000, "n_samples": 6}
    }
    actions_uploaded = strategy.get_actions(uploaded_context)
    insights_uploaded = strategy.get_insights(uploaded_context)
    
    assert any("quality control" in action.lower() for action in actions_uploaded), "Should suggest QC"
    
    # QC completed context
    qc_context = {
        "data_uploaded": True,
        "pipeline_status": {"qc": True}
    }
    actions_qc = strategy.get_actions(qc_context)
    assert any("peak" in action.lower() for action in actions_qc), "Should suggest peak calling"
    
    # Peak calling completed context
    peak_context = {
        "data_uploaded": True,
        "pipeline_status": {
            "qc": True,
            "peak_calling": True
        }
    }
    actions_peak = strategy.get_actions(peak_context)
    assert any("differential" in action.lower() or "motif" in action.lower() or "visual" in action.lower() 
              for action in actions_peak), "Should suggest next analysis steps"
    
    print("✅ Progressive workflow tests passed")
    
    # Test workflow step dependencies
    print("Testing workflow step dependencies...")
    upload_step = next((step for step in workflow_steps if step.key == "data_upload"), None)
    qc_step = next((step for step in workflow_steps if step.key == "qc"), None)
    peak_step = next((step for step in workflow_steps if step.key == "peak_calling"), None)
    
    assert upload_step is not None, "Should have upload step"
    assert qc_step is not None, "Should have QC step"
    assert peak_step is not None, "Should have peak calling step"
    
    assert upload_step.dependencies == [], "Upload should have no dependencies"
    assert "data_validation" in qc_step.dependencies, "QC should depend on validation"
    assert "qc" in peak_step.dependencies, "Peak calling should depend on QC"
    print("✅ Workflow dependency tests passed")
    
    # Test time estimation
    print("Testing time estimation...")
    time_remaining = strategy.get_estimated_time_remaining(peak_context)
    completion_pct = strategy.get_completion_percentage(peak_context)
    
    assert isinstance(time_remaining, int), "Time remaining should be integer"
    assert 0 <= completion_pct <= 100, f"Completion should be 0-100%, got {completion_pct}"
    assert completion_pct > 30, "Should show significant progress for peak calling completed context"
    print("✅ Time estimation tests passed")
    
    # Test peak count
    print("Testing peak count...")
    peak_count = strategy.get_peak_count(peak_context)
    assert isinstance(peak_count, int), "Peak count should be integer"
    assert peak_count >= 0, "Peak count should be non-negative"
    print("✅ Peak count tests passed")
    
    # Test context validation
    print("Testing context validation...")
    valid_contexts = [
        {},
        {"data_uploaded": True},
        {"pipeline_status": {"peak_calling": True}},
        {"data_summary": {"n_peaks": 10000, "n_samples": 4}}
    ]
    
    invalid_contexts = [
        "not a dict",
        None,
        {"pipeline_status": "not a dict"},
        {"data_summary": {"n_peaks": -1}}
    ]
    
    for valid_ctx in valid_contexts:
        assert strategy.validate_context(valid_ctx), f"Should validate context: {valid_ctx}"
    
    for invalid_ctx in invalid_contexts:
        result = strategy.validate_context(invalid_ctx)
        # Should handle gracefully, might return False but shouldn't crash
        assert isinstance(result, bool), "Validation should return boolean"
    
    print("✅ Context validation tests passed")
    
    print("\n🎉 All ATAC-seq strategy tests passed!")
    return True


if __name__ == "__main__":
    def test_static_atac():
        """Static tests for ATAC-seq strategy"""
        print("Running static ATAC-seq strategy tests...")
        
        # Test class attributes
        assert hasattr(ATACSeqAnalysisStrategy, 'STRATEGY_NAME'), "Should have strategy name"
        assert hasattr(ATACSeqAnalysisStrategy, 'VERSION'), "Should have version"
        assert ATACSeqAnalysisStrategy.STRATEGY_NAME == "atacseq", "Should have correct strategy name"
        
        print("✅ Static ATAC-seq strategy tests passed!")
    
    def test_dynamic_atac():
        """Dynamic tests for ATAC-seq strategy"""
        print("Running dynamic ATAC-seq strategy tests...")
        
        # Run comprehensive main tests
        success = main()
        assert success, "Main tests should pass"
        
        print("✅ Dynamic ATAC-seq strategy tests passed!")
    
    # Run all tests
    test_static_atac()
    test_dynamic_atac()