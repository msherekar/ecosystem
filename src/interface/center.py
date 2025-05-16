import streamlit as st
import logging
import os
import uuid
from datetime import datetime
from openai import OpenAI

# Set up logging
logging.basicConfig(level=logging.INFO)

def display_chatbot_response(response, prompt):
    """Process and display a chatbot response in both chat interface and center area"""
    logging.info(f"Processing chatbot response of type: {type(response)}")
    
    # Extract content from response (different formats handled)
    if isinstance(response, dict):
        content = response.get("content", "No content provided")
        # Source will indicate which system processed the response
        source = response.get("source", "")
    else:
        content = response.content if hasattr(response, "content") else str(response)
        source = ""
    
    # Display in chat interface
    with st.chat_message("assistant"):
        st.markdown(content)
    
    # Add to messages for context in future exchanges
    if 'messages' in st.session_state:
        st.session_state.messages.append({"role": "assistant", "content": content})
    
    # Add to results history
    result_id = str(uuid.uuid4())
    
    # Determine database type from source
    database_type = "general"
    if source:
        if "geo" in source.lower():
            database_type = "geo"
        elif "tcga" in source.lower():
            database_type = "tcga"
        elif "uniprot" in source.lower():
            database_type = "uniprot"
    
    result = {
        "id": result_id,
        "query": prompt,
        "content": content,
        "source": source or "API",
        "database_type": database_type,  # Store database type in the result
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    st.session_state.results_history.append(result)
    st.session_state.active_result_id = result_id
    
    # Activate search to show results in center panel
    # Using a boolean flag as in your original code
    st.session_state.search = True
    
    return result

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
                    database_type = active_result.get('database_type', 'general')
                    
                    # Debug log to help diagnose issues
                    logging.info(f"Result source: {source}")
                    logging.info(f"Result database_type: {database_type}")
                    logging.info(f"Result content first 100 chars: {content[:100]}")
                    
                    # Set display name based on database_type
                    if database_type == "geo":
                        db_type = "GEO"
                    elif database_type == "tcga":
                        db_type = "TCGA"
                    elif database_type == "uniprot":
                        db_type = "UniProt"
                    else:
                        # Fallback to determine from content if needed
                        if "geo" in source.lower() or "geo results" in content.lower():
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
                        database_type = result.get('database_type', 'general')
                        
                        # Set display label based on database_type
                        if database_type == "geo":
                            label = "GEO"
                        elif database_type == "tcga":
                            label = "TCGA"
                        elif database_type == "uniprot":
                            label = "UniProt"
                        else:
                            # Fallback to content-based determination
                            if "geo" in source.lower() or "geo results" in content.lower():
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
                    st.session_state.search = False
                    st.rerun()
        else:
            st.error("No search results to display. Try making a search query.")
            logging.warning("display_results_in_center called but results_history is empty")
