"""
RNA-seq Analysis Strategy

Strategy implementation for bulk RNA sequencing analysis
with specific rules for RNA-seq workflows.
"""

import streamlit as st
from typing import Dict, Any
from .base import WorkflowStage, WorkflowStep
from .rule_based import RuleBasedAnalysisStrategy


class RNASeqAnalysisStrategy(RuleBasedAnalysisStrategy):
    """Strategy for RNA-seq suggested actions and insights"""
    
    def __init__(self):
        super().__init__("rnaseq")
    
    def _initialize_rules(self):
        """Initialize RNA-seq specific rules"""
        
        # === ACTION RULES ===
        
        # Data upload rules
        self.add_action_rule(
            condition=lambda ctx: not ctx.get("data_uploaded", False),
            action="Upload RNA-seq counts and metadata files",
            priority=10,
            stage=WorkflowStage.DATA_UPLOAD
        )
        
        # DESeq2 rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("data_uploaded", False) and
                                 not ctx.get("pipeline_status", {}).get("deseq2_completed", False)),
            action="Run differential expression analysis (DESeq2)",
            priority=9,
            stage=WorkflowStage.ANALYSIS
        )
        
        # GO enrichment rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("pipeline_status", {}).get("deseq2_completed", False) and
                                 not ctx.get("pipeline_status", {}).get("go_enrichment_completed", False)),
            action="Perform Gene Ontology enrichment analysis",
            priority=8,
            stage=WorkflowStage.INTERPRETATION
        )
        
        # Visualization rules
        self.add_action_rule(
            condition=lambda ctx: ctx.get("pipeline_status", {}).get("deseq2_completed", False),
            action="Create visualizations (PCA, volcano plot, heatmap)",
            priority=7,
            stage=WorkflowStage.VISUALIZATION
        )
        
        # === INSIGHT RULES ===
        
        # Dataset insights
        self.add_insight_rule(
            condition=lambda ctx: self._has_count_data(),
            insight_generator=lambda ctx: f"RNA-seq dataset: {st.session_state.rnaseq_counts_df.shape[1]} samples × {st.session_state.rnaseq_counts_df.shape[0]} genes",
            priority=10,
            category="data_overview"
        )
        
        # DESeq2 results insights
        self.add_insight_rule(
            condition=lambda ctx: self._has_deseq_data(),
            insight_generator=lambda ctx: self._generate_deseq_insight(),
            priority=9,
            category="analysis_results"
        )
        
        # GO enrichment insights
        self.add_insight_rule(
            condition=lambda ctx: self._has_go_data(),
            insight_generator=lambda ctx: f"GO enrichment: {len(st.session_state.go_results)} significant pathways",
            priority=8,
            category="analysis_results"
        )
        
        # Define workflow steps
        self.workflow_steps = [
            WorkflowStep("data_upload", "Data Upload", "Upload counts and metadata", WorkflowStage.DATA_UPLOAD),
            WorkflowStep("deseq2", "Differential Expression", "DESeq2 analysis", WorkflowStage.ANALYSIS, ["data_upload"]),
            WorkflowStep("go_enrichment", "GO Enrichment", "Pathway analysis", WorkflowStage.INTERPRETATION, ["deseq2"]),
            WorkflowStep("visualization", "Visualization", "Create plots", WorkflowStage.VISUALIZATION, ["deseq2"])
        ]
    
    def _has_count_data(self) -> bool:
        """Check if RNA-seq count data is available"""
        try:
            return ("rnaseq_counts_df" in st.session_state and 
                   st.session_state.rnaseq_counts_df is not None)
        except:
            return False
    
    def _has_deseq_data(self) -> bool:
        """Check if DESeq2 results are available"""
        try:
            return ("deseq_results" in st.session_state and 
                   st.session_state.deseq_results is not None)
        except:
            return False
    
    def _has_go_data(self) -> bool:
        """Check if GO enrichment results are available"""
        try:
            return ("go_results" in st.session_state and 
                   st.session_state.go_results is not None)
        except:
            return False
    
    def _generate_deseq_insight(self) -> str:
        """Generate DESeq2 results insight"""
        try:
            deseq_results = st.session_state.deseq_results
            if hasattr(deseq_results, 'shape'):
                significant = deseq_results[deseq_results['padj'] < 0.05] if 'padj' in deseq_results.columns else deseq_results
                return f"DESeq2: {len(significant)} significant genes (padj < 0.05)"
            return "DESeq2 analysis completed"
        except:
            return "DESeq2 analysis completed"


# Test code for independent validation
if __name__ == "__main__":
    def test_rna_strategy():
        """Test RNASeqAnalysisStrategy functionality"""
        print("Testing RNA-seq analysis strategy...")
        
        # Create strategy
        strategy = RNASeqAnalysisStrategy()
        print(f"✅ Created RNA-seq strategy: {strategy.analysis_type}")
        
        # Test empty context
        empty_context = {}
        actions = strategy.get_actions(empty_context)
        insights = strategy.get_insights(empty_context)
        workflow_steps = strategy.get_workflow_steps()
        
        print(f"✅ Empty context - Actions: {len(actions)}")
        print(f"✅ Empty context - Insights: {insights}")
        print(f"✅ Workflow steps: {len(workflow_steps)}")
        
        assert len(actions) > 0, "Should have at least one action"
        assert any("Upload RNA-seq counts" in action for action in actions), "Should suggest data upload"
        assert len(workflow_steps) == 4, "Should have 4 workflow steps"
        
        # Test with data uploaded context
        uploaded_context = {"data_uploaded": True}
        actions_uploaded = strategy.get_actions(uploaded_context)
        insights_uploaded = strategy.get_insights(uploaded_context)
        
        print(f"✅ Uploaded context - Actions: {actions_uploaded}")
        print(f"✅ Uploaded context - Insights: {insights_uploaded}")
        
        assert any("DESeq2" in action for action in actions_uploaded), "Should suggest DESeq2"
        
        # Test with DESeq2 completed context
        deseq_context = {
            "data_uploaded": True,
            "pipeline_status": {"deseq2_completed": True}
        }
        actions_deseq = strategy.get_actions(deseq_context)
        
        print(f"✅ DESeq2 context - Actions: {actions_deseq}")
        
        assert any("Gene Ontology" in action for action in actions_deseq), "Should suggest GO enrichment"
        assert any("visualization" in action.lower() for action in actions_deseq), "Should suggest visualizations"
        
        # Test workflow step dependencies
        upload_step = next((step for step in workflow_steps if step.key == "data_upload"), None)
        deseq_step = next((step for step in workflow_steps if step.key == "deseq2"), None)
        go_step = next((step for step in workflow_steps if step.key == "go_enrichment"), None)
        
        assert upload_step is not None, "Should have upload step"
        assert deseq_step is not None, "Should have DESeq2 step"
        assert go_step is not None, "Should have GO enrichment step"
        
        assert upload_step.dependencies is None, "Upload should have no dependencies"
        assert deseq_step.dependencies == ["data_upload"], "DESeq2 should depend on upload"
        assert go_step.dependencies == ["deseq2"], "GO should depend on DESeq2"
        
        # Test stage categorization
        assert upload_step.stage == WorkflowStage.DATA_UPLOAD, "Upload should be in DATA_UPLOAD stage"
        assert deseq_step.stage == WorkflowStage.ANALYSIS, "DESeq2 should be in ANALYSIS stage"
        assert go_step.stage == WorkflowStage.INTERPRETATION, "GO should be in INTERPRETATION stage"
        
        # Test helper methods with mock data
        class MockSessionState:
            def __init__(self):
                self.rnaseq_counts_df = None
                self.deseq_results = None
                self.go_results = None
        
        # Test without session state (should not crash)
        original_st = st
        try:
            st.session_state = MockSessionState()
            
            assert not strategy._has_count_data(), "Should return False for no count data"
            assert not strategy._has_deseq_data(), "Should return False for no DESeq2 data"
            assert not strategy._has_go_data(), "Should return False for no GO data"
            
            # Test with mock data
            import pandas as pd
            st.session_state.rnaseq_counts_df = pd.DataFrame({'sample1': [1, 2], 'sample2': [3, 4]})
            st.session_state.deseq_results = pd.DataFrame({'padj': [0.01, 0.1]})
            st.session_state.go_results = [{'term': 'GO:123', 'pvalue': 0.01}]
            
            assert strategy._has_count_data(), "Should return True for count data"
            assert strategy._has_deseq_data(), "Should return True for DESeq2 data"
            assert strategy._has_go_data(), "Should return True for GO data"
            
            deseq_insight = strategy._generate_deseq_insight()
            assert "1 significant genes" in deseq_insight, "Should report significant genes"
            
        except ImportError:
            # Skip pandas tests if not available
            print("⚠️  Skipping pandas-dependent tests")
        finally:
            st = original_st
        
        print("🎉 All RNA-seq strategy tests passed!")
    
    # Run test
    test_rna_strategy() 