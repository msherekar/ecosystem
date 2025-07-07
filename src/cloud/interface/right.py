import streamlit as st
import asyncio
from src.chat.enhanced_chat_handler import EnhancedChatHandler
from src.chat.chatbot import ask_chatbot

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
        
        # Initialize enhanced chat handler if not already done
        if "enhanced_chat_handler" not in st.session_state:
            # Set up debug logging for cost/token analysis
            import logging
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                force=True  # Override any existing configuration
            )
            
            # Ensure hybrid router logger is set to DEBUG
            hybrid_logger = logging.getLogger("hybrid_router")
            hybrid_logger.setLevel(logging.DEBUG)
            
            st.session_state.enhanced_chat_handler = EnhancedChatHandler()
            print("🔧 DEBUG: Created EnhancedChatHandler with enhanced logging enabled")
        else:
            print("🔧 DEBUG: Using existing EnhancedChatHandler")
        
        chat_handler = st.session_state.enhanced_chat_handler

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
                        print("🔧 DEBUG: Using enhanced chat handler with hybrid routing...")
                        
                        # Use hybrid routing system
                        async def get_hybrid_response():
                            print("🔧 DEBUG: Calling hybrid router...")
                            
                            # Initialize handler if needed
                            if not chat_handler.router_initialized:
                                await chat_handler.initialize()
                                print("🔧 DEBUG: Enhanced chat handler initialized")
                            
                            result = await chat_handler.handle_user_message(user_prompt)
                            print(f"🔧 DEBUG: Hybrid response received: {type(result)}")
                            return result
                        
                        # Run async method
                        print("🔧 DEBUG: Running async hybrid routing...")
                        response_data = asyncio.run(get_hybrid_response())
                        
                        # Store special display data in session state for later rendering
                        search_results_to_display = None
                        
                        # Extract response from hybrid result
                        if isinstance(response_data, dict):
                            # Check if it's a hybrid router response
                            if "response" in response_data:
                                response_info = response_data["response"]
                                
                                # Handle different response types
                                if isinstance(response_info, dict):
                                    if response_info.get("type") == "search_results":
                                        # Handle search results from any database
                                        if response_info.get("display_results"):
                                            # Store results for display after adding message
                                            search_results_to_display = {
                                                "data": response_info.get("data", {}),
                                                "count": response_info.get("count", 0),
                                                "provider": response_info.get("provider", "unknown")
                                            }
                                            response = response_info.get("message", "Search completed.")
                                        else:
                                            response = response_info.get("message", "Search completed.")
                                    elif response_info.get("type") == "error":
                                        response = response_info.get("message", "An error occurred.")
                                    else:
                                        response = response_info.get("message", str(response_info))
                                else:
                                    response = str(response_info)
                                
                                # Get routing info
                                routing_info = response_data.get("routing_info", {})
                                strategy_used = routing_info.get("strategy_used", "unknown")
                                execution_time = routing_info.get("execution_time", 0)
                                
                                print(f"🔧 DEBUG: Strategy used: {strategy_used}, time: {execution_time:.2f}s")
                                
                            else:
                                response = str(response_data)
                        else:
                            response = str(response_data)
                            
                        print(f"🔧 DEBUG: Hybrid router returned - response length: {len(response) if response else 0}")
                        
                        # Add assistant response to chat
                        if response and response.strip():
                            print("🔧 DEBUG: Adding hybrid router response to chat")
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": response
                            })
                            
                            # Store search results for center panel display
                            if search_results_to_display:
                                print(f"🔧 DEBUG: Storing {search_results_to_display['count']} search results for center panel")
                                # Set flags for center panel to display results
                                st.session_state["agent_requested_search"] = True
                                st.session_state["search_results"] = search_results_to_display["data"]
                                
                                # Add timestamp for search history
                                import datetime
                                st.session_state["_search_timestamp"] = datetime.datetime.now().strftime("%H:%M:%S")
                        else:
                            print("🔧 DEBUG: Hybrid router response was empty, adding fallback message")
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": "I'm processing your request. Could you please provide more details or try asking about your data analysis?"
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
