import streamlit as st
from src.modules.reader.pubmed import fetch_pubmed_with_abstract, display_pubmed_with_abstract
from src.modules.search.geo import geo_search, geo_display
from src.modules.reader.pubmed import reader
from src.interface.technique_ui import technique_registry
from src.modules.search.registry import search_registry, initialize_search_registry


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

        # Database search results (using search registry)
        if st.session_state.search or st.session_state.get("agent_requested_search", False):
            # Import search registry
            initialize_search_registry()
            
            # Initialize search history if not exists
            if "search_history" not in st.session_state:
                st.session_state["search_history"] = []
            
            # Check if we have NEW results from the agent
            if st.session_state.get("search_results"):
                print("🔧 DEBUG: Displaying search results from agent in center panel")
                results = st.session_state["search_results"]
                
                # Add to search history (avoid duplicates)
                query = results.get("query", "Unknown query")
                provider = results.get("provider", "unknown")
                
                # Check if this is a new search (different query or provider)
                is_new_search = True
                if st.session_state["search_history"]:
                    last_search = st.session_state["search_history"][-1]
                    if (last_search.get("query") == query and 
                        last_search.get("provider") == provider):
                        is_new_search = False
                
                if is_new_search:
                    # Add new search to history
                    search_entry = {
                        "query": query,
                        "provider": provider,
                        "provider_display_name": results.get("provider_display_name", provider),
                        "results": results,
                        "timestamp": st.session_state.get("_search_timestamp", "recent")
                    }
                    st.session_state["search_history"].append(search_entry)
                    
                    # Keep only last 5 searches to avoid memory issues
                    if len(st.session_state["search_history"]) > 5:
                        st.session_state["search_history"] = st.session_state["search_history"][-5:]
                
                # Clear the temporary results (but keep in history)
                del st.session_state["search_results"]
                st.session_state["agent_requested_search"] = False
            
            # Display all search results from history
            if st.session_state["search_history"]:
                print(f"🔧 DEBUG: Displaying {len(st.session_state['search_history'])} search results from history")
                
                # Show most recent searches first
                for i, search_entry in enumerate(reversed(st.session_state["search_history"])):
                    results = search_entry["results"]
                    provider_name = search_entry["provider_display_name"]
                    query = search_entry["query"]
                    
                    # Create a unique header for each search
                    search_num = len(st.session_state["search_history"]) - i
                    with st.expander(f"🔬 {provider_name}: '{query}' ({search_entry['timestamp']})", 
                                   expanded=(i == 0)):  # Expand only the most recent
                        
                        # Use registry to display results
                        search_registry.display_results(results)
                        
                        # Add clear button for this specific search
                        col1, col2 = st.columns([1, 4])
                        with col1:
                            if st.button(f"Clear", key=f"clear_search_{search_num}"):
                                # Remove this specific search from history
                                actual_index = len(st.session_state["search_history"]) - 1 - i
                                st.session_state["search_history"].pop(actual_index)
                                st.rerun()
                
                # Add button to clear all search history
                st.markdown("---")
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button("🗑️ Clear All Search History", type="secondary"):
                        st.session_state["search_history"] = []
                        st.rerun()
                
            # Handle manual search from left panel (legacy GEO search)
            elif st.session_state.geo_search_query.strip():
                print("🔧 DEBUG: Performing manual GEO search in center panel")
                st.markdown("### 🔬 GEO Search Results")
                results = geo_search(st.session_state.geo_search_query)
                geo_display(results)
                st.session_state.geo_search = False
                st.session_state.geo_search_query = ''
            else:
                if not st.session_state["search_history"]:
                    st.info("🔍 Search databases using the chat or left panel.")
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





