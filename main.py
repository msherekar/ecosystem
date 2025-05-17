import streamlit as st
import pandas as pd
import PyPDF2
import os
import json
from chatbot import ask_chatbot

from reader import fetch_pubmed_with_abstract, display_pubmed_with_abstract

# --- Session State Initialization ---
st.set_page_config(page_title="Lab Assistant Chatbot", layout="wide")
st.session_state.setdefault("welcome_message", "")
st.session_state.setdefault("messages", [])
st.session_state.setdefault("uploaded_df", {}) # each element is a dataframe
st.session_state.setdefault("project_name", "")
st.session_state.setdefault("uploaded_pdf", None)

st.session_state.setdefault("tabular_analysis", False)  # Default to False
st.session_state.setdefault("image_analysis", False)  # Default to False
st.session_state.setdefault("scRNAseq_analysis", False)  # Default to False
st.session_state.setdefault("reader", False)  # Default to False
st.session_state.setdefault("pubmed_search", False)  # Default to False
st.session_state.setdefault("pubmed_search_query", '')
st.session_state.setdefault("create_project", False)
st.session_state.setdefault("user_interest", 'cancer')


st.sidebar.markdown("## Select the module")
st.sidebar.checkbox("Tabular Analysis",  key="tabular_analysis")
st.sidebar.checkbox("Image Analysis", key="image_analysis")
st.sidebar.checkbox("scRNAseq Analysis", key="scRNAseq_analysis")
st.sidebar.checkbox("Reader",  key="reader")

for i in range(28):
    st.sidebar.write("")



# Sidebar button to trigger project creation
if st.sidebar.button("Create Project", use_container_width=True):
    st.session_state.create_project = True

# Display text input only if creation is triggered
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

if st.sidebar.button("Clear Uploaded Files", use_container_width=True, key="clear_uploaded_files"):
    st.session_state.uploaded_df = {}
    st.session_state.last_uploaded_file = None
    st.session_state.uploaded_pdf = None
if st.sidebar.button("Clear Chat History", use_container_width=True, key="clear_chat_history"):
    st.session_state.messages = []

# --- Layout: two columns ---
data_col, chat_col = st.columns([2.5,1], border=True)

if not st.session_state.tabular_analysis and not st.session_state.image_analysis and not st.session_state.scRNAseq_analysis and not st.session_state.reader:
    with data_col:
        if st.session_state.welcome_message == "":
            welcome_message = ask_chatbot(user_question=[{"role": "user", "content": "Write an inspiration story in 300 words about a scientist or a discovery. Please format it as a markdown document."}], model_choice='gpt4')
            st.session_state.welcome_message = welcome_message.content
            st.markdown(st.session_state.welcome_message)
        else:
            st.markdown(st.session_state.welcome_message)

if st.session_state.tabular_analysis:
    import tabular
    with data_col:
        tabular.tabular_data()

if st.session_state.reader:
    from reader import reader
    with data_col:
        reader(st.session_state.user_interest)

if st.session_state.pubmed_search:
    from reader import fetch_pubmed_with_abstract
    with data_col:
        articles_info = fetch_pubmed_with_abstract(st.session_state.pubmed_search_query)
        display_pubmed_with_abstract(articles_info)
        st.session_state.pubmed_search = False
        st.session_state.pubmed_search_query = ''



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
            
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = tool_call.function.arguments
                    if tool_name == "pubmed_search":
                        st.write("mamta pagal hain")
                        st.write(tool_args)
                        st.session_state.pubmed_search_query = tool_args
                        st.session_state.pubmed_search = True
                        
            content = message.content
        with st.chat_message("assistant"):
            st.markdown(content)
            st.session_state.messages.append({"role": "assistant", "content": content})


