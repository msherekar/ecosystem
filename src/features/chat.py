import streamlit as st
from chat.chatbot import ask_chatbot

def chat_interface():
    # Initialize messages if it doesn't exist
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    st.markdown(
        """<div style="text-align: center"><p>Hi there! I'm your AI assistant for biological data insights — how can I help analyze your data today?</p></div>""",
        unsafe_allow_html=True,
    )

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("What can I help you with?")
    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

        response = ask_chatbot(st.session_state.messages, model_choice='gpt4')
        
        with st.chat_message("assistant"):
            st.markdown(response.content)
            st.session_state.messages.append({"role": "assistant", "content": response.content})
