import streamlit as st
import asyncio
from src.mcp.agent.brain import ask_agent
from src.mcp.agent.core import Agent
from src.chat.chatbot import ask_chatbot
import json

def chat_interface(right_area):
    """
    Renders the chat interface in the provided layout area
    
    Args:
        right_area: Streamlit column/container for the chat interface
    """
    with right_area:
        # Add spacing to align with left panel
        st.markdown("""
        <style>
        /* Push right panel content down */
        div[data-testid="column"]:last-child .element-container:first-child {
            margin-top: 8rem !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Add spacing div to push content down to match left panel
        st.markdown("<div style='height: 120px;'></div>", unsafe_allow_html=True)
        
        # Chat panel header
        #st.markdown("### 💬 AI Assistant")
        
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

        # --- Chat input handling ---
        if st.session_state.clicked_button == "Code-writer":
            prompt = st.chat_input("Ask to write a code here")

            # Only add system prompt once at the start
            if not st.session_state.tabular_coding:
                st.session_state.tabular_coding.append({
                    "role": "assistant", 
                    "content": """
Prompt:

Return only valid raw Python code (no markdown, no explanations).

You are writing Streamlit code to manipulate a pandas DataFrame.

Multiple DataFrames are stored as dictionaries inside st.session_state.modified_df, like:

python
Copy
Edit
{"df1": df1_dict, "df2": df2_dict, ...}
To load a selected DataFrame, use:

python
Copy
Edit
df = pd.DataFrame(st.session_state.modified_df[chosen_df])
All Streamlit UI widgets, including:

st.selectbox("Select a dataframe", ...)

st.selectbox("Select a column", ...)
must be wrapped inside a single st.form("...") block followed by a st.form_submit_button("...").

Do not place any widgets outside the form.
Only process and display output after the user clicks the submit button.
Do not return markdown or code fences — only raw Python code.
"""
                })

            if prompt:
                print(f"🔧 DEBUG: User sent code-writer message: {prompt}")
                st.session_state.tabular_coding.append({"role": "user", "content": prompt})

                with st.chat_message("user"):
                    st.markdown(prompt)

                try:
                    message = ask_chatbot(user_question=st.session_state.tabular_coding, model_choice='gpt4')

                    with st.chat_message("assistant"):
                        st.code(message.content, language="python")

                    st.session_state.tabular_coding.append({"role": "assistant", "content": message.content})
                    st.session_state.ai_code = message.content
                    st.session_state.ai_coder = True
                except Exception as e:
                    print(f"🔧 DEBUG: Exception in code-writer mode: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    error_message = f"Sorry, I encountered an error: {str(e)}"
                    st.session_state.tabular_coding.append({"role": "assistant", "content": error_message})

        else:
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
                            
                            # Handle tool calls
                            if triggered_flags:
                                for flag in triggered_flags:
                                    if flag == "pubmed_search":
                                        st.session_state.pubmed_search_query = user_prompt
                                        st.session_state.pubmed_search = True
                                    elif flag == "geo_search":
                                        st.session_state.geo_search_query = user_prompt
                                        st.session_state.geo_search = True
                            
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
