import streamlit as st
import scanpy as sc
import matplotlib.pyplot as plt
import numpy as np
from scipy import sparse
from modules.scrna_seq.tracking import status, log_shape
from modules.scrna_seq.clean import clean_invalid_values


def do_normalization():
    """
    Step 4: Normalize total counts and apply log1p transform.
    - Runs only when you click ▶️ Run Normalization.
    - Logs dataset shape before and after normalization.
    - Automatically displays:
        - Histogram of total counts per cell.
        - Histogram of number of genes per cell.
        - Histogram of total counts per gene.
    """
    with st.expander(status("4. Normalization & Log1p"), expanded=True):
        adata = st.session_state.get("adata")
        if adata is None:
            st.error("⚠️ No AnnData loaded. Please complete previous steps first.")
            return

        norm_done = st.session_state.get("normalized", False)

        # Trigger normalization once
        if not norm_done:
            if st.button("▶️ Run Normalization", key="run_normalization"):
                try:
                    log_shape("Before Normalization", adata)
                    sc.pp.normalize_total(adata, target_sum=1e4)
                    sc.pp.log1p(adata)
                    adata = clean_invalid_values(adata)
                    st.session_state["adata"] = adata
                    st.session_state["normalized"] = True
                    log_shape("After Normalization", adata)
                    norm_done = True
                except Exception as e:
                    st.error(f"Normalization failed: {e}")
        else:
            st.info("✅ Normalization already applied.")

        # Auto-display plots once normalized
        if norm_done:
            # Compute per-cell metrics
            X = adata.X
            mat = X.toarray() if sparse.issparse(X) else X
            adata.obs["total_counts"] = np.sum(mat, axis=1).flatten()
            adata.obs["n_genes_by_counts"] = np.sum(mat > 0, axis=1).flatten()
            # Compute per-gene metrics
            var_counts = np.sum(mat, axis=0).flatten()

            # Plot per-cell metrics
            st.markdown("**Per-cell Metrics**")
            fig, axes = plt.subplots(1, 2, figsize=(12, 4))
            # Normalize axes iterable
            if isinstance(axes, np.ndarray):
                axes_list = axes.flatten().tolist()
            elif not isinstance(axes, (list, tuple)):
                axes_list = [axes]
            else:
                axes_list = list(axes)
            metrics = ["total_counts", "n_genes_by_counts"]
            for ax, metric in zip(axes_list, metrics):
                values = adata.obs[metric].dropna().values
                ax.hist(values, bins=50)
                ax.set_title(metric)
                ax.set_xlabel(metric)
                ax.set_ylabel("Count")
            fig.tight_layout()
            st.pyplot(fig)

            # Plot per-gene total counts
            st.markdown("**Per-gene Total Counts**")
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            ax2.hist(var_counts, bins=50)
            ax2.set_title("Total counts per gene")
            ax2.set_xlabel("Total counts")
            ax2.set_ylabel("Number of genes")
            fig2.tight_layout()
            st.pyplot(fig2)

        # Reset normalization state
        if st.button("♻️ Reset Normalization", key="reset_normalization"):
            st.session_state.pop("normalized", None)
