import streamlit as st
import pandas as pd
<<<<<<< HEAD
import os
import base64
# --- Helper Functions ---
def process_uploaded_file(file):
    if file is not None:
        try:
            if file.name.endswith(".csv"):
                df = pd.read_csv(file)
            elif file.name.endswith(".xlsx"):
                df = pd.read_excel(file)
            elif file.name.endswith(".txt"):
                df = pd.read_csv(file, delimiter="\t")
            else:
                st.error("Unsupported file format.")
                return None
            return df
        except Exception as e:
            st.error(f"Error reading file: {e}")
            return None
    return None
    
def create_table(new_file_name):
      # Ensure df is always defined
    
    if new_file_name:
        with st.form("add_multiple_columns"):
            num_cols = st.number_input("How many columns to add?", min_value=1, max_value=10, step=1)
=======
import numpy as np


# Initialize session state
st.session_state.setdefault("original_df", {})
st.session_state.setdefault("working_df", {})
st.session_state.setdefault("modified_df", {})

# Available tools
tools = ["None", "sort", "filter", "Add column with formula", "plot", "summary", "describe", "groupby", "merge", "join", "concat"]

def process_uploaded_file(file):
    try:
        if file.endswith(".csv"):
            return pd.read_csv(file)
        elif file.endswith(".xlsx"):
            return pd.read_excel(file)
        elif file.endswith(".txt"):
            return pd.read_csv(file, delimiter="\t")
        else:
            st.error("Unsupported file format.")
            return None
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None

def create_table(new_file_name):
    df = None
    if new_file_name:
        with st.form("add_multiple_columns"):
            num_cols = st.number_input("How many columns to add?", min_value=1, max_value=10, step=1, key="num_cols")
            default_rows = st.number_input("Default number of rows", value=5, min_value=1, key="default_rows")
>>>>>>> origin/feature/pdf-viewer

            col_names = []
            col_types = []

            for i in range(num_cols):
                st.markdown(f"**Column {i+1}**")
                col_name = st.text_input(f"Name for column {i+1}", key=f"col_name_{i}")
                col_type = st.selectbox(
                    f"Data type for column {i+1}", ["str", "int", "float", "bool"], key=f"col_type_{i}"
                )
                col_names.append(col_name)
                col_types.append(col_type)

            submitted = st.form_submit_button("Create table")

            if submitted:
<<<<<<< HEAD
                default_values = {"str": "", "int": 0, "float": 0.0, "bool": False}
                default_rows = 5
                df = pd.DataFrame()
                for name, dtype in zip(col_names, col_types):
                    if name:
                        if name in df.columns:
                            st.warning(f"Column '{name}' already exists.")
                        else:
                            df[name] = pd.Series(
                                [default_values[dtype]] * default_rows,
                                dtype=dtype
                            )
                    else:
                        st.warning("Column name cannot be empty.")
                
                for i in range(num_cols):
                        st.session_state.pop(f"col_name_{i}", None)
                        st.session_state.pop(f"col_type_{i}", None)
                st.session_state.pop("num_cols", None)
                return df
    return None 

def tabular_data():
    
    st.session_state.setdefault("new_file_ready", False) 

    with st.expander("Click here to create a new project, upload or create a new file"):
        '''# create a new project
        project_name = st.text_input("Create a project")
        if project_name:
            os.makedirs(project_name, exist_ok=True)
            st.session_state.project_name = project_name  
        '''
        # upload a file
        file = st.file_uploader("Upload a file", type=["csv", "xlsx", "txt"])
        if file is not None and file.name not in st.session_state.uploaded_df.keys():
            st.session_state.uploaded_df[file.name] =  process_uploaded_file(file)
    
    with st.expander("Create a new file"):# create a new file
        new_file_name = st.text_input("Create a file")
        new_df = create_table(new_file_name)
        if new_df is not None:
            if new_file_name not in st.session_state.uploaded_df:
                st.session_state.uploaded_df[new_file_name] = new_df
                st.session_state.new_file_ready = True
                st.rerun()  # Ensures clean state before editing

    # render uploaded or created files for editing if they exist
    for key in st.session_state.uploaded_df.keys():
        df = st.session_state.uploaded_df[key]
        if df is not None:
            st.markdown(f"**{key}**")
            edited_df = st.data_editor(df.copy(), num_rows="dynamic", key=f"data_editor_{key}")
            if not edited_df.equals(df):
                st.session_state.uploaded_df[key] = edited_df
=======
                if all(name for name in col_names):
                    if len(set(col_names)) < len(col_names):
                        st.warning("Column names must be unique.")
                    else:
                        default_values = {"str": "", "int": 0, "float": 0.0, "bool": False}
                        df = pd.DataFrame()
                        for name, dtype in zip(col_names, col_types):
                            df[name] = pd.Series([default_values[dtype]] * default_rows, dtype=dtype)
                         # Clean up form state
                        for i in range(num_cols):
                            st.session_state.pop(f"col_name_{i}", None)
                            st.session_state.pop(f"col_type_{i}", None)
                        st.session_state.pop("num_cols", None)
                        st.session_state.pop("default_rows", None)

                        # Refresh UI
                        st.success(f"Table '{new_file_name}' created.")

                else:
                    st.warning("Please fill in all column names.")
                
    return df

def display_dataframe(dataframe_dict):
    for key, df in dataframe_dict.items():
        if df is not None:
            st.markdown(f"Viewing **{key}**, **{df.shape[0]}** rows, **{df.shape[1]}** columns")
            st.dataframe(df, use_container_width=True)


def editing_dataframe(dataframe_dict):
    for key in dataframe_dict:
        df = dataframe_dict[key].copy()
        if df is not None:
            st.markdown(f"Editing **{key}**, **{df.shape[0]}** rows, **{df.shape[1]}** columns")
            st.session_state.setdefault(f"tools_{key}", "None")
            tools_options = st.selectbox("Select tools", tools, key=f"tools_{key}")

            mod_df = df
            option = None

            if tools_options == "sort":
                option = st.selectbox("Select column to sort by", df.columns, key=f"sort_option_{key}")
                if option:
                    mod_df = df.sort_values(by=option)

            elif tools_options == "filter":
                with st.expander("Filter Options"):
                    option = st.selectbox("Select column to filter by", df.columns, key=f"filter_option_{key}")
                    if option:
                        col_dtype = df[option].dtype
                        if np.issubdtype(col_dtype, np.number):
                            min_value = st.number_input("Min value", value=float(df[option].min()), key=f"min_value_{key}")
                            max_value = st.number_input("Max value", value=float(df[option].max()), key=f"max_value_{key}")
                            mod_df = df[(df[option] > min_value) & (df[option] < max_value)]
                        elif pd.api.types.is_string_dtype(col_dtype):
                            search_str = st.text_input("Enter a string to search", key=f"search_str_{key}")
                            mod_df = df[df[option].str.contains(search_str, na=False)]
                        elif pd.api.types.is_bool_dtype(col_dtype):
                            bool_value = st.checkbox("Filter for True values", key=f"bool_value_{key}")
                            mod_df = df[df[option] == bool_value]
            
            elif tools_options == "Add column with formula":
                with st.expander("Insert a new column with formula"):
                    new_col_name = st.text_input("New column name", key = f"new_col_name_{key}")
                    formula = st.text_input("Enter a formula using existing columns", help="E.g., col1 + col2 * 2")
                    if st.button("Add Column"):
                        if new_col_name in df.columns:
                            st.warning("Column name already exists.")
                        elif not new_col_name or not formula:
                            st.warning("Please provide both a name and formula.")
                        else:
                            try:
                                # Evaluate formula
                                mod_df[new_col_name] = df.eval(formula)
                                st.success(f"Column '{new_col_name}' added.")
                                st.session_state.modified_df[key] = mod_df
                                #st.dataframe(mod_df)
                            except Exception as e:
                                st.error(f"Error in formula: {e}")
        
            edited_df = st.data_editor(mod_df, num_rows="dynamic", key=f"data_editor_{key}", use_container_width=True)
            #st.dataframe(edited_df)
            st.write(edited_df.shape)

            if st.button(f"Save {key}", key=f"save_button_{key}"):
                if not edited_df.equals(df):
                    st.session_state.modified_df[key] = edited_df
                    #st.dataframe(edited_df)
                    st.success("File saved successfully.")
                else:
                    st.info("No changes to save.")

def tabular_data():
    '''
    with st.expander("Click here to upload a new file"):
        file = st.file_uploader("Upload a file", type=["csv", "xlsx", "txt"])
        if file is not None and file.name not in st.session_state.original_df:
            df = process_uploaded_file(file)
            if df is not None:
                st.session_state.original_df[file.name] = df
                st.session_state.modified_df[file.name] = st.session_state.original_df[file.name]

    with st.expander("Click here to create a new file"):
        new_file_name = st.text_input("Create a file")
        new_df = create_table(new_file_name)
        if new_df is not None and new_file_name not in st.session_state.modified_df:
            st.session_state.modified_df[new_file_name] = new_df
    '''
    if st.session_state.original_df:
        st.write("Uploaded Files")
        st.markdown("---")
        display_dataframe(st.session_state.original_df)
        st.markdown("---")

    if st.session_state.modified_df:
        
        st.write("Editable Files")
        st.markdown("---")
        editing_dataframe(st.session_state.modified_df)
        st.markdown("---")
    
>>>>>>> origin/feature/pdf-viewer
