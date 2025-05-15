import streamlit as st
from chat.chatbot import ask_chatbot
import logging
import os
from openai import OpenAI

# Set up logging
logging.basicConfig(level=logging.INFO)

def chat_interface():
    # Initialize messages if it doesn't exist
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    # Initialize result_content for data display
    if 'result_content' not in st.session_state:
        st.session_state.result_content = None
        
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

        logging.info(f"Messages sent to API: {st.session_state.messages}")

        try:
            # Use GPT-3.5 instead of GPT-4 to save credits
            response = ask_chatbot(st.session_state.messages, model_choice='gpt3.5')
            logging.info(f"API response type: {type(response)}")
            
            # Get the content from either object attribute or dictionary key
            if hasattr(response, 'content'):
                content = response.content
                logging.info("Got content from response.content attribute")
            elif isinstance(response, dict) and 'content' in response:
                content = response['content']
                logging.info("Got content from response['content'] dictionary key")
                
                # Check if it looks like a data/search result
                if content.startswith("## Search Results") or "GEO Results" in content or "TCGA Results" in content:
                    # This is likely a search result, store it for display in the data column
                    st.session_state.result_content = content
                    # Set a flag to indicate which type of analysis was performed
                    st.session_state.genomics_search = True
                    # Rerun the app to display the results in the data column
                    st.rerun()
                    
                # Check if content is an error message and log it
                if content.startswith("Error:"):
                    logging.error(f"Error in response: {content}")
            else:
                content = "I'm sorry, I couldn't process that request. Please try again."
                logging.error(f"Unexpected response format: {response}")
            
            with st.chat_message("assistant"):
                st.markdown(content)
                st.session_state.messages.append({"role": "assistant", "content": content})
                
        except Exception as e:
            logging.error(f"API call failed: {str(e)}", exc_info=True)
            with st.chat_message("assistant"):
                error_message = "I'm sorry, there was an error processing your request. Please try again."
                st.markdown(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})
                
def display_results_in_data_column(data_col):
    """Display the search results in the data column"""
    if st.session_state.result_content:
        with data_col:
            st.markdown(st.session_state.result_content)
            
            # Add buttons for further analysis
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Download Data"):
                    st.info("Download functionality would be implemented here")
            with col2:
                if st.button("Visualize"):
                    st.info("Visualization functionality would be implemented here")
            with col3:
                if st.button("Clear Results"):
                    st.session_state.result_content = None
                    st.session_state.genomics_search = False
                    st.rerun()

