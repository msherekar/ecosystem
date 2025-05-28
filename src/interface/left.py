import streamlit as st
import pandas as pd
from src.interface.layout import layout_sidebar_spacer
from src.modules.utils.upload import create_project, browse_to_open_file, handle_rnaseq_upload, handle_scrnaseq_upload

def sidebar_controls():
    # --- Sidebar Navigation ---
    with st.sidebar:
        for label, key in [
            ("Tabular Analysis", "tabular_analysis"),
            ("Image Analysis", "image_analysis"),
            ("RNAseq Analysis", "rnaseq_analysis"),  # RE-ENABLED: Local analysis doesn't use API
            ("scRNAseq Analysis", "scRNAseq_analysis"),
            ("Reader", "reader"),
            ("Search", "search"),
        ]:
            if st.button(label, use_container_width=True, key=f"{key}_btn"):
                # Reset all analysis flags first
                st.session_state.tabular_analysis = False
                st.session_state.image_analysis = False
                st.session_state.rnaseq_analysis = False
                st.session_state.scRNAseq_analysis = False
                st.session_state.reader = False
                st.session_state.search = False
                
                # Set the active tab and corresponding analysis flag
                st.session_state.active_tab = key
                st.session_state[key] = True

        layout_sidebar_spacer(1)

        if st.button("Create Project", use_container_width=True):
            st.session_state.create_project = True
        create_project()

        if st.button("Open a file", use_container_width=True):
            st.session_state.show_file_browser = True
        browse_to_open_file()

        if st.button("Clear Uploaded Files", use_container_width=True):
            st.session_state.original_df = {}
            st.session_state.modified_df = {}
            st.session_state.uploaded_pdf = None

        if st.button("Clear Chat History", use_container_width=True):
            st.session_state.messages = []

        # --- RNAseq Upload --- RE-ENABLED: Local analysis doesn't use API
        if st.session_state.get("active_tab") == "rnaseq_analysis":
            handle_rnaseq_upload()

        # --- scRNAseq Upload ---
        if st.session_state.get("active_tab") == "scRNAseq_analysis":
            handle_scrnaseq_upload()


