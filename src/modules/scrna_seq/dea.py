import streamlit as st
import scanpy as sc
import matplotlib.pyplot as plt
import numpy as np
from modules.scrna_seq.tracking import status, log_shape


def run_differential_expression():
    """
    Step 8: Differential expression analysis per Leiden cluster.
    - Runs on explicit ▶️ Run DEG.
    - Displays:
        1. Rank genes groups barplot.
        2. Dotplot of top marker genes for each cluster.
        3. Heatmap of marker gene expression.
        4. Volcano plot for a selected cluster.
    """
    with st.expander(status("8. Differential Expression"), expanded=True):
        adata = st.session_state.get("adata")
        if adata is None:
            st.error("⚠️ No AnnData loaded. Please complete clustering first.")
            return

        deg_done = st.session_state.get("deg_done", False)
        # Button to run DEG
        if not deg_done:
            if st.button("▶️ Run DEG", key="run_deg"):
                try:
                    # Check clustering
                    if 'leiden' not in adata.obs:
                        st.error("Leiden clusters missing. Cannot run DEG.")
                        return
                    log_shape("Before DEG", adata)

                    # Run rank genes groups
                    sc.tl.rank_genes_groups(adata, groupby='leiden', method='t-test')
                    st.session_state['adata'] = adata
                    st.session_state['deg_done'] = True
                    log_shape("After DEG", adata)
                    st.success("✅ Differential expression completed.")
                except Exception as e:
                    st.error(f"DEG failed: {e}")
                    return
        else:
            st.info("✅ Differential expression already run.")

        # Visualize results
        if st.session_state.get('deg_done', False):
            # 1) Rank genes groups barplot
            st.markdown("**1. Top Marker Genes per Cluster**")
            fig1 = sc.pl.rank_genes_groups(adata, show=False, return_fig=True)
            st.pyplot(fig1)
            plt.clf()

            # Input for number of genes
            n_markers = st.number_input(
                "Number of top markers per cluster", min_value=1, value=5, step=1, key="deg_n_markers"
            )

            # 2) Dotplot
            st.markdown("**2. Dotplot: Marker Gene Expression Across Clusters**")
            fig2 = sc.pl.rank_genes_groups_dotplot(
                adata, groupby='leiden', n_genes=n_markers, show=False, return_fig=True
            )
            st.pyplot(fig2)
            plt.clf()

            # 3) Heatmap
            st.markdown("**3. Heatmap: Marker Gene Expression**")
            fig3 = sc.pl.rank_genes_groups_heatmap(
                adata, groupby='leiden', n_genes=n_markers, show=False, return_fig=True
            )
            st.pyplot(fig3)
            plt.clf()

            # 4) Volcano plot for selected cluster
            # Identify cluster names
            groups = adata.uns['rank_genes_groups']['names'].dtype.names
            sel = st.selectbox("Select cluster for volcano plot", groups, key="volc_group")
            st.markdown(f"**4. Volcano Plot: Cluster {sel}**")
            # Extract data for selected cluster
            names = adata.uns['rank_genes_groups']['names'][sel]
            pvals = adata.uns['rank_genes_groups']['pvals_adj'][sel]
            logfc = adata.uns['rank_genes_groups']['logfoldchanges'][sel]
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
        if st.button("♻️ Reset DEG", key="reset_deg"):
            st.session_state.pop('deg_done', None)
            st.experimental_rerun()
