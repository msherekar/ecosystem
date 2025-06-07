import streamlit as st
from src.modules.reader.pubmed import fetch_pubmed_with_abstract, display_pubmed_with_abstract
from src.modules.search.geo import geo_search, geo_display
from src.modules.reader.pubmed import reader
from src.interface.technique_ui import technique_registry
from src.chat.chatbot import ask_chatbot
from src.interface.welcome import show_welcome_message


def is_rnaseq_ready():
    """
    Check if RNAseq data is ready for analysis
    """
    return (
        "rnaseq_counts_df" in st.session_state and
        "rnaseq_metadata_df" in st.session_state
    )


def is_scrnaseq_ready():
    """
    Check if scRNAseq data is ready for analysis
    """
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
        
        # Get current active tab
        tab = st.session_state.active_tab
        
        # Show welcome message if no valid tab is selected
        if tab not in ["tabular_analysis", "image_analysis", "scRNAseq_analysis", "reader", "bulk", "terminal"]:
            show_welcome_message(center_area)
            return

        # Handle each analysis type
        if tab == "tabular_analysis" or st.session_state.get("agent_requested_tabular", False):
            st.markdown("### 📊 Tabular Analysis")
            from src.modules.data import tabular
            tabular.tabular_data()

        elif tab == "bulk" or st.session_state.get("agent_requested_rnaseq", False):
            st.markdown("### 🧬 Bulk RNAseq Analysis")
            if is_rnaseq_ready():
                from src.modules.rna_seq.workflow import run_rnaseq_pipeline
                run_rnaseq_pipeline()
            else:
                st.info("Please upload RNAseq data to begin analysis.")

        elif tab == "scRNAseq_analysis" or st.session_state.get("agent_requested_scrnaseq", False):
            st.markdown("### 🔬 scRNAseq Analysis")
            if is_scrnaseq_ready():
                from src.modules.scrna_seq.workflow import run_scrnaseq_pipeline
                run_scrnaseq_pipeline()
            else:
                st.info("Please upload scRNAseq data to begin analysis.")

        elif tab == "image_analysis" or st.session_state.get("agent_requested_image", False):
            st.markdown("### 🖼️ Image Analysis")
            from src.modules.image_analysis.image import image_main
            image_main()

        elif tab == "reader" or st.session_state.get("agent_requested_reader", False):
            st.markdown("### 📚 Document Reader")
            if st.session_state.uploaded_pdf_path is None:
                user_interest = st.session_state.user_interest
                reader(user_interest)
            else:
                from src.modules.reader.pubmed import display_pdf
                display_pdf(st.session_state.uploaded_pdf_path)

        elif tab == "terminal":
            st.markdown("### 💻 Terminal")
            from src.modules.terminal import terminal
            terminal.terminal()

        # Handle PubMed search results
        if st.session_state.pubmed_search:
            st.markdown("### 🔍 PubMed Search Results")
            if st.session_state.pubmed_search_query.strip():
                articles_info = fetch_pubmed_with_abstract(st.session_state.pubmed_search_query)
                display_pubmed_with_abstract(articles_info)
            else:
                st.warning("Search query cannot be empty.")
            st.session_state.pubmed_search = False

        # Handle GEO search results
        if st.session_state.geo_search:
            st.markdown("### 🔍 GEO Search Results")
            if st.session_state.geo_search_query.strip():
                geo_results = geo_search(st.session_state.geo_search_query)
                geo_display(geo_results)
            else:
                st.warning("Search query cannot be empty.")
            st.session_state.geo_search = False





