import streamlit as st
import scanpy as sc
import matplotlib.pyplot as plt
from modules.scrna_seq.tracking import status


def create_visualization():
    """
    Step 7: UMAP visualization and exploratory plots.
    - Computes neighbors and UMAP if missing.
    - Automatically displays:
        1. UMAP colored by Leiden clusters.
        2. UMAP colored by QC metrics (total_counts, n_genes_by_counts).
        3. UMAP expression overlays for selected marker genes.
        4. Proportion barplot of cells per cluster.
        5. Optional split UMAP by metadata column.
    """
    with st.expander(status("7. UMAP Visualization"), expanded=True):
        anndata = st.session_state.get("anndata")
        if anndata is None:
            st.error("⚠️ No AnnData loaded. Please complete clustering first.")
            return

        # 1) Ensure UMAP computed
        if 'X_umap' not in anndata.obsm:
            if st.button("▶️ Compute Neighbors & UMAP", key="run_umap_neighbors"):
                try:
                    sc.pp.neighbors(anndata)
                    sc.tl.umap(anndata)
                    st.session_state['anndata'] = anndata
                    st.success("✅ UMAP computed.")
                except Exception as e:
                    st.error(f"UMAP computation failed: {e}")
                    return
        else:
            st.info("✅ UMAP embedding available.")

        # 2) Main UMAP plot colored by clusters
        if 'X_umap' in anndata.obsm and 'leiden' in anndata.obs:
            st.markdown("**UMAP: Leiden Clusters**")
            fig1 = sc.pl.umap(anndata, color='leiden', show=False, return_fig=True)
            st.pyplot(fig1)
            plt.clf()
        else:
            st.warning("⚠️ Cannot plot clusters: missing UMAP or Leiden results.")

        # 3) UMAP colored by QC metrics
        qc_metrics = [m for m in ['total_counts', 'n_genes_by_counts'] if m in anndata.obs.columns]
        if qc_metrics:
            st.markdown("**UMAP: QC Metrics**")
            for metric in qc_metrics:
                fig_qc = sc.pl.umap(anndata, color=metric, show=False, return_fig=True)
                st.pyplot(fig_qc)
                plt.clf()
        else:
            st.warning("⚠️ QC metrics not found in .obs. Run QC/filtering steps.")

        # 4) Gene expression overlay
        gene_input = st.text_input("Enter gene(s) to overlay (comma-separated)", key="umap_genes")
        genes = [g.strip() for g in gene_input.split(',') if g.strip()]
        if genes:
            valid = [g for g in genes if g in anndata.var_names]
            if valid:
                st.markdown("**UMAP: Gene Expression Overlays**")
                for gene in valid:
                    fig_gene = sc.pl.umap(anndata, color=gene, show=False, return_fig=True)
                    st.pyplot(fig_gene)
                    plt.clf()
            else:
                st.warning("⚠️ None of the entered genes found in var_names.")

        # 5) Cluster proportions barplot
        if 'leiden' in anndata.obs:
            st.markdown("**Cluster Proportions**")
            counts = anndata.obs['leiden'].value_counts(normalize=True).sort_index()
            fig2, ax2 = plt.subplots(figsize=(6,4))
            ax2.bar(counts.index.astype(str), counts.values)
            ax2.set_xlabel('Cluster')
            ax2.set_ylabel('Proportion of cells')
            ax2.set_title('Cluster Proportions')
            fig2.tight_layout()
            st.pyplot(fig2)
            plt.clf()

        # 6) Optional split by metadata
        meta_cols = [c for c in anndata.obs.columns if anndata.obs[c].nunique() <= 10]
        if meta_cols:
            split = st.selectbox("Split UMAP by metadata column", ['None'] + meta_cols, key="umap_split")
            if split and split != 'None':
                st.markdown(f"**UMAP Split by {split}**")
                fig_split = sc.pl.umap(anndata, color=split, show=False, return_fig=True)
                st.pyplot(fig_split)
                plt.clf()
