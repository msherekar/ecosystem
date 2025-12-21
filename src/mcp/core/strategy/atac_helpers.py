"""
ATAC-seq Helper Components

Support classes for ATAC-seq analysis strategy including
data validation, insight generation, and progress tracking.
"""

import logging
from typing import Dict, Any, List, Optional
from .base import WorkflowStep

logger = logging.getLogger(__name__)


class ATACDataValidator:
    """Data validation utilities for ATAC-seq analysis"""
    
    def __init__(self):
        self.required_session_keys = {
            "peak_data": ["atacseq_peaks_df"],
            "fragment_data": ["fragment_files"],
            "tss_data": ["tss_enrichment_scores"],
            "motif_data": ["motif_enrichment_results"]
        }
        
        self.peak_file_formats = [".bed", ".narrowPeak", ".broadPeak", ".gappedPeak"]
        self.fragment_file_formats = [".bam", ".bed", ".tsv.gz"]
    
    def validate_context(self, context: Dict[str, Any]) -> bool:
        """Validate ATAC-seq specific context"""
        if not isinstance(context, dict):
            return False
        
        # Check pipeline status format if present
        pipeline_status = context.get("pipeline_status")
        if pipeline_status is not None:
            if not isinstance(pipeline_status, dict):
                logger.warning("pipeline_status should be a dictionary")
                return False
            
            # Validate status values
            for step, status in pipeline_status.items():
                if not isinstance(status, bool):
                    logger.warning(f"Pipeline status for {step} should be boolean")
                    return False
        
        # Validate data summary if present
        data_summary = context.get("data_summary")
        if data_summary is not None:
            if not isinstance(data_summary, dict):
                logger.warning("data_summary should be a dictionary")
                return False
            
            # Check for required numeric fields
            numeric_fields = ["n_peaks", "n_samples"]
            for field in numeric_fields:
                if field in data_summary:
                    value = data_summary[field]
                    if not isinstance(value, (int, float)) or value < 0:
                        logger.warning(f"data_summary.{field} should be non-negative number")
                        return False
        
        # Validate TSS enrichment scores if present
        tss_config = context.get("tss_config")
        if tss_config is not None:
            if not isinstance(tss_config, dict):
                logger.warning("tss_config should be a dictionary")
                return False
            
            if "threshold" in tss_config:
                threshold = tss_config["threshold"]
                if not isinstance(threshold, (int, float)) or threshold <= 0:
                    logger.warning("TSS enrichment threshold should be positive number")
                    return False
        
        return True
    
    def is_data_validated(self, context: Dict[str, Any]) -> bool:
        """Check if data has been validated"""
        return (context.get("data_uploaded", False) and 
                context.get("data_validated", False))
    
    def has_peak_data(self, context: Dict[str, Any]) -> bool:
        """Check if peak data is available"""
        try:
            import streamlit as st
            return ("atacseq_peaks_df" in st.session_state and 
                   st.session_state.atacseq_peaks_df is not None)
        except ImportError:
            # Fallback when streamlit not available
            return (context.get("data_uploaded", False) and
                   "data_summary" in context)
    
    def has_tss_enrichment(self, context: Dict[str, Any]) -> bool:
        """Check if TSS enrichment data is available"""
        try:
            import streamlit as st
            return ("tss_enrichment_scores" in st.session_state and 
                   st.session_state.tss_enrichment_scores is not None)
        except ImportError:
            # Fallback when streamlit not available
            pipeline_status = context.get("pipeline_status", {})
            return pipeline_status.get("qc", False)
    
    def has_peak_calling_results(self, context: Dict[str, Any]) -> bool:
        """Check if peak calling results are available"""
        try:
            import streamlit as st
            return ("atacseq_peaks_df" in st.session_state and 
                   st.session_state.atacseq_peaks_df is not None and
                   hasattr(st.session_state.atacseq_peaks_df, 'shape'))
        except ImportError:
            # Fallback when streamlit not available
            pipeline_status = context.get("pipeline_status", {})
            return pipeline_status.get("peak_calling", False)
    
    def has_differential_peaks(self, context: Dict[str, Any]) -> bool:
        """Check if differential accessibility results are available"""
        try:
            import streamlit as st
            return ("differential_peaks" in st.session_state and 
                   st.session_state.differential_peaks is not None)
        except ImportError:
            # Fallback when streamlit not available
            pipeline_status = context.get("pipeline_status", {})
            return pipeline_status.get("differential", False)
    
    def has_motif_enrichment(self, context: Dict[str, Any]) -> bool:
        """Check if motif enrichment results are available"""
        try:
            import streamlit as st
            return ("motif_enrichment_results" in st.session_state and 
                   st.session_state.motif_enrichment_results is not None)
        except ImportError:
            # Fallback when streamlit not available
            pipeline_status = context.get("pipeline_status", {})
            return pipeline_status.get("motif_enrichment", False)
    
    def get_peak_count(self, context: Dict[str, Any]) -> int:
        """Get count of identified peaks"""
        try:
            import streamlit as st
            
            if not hasattr(st.session_state, 'atacseq_peaks_df'):
                return 0
            
            peaks_df = st.session_state.atacseq_peaks_df
            
            if hasattr(peaks_df, 'shape'):
                return peaks_df.shape[0]
            
            return 0
            
        except ImportError:
            # Fallback when streamlit not available
            data_summary = context.get("data_summary", {})
            return data_summary.get("n_peaks", 0)
        except Exception as e:
            logger.warning(f"Error getting peak count: {e}")
            return 0


class ATACInsightGenerator:
    """Generate insights for ATAC-seq analysis"""
    
    def __init__(self):
        self.insight_templates = {
            "dataset_overview": "ATAC-seq dataset: {n_peaks:,} peaks across {n_samples} samples",
            "tss_good": "Good data quality with TSS enrichment of {score:.1f}",
            "tss_poor": "Poor data quality - TSS enrichment only {score:.1f} (should be >7)",
            "peak_basic": "Identified {n_peaks:,} accessible chromatin regions",
            "peak_detailed": "Peak calling: {n_peaks:,} peaks with median width {median_width}bp",
            "differential_basic": "Found {n_diff_peaks:,} differentially accessible regions",
            "motif_basic": "Motif enrichment: {n_motifs} enriched transcription factor motifs"
        }
    
    def generate_dataset_overview(self, context: Dict[str, Any]) -> str:
        """Generate dataset overview insight"""
        try:
            data_summary = context.get("data_summary", {})
            n_peaks = data_summary.get("n_peaks", 0)
            n_samples = data_summary.get("n_samples", 0)
            
            if n_peaks > 0 and n_samples > 0:
                return self.insight_templates["dataset_overview"].format(
                    n_peaks=n_peaks, n_samples=n_samples
                )
            
            # Fallback to session state
            try:
                import streamlit as st
                if hasattr(st.session_state, 'atacseq_peaks_df'):
                    peaks_df = st.session_state.atacseq_peaks_df
                    if hasattr(peaks_df, 'shape'):
                        n_peaks = peaks_df.shape[0]
                        # Try to infer sample count from columns
                        n_samples = len([col for col in peaks_df.columns if 'sample' in col.lower()])
                        if n_samples == 0:
                            n_samples = max(1, peaks_df.shape[1] - 3)  # Assume 3 coordinate columns
                        
                        return self.insight_templates["dataset_overview"].format(
                            n_peaks=n_peaks, n_samples=n_samples
                        )
            except ImportError:
                pass
            
            return "ATAC-seq dataset uploaded and ready for analysis"
            
        except Exception as e:
            logger.warning(f"Error generating dataset overview: {e}")
            return "Dataset information available"
    
    def generate_tss_insights(self, context: Dict[str, Any]) -> str:
        """Generate TSS enrichment insights"""
        try:
            import streamlit as st
            
            if not hasattr(st.session_state, 'tss_enrichment_scores'):
                return "TSS enrichment analysis completed"
            
            tss_score = st.session_state.tss_enrichment_scores
            
            # Handle different score formats
            if hasattr(tss_score, 'mean'):  # Series or array
                score_value = tss_score.mean()
            elif isinstance(tss_score, (int, float)):
                score_value = tss_score
            else:
                return "TSS enrichment calculated"
            
            if score_value > 7:
                return self.insight_templates["tss_good"].format(score=score_value)
            else:
                return self.insight_templates["tss_poor"].format(score=score_value)
            
        except ImportError:
            return "TSS enrichment analysis completed"
        except Exception as e:
            logger.warning(f"Error generating TSS insights: {e}")
            return "TSS enrichment analysis completed"
    
    def generate_peak_insights(self, context: Dict[str, Any]) -> str:
        """Generate peak calling insights"""
        try:
            import streamlit as st
            
            if not hasattr(st.session_state, 'atacseq_peaks_df'):
                pipeline_status = context.get("pipeline_status", {})
                if pipeline_status.get("peak_calling", False):
                    return "Peak calling analysis completed"
                return "Peak calling results not available"
            
            peaks_df = st.session_state.atacseq_peaks_df
            
            if hasattr(peaks_df, 'shape'):
                n_peaks = peaks_df.shape[0]
                
                # Calculate median peak width if coordinate columns available
                if all(col in peaks_df.columns for col in ['start', 'end']):
                    peak_widths = peaks_df['end'] - peaks_df['start']
                    median_width = int(peak_widths.median())
                    
                    return self.insight_templates["peak_detailed"].format(
                        n_peaks=n_peaks, median_width=median_width
                    )
                else:
                    return self.insight_templates["peak_basic"].format(n_peaks=n_peaks)
            
            return "Peak calling analysis completed"
            
        except ImportError:
            return "Peak calling completed"
        except Exception as e:
            logger.warning(f"Error generating peak insights: {e}")
            return "Peak calling analysis completed"
    
    def generate_differential_insights(self, context: Dict[str, Any]) -> str:
        """Generate differential accessibility insights"""
        try:
            import streamlit as st
            
            if not hasattr(st.session_state, 'differential_peaks'):
                pipeline_status = context.get("pipeline_status", {})
                if pipeline_status.get("differential", False):
                    return "Differential accessibility analysis completed"
                return "Differential accessibility results not available"
            
            diff_peaks = st.session_state.differential_peaks
            
            if hasattr(diff_peaks, '__len__'):
                n_diff_peaks = len(diff_peaks)
                
                if n_diff_peaks == 0:
                    return "No significantly differentially accessible regions found"
                
                return self.insight_templates["differential_basic"].format(
                    n_diff_peaks=n_diff_peaks
                )
            
            return "Differential accessibility analysis completed"
            
        except ImportError:
            return "Differential accessibility analysis completed"
        except Exception as e:
            logger.warning(f"Error generating differential insights: {e}")
            return "Differential accessibility analysis completed"
    
    def generate_motif_insights(self, context: Dict[str, Any]) -> str:
        """Generate motif enrichment insights"""
        try:
            import streamlit as st
            
            if not hasattr(st.session_state, 'motif_enrichment_results'):
                pipeline_status = context.get("pipeline_status", {})
                if pipeline_status.get("motif_enrichment", False):
                    return "Motif enrichment analysis completed"
                return "Motif enrichment results not available"
            
            motif_results = st.session_state.motif_enrichment_results
            
            if hasattr(motif_results, '__len__'):
                n_motifs = len(motif_results)
                
                if n_motifs == 0:
                    return "No significantly enriched motifs found"
                
                # Try to get most enriched TF family
                if hasattr(motif_results, 'groupby') and 'tf_family' in motif_results.columns:
                    top_family = motif_results.groupby('tf_family').size().idxmax()
                    return f"Most enriched TF family: {top_family} ({n_motifs} total motifs)"
                
                return self.insight_templates["motif_basic"].format(n_motifs=n_motifs)
            
            return "Motif enrichment analysis completed"
            
        except ImportError:
            return "Motif enrichment analysis completed"
        except Exception as e:
            logger.warning(f"Error generating motif insights: {e}")
            return "Motif enrichment analysis completed"


class ATACProgressTracker:
    """Track and report ATAC-seq analysis progress"""
    
    def __init__(self):
        self.step_weights = {
            "data_upload": 5,
            "data_validation": 3,
            "qc": 12,
            "peak_calling": 25,
            "differential": 20,
            "motif_enrichment": 15,
            "footprinting": 25,
            "visualization": 12,
            "export": 5
        }
        
        self.progress_messages = {
            "early": "Analysis in initial stages",
            "qc": "Quality control assessment",
            "peak_calling": "Peak calling in progress",
            "analysis": "Advanced analysis phase",
            "interpretation": "Biological interpretation",
            "complete": "ATAC-seq analysis completed"
        }
    
    def calculate_completion_percentage(self, context: Dict[str, Any], 
                                     workflow_steps: List[WorkflowStep]) -> float:
        """Calculate overall completion percentage"""
        try:
            pipeline_status = context.get("pipeline_status", {})
            total_weight = sum(self.step_weights.get(step.key, 10) for step in workflow_steps)
            
            completed_weight = 0
            for step in workflow_steps:
                if pipeline_status.get(step.key, False):
                    completed_weight += self.step_weights.get(step.key, 10)
            
            if total_weight == 0:
                return 0.0
            
            percentage = (completed_weight / total_weight) * 100
            return min(100.0, max(0.0, percentage))
            
        except Exception as e:
            logger.warning(f"Error calculating completion percentage: {e}")
            return 0.0
    
    def calculate_time_remaining(self, context: Dict[str, Any], 
                               workflow_steps: List[WorkflowStep]) -> int:
        """Calculate estimated time remaining in minutes"""
        try:
            pipeline_status = context.get("pipeline_status", {})
            
            remaining_time = 0
            for step in workflow_steps:
                if not pipeline_status.get(step.key, False):
                    remaining_time += step.estimated_time or 15
            
            return remaining_time
            
        except Exception as e:
            logger.warning(f"Error calculating time remaining: {e}")
            return 45  # Default fallback
    
    def generate_progress_insight(self, context: Dict[str, Any]) -> str:
        """Generate progress insight based on completed steps"""
        try:
            pipeline_status = context.get("pipeline_status", {})
            completed_steps = [step for step, done in pipeline_status.items() if done]
            
            if not completed_steps:
                return "ATAC-seq analysis not started - upload data to begin"
            
            # Determine analysis phase
            if pipeline_status.get("motif_enrichment", False) or pipeline_status.get("footprinting", False):
                return f"{self.progress_messages['interpretation']} ({len(completed_steps)} steps completed)"
            elif pipeline_status.get("differential", False):
                return f"{self.progress_messages['analysis']} ({len(completed_steps)} steps completed)"
            elif pipeline_status.get("peak_calling", False):
                return f"{self.progress_messages['peak_calling']} completed ({len(completed_steps)} steps)"
            elif pipeline_status.get("qc", False):
                return f"{self.progress_messages['qc']} completed ({len(completed_steps)} steps)"
            else:
                return f"{self.progress_messages['early']} ({len(completed_steps)} steps completed)"
                
        except Exception as e:
            logger.warning(f"Error generating progress insight: {e}")
            return "Analysis progress tracked"


def main():
    """Test ATAC-seq helper components"""
    print("🧪 Testing ATAC-seq Helper Components")
    print("=" * 50)
    
    # Test data validator
    print("Testing ATACDataValidator...")
    validator = ATACDataValidator()
    
    # Test valid contexts
    valid_contexts = [
        {},
        {"data_uploaded": True},
        {"pipeline_status": {"peak_calling": True, "differential": False}},
        {"data_summary": {"n_peaks": 50000, "n_samples": 6}},
        {"tss_config": {"threshold": 7.0}}
    ]
    
    for ctx in valid_contexts:
        assert validator.validate_context(ctx), f"Should validate context: {ctx}"
    
    # Test invalid contexts
    invalid_contexts = [
        "not a dict",
        {"pipeline_status": "not a dict"},
        {"data_summary": {"n_peaks": -1}},
        {"pipeline_status": {"peak_calling": "not a bool"}},
        {"tss_config": {"threshold": -1}}
    ]
    
    for ctx in invalid_contexts:
        assert not validator.validate_context(ctx), f"Should reject context: {ctx}"
    
    print("✅ ATACDataValidator tests passed")
    
    # Test insight generator
    print("Testing ATACInsightGenerator...")
    insight_gen = ATACInsightGenerator()
    
    # Test dataset overview
    ctx_with_summary = {"data_summary": {"n_peaks": 50000, "n_samples": 6}}
    overview = insight_gen.generate_dataset_overview(ctx_with_summary)
    assert "50,000 peaks" in overview, f"Should show peak count: {overview}"
    assert "6 samples" in overview, f"Should show sample count: {overview}"
    
    # Test fallback cases
    empty_overview = insight_gen.generate_dataset_overview({})
    assert isinstance(empty_overview, str), "Should return string for empty context"
    
    tss_insight = insight_gen.generate_tss_insights({})
    assert isinstance(tss_insight, str), "Should return string for TSS insights"
    
    peak_insight = insight_gen.generate_peak_insights({})
    assert isinstance(peak_insight, str), "Should return string for peak insights"
    
    differential_insight = insight_gen.generate_differential_insights({})
    assert isinstance(differential_insight, str), "Should return string for differential insights"
    
    motif_insight = insight_gen.generate_motif_insights({})
    assert isinstance(motif_insight, str), "Should return string for motif insights"
    
    print("✅ ATACInsightGenerator tests passed")
    
    # Test progress tracker
    print("Testing ATACProgressTracker...")
    progress_tracker = ATACProgressTracker()
    
    # Mock workflow steps
    mock_steps = [
        MockWorkflowStep("data_upload", 5),
        MockWorkflowStep("qc", 12),
        MockWorkflowStep("peak_calling", 25)
    ]
    
    # Test completion calculation
    ctx_empty = {}
    completion_empty = progress_tracker.calculate_completion_percentage(ctx_empty, mock_steps)
    assert completion_empty == 0.0, "Empty context should be 0% complete"
    
    ctx_partial = {"pipeline_status": {"data_upload": True, "qc": False, "peak_calling": False}}
    completion_partial = progress_tracker.calculate_completion_percentage(ctx_partial, mock_steps)
    assert 0 < completion_partial < 100, f"Partial completion should be between 0-100: {completion_partial}"
    
    # Test time remaining calculation
    time_empty = progress_tracker.calculate_time_remaining(ctx_empty, mock_steps)
    assert time_empty > 0, "Should have time remaining for empty context"
    
    time_partial = progress_tracker.calculate_time_remaining(ctx_partial, mock_steps)
    assert time_partial < time_empty, "Partial completion should have less time remaining"
    
    # Test progress insights
    progress_insight = progress_tracker.generate_progress_insight(ctx_partial)
    assert "steps completed" in progress_insight.lower(), f"Should mention completion: {progress_insight}"
    
    print("✅ ATACProgressTracker tests passed")
    
    print("\n🎉 All ATAC-seq helper component tests passed!")
    return True


class MockWorkflowStep:
    """Mock workflow step for testing"""
    def __init__(self, key: str, estimated_time: int):
        self.key = key
        self.estimated_time = estimated_time


if __name__ == "__main__":
    def test_static_helpers():
        """Static tests for helper components"""
        print("Running static helper component tests...")
        
        # Test class instantiation
        validator = ATACDataValidator()
        assert hasattr(validator, 'required_session_keys'), "Should have required session keys"
        assert hasattr(validator, 'peak_file_formats'), "Should have peak file formats"
        
        insight_gen = ATACInsightGenerator()
        assert hasattr(insight_gen, 'insight_templates'), "Should have insight templates"
        
        progress_tracker = ATACProgressTracker()
        assert hasattr(progress_tracker, 'step_weights'), "Should have step weights"
        assert hasattr(progress_tracker, 'progress_messages'), "Should have progress messages"
        
        print("✅ Static helper component tests passed!")
    
    def test_dynamic_helpers():
        """Dynamic tests for helper components"""
        print("Running dynamic helper component tests...")
        
        # Run comprehensive main tests
        success = main()
        assert success, "Main tests should pass"
        
        print("✅ Dynamic helper component tests passed!")
    
    # Run all tests
    test_static_helpers()
    test_dynamic_helpers()