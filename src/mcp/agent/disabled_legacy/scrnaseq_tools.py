"""
Single-cell RNA-seq specific tools for the agent system.
"""

import streamlit as st
from src.modules.agent.registry import registry
from src.modules.scrna_seq.workflow import run_scrnaseq_pipeline
from src.modules.agent.plot_analyzer import analyze_current_plots, PlotAnalyzer

def get_scrnaseq_insights():
    """Get detailed insights about current scRNA-seq analysis state."""
    return {
        "success": True, 
        "message": registry.get_analysis_summary("scrnaseq"),
        "summary": "Retrieved scRNA-seq analysis insights"
    }

def advance_scrnaseq_step():
    """Advance to the next step in the scRNA-seq pipeline."""
    if "scrna_current_step" not in st.session_state:
        st.session_state.scrna_current_step = "input_summary"
    
    current_step = st.session_state.scrna_current_step
    
    # Define the step progression
    step_progression = {
        "input_summary": "qc",
        "qc": "filtering", 
        "filtering": "normalization",
        "normalization": "dimred",
        "dimred": "clustering",
        "clustering": "viz",
        "viz": "dea",
        "dea": "enrichment",
        "enrichment": "markers",
        "markers": "trajectory",
        "trajectory": "ml"
    }
    
    next_step = step_progression.get(current_step)
    if next_step:
        st.session_state.scrna_current_step = next_step
        st.session_state.scrna_step_acknowledged = True
        return {
            "success": True,
            "message": f"Advanced to {next_step} step in scRNA-seq pipeline",
            "summary": f"Moved from {current_step} to {next_step}"
        }
    else:
        return {
            "success": False,
            "message": f"Already at the final step or unknown step: {current_step}",
            "summary": "Cannot advance further in pipeline"
        }

def analyze_plots():
    """Analyze currently displayed plots and provide biological insights."""
    insights = analyze_current_plots()
    return {
        "success": True,
        "message": insights,
        "summary": "Analyzed current plots and provided biological insights"
    }

def get_plot_details():
    """Get detailed information about specific plots or analysis results."""
    details = []
    
    if "anndata" in st.session_state and st.session_state.anndata is not None:
        anndata = st.session_state.anndata
        
        # Get current step summaries if available
        step_summaries = st.session_state.get("scrna_step_summaries", {})
        if step_summaries:
            details.append("**Previous Analysis Summaries:**")
            for step, summary in step_summaries.items():
                details.append(f"- {step.upper()}: {summary}")
        
        # Add current data statistics
        details.append(f"\n**Current Data:** {anndata.n_obs:,} cells × {anndata.n_vars:,} genes")
        
        # Add available analysis results
        available_results = []
        if "X_pca" in anndata.obsm:
            available_results.append("PCA")
        if "X_umap" in anndata.obsm:
            available_results.append("UMAP")
        if "leiden" in anndata.obs:
            available_results.append("Leiden clustering")
        
        if available_results:
            details.append(f"**Available Results:** {', '.join(available_results)}")
    
    return {
        "success": True,
        "message": "\n".join(details) if details else "No detailed plot information available.",
        "summary": "Retrieved detailed plot and analysis information"
    }

def register_scrnaseq_tools():
    registry.register_tool(
        name="run_scrnaseq",
        description="Set up and run the scRNA-seq analysis pipeline",
        parameters={},
        executor=run_scrnaseq_pipeline,
        analysis_type="scrnaseq",
        ui_message="✅ scRNA-seq analysis activated. Please upload the required files."
    )
    
    registry.register_tool(
        name="advance_scrnaseq_step",
        description="Advance to the next step in the scRNA-seq analysis pipeline. Use this when the user asks to 'perform the next step', 'advance', 'continue', or 'move to the next step'. This will automatically move from the current step to the next one in the pipeline sequence.",
        parameters={},
        executor=advance_scrnaseq_step,
        analysis_type="scrnaseq",
        ui_message="➡️ Advancing to next scRNA-seq analysis step..."
    )
    
    registry.register_tool(
        name="get_scrnaseq_insights",
        description="Get detailed insights about current scRNA-seq analysis results",
        parameters={},
        executor=get_scrnaseq_insights,
        analysis_type="scrnaseq",
        ui_message="📊 Getting scRNA-seq analysis insights..."
    )

    registry.register_tool(
        name="analyze_plots",
        description="Analyze currently displayed plots and provide biological insights",
        parameters={},
        executor=analyze_plots,
        analysis_type="scrnaseq",
        ui_message="🔍 Analyzing current plots..."
    )

    registry.register_tool(
        name="get_plot_details",
        description="Get detailed information about specific plots or analysis results",
        parameters={},
        executor=get_plot_details,
        analysis_type="scrnaseq",
        ui_message="📊 Retrieving plot details..."
    )