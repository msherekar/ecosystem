import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from gprofiler import GProfiler
from src.modules.scrna_seq.tracking import status


def run_go_enrichment():
    """
    Step: GO term enrichment using g:Profiler.
    - Collects top DE genes across clusters.
    - Runs enrichment for GO:BP, GO:CC, GO:MF.
    - Displays table and barplot of top terms.
    """
    anndata = st.session_state.get("anndata")
    if anndata is None:
        st.error("⚠️ No AnnData loaded. Please complete previous steps first.")
        return

    # Check if differential expression has been completed first
    if not st.session_state.get("dea_done", False):
        st.error("⚠️ Please complete Differential Expression step first. GO enrichment requires DEG results.")
        return

    # Check if DEG results exist
    if 'rank_genes_groups' not in anndata.uns:
        st.error("⚠️ Differential expression results not found. Please complete the DEA step first.")
        return

    # Show current data dimensions
    n_clusters = len(anndata.obs["leiden"].unique())
    st.info(f"📊 Current data: {anndata.shape[0]:,} cells × {anndata.shape[1]:,} genes, {n_clusters} clusters")

    if not st.session_state.get("go_enriched", False):
        if st.button("▶️ Run GO Enrichment", key="run_go_enr"):
            try:
                st.info("Running GO enrichment analysis...")
                
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
                st.success(f"✅ GO enrichment completed! Found {len(res)} terms.")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ GO enrichment failed: {e}")
                return
    else:
        st.success("✅ GO enrichment already completed.")

    # Show results if GO enrichment is done
    if st.session_state.get('go_enriched', False):
        res = st.session_state['go_results']
        # Filter by significance
        sig = res.query('p_value < 0.05')

        # Show top terms table
        st.markdown("**Top GO terms (p < 0.05)**")
        st.dataframe(sig[['source', 'term_name', 'p_value', 'intersection_size']].head(10))

        # Barplot of top 10 terms by -log10(p_value)
        if len(sig) > 0:
            top = sig.head(10)
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.barh(top['term_name'], -np.log10(top['p_value']))
            ax.set_xlabel('-Log10(p-value)')
            ax.set_ylabel('GO term')
            ax.invert_yaxis()
            fig.tight_layout()
            st.pyplot(fig)
            plt.clf()
        else:
            st.warning("⚠️ No significant GO terms found (p < 0.05).")


def run_pathway_enrichment():
    """
    Step: Pathway enrichment using g:Profiler.
    - Uses same gene list as GO enrichment.
    - Runs enrichment for KEGG and REAC.
    - Displays table and barplot of top pathways.
    """
    anndata = st.session_state.get("anndata")
    if anndata is None:
        st.error("⚠️ No AnnData loaded. Please complete previous steps first.")
        return

    # Check if GO enrichment has been completed first
    if not st.session_state.get("go_enriched", False):
        st.error("⚠️ Please complete GO enrichment first to get gene list.")
        return

    if not st.session_state.get("pathway_enriched", False):
        if st.button("▶️ Run Pathway Enrichment", key="run_path_enr"):
            try:
                st.info("Running pathway enrichment analysis...")
                
                # Use same genes as GO enrichment
                groups = anndata.uns['rank_genes_groups']['names'].dtype.names
                genes = []
                for g in groups:
                    genes.extend(anndata.uns['rank_genes_groups']['names'][g].tolist())
                genes = list(set(genes))
                
                gp = GProfiler(return_dataframe=True)
                res = gp.profile(
                    organism='hsapiens',
                    query=genes,
                    sources=['KEGG', 'REAC']
                )
                
                st.session_state['path_results'] = res
                st.session_state['pathway_enriched'] = True
                st.session_state['enrichment_done'] = True  # Set the proper completion flag
                st.success(f"✅ Pathway enrichment completed! Found {len(res)} terms.")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Pathway enrichment failed: {e}")
                return
    else:
        st.success("✅ Pathway enrichment already completed.")

    # Show results if pathway enrichment is done
    if st.session_state.get('pathway_enriched', False):
        res = st.session_state['path_results']
        sig = res.query('p_value < 0.05')

        st.markdown("**Top Pathways (p < 0.05)**")
        st.dataframe(sig[['source', 'term_name', 'p_value', 'intersection_size']].head(10))

        if len(sig) > 0:
            top = sig.head(10)
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            ax2.barh(top['term_name'], -np.log10(top['p_value']))
            ax2.set_xlabel('-Log10(p-value)')
            ax2.set_ylabel('Pathway')
            ax2.invert_yaxis()
            fig2.tight_layout()
            st.pyplot(fig2)
            plt.clf()
        else:
            st.warning("⚠️ No significant pathways found (p < 0.05).")
        
        # Option to reset enrichment
        if st.button("♻️ Reset Enrichment", key="reset_enrichment"):
            st.session_state.pop("go_enriched", None)
            st.session_state.pop("pathway_enriched", None)
            st.session_state.pop("enrichment_done", None)
            st.warning("⚠️ Enrichment analysis reset. You'll need to re-run the analysis.")
            st.rerun()
