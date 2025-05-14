import streamlit as st
from chat.chatbot import ask_chatbot

def show_welcome_message(col):
    with col:
        if not st.session_state.welcome_message:
            response = ask_chatbot(
                user_question=[{"role": "user", "content": "Write an inspiration story in 300 words about a scientist or a discovery. Please format it as a markdown document."}],
                model_choice='gpt4'
            )
            st.session_state.welcome_message = response
        st.markdown(st.session_state.welcome_message)
