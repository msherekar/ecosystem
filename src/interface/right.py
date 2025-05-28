import streamlit as st
import asyncio
from src.agent.brain import ask_agent
from src.chat.chatbot import ask_chatbot

def chat_interface(chat_col):
    with chat_col:
        # --- Intro section ---
        st.markdown("""
            <div style="text-align: center">
                <p>Hi there! I'm your AI assistant for biological data insights — how can I help analyze your data today?</p>
                <p style="font-size: 0.9em; color: #666;">Try saying <i>\"Run Bulk RNASeq\"</i> or <i>\"Perform scRNAseq\"</i> to get started!</p>
                
            </div>
        """, unsafe_allow_html=True)

        # --- Scrollable chat area style ---
        st.markdown("""
            <style>
            .chat-scrollbox {
                height: 500px;
                overflow-y: auto;
                padding: 1rem;
                border: 1px solid #444;
                border-radius: 0.5rem;
                background-color: #000000;
                margin-bottom: 1rem;
                color: #e0e0e0;
            }
            .chat-msg {
                margin-bottom: 0.75rem;
                line-height: 1.5;
                word-wrap: break-word;
            }
            .chat-msg-user {
                color: #4ea8ff;  /* Light blue */
            }
            .chat-msg-assistant {
                color: #ffffff;  /* White for contrast */
            }
            </style>
        """, unsafe_allow_html=True)

        # --- Display chat messages ---
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # --- Chat input box ---
        prompt = st.chat_input("What can I help you with?")

        if prompt:
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Force rerun to show user message immediately
            st.rerun()

        # Process the last message if it's from user and hasn't been processed
        if (st.session_state.messages and 
            st.session_state.messages[-1]["role"] == "user" and
            not st.session_state.get("processing_last_message", False)):
            
            # Mark as processing to avoid infinite loop
            st.session_state.processing_last_message = True
            
            user_prompt = st.session_state.messages[-1]["content"]
            use_agent = st.session_state.get("use_agent", True)
            model_choice = st.session_state.get("model_choice", "gpt4")

            try:
                if use_agent:
                    # Use async agent processing
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(
                            ask_agent(user_prompt, conversation_history=st.session_state.messages[:-1])
                        )
                    finally:
                        loop.close()
                    
                    assistant_content = result.get("response", "")
                    actions = result.get("actions", [])

                    # Handle any triggered analysis flags from MCP tools
                    triggered_flags = []
                    for action in actions:
                        tool_name = action.get("tool")
                        # Map tool names to session state flags for UI updates
                        if "rnaseq" in tool_name.lower():
                            triggered_flags.append("agent_requested_rnaseq")
                        elif "scrnaseq" in tool_name.lower() or "scrna" in tool_name.lower():
                            triggered_flags.append("agent_requested_scrnaseq")

                    if triggered_flags:
                        for flag in triggered_flags:
                            st.session_state[flag] = True

                    # Only add non-empty responses to chat
                    if assistant_content and assistant_content.strip():
                        st.session_state.messages.append({"role": "assistant", "content": assistant_content})

                else:
                    message = ask_chatbot(user_question=st.session_state.messages, model_choice=model_choice)
                    # Only add non-empty responses to chat
                    if message.content and message.content.strip():
                        st.session_state.messages.append({"role": "assistant", "content": message.content})

            except Exception as e:
                error_message = f"Sorry, I encountered an error: {str(e)}"
                st.session_state.messages.append({"role": "assistant", "content": error_message})
            
            finally:
                # Reset processing flag
                st.session_state.processing_last_message = False
                # Rerun to show assistant response
                st.rerun()
