import streamlit as st
from src.modules.reader.pubmed import fetch_pubmed_with_abstract, display_pubmed_with_abstract
from src.modules.search.geo import geo_search, geo_display
from src.modules.reader.pubmed import reader
from src.interface.technique_ui import technique_registry


class GenericTechniqueUI:
    def __init__(self, config: TechniqueConfig):
        self.config = config  # Technique-specific configuration
    
    def _show_technique_header(self, context):
        # Uses config.icon, config.title - different per technique
        st.markdown(f"## {self.config.icon} {self.config.title}")
        
        # Shows progress IF technique has pipeline
        if context.get("has_pipeline"):
            self._show_progress_bar(context)
    
    def _show_automated_section(self, context):
        # Button key is technique-specific to avoid conflicts
        if st.button("🚀 Run All Steps", key=f"run_all_{self.config.server_name}"):
            # Calls technique-specific automated pipeline
            self._run_automated_pipeline()

def is_rnaseq_ready():
    return (
        "rnaseq_counts_df" in st.session_state and
        "rnaseq_metadata_df" in st.session_state
    )

def is_scrnaseq_ready():
    return (
        "anndata" in st.session_state and
        st.session_state.anndata is not None
    )

def render_center_panel(data_col):
    with data_col:
        # Show default message when no analysis is active
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
            st.markdown("## 🧬 Integrated Analysis Environment")
            st.info("Select an analysis type from the left panel to begin.")

        if st.session_state.reader or st.session_state.get("agent_requested_reader", False):
            reader(st.session_state.user_interest)

        if st.session_state.pubmed_search:
            if st.session_state.pubmed_search_query.strip():
                articles_info = fetch_pubmed_with_abstract(st.session_state.pubmed_search_query)
                display_pubmed_with_abstract(articles_info)
            else:
                st.warning("Search query cannot be empty.")
            st.session_state.pubmed_search = False
            st.session_state.pubmed_search_query = ''

        if st.session_state.search or st.session_state.get("agent_requested_search", False):
            if st.session_state.geo_search_query.strip():
                results = geo_search(st.session_state.geo_search_query)
                geo_display(results)
            else:
                st.warning("Search query cannot be empty.")
            st.session_state.geo_search = False
            st.session_state.geo_search_query = ''
        
        # RNA-seq analysis - using scalable technique UI
        if st.session_state.get("rnaseq_analysis") or st.session_state.get("agent_requested_rnaseq"):
            rnaseq_ui = technique_registry.get_technique_ui("rnaseq")
            if rnaseq_ui:
                rnaseq_ui.render()
            else:
                st.error("RNA-seq technique not found in registry")

        # scRNA-seq analysis - using scalable technique UI  
        if st.session_state.get("scRNAseq_analysis") or st.session_state.get("agent_requested_scrnaseq"):
            scrnaseq_ui = technique_registry.get_technique_ui("scrnaseq")
            if scrnaseq_ui:
                scrnaseq_ui.render()
            else:
                st.error("scRNA-seq technique not found in registry")

        # Tabular analysis
        if st.session_state.tabular_analysis or st.session_state.get("agent_requested_tabular", False):
            st.info("Tabular analysis mode is active")
            
        # Image analysis
        if st.session_state.image_analysis or st.session_state.get("agent_requested_image", False):
            st.info("Image analysis mode is active")




