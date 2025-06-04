import streamlit as st
import scanpy as sc
import matplotlib.pyplot as plt
from modules.scrna_seq.tracking import status, log_shape
import numpy as np

def do_qc():
    """
    Step 2: Compute and inspect QC metrics.
    - Runs only when you click ▶️ Run QC.
    - Automatically displays QC metrics preview and distributions once done.
    - Track shape and status with log_shape.
    """
    with st.expander(status("2. Quality Control"), expanded=True):
        adata = st.session_state.get("adata")
        if adata is None:
            st.error("⚠️ No AnnData loaded. Please upload via the left panel.")
            return

        # Track QC completion
        qc_done = st.session_state.get("qc_done", False)

        # Define expected QC columns
        qc_cols = ["n_genes_by_counts", "total_counts", "pct_counts_mt"]

        # Run QC only on button press
        if not qc_done:
            if st.button("▶️ Run QC", key="run_qc"):
                try:
                    # Identify mitochondrial genes
                    adata.var["mt"] = adata.var_names.str.upper().str.startswith("MT-")
                    # Calculate QC metrics
                    sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], inplace=True)
                    # Save updated adata and flag
                    st.session_state["adata"] = adata
                    st.session_state["qc_done"] = True
                    log_shape("QC metric calculation", adata)
                except Exception as e:
                    st.error(f"QC failed: {e}")
        else:
            st.info("✅ QC already completed.")

        # After QC, display preview and distributions
        # Display metrics and distributions once done
        if st.session_state.get("qc_done", False):
            available = [c for c in qc_cols if c in adata.obs.columns]
            if available:
                st.markdown("**QC Metrics Preview**")
                st.dataframe(adata.obs[available].head())

                st.markdown("**QC Metrics Distributions**")
                fig, axes = plt.subplots(1, len(available), figsize=(5 * len(available), 4))
                # Normalize axes
                if isinstance(axes, np.ndarray):
                    axes_list = axes.flatten().tolist()
                elif not isinstance(axes, (list, tuple)):
                    axes_list = [axes]
                else:
                    axes_list = list(axes)
                for ax, col in zip(axes_list, available):
                    values = adata.obs[col].dropna().values
                    ax.hist(values, bins=50)
                    ax.set_title(col)
                    ax.set_xlabel(col)
                    ax.set_ylabel("Count")
                fig.tight_layout()
                st.pyplot(fig)
            else:
                st.warning("⚠️ QC metrics not found in AnnData.obs. Please verify QC calculation.")

        # Reset QC state
        if st.button("♻️ Reset QC", key="reset_qc"):
            st.session_state.pop("qc_done", None)

