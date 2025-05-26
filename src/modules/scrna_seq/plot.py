# modules/scrna_seq/plot.py
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import scanpy as sc
import scipy.sparse as sp




def plot_normalization_qc(anndata):
    """Show cell-wise and gene-wise histograms after normalization."""
    X = anndata.X
    mat = X.toarray() if sparse.issparse(X) else X

    # Cell-level metrics
    anndata.obs["total_counts"] = np.sum(mat, axis=1).flatten()
    anndata.obs["n_genes_by_counts"] = np.sum(mat > 0, axis=1).flatten()

    # Gene-level metric
    var_counts = np.sum(mat, axis=0).flatten()

    # 📊 Per-cell metrics
    st.markdown("**Per-cell Metrics**")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    metrics = ["total_counts", "n_genes_by_counts"]

    for ax, metric in zip(axes, metrics):
        values = anndata.obs[metric].dropna().values
        ax.hist(values, bins=50)
        ax.set_title(metric)
        ax.set_xlabel(metric)
        ax.set_ylabel("Cell count")

    fig.tight_layout()
    st.pyplot(fig)

    # 📊 Per-gene metric
    st.markdown("**Per-gene Total Counts**")
    fig2, ax2 = plt.subplots(figsize=(6, 4))
    ax2.hist(var_counts, bins=50)
    ax2.set_title("Total counts per gene")
    ax2.set_xlabel("Total counts")
    ax2.set_ylabel("Gene count")
    fig2.tight_layout()
    st.pyplot(fig2)

def plot_hvg_trend(adata):
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

def plot_pca_variance(adata):
    if 'pca' in adata.uns:
        sc.pl.pca_variance_ratio(adata, log=True, show=False)
        st.pyplot(plt.gcf())

        evr = adata.uns['pca']['variance_ratio']
        cumvar = np.cumsum(evr)
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(np.arange(1, len(cumvar) + 1), cumvar, '-o')
        ax.set_xlabel('PC')
        ax.set_ylabel('Cumulative Variance')
        ax.set_title('Cumulative Explained Variance')
        fig.tight_layout()
        st.pyplot(fig)
    else:
        st.warning("⚠️ PCA results missing: cannot plot variance ratio.")

def plot_pca_scatter(adata):
    if 'X_pca' in adata.obsm:
        sc.pl.pca(adata, color=['total_counts', 'n_genes_by_counts'], show=False)
        st.pyplot(plt.gcf())

def plot_pca_loadings(adata):
    try:
        sc.pl.pca_loadings(adata, components=[1,2,3], show=False)
        st.pyplot(plt.gcf())
    except Exception as e:
        st.warning(f"Cannot plot PCA loadings: {e}")

def plot_scaled_distribution(adata):
    Xmat = adata.X.toarray() if sp.issparse(adata.X) else adata.X
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(Xmat.flatten(), bins=100)
    ax.set_xlim(-5, 5)
    ax.set_title('Scaled Expression Distribution')
    ax.set_xlabel('Expression value')
    ax.set_ylabel('Frequency')
    fig.tight_layout()
    st.pyplot(fig)
