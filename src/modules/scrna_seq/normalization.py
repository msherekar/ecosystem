import streamlit as st
import scanpy as sc
from src.modules.scrna_seq.tracking import _status, log_shape
from src.modules.scrna_seq.clean import clean_invalid_values

def do_normalization():
    with st.expander(_status("4. Normalization & Log1p")):
        if st.checkbox("▶️ Run Normalization", key="run_normalization") and not st.session_state.get("normalized"):
            adata = st.session_state["adata"]
            sc.pp.normalize_total(adata, target_sum=1e4)
            sc.pp.log1p(adata)
            adata = clean_invalid_values(adata)
            st.session_state["adata"] = adata
            st.session_state["normalized"] = True
            log_shape("Normalization", adata)
        elif st.session_state.get("normalized"):
            st.info("✅ Normalization already applied.")

        if st.button("♻️ Reset Normalization"):
            st.session_state["normalized"] = False