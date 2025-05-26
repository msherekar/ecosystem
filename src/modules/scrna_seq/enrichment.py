import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from gprofiler import GProfiler
from modules.scrna_seq.tracking import status


def run_go_enrichment():
    """
    Step 9: GO term enrichment using g:Profiler.
    - Collects top DE genes across clusters.
    - Runs enrichment for GO:BP, GO:CC, GO:MF.
    - Displays table and barplot of top terms.
    """
    anndata = st.session_state.get("anndata")
    if anndata is None or not st.session_state.get("deg_done", False):
        st.warning("⚠️ Run differential expression first.")
        return

    go_done = st.session_state.get("go_enriched", False)
    if not go_done:
        if st.button("▶️ Run GO Enrichment", key="run_go_enr"):
            # Gather top genes across clusters
            groups = anndata.uns['rank_genes_groups']['names'].dtype.names
            genes = []
            for g in groups:
                genes.extend(anndata.uns['rank_genes_groups']['names'][g].tolist())
            genes = list(set(genes))

            gp = GProfiler(return_dataframe=True)
            res = gp.profile(
                organism='hsapiens',
                query=genes,
                sources=['GO:BP', 'GO:CC', 'GO:MF']
            )
            st.session_state['go_results'] = res
            st.session_state['go_enriched'] = True
            st.success(f"✅ GO enrichment found {len(res)} terms.")
    else:
        st.info("✅ GO enrichment already run.")

    if st.session_state.get('go_enriched', False):
        res = st.session_state['go_results']
        # Filter by significance
        sig = res.query('p_value < 0.05')

        # Show top terms table
        st.markdown("**Top GO terms (p < 0.05)**")
        st.dataframe(sig[['source', 'term_name', 'p_value', 'intersection_size']].head(10))

        # Barplot of top 10 terms by -log10(p_value)
        top = sig.head(10)
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.barh(top['term_name'], -np.log10(top['p_value']))
        ax.set_xlabel('-Log10(p-value)')
        ax.set_ylabel('GO term')
        ax.invert_yaxis()
        fig.tight_layout()
        st.pyplot(fig)


def run_pathway_enrichment():
    """
    Step 10: Pathway enrichment using g:Profiler.
    - Uses same gene list as GO enrichment.
    - Runs enrichment for KEGG and REAC.
    - Displays table and barplot of top pathways.
    """
    anndata = st.session_state.get("anndata")
    if anndata is None or not st.session_state.get("go_enriched", False):
        st.warning("⚠️ Run GO enrichment first to get gene list.")
        return

    path_done = st.session_state.get("pathway_enriched", False)
    if not path_done:
        if st.button("▶️ Run Pathway Enrichment", key="run_path_enr"):
            genes = list(set(anndata.uns['rank_genes_groups']['names'][g] for g in anndata.uns['rank_genes_groups']['names'].dtype.names))
            gp = GProfiler(return_dataframe=True)
            res = gp.profile(
                organism='hsapiens',
                query=genes,
                sources=['KEGG', 'REAC']
            )
            st.session_state['path_results'] = res
            st.session_state['pathway_enriched'] = True
            st.session_state['enrichment_done'] = True  # Set the proper completion flag
            st.success(f"✅ Pathway enrichment found {len(res)} terms.")
    else:
        st.info("✅ Pathway enrichment already run.")

    if st.session_state.get('pathway_enriched', False):
        res = st.session_state['path_results']
        sig = res.query('p_value < 0.05')

        st.markdown("**Top Pathways (p < 0.05)**")
        st.dataframe(sig[['source', 'term_name', 'p_value', 'intersection_size']].head(10))

        top = sig.head(10)
        fig2, ax2 = plt.subplots(figsize=(6, 4))
        ax2.barh(top['term_name'], -np.log10(top['p_value']))
        ax2.set_xlabel('-Log10(p-value)')
        ax2.set_ylabel('Pathway')
        ax2.invert_yaxis()
        fig2.tight_layout()
        st.pyplot(fig2)
