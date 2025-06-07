import streamlit as st
import pandas as pd
import numpy as np
from gprofiler import GProfiler
from src.modules.scrna_seq.tracking import status, log_shape
from src.modules.scrna_seq.enrichment_plots import (
    plot_go_bar_plotly,
    plot_go_bubble_plotly,
    plot_go_faceted_plotly,
    plot_pathway_network_plotly,
    plot_enrichment_comparison_plotly,
    plot_enrichment_sunburst_plotly
)


def run_enrichment_analysis():
    """
    Step: Gene Ontology and Pathway Enrichment Analysis.
    - Runs automatically when accessed
    - Displays interactive Plotly visualizations:
        1. Interactive GO terms bar plot
        2. GO terms bubble plot
        3. Faceted GO analysis by category
        4. Pathway network visualization
        5. Comparison between GO and pathway results
        6. Sunburst hierarchical view
    """
    anndata = st.session_state.get("anndata")
    if anndata is None:
        st.error("⚠️ No AnnData loaded. Please complete previous steps first.")
        return

    # Check if DEA has been completed first
    if not st.session_state.get("dea_done", False):
        st.error("⚠️ Please complete Differential Expression step first. Enrichment requires DEA results.")
        return

    # Check if DEA results exist
    if 'rank_genes_groups' not in anndata.uns:
        st.error("⚠️ Differential expression results not found. Please complete the DEA step first.")
        return

    # Show current data dimensions
    n_clusters = len(anndata.obs["leiden"].unique())
    st.info(f"📊 Current data: {anndata.shape[0]:,} cells × {anndata.shape[1]:,} genes, {n_clusters} clusters")

    # Run enrichment automatically if not already done
    if not st.session_state.get("enrichment_done", False):
        try:
            st.info("Running enrichment analysis...")
            
            # Get top genes from each cluster
            groups = anndata.uns['rank_genes_groups']['names'].dtype.names
            
            # Collect all significant genes
            all_genes = set()
            cluster_genes = {}
            
            for group in groups:
                # Get genes for this cluster
                genes = anndata.uns['rank_genes_groups']['names'][group]
                
                # Get p-values
                if 'pvals_adj' in anndata.uns['rank_genes_groups']:
                    pvals = anndata.uns['rank_genes_groups']['pvals_adj'][group]
                else:
                    pvals = anndata.uns['rank_genes_groups']['pvals'][group]
                
                # Filter significant genes (p < 0.05)
                sig_genes = []
                for gene, pval in zip(genes, pvals):
                    if pval < 0.05:
                        sig_genes.append(gene)
                        all_genes.add(gene)
                
                cluster_genes[group] = sig_genes[:50]  # Top 50 per cluster
            
            if not all_genes:
                st.warning("⚠️ No significant genes found for enrichment analysis")
                return
            
            st.info(f"Found {len(all_genes)} significant genes across all clusters")
            
            # Initialize g:Profiler
            gp = GProfiler(return_dataframe=True)
            
            # Run GO enrichment
            st.info("Running GO enrichment analysis...")
            go_results = gp.profile(
                organism='hsapiens',
                query=list(all_genes),
                sources=['GO:BP', 'GO:MF', 'GO:CC'],
                user_threshold=0.05,
                significance_threshold_method='fdr'
            )
            
            # Run pathway enrichment
            st.info("Running pathway enrichment analysis...")
            pathway_results = gp.profile(
                organism='hsapiens',
                query=list(all_genes),
                sources=['KEGG', 'REAC', 'WP'],
                user_threshold=0.05,
                significance_threshold_method='fdr'
            )
            
            # Store results in session state
            st.session_state['go_results'] = go_results
            st.session_state['pathway_results'] = pathway_results
            st.session_state['enrichment_done'] = True
            
            st.success("✅ Enrichment analysis completed successfully!")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Enrichment analysis failed: {e}")
            st.info("This might be due to network connectivity or g:Profiler service issues. Please try again.")
            return

    # Show results if enrichment is done
    if st.session_state.get('enrichment_done', False):
        st.success("✅ Enrichment analysis completed successfully!")
        
        # Get results from session state
        go_results = st.session_state.get('go_results', pd.DataFrame())
        pathway_results = st.session_state.get('pathway_results', pd.DataFrame())
        
        # Display summary
        col1, col2 = st.columns(2)
        with col1:
            st.metric("GO Terms Found", len(go_results))
        with col2:
            st.metric("Pathways Found", len(pathway_results))
        
        # Input for number of terms to display
        n_terms = st.number_input(
            "Number of top terms to display", min_value=5, max_value=50, value=15, step=5
        )
        
        # Tabs for different visualizations
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 GO Bar Plot", 
            "🫧 GO Bubble Plot", 
            "🔬 GO Categories", 
            "🕸️ Pathway Network",
            "📈 Comparison",
            "☀️ Sunburst"
        ])
        
        with tab1:
            st.markdown("### 🧬 Interactive GO Terms Bar Plot")
            if len(go_results) > 0:
                go_bar_fig = plot_go_bar_plotly(go_results, n_terms)
                if go_bar_fig:
                    st.plotly_chart(go_bar_fig, use_container_width=True)
                    
                    # Show data table
                    if st.checkbox("Show GO results table", key="show_go_table"):
                        st.dataframe(
                            go_results[['term_name', 'source', 'p_value', 'intersection_size']].head(n_terms),
                            use_container_width=True
                        )
            else:
                st.warning("⚠️ No GO terms found")
        
        with tab2:
            st.markdown("### 🫧 GO Enrichment Bubble Plot")
            if len(go_results) > 0:
                go_bubble_fig = plot_go_bubble_plotly(go_results, n_terms)
                if go_bubble_fig:
                    st.plotly_chart(go_bubble_fig, use_container_width=True)
            else:
                st.warning("⚠️ No GO terms found")
        
        with tab3:
            st.markdown("### 🔬 GO Enrichment by Category")
            if len(go_results) > 0:
                go_faceted_fig = plot_go_faceted_plotly(go_results, n_terms//3)
                if go_faceted_fig:
                    st.plotly_chart(go_faceted_fig, use_container_width=True)
            else:
                st.warning("⚠️ No GO terms found")
        
        with tab4:
            st.markdown("### 🕸️ Pathway Network Visualization")
            if len(pathway_results) > 0:
                pathway_network_fig = plot_pathway_network_plotly(pathway_results, n_terms)
                if pathway_network_fig:
                    st.plotly_chart(pathway_network_fig, use_container_width=True)
                    
                    # Show pathway data table
                    if st.checkbox("Show pathway results table", key="show_pathway_table"):
                        st.dataframe(
                            pathway_results[['term_name', 'source', 'p_value', 'intersection_size']].head(n_terms),
                            use_container_width=True
                        )
            else:
                st.warning("⚠️ No pathways found")
        
        with tab5:
            st.markdown("### 📈 GO vs Pathway Comparison")
            comparison_fig = plot_enrichment_comparison_plotly(go_results, pathway_results)
            if comparison_fig:
                st.plotly_chart(comparison_fig, use_container_width=True)
        
        with tab6:
            st.markdown("### ☀️ Hierarchical Sunburst View")
            sunburst_fig = plot_enrichment_sunburst_plotly(go_results, pathway_results)
            if sunburst_fig:
                st.plotly_chart(sunburst_fig, use_container_width=True)

        # Reset enrichment
        if st.button("♻️ Reset Enrichment Analysis", key="reset_enrichment"):
            st.session_state.pop('enrichment_done', None)
            st.session_state.pop('go_results', None)
            st.session_state.pop('pathway_results', None)
            st.warning("⚠️ Enrichment analysis reset. You'll need to re-run the analysis.")
            st.rerun()
