import streamlit as st
from src.modules.scrna_seq.tracking import _status

def create_visualization():
    with st.expander(_status("7. UMAP Visualization")):
        # First show any action buttons that might need to run regardless of other checkboxes
        col1, col2 = st.columns(2)
        
        with col1:
            # Button to run UMAP if missing
            if not st.session_state.get("has_umap", False) and "adata" in st.session_state:
                if st.button("🔄 Run UMAP", key="run_umap_fix"):
                    adata = st.session_state["adata"]
                    # Make sure we have neighbors first
                    try:
                        sc.pp.neighbors(adata)
                        sc.tl.umap(adata)
                        st.session_state["adata"] = adata
                        st.session_state["has_umap"] = True
                        if st.session_state.get("has_leiden", False):
                            st.session_state["clustered"] = True
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Error running UMAP: {str(e)}")
        
        with col2:
            # Button to run Leiden if missing
            if not st.session_state.get("has_leiden", False) and "adata" in st.session_state:
                if st.button("🔄 Run Leiden", key="run_leiden_fix"):
                    adata = st.session_state["adata"]
                    try:
                        sc.tl.leiden(adata)
                        st.session_state["adata"] = adata
                        st.session_state["has_leiden"] = True
                        if st.session_state.get("has_umap", False):
                            st.session_state["clustered"] = True
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Error running Leiden: {str(e)}")
        
        # Now handle the main visualization
        if st.checkbox("▶️ Show UMAP", key="show_umap"):
            if "adata" not in st.session_state:
                st.warning("⚠️ No AnnData object found in session.")
                return
                
            adata = st.session_state["adata"]
            st.write("✅ adata loaded")
            st.write("🔍 Has UMAP:", st.session_state.get("has_umap", 'X_umap' in adata.obsm))
            st.write("🔍 Has Leiden:", st.session_state.get("has_leiden", 'leiden' in adata.obs))
            
            # Update the state flags based on actual data
            has_umap = 'X_umap' in adata.obsm
            has_leiden = 'leiden' in adata.obs
            st.session_state["has_umap"] = has_umap
            st.session_state["has_leiden"] = has_leiden
            
            if not has_umap or not has_leiden:
                st.warning("⚠️ Clustering is incomplete. Please use the buttons above to complete the process.")
                return
                
            try:
                # If everything is available, create the plot
                fig = sc.pl.umap(adata, color="leiden", return_fig=True, show=False)
                st.pyplot(fig)
                
                # Add option to save the figure
                if st.button("💾 Save UMAP figure", key="save_umap"):
                    fig.savefig("umap_clusters.png", dpi=300, bbox_inches='tight')
                    st.success("Figure saved as 'umap_clusters.png'")
                
            except Exception as e:
                st.error(f"Error visualizing UMAP: {str(e)}")
                import traceback
                st.code(traceback.format_exc())