import streamlit as st
import scanpy as sc
import pandas as pd
import numpy as np
import scipy.sparse as sp
from modules.scrna_seq.tracking import status, log_shape
from modules.scrna_seq.enrichment import run_go_enrichment
from modules.scrna_seq.clean import clean_invalid_values
from modules.scrna_seq.inputs import show_scrnaseq_inputs
from modules.scrna_seq.qc import do_qc
from modules.scrna_seq.filtering import do_filtering
from modules.scrna_seq.normalization import do_normalization
from modules.scrna_seq.reduction import perform_dimensionality_reduction
from modules.scrna_seq.clustering import perform_clustering
from modules.scrna_seq.visualization import create_visualization
from modules.scrna_seq.dea import run_differential_expression
from modules.scrna_seq.export import export_outputs
from modules.scrna_seq.enrichment import run_pathway_enrichment
from modules.scrna_seq.analysis import run_cell_cycle_analysis
from modules.scrna_seq.identification import run_marker_gene_identification
from modules.scrna_seq.analysis import run_trajectory_analysis
from modules.scrna_seq.networks import run_single_cell_networks
from modules.scrna_seq.ml import apply_ML
from modules.scrna_seq.tuning import perform_fine_tuning
from modules.agent.brain import ask_agent
from modules.agent.plot_analyzer import get_step_summary

SCRNA_STEP_ORDER = [
    ("input_summary", show_scrnaseq_inputs, "📊 Data Summary", "input_summary_done"),
    ("qc", do_qc, "🧼 Quality Control", "qc_done"),
    ("filtering", do_filtering, "🧹 Filtering", "filtering_done"),
    ("normalization", do_normalization, "⚖️ Normalization", "normalization_done"),
    ("dimred", perform_dimensionality_reduction, "Dimensionality Reduction", "dimred_done"),
    ("clustering", perform_clustering, "🔗 Clustering", "clustering_done"),
    ("viz", create_visualization, "🧬 Visualization", "viz_done"),
    ("dea", lambda: (run_differential_expression(), export_outputs()), "🆚 Differential Expression", "dea_done"),
    ("enrichment", lambda: (run_go_enrichment(), run_pathway_enrichment()), "🔬 Enrichment", "enrichment_done"),
    ("markers", lambda: (run_cell_cycle_analysis(), run_marker_gene_identification()), "⏳ Marker Genes & Cell Cycle", "markers_done"),
    ("trajectory", run_trajectory_analysis, "🧭 Trajectory", "trajectory_done"),
    ("ml", lambda: (run_single_cell_networks(), apply_ML(), perform_fine_tuning()), "🌐 ML & Networks", "ml_done"),
]


def run_scrnaseq_pipeline():
    
    
    if "anndata" not in st.session_state or st.session_state.anndata is None:
        st.info("🔬 Please upload your `.h5ad` or 10x files to begin.")
        return {
            "success": False,
            "message": "No scRNA-seq data uploaded. Please upload .h5ad or 10x files first.",
            "summary": "scRNA-seq pipeline requires data upload"
        }

    if "scrna_current_step" not in st.session_state:
        st.session_state.scrna_current_step = "input_summary"

    current_step = st.session_state.scrna_current_step

    for i, (step_key, step_fn, step_title, done_flag) in enumerate(SCRNA_STEP_ORDER):
        if current_step == step_key:
            # st.markdown(f"### {step_title}")  # Removed for cleaner UI
            step_fn()

            # Check if step is completed and show continue button
            if st.session_state.get(done_flag):
                # Generate automatic plot analysis summary only once per step completion
                if st.session_state.get("scrna_last_completed_step") != step_key:
                    st.session_state.scrna_last_completed_step = step_key
                    
                    # Generate automatic plot analysis summary
                    anndata = st.session_state.get("anndata")
                    auto_summary = get_step_summary(step_key, anndata=anndata)
                    
                    # Store the summary for later reference
                    st.session_state.setdefault("scrna_step_summaries", {})[step_key] = auto_summary

                    # Get additional feedback from agent
                    # Find the next step name for better agent guidance
                    next_step_name = "the next step"
                    if i + 1 < len(SCRNA_STEP_ORDER):
                        next_step_name = SCRNA_STEP_ORDER[i + 1][2]  # Get the step title
                    
                    agent_summary = ask_agent(
                        f"The user has completed the step '{step_key}' in scRNA-seq. "
                        f"The automatic analysis shows: {auto_summary}. "
                        f"The next step in the pipeline is: {next_step_name}. "
                        f"Reply in 2-3 lines. Be concise. Provide high-level feedback and suggest moving to {next_step_name}."
                    )
                    summary_text = agent_summary.get("response", "✅ Step completed.")
                    st.session_state.setdefault("scrna_agent_thoughts", {})[step_key] = summary_text
                    st.session_state.messages.append({"role": "assistant", "content": summary_text})
                
                # Always show continue button if step is done and there's a next step
                if i + 1 < len(SCRNA_STEP_ORDER):
                    next_step_key, _, next_step_title, _ = SCRNA_STEP_ORDER[i + 1]
                    if st.button(f"✅ Continue to {next_step_title}", key=f"continue_step_{step_key}"):
                        st.session_state.scrna_current_step = next_step_key
                        st.rerun()
                else:
                    st.success("🎉 All steps complete!")
                
            break

    # Return success result
    return {
        "success": True,
        "message": f"scRNA-seq pipeline is running. Current step: {current_step}",
        "summary": f"Executed scRNA-seq pipeline step: {current_step}"
    }


