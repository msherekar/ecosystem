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

SCRNA_STEP_ORDER = [
    ("input_summary", show_scrnaseq_inputs, "📁 Input Summary", "input_summary_done"),
    ("qc", do_qc, "🧼 Quality Control", "qc_done"),
    ("filtering", do_filtering, "🧹 Filtering", "filtering_done"),
    ("normalization", do_normalization, "⚖️ Normalization", "normalization_done"),
    ("dimred", perform_dimensionality_reduction, "🔻 Dimensionality Reduction", "dimred_done"),
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
        return

    # Init state
    if "scrna_current_step" not in st.session_state:
        st.session_state.scrna_current_step = "input_summary"

    # Get current step info
    current_step = st.session_state.scrna_current_step
    for i, (step_key, step_fn, title, done_flag) in enumerate(SCRNA_STEP_ORDER):
        if current_step == step_key:
            st.markdown(f"### {title}")
            step_fn()

            # Check if step is done
            if st.session_state.get(done_flag):
                if i + 1 < len(SCRNA_STEP_ORDER):
                    st.session_state.scrna_current_step = SCRNA_STEP_ORDER[i + 1][0]
                    st.experimental_rerun()
                else:
                    st.success("🎉 All steps complete!")
            break

