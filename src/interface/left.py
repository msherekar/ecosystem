import streamlit as st
import os
import pandas as pd
from modules.scrna_seq.upload import handle_uploaded_files


def sidebar_controls():
    st.sidebar.checkbox("Tabular Analysis", key="tabular_analysis")
    st.sidebar.checkbox("Image Analysis", key="image_analysis")
    st.sidebar.checkbox("RNAseq Analysis", key="rnaseq_analysis")
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
    
    # trigger first step of RNAseq analysis i.e upload counts file
        # --- RNAseq file upload ---
    if st.session_state.get("rnaseq_analysis", False):
        uploaded_file = st.sidebar.file_uploader("Upload RNA-seq counts file (.csv or .tsv)", type=["csv", "tsv"], key="rnaseq_counts_uploader")

        if uploaded_file:
            try:
                 # Read first 1KB to infer delimiter
                sample = uploaded_file.read(1024).decode("utf-8")
                uploaded_file.seek(0)  # rewind for full read

                # Infer delimiter
                delimiter = "\t" if sample.count("\t") > sample.count(",") else ","

                df = pd.read_csv(uploaded_file, sep=delimiter)

                
                st.session_state["rnaseq_counts_df"] = df
                st.session_state["rnaseq_counts_filename"] = uploaded_file.name
                st.sidebar.success("File uploaded and parsed successfully!")
            except Exception as e:
                st.sidebar.error(f"Error loading file: {e}")
    
        # Upload metadata
        metadata_file = st.sidebar.file_uploader("Upload metadata file (CSV)", type=["csv"], key="rnaseq_metadata_uploader")

        if metadata_file:
            try:
                # Expect: sample IDs in index, and a 'condition' column
                metadata_df = pd.read_csv(metadata_file, index_col=0)
                
                # Validate condition column
                if "condition" not in metadata_df.columns:
                    st.sidebar.error("Metadata must include a column named 'condition'.")
                else:
                    st.session_state["rnaseq_metadata_df"] = metadata_df
                    st.session_state["rnaseq_metadata_filename"] = metadata_file.name
                    st.sidebar.success("✅ Metadata uploaded successfully.")
            except Exception as e:
                st.sidebar.error(f"Failed to load metadata: {e}")
        
    # --- scRNAseq file upload ---
    if st.session_state.get("scRNAseq_analysis", False):
        single_file = st.sidebar.file_uploader("Upload a file", type=["csv", "tsv", "h5ad", "h5"], key="single_upload")
        multi_files = st.sidebar.file_uploader("Or upload 10x files", type=["mtx", "tsv", "gz"], accept_multiple_files=True, key="multi_upload")
        handle_uploaded_files(single_file, multi_files)