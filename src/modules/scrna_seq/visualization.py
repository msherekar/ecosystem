from modules.scrna_seq.plot import plot_interactive_umap, plot_interactive_bar
import streamlit as st
import scanpy as sc

def create_visualization():
    anndata = st.session_state.get("anndata")
    if anndata is None:
        st.error("⚠️ No AnnData loaded. Please complete clustering first.")
        return

    if 'X_umap' not in anndata.obsm:
        if st.button("▶️ Compute Neighbors & UMAP", key="run_umap_neighbors"):
            try:
                sc.pp.neighbors(anndata)
                sc.tl.umap(anndata)
                st.session_state['anndata'] = anndata
                st.session_state["viz_done"] = True  # Set completion flag when UMAP is computed
                st.success("✅ UMAP computed.")
            except Exception as e:
                st.error(f"UMAP computation failed: {e}")
                return
    else:
        st.info("✅ UMAP embedding available.")
        st.session_state["viz_done"] = True  # Set completion flag if UMAP already exists

    # 1. UMAP colored by Leiden clusters
    if 'X_umap' in anndata.obsm and 'leiden' in anndata.obs:
        st.markdown("**UMAP: Leiden Clusters**")
        plot_interactive_umap(anndata, color_by="leiden", title="Leiden Clusters")

    # 2. UMAP colored by QC metrics
    qc_metrics = [m for m in ['total_counts', 'n_genes_by_counts'] if m in anndata.obs.columns]
    if qc_metrics:
        st.markdown("**UMAP: QC Metrics**")
        for metric in qc_metrics:
            plot_interactive_umap(anndata, color_by=metric, title=f"UMAP Colored by {metric}")
    else:
        st.warning("⚠️ QC metrics not found in .obs. Run QC/filtering steps.")

    # 3. Gene expression overlay
    gene_input = st.text_input("Enter gene(s) to overlay (comma-separated)", key="umap_genes")
    genes = [g.strip() for g in gene_input.split(',') if g.strip()]
    if genes:
        valid = [g for g in genes if g in anndata.var_names]
        if valid:
            st.markdown("**UMAP: Gene Expression Overlays**")
            for gene in valid:
                plot_interactive_umap(anndata, color_by=gene, title=f"UMAP: {gene}")
        else:
            st.warning("⚠️ None of the entered genes found in var_names.")

    # 4. Cluster proportions
    if 'leiden' in anndata.obs:
        st.markdown("**Cluster Proportions**")
        counts = anndata.obs['leiden'].value_counts(normalize=True).sort_index()
        plot_interactive_bar(counts, title="Cluster Proportions", xlabel="Cluster", ylabel="Proportion")

    # 5. Optional split UMAP
    meta_cols = [c for c in anndata.obs.columns if anndata.obs[c].nunique() <= 10]
    if meta_cols:
        split = st.selectbox("Split UMAP by metadata column", ['None'] + meta_cols, key="umap_split")
        if split and split != 'None':
            st.markdown(f"**UMAP Split by {split}**")
            plot_interactive_umap(anndata, color_by="leiden", split_by=split, title=f"UMAP Split by {split}")
