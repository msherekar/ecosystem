import streamlit as st
import logging
import os
from openai import OpenAI

# Set up logging
logging.basicConfig(level=logging.INFO)

def display_results_in_center(data_col):
    """Display the search results in the data column"""
    logging.info(f"Displaying results in center panel. Results history: {len(st.session_state.results_history)} items")
    
    with data_col:
        # Add tabs for result history
        if st.session_state.results_history:
            # Create a container for the results with max height
            results_container = st.container()
            
            # Display the active result first
            active_result = None
            for result in st.session_state.results_history:
                if result["id"] == st.session_state.get("active_result_id"):
                    active_result = result
                    break
            
            if active_result:
                logging.info(f"Found active result: {active_result.get('id')} - {active_result.get('query')}")
                
                with results_container:
                    # Extract database type from source or content for a more specific header
                    source = active_result.get('source', '')
                    content = active_result.get('content', '')
                    
                    # Debug log to help diagnose issues
                    logging.info(f"Result source: {source}")
                    logging.info(f"Result content first 100 chars: {content[:100]}")
                    
                    if "geo" in source.lower() or "geo results" in content:
                        db_type = "GEO"
                    elif "tcga" in source.lower() or "tcga" in content.lower():
                        db_type = "TCGA"
                    elif "uniprot" in source.lower() or "uniprot" in content.lower():
                        db_type = "UniProt"
                    else:
                        db_type = "Database"
                    
                    st.header(f"{db_type} Results: {active_result['query']}")
                    
                    # Add source badge
                    source_label = "🧠 Local Processing" if "local" in source else "☁️ OpenAI API"
                    st.caption(f"Source: {source_label}")
                    
                    # Display the content directly first for debugging
                    with st.expander("Debug: Raw Content", expanded=False):
                        st.text(f"Content length: {len(content)} characters")
                        st.text(content[:500] + "..." if len(content) > 500 else content)
                    
                    # Display the content in a card for better visual separation
                    st.markdown("""
                    <style>
                    .result-card {
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        padding: 20px;
                        background-color: #f9f9f9;
                        overflow-wrap: break-word;
                        max-width: 100%;
                        margin: 10px 0;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    # Display the content without using a custom HTML container, for simplicity
                    st.markdown(content)
            else:
                logging.warning(f"No active result found. Active ID: {st.session_state.get('active_result_id')}")
                st.error("No active result found. Try making a new search query.")
            
            # Create a horizontal line to separate current and previous results
            st.markdown("---")
            
            # Display previous results in reverse chronological order (newest first)
            if len(st.session_state.results_history) > 1:
                st.subheader("Previous Results")
                for result in reversed(st.session_state.results_history):
                    # Skip the active result as it's already shown
                    if result["id"] != st.session_state.get("active_result_id"):
                        # Determine the database type for each result
                        source = result.get('source', '')
                        content = result.get('content', '')
                        
                        if "geo" in source.lower() or "geo results" in content:
                            label = "GEO"
                        elif "tcga" in source.lower() or "tcga" in content.lower():
                            label = "TCGA"
                        elif "uniprot" in source.lower() or "uniprot" in content.lower():
                            label = "UniProt"
                        else:
                            label = "Search"
                        
                        with st.expander(f"{label}: {result['query']} ({result['timestamp']})"):
                            st.markdown(result['content'])
                            
                            # Add a button to make this the active result
                            if st.button(f"Show in main view", key=f"btn_{result['id']}"):
                                st.session_state.active_result_id = result["id"]
                                st.rerun()
            
            # Add buttons for further analysis of the active result
            st.markdown("### Actions")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Download Data", use_container_width=True):
                    st.info("Download functionality would be implemented here")
            
            with col2:
                if st.button("Visualize", use_container_width=True):
                    st.info("Visualization functionality would be implemented here")
            with col3:
                if st.button("Clear Results", use_container_width=True):
                    st.session_state.results_history = []
                    st.session_state.search["active"] = False
                    st.session_state.search["type"] = None
                    st.session_state.search["database"] = None
                    st.rerun()
        else:
            st.error("No search results to display. Try making a search query.")
            logging.warning("display_results_in_center called but results_history is empty")
