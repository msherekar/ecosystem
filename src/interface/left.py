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
                st.session_state.user_interaction = True  # Set interaction flag
            st.sidebar.success(msg) if session else st.sidebar.error(msg)

    if st.sidebar.button("🔐 Connect to Azure"):
        with st.spinner("Connecting to Azure..."):
            credential, msg, subs = one_click_azure_login()
            if credential:
                st.session_state["azure_credential"] = credential
                st.session_state.user_interaction = True  # Set interaction flag
                st.sidebar.success(msg)



    def on_module_change():
        st.session_state["module_changed"] = True  # You can use this to trigger actions later

    # --- Sidebar: Module Selector ---
    st.sidebar.markdown("## Select One Module")

    active_module = st.sidebar.radio(
        "Choose analysis mode:",
        options=["None", "🧪 Tabular Analysis", "📚 Reader Mode", "🧬 RNAseq Analysis", "🧬 scRNAseq Analysis", "🖼️ Image Analysis"],
        key="active_module",
        on_change=on_module_change
    )

    # --- Logic: Activate Only One ---
    st.session_state["tabular_analysis"] = active_module == "🧪 Tabular Analysis"
    st.session_state["reader"] = active_module == "📚 Reader Mode"
    st.session_state["RNAseq_analysis"] = active_module == "🧬 RNAseq Analysis"
    st.session_state["scRNAseq_analysis"] = active_module == "🧬 scRNAseq Analysis"
    st.session_state["image_analysis"] = active_module == "🖼️ Image Analysis"


    # --- Clear State Controls ---
    st.sidebar.markdown("---")
    st.sidebar.markdown("## Reset Controls")
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("Clear Uploaded Files", use_container_width=True):
            st.session_state.uploaded_df = {}
            st.session_state.uploaded_pdf = None
            
    with col2:
        if st.button("Notepads", use_container_width=True):
            st.session_state.messages = []
            
    if st.sidebar.button("Reset All", use_container_width=True):
        # Reset all interactive state but keep credentials
        for key in list(st.session_state.keys()):
            if key not in ["aws_session", "azure_credential"]:
                if key in ["messages", "results_history"]:
                    st.session_state[key] = []
                elif key in ["tabular_analysis", "image_analysis", 
                            "scRNAseq_analysis", "RNAseq_analysis", 
                            "reader", "genomics_search", "user_interaction"]:
                    st.session_state[key] = False
                elif key == "welcome_message":
                    st.session_state[key] = ""
        st.rerun()
