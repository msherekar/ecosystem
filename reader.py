import streamlit as st
import base64

def reader():
    st.session_state.setdefault("uploaded_pdf", None)
    st.session_state.setdefault("pdf_bytes", None)
    
    with st.expander("Click here to upload a PDF file"):
        file = st.file_uploader("Upload a PDF file", type=["pdf"])

    if file is not None:
        # Store uploaded file and its bytes in session state
        st.session_state.uploaded_pdf = file
        st.session_state.pdf_bytes = file.read()

    # Display PDF if uploaded
    if "uploaded_pdf" in st.session_state and st.session_state.uploaded_pdf:
        try:
            # Avoid re-reading: only use stored bytes
            base64_pdf = base64.b64encode(st.session_state.pdf_bytes).decode('utf-8')
            pdf_display = f"""
                <iframe src="data:application/pdf;base64,{base64_pdf}"
                width="100%" height="1000px"
                type="application/pdf"></iframe>
            """
            st.markdown(pdf_display, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error displaying PDF: {e}")