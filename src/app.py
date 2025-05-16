import streamlit as st
import logging

from interface.layout import layout_columns
from interface.left import sidebar_controls
from interface.welcome import show_welcome_message
from interface.right import chat_interface
from interface.center import display_results_in_center

# Set up logging
logging.basicConfig(level=logging.INFO)

# --- Streamlit Setup ---
st.set_page_config(page_title="Scientific Database Assistant", layout="wide")

# --- Session State Defaults ---
for key, default in {
    "tabular_analysis": False,
    "image_analysis": False,
    "scRNAseq_analysis": False,
    "reader": False,
    "RNAseq_analysis": False,  
    "welcome_message": "",
    "search": False,
    "user_interaction": False,
    "results_history": [],
}.items():
    st.session_state.setdefault(key, default)

# --- Sidebar ---
sidebar_controls()

# --- Layout ---
data_col, chat_col = layout_columns()

# --- Main Content ---
if st.session_state.user_interaction:
    # Check if any search results need to be displayed
    has_search_results = (
        st.session_state.results_history and 
        st.session_state.search
    )
    
    # Log session state for debugging
    logging.info(f"Session state - search: {st.session_state.search}, " +
                f"results_history: {len(st.session_state.results_history)} items")
    
    # If user interacted with the chat, display search results in the main data column
    if has_search_results:
        # Log that we're going to display search results
        logging.info("Displaying search results in center panel")
        display_results_in_center(data_col)
    
    elif st.session_state.tabular_analysis:
        with data_col:
            st.header("Tabular Analysis")
            st.info("Tabular analysis module would be displayed here")
    elif st.session_state.image_analysis:
        with data_col:
            st.header("Image Analysis")
            st.info("Image analysis module would be displayed here")
    elif st.session_state.scRNAseq_analysis:
        with data_col:
            st.header("scRNAseq Analysis")
            st.info("scRNAseq analysis module would be displayed here")
    elif st.session_state.RNAseq_analysis:
        with data_col:
            st.header("RNAseq Analysis")
            st.info("RNAseq analysis module would be displayed here")
    elif st.session_state.reader:
        with data_col:
            st.header("Document Reader")
            st.info("Document reader module would be displayed here")
    else:
        # No specific module active, but user has interacted
        with data_col:
            st.header("Gliaent")
            st.info("")
else:
    # Show welcome message for first-time users
    show_welcome_message(data_col)

# --- Chat Column (full height) ---
with chat_col:
    # Render the chat interface
    chat_interface()
