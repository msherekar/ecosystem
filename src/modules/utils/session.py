import streamlit as st

def initialize_session_state():
    """Initialize all session state variables with default values."""
    
    # Analysis mode flags
    if "tabular_analysis" not in st.session_state:
        st.session_state.tabular_analysis = False
    if "image_analysis" not in st.session_state:
        st.session_state.image_analysis = False
    if "scRNAseq_analysis" not in st.session_state:
        st.session_state.scRNAseq_analysis = False
    if "rnaseq_analysis" not in st.session_state:
        st.session_state.rnaseq_analysis = False
    if "reader" not in st.session_state:
        st.session_state.reader = False
    if "search" not in st.session_state:
        st.session_state.search = False
    
    # UI system selection
    if "use_technique_ui" not in st.session_state:
        st.session_state.use_technique_ui = True  # Use new scalable UI by default
    
    # Active tab tracking
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = None
    
    # Chat system
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Data storage
    if "original_df" not in st.session_state:
        st.session_state.original_df = {}
    if "modified_df" not in st.session_state:
        st.session_state.modified_df = {}
    if "uploaded_pdf" not in st.session_state:
        st.session_state.uploaded_pdf = None
    
    # Search functionality
    if "pubmed_search" not in st.session_state:
        st.session_state.pubmed_search = False
    if "pubmed_search_query" not in st.session_state:
        st.session_state.pubmed_search_query = ""
    if "geo_search_query" not in st.session_state:
        st.session_state.geo_search_query = ""
    
    # User preferences
    if "user_interest" not in st.session_state:
        st.session_state.user_interest = ""
    
    # File browser
    if "show_file_browser" not in st.session_state:
        st.session_state.show_file_browser = False
    if "create_project" not in st.session_state:
        st.session_state.create_project = False
    
    # Agent requests
    if "agent_requested_rnaseq" not in st.session_state:
        st.session_state.agent_requested_rnaseq = False
    if "agent_requested_scrnaseq" not in st.session_state:
        st.session_state.agent_requested_scrnaseq = False
    if "agent_requested_tabular" not in st.session_state:
        st.session_state.agent_requested_tabular = False
    if "agent_requested_image" not in st.session_state:
        st.session_state.agent_requested_image = False
    if "agent_requested_reader" not in st.session_state:
        st.session_state.agent_requested_reader = False
    if "agent_requested_search" not in st.session_state:
        st.session_state.agent_requested_search = False
    
    # scRNA-seq pipeline state
    if "scrna_current_step" not in st.session_state:
        st.session_state.scrna_current_step = "qc"  # Start with Quality Control
