"""
ATAC-seq Analysis Strategy

Strategy implementation for ATAC-seq (chromatin accessibility) analysis
with specific rules for ATAC-seq workflows.
"""

import streamlit as st
from typing import Dict, Any
from .base import WorkflowStage, WorkflowStep
from .rule_based import RuleBasedAnalysisStrategy


class ATACSeqAnalysisStrategy(RuleBasedAnalysisStrategy):
    """Strategy for ATAC-seq suggested actions and insights"""
    
    def __init__(self):
        super().__init__("atacseq")
    
    def _initialize_rules(self):
        """Initialize ATAC-seq specific rules"""
        
        # === ACTION RULES ===
        
        # Data upload rules
        self.add_action_rule(
            condition=lambda ctx: not ctx.get("data_uploaded", False),
            action="Upload ATAC-seq peak data or fragment files",
            priority=10,
            stage=WorkflowStage.DATA_UPLOAD
        )
        
        # QC rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("data_uploaded", False) and
                                 not self._has_qc_metrics()),
            action="Calculate QC metrics (TSS enrichment, nucleosome signal)",
            priority=9,
            stage=WorkflowStage.QUALITY_CONTROL
        )
        
        # Peak calling rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("data_uploaded", False) and
                                 not self._has_peaks()),
            action="Call accessible chromatin peaks",
            priority=8,
            stage=WorkflowStage.ANALYSIS
        )
        
        # Differential accessibility rules
        self.add_action_rule(
            condition=lambda ctx: (self._has_peaks() and
                                 not self._has_differential_peaks()),
            action="Perform differential accessibility analysis",
            priority=7,
            stage=WorkflowStage.ANALYSIS
        )
        
        # Motif enrichment rules
        self.add_action_rule(
            condition=lambda ctx: (self._has_differential_peaks() and
                                 not self._has_motif_enrichment()),
            action="Run motif enrichment analysis",
            priority=6,
            stage=WorkflowStage.INTERPRETATION
        )
        
        # === INSIGHT RULES ===
        
        # TSS enrichment insights
        self.add_insight_rule(
            condition=lambda ctx: self._has_tss_enrichment(),
            insight_generator=lambda ctx: self._generate_tss_insight(),
            priority=10,
            category="data_quality"
        )
        
        # Peak insights
        self.add_insight_rule(
            condition=lambda ctx: self._has_peaks(),
            insight_generator=lambda ctx: f"Identified {len(st.session_state.atacseq_peaks_df):,} accessible chromatin regions",
            priority=9,
            category="analysis_results"
        )
        
        # Differential accessibility insights
        self.add_insight_rule(
            condition=lambda ctx: self._has_differential_peaks(),
            insight_generator=lambda ctx: f"Found {len(st.session_state.differential_peaks):,} differentially accessible regions",
            priority=8,
            category="analysis_results"
        )
        
        # Motif enrichment insights
        self.add_insight_rule(
            condition=lambda ctx: self._has_motif_enrichment(),
            insight_generator=lambda ctx: self._generate_motif_insight(),
            priority=7,
            category="analysis_results"
        )
        
        # Define workflow steps
        self.workflow_steps = [
            WorkflowStep("data_upload", "Data Upload", "Upload ATAC-seq data", WorkflowStage.DATA_UPLOAD),
            WorkflowStep("qc", "Quality Control", "Calculate QC metrics", WorkflowStage.QUALITY_CONTROL, ["data_upload"]),
            WorkflowStep("peak_calling", "Peak Calling", "Call accessible peaks", WorkflowStage.ANALYSIS, ["qc"]),
            WorkflowStep("differential", "Differential Analysis", "Find differential peaks", WorkflowStage.ANALYSIS, ["peak_calling"]),
            WorkflowStep("motif_enrichment", "Motif Enrichment", "Analyze TF motifs", WorkflowStage.INTERPRETATION, ["differential"]),
            WorkflowStep("visualization", "Visualization", "Create plots", WorkflowStage.VISUALIZATION, ["peak_calling"])
        ]
    
    def _has_qc_metrics(self) -> bool:
        """Check if QC metrics are calculated"""
        try:
            return ("qc_metrics_calculated" in st.session_state and 
                   st.session_state.qc_metrics_calculated)
        except:
            return False
    
    def _has_peaks(self) -> bool:
        """Check if peaks are called"""
        try:
            return ("atacseq_peaks_df" in st.session_state and 
                   st.session_state.atacseq_peaks_df is not None)
        except:
            return False
    
    def _has_differential_peaks(self) -> bool:
        """Check if differential peaks are available"""
        try:
            return ("differential_peaks" in st.session_state and 
                   st.session_state.differential_peaks is not None)
        except:
            return False
    
    def _has_motif_enrichment(self) -> bool:
        """Check if motif enrichment results are available"""
        try:
            return ("motif_enrichment_results" in st.session_state and 
                   st.session_state.motif_enrichment_results is not None)
        except:
            return False
    
    def _has_tss_enrichment(self) -> bool:
        """Check if TSS enrichment scores are available"""
        try:
            return ("tss_enrichment_scores" in st.session_state and 
                   st.session_state.tss_enrichment_scores is not None)
        except:
            return False
    
    def _generate_tss_insight(self) -> str:
        """Generate TSS enrichment insight"""
        try:
            tss_score = st.session_state.tss_enrichment_scores
            if tss_score > 7:
                return f"Good data quality with TSS enrichment of {tss_score:.1f}"
            else:
                return f"Poor data quality - TSS enrichment only {tss_score:.1f} (should be >7)"
        except:
            return "TSS enrichment calculated"
    
    def _generate_motif_insight(self) -> str:
        """Generate motif enrichment insight"""
        try:
            motif_df = st.session_state.motif_enrichment_results
            if hasattr(motif_df, 'groupby') and 'tf_family' in motif_df.columns:
                top_family = motif_df.groupby('tf_family').size().idxmax()
                return f"Most enriched TF family: {top_family}"
            return "Motif enrichment analysis completed"
        except:
            return "Motif enrichment analysis completed"


# Test code for independent validation
if __name__ == "__main__":
    def test_atac_strategy():
        """Test ATACSeqAnalysisStrategy functionality"""
        print("Testing ATAC-seq analysis strategy...")
        
        # Create strategy
        strategy = ATACSeqAnalysisStrategy()
        print(f"✅ Created ATAC-seq strategy: {strategy.analysis_type}")
        
        # Test empty context
        empty_context = {}
        actions = strategy.get_actions(empty_context)
        insights = strategy.get_insights(empty_context)
        workflow_steps = strategy.get_workflow_steps()
        
        print(f"✅ Empty context - Actions: {len(actions)}")
        print(f"✅ Empty context - Insights: {insights}")
        print(f"✅ Workflow steps: {len(workflow_steps)}")
        
        assert len(actions) > 0, "Should have at least one action"
        assert any("Upload ATAC-seq" in action for action in actions), "Should suggest data upload"
        assert len(workflow_steps) == 6, "Should have 6 workflow steps"
        
        # Test with data uploaded context
        uploaded_context = {"data_uploaded": True}
        actions_uploaded = strategy.get_actions(uploaded_context)
        insights_uploaded = strategy.get_insights(uploaded_context)
        
        print(f"✅ Uploaded context - Actions: {actions_uploaded}")
        print(f"✅ Uploaded context - Insights: {insights_uploaded}")
        
        assert any("QC metrics" in action for action in actions_uploaded), "Should suggest QC"
        assert any("Call accessible" in action for action in actions_uploaded), "Should suggest peak calling"
        
        # Test workflow step dependencies
        upload_step = next((step for step in workflow_steps if step.key == "data_upload"), None)
        qc_step = next((step for step in workflow_steps if step.key == "qc"), None)
        peak_step = next((step for step in workflow_steps if step.key == "peak_calling"), None)
        diff_step = next((step for step in workflow_steps if step.key == "differential"), None)
        
        assert upload_step is not None, "Should have upload step"
        assert qc_step is not None, "Should have QC step"
        assert peak_step is not None, "Should have peak calling step"
        assert diff_step is not None, "Should have differential step"
        
        assert upload_step.dependencies is None, "Upload should have no dependencies"
        assert qc_step.dependencies == ["data_upload"], "QC should depend on upload"
        assert peak_step.dependencies == ["qc"], "Peak calling should depend on QC"
        assert diff_step.dependencies == ["peak_calling"], "Differential should depend on peak calling"
        
        # Test stage categorization
        assert upload_step.stage == WorkflowStage.DATA_UPLOAD, "Upload should be in DATA_UPLOAD stage"
        assert qc_step.stage == WorkflowStage.QUALITY_CONTROL, "QC should be in QUALITY_CONTROL stage"
        assert peak_step.stage == WorkflowStage.ANALYSIS, "Peak calling should be in ANALYSIS stage"
        assert diff_step.stage == WorkflowStage.ANALYSIS, "Differential should be in ANALYSIS stage"
        
        # Test helper methods with mock data
        class MockSessionState:
            def __init__(self):
                self.qc_metrics_calculated = False
                self.atacseq_peaks_df = None
                self.differential_peaks = None
                self.motif_enrichment_results = None
                self.tss_enrichment_scores = None
        
        # Test without session state (should not crash)
        original_st = st
        try:
            st.session_state = MockSessionState()
            
            assert not strategy._has_qc_metrics(), "Should return False for no QC metrics"
            assert not strategy._has_peaks(), "Should return False for no peaks"
            assert not strategy._has_differential_peaks(), "Should return False for no differential peaks"
            assert not strategy._has_motif_enrichment(), "Should return False for no motif enrichment"
            assert not strategy._has_tss_enrichment(), "Should return False for no TSS enrichment"
            
            # Test with mock data
            st.session_state.qc_metrics_calculated = True
            st.session_state.tss_enrichment_scores = 8.5
            
            assert strategy._has_qc_metrics(), "Should return True for QC metrics"
            assert strategy._has_tss_enrichment(), "Should return True for TSS enrichment"
            
            tss_insight = strategy._generate_tss_insight()
            assert "Good data quality" in tss_insight, "Should indicate good quality"
            assert "8.5" in tss_insight, "Should include TSS score"
            
            # Test poor quality TSS
            st.session_state.tss_enrichment_scores = 5.0
            tss_insight_poor = strategy._generate_tss_insight()
            assert "Poor data quality" in tss_insight_poor, "Should indicate poor quality"
            
            # Test with peaks data
            import pandas as pd
            st.session_state.atacseq_peaks_df = pd.DataFrame({'chr': ['chr1', 'chr2'], 'start': [100, 200], 'end': [300, 400]})
            st.session_state.differential_peaks = pd.DataFrame({'chr': ['chr1'], 'start': [100], 'end': [300]})
            
            assert strategy._has_peaks(), "Should return True for peaks data"
            assert strategy._has_differential_peaks(), "Should return True for differential peaks"
            
            # Test motif enrichment
            st.session_state.motif_enrichment_results = pd.DataFrame({'tf_family': ['bHLH', 'bHLH', 'ETS'], 'pvalue': [0.01, 0.02, 0.03]})
            
            assert strategy._has_motif_enrichment(), "Should return True for motif enrichment"
            motif_insight = strategy._generate_motif_insight()
            assert "bHLH" in motif_insight, "Should identify most enriched TF family"
            
        except ImportError:
            # Skip pandas tests if not available
            print("⚠️  Skipping pandas-dependent tests")
        finally:
            st = original_st
        
        print("🎉 All ATAC-seq strategy tests passed!")
    
    # Run test
    test_atac_strategy() 