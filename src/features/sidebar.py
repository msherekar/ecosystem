import streamlit as st
from cloud.login import one_click_aws_login, one_click_azure_login

def sidebar_controls():
    st.sidebar.title("🔧 Controls")

    # --- Cloud Connections ---
    if st.sidebar.button("🔐 Connect to AWS"):
        with st.spinner("Connecting to AWS..."):
            session, msg = one_click_aws_login()
            if session:
                st.session_state["aws_session"] = session
            st.sidebar.success(msg) if session else st.sidebar.error(msg)

    if st.sidebar.button("🔐 Connect to Azure"):
        with st.spinner("Connecting to Azure..."):
            credential, msg, subs = one_click_azure_login()
            if credential:
                st.session_state["azure_credential"] = credential
                st.sidebar.success(msg)

    # --- Module Toggles ---
    st.sidebar.markdown("---")
    st.sidebar.markdown("## Select the module")
    st.sidebar.checkbox("🧪 Tabular Analysis", key="tabular_analysis")
    st.sidebar.checkbox("📚 Reader Mode", key="reader")
    st.sidebar.checkbox("🧬 RNAseq Analysis", key="RNAseq_analysis")
    st.sidebar.checkbox("🧬 scRNAseq Analysis", key="scRNAseq_analysis")
    st.sidebar.checkbox("🖼️ Image Analysis", key="image_analysis")
    


    # --- Clear State Controls ---
    for _ in range(27):
        st.sidebar.write("")
    if st.sidebar.button("Clear Uploaded Files", use_container_width=True):
        st.session_state.uploaded_df = {}
        st.session_state.uploaded_pdf = None
    if st.sidebar.button("Clear Chat History", use_container_width=True):
        st.session_state.messages = []
