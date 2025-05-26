# src/interface/welcome.py

import streamlit as st
from chat.chatbot import ask_chatbot
import logging

def show_welcome_message(col):
    """
    Display a welcome message in the given Streamlit column.
    Uses GPT model to generate the content if not already cached in session state.
    """
    with col:
        if 'welcome_message' not in st.session_state:
            st.session_state.welcome_message = None

        if not st.session_state.welcome_message:
            try:
                # GPT-3.5 recommended if you're saving credits
                welcome_message = ask_chatbot(
                    messages=[{
                        "role": "user",
                        "content": "Write an inspiration story in 300 words about a scientist or a discovery. Please format it as a markdown document."
                    }],
                    model_choice='gpt-3.5'  # Use 'gpt-3.5' instead of 'gpt4' to save credits
                )

                # Handle both API response formats
                if hasattr(welcome_message, 'content'):
                    st.session_state.welcome_message = welcome_message.content
                elif isinstance(welcome_message, dict) and 'content' in welcome_message:
                    content = welcome_message['content']
                    if content.startswith("Error:"):
                        logging.error(f"Error in welcome message: {content}")
                        raise Exception(content)
                    st.session_state.welcome_message = content
                else:
                    raise Exception("Unexpected response format")

            except Exception as e:
                logging.error(f"Failed to get welcome message: {str(e)}")
                st.session_state.welcome_message = "# 👋 Welcome to Gliaent"

        st.markdown(st.session_state.welcome_message)
