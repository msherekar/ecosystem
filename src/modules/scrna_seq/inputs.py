# show_inputs.py
import streamlit as st
from modules.scrna_seq.tracking import status, reset_steps
import scanpy as sc

import streamlit as st

def show_scrnaseq_inputs():
    anndata = st.session_state["anndata"]
    st.subheader("Summary of raw data")

    # Compact metrics
    col1, col2 = st.columns(2)
    col1.metric("Cells", f"{anndata.shape[0]:,}")
    col2.metric("Genes", f"{anndata.shape[1]:,}")

    # Gene features preview
    st.markdown("**Gene Features (first 10):**")
    st.code(", ".join(anndata.var_names[:10].tolist()) + " ...", language="text")

    # Metadata fields
    st.markdown("**Metadata:**")
    st.code("\n".join(anndata.obs.columns.tolist()), language="text")

    # Optional: set done flag
    st.session_state["input_summary_done"] = True






