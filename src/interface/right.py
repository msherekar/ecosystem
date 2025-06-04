import streamlit as st
import json
from chat.chatbot import ask_chatbot

def chat_interface(chat_col):
    with chat_col:
        st.markdown("""
            <div style="text-align: center">
                <p>Hi there! I'm your AI assistant for biological data insights — how can I help analyze your data today?</p>
            </div>
        """, unsafe_allow_html=True)

        # Display past messages
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Prompt for new input
        prompt = st.chat_input("What can I help you with?")

        if prompt:
            # Show user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Get assistant response
            message = ask_chatbot(user_question=st.session_state.messages, model_choice='gpt4')

            # Handle tool calls
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    args = json.loads(tool_call.function.arguments)
                    if tool_call.function.name == "pubmed_search":
                        st.session_state.pubmed_search_query = args.get("query", "")
                        st.session_state.pubmed_search = True
                    elif tool_call.function.name == "geo_search":
                        st.session_state.geo_search_query = args.get("query", "")
                        st.session_state.geo_search = True

            # Show assistant response
            assistant_content = message.content
            st.session_state.messages.append({"role": "assistant", "content": assistant_content})
            with st.chat_message("assistant"):
                st.markdown(assistant_content)
