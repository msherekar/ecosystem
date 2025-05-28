import streamlit as st
import scanpy as sc
import numpy as np
import scipy.sparse as sp
from src.modules.scrna_seq.clean import clean_invalid_values
from src.modules.scrna_seq.plot import (
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
        st.error("⚠️ No AnnData loaded. Please complete previous steps first.")
        return

    # Check if normalization has been completed first
    if not st.session_state.get("normalization_done", False):
        st.error("⚠️ Please complete Normalization step first. PCA should be applied to normalized data.")
        return

    # Show current data dimensions
    st.info(f"📊 Current data: {adata.shape[0]:,} cells × {adata.shape[1]:,} genes")

    # Run PCA automatically if not already done
    if not st.session_state.get("dimred_done", False):
        try:
            st.info("Running PCA on highly variable genes...")

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
                try:
                    sc.pp.highly_variable_genes(adata, flavor='seurat')
                except:
                    # Manual fallback if both fail
                    st.warning("Using manual HVG calculation...")
                    Xmat = adata.X.toarray() if sp.issparse(adata.X) else adata.X
                    means = np.mean(Xmat, axis=0)
                    vars_ = np.var(Xmat, axis=0)
                    dispersion = vars_ / (means + 1e-6)
                    
                    # Set HVG based on top dispersions
                    top_genes = np.argsort(dispersion)[-2000:]  # Top 2000 genes
                    highly_variable = np.zeros(len(adata.var), dtype=bool)
                    highly_variable[top_genes] = True
                    
                    adata.var['highly_variable'] = highly_variable
                    adata.var['means'] = means
                    adata.var['dispersions_norm'] = dispersion

            # Ensure means and dispersions are available for plotting
            if 'means' not in adata.var.columns or 'dispersions_norm' not in adata.var.columns:
                Xmat = adata.X.toarray() if sp.issparse(adata.X) else adata.X
                adata.var['means'] = np.mean(Xmat, axis=0)
                vars_ = np.var(Xmat, axis=0)
                adata.var['dispersions_norm'] = vars_ / (adata.var['means'] + 1e-6)

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

            # Calculate appropriate n_components for small datasets
            n_samples, n_features = adata.shape
            max_components = min(n_samples, n_features) - 1
            n_components = min(50, max_components)  # Use 50 or less if dataset is small
            
            # Run PCA with dynamic components
            if n_components < 10:
                # For very small datasets, use full SVD solver
                sc.tl.pca(adata, n_comps=n_components, svd_solver='full')
            else:
                # For larger datasets, use arpack
                sc.tl.pca(adata, n_comps=n_components, svd_solver='arpack')
            
            # Ensure PCA loadings are available in expected location
            if 'PCs' in adata.varm and 'pca_loadings' not in adata.varm:
                adata.varm['pca_loadings'] = adata.varm['PCs']

            # Store results
            st.session_state["anndata"] = adata
            st.session_state["dimred_done"] = True
            st.session_state["pca_done"] = True  # Also set for backward compatibility
            st.success("✅ PCA completed successfully!")
            st.rerun()

        except Exception as e:
            st.error(f"❌ PCA step failed: {e}")
            return

    # Show results if dimred is done
    if st.session_state.get("dimred_done", False):
        st.success("✅ PCA completed successfully!")
        
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
        
        # Option to reset dimred
        if st.button("♻️ Reset PCA", key="reset_dimred"):
            st.session_state.pop("dimred_done", None)
            st.session_state.pop("pca_done", None)
            st.warning("⚠️ PCA reset. You'll need to re-run dimensionality reduction.")
            st.rerun()
