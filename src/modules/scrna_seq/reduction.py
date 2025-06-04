import streamlit as st
import scanpy as sc
import numpy as np
import matplotlib.pyplot as plt
import scipy.sparse as sp
from modules.scrna_seq.tracking import status, log_shape
from modules.scrna_seq.clean import clean_invalid_values

def perform_dimensionality_reduction():
    """
    Step 5: Identify highly variable genes and compute PCA.
    - Handles infinities/NaNs, selects HVGs, scales data, and runs PCA.
    - Automatically displays diagnostic plots:
        1. Mean-variance trend for HVGs
        2. Explained variance ratio (scree plot)
        3. Cumulative variance curve
        4. PC1-PC2 scatter
        5. Top gene loadings heatmap
        6. Distribution of scaled expression values
    """
    with st.expander(status("5. PCA & Variable Genes"), expanded=True):
        adata = st.session_state.get("adata")
        if adata is None:
            st.error("⚠️ No AnnData loaded. Please complete normalization first.")
            return

        pca_done = st.session_state.get("pca_done", False)
        if not pca_done:
            if st.button("▶️ Run PCA", key="run_pca"):
                try:
                    # Clean inf/nan values in X
                    if sp.issparse(adata.X):
                        data = adata.X.data
                        data[np.isinf(data)] = np.nan
                        adata.X.data = np.nan_to_num(data, nan=0.0)
                    else:
                        X = adata.X
                        X[np.isinf(X)] = np.nan
                        adata.X = np.nan_to_num(X)
                    adata = clean_invalid_values(adata)

                    # Highly variable genes
                    try:
                        sc.pp.highly_variable_genes(adata, flavor='seurat_v3')
                    except:
                        sc.pp.highly_variable_genes(adata, flavor='seurat')

                    # Fallback: compute means & dispersion if uns missing
                    if 'hvg' not in adata.uns:
                        Xmat = adata.X.toarray() if sp.issparse(adata.X) else adata.X
                        means = np.mean(Xmat, axis=0)
                        vars_ = np.var(Xmat, axis=0)
                        dispersion = vars_ / (means + 1e-6)
                        adata.var['means'] = means
                        adata.var['dispersions_norm'] = dispersion

                    n_hvg = adata.var.get('highly_variable', np.array([])).sum()
                    st.info(f"Found {n_hvg} highly variable genes.")

                    # Filter to HVGs
                    adata = adata[:, adata.var.get('highly_variable', False)]
                    adata = clean_invalid_values(adata)

                    # Scale data
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

                    # PCA
                    sc.tl.pca(adata, svd_solver='arpack')

                    # Save state
                    st.session_state['adata'] = adata
                    st.session_state['pca_done'] = True
                    log_shape("PCA", adata)
                    st.success("✅ PCA completed successfully!")
                except Exception as e:
                    st.error(f"PCA step failed: {e}")
                    return
        else:
            st.info("✅ PCA already completed.")

        # Diagnostic plots once PCA is done
        if st.session_state.get('pca_done', False):
            # 1. Mean-variance trend
            st.markdown("**1. Highly Variable Genes: Mean-Variance Trend**")
            try:
                sc.pl.highly_variable_genes(adata, show=False)
                st.pyplot(plt.gcf())
            except KeyError:
                if 'means' in adata.var.columns and 'dispersions_norm' in adata.var.columns:
                    fig, ax = plt.subplots(figsize=(6, 4))
                    ax.scatter(adata.var['means'], adata.var['dispersions_norm'], s=5)
                    ax.set_xscale('log')
                    ax.set_yscale('log')
                    ax.set_xlabel('Mean expression')
                    ax.set_ylabel('Normalized dispersion')
                    ax.set_title('HVG Mean-Variance Trend')
                    fig.tight_layout()
                    st.pyplot(fig)
                else:
                    st.warning("⚠️ Cannot plot HVG trend: missing mean/dispersion metrics.")

            # 2. Scree plot
            st.markdown("**2. PCA Explained Variance Ratio (Scree Plot)**")
            if 'pca' in adata.uns:
                sc.pl.pca_variance_ratio(adata, log=True, show=False)
                st.pyplot(plt.gcf())
            else:
                st.warning("⚠️ PCA results missing: cannot plot variance ratio.")

            # 3. Cumulative variance
            st.markdown("**3. Cumulative Explained Variance**")
            if 'pca' in adata.uns:
                evr = adata.uns['pca']['variance_ratio']
                cumvar = np.cumsum(evr)
                fig3, ax3 = plt.subplots(figsize=(6, 4))
                ax3.plot(np.arange(1, len(cumvar) + 1), cumvar, '-o')
                ax3.set_xlabel('PC')
                ax3.set_ylabel('Cumulative Variance')
                ax3.set_title('Cumulative Explained Variance')
                fig3.tight_layout()
                st.pyplot(fig3)
            else:
                st.warning("⚠️ PCA results missing: cannot plot cumulative variance.")

            # 4. PC1 vs PC2 scatter
            st.markdown("**4. PCA Scatter (PC1 vs PC2)**")
            if 'X_pca' in adata.obsm:
                sc.pl.pca(adata, color=['total_counts', 'n_genes_by_counts'], show=False)
                st.pyplot(plt.gcf())
            else:
                st.warning("⚠️ PCA embedding missing: cannot plot scatter.")

            # 5. Top gene loadings heatmap
            st.markdown("**5. Top Gene Loadings per PC**")
            try:
                sc.pl.pca_loadings(adata, components=[1,2,3], show=False)
                st.pyplot(plt.gcf())
            except Exception as e:
                st.warning(f"Cannot plot PCA loadings: {e}")

            # 6. Scaled expression distribution
            st.markdown("**6. Distribution of Scaled Expression Values**")
            Xmat = adata.X.toarray() if sp.issparse(adata.X) else adata.X
            fig4, ax4 = plt.subplots(figsize=(6, 4))
            ax4.hist(Xmat.flatten(), bins=100)
            ax4.set_xlim(-5, 5)
            ax4.set_title('Scaled Expression Distribution')
            ax4.set_xlabel('Expression value')
            ax4.set_ylabel('Frequency')
            fig4.tight_layout()
            st.pyplot(fig4)

        # Reset PCA
        if st.button("♻️ Reset PCA", key="reset_pca"):
            st.session_state.pop('pca_done', None)
