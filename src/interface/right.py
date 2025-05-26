import streamlit as st
from modules.agent.brain import ask_agent
from chat.chatbot import ask_chatbot
from modules.agent.registry import registry  # ✅ Global registry

def chat_interface(chat_col):
    with chat_col:
        # Intro section
        st.markdown("""
            <div style="text-align: center">
                <p>Hi there! I'm your AI assistant for biological data insights — how can I help analyze your data today?</p>
                <p style="font-size: 0.9em; color: #666;">Try saying <i>\"Run Bulk RNASeq\"</i> or <i>\"Perform scRNAseq\"</i> to get started!</p>
                <p style="font-size: 0.85em; color: #999;">After selecting a module, please upload your files in the left panel.</p>
            </div>
        """, unsafe_allow_html=True)

        # Display conversation history
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Prompt input
        prompt = st.chat_input("What can I help you with?")

        if prompt:
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            try:
                use_agent = st.session_state.get("use_agent", True)
                model_choice = st.session_state.get("model_choice", "gpt4")

                if use_agent:
                    result = ask_agent(prompt, conversation_history=st.session_state.messages[:-1])
                    assistant_content = result.get("response", "")
                    actions = result.get("actions", [])

                    # Detect agent-requested analysis tools
                    triggered_flags = []
                    for action in actions:
                        tool_name = action.get("tool")
                        flag = registry.get_analysis_flag(tool_name)
                        if flag:
                            triggered_flags.append(flag)
                            st.session_state[flag] = True

                    # If any analysis flags were triggered, show UI messages only
                    if triggered_flags:
                        for flag in triggered_flags:
                            message = registry.get_ui_message(flag)
                            if message:
                                st.session_state.messages.append({"role": "assistant", "content": message})
                                with st.chat_message("assistant"):
                                    st.markdown(message)
                        return  # ✅ Do not show assistant_content or tool results

                    # Otherwise, show assistant content as usual
                    st.session_state.messages.append({"role": "assistant", "content": assistant_content})
                    with st.chat_message("assistant"):
                        st.markdown(assistant_content)

                    # Optionally show execution messages for tools not linked to flags
                    if result.get("actions"):
                        for action in result["actions"]:
                            tool = action.get("tool")
                            msg = action["result"].get("message", "No output")
                            st.info(f"✅ Executed: `{tool}`\n\n**Result**: {msg}")

                else:
                    # Fallback to simple chatbot mode
                    message = ask_chatbot(user_question=st.session_state.messages, model_choice=model_choice)
                    st.session_state.messages.append({"role": "assistant", "content": message.content})
                    with st.chat_message("assistant"):
                        st.markdown(message.content)

            except Exception as e:
                error_message = f"Sorry, I encountered an error: {str(e)}"
                st.session_state.messages.append({"role": "assistant", "content": error_message})
                with st.chat_message("assistant"):
                    st.markdown(error_message)
