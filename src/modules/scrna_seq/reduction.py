import streamlit as st
import scanpy as sc
import numpy as np
import scipy.sparse as sp
from modules.scrna_seq.clean import clean_invalid_values
from modules.scrna_seq.plot import (
    plot_hvg_trend, plot_pca_variance,
    plot_pca_scatter, plot_pca_loadings,
    plot_scaled_distribution
)

def perform_dimensionality_reduction():
    """
    Step: Identify highly variable genes and run PCA.
    - Cleans invalid values
    - Selects HVGs
    - Scales and runs PCA
    - Shows diagnostic plots
    """
    adata = st.session_state.get("anndata")
    if adata is None:
        st.error("⚠️ No AnnData loaded. Please upload scRNA-seq data first.")
        return

    if not st.session_state.get("dimred_done"):
        try:
            st.markdown("Running PCA on highly variable genes...")

            # Clean inf/nan values
            if sp.issparse(adata.X):
                data = adata.X.data
                data[np.isinf(data)] = np.nan
                adata.X.data = np.nan_to_num(data, nan=0.0)
            else:
                X = adata.X
                X[np.isinf(X)] = np.nan
                adata.X = np.nan_to_num(X)

            adata = clean_invalid_values(adata)

            # Identify highly variable genes
            try:
                sc.pp.highly_variable_genes(adata, flavor='seurat_v3')
            except:
                sc.pp.highly_variable_genes(adata, flavor='seurat')

            # If needed, fallback to manual mean/dispersion
            if 'hvg' not in adata.uns:
                Xmat = adata.X.toarray() if sp.issparse(adata.X) else adata.X
                means = np.mean(Xmat, axis=0)
                vars_ = np.var(Xmat, axis=0)
                dispersion = vars_ / (means + 1e-6)
                adata.var['means'] = means
                adata.var['dispersions_norm'] = dispersion

            hvg_count = adata.var.get('highly_variable', np.array([])).sum()
            st.info(f"📊 Found {hvg_count} highly variable genes.")

            # Filter to HVGs
            adata = adata[:, adata.var.get('highly_variable', False)]
            adata = clean_invalid_values(adata)

            # Scale
            try:
                sc.pp.scale(adata, max_value=10)
            except:
                Xmat = adata.X.toarray() if sp.issparse(adata.X) else adata.X
                mean = np.mean(Xmat, axis=0)
                std = np.std(Xmat, axis=0)
                std[std == 0] = 1
                Xs = (Xmat - mean) / std
                Xs = np.clip(Xs, -10, 10)
                adata.X = Xs

            # Run PCA
            sc.tl.pca(adata, svd_solver='arpack')

            # Store results
            st.session_state["anndata"] = adata
            st.session_state["dimred_done"] = True
            st.success("✅ PCA completed successfully!")

        except Exception as e:
            st.error(f"PCA step failed: {e}")
            return

    else:
        st.info("✅ PCA already completed.")

    # === Plots ===
    st.markdown("### 🧪 PCA Diagnostics")
    st.markdown("**1. Highly Variable Genes Trend**")
    plot_hvg_trend(adata)

    st.markdown("**2–3. Variance Ratio and Cumulative Variance**")
    plot_pca_variance(adata)

    st.markdown("**4. PCA Scatter (PC1 vs PC2)**")
    plot_pca_scatter(adata)

    st.markdown("**5. PCA Loadings Heatmap**")
    plot_pca_loadings(adata)

    st.markdown("**6. Distribution of Scaled Expression Values**")
    plot_scaled_distribution(adata)
