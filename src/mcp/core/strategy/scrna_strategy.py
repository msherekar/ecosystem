"""
scRNA-seq Analysis Strategy

Strategy implementation for single-cell RNA sequencing analysis
with specific rules for scRNA-seq workflows.
"""

import streamlit as st
from typing import Dict, Any
from .base import WorkflowStage, WorkflowStep
from .rule_based import RuleBasedAnalysisStrategy


class scRNASeqAnalysisStrategy(RuleBasedAnalysisStrategy):
    """Strategy for scRNA-seq suggested actions and insights"""
    
    def __init__(self):
        super().__init__("scrnaseq")
    
    def _initialize_rules(self):
        """Initialize scRNA-seq specific rules"""
        
        # === ACTION RULES ===
        
        # Data upload rules
        self.add_action_rule(
            condition=lambda ctx: not ctx.get("data_uploaded", False),
            action="Upload scRNA-seq data (.h5ad or 10x format)",
            priority=10,
            stage=WorkflowStage.DATA_UPLOAD
        )
        
        # QC rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("data_uploaded", False) and 
                                 not ctx.get("pipeline_status", {}).get("qc", False)),
            action="Perform quality control analysis",
            priority=9,
            stage=WorkflowStage.QUALITY_CONTROL
        )
        
        # Filtering rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("pipeline_status", {}).get("qc", False) and
                                 not ctx.get("pipeline_status", {}).get("filtering", False)),
            action="Filter low-quality cells and genes",
            priority=8,
            stage=WorkflowStage.PREPROCESSING
        )
        
        # Normalization rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("pipeline_status", {}).get("filtering", False) and
                                 not ctx.get("pipeline_status", {}).get("normalization", False)),
            action="Normalize and scale expression data",
            priority=7,
            stage=WorkflowStage.PREPROCESSING
        )
        
        # Dimensionality reduction rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("pipeline_status", {}).get("normalization", False) and
                                 not ctx.get("pipeline_status", {}).get("dimred", False)),
            action="Perform dimensionality reduction (PCA/UMAP)",
            priority=6,
            stage=WorkflowStage.ANALYSIS
        )
        
        # Clustering rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("pipeline_status", {}).get("dimred", False) and
                                 not ctx.get("pipeline_status", {}).get("clustering", False)),
            action="Cluster cells to identify populations",
            priority=5,
            stage=WorkflowStage.ANALYSIS
        )
        
        # Differential expression rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("pipeline_status", {}).get("clustering", False) and
                                 not ctx.get("pipeline_status", {}).get("dea", False)),
            action="Find marker genes for each cluster",
            priority=4,
            stage=WorkflowStage.ANALYSIS
        )
        
        # Visualization rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("pipeline_status", {}).get("clustering", False) and
                                 not ctx.get("pipeline_status", {}).get("viz", False)),
            action="Create visualizations (UMAP, heatmaps)",
            priority=4,
            stage=WorkflowStage.VISUALIZATION
        )
        
        # Enrichment rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("pipeline_status", {}).get("dea", False) and
                                 not ctx.get("pipeline_status", {}).get("enrichment", False)),
            action="Perform pathway enrichment analysis",
            priority=3,
            stage=WorkflowStage.INTERPRETATION
        )
        
        # === INSIGHT RULES ===
        
        # Dataset overview insights
        self.add_insight_rule(
            condition=lambda ctx: ctx.get("data_uploaded", False) and "data_summary" in ctx,
            insight_generator=lambda ctx: f"Dataset: {ctx['data_summary'].get('n_cells', 0):,} cells × {ctx['data_summary'].get('n_genes', 0):,} genes",
            priority=10,
            category="data_overview"
        )
        
        # QC insights
        self.add_insight_rule(
            condition=lambda ctx: self._has_mitochondrial_data(),
            insight_generator=lambda ctx: f"Median mitochondrial content: {st.session_state.anndata.obs['pct_counts_mt'].median():.1f}%",
            priority=9,
            category="data_quality"
        )
        
        # Clustering insights
        self.add_insight_rule(
            condition=lambda ctx: self._has_clustering_data(),
            insight_generator=lambda ctx: f"Identified {len(st.session_state.anndata.obs['leiden'].unique())} cell clusters",
            priority=8,
            category="analysis_results"
        )
        
        # Progress insights
        self.add_insight_rule(
            condition=lambda ctx: ctx.get("pipeline_status", {}),
            insight_generator=lambda ctx: self._generate_progress_insight(ctx),
            priority=7,
            category="analysis_progress"
        )
        
        # Define workflow steps
        self.workflow_steps = [
            WorkflowStep("data_upload", "Data Upload", "Upload scRNA-seq data", WorkflowStage.DATA_UPLOAD),
            WorkflowStep("qc", "Quality Control", "Assess data quality", WorkflowStage.QUALITY_CONTROL, ["data_upload"]),
            WorkflowStep("filtering", "Filtering", "Filter cells and genes", WorkflowStage.PREPROCESSING, ["qc"]),
            WorkflowStep("normalization", "Normalization", "Normalize expression", WorkflowStage.PREPROCESSING, ["filtering"]),
            WorkflowStep("dimred", "Dimensionality Reduction", "PCA and UMAP", WorkflowStage.ANALYSIS, ["normalization"]),
            WorkflowStep("clustering", "Clustering", "Identify cell populations", WorkflowStage.ANALYSIS, ["dimred"]),
            WorkflowStep("dea", "Differential Expression", "Find marker genes", WorkflowStage.ANALYSIS, ["clustering"]),
            WorkflowStep("viz", "Visualization", "Create plots", WorkflowStage.VISUALIZATION, ["clustering"]),
            WorkflowStep("enrichment", "Enrichment", "Pathway analysis", WorkflowStage.INTERPRETATION, ["dea"])
        ]
    
    def _has_mitochondrial_data(self) -> bool:
        """Check if mitochondrial data is available"""
        try:
            return ("anndata" in st.session_state and 
                   hasattr(st.session_state.anndata, 'obs') and 
                   "pct_counts_mt" in st.session_state.anndata.obs)
        except:
            return False
    
    def _has_clustering_data(self) -> bool:
        """Check if clustering data is available"""
        try:
            return ("anndata" in st.session_state and 
                   hasattr(st.session_state.anndata, 'obs') and 
                   "leiden" in st.session_state.anndata.obs)
        except:
            return False
    
    def _generate_progress_insight(self, context: Dict[str, Any]) -> str:
        """Generate progress insight based on completed steps"""
        pipeline_status = context.get("pipeline_status", {})
        completed_steps = [step for step, done in pipeline_status.items() if done]
        
        if not completed_steps:
            return "Analysis not started"
        elif len(completed_steps) < 3:
            return f"Early stage: {len(completed_steps)} steps completed"
        elif len(completed_steps) < 6:
            return f"Mid-stage analysis: {len(completed_steps)} steps completed"
        else:
            return f"Advanced analysis: {len(completed_steps)} steps completed"


# Test code for independent validation
if __name__ == "__main__":
    def test_scrna_strategy():
        """Test scRNASeqAnalysisStrategy functionality"""
        print("Testing scRNA-seq analysis strategy...")
        
        # Create strategy
        strategy = scRNASeqAnalysisStrategy()
        print(f"✅ Created scRNA-seq strategy: {strategy.analysis_type}")
        
        # Test empty context
        empty_context = {}
        actions = strategy.get_actions(empty_context)
        insights = strategy.get_insights(empty_context)
        workflow_steps = strategy.get_workflow_steps()
        
        print(f"✅ Empty context - Actions: {len(actions)}")
        print(f"✅ Empty context - Insights: {insights}")
        print(f"✅ Workflow steps: {len(workflow_steps)}")
        
        assert len(actions) > 0, "Should have at least one action"
        assert any("Upload scRNA-seq data" in action for action in actions), "Should suggest data upload"
        assert len(workflow_steps) == 9, "Should have 9 workflow steps"
        
        # Test with data uploaded context
        uploaded_context = {
            "data_uploaded": True,
            "data_summary": {"n_cells": 5000, "n_genes": 20000}
        }
        actions_uploaded = strategy.get_actions(uploaded_context)
        insights_uploaded = strategy.get_insights(uploaded_context)
        
        print(f"✅ Uploaded context - Actions: {actions_uploaded}")
        print(f"✅ Uploaded context - Insights: {insights_uploaded}")
        
        assert any("quality control" in action.lower() for action in actions_uploaded), "Should suggest QC"
        assert "5,000 cells × 20,000 genes" in insights_uploaded, "Should have dataset summary"
        
        # Test with progressive pipeline status
        pipeline_context = {
            "data_uploaded": True,
            "pipeline_status": {
                "qc": True,
                "filtering": True,
                "normalization": False
            }
        }
        actions_pipeline = strategy.get_actions(pipeline_context)
        insights_pipeline = strategy.get_insights(pipeline_context)
        
        print(f"✅ Pipeline context - Actions: {actions_pipeline}")
        print(f"✅ Pipeline context - Insights: {insights_pipeline}")
        
        assert any("normalize" in action.lower() for action in actions_pipeline), "Should suggest normalization"
        assert "2 steps completed" in insights_pipeline, "Should show progress"
        
        # Test workflow step dependencies
        upload_step = next((step for step in workflow_steps if step.key == "data_upload"), None)
        qc_step = next((step for step in workflow_steps if step.key == "qc"), None)
        
        assert upload_step is not None, "Should have upload step"
        assert qc_step is not None, "Should have QC step"
        assert upload_step.dependencies is None, "Upload should have no dependencies"
        assert qc_step.dependencies == ["data_upload"], "QC should depend on upload"
        
        # Test stage categorization
        upload_stage = upload_step.stage
        qc_stage = qc_step.stage
        
        assert upload_stage == WorkflowStage.DATA_UPLOAD, "Upload should be in DATA_UPLOAD stage"
        assert qc_stage == WorkflowStage.QUALITY_CONTROL, "QC should be in QUALITY_CONTROL stage"
        
        print("🎉 All scRNA-seq strategy tests passed!")
    
    # Run test
    test_scrna_strategy() 