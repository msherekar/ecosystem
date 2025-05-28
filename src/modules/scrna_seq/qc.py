import streamlit as st
import scanpy as sc
import matplotlib.pyplot as plt
from src.modules.scrna_seq.tracking import status, log_shape
import numpy as np

from src.modules.scrna_seq.plot import plot_qc_metrics

def do_qc():
    anndata = st.session_state["anndata"]

    if not st.session_state.get("qc_done"):
        # st.markdown("Running quality control...")  # Removed for cleaner UI

        anndata.var["mt"] = anndata.var_names.str.upper().str.startswith("MT-")
        sc.pp.calculate_qc_metrics(anndata, qc_vars=["mt"], inplace=True)

        st.session_state["anndata"] = anndata
        st.session_state["qc_done"] = True

    # st.success("✅ QC complete.")  # Removed for cleaner UI
    plot_qc_metrics(anndata)

