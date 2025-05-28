"""
scRNA-seq Workflow Manager
Main entry point for the scRNA-seq analysis pipeline.
Handles both manual step-by-step and automated pipeline execution.
"""

import streamlit as st
from src.modules.scrna_seq.step_manager import get_step_manager
from src.modules.scrna_seq.pipeline_config import get_automated_steps

# Import the actual step functions with correct names
from src.modules.scrna_seq.qc import do_qc
from src.modules.scrna_seq.filtering import do_filtering
from src.modules.scrna_seq.normalization import do_normalization
from src.modules.scrna_seq.reduction import perform_dimensionality_reduction
from src.modules.scrna_seq.clustering import perform_clustering
from src.modules.scrna_seq.dea import run_differential_expression
from src.modules.scrna_seq.enrichment import run_enrichment_analysis


def run_scrnaseq_pipeline():
    """
    Main function to run the scRNA-seq pipeline.
    Returns pipeline status for UI components to handle display.
    """
    # Check if data is loaded
    if "anndata" not in st.session_state or st.session_state.anndata is None:
        return {
            "success": False,
            "message": "No scRNA-seq data uploaded. Please upload .h5ad or 10x files first.",
            "summary": "scRNA-seq pipeline requires data upload",
            "show_upload_message": True
        }

    # Check if we're using the new technique UI (scalable system)
    if st.session_state.get("use_technique_ui", True):
        # Return status without rendering old UI
        return {
            "success": True,
            "message": "scRNA-seq pipeline ready - using scalable technique UI",
            "summary": "Pipeline managed by technique UI system",
            "show_upload_message": False
        }
    
    # Legacy mode: use old step manager (for backward compatibility)
    step_manager = get_step_manager()
    step_manager.run_current_step()
    
    current_step = st.session_state.scrna_current_step
    return {
        "success": True,
        "message": f"scRNA-seq pipeline is running. Current step: {current_step}",
        "summary": f"Executed scRNA-seq pipeline step: {current_step}",
        "step_manager": step_manager,
        "show_upload_message": False
    }


def run_automated_pipeline():
    """
    Run the entire scRNA-seq pipeline automatically using existing step functions.
    Returns True if successful, False otherwise.
    """
    anndata = st.session_state.get("anndata")
    if anndata is None:
        st.error("⚠️ No AnnData loaded. Please upload scRNA-seq data first.")
        return False

    try:
        # Clear any previous outputs
        st.empty()
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        automated_steps = get_automated_steps()
        total_steps = len(automated_steps)
        
        for i, step_config in enumerate(automated_steps):
            step_key = step_config["key"]
            step_title = step_config["title"]
            done_flag = step_config["done_flag"]
            
            # Skip if already done
            if st.session_state.get(done_flag, False):
                continue
                
            # Update progress
            progress = int((i / total_steps) * 100)
            status_text.text(f"{step_title}...")
            progress_bar.progress(progress)
            
            # Execute step using existing functions
            success = _execute_step(step_key)
            if not success:
                return False

        # Complete
        progress_bar.progress(100)
        status_text.text("✅ All steps completed successfully!")
        
        # Set current step to visualization to show results
        st.session_state.scrna_current_step = "viz"
        
        # Add completion message to chat
        _add_completion_message()
        
        return True
        
    except Exception as e:
        st.error(f"❌ Automated pipeline failed: {e}")
        return False


def _execute_step(step_key):
    """Execute a specific pipeline step using existing functions."""
    try:
        if step_key == "qc":
            do_qc()
        elif step_key == "filtering":
            do_filtering()
        elif step_key == "normalization":
            do_normalization()
        elif step_key == "dimred":
            perform_dimensionality_reduction()
        elif step_key == "clustering":
            perform_clustering()
        elif step_key == "viz":
            # Visualization is handled in clustering step
            pass
        elif step_key == "dea":
            run_differential_expression()
        elif step_key == "enrichment":
            run_enrichment_analysis()
        else:
            st.warning(f"⚠️ Step {step_key} not implemented")
            return True
        
        return True
            
    except Exception as e:
        st.error(f"❌ Step {step_key} failed: {e}")
        return False


def _add_completion_message():
    """Add completion message to chat."""
    anndata = st.session_state.get("anndata")
    if anndata and "leiden" in anndata.obs:
        n_clusters = len(anndata.obs["leiden"].unique())
        completion_message = (
            f"🎉 Complete scRNA-seq analysis finished! "
            f"Analyzed {anndata.shape[0]:,} cells × {anndata.shape[1]:,} genes, "
            f"identified {n_clusters} clusters, and performed enrichment analysis."
        )
    else:
        completion_message = "🎉 scRNA-seq analysis pipeline completed successfully!"
        
    if 'messages' in st.session_state:
        st.session_state.messages.append({"role": "assistant", "content": completion_message})


def run_automated_scrnaseq_pipeline():
    """
    Run the automated scRNA-seq pipeline.
    Returns success status for UI handling.
    """
    return run_automated_pipeline()


def get_pipeline_status():
    """Get current pipeline status for external use."""
    if "anndata" not in st.session_state or st.session_state.anndata is None:
        return {
            "status": "no_data",
            "message": "No data loaded",
            "current_step": None,
            "progress": 0
        }
    
    step_manager = get_step_manager()
    progress = step_manager.get_pipeline_progress()
    current_step = step_manager.get_current_step_info()
    
    return {
        "status": "running" if progress["percentage"] < 100 else "complete",
        "message": f"Pipeline {progress['percentage']}% complete",
        "current_step": current_step["key"] if current_step else None,
        "progress": progress["percentage"],
        "step_manager": step_manager
    }


