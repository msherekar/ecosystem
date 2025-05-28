import streamlit as st
import scanpy as sc
import matplotlib.pyplot as plt
import numpy as np
from src.modules.scrna_seq.tracking import status, log_shape


def run_differential_expression():
    """
    Step: Differential expression analysis per Leiden cluster.
    - Runs on explicit ▶️ Run DEG.
    - Displays:
        1. Rank genes groups barplot.
        2. Dotplot of top marker genes for each cluster.
        3. Heatmap of marker gene expression.
        4. Volcano plot for a selected cluster.
    """
    anndata = st.session_state.get("anndata")
    if anndata is None:
        st.error("⚠️ No AnnData loaded. Please complete previous steps first.")
        return

    # Check if clustering has been completed first
    if not st.session_state.get("clustering_done", False):
        st.error("⚠️ Please complete Clustering step first. Differential expression requires clustering results.")
        return

    # Check if clustering results exist
    if 'leiden' not in anndata.obs:
        st.error("⚠️ Leiden clustering results not found. Please complete the Clustering step first.")
        return

    # Show current data dimensions
    n_clusters = len(anndata.obs["leiden"].unique())
    st.info(f"📊 Current data: {anndata.shape[0]:,} cells × {anndata.shape[1]:,} genes, {n_clusters} clusters")

    # Button to run DEG
    if not st.session_state.get("dea_done", False):
        if st.button("▶️ Run Differential Expression", key="run_deg"):
            try:
                st.info("Running differential expression analysis...")
                log_shape("Before DEG", anndata)

                # Run rank genes groups
                sc.tl.rank_genes_groups(anndata, groupby='leiden', method='t-test')
                
                # Update session state
                st.session_state['anndata'] = anndata
                st.session_state['dea_done'] = True
                
                log_shape("After DEG", anndata)
                st.success("✅ Differential expression completed successfully!")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Differential expression failed: {e}")
                return
    else:
        st.success("✅ Differential expression already completed.")

    # Show results if DEA is done
    if st.session_state.get('dea_done', False):
        # Input for number of genes
        n_markers = st.number_input(
            "Number of top markers per cluster", min_value=1, value=5, step=1, key="deg_n_markers"
        )

        # 1) Rank genes groups barplot
        st.markdown("**1. Top Marker Genes per Cluster**")
        fig1 = sc.pl.rank_genes_groups(anndata, show=False, return_fig=True)
        st.pyplot(fig1)
        plt.clf()

        # 2) Dotplot
        st.markdown("**2. Dotplot: Marker Gene Expression Across Clusters**")
        fig2 = sc.pl.rank_genes_groups_dotplot(
            anndata, groupby='leiden', n_genes=n_markers, show=False, return_fig=True
        )
        st.pyplot(fig2)
        plt.clf()

        # 3) Heatmap
        st.markdown("**3. Heatmap: Marker Gene Expression**")
        fig3 = sc.pl.rank_genes_groups_heatmap(
            anndata, groupby='leiden', n_genes=n_markers, show=False, return_fig=True
        )
        st.pyplot(fig3)
        plt.clf()

        # 4) Volcano plot for selected cluster
        # Identify cluster names
        groups = anndata.uns['rank_genes_groups']['names'].dtype.names
        sel = st.selectbox("Select cluster for volcano plot", groups, key="volc_group")
        st.markdown(f"**4. Volcano Plot: Cluster {sel}**")
        # Extract data for selected cluster
        names = anndata.uns['rank_genes_groups']['names'][sel]
        pvals = anndata.uns['rank_genes_groups']['pvals_adj'][sel]
        logfc = anndata.uns['rank_genes_groups']['logfoldchanges'][sel]
        # Plot volcano
        fig4, ax4 = plt.subplots(figsize=(6,4))
        # scatter all genes
        ax4.scatter(logfc, -np.log10(pvals), s=5, alpha=0.5)
        # highlight top n_markers
        topn = min(n_markers, len(names))
        ax4.scatter(logfc[:topn], -np.log10(pvals[:topn]), color='red', s=10)
        for x,y,g in zip(logfc[:topn], -np.log10(pvals[:topn]), names[:topn]):
            ax4.text(x, y, g, fontsize=6)
        ax4.set_xlabel('Log2 fold change')
        ax4.set_ylabel('-Log10(adj p-value)')
        ax4.set_title(f'Volcano: {sel}')
        fig4.tight_layout()
        st.pyplot(fig4)
        plt.clf()

        # Reset DEG
        if st.button("♻️ Reset Differential Expression", key="reset_deg"):
            st.session_state.pop('dea_done', None)
            st.warning("⚠️ Differential expression reset. You'll need to re-run the analysis.")
            st.rerun()
