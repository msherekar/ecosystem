"""
scRNA-seq Helper Components

Support classes for scRNA-seq analysis strategy including
data validation, insight generation, and progress tracking.
"""

import logging
from typing import Dict, Any, List, Optional
from .base import WorkflowStep

logger = logging.getLogger(__name__)


class scRNADataValidator:
    """Data validation utilities for scRNA-seq analysis"""
    
    def __init__(self):
        self.required_session_keys = {
            "basic_data": ["anndata"],
            "qc_metrics": ["anndata"],
            "clustering": ["anndata"],
            "differential": ["anndata"]
        }
    
    def validate_context(self, context: Dict[str, Any]) -> bool:
        """Validate scRNA-seq specific context"""
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
            numeric_fields = ["n_cells", "n_genes"]
            for field in numeric_fields:
                if field in data_summary:
                    value = data_summary[field]
                    if not isinstance(value, (int, float)) or value < 0:
                        logger.warning(f"data_summary.{field} should be non-negative number")
                        return False
        
        return True
    
    def is_data_validated(self, context: Dict[str, Any]) -> bool:
        """Check if data has been validated"""
        return (context.get("data_uploaded", False) and 
                context.get("data_validated", False))
    
    def has_basic_data(self, context: Dict[str, Any]) -> bool:
        """Check if basic dataset information is available"""
        try:
            import streamlit as st
            return (context.get("data_uploaded", False) and
                   "data_summary" in context and
                   isinstance(context["data_summary"], dict))
        except ImportError:
            # Fallback when streamlit not available
            return (context.get("data_uploaded", False) and
                   "data_summary" in context)
    
    def has_qc_metrics(self, context: Dict[str, Any]) -> bool:
        """Check if QC metrics are available"""
        try:
            import streamlit as st
            return ("anndata" in st.session_state and 
                   hasattr(st.session_state.anndata, 'obs') and 
                   "pct_counts_mt" in st.session_state.anndata.obs)
        except (ImportError, AttributeError):
            # Fallback when streamlit not available or data not in session
            pipeline_status = context.get("pipeline_status", {})
            return pipeline_status.get("qc", False)
    
    def has_clustering_data(self, context: Dict[str, Any]) -> bool:
        """Check if clustering data is available"""
        try:
            import streamlit as st
            return ("anndata" in st.session_state and 
                   hasattr(st.session_state.anndata, 'obs') and 
                   "leiden" in st.session_state.anndata.obs)
        except (ImportError, AttributeError):
            # Fallback when streamlit not available
            pipeline_status = context.get("pipeline_status", {})
            return pipeline_status.get("clustering", False)


class scRNAInsightGenerator:
    """Generate insights for scRNA-seq analysis"""
    
    def __init__(self):
        self.insight_templates = {
            "dataset_overview": "Dataset: {n_cells:,} cells × {n_genes:,} genes",
            "qc_good": "Good data quality with {metric_name}: {value:.1f}",
            "qc_poor": "Poor data quality - {metric_name}: {value:.1f} (threshold: {threshold})",
            "clustering_basic": "Identified {n_clusters} cell clusters",
            "clustering_detailed": "Identified {n_clusters} cell populations with {largest_cluster} cells in largest cluster"
        }
    
    def generate_dataset_overview(self, context: Dict[str, Any]) -> str:
        """Generate dataset overview insight"""
        try:
            data_summary = context.get("data_summary", {})
            n_cells = data_summary.get("n_cells", 0)
            n_genes = data_summary.get("n_genes", 0)
            
            if n_cells > 0 and n_genes > 0:
                return self.insight_templates["dataset_overview"].format(
                    n_cells=n_cells, n_genes=n_genes
                )
            else:
                return "Dataset uploaded and ready for analysis"
        except Exception as e:
            logger.warning(f"Error generating dataset overview: {e}")
            return "Dataset information available"
    
    def generate_qc_insights(self, context: Dict[str, Any]) -> str:
        """Generate quality control insights"""
        try:
            import streamlit as st
            
            if not hasattr(st.session_state, 'anndata'):
                return "Quality control metrics calculated"
            
            adata = st.session_state.anndata
            
            # Check mitochondrial content
            if 'pct_counts_mt' in adata.obs:
                mt_median = adata.obs['pct_counts_mt'].median()
                if mt_median < 20:  # Good quality threshold
                    return self.insight_templates["qc_good"].format(
                        metric_name="mitochondrial content",
                        value=mt_median
                    )
                else:
                    return self.insight_templates["qc_poor"].format(
                        metric_name="mitochondrial content",
                        value=mt_median,
                        threshold="<20%"
                    )
            
            # Check ribosomal content
            if 'pct_counts_ribo' in adata.obs:
                ribo_median = adata.obs['pct_counts_ribo'].median()
                return f"Ribosomal gene content: {ribo_median:.1f}%"
            
            return "Quality control analysis completed"
            
        except ImportError:
            return "Quality control metrics calculated"
        except Exception as e:
            logger.warning(f"Error generating QC insights: {e}")
            return "Quality control analysis completed"
    
    def generate_clustering_insights(self, context: Dict[str, Any]) -> str:
        """Generate clustering insights"""
        try:
            import streamlit as st
            
            if not hasattr(st.session_state, 'anndata'):
                pipeline_status = context.get("pipeline_status", {})
                if pipeline_status.get("clustering", False):
                    return "Cell clustering completed"
                return "Clustering data not available"
            
            adata = st.session_state.anndata
            
            if 'leiden' in adata.obs:
                n_clusters = len(adata.obs['leiden'].unique())
                
                # Get cluster sizes
                cluster_sizes = adata.obs['leiden'].value_counts()
                largest_cluster_size = cluster_sizes.max()
                
                if len(cluster_sizes) > 1:
                    return self.insight_templates["clustering_detailed"].format(
                        n_clusters=n_clusters,
                        largest_cluster=largest_cluster_size
                    )
                else:
                    return self.insight_templates["clustering_basic"].format(
                        n_clusters=n_clusters
                    )
            
            return "Clustering analysis completed"
            
        except ImportError:
            return "Cell clustering completed"
        except Exception as e:
            logger.warning(f"Error generating clustering insights: {e}")
            return "Clustering analysis completed"
    
    def generate_performance_insights(self, context: Dict[str, Any]) -> str:
        """Generate performance-related insights"""
        try:
            performance_data = context.get("performance_data", {})
            
            if "analysis_time" in performance_data:
                analysis_time = performance_data["analysis_time"]
                if analysis_time < 60:
                    return f"Fast analysis completed in {analysis_time:.1f} seconds"
                elif analysis_time < 300:
                    return f"Analysis completed in {analysis_time/60:.1f} minutes"
                else:
                    return f"Long analysis completed in {analysis_time/60:.1f} minutes"
            
            if "memory_usage" in performance_data:
                memory_mb = performance_data["memory_usage"]
                if memory_mb < 1000:
                    return f"Low memory usage: {memory_mb:.0f} MB"
                elif memory_mb < 5000:
                    return f"Moderate memory usage: {memory_mb/1000:.1f} GB"
                else:
                    return f"High memory usage: {memory_mb/1000:.1f} GB"
            
            return "Performance metrics available"
            
        except Exception as e:
            logger.warning(f"Error generating performance insights: {e}")
            return "Analysis performance tracked"


class scRNAProgressTracker:
    """Track and report analysis progress"""
    
    def __init__(self):
        self.step_weights = {
            "data_upload": 5,
            "data_validation": 3,
            "qc": 10,
            "filtering": 15,
            "normalization": 20,
            "dimred": 25,
            "clustering": 20,
            "dea": 30,
            "viz": 15,
            "enrichment": 20
        }
        
        self.progress_messages = {
            "early": "Analysis in early stages",
            "mid": "Analysis progressing well",
            "advanced": "Analysis nearly complete",
            "complete": "Analysis workflow completed"
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
            return 60  # Default fallback
    
    def generate_progress_insight(self, context: Dict[str, Any]) -> str:
        """Generate progress insight based on completed steps"""
        try:
            pipeline_status = context.get("pipeline_status", {})
            completed_steps = [step for step, done in pipeline_status.items() if done]
            
            if not completed_steps:
                return "Analysis not started - upload data to begin"
            elif len(completed_steps) <= 2:
                return f"{self.progress_messages['early']} ({len(completed_steps)} steps completed)"
            elif len(completed_steps) <= 5:
                return f"{self.progress_messages['mid']} ({len(completed_steps)} steps completed)"
            elif len(completed_steps) <= 8:
                return f"{self.progress_messages['advanced']} ({len(completed_steps)} steps completed)"
            else:
                return f"{self.progress_messages['complete']} ({len(completed_steps)} steps completed)"
                
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


def main():
    """Test scRNA-seq helper components"""
    print("🧪 Testing scRNA-seq Helper Components")
    print("=" * 50)
    
    # Test data validator
    print("Testing scRNADataValidator...")
    validator = scRNADataValidator()
    
    # Test valid contexts
    valid_contexts = [
        {},
        {"data_uploaded": True},
        {"pipeline_status": {"qc": True, "filtering": False}},
        {"data_summary": {"n_cells": 1000, "n_genes": 2000}}
    ]
    
    for ctx in valid_contexts:
        assert validator.validate_context(ctx), f"Should validate context: {ctx}"
    
    # Test invalid contexts
    invalid_contexts = [
        "not a dict",
        {"pipeline_status": "not a dict"},
        {"data_summary": {"n_cells": -1}},
        {"pipeline_status": {"qc": "not a bool"}}
    ]
    
    for ctx in invalid_contexts:
        assert not validator.validate_context(ctx), f"Should reject context: {ctx}"
    
    print("✅ scRNADataValidator tests passed")
    
    # Test insight generator
    print("Testing scRNAInsightGenerator...")
    insight_gen = scRNAInsightGenerator()
    
    # Test dataset overview
    ctx_with_summary = {"data_summary": {"n_cells": 5000, "n_genes": 20000}}
    overview = insight_gen.generate_dataset_overview(ctx_with_summary)
    assert "5,000 cells" in overview, f"Should format cell count: {overview}"
    assert "20,000 genes" in overview, f"Should format gene count: {overview}"
    
    # Test fallback cases
    empty_overview = insight_gen.generate_dataset_overview({})
    assert isinstance(empty_overview, str), "Should return string for empty context"
    
    qc_insight = insight_gen.generate_qc_insights({})
    assert isinstance(qc_insight, str), "Should return string for QC insights"
    
    clustering_insight = insight_gen.generate_clustering_insights({})
    assert isinstance(clustering_insight, str), "Should return string for clustering insights"
    
    print("✅ scRNAInsightGenerator tests passed")
    
    # Test progress tracker
    print("Testing scRNAProgressTracker...")
    progress_tracker = scRNAProgressTracker()
    
    # Mock workflow steps
    mock_steps = [
        MockWorkflowStep("data_upload", 5),
        MockWorkflowStep("qc", 10),
        MockWorkflowStep("clustering", 20)
    ]
    
    # Test completion calculation
    ctx_empty = {}
    completion_empty = progress_tracker.calculate_completion_percentage(ctx_empty, mock_steps)
    assert completion_empty == 0.0, "Empty context should be 0% complete"
    
    ctx_partial = {"pipeline_status": {"data_upload": True, "qc": False}}
    completion_partial = progress_tracker.calculate_completion_percentage(ctx_partial, mock_steps)
    assert 0 < completion_partial < 100, f"Partial completion should be between 0-100: {completion_partial}"
    
    # Test time remaining calculation
    time_empty = progress_tracker.calculate_time_remaining(ctx_empty, mock_steps)
    assert time_empty > 0, "Should have time remaining for empty context"
    
    time_partial = progress_tracker.calculate_time_remaining(ctx_partial, mock_steps)
    assert time_partial < time_empty, "Partial completion should have less time remaining"
    
    # Test progress insights
    progress_insight = progress_tracker.generate_progress_insight(ctx_partial)
    assert "completed" in progress_insight.lower(), f"Should mention completion: {progress_insight}"
    
    print("✅ scRNAProgressTracker tests passed")
    
    print("\n🎉 All scRNA-seq helper component tests passed!")
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
        validator = scRNADataValidator()
        assert hasattr(validator, 'required_session_keys'), "Should have required session keys"
        
        insight_gen = scRNAInsightGenerator()
        assert hasattr(insight_gen, 'insight_templates'), "Should have insight templates"
        
        progress_tracker = scRNAProgressTracker()
        assert hasattr(progress_tracker, 'step_weights'), "Should have step weights"
        
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