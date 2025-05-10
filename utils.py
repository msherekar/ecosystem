import streamlit as st
import pandas as pd
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
    
    
    
def tabular_data():   
    with st.expander("Click here to upload a file or make a new project"):
        file = st.file_uploader("Upload a file", type=["csv", "xlsx", "txt"])
        if file:
            st.session_state.uploaded_df.append(process_uploaded_file(file))
        
        project_name = st.text_input("Enter project name")
    
        if project_name:
            os.makedirs(project_name, exist_ok=True)
            st.session_state.project_name = project_name           
    
    st.write(len(st.session_state.uploaded_df))
    if st.session_state.uploaded_df:
        for i, df in enumerate(st.session_state.uploaded_df):
            st.dataframe(df.head())

def reader():
    with st.expander("Click here to upload a PDF file"):
        file = st.file_uploader("Upload a PDF file", type=["pdf"])
    if file:
        st.session_state.uploaded_pdf.append(file)
    if st.session_state.uploaded_pdf:
        base64_pdf = base64.b64encode(st.session_state.uploaded_pdf[-1].read()).decode('utf-8') # 
        pdf_display = f"""
            <iframe src="data:application/pdf;base64,{base64_pdf}"
                width="100%" height="1000px"
                type="application/pdf"></iframe>
        """
        st.markdown(pdf_display, unsafe_allow_html=True)        
