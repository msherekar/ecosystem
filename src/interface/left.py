import streamlit as st
import os

def sidebar_controls():
    st.sidebar.checkbox("Tabular Analysis", key="tabular_analysis")
    st.sidebar.checkbox("Image Analysis", key="image_analysis")
    st.sidebar.checkbox("scRNAseq Analysis", key="scRNAseq_analysis")
    st.sidebar.checkbox("Reader", key="reader")
    st.sidebar.checkbox("Search", key="search")

    if st.sidebar.button("Create Project", use_container_width=True):
        st.session_state.create_project = True

    if st.session_state.create_project:
        project_name = st.sidebar.text_input("Enter the project name", key="enter_project_name")
        if project_name:
            try:
                os.makedirs(project_name, exist_ok=False)
                st.session_state.project_name = project_name
                st.sidebar.success(f"Project '{project_name}' created successfully.")
            except FileExistsError:
                st.sidebar.error(f"A folder named '{project_name}' already exists.")
            except Exception as e:
                st.sidebar.error(f"An error occurred: {e}")
            else:
                st.session_state.create_project = False
                st.rerun()

    if st.sidebar.button("Clear Uploaded Files", use_container_width=True):
        st.session_state.uploaded_df = {}
        st.session_state.uploaded_pdf = None

    if st.sidebar.button("Clear Chat History", use_container_width=True):
        st.session_state.messages = []
