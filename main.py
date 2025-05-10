import streamlit as st
import pandas as pd
import PyPDF2
import os
import json
from chatbot import ask_chatbot  # Your custom chatbot handler
from utils import process_uploaded_file, tabular_data, reader

# --- Session State Initialization ---
st.set_page_config(page_title="Lab Assistant Chatbot", layout="wide")
st.session_state.setdefault("messages", [])
st.session_state.setdefault("uploaded_df", []) # each element is a dataframe
st.session_state.setdefault("project_name", "")
st.session_state.setdefault("last_uploaded_file", None)
st.session_state.setdefault("uploaded_pdf", [])

st.session_state.setdefault("tabular_analysis", False)  # Default to False
st.session_state.setdefault("image_analysis", False)  # Default to False
st.session_state.setdefault("scRNAseq_analysis", False)  # Default to False
st.session_state.setdefault("reader", False)  # Default to False

st.sidebar.markdown("## Select the module")
st.sidebar.checkbox("Tabular Analysis",  key="tabular_analysis")
st.sidebar.checkbox("Image Analysis", key="image_analysis")
st.sidebar.checkbox("scRNAseq Analysis", key="scRNAseq_analysis")
st.sidebar.checkbox("Reader",  key="reader")

for i in range(27):
    st.sidebar.write("")
if st.sidebar.button("Clear Uploaded Files", use_container_width=True, key="clear_uploaded_files"):
    st.session_state.uploaded_df = []
    st.session_state.last_uploaded_file = None
    st.session_state.uploaded_pdf = []
if st.sidebar.button("Clear Chat History", use_container_width=True, key="clear_chat_history"):
    st.session_state.messages = []

# --- Layout: two columns ---
data_col, chat_col = st.columns([2.5,1], border=True)

if not st.session_state.tabular_analysis and not st.session_state.image_analysis and not st.session_state.scRNAseq_analysis and not st.session_state.reader:
    with data_col:
        st.markdown("### Begin your analysis!")

if st.session_state.tabular_analysis:
    with data_col:
        tabular_data()

if st.session_state.reader:
    with data_col:
        reader()
               
# Right Column: Chat Interface
with chat_col:
    
    st.markdown("""<div style="text-align: center"><p>Hi there! I'm your AI assistant for biological data insights — how can I help analyze your data today?</p></div>""", unsafe_allow_html=True)
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("What can I help you with?")
    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

            message = ask_chatbot(user_question=st.session_state.messages, model_choice='gpt4')
            content = message.content
        with st.chat_message("assistant"):
            st.markdown(content)
            st.session_state.messages.append({"role": "assistant", "content": content})


