# show_inputs.py
import streamlit as st
from modules.scrna_seq.tracking import status, reset_steps
import scanpy as sc

def show_scrnaseq_inputs():
    """
    Step 1: Display summary of the currently loaded AnnData.
    Resets all downstream flags only once when a *new* AnnData is detected.
    """
    with st.expander(status("1. Input Summary"), expanded=True):
        adata = st.session_state.get("adata")
        if adata is None:
            st.warning("⚠️ No AnnData object loaded. Please upload your .h5ad via the left panel.")
            return

        # Only reset when a *different* dataset arrives
        sig = (adata.n_obs, adata.n_vars)
        if st.session_state.get("adata_signature") != sig:
            reset_steps()
            st.session_state["adata_signature"] = sig

        st.success(f"Loaded AnnData: Cells={adata.n_obs}, Genes={adata.n_vars}")
        st.dataframe(adata.obs.head())



