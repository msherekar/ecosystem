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
                # Generate welcome content using chatbot
                # GPT-3.5 recommended for cost savings
                welcome_content = ask_chatbot(
                    user_question=[
                        {"role": "user", "content": "Generate a brief, friendly welcome message for a bioinformatics data analysis platform. Keep it concise and mention key features like RNA-seq, scRNA-seq analysis, and AI assistance."}
                    ],
                    model_choice='gpt3'  # Use 'gpt3' (now mapped to gpt-3.5-turbo) to save credits
                )

                # Handle both API response formats
                if hasattr(welcome_content, 'content'):
                    st.session_state.welcome_message = welcome_content.content
                elif isinstance(welcome_content, dict) and 'content' in welcome_content:
                    content = welcome_content['content']
                    if content.startswith("Error:"):
                        logging.error(f"Error in welcome message: {content}")
                        st.session_state.welcome_message = "Welcome to the Bioinformatics Analysis Platform!"
                    else:
                        st.session_state.welcome_message = content
                elif isinstance(welcome_content, str):
                    st.session_state.welcome_message = welcome_content
                else:
                    logging.warning(f"Unexpected welcome message format: {type(welcome_content)}")
                    st.session_state.welcome_message = "Welcome to the Bioinformatics Analysis Platform!"

            except Exception as e:
                logging.error(f"Failed to get welcome message: {str(e)}")
                st.session_state.welcome_message = "# 👋 Welcome to Gliaent"

        st.markdown(st.session_state.welcome_message)
