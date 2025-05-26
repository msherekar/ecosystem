import streamlit as st
import scanpy as sc
import matplotlib.pyplot as plt
import numpy as np
from scipy import sparse
from modules.scrna_seq.tracking import status, log_shape
from modules.scrna_seq.plot import plot_filtering_qc

def do_filtering():
    anndata = st.session_state.get("anndata")
    if anndata is None:
        st.error("⚠️ No AnnData loaded. Please complete the Input and QC steps first.")
        return

    with st.form(key="filter_form"):
        min_genes = st.number_input("Minimum genes per cell", min_value=0, value=200, step=1, key="min_genes_input")
        min_cells = st.number_input("Minimum cells per gene", min_value=0, value=3, step=1, key="min_cells_input")
        submitted = st.form_submit_button("▶️ Run Filtering")

    if submitted and not st.session_state.get("filtered", False):
        try:
            log_shape("Before Filtering", anndata)
            sc.pp.filter_cells(anndata, min_genes=min_genes)
            sc.pp.filter_genes(anndata, min_cells=min_cells)
            st.session_state["anndata"] = anndata
            st.session_state["filtered"] = True
            st.session_state["filtering_done"] = True
            log_shape("After Filtering", anndata)
        except Exception as e:
            st.error(f"Filtering failed: {e}")

    if st.session_state.get("filtered", False):
        st.info("✅ Filtering applied.")
        plot_filtering_qc(anndata)

    if st.button("♻️ Reset Filtering", key="reset_filtering"):
        st.session_state.pop("filtered", None)
        st.session_state.pop("filtering_done", None)
