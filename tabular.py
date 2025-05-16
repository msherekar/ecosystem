import streamlit as st
import pandas as pd
import os
import base64
import numpy as np

tools = ["None", "sort", "filter", "plot", "summary", "describe", "groupby", "merge", "join", "concat"]

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
        
    if new_file_name:
        with st.form("add_multiple_columns"):
            num_cols = st.number_input("How many columns to add?", min_value=1, max_value=10, step=1)

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
   
    with st.expander("Click here to upload a new file"):
        # upload a file
        file = st.file_uploader("Upload a file", type=["csv", "xlsx", "txt"])
        if file is not None and file.name not in st.session_state.uploaded_df.keys():
            st.session_state.uploaded_df[file.name] =  process_uploaded_file(file)
    
    with st.expander("Click here to create a new file"):# create a new file
        new_file_name = st.text_input("Create a file")
        new_df = create_table(new_file_name)
        if new_df is not None:
            if new_file_name not in st.session_state.uploaded_df:
                st.session_state.uploaded_df[new_file_name] = new_df
    
    # render uploaded or created files for editing if they exist
    for key in st.session_state.uploaded_df.keys():
        df = st.session_state.uploaded_df[key]
        if df is not None:
            st.markdown(f"Editing **{key}**, **{df.shape[0]}** rows, **{df.shape[1]}** columns")
            tools_options = st.selectbox("Select tools", tools, key=f"tools_{key}")
            
            option = None  # Ensure it's initialized
            
            if tools_options == "sort":
                option = st.selectbox("Select column to sort by", df.columns, key=f"sort_option_{key}")
            
            elif tools_options == "filter":
                with st.expander("Filter Options"):
                    option = st.selectbox("Select column to filter by", df.columns, key=f"filter_option_{key}")
                    col_dtype = df[option].dtype

                    if np.issubdtype(col_dtype, np.number):
                        min_value = st.number_input("Min value", value=float(df[option].min()), key=f"min_value_{key}")
                        max_value = st.number_input("Max value", value=float(df[option].max()), key=f"max_value_{key}")
                    elif pd.api.types.is_string_dtype(col_dtype):
                        search_str = st.text_input("Enter a string to search", key=f"search_str_{key}")
                    elif pd.api.types.is_bool_dtype(col_dtype):
                        bool_value = st.checkbox("Filter for True values", key=f"bool_value_{key}")

            filtered_df = df.copy()

            if tools_options == "sort" and option:
                filtered_df = filtered_df.sort_values(by=option)

            elif tools_options == "filter" and option:
                col_dtype = df[option].dtype
                if np.issubdtype(col_dtype, np.number):
                    filtered_df = filtered_df[(filtered_df[option] > min_value) & (filtered_df[option] < max_value)]
                elif pd.api.types.is_string_dtype(col_dtype):
                    filtered_df = filtered_df[filtered_df[option].str.contains(search_str, na=False)]
                elif pd.api.types.is_bool_dtype(col_dtype):
                    filtered_df = filtered_df[filtered_df[option] == bool_value]

            edited_df = st.data_editor(filtered_df, num_rows="dynamic", key=f"data_editor_{key}")
            st.write(edited_df.shape)
            if st.button("Save"):
                if not edited_df.equals(df):
                    st.session_state.uploaded_df[key] = edited_df
                    st.success("File saved successfully")
                else:
                    st.info("No changes to save.")

               
                
