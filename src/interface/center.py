import streamlit as st
from src.modules.reader.pubmed import fetch_pubmed_with_abstract, display_pubmed_with_abstract
from src.modules.search.geo import geo_search, geo_display
from src.modules.reader.pubmed import reader
from src.interface.technique_ui import technique_registry


def is_rnaseq_ready():
    return (
        "rnaseq_counts_df" in st.session_state and
        "rnaseq_metadata_df" in st.session_state
    )
    # RNA-seq analysis itself doesn't use API - only agent interactions do

def is_scrnaseq_ready():
    return (
        "anndata" in st.session_state and
        st.session_state.anndata is not None
    )

def render_center_panel(center_area):
    """
    Renders the center panel content (main analysis area) in the provided layout area
    
    Args:
        center_area: Streamlit column/container for the center panel
    """
    with center_area:
        # Additional CSS to force top alignment
        st.markdown("""
        <style>
        /* Force this specific column to top */
        div[data-testid="column"]:nth-child(2) {
            margin-top: 0rem !important;
            padding-top: 0rem !important;
        }
        
        /* Force heading to top */
        h1 {
            margin-top: 0rem !important;
            padding-top: 0rem !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Main heading for the center panel
        #st.markdown("# Integrated Analysis Environment")
        #st.info("Select an analysis type from the left panel to begin.")
        
        # Show message when no analysis is active
        if not any([
            st.session_state.tabular_analysis,
            st.session_state.image_analysis,
            st.session_state.scRNAseq_analysis,
            st.session_state.rnaseq_analysis,
            st.session_state.reader,
            st.session_state.search,
            st.session_state.get("agent_requested_rnaseq", False),
            st.session_state.get("agent_requested_scrnaseq", False),
            st.session_state.get("agent_requested_tabular", False),
            st.session_state.get("agent_requested_image", False),
            st.session_state.get("agent_requested_reader", False),
            st.session_state.get("agent_requested_search", False)
        ]):
            pass  # Content was commented out, keeping block valid
            # st.markdown("### 🔬 Analysis Workspace")
            # st.info("👈 Select an analysis type from the left panel to begin your work.")
            
            # Show a helpful overview
            # with st.expander("📋 Available Analysis Types", expanded=True):
            #     st.markdown("""
            #     **📊 Tabular Analysis:** Work with CSV, Excel, and other structured data
                
            #     **🖼️ Image Analysis:** Process and analyze images
                
            #     **🧬 RNAseq Analysis:** Differential gene expression analysis
                
            #     **🔬 scRNAseq Analysis:** Single-cell RNA sequencing analysis
                
            #     **📚 Reader:** View and analyze PDF documents
                
            #     **🔍 Search:** Search scientific databases and resources
            #     """)

        # Reader functionality
        if st.session_state.reader or st.session_state.get("agent_requested_reader", False):
            st.markdown("### Document Reader")
            reader(st.session_state.user_interest)

        # PubMed search
        if st.session_state.pubmed_search:
            st.markdown("### PubMed Search Results")
            if st.session_state.pubmed_search_query.strip():
                articles_info = fetch_pubmed_with_abstract(st.session_state.pubmed_search_query)
                display_pubmed_with_abstract(articles_info)
            else:
                st.warning("Search query cannot be empty.")
            st.session_state.pubmed_search = False
            st.session_state.pubmed_search_query = ''

        # GEO search
        if st.session_state.search or st.session_state.get("agent_requested_search", False):
           # st.markdown("### Search")
            if st.session_state.geo_search_query.strip():
                results = geo_search(st.session_state.geo_search_query)
                geo_display(results)
            else:
                st.warning("Search Pubmed or Geo.")
            st.session_state.geo_search = False
            st.session_state.geo_search_query = ''
        
        # RNA-seq analysis - using scalable technique UI
        if st.session_state.get("rnaseq_analysis") or st.session_state.get("agent_requested_rnaseq"):
            #st.markdown("### 🧬 RNA-seq Analysis")
            rnaseq_ui = technique_registry.get_technique_ui("rnaseq")
            if rnaseq_ui:
                rnaseq_ui.render()
            else:
                st.error("RNA-seq technique not found in registry")

        # scRNA-seq analysis - using scalable technique UI  
        if st.session_state.get("scRNAseq_analysis") or st.session_state.get("agent_requested_scrnaseq"):
            #st.markdown("### 🔬 Single-cell RNA-seq Analysis")
            scrnaseq_ui = technique_registry.get_technique_ui("scrnaseq")
            if scrnaseq_ui:
                scrnaseq_ui.render()
            else:
                st.error("scRNA-seq technique not found in registry")

        # Tabular analysis
        if st.session_state.tabular_analysis or st.session_state.get("agent_requested_tabular", False):
            #st.markdown("### 📊 Tabular Data Analysis")
            st.info("Tabular analysis workspace is ready. Upload data files from the left panel to begin.")
            
            # Show uploaded files if any
            if st.session_state.get("original_df"):
                st.markdown("**📁 Uploaded Files:**")
                for filename in st.session_state.original_df.keys():
                    st.write(f"📄 {filename}")
            
        # Image analysis
        if st.session_state.image_analysis or st.session_state.get("agent_requested_image", False):
            #st.markdown("### 🖼️ Image Analysis")
            st.info("Image analysis workspace is ready. Upload image files from the left panel to begin.")





