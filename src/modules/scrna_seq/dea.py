import streamlit as st
from src.modules.scrna_seq.tracking import _status

def run_differential_expression():
    with st.expander(_status("8. Differential Expression")):
        # Check for leiden data availability first
        if "adata" in st.session_state:
            adata = st.session_state["adata"]
            has_leiden = st.session_state.get("has_leiden", 'leiden' in adata.obs)
            
            if not has_leiden:
                st.warning("⚠️ Leiden clustering results not found. Please run clustering first.")
                
                # Offer a quick fix button
                if st.button("🔄 Run Leiden Clustering", key="run_leiden_for_deg"):
                    try:
                        # Check if we need to compute neighbors first
                        if 'neighbors' not in adata.uns:
                            st.info("Computing neighbors first...")
                            sc.pp.neighbors(adata)
                        
                        sc.tl.leiden(adata)
                        st.session_state["adata"] = adata
                        st.session_state["has_leiden"] = True
                        if st.session_state.get("has_umap", False):
                            st.session_state["clustered"] = True
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Error running Leiden clustering: {str(e)}")
                return
        
        # Now perform DEG analysis if conditions are met
        if st.checkbox("▶️ Run DEG", key="run_deg") and not st.session_state.get("deg_done"):
            try:
                adata = st.session_state["adata"]
                
                # Double-check leiden exists before proceeding
                if 'leiden' not in adata.obs:
                    st.error("Leiden clustering results not found. Cannot perform differential expression.")
                    return
                
                # Run the differential expression analysis
                st.info("Running differential expression analysis...")
                sc.tl.rank_genes_groups(adata, "leiden", method="t-test")
                
                # Check if the analysis was successful
                if 'rank_genes_groups' not in adata.uns:
                    st.error("Differential expression analysis failed. No results found.")
                    return
                    
                # Plot the results
                fig = sc.pl.rank_genes_groups(adata, sharey=False, return_fig=True, show=False)
                st.pyplot(fig)
                
                # Save state
                st.session_state["adata"] = adata
                st.session_state["deg_done"] = True
                st.success("✅ Differential expression analysis completed successfully.")
                
            except Exception as e:
                st.error(f"Error during differential expression analysis: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
                
        elif st.session_state.get("deg_done"):
            st.info("✅ DEG already run.")
            
            # Option to show the results again
            if st.button("🔍 Show DEG Results Again", key="show_deg_again"):
                try:
                    adata = st.session_state["adata"]
                    fig = sc.pl.rank_genes_groups(adata, sharey=False, return_fig=True, show=False)
                    st.pyplot(fig)
                except Exception as e:
                    st.error(f"Error displaying results: {str(e)}")

        if st.button("♻️ Reset DEG", key="reset_deg"):
            st.session_state["deg_done"] = False
            st.experimental_rerun()