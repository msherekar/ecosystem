import streamlit as st
import scanpy as sc
import pandas as pd
import numpy as np
import scipy.sparse as sp
from src.modules.scrna_seq.tracking import _status, log_shape
from src.modules.scrna_seq.enrichment import run_go_enrichment
from src.modules.scrna_seq.clean import clean_invalid_values
from src.modules.scrna_seq.inputs import show_scrnaseq_inputs
from src.modules.scrna_seq.qc import do_qc
from src.modules.scrna_seq.filtering import do_filtering
from src.modules.scrna_seq.normalization import do_normalization
from src.modules.scrna_seq.reduction import perform_dimensionality_reduction
from src.modules.scrna_seq.clustering import perform_clustering
from src.modules.scrna_seq.visualization import create_visualization
from src.modules.scrna_seq.dea import run_differential_expression
from src.modules.scrna_seq.export import export_outputs
from src.modules.scrna_seq.enrichment import run_pathway_enrichment
from src.modules.scrna_seq.analysis import run_cell_cycle_analysis
from src.modules.scrna_seq.identification import run_marker_gene_identification
from src.modules.scrna_seq.analysis import run_trajectory_analysis
from src.modules.scrna_seq.networks import run_single_cell_networks
from src.modules.scrna_seq.ml import apply_ML
from src.modules.scrna_seq.tuning import perform_fine_tuning

def run_scrnaseq_pipeline():
    if "adata" not in st.session_state:
        st.warning("⚠️ No AnnData object found. Please upload your scRNA-seq file.")
        return

    show_scrnaseq_inputs()
    do_qc()
    do_filtering()
    do_normalization()
    perform_dimensionality_reduction()
    perform_clustering()
    create_visualization()
    run_differential_expression()
    export_outputs()  
    run_go_enrichment()
    run_pathway_enrichment()
    run_cell_cycle_analysis()
    run_marker_gene_identification()
    run_trajectory_analysis()
    run_single_cell_networks()
    apply_ML()
    perform_fine_tuning()
