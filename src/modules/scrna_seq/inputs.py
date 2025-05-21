import streamlit as st
from src.modules.scrna_seq.tracking import _status

def show_scrnaseq_inputs():
    with st.expander(_status("1. Input Summary")):
        adata = st.session_state.get("adata")
        if adata is not None:
            st.success(f"Cells: {adata.n_obs}, Genes: {adata.n_vars}")
            st.dataframe(adata.obs.head())
        else:
            st.warning("No AnnData object found.")
