"""
RNA-seq Helper Components

Support classes for RNA-seq analysis strategy including
data validation, insight generation, and progress tracking.
"""

import logging
from typing import Dict, Any, List, Optional
from .base import WorkflowStep

logger = logging.getLogger(__name__)


class RNADataValidator:
    """Data validation utilities for RNA-seq analysis"""
    
    def __init__(self):
        self.required_session_keys = {
            "count_data": ["rnaseq_counts_df"],
            "metadata": ["sample_metadata"],
            "deseq_results": ["deseq_results"],
            "go_results": ["go_results"]
        }
        
        self.count_matrix_formats = [".csv", ".tsv", ".txt", ".xlsx"]
        self.metadata_formats = [".csv", ".tsv", ".txt", ".xlsx"]
    
    def validate_context(self, context: Dict[str, Any]) -> bool:
        """Validate RNA-seq specific context"""
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
            numeric_fields = ["n_samples", "n_genes"]
            for field in numeric_fields:
                if field in data_summary:
                    value = data_summary[field]
                    if not isinstance(value, (int, float)) or value < 0:
                        logger.warning(f"data_summary.{field} should be non-negative number")
                        return False
        
        # Validate DESeq2 results format if present
        deseq_config = context.get("deseq_config")
        if deseq_config is not None:
            if not isinstance(deseq_config, dict):
                logger.warning("deseq_config should be a dictionary")
                return False
            
            # Check for valid comparison columns
            if "comparison_column" in deseq_config:
                if not isinstance(deseq_config["comparison_column"], str):
                    logger.warning("comparison_column should be a string")
                    return False
        
        return True
    
    def is_data_validated(self, context: Dict[str, Any]) -> bool:
        """Check if data has been validated"""
        return (context.get("data_uploaded", False) and 
                context.get("data_validated", False))
    
    def has_count_data(self, context: Dict[str, Any]) -> bool:
        """Check if RNA-seq count data is available"""
        try:
            import streamlit as st
            return ("rnaseq_counts_df" in st.session_state and 
                   st.session_state.rnaseq_counts_df is not None)
        except ImportError:
            # Fallback when streamlit not available
            return (context.get("data_uploaded", False) and
                   "data_summary" in context)
    
    def has_qc_metrics(self, context: Dict[str, Any]) -> bool:
        """Check if QC metrics are available"""
        try:
            import streamlit as st
            return ("qc_metrics" in st.session_state and 
                   st.session_state.qc_metrics is not None)
        except ImportError:
            # Fallback when streamlit not available
            pipeline_status = context.get("pipeline_status", {})
            return pipeline_status.get("qc", False)
    
    def has_deseq_data(self, context: Dict[str, Any]) -> bool:
        """Check if DESeq2 results are available"""
        try:
            import streamlit as st
            return ("deseq_results" in st.session_state and 
                   st.session_state.deseq_results is not None)
        except ImportError:
            # Fallback when streamlit not available
            pipeline_status = context.get("pipeline_status", {})
            return pipeline_status.get("deseq2_completed", False)
    
    def has_go_data(self, context: Dict[str, Any]) -> bool:
        """Check if GO enrichment results are available"""
        try:
            import streamlit as st
            return ("go_results" in st.session_state and 
                   st.session_state.go_results is not None)
        except ImportError:
            # Fallback when streamlit not available
            pipeline_status = context.get("pipeline_status", {})
            return pipeline_status.get("go_enrichment_completed", False)
    
    def get_significant_genes_count(self, context: Dict[str, Any]) -> int:
        """Get count of significantly differentially expressed genes"""
        try:
            import streamlit as st
            
            if not hasattr(st.session_state, 'deseq_results'):
                return 0
            
            deseq_results = st.session_state.deseq_results
            
            if hasattr(deseq_results, 'shape') and 'padj' in deseq_results.columns:
                significant = deseq_results[deseq_results['padj'] < 0.05]
                return len(significant)
            
            return 0
            
        except ImportError:
            # Fallback when streamlit not available
            return context.get("significant_genes_count", 0)
        except Exception as e:
            logger.warning(f"Error getting significant genes count: {e}")
            return 0


class RNAInsightGenerator:
    """Generate insights for RNA-seq analysis"""
    
    def __init__(self):
        self.insight_templates = {
            "dataset_overview": "RNA-seq dataset: {n_samples} samples × {n_genes:,} genes",
            "qc_good": "Good library quality - {metric_name}: {value}",
            "qc_poor": "Library quality concern - {metric_name}: {value}",
            "deseq_basic": "DESeq2: {n_significant} significant genes (padj < 0.05)",
            "deseq_detailed": "Found {n_up} upregulated and {n_down} downregulated genes",
            "go_basic": "GO enrichment: {n_pathways} significant pathways",
            "go_detailed": "Top enriched pathway: {top_pathway}"
        }
    
    def generate_dataset_overview(self, context: Dict[str, Any]) -> str:
        """Generate dataset overview insight"""
        try:
            data_summary = context.get("data_summary", {})
            n_samples = data_summary.get("n_samples", 0)
            n_genes = data_summary.get("n_genes", 0)
            
            if n_samples > 0 and n_genes > 0:
                return self.insight_templates["dataset_overview"].format(
                    n_samples=n_samples, n_genes=n_genes
                )
            
            # Fallback to session state
            try:
                import streamlit as st
                if hasattr(st.session_state, 'rnaseq_counts_df'):
                    counts_df = st.session_state.rnaseq_counts_df
                    if hasattr(counts_df, 'shape'):
                        n_genes, n_samples = counts_df.shape
                        return self.insight_templates["dataset_overview"].format(
                            n_samples=n_samples, n_genes=n_genes
                        )
            except ImportError:
                pass
            
            return "RNA-seq dataset uploaded and ready for analysis"
            
        except Exception as e:
            logger.warning(f"Error generating dataset overview: {e}")
            return "Dataset information available"
    
    def generate_qc_insights(self, context: Dict[str, Any]) -> str:
        """Generate quality control insights"""
        try:
            import streamlit as st
            
            if not hasattr(st.session_state, 'qc_metrics'):
                return "Quality control assessment completed"
            
            qc_metrics = st.session_state.qc_metrics
            
            # Check library sizes
            if 'library_sizes' in qc_metrics:
                lib_sizes = qc_metrics['library_sizes']
                median_lib_size = lib_sizes.median() if hasattr(lib_sizes, 'median') else 0
                
                if median_lib_size > 1000000:  # > 1M reads
                    return self.insight_templates["qc_good"].format(
                        metric_name="median library size",
                        value=f"{median_lib_size/1000000:.1f}M reads"
                    )
                else:
                    return self.insight_templates["qc_poor"].format(
                        metric_name="median library size",
                        value=f"{median_lib_size/1000000:.1f}M reads"
                    )
            
            # Check detection rates
            if 'detection_rates' in qc_metrics:
                detection_rates = qc_metrics['detection_rates']
                mean_detection = detection_rates.mean() if hasattr(detection_rates, 'mean') else 0
                
                if mean_detection > 0.5:  # > 50% genes detected
                    return self.insight_templates["qc_good"].format(
                        metric_name="gene detection rate",
                        value=f"{mean_detection*100:.1f}%"
                    )
                else:
                    return self.insight_templates["qc_poor"].format(
                        metric_name="gene detection rate",
                        value=f"{mean_detection*100:.1f}%"
                    )
            
            return "Quality control metrics calculated"
            
        except ImportError:
            return "Quality control assessment completed"
        except Exception as e:
            logger.warning(f"Error generating QC insights: {e}")
            return "Quality control analysis completed"
    
    def generate_deseq_insights(self, context: Dict[str, Any]) -> str:
        """Generate DESeq2 results insights"""
        try:
            import streamlit as st
            
            if not hasattr(st.session_state, 'deseq_results'):
                pipeline_status = context.get("pipeline_status", {})
                if pipeline_status.get("deseq2_completed", False):
                    return "Differential expression analysis completed"
                return "DESeq2 results not available"
            
            deseq_results = st.session_state.deseq_results
            
            if hasattr(deseq_results, 'shape') and 'padj' in deseq_results.columns:
                # Count significant genes
                significant = deseq_results[deseq_results['padj'] < 0.05]
                n_significant = len(significant)
                
                if n_significant == 0:
                    return "DESeq2: No significantly differentially expressed genes found"
                
                # Count up/down regulated
                if 'log2FoldChange' in deseq_results.columns:
                    upregulated = significant[significant['log2FoldChange'] > 0]
                    downregulated = significant[significant['log2FoldChange'] < 0]
                    
                    if len(upregulated) > 0 or len(downregulated) > 0:
                        return self.insight_templates["deseq_detailed"].format(
                            n_up=len(upregulated),
                            n_down=len(downregulated)
                        )
                
                return self.insight_templates["deseq_basic"].format(
                    n_significant=n_significant
                )
            
            return "Differential expression analysis completed"
            
        except ImportError:
            return "DESeq2 analysis completed"
        except Exception as e:
            logger.warning(f"Error generating DESeq2 insights: {e}")
            return "Differential expression analysis completed"
    
    def generate_go_insights(self, context: Dict[str, Any]) -> str:
        """Generate GO enrichment insights"""
        try:
            import streamlit as st
            
            if not hasattr(st.session_state, 'go_results'):
                pipeline_status = context.get("pipeline_status", {})
                if pipeline_status.get("go_enrichment_completed", False):
                    return "Gene Ontology enrichment analysis completed"
                return "GO enrichment results not available"
            
            go_results = st.session_state.go_results
            
            if hasattr(go_results, '__len__'):
                n_pathways = len(go_results)
                
                if n_pathways == 0:
                    return "GO enrichment: No significantly enriched pathways found"
                
                # Get top pathway if available
                if hasattr(go_results, 'iloc') and len(go_results) > 0:
                    if 'term' in go_results.columns:
                        top_pathway = go_results.iloc[0]['term']
                        return self.insight_templates["go_detailed"].format(
                            top_pathway=top_pathway
                        )
                
                return self.insight_templates["go_basic"].format(
                    n_pathways=n_pathways
                )
            
            return "Gene Ontology enrichment analysis completed"
            
        except ImportError:
            return "GO enrichment analysis completed"
        except Exception as e:
            logger.warning(f"Error generating GO insights: {e}")
            return "Gene Ontology enrichment analysis completed"
    
    def generate_performance_insights(self, context: Dict[str, Any]) -> str:
        """Generate performance-related insights"""
        try:
            performance_data = context.get("performance_data", {})
            
            if "deseq2_time" in performance_data:
                deseq_time = performance_data["deseq2_time"]
                if deseq_time < 30:
                    return f"Fast DESeq2 analysis completed in {deseq_time:.1f} seconds"
                elif deseq_time < 300:
                    return f"DESeq2 analysis completed in {deseq_time/60:.1f} minutes"
                else:
                    return f"Long DESeq2 analysis completed in {deseq_time/60:.1f} minutes"
            
            if "memory_usage" in performance_data:
                memory_mb = performance_data["memory_usage"]
                if memory_mb < 500:
                    return f"Low memory usage: {memory_mb:.0f} MB"
                elif memory_mb < 2000:
                    return f"Moderate memory usage: {memory_mb/1000:.1f} GB"
                else:
                    return f"High memory usage: {memory_mb/1000:.1f} GB"
            
            if "sample_count" in performance_data:
                n_samples = performance_data["sample_count"]
                if n_samples < 10:
                    return f"Small dataset: {n_samples} samples"
                elif n_samples < 50:
                    return f"Medium dataset: {n_samples} samples"
                else:
                    return f"Large dataset: {n_samples} samples"
            
            return "Performance metrics available"
            
        except Exception as e:
            logger.warning(f"Error generating performance insights: {e}")
            return "Analysis performance tracked"


class RNAProgressTracker:
    """Track and report RNA-seq analysis progress"""
    
    def __init__(self):
        self.step_weights = {
            "data_upload": 5,
            "data_validation": 3,
            "qc": 8,
            "filtering": 5,
            "deseq2": 25,
            "visualization": 10,
            "go_enrichment": 15,
            "pathway_analysis": 12,
            "export": 5
        }
        
        self.progress_messages = {
            "early": "Analysis in initial stages",
            "preprocessing": "Data preprocessing in progress", 
            "analysis": "Differential expression analysis",
            "interpretation": "Biological interpretation phase",
            "complete": "RNA-seq analysis completed"
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
                    remaining_time += step.estimated_time or 10
            
            return remaining_time
            
        except Exception as e:
            logger.warning(f"Error calculating time remaining: {e}")
            return 30  # Default fallback
    
    def generate_progress_insight(self, context: Dict[str, Any]) -> str:
        """Generate progress insight based on completed steps"""
        try:
            pipeline_status = context.get("pipeline_status", {})
            completed_steps = [step for step, done in pipeline_status.items() if done]
            
            if not completed_steps:
                return "RNA-seq analysis not started - upload data to begin"
            
            # Determine analysis phase
            if pipeline_status.get("deseq2_completed", False):
                if pipeline_status.get("go_enrichment_completed", False):
                    return f"{self.progress_messages['interpretation']} ({len(completed_steps)} steps completed)"
                else:
                    return f"{self.progress_messages['analysis']} completed ({len(completed_steps)} steps)"
            elif pipeline_status.get("qc", False):
                return f"{self.progress_messages['preprocessing']} ({len(completed_steps)} steps completed)"
            else:
                return f"{self.progress_messages['early']} ({len(completed_steps)} steps completed)"
                
        except Exception as e:
            logger.warning(f"Error generating progress insight: {e}")
            return "Analysis progress tracked"
    
    def has_performance_data(self, context: Dict[str, Any]) -> bool:
        """Check if performance data is available"""
        performance_data = context.get("performance_data", {})
        return isinstance(performance_data, dict) and len(performance_data) > 0
    
    def get_next_recommended_step(self, context: Dict[str, Any], 
                                workflow_steps: List[WorkflowStep]) -> Optional[str]:
        """Get next recommended workflow step"""
        try:
            pipeline_status = context.get("pipeline_status", {})
            completed_steps = [step for step, done in pipeline_status.items() if done]
            
            # Find next available step
            for step in workflow_steps:
                if not pipeline_status.get(step.key, False):
                    # Check if dependencies are met
                    if step.is_ready(completed_steps):
                        return step.key
            
            return None
            
        except Exception as e:
            logger.warning(f"Error finding next step: {e}")
            return None
    
    def get_analysis_phase(self, context: Dict[str, Any]) -> str:
        """Get current analysis phase"""
        try:
            pipeline_status = context.get("pipeline_status", {})
            
            if pipeline_status.get("go_enrichment_completed", False):
                return "interpretation"
            elif pipeline_status.get("deseq2_completed", False):
                return "analysis"
            elif pipeline_status.get("qc", False):
                return "preprocessing"
            elif pipeline_status.get("data_uploaded", False):
                return "setup"
            else:
                return "initial"
                
        except Exception as e:
            logger.warning(f"Error determining analysis phase: {e}")
            return "unknown"
    
    def estimate_remaining_by_phase(self, context: Dict[str, Any]) -> Dict[str, int]:
        """Estimate time remaining by analysis phase"""
        try:
            phase = self.get_analysis_phase(context)
            
            phase_times = {
                "initial": 60,     # Full analysis
                "setup": 55,       # After upload
                "preprocessing": 45, # After QC
                "analysis": 25,    # After DESeq2
                "interpretation": 10, # After GO
                "complete": 0
            }
            
            return {
                "current_phase": phase,
                "estimated_minutes": phase_times.get(phase, 30),
                "confidence": "medium" if phase in phase_times else "low"
            }
            
        except Exception as e:
            logger.warning(f"Error estimating time by phase: {e}")
            return {
                "current_phase": "unknown",
                "estimated_minutes": 30,
                "confidence": "low"
            }


def main():
    """Test RNA-seq helper components"""
    print("🧪 Testing RNA-seq Helper Components")
    print("=" * 50)
    
    # Test data validator
    print("Testing RNADataValidator...")
    validator = RNADataValidator()
    
    # Test valid contexts
    valid_contexts = [
        {},
        {"data_uploaded": True},
        {"pipeline_status": {"deseq2_completed": True, "go_enrichment_completed": False}},
        {"data_summary": {"n_samples": 12, "n_genes": 15000}},
        {"deseq_config": {"comparison_column": "condition"}}
    ]
    
    for ctx in valid_contexts:
        assert validator.validate_context(ctx), f"Should validate context: {ctx}"
    
    # Test invalid contexts
    invalid_contexts = [
        "not a dict",
        {"pipeline_status": "not a dict"},
        {"data_summary": {"n_samples": -1}},
        {"pipeline_status": {"deseq2_completed": "not a bool"}},
        {"deseq_config": {"comparison_column": 123}}
    ]
    
    for ctx in invalid_contexts:
        assert not validator.validate_context(ctx), f"Should reject context: {ctx}"
    
    print("✅ RNADataValidator tests passed")
    
    # Test insight generator
    print("Testing RNAInsightGenerator...")
    insight_gen = RNAInsightGenerator()
    
    # Test dataset overview
    ctx_with_summary = {"data_summary": {"n_samples": 12, "n_genes": 15000}}
    overview = insight_gen.generate_dataset_overview(ctx_with_summary)
    assert "12 samples" in overview, f"Should show sample count: {overview}"
    assert "15,000 genes" in overview, f"Should format gene count: {overview}"
    
    # Test fallback cases
    empty_overview = insight_gen.generate_dataset_overview({})
    assert isinstance(empty_overview, str), "Should return string for empty context"
    
    qc_insight = insight_gen.generate_qc_insights({})
    assert isinstance(qc_insight, str), "Should return string for QC insights"
    
    deseq_insight = insight_gen.generate_deseq_insights({})
    assert isinstance(deseq_insight, str), "Should return string for DESeq2 insights"
    
    go_insight = insight_gen.generate_go_insights({})
    assert isinstance(go_insight, str), "Should return string for GO insights"
    
    print("✅ RNAInsightGenerator tests passed")
    
    # Test progress tracker
    print("Testing RNAProgressTracker...")
    progress_tracker = RNAProgressTracker()
    
    # Mock workflow steps
    mock_steps = [
        MockWorkflowStep("data_upload", 5),
        MockWorkflowStep("qc", 8),
        MockWorkflowStep("deseq2", 25)
    ]
    
    # Test completion calculation
    ctx_empty = {}
    completion_empty = progress_tracker.calculate_completion_percentage(ctx_empty, mock_steps)
    assert completion_empty == 0.0, "Empty context should be 0% complete"
    
    ctx_partial = {"pipeline_status": {"data_upload": True, "qc": False, "deseq2": False}}
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
    
    # Test analysis phase detection
    phase_empty = progress_tracker.get_analysis_phase({})
    assert phase_empty == "initial", "Empty context should be initial phase"
    
    phase_deseq = progress_tracker.get_analysis_phase({"pipeline_status": {"deseq2_completed": True}})
    assert phase_deseq == "analysis", "DESeq2 completed should be analysis phase"
    
    # Test time estimation by phase
    time_estimate = progress_tracker.estimate_remaining_by_phase(ctx_partial)
    assert "current_phase" in time_estimate, "Should include current phase"
    assert "estimated_minutes" in time_estimate, "Should include time estimate"
    assert isinstance(time_estimate["estimated_minutes"], int), "Time should be integer"
    
    print("✅ RNAProgressTracker tests passed")
    
    print("\n🎉 All RNA-seq helper component tests passed!")
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
        validator = RNADataValidator()
        assert hasattr(validator, 'required_session_keys'), "Should have required session keys"
        assert hasattr(validator, 'count_matrix_formats'), "Should have matrix formats"
        
        insight_gen = RNAInsightGenerator()
        assert hasattr(insight_gen, 'insight_templates'), "Should have insight templates"
        
        progress_tracker = RNAProgressTracker()
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