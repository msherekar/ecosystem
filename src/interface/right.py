import streamlit as st
import asyncio
from src.agent.brain import ask_agent
from src.agent.core import Agent
from src.chat.chatbot import ask_chatbot

def chat_interface(chat_col):
    with chat_col:
        # Initialize agent if not already done
        if "agent" not in st.session_state:
            api_key = st.secrets.get("OPENROUTER_API_KEY", "")
            if api_key:
                print(f"🔧 DEBUG: Creating agent with API key length: {len(api_key)}")
                st.session_state.agent = Agent(api_key)
                print("🔧 DEBUG: Agent created successfully")
            else:
                print("🔧 DEBUG: No API key found in secrets")
                st.error("OpenRouter API key not found in secrets")
                return
        
        agent = st.session_state.agent

        # --- Intro section ---
        st.markdown("""
            <div style="text-align: center">
                <h1>💬</h1>
            </div>
        """, unsafe_allow_html=True)

        # --- Auto-scroll JavaScript ---
        st.markdown("""
            <script>
            function scrollChatToBottom() {
                // Only target chat-specific containers, NOT the entire page
                const chatSelectors = [
                    '[data-testid="stChatMessageContainer"]',
                    '.stChatMessage',
                    '[data-testid="stVerticalBlock"] [data-testid="stChatMessage"]'
                ];
                
                let scrolled = false;
                for (const selector of chatSelectors) {
                    const elements = window.parent.document.querySelectorAll(selector);
                    if (elements.length > 0) {
                        // Find the container that holds all chat messages
                        const container = elements[0].closest('[data-testid="stVerticalBlock"]');
                        if (container) {
                            container.scrollTop = container.scrollHeight;
                            scrolled = true;
                            break;
                        }
                    }
                }
                
                // If no chat container found, don't scroll anything
                // This prevents interfering with the main page scroll
            }
            
            // Auto-scroll when new chat content is added
            const observer = new MutationObserver(function(mutations) {
                let shouldScroll = false;
                mutations.forEach(function(mutation) {
                    if (mutation.addedNodes.length > 0) {
                        // Only scroll if chat messages are added
                        for (const node of mutation.addedNodes) {
                            if (node.nodeType === 1 && (
                                node.querySelector && (
                                    node.querySelector('[data-testid="stChatMessage"]') ||
                                    node.getAttribute('data-testid') === 'stChatMessage' ||
                                    node.classList.contains('stChatMessage')
                                )
                            )) {
                                shouldScroll = true;
                                break;
                            }
                        }
                    }
                });
                
                if (shouldScroll) {
                    setTimeout(scrollChatToBottom, 100);
                }
            });
            
            // Only observe chat-related areas, not the entire document
            const chatArea = window.parent.document.querySelector('[data-testid="stSidebar"]');
            if (chatArea) {
                observer.observe(chatArea, { 
                    childList: true, 
                    subtree: true,
                    attributes: false,
                    characterData: false
                });
            }
            </script>
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
            
            /* Ensure chat messages container is scrollable */
            [data-testid="stChatMessageContainer"] {
                max-height: 70vh;
                overflow-y: auto;
            }
            </style>
        """, unsafe_allow_html=True)

        # --- Display chat messages ---
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        # Add an invisible anchor at the bottom to auto-scroll to
        if st.session_state.messages:
            # Create a unique key based on message count to force re-render
            message_count = len(st.session_state.messages)
            st.markdown(f'<div id="chat-bottom-{message_count}" style="height: 1px;"></div>', unsafe_allow_html=True)
            
            # Auto-scroll to bottom using JavaScript with the unique ID - CHAT ONLY
            st.markdown(f"""
                <script>
                setTimeout(function() {{
                    // Only scroll the chat area, not the entire page
                    const chatBottom = window.parent.document.getElementById('chat-bottom-{message_count}');
                    if (chatBottom) {{
                        const chatContainer = chatBottom.closest('[data-testid="stVerticalBlock"]');
                        if (chatContainer) {{
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }}
                    }}
                }}, 300);
                </script>
            """, unsafe_allow_html=True)

        # --- Scroll to bottom button (optional) ---
        if len(st.session_state.messages) > 3:  # Only show if there are several messages
            if st.button("⬇️ Scroll to Bottom", key="scroll_bottom"):
                st.markdown("""
                    <script>
                    setTimeout(function() {
                        // Only scroll the chat area, not the entire page
                        const chatArea = window.parent.document.querySelector('[data-testid="stSidebar"]');
                        if (chatArea) {
                            const chatContainer = chatArea.querySelector('[data-testid="stVerticalBlock"]');
                            if (chatContainer) {
                                chatContainer.scrollTop = chatContainer.scrollHeight;
                            }
                        }
                    }, 100);
                    </script>
                """, unsafe_allow_html=True)
                st.rerun()

        # --- Chat input box ---
        prompt = st.chat_input("What can I help you with?")

        if prompt:
            print(f"🔧 DEBUG: User sent message: {prompt}")
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            print(f"🔧 DEBUG: Added user message to chat history. Total messages: {len(st.session_state.messages)}")
            
            # Trigger immediate scroll after adding user message - CHAT ONLY
            st.markdown("""
                <script>
                setTimeout(function() {
                    // Only scroll the chat area, not the entire page
                    const chatArea = window.parent.document.querySelector('[data-testid="stSidebar"]');
                    if (chatArea) {
                        const chatContainer = chatArea.querySelector('[data-testid="stVerticalBlock"]');
                        if (chatContainer) {
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }
                    }
                }, 100);
                </script>
            """, unsafe_allow_html=True)
            
            # Force rerun to show user message immediately
            st.rerun()

        # Process the last message if it's from user and hasn't been processed
        if (st.session_state.messages and 
            st.session_state.messages[-1]["role"] == "user" and
            not st.session_state.get("processing_last_message", False)):
            
            print("🔧 DEBUG: Processing user message...")
            
            # Mark as processing to avoid infinite loop
            st.session_state.processing_last_message = True
            
            user_prompt = st.session_state.messages[-1]["content"]
            use_agent = st.session_state.get("use_agent", True)
            model_choice = st.session_state.get("model_choice", "gpt4")

            print(f"🔧 DEBUG: use_agent={use_agent}, user_prompt='{user_prompt}'")

            with st.spinner("Thinking..."):
                try:
                    if use_agent:
                        print("🔧 DEBUG: Using agent for response...")
                        # Use async method with MCP tools
                        async def get_agent_response():
                            print("🔧 DEBUG: Calling agent.chat()...")
                            result = await agent.chat(user_prompt)
                            print(f"🔧 DEBUG: Agent response received: {type(result)}")
                            return result
                        
                        # Run async method
                        print("🔧 DEBUG: Running async agent call...")
                        response, triggered_flags = asyncio.run(get_agent_response())
                        print(f"🔧 DEBUG: Agent returned - response length: {len(response) if response else 0}, flags: {triggered_flags}")
                        
                        # Add assistant response to chat
                        if response and response.strip():
                            print("🔧 DEBUG: Adding agent response to chat")
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": response
                            })
                        else:
                            print("🔧 DEBUG: Agent response was empty, adding fallback message")
                            # Add a fallback message if response is empty
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": "I'm processing your request..."
                            })
                        
                    else:
                        print("🔧 DEBUG: Using chatbot for response...")
                        message = ask_chatbot(user_question=st.session_state.messages, model_choice=model_choice)
                        # Only add non-empty responses to chat
                        if message.content and message.content.strip():
                            st.session_state.messages.append({"role": "assistant", "content": message.content})
                        else:
                            st.session_state.messages.append({"role": "assistant", "content": "I'm having trouble generating a response."})

                except Exception as e:
                    print(f"🔧 DEBUG: Exception occurred: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    error_message = f"Sorry, I encountered an error: {str(e)}"
                    st.session_state.messages.append({"role": "assistant", "content": error_message})
                
                finally:
                    print("🔧 DEBUG: Resetting processing flag and triggering rerun")
                    # Reset processing flag
                    st.session_state.processing_last_message = False
                    # Only rerun if we successfully added a message
                    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
                        print(f"🔧 DEBUG: Final message count: {len(st.session_state.messages)}")
                        st.rerun()
                    else:
                        print("🔧 DEBUG: No assistant message to rerun with")
