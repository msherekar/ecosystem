import streamlit as st
import scanpy as sc
from src.modules.scrna_seq.tracking import _status, log_shape

def do_qc():
    with st.expander(_status("2. Quality Control")):
        if st.checkbox("▶️ Run QC", key="run_qc") and not st.session_state.get("qc_done"):
            adata = st.session_state["adata"]
            adata.var["mt"] = adata.var_names.str.startswith("MT-")
            sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], inplace=True)
            st.session_state["adata"] = adata
            st.session_state["qc_done"] = True
            log_shape("QC", adata)
        elif st.session_state.get("qc_done"):
            st.info("✅ QC already completed.")

        if st.button("♻️ Reset QC"):
            st.session_state["qc_done"] = False