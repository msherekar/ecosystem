# modules/scrna_seq/plot.py
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import scanpy as sc
import scipy.sparse as sp
from sklearn.metrics import silhouette_samples, silhouette_score
import plotly.express as px
import pandas as pd



def plot_qc_metrics(anndata):
   
    st.markdown("**QC Metrics Preview**")
    st.dataframe(anndata.obs[["n_genes_by_counts", "total_counts", "pct_counts_mt"]].head())

    st.markdown("**QC Distributions (Interactive)**")
    for metric in ["n_genes_by_counts", "total_counts", "pct_counts_mt"]:
        values = anndata.obs[metric].dropna().values
        fig = px.histogram(x=values, nbins=50, title=metric)
        fig.update_layout(xaxis_title=metric, yaxis_title="Cell count")
        st.plotly_chart(fig, use_container_width=True, key=f"qc_metric_{metric}")


def plot_filtering_qc(anndata):


    X = anndata.X
    mat = X.toarray() if sp.issparse(X) else X

    anndata.obs["n_genes_by_counts"] = np.sum(mat > 0, axis=1).flatten()
    anndata.obs["total_counts"] = np.sum(mat, axis=1).flatten()

    st.markdown("**Filtering QC Distributions (Interactive)**")
    for metric in ["n_genes_by_counts", "total_counts"]:
        values = anndata.obs[metric].dropna().values
        fig = px.histogram(x=values, nbins=50, title=metric)
        fig.update_layout(xaxis_title=metric, yaxis_title="Cell count")
        st.plotly_chart(fig, use_container_width=True, key=f"filtering_qc_{metric}")

def plot_normalization_qc(anndata):
    """Show cell-wise and gene-wise histograms after normalization."""
    X = anndata.X
    mat = X.toarray() if sp.issparse(X) else X

    anndata.obs["total_counts"] = np.sum(mat, axis=1).flatten()
    anndata.obs["n_genes_by_counts"] = np.sum(mat > 0, axis=1).flatten()
    var_counts = np.sum(mat, axis=0).flatten()

    st.markdown("**Per-cell Metrics (Interactive)**")
    for metric in ["total_counts", "n_genes_by_counts"]:
        values = anndata.obs[metric].dropna().values
        fig = px.histogram(x=values, nbins=50, title=metric)
        fig.update_layout(xaxis_title=metric, yaxis_title="Cell count")
        st.plotly_chart(fig, use_container_width=True, key=f"norm_qc_{metric}")

    st.markdown("**Per-gene Total Counts (Interactive)**")
    fig2 = px.histogram(x=var_counts, nbins=50, title="Total counts per gene")
    fig2.update_layout(xaxis_title="Total counts", yaxis_title="Gene count")
    st.plotly_chart(fig2, use_container_width=True, key="norm_qc_gene_counts")

def plot_hvg_trend(adata):


    if "means" in adata.var.columns and "dispersions_norm" in adata.var.columns:
        df = adata.var[["means", "dispersions_norm"]].dropna()
        fig = px.scatter(
            df,
            x="means",
            y="dispersions_norm",
            log_x=True,
            log_y=True,
            title="HVG Mean-Variance Trend"
        )
        fig.update_layout(xaxis_title="Mean expression", yaxis_title="Normalized dispersion")
        st.plotly_chart(fig, use_container_width=True, key="hvg_trend")
    else:
        st.warning("⚠️ HVG data missing in adata.var.")

def plot_pca_variance(adata):


    if "pca" in adata.uns and "variance_ratio" in adata.uns["pca"]:
        evr = adata.uns["pca"]["variance_ratio"]
        df = pd.DataFrame({
            "PC": [f"PC{i+1}" for i in range(len(evr))],
            "Variance Ratio": evr,
            "Cumulative": np.cumsum(evr)
        })

        fig1 = px.bar(df, x="PC", y="Variance Ratio", title="Explained Variance by PC")
        fig2 = px.line(df, x="PC", y="Cumulative", markers=True, title="Cumulative Explained Variance")
        st.plotly_chart(fig1, use_container_width=True, key="pca_variance_bar")
        st.plotly_chart(fig2, use_container_width=True, key="pca_variance_cumulative")
    else:
        st.warning("⚠️ PCA results missing.")


def plot_pca_scatter(adata):


    if "X_pca" in adata.obsm:
        df = pd.DataFrame(adata.obsm["X_pca"][:, :2], columns=["PC1", "PC2"], index=adata.obs.index)
        for color in ["total_counts", "n_genes_by_counts"]:
            if color in adata.obs.columns:
                df[color] = adata.obs[color].values
                fig = px.scatter(df, x="PC1", y="PC2", color=color, title=f"PCA colored by {color}")
                st.plotly_chart(fig, use_container_width=True, key=f"pca_scatter_{color}")


def plot_pca_loadings(adata):


    if "pca_loadings" in adata.varm:
        loadings = pd.DataFrame(adata.varm["pca_loadings"][:, :3], index=adata.var_names, columns=["PC1", "PC2", "PC3"])
        top_genes = loadings.abs().sum(axis=1).sort_values(ascending=False).head(30).index
        fig = px.imshow(loadings.loc[top_genes].T, aspect="auto", labels={"x": "Gene", "y": "PC"}, title="Top Gene Loadings")
        st.plotly_chart(fig, use_container_width=True, key="pca_loadings")
    else:
        st.warning("⚠️ PCA loadings not found.")

def plot_scaled_distribution(adata):


    Xmat = adata.X.toarray() if sp.issparse(adata.X) else adata.X
    fig = px.histogram(x=Xmat.flatten(), nbins=100, title="Scaled Expression Distribution")
    fig.update_layout(xaxis_title="Expression value", yaxis_title="Frequency")
    st.plotly_chart(fig, use_container_width=True, key="scaled_distribution")

def plot_clustering_diagnostics(anndata, n_markers=5):


    if "X_umap" in anndata.obsm and "leiden" in anndata.obs:
        df_umap = pd.DataFrame(anndata.obsm["X_umap"], columns=["UMAP1", "UMAP2"], index=anndata.obs.index)
        df_umap["Cluster"] = anndata.obs["leiden"].astype(str).values
        st.plotly_chart(px.scatter(df_umap, x="UMAP1", y="UMAP2", color="Cluster", title="UMAP: Leiden Clusters"), use_container_width=True, key="clustering_umap")

        counts = anndata.obs["leiden"].value_counts().sort_index()
        st.plotly_chart(px.bar(x=counts.index.astype(str), y=counts.values, title="Cluster Sizes", labels={"x": "Cluster", "y": "Cell count"}), use_container_width=True, key="clustering_sizes")

        try:
            labels = anndata.obs["leiden"].astype(int).values
            sil_scores = silhouette_samples(anndata.obsm["X_pca"], labels)
            avg_score = silhouette_score(anndata.obsm["X_pca"], labels)
            fig = px.histogram(x=sil_scores, nbins=50, title=f"Silhouette Score Distribution (avg = {avg_score:.2f})")
            fig.update_layout(xaxis_title="Silhouette coefficient", yaxis_title="Cell count")
            st.plotly_chart(fig, use_container_width=True, key="clustering_silhouette")
        except Exception as e:
            st.warning(f"Silhouette error: {e}")

        try:
            sc.tl.rank_genes_groups(anndata, groupby="leiden", method="wilcoxon", n_genes=n_markers)
            fig = sc.pl.rank_genes_groups_heatmap(anndata, groupby="leiden", n_genes=n_markers, show=False, return_fig=True)
            st.pyplot(fig)
        except Exception as e:
            st.warning(f"Marker heatmap failed: {e}")
    else:
        st.warning("⚠️ UMAP or Leiden not found.")


        
def plot_interactive_umap(anndata, color_by, title="UMAP Projection", split_by=None):
    if "X_umap" not in anndata.obsm:
        st.warning("UMAP not computed.")
        return

    umap = anndata.obsm["X_umap"]
    df = pd.DataFrame(umap, columns=["UMAP1", "UMAP2"])
    df.index = anndata.obs.index

    if color_by in anndata.obs.columns:
        df["color"] = anndata.obs[color_by].astype(str)
    elif color_by in anndata.var_names:
        expr = anndata[:, color_by].X
        df["color"] = expr.toarray().flatten() if hasattr(expr, "toarray") else expr.flatten()
    else:
        st.warning(f"⚠️ `{color_by}` not found in obs or var_names.")
        return

    if split_by and split_by in anndata.obs.columns:
        df["facet"] = anndata.obs[split_by].astype(str)
        fig = px.scatter(df, x="UMAP1", y="UMAP2", color="color", facet_col="facet",
                         title=title, height=500)
    else:
        fig = px.scatter(df, x="UMAP1", y="UMAP2", color="color", title=title, height=500)

    st.plotly_chart(fig, use_container_width=True, key=f"interactive_umap_{color_by}_{split_by or 'no_split'}")


def plot_interactive_bar(counts, title="Barplot", xlabel="Group", ylabel="Proportion"):
    df = pd.DataFrame({xlabel: counts.index.astype(str), ylabel: counts.values})
    fig = px.bar(df, x=xlabel, y=ylabel, title=title)
    st.plotly_chart(fig, use_container_width=True, key=f"interactive_bar_{title.replace(' ', '_')}")
