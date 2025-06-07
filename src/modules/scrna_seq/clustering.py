import streamlit as st
import scanpy as sc
import matplotlib.pyplot as plt
from src.modules.scrna_seq.tracking import status, log_shape
from sklearn.metrics import silhouette_samples, silhouette_score
from src.modules.scrna_seq.plot import plot_clustering_diagnostics

def perform_clustering():
    anndata = st.session_state.get("anndata")
    if anndata is None:
        st.error("⚠️ No AnnData loaded. Please complete previous steps first.")
        return

    # Check if dimensionality reduction has been completed first
    if not st.session_state.get("dimred_done", False):
        st.error("⚠️ Please complete Dimensionality Reduction step first. Clustering requires PCA results.")
        return

    # Check if PCA results exist
    if "X_pca" not in anndata.obsm:
        st.error("⚠️ PCA results not found. Please complete the Dimensionality Reduction step first.")
        return

    # Show current data dimensions
    st.info(f"📊 Current data: {anndata.shape[0]:,} cells × {anndata.shape[1]:,} genes")

    # Parameters (use defaults for automatic execution)
    resolution = st.number_input("Leiden resolution", min_value=0.1, value=1.0, step=0.1, key="leiden_resolution")
    n_markers = st.number_input("Marker genes per cluster", min_value=1, value=5, step=1, key="n_markers")

    # Run clustering automatically if not already done
    if not st.session_state.get("clustering_done", False):
        try:
            st.info("Running clustering...")
            log_shape("Before Clustering", anndata)
            
            # Compute neighborhood graph
            sc.pp.neighbors(anndata)
            
            # Compute UMAP embedding
            sc.tl.umap(anndata)
            
            # Perform Leiden clustering
            sc.tl.leiden(anndata, resolution=resolution)
            
            # Update session state
            st.session_state["anndata"] = anndata
            st.session_state["clustering_done"] = True
            st.session_state["clustered"] = True
            st.session_state["umap_done"] = True  # Also set UMAP flag
            
            log_shape("After Clustering", anndata)
            
            n_clusters = len(anndata.obs["leiden"].unique())
            st.success(f"✅ Clustering completed successfully! Found {n_clusters} clusters.")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Clustering failed: {e}")
            return

    # Show results if clustering is done
    if st.session_state.get("clustering_done", False):
        st.success("✅ Clustering completed successfully!")
        
        # Recompute UMAP if needed
        if "X_umap" not in anndata.obsm:
            try:
                st.info("Recomputing UMAP...")
                log_shape("Recomputing UMAP", anndata)
                sc.pp.neighbors(anndata)
                sc.tl.umap(anndata)
                st.session_state["anndata"] = anndata
                st.success("✅ UMAP recomputed.")
            except Exception as e:
                st.warning(f"Could not recompute UMAP: {e}")

        # Plot all clustering visualizations
        plot_clustering_diagnostics(anndata, n_markers=n_markers)
        
        # Option to reset clustering
        if st.button("♻️ Reset Clustering", key="reset_clustering"):
            st.session_state.pop("clustering_done", None)
            st.session_state.pop("clustered", None)
            st.session_state.pop("umap_done", None)
            st.warning("⚠️ Clustering reset. You'll need to re-run clustering.")
            st.rerun()
