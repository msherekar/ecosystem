import streamlit as st
import pandas as pd
import os
import base64

def reader():
    if st.session_state.uploaded_pdf is None:
        with st.expander("Click here to upload a PDF file"):
            file = st.file_uploader("Upload a PDF file", type=["pdf"], key="pdf_file")
        if file:
            st.session_state.uploaded_pdf = file
        if st.session_state.uploaded_pdf:
            try:
                base64_pdf = base64.b64encode(st.session_state.uploaded_pdf.read()).decode('utf-8') # 
                pdf_display = f"""
                    <iframe src="data:application/pdf;base64,{base64_pdf}"
                    width="100%" height="1000px"
                    type="application/pdf"></iframe>
                """
                st.markdown(pdf_display, unsafe_allow_html=True)        
            except Exception as e:
                st.error(f"Error displaying PDF: {e}")
    else:
        try:        
            base64_pdf = base64.b64encode(st.session_state.uploaded_pdf.read()).decode('utf-8') # 
            pdf_display = f"""
                <iframe src="data:application/pdf;base64,{base64_pdf}"
                    width="100%" height="1000px"
                type="application/pdf"></iframe>
            """
            st.markdown(pdf_display, unsafe_allow_html=True)        
        except Exception as e:
            st.error(f"Error displaying PDF: {e}")
