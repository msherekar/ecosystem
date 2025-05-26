import streamlit as st
from modules.agent.brain import ask_agent
from chat.chatbot import ask_chatbot
from modules.agent.registry import registry  # ✅ Global registry

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


        # --- Chat input box ---
        prompt = st.chat_input("What can I help you with?")

        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            use_agent = st.session_state.get("use_agent", True)
            model_choice = st.session_state.get("model_choice", "gpt4")

            try:
                if use_agent:
                    result = ask_agent(prompt, conversation_history=st.session_state.messages[:-1])
                    assistant_content = result.get("response", "")
                    actions = result.get("actions", [])

                    triggered_flags = []
                    for action in actions:
                        tool_name = action.get("tool")
                        flag = registry.get_analysis_flag(tool_name)
                        if flag:
                            triggered_flags.append(flag)
                            st.session_state[flag] = True

                    if triggered_flags:
                        for flag in triggered_flags:
                            message = registry.get_ui_message(flag)
                            if message:
                                st.session_state.messages.append({"role": "assistant", "content": message})
                        return  # Don't show assistant response if it's just triggering UI

                    st.session_state.messages.append({"role": "assistant", "content": assistant_content})

                    for action in actions:
                        tool = action.get("tool")
                        msg = action["result"].get("message", "No output")
                        st.info(f"✅ Executed: `{tool}`\n\n**Result**: {msg}")

                else:
                    message = ask_chatbot(user_question=st.session_state.messages, model_choice=model_choice)
                    st.session_state.messages.append({"role": "assistant", "content": message.content})

            except Exception as e:
                error_message = f"Sorry, I encountered an error: {str(e)}"
                st.session_state.messages.append({"role": "assistant", "content": error_message})
