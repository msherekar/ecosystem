import streamlit as st
from chat.chatbot import ask_chatbot
import logging
import os
from openai import OpenAI
import time
import uuid
from datetime import datetime
from interface.center import display_chatbot_response

# Set up logging
logging.basicConfig(level=logging.INFO)

def chat_interface():
    # Initialize messages if it doesn't exist
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    # Initialize results history for data display
    if 'results_history' not in st.session_state:
        st.session_state.results_history = []
        
    st.markdown(
        """<div style="text-align: center"><p>Chat?</p></div>""",
        unsafe_allow_html=True,
    )

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Ask a question")
    
    if prompt:
        # Clear welcome message on any user interaction
        st.session_state.welcome_message = None
        
        # Set active interaction flag to hide welcome message
        st.session_state.user_interaction = True
        
        with st.chat_message("user"):
            st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

        logging.info(f"Messages sent to API: {st.session_state.messages}")

        
        # Use GPT-3.5 instead of GPT-4 to save credits
        # Here, response means answer from the chatbot
        response = ask_chatbot(st.session_state.messages, model_choice='deepseek')
        logging.info(f"API response type: {type(response)}")
        
        # Process and display the response in both chat interface and central area
        display_chatbot_response(response, prompt)