import streamlit as st
import scanpy as sc
import matplotlib.pyplot as plt
import numpy as np
from scipy import sparse
from src.modules.scrna_seq.tracking import status, log_shape
from src.modules.scrna_seq.clean import clean_invalid_values
from src.modules.scrna_seq.plot import plot_normalization_qc

def do_normalization():
    anndata = st.session_state.get("anndata")
    if anndata is None:
        st.error("⚠️ No AnnData loaded. Please complete previous steps first.")
        return

    # Check if filtering has been completed first
    if not st.session_state.get("filtering_done", False):
        st.error("⚠️ Please complete Filtering step first. Normalization should be applied to filtered data.")
        return

    # Show current data dimensions
    st.info(f"📊 Current data: {anndata.shape[0]:,} cells × {anndata.shape[1]:,} genes")

    # Run normalization automatically if not already done
    if not st.session_state.get("normalization_done", False):
        try:
            st.info("Running normalization...")
            log_shape("Before Normalization", anndata)
            
            # Normalize to 10,000 reads per cell
            sc.pp.normalize_total(anndata, target_sum=1e4)
            
            # Log transform
            sc.pp.log1p(anndata)
            
            # Clean any invalid values that might have been introduced
            anndata = clean_invalid_values(anndata)
            
            # Update session state
            st.session_state["anndata"] = anndata
            st.session_state["normalization_done"] = True
            st.session_state["normalized"] = True  # Also set the flag that technique UI checks
            
            log_shape("After Normalization", anndata)
            st.success("✅ Normalization completed successfully!")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Normalization failed: {e}")
            return

    # Show results if normalization is done
    if st.session_state.get("normalization_done", False):
        st.success("✅ Normalization completed successfully!")
        plot_normalization_qc(anndata)
        
        # Option to reset normalization
        if st.button("♻️ Reset Normalization", key="reset_normalization"):
            st.session_state.pop("normalization_done", None)
            st.session_state.pop("normalized", None)
            st.warning("⚠️ Normalization reset. You'll need to re-run normalization.")
            st.rerun()
