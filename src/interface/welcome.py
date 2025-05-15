import streamlit as st
from chat.chatbot import ask_chatbot
import logging

def show_welcome_message(col):
    with col:
        if 'welcome_message' not in st.session_state:
            st.session_state.welcome_message = None
            
        if not st.session_state.welcome_message:
            try:
                # Try to get a welcome message from the AI using gpt3.5 instead of gpt4 to save credits
                welcome_message = ask_chatbot(
                    messages=[{"role": "user", "content": "Write an inspiration story in 300 words about a scientist or a discovery. Please format it as a markdown document."}],
                    model_choice='gpt3.5'  # Use GPT-3.5 to save credits
                )
                
                # Check if welcome_message has content attribute
                if hasattr(welcome_message, 'content'):
                    st.session_state.welcome_message = welcome_message.content
                elif isinstance(welcome_message, dict) and 'content' in welcome_message:
                    content = welcome_message['content']
                    # Check if the content is an error message
                    if content.startswith("Error:"):
                        logging.error(f"Error in welcome message: {content}")
                        raise Exception(content)
                    st.session_state.welcome_message = content
                else:
                    raise Exception("Unexpected response format")
                    
            except Exception as e:
                # If anything goes wrong, use the fallback message
                logging.error(f"Failed to get welcome message: {str(e)}")
                st.session_state.welcome_message = """
# Welcome to the Lab Assistant

I'm here to help you analyze your research data and answer your scientific questions. 
Please select a module from the sidebar to get started.

## Available Modules:
- **Tabular Analysis** - For analyzing spreadsheet data
- **Reader Mode** - For extracting information from PDFs
- **RNAseq Analysis** - For gene expression data
- **Image Analysis** - For microscopy and imaging data
                """
            
            st.markdown(st.session_state.welcome_message)
        else:
            st.markdown(st.session_state.welcome_message)
    
    
