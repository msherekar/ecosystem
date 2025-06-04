import streamlit as st
import scanpy as sc
import matplotlib.pyplot as plt
import numpy as np
from scipy import sparse
from modules.scrna_seq.tracking import status, log_shape


def do_filtering():
    """
    Step 3: Filter cells/genes in the AnnData object.
    - Uses a form for input parameters; filters apply only on explicit submit.
    - Automatically displays post-filtering distributions of gene counts and total counts per cell.
    - Does NOT clear QC state, so QC plots remain visible.
    """
    with st.expander(status("3. Filtering"), expanded=True):
        adata = st.session_state.get("adata")
        if adata is None:
            st.error("⚠️ No AnnData loaded. Please complete the Input and QC steps first.")
            return

        # Filtering parameters form
        with st.form(key="filter_form"):
            min_genes = st.number_input(
                "Minimum genes per cell",
                min_value=0,
                value=200,
                step=1,
                help="Cells with fewer genes will be removed.",
                key="min_genes_input"
            )
            min_cells = st.number_input(
                "Minimum cells per gene",
                min_value=0,
                value=3,
                step=1,
                help="Genes present in fewer cells will be removed.",
                key="min_cells_input"
            )
            submitted = st.form_submit_button("▶️ Run Filtering")

        # Execute filtering only on explicit submit
        if submitted and not st.session_state.get("filtered", False):
            try:
                log_shape("Before Filtering", adata)

                # Apply cell and gene filters
                sc.pp.filter_cells(adata, min_genes=min_genes)
                sc.pp.filter_genes(adata, min_cells=min_cells)

                # Save updated AnnData and flag
                st.session_state["adata"] = adata
                st.session_state["filtered"] = True

                log_shape("After Filtering", adata)
            except Exception as e:
                st.error(f"Filtering failed: {e}")

        # Post-filtering distributions
        if st.session_state.get("filtered", False):
            st.info("✅ Filtering applied.")

            # Compute metrics if absent
            X = adata.X
            if sparse.issparse(X):
                mat = X.toarray()
            else:
                mat = X
            # Genes per cell and total counts
            adata.obs["n_genes_by_counts"] = np.sum(mat > 0, axis=1).flatten()
            adata.obs["total_counts"] = np.sum(mat, axis=1).flatten()

            # Plot distributions
            metrics = ["n_genes_by_counts", "total_counts"]
            fig, axes = plt.subplots(1, len(metrics), figsize=(5 * len(metrics), 4))
            if isinstance(axes, np.ndarray):
                axes_list = axes.flatten().tolist()
            elif hasattr(axes, 'hist'):
                axes_list = [axes]
            else:
                axes_list = list(axes)

            for ax, metric in zip(axes_list, metrics):
                values = adata.obs[metric].dropna().values
                ax.hist(values, bins=50)
                ax.set_title(metric)
                ax.set_xlabel(metric)
                ax.set_ylabel("Count")

            fig.tight_layout()
            st.pyplot(fig)

        # Reset filtering state
        if st.button("♻️ Reset Filtering", key="reset_filtering"):
            st.session_state.pop("filtered", None)
