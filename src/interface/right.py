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

    prompt = st.chat_input("Analyse anything?")
    if prompt:
        # Clear welcome message on any user interaction
        st.session_state.welcome_message = None
        
        # Set active interaction flag to hide welcome message
        st.session_state.user_interaction = True
        
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
                    # Add a timestamp as a simple ID
                    import time
                    result_id = str(int(time.time()))
                    
                    # Add to results history
                    st.session_state.results_history.append({
                        "id": result_id,
                        "type": "search",
                        "query": prompt,
                        "content": content,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    
                    # Set active result for display
                    st.session_state.active_result_id = result_id
                    
                    # Set a flag to indicate genomics search was performed
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
    with data_col:
        # Add tabs for result history
        if st.session_state.results_history:
            # Create a container for the results with max height
            results_container = st.container()
            
            # Display the active result first
            active_result = None
            for result in st.session_state.results_history:
                if result["id"] == st.session_state.get("active_result_id"):
                    active_result = result
                    break
            
            if active_result:
                with results_container:
                    st.subheader(f"Results for: {active_result['query']}")
                    st.markdown(active_result['content'])
            
            # Create a horizontal line to separate current and previous results
            st.markdown("---")
            
            # Display previous results in reverse chronological order (newest first)
            if len(st.session_state.results_history) > 1:
                st.subheader("Previous Results")
                for result in reversed(st.session_state.results_history):
                    # Skip the active result as it's already shown
                    if result["id"] != st.session_state.get("active_result_id"):
                        with st.expander(f"{result['timestamp']} - {result['query']}"):
                            st.markdown(result['content'])
                            
                            # Add a button to make this the active result
                            if st.button(f"Show in main view", key=f"btn_{result['id']}"):
                                st.session_state.active_result_id = result["id"]
                                st.rerun()
            
            # Add buttons for further analysis of the active result
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Download Data"):
                    st.info("Download functionality would be implemented here")
            
                    st.session_state.results_history = []
                    st.session_state.genomics_search = False
                    st.rerun()
            with col2:
                if st.button("Visualize"):
                    st.info("Visualization functionality would be implemented here")
            with col3:
                if st.button("Clear Results"):
                    st.session_state.results_history = []
                    st.session_state.genomics_search = False
                    st.rerun()
