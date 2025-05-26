import streamlit as st
import scanpy as sc
import matplotlib.pyplot as plt
import numpy as np
from scipy import sparse
from modules.scrna_seq.tracking import status, log_shape
from modules.scrna_seq.clean import clean_invalid_values


from modules.scrna_seq.plot import plot_normalization_qc

def do_normalization():
    anndata = st.session_state.get("anndata")
    if anndata is None:
        st.error("⚠️ No AnnData loaded. Please complete previous steps first.")
        return

    if not st.session_state.get("normalized"):
        st.markdown("Running normalization...")
        try:
            log_shape("Before Normalization", anndata)
            sc.pp.normalize_total(anndata, target_sum=1e4)
            sc.pp.log1p(anndata)
            anndata = clean_invalid_values(anndata)
            st.session_state["anndata"] = anndata
            st.session_state["normalized"] = True
            log_shape("After Normalization", anndata)
        except Exception as e:
            st.error(f"Normalization failed: {e}")
            return

    st.success("✅ Normalization complete.")
    plot_normalization_qc(anndata)
