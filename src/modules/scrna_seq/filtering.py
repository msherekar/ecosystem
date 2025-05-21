import streamlit as st
import scanpy as sc
from src.modules.scrna_seq.tracking import _status, log_shape

def do_filtering():
    with st.expander(_status("3. Filtering")):
        if st.checkbox("▶️ Run Filtering", key="run_filtering") and not st.session_state.get("filtered"):
            adata = st.session_state["adata"]
            sc.pp.filter_cells(adata, min_genes=200)
            sc.pp.filter_genes(adata, min_cells=3)
            st.session_state["adata"] = adata
            st.session_state["filtered"] = True
            log_shape("Filtering", adata)
        elif st.session_state.get("filtered"):
            st.info("✅ Filtering already applied.")

        if st.button("♻️ Reset Filtering"):
            st.session_state["filtered"] = False