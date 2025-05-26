import streamlit as st
import scanpy as sc
import matplotlib.pyplot as plt
from modules.scrna_seq.tracking import status, log_shape
import numpy as np

def do_qc():
    anndata = st.session_state["anndata"]

    if not st.session_state.get("qc_done"):
        st.markdown("Running quality control...")

        anndata.var["mt"] = anndata.var_names.str.upper().str.startswith("MT-")
        sc.pp.calculate_qc_metrics(anndata, qc_vars=["mt"], inplace=True)

        st.session_state["anndata"] = anndata
        st.session_state["qc_done"] = True

    st.success("✅ QC complete.")

    st.markdown("**QC Metrics Preview**")
    st.dataframe(anndata.obs[["n_genes_by_counts", "total_counts", "pct_counts_mt"]].head())

    st.markdown("**QC Distributions**")
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    metrics = ["n_genes_by_counts", "total_counts", "pct_counts_mt"]
    for ax, metric in zip(axes, metrics):
        ax.hist(anndata.obs[metric], bins=50)
        ax.set_title(metric)
        ax.set_xlabel(metric)
        ax.set_ylabel("Cell Count")
    st.pyplot(fig)
