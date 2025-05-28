import streamlit as st
import asyncio
from src.agent.core import BioinformaticsAgent

def display_right_panel():
    st.header("🤖 AI Assistant")
    
    # Initialize agent
    if "agent" not in st.session_state:
        st.session_state.agent = BioinformaticsAgent()
    
    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Display chat history
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.chat_message("user").write(message["content"])
        else:
            st.chat_message("assistant").write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask about your analysis or request help..."):
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        
        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Use async chat method
                    response, actions = asyncio.run(st.session_state.agent.chat(prompt))
                    
                    # Check if response is empty or just whitespace
                    if response and response.strip():
                        st.write(response)
                        # Add to chat history
                        st.session_state.chat_history.append({"role": "assistant", "content": response})
                    else:
                        # Don't add empty responses to chat
                        st.write("I'm processing your request...")
                        
                except Exception as e:
                    error_msg = f"Sorry, I encountered an error: {str(e)}"
                    st.write(error_msg)
                    st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
