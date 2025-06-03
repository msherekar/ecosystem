"""
RNA-seq specific tools for the agent system.
"""

import streamlit as st
from src.modules.agent.registry import registry
from src.modules.rna_seq.workflow import run_rnaseq_pipeline
from src.modules.agent.plot_analyzer import PlotAnalyzer

def get_rnaseq_insights():
    """Get detailed insights about current RNA-seq analysis state."""
    return {
        "success": True, 
        "message": registry.get_analysis_summary("rnaseq"),
        "summary": "Retrieved RNA-seq analysis insights"
    }

def analyze_rnaseq_plots():
    """Analyze currently displayed RNA-seq plots and provide biological insights."""
    insights = []
    
    # Check DESeq2 results
    if "deseq_results" in st.session_state:
        results_df = st.session_state["deseq_results"]
        insights.append(PlotAnalyzer.analyze_differential_expression(results_df))
        insights.append(PlotAnalyzer.analyze_volcano_plot(results_df))
    
    # Check GO enrichment results
    if "go_results" in st.session_state:
        go_results = st.session_state["go_results"]
        insights.append(PlotAnalyzer.analyze_go_enrichment(go_results))
    
    # Check data upload status
    if "rnaseq_counts_df" in st.session_state:
        counts_df = st.session_state["rnaseq_counts_df"]
        insights.append(f"RNA-seq dataset contains {counts_df.shape[0]:,} genes across {counts_df.shape[1]:,} samples.")
    
    message = " ".join(insights) if insights else "No RNA-seq analysis results available to analyze yet."
    
    return {
        "success": True,
        "message": message,
        "summary": "Analyzed RNA-seq plots and provided biological insights"
    }

def get_rnaseq_plot_details():
    """Get detailed information about RNA-seq plots and results."""
    details = []
    
    # Check data upload status
    if "rnaseq_counts_df" in st.session_state:
        counts_df = st.session_state["rnaseq_counts_df"]
        details.append(f"**Counts Data:** {counts_df.shape[0]:,} genes × {counts_df.shape[1]:,} samples")
    
    if "rnaseq_metadata_df" in st.session_state:
        metadata_df = st.session_state["rnaseq_metadata_df"]
        details.append(f"**Metadata:** {metadata_df.shape[0]:,} samples with {metadata_df.shape[1]:,} variables")
    
    # Check analysis results
    if "deseq_results" in st.session_state:
        results_df = st.session_state["deseq_results"]
        if "padj" in results_df.columns:
            sig_genes = len(results_df[results_df["padj"] < 0.05])
            details.append(f"**DESeq2 Results:** {sig_genes:,} significant genes (padj < 0.05)")
        
        if "log2FoldChange" in results_df.columns:
            max_lfc = results_df["log2FoldChange"].abs().max()
            details.append(f"**Fold Changes:** Maximum |log2FC| = {max_lfc:.2f}")
    
    if "go_results" in st.session_state:
        go_results = st.session_state["go_results"]
        details.append(f"**GO Enrichment:** {len(go_results):,} significant terms")
        
        if "source" in go_results.columns:
            sources = go_results["source"].value_counts()
            source_summary = ", ".join([f"{count} {source}" for source, count in sources.items()])
            details.append(f"**GO Categories:** {source_summary}")
    
    message = "\n".join(details) if details else "No RNA-seq analysis details available."
    
    return {
        "success": True,
        "message": message,
        "summary": "Retrieved detailed RNA-seq analysis information"
    }

def register_rnaseq_tools():
    registry.register_tool(
        name="run_rnaseq",
        description="Set up and run the RNA-seq analysis pipeline",
        parameters={},
        executor=run_rnaseq_pipeline,
        analysis_type="rnaseq",
        ui_message="✅ RNA-seq analysis activated. Please upload the required files."
    )
    
    registry.register_tool(
        name="get_rnaseq_insights",
        description="Get detailed insights about current RNA-seq analysis results",
        parameters={},
        executor=get_rnaseq_insights,
        analysis_type="rnaseq",
        ui_message="📊 Getting RNA-seq analysis insights..."
    )
    
    registry.register_tool(
        name="analyze_rnaseq_plots",
        description="Analyze currently displayed RNA-seq plots and provide biological insights",
        parameters={},
        executor=analyze_rnaseq_plots,
        analysis_type="rnaseq",
        ui_message="🔍 Analyzing RNA-seq plots..."
    )
    
    registry.register_tool(
        name="get_rnaseq_plot_details",
        description="Get detailed information about RNA-seq plots and analysis results",
        parameters={},
        executor=get_rnaseq_plot_details,
        analysis_type="rnaseq",
        ui_message="📊 Retrieving RNA-seq plot details..."
    )
    