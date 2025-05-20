import streamlit as st

def initialize_session_state():
    defaults = {
        "welcome_message": "",
        "messages": [],
        "uploaded_df": {},
        "project_name": "",
        "uploaded_pdf": None,
        "tabular_analysis": False,
        "image_analysis": False,
        "rnaseq_analysis": False,
        "scRNAseq_analysis": False,
        "reader": False,
        "pubmed_search": False,
        "pubmed_search_query": "",
        "search": False,
        "geo_search": False,
        "geo_search_query": "",
        "create_project": False,
        "user_interest": "cancer"
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
