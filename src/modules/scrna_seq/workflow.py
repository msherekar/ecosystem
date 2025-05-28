"""
scRNA-seq Workflow Manager
Main entry point for the scRNA-seq analysis pipeline.
Handles business logic for pipeline execution without UI components.
"""

import streamlit as st
from src.modules.scrna_seq.automated_pipeline import run_automated_pipeline
from src.modules.scrna_seq.step_manager import get_step_manager


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

    # Get step manager
    step_manager = get_step_manager()
    
    # Execute current step
    step_manager.run_current_step()
    
    # Return success result
    current_step = st.session_state.scrna_current_step
    return {
        "success": True,
        "message": f"scRNA-seq pipeline is running. Current step: {current_step}",
        "summary": f"Executed scRNA-seq pipeline step: {current_step}",
        "step_manager": step_manager,
        "show_upload_message": False
    }


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


