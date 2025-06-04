import streamlit as st
import os
from interface.layout import layout_sidebar_spacer
from modules.utils.session import create_project, browse_to_open_file

def sidebar_controls():
    if st.sidebar.button("Tabular Analysis", key="tab_analysis", use_container_width=True):
        st.session_state.active_tab = "tabular_analysis" 
    if st.sidebar.button("Image Analysis", key="im_analysis", use_container_width=True):
        st.session_state.active_tab = "image_analysis"
    if st.sidebar.button("scRNAseq Analysis", key="scRNA_analysis", use_container_width=True):
        st.session_state.active_tab = "scRNAseq_analysis"
    if st.sidebar.button("Reader", key="re_der", use_container_width=True):
        st.session_state.active_tab = "reader"
    if st.sidebar.button("Bulk RNASeq", key="bulk_rnaseq", use_container_width=True):
        st.session_state.active_tab = "bulk"
    if st.sidebar.button("Terminal", key="terminal", use_container_width=True):
        st.session_state.active_tab = "terminal"
    
    
    layout_sidebar_spacer(13)
    
    
    if st.sidebar.button("Create Project", use_container_width= True):
        st.session_state.create_project = True

    create_project()

    if st.sidebar.button("Open a file", key= "file_opening", use_container_width=True):
        st.session_state.show_file_browser = True
        
    browse_to_open_file()

    if st.sidebar.button("Clear Uploaded Files", use_container_width=True):
        st.session_state.original_df = {}
        st.session_state.modified_df = {}
        st.session_state.uploaded_pdf = None

    if st.sidebar.button("Clear Chat History", use_container_width=True):
        st.session_state.messages = []




