import streamlit as st
import scanpy as sc
import matplotlib.pyplot as plt
from modules.scrna_seq.tracking import status, log_shape
from sklearn.metrics import silhouette_samples, silhouette_score


def perform_clustering():
    """
    Step 6: Compute neighbors, UMAP, and Leiden clustering with diagnostics.
    - Runs on explicit ▶️ Run Clustering.
    - Logs dataset shape before and after clustering.
    - Automatically recomputes UMAP if missing.
    - Displays:
        1. UMAP projection colored by Leiden clusters.
        2. Barplot of cluster sizes.
        3. Silhouette score distribution.
        4. Marker gene heatmap.
    - Allows input of Leiden resolution and number of marker genes.
    """
    with st.expander(status("6. Clustering with Leiden"), expanded=True):
        anndata = st.session_state.get("anndata")
        if anndata is None:
            st.error("⚠️ No AnnData loaded. Please complete previous steps first.")
            return

        clustered = st.session_state.get("clustered", False)
        resolution = st.number_input(
            "Leiden resolution", min_value=0.1, value=1.0, step=0.1, key="leiden_resolution"
        )
        n_markers = st.number_input(
            "Marker genes per cluster", min_value=1, value=5, step=1, key="n_markers"
        )

        # 1) Run clustering if not done
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

        # 2) Ensure UMAP embedding exists (recompute if needed)
        if clustered and "X_umap" not in anndata.obsm:
            try:
                log_shape("Recomputing UMAP", anndata)
                sc.pp.neighbors(anndata)
                sc.tl.umap(anndata)
                st.session_state["anndata"] = anndata
                st.success("✅ UMAP recomputed.")
            except Exception as e:
                st.warning(f"Could not recompute UMAP: {e}")

        # 3) Visualizations: only if both UMAP and clustering exist
        if "X_umap" in anndata.obsm and "leiden" in anndata.obs:
            # UMAP scatter
            st.markdown("**1. UMAP Projection (Leiden clusters)**")
            fig1 = sc.pl.umap(anndata, color="leiden", show=False, return_fig=True)
            st.pyplot(fig1)
            plt.clf()

            # Cluster size barplot
            st.markdown("**2. Cluster Sizes**")
            clusters = anndata.obs["leiden"].value_counts().sort_index()
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            ax2.bar(clusters.index.astype(str), clusters.values)
            ax2.set_xlabel("Cluster")
            ax2.set_ylabel("Number of cells")
            ax2.set_title("Leiden Cluster Sizes")
            fig2.tight_layout()
            st.pyplot(fig2)
            plt.clf()

            # Silhouette analysis
            st.markdown("**3. Silhouette Score Distribution**")
            try:
                
                labels = anndata.obs["leiden"].astype(int).values
                sil_scores = silhouette_samples(anndata.obsm['X_pca'], labels)
                avg_score = silhouette_score(anndata.obsm['X_pca'], labels)
                fig3, ax3 = plt.subplots(figsize=(6, 4))
                ax3.hist(sil_scores, bins=50)
                ax3.axvline(avg_score, color='red', linestyle='--')
                ax3.set_title(f"Silhouette Scores (avg = {avg_score:.2f})")
                ax3.set_xlabel("Silhouette coefficient")
                ax3.set_ylabel("Count")
                fig3.tight_layout()
                st.pyplot(fig3)
                plt.clf()
            except Exception as e:
                st.warning(f"Could not compute silhouette: {e}")

            # Marker gene heatmap
            st.markdown("**4. Marker Gene Heatmap**")
            try:
                sc.tl.rank_genes_groups(anndata, groupby='leiden', method='wilcoxon', n_genes=n_markers)
                fig4 = sc.pl.rank_genes_groups_heatmap(
                    anndata,
                    groupby='leiden',
                    n_genes=n_markers,
                    show=False,
                    return_fig=True,
                    swap_axes=True,
                    figsize=(8, 4)
                )
                st.pyplot(fig4)
                plt.clf()
            except Exception as e:
                st.warning(f"Marker heatmap failed: {e}")
        else:
            st.warning("⚠️ Cannot plot clustering visualizations: UMAP or Leiden missing.")

        # Reset clustering
        if st.button("♻️ Reset Clustering", key="reset_clustering"):
            st.session_state.pop("clustered", None)
            st.experimental_rerun()
