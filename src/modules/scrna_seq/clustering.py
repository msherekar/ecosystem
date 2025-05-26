import streamlit as st
import scanpy as sc
import matplotlib.pyplot as plt
from modules.scrna_seq.tracking import status, log_shape
from sklearn.metrics import silhouette_samples, silhouette_score


from modules.scrna_seq.plot import plot_clustering_diagnostics

def perform_clustering():
    anndata = st.session_state.get("anndata")
    if anndata is None:
        st.error("⚠️ No AnnData loaded. Please complete previous steps first.")
        return

    clustered = st.session_state.get("clustered", False)
    resolution = st.number_input("Leiden resolution", min_value=0.1, value=1.0, step=0.1, key="leiden_resolution")
    n_markers = st.number_input("Marker genes per cluster", min_value=1, value=5, step=1, key="n_markers")

    if not clustered:
        if st.button("▶️ Run Clustering", key="run_clustering"):
            try:
                log_shape("Before Clustering", anndata)
                sc.pp.neighbors(anndata)
                sc.tl.umap(anndata)
                sc.tl.leiden(anndata, resolution=resolution)
                st.session_state["anndata"] = anndata
                st.session_state["clustered"] = True
                log_shape("After Clustering", anndata)
                st.success("✅ Clustering completed successfully!")
            except Exception as e:
                st.error(f"Clustering failed: {e}")
                return
    else:
        st.info("✅ Clustering already applied.")

    # Recompute UMAP if needed
    if clustered and "X_umap" not in anndata.obsm:
        try:
            log_shape("Recomputing UMAP", anndata)
            sc.pp.neighbors(anndata)
            sc.tl.umap(anndata)
            st.session_state["anndata"] = anndata
            st.success("✅ UMAP recomputed.")
        except Exception as e:
            st.warning(f"Could not recompute UMAP: {e}")

    # Plot all clustering visualizations
    if st.session_state.get("clustered", False):
        plot_clustering_diagnostics(anndata, n_markers=n_markers)

    if st.button("♻️ Reset Clustering", key="reset_clustering"):
        st.session_state.pop("clustered", None)
        st.experimental_rerun()
