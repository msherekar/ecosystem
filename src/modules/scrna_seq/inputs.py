# show_inputs.py
import streamlit as st
from modules.scrna_seq.tracking import status, reset_steps
import scanpy as sc

def show_scrnaseq_inputs():
    """
    Step 1: Load Anndata object from the file path.
    Display summary of the currently loaded AnnData.
    Resets all downstream flags only once when a *new* AnnData is detected.
    """
    if st.session_state.input_h5ad_path is not None:
        try:
            anndata = sc.read_h5ad(st.session_state.input_h5ad_path)
            st.session_state.adata =anndata
            with st.expander(status("1. Input Summary"), expanded=True):
                st.success(f"Loaded AnnData: Cells={st.session_state.adata.n_obs}, Genes={st.session_state.adata.n_vars}")
                st.dataframe(st.session_state.adata.obs.head())

        except Exception as e:
            st.error(f"Failed to read h5ad file: {e}")
    '''
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
    '''
        



