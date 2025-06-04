import streamlit as st
import scanpy as sc
import matplotlib.pyplot as plt
import numpy as np
from src.modules.scrna_seq.tracking import status, log_shape
from src.modules.scrna_seq.dea_plots import (
    plot_dea_volcano_plotly, 
    plot_dea_heatmap_plotly, 
    plot_dea_dotplot_plotly,
    plot_dea_summary_plotly
)


def run_differential_expression():
    """
    Step: Differential expression analysis per Leiden cluster.
    - Runs automatically when accessed
    - Displays interactive Plotly visualizations:
        1. Summary of significant genes per cluster
        2. Interactive volcano plot for selected cluster
        3. Interactive heatmap of top marker genes
        4. Interactive dot plot of marker gene expression
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

    # Run DEA automatically if not already done
    if not st.session_state.get("dea_done", False):
        try:
            st.info("Running differential expression analysis...")
            log_shape("Before DEG", anndata)

            # Use wilcoxon method which is more robust and provides better log fold changes
            sc.tl.rank_genes_groups(
                anndata, 
                groupby='leiden', 
                method='wilcoxon',
                use_raw=False,
                n_genes=2000  # Get more genes for better analysis
            )
            
            # Also calculate log fold changes explicitly
            st.info("Calculating log fold changes...")
            sc.tl.rank_genes_groups(
                anndata,
                groupby='leiden',
                method='t-test',
                use_raw=False,
                n_genes=2000
            )
            
            # Update session state
            st.session_state['anndata'] = anndata
            st.session_state['dea_done'] = True
            
            log_shape("After DEG", anndata)
            st.success("✅ Differential expression completed successfully!")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Differential expression failed: {e}")
            return

    # Show results if DEA is done
    if st.session_state.get('dea_done', False):
        st.success("✅ Differential expression completed successfully!")
        
        # Input for number of genes
        n_markers = st.number_input(
            "Number of top markers per cluster", min_value=1, value=5, step=1, key="deg_n_markers"
        )

        # 1) Summary plot - Number of significant genes per cluster
        st.markdown("### 📊 Summary: Significant Genes per Cluster")
        summary_fig = plot_dea_summary_plotly(anndata)
        if summary_fig:
            st.plotly_chart(summary_fig, use_container_width=True)

        # 2) Interactive volcano plot for selected cluster
        st.markdown("### 🌋 Interactive Volcano Plot")
        groups = anndata.uns['rank_genes_groups']['names'].dtype.names
        selected_cluster = st.selectbox("Select cluster for volcano plot", groups, key="volc_group")
        
        volcano_fig = plot_dea_volcano_plotly(anndata, selected_cluster, n_markers)
        if volcano_fig:
            st.plotly_chart(volcano_fig, use_container_width=True)

        # 3) Interactive heatmap of top marker genes
        st.markdown("### 🔥 Interactive Heatmap: Top Marker Genes")
        heatmap_fig = plot_dea_heatmap_plotly(anndata, n_markers)
        if heatmap_fig:
            st.plotly_chart(heatmap_fig, use_container_width=True)

        # 4) Interactive dot plot
        st.markdown("### 🎯 Interactive Dot Plot: Marker Gene Expression")
        dotplot_fig = plot_dea_dotplot_plotly(anndata, n_markers)
        if dotplot_fig:
            st.plotly_chart(dotplot_fig, use_container_width=True)

        # Reset DEG
        if st.button("♻️ Reset Differential Expression", key="reset_deg"):
            st.session_state.pop('dea_done', None)
            st.warning("⚠️ Differential expression reset. You'll need to re-run the analysis.")
            st.rerun()
