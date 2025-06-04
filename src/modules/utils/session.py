import streamlit as st
import os
import numpy as np
import pandas as pd

def initialize_session_state():
    defaults = {
        "welcome_message": "",
        "messages": [],
        "tabular_coding": [],
        "uploaded_df": {},
        "project_name": "",
        "uploaded_pdf_path": None,
        "input_h5ad_path": None,
        "temp": {},
        "current_dir": os.getcwd(),
        "show_file_browser": False,
        "active_tab": "Main",
        "pubmed_search": False,
        "pubmed_search_query": "",
        "search": False,
        "geo_search": False,
        "geo_search_query": "",
        "create_project": False,
        "create_file": False,
        "ai_coder": False,
        "ai_code": {},
        "user_interest": "cancer biomarkers"
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

def create_project():
    
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


def is_raw_count_matrix_df(df):
    # Assume the first column contains gene names/IDs
    gene_column = df.columns[0]
    df_counts = df.drop(columns=[gene_column], errors="ignore")

    # Try converting all values to numeric
    df_counts = df_counts.apply(pd.to_numeric, errors='coerce')

    # Drop columns with too many missing values
    df_counts = df_counts.dropna(axis=1, thresh=len(df_counts) * 0.8)

    # Not enough valid sample columns?
    if df_counts.shape[1] < 2:
        return False, "Too few numeric sample columns."

    # Flatten all values into one array
    all_values = df_counts.values.flatten()
    valid_values = all_values[~np.isnan(all_values)]

    # Check properties of raw count data
    is_integer_like = np.all(np.abs(valid_values - np.round(valid_values)) < 1e-6)
    is_non_negative = np.all(valid_values >= 0)
    median_value = np.median(valid_values)

    if is_integer_like and is_non_negative and median_value > 10:
        return True
    else:
        return False

def browse_to_open_file():
    if st.session_state.show_file_browser:
        with st.sidebar.popover("Select a file", use_container_width=True):
            current_dir = st.session_state['current_dir']
            st.write(f"**Current directory:** `{current_dir}`")

            if os.path.isdir(current_dir):
                entries = os.listdir(current_dir)
                entries.sort()
                folders = [f for f in entries if os.path.isdir(os.path.join(current_dir, f))]
                files = [f for f in entries if os.path.isfile(os.path.join(current_dir, f))]

                # Navigate to a folder
                selected_folder = st.selectbox("Folders", [".. (go up)"] + folders)
                if st.button("Go to folder"):
                    if selected_folder == ".. (go up)":
                        st.session_state['current_dir'] = os.path.dirname(current_dir)
                    else:
                        st.session_state['current_dir'] = os.path.join(current_dir, selected_folder)
                    st.rerun()

                # File selection
                if files:
                    selected_file = st.selectbox("Files", files)
                    file_path = os.path.join(current_dir, selected_file)
                    if st.button("Load File"):
                        # Load files from the path
                        file_name = os.path.basename(file_path)
                        if file_name.endswith(("csv", "txt", "xlsx")):
                            from modules.data.tabular import process_uploaded_file
                            df = process_uploaded_file(file_path)
                            st.write('check')
                            #Check if the df could be raw count file from rnaseq pipeline
                            if is_raw_count_matrix_df(df):
                                st.session_state.active_tab = 'bulk'
                                st.session_state.rnaseq_counts_df = df
                            else:
                                st.session_state.active_tab = 'tabular_analysis'
                                st.session_state.original_df[file_name] = df
                                st.session_state.modified_df[file_name] = df.copy()
                            
                            st.session_state.show_file_browser = False
                            st.rerun()
                        elif file_name.endswith("pdf"):
                            st.session_state.active_tab = 'reader'
                            st.session_state.uploaded_pdf_path = file_path
                            st.session_state.show_file_browser = False
                            st.rerun()
                        elif file_name.endswith("h5ad"):
                           
                            st.session_state.active_tab = 'scRNAseq_analysis'
                            st.session_state.input_h5ad_path = file_path
                            st.session_state.show_file_browser = False
                            st.rerun()

