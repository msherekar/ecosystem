import json
import openai
import streamlit as st
import asyncio
from typing import List
from src.mcp.core.registry import get_mcp_registry
from src.mcp.core.training_collector import get_training_collector

class Agent:
    def __init__(self, api_key: str):
        # Use OpenRouter's API endpoint instead of OpenAI's direct API
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        self.mcp_registry = None
        self.memory = []
        self.available_tools = []  # Tools set by intelligent router
        self.training_collector = None

    async def _ensure_mcp_initialized(self):
        """Ensure MCP registry is initialized"""
        if self.mcp_registry is None:
            self.mcp_registry = await get_mcp_registry()
        return self.mcp_registry

    async def _ensure_training_collector_initialized(self):
        """Ensure training data collector is initialized"""
        if self.training_collector is None:
            self.training_collector = await get_training_collector()
        return self.training_collector

    def set_available_tools(self, tools):
        """Set available tools (called by intelligent router)"""
        self.available_tools = tools

    async def get_file_status_context(self):
        """Get file status context from MCP registry"""
        try:
            mcp_registry = await self._ensure_mcp_initialized()
            context = mcp_registry.get_aggregated_context()
            
            # Extract relevant information for agent
            file_status = []
            
            server_contexts = context.get("server_contexts", {})
            for server_name, server_context in server_contexts.items():
                if server_context.get("data_uploaded"):
                    file_status.append(f"✅ {server_name.capitalize()} data uploaded")
                    
                    # Add analysis status
                    pipeline_status = server_context.get("pipeline_status", {})
                    for step, completed in pipeline_status.items():
                        if completed:
                            file_status.append(f"✅ {step.replace('_', ' ').title()} completed")
                        else:
                            file_status.append(f"⏳ {step.replace('_', ' ').title()} pending")
            
            if not file_status:
                file_status.append("📁 No data uploaded yet")
            
            return "\n".join(file_status)
            
        except Exception as e:
            return f"❌ Error getting file status: {str(e)}"

    def get_tool_memory_summary(self):
        """Get summary of recent tool usage"""
        if not self.memory:
            return "No recent tool usage."
        
        recent_tools = [entry.get("tool", "unknown") for entry in self.memory[-5:]]
        return f"Recent tools used: {', '.join(recent_tools)}"

    def process_command(self, command, conversation_history=None):
        if conversation_history is None:
            conversation_history = []

        # Limit conversation history to last 3 messages to reduce costs
        if len(conversation_history) > 6:  # 3 user + 3 assistant messages
            conversation_history = conversation_history[-6:]

        # Get context synchronously to avoid event loop issues
        file_status = self._get_simple_file_status()
        tool_summary = self.get_tool_memory_summary()

        # Enhanced system prompt for bioinformatics assistant
        system_prompt = f"""You are an expert bioinformatics assistant with deep knowledge of:
- RNA-seq and scRNA-seq analysis pipelines
- Statistical methods (DESeq2, Seurat, scanpy)
- Biological interpretation of genomics data
- Data visualization and quality control

Current Analysis State:
{file_status}

Recent Activity:
{tool_summary}

Your role is to:
1. Guide users through bioinformatics workflows
2. Interpret analysis results and provide biological insights
3. Suggest appropriate next steps based on current data state
4. Use available tools to perform analyses when requested
5. Explain complex biological concepts in accessible terms

When users ask for analysis, use the appropriate tools. When they ask about results, provide biological interpretation and suggest next steps.

Be conversational, helpful, and focus on actionable biological insights."""

        # Prepare messages for the API
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        for msg in conversation_history:
            messages.append(msg)
        
        # Add current command
        messages.append({"role": "user", "content": command})

        try:
            # Use available tools set by intelligent router
            tools = self.available_tools
            if not tools:
                # Fallback to empty tools list to avoid MCP complexity
                tools = []

            # Make API call with tools (if any)
            if tools:
                response = self.client.chat.completions.create(
                    model="anthropic/claude-3.5-sonnet",
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=0.1,
                    max_tokens=4000
                )
            else:
                # No tools available, just chat
                response = self.client.chat.completions.create(
                    model="anthropic/claude-3.5-sonnet",
                    messages=messages,
                    temperature=0.1,
                    max_tokens=4000
                )

            assistant_message = response.choices[0].message
            actions = []

            # Handle tool calls (simplified without MCP for now)
            if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                    # For now, just log the tool call without executing
                    # This avoids the async event loop issue
                    tool_result = {
                        "success": False,
                        "message": "Tool execution temporarily disabled to fix async issues"
                    }

                    # Store in memory
                    self.memory.append({
                        "tool": function_name,
                        "arguments": arguments,
                        "result": tool_result
                    })

                    actions.append({
                        "tool": function_name,
                        "arguments": arguments,
                        "result": tool_result
                    })

            return {
                "response": assistant_message.content or "",
                "actions": actions,
                "tool_calls": len(assistant_message.tool_calls) if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls else 0
            }

        except Exception as e:
            return {
                "response": f"I encountered an error: {str(e)}",
                "actions": [],
                "tool_calls": 0
            }

    def _get_simple_file_status(self):
        """Simple file status without MCP - fallback for when async is problematic"""
        file_status = []
        
        # Check session state for data
        if st.session_state.get("anndata") is not None:
            file_status.append("✅ scRNA-seq data uploaded")
            
            # Check analysis steps
            if st.session_state.get("qc_done"):
                file_status.append("✅ Quality Control completed")
            if st.session_state.get("filtering_done"):
                file_status.append("✅ Filtering completed")
            if st.session_state.get("normalization_done"):
                file_status.append("✅ Normalization completed")
            if st.session_state.get("dimred_done"):
                file_status.append("✅ Dimensionality Reduction completed")
            if st.session_state.get("clustering_done"):
                file_status.append("✅ Clustering completed")
            if st.session_state.get("dea_done"):
                file_status.append("✅ Differential Expression completed")
            if st.session_state.get("enrichment_done"):
                file_status.append("✅ Enrichment Analysis completed")
        
        if st.session_state.get("rnaseq_counts_df") is not None:
            file_status.append("✅ RNA-seq data uploaded")
            if st.session_state.get("deseq_results"):
                file_status.append("✅ DESeq2 Analysis completed")
            if st.session_state.get("go_results"):
                file_status.append("✅ GO Enrichment completed")
        
        if not file_status:
            file_status.append("📁 No data uploaded yet")
        
        return "\n".join(file_status)

    def add_to_memory(self, item):
        self.memory.append(item)

    def get_memory(self):
        return self.memory

    async def chat(self, user_message: str) -> tuple[str, List[str]]:
        """Enhanced chat method using MCP tools"""
        try:
            print(f"🔧 DEBUG: chat() called with message: '{user_message}'")
            
            # Ensure MCP is initialized
            print("🔧 DEBUG: Initializing MCP registry...")
            mcp_registry = await self._ensure_mcp_initialized()
            print(f"🔧 DEBUG: MCP registry initialized: {mcp_registry is not None}")
            
            # Initialize training collector
            training_collector = await self._ensure_training_collector_initialized()
            
            # Get current context
            print("🔧 DEBUG: Getting file status context...")
            context = await self.get_file_status_context()
            print(f"🔧 DEBUG: Context received: {context[:100]}...")
            
            # If user is asking about plots/results, get current step context only
            if any(keyword in user_message.lower() for keyword in ['plot', 'result', 'chart', 'graph', 'visualization', 'summarize']):
                print("🔧 DEBUG: User asking about plots - getting current step context only")
                current_step = st.session_state.get("scrna_current_step", "qc")
                step_names = {
                    "input_summary": "Data Summary",
                    "qc": "Quality Control", 
                    "filtering": "Filtering",
                    "normalization": "Normalization",
                    "dimred": "Dimensionality Reduction (PCA)",
                    "clustering": "Clustering",
                    "viz": "Visualization (UMAP)",
                    "dea": "Differential Expression",
                    "enrichment": "Enrichment Analysis"
                }
                current_step_name = step_names.get(current_step, current_step)
                context = f"Currently viewing: {current_step_name} step"
                print(f"🔧 DEBUG: Modified context for plot analysis: {context}")
            
            # Get available tools from MCP
            print("🔧 DEBUG: Getting tool definitions...")
            available_tools = mcp_registry.get_tool_definitions_for_agent()
            print(f"🔧 DEBUG: Available tools count: {len(available_tools) if available_tools else 0}")
            
            # Build conversation history from Streamlit session
            conversation_history = []
            if "messages" in st.session_state:
                # Get last 6 messages (3 exchanges) for context
                recent_messages = st.session_state.messages[-6:] if len(st.session_state.messages) > 6 else st.session_state.messages
                for msg in recent_messages[:-1]:  # Exclude the current message
                    conversation_history.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            messages = [
                {
                    "role": "system",
                    "content": f"""
                    You are an intelligent bioinformatics assistant helping users analyze their data. 
                    You provide conversational, contextual responses that directly answer the user's questions.
                    
                    CRITICAL: When users ask about plots, charts, graphs, visualizations, or want to summarize results on the current page, you MUST use the "analyze_current_plots" tool to get the actual data before responding. Do not provide generic responses about plots without first calling this tool.
                    
                    IMPORTANT GUIDELINES:
                    1. ALWAYS use tools when users ask about plots, visualizations, or results
                    2. Answer the user's specific question - don't just dump tool outputs
                    3. Use conversation history to avoid repeating information
                    4. Be conversational and helpful, not robotic
                    5. When using tools, interpret the results in context of the user's question
                    6. If you've already provided information, build on it rather than repeating it
                    
                    Your capabilities:
                    - Analyze QC metrics, filtering, normalization, clustering, and visualization results
                    - Interpret biological significance of findings
                    - Suggest next steps in analysis pipelines
                    - Answer specific questions about plots and data patterns
                    
                    Current analysis state:
                    {context}
                    
                    When users ask about plots or results, FIRST use the analyze_current_plots tool to get current data, THEN 
                    provide a natural, conversational response that directly addresses their question.
                    """
                }
            ]
            
            # Add conversation history
            messages.extend(conversation_history)
            
            # Add current user message
            messages.append({
                "role": "user", 
                "content": user_message
            })
            
            # Add tools if available
            kwargs = {"messages": messages}
            if available_tools:
                kwargs["tools"] = available_tools
                
                # Force tool usage for plot-related questions
                if any(keyword in user_message.lower() for keyword in ['plot', 'chart', 'graph', 'visualization', 'summarize', 'results on this page', 'on this page']):
                    # Find the analyze_current_plots tool
                    plot_tool = None
                    for tool in available_tools:
                        if tool.get("function", {}).get("name") == "analyze_current_plots":
                            plot_tool = tool
                            break
                    
                    if plot_tool:
                        kwargs["tool_choice"] = {"type": "function", "function": {"name": "analyze_current_plots"}}
                        print("🔧 DEBUG: Forcing analyze_current_plots tool usage for plot question")
                    else:
                        kwargs["tool_choice"] = "auto"
                        print("🔧 DEBUG: analyze_current_plots tool not found, using auto")
                else:
                    kwargs["tool_choice"] = "auto"
                
                print(f"🔧 DEBUG: Making API call with {len(available_tools)} tools")
            else:
                print("🔧 DEBUG: Making API call without tools")
            
            print("🔧 DEBUG: Calling OpenAI API...")
            response = self.client.chat.completions.create(
                model="openai/gpt-4",
                temperature=0.3,  # Add some creativity for more natural responses
                **kwargs
            )
            print("🔧 DEBUG: API call completed")
            
            assistant_message = response.choices[0].message
            assistant_content = assistant_message.content or ""
            print(f"🔧 DEBUG: Assistant content length: {len(assistant_content)}")
            print(f"🔧 DEBUG: Assistant content preview: {assistant_content[:100]}...")
            
            # Handle tool calls via MCP
            triggered_flags = []
            tool_results = []
            
            if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
                print(f"🔧 DEBUG: Processing {len(assistant_message.tool_calls)} tool calls")
                for tool_call in assistant_message.tool_calls:
                    try:
                        tool_name = tool_call.function.name
                        parameters = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                        print(f"🔧 DEBUG: Executing tool: {tool_name} with params: {parameters}")
                        
                        # Execute tool via MCP registry
                        result = await mcp_registry.execute_tool(tool_name, parameters)
                        print(f"🔧 DEBUG: Tool result: {result}")
                        
                        if result.get("success"):
                            # Tool executed successfully - store result for context
                            tool_result = result.get("result", {})
                            tool_message = tool_result.get("message", "")
                            if tool_message:
                                tool_results.append(f"Tool {tool_name}: {tool_message}")
                                print(f"🔧 DEBUG: Stored tool result: {len(tool_message)} chars")
                        else:
                            # Tool execution failed
                            error_msg = result.get("message", "Unknown error")
                            tool_results.append(f"Tool {tool_name} failed: {error_msg}")
                            print(f"🔧 DEBUG: Tool execution failed: {error_msg}")
                        
                    except Exception as e:
                        error_msg = f"Error executing tool {tool_call.function.name}: {str(e)}"
                        tool_results.append(error_msg)
                        print(f"🔧 DEBUG: Tool execution exception: {str(e)}")
                
                # If we have tool results but no assistant content, make a follow-up call
                if tool_results and not assistant_content.strip():
                    print("🔧 DEBUG: No assistant content but have tool results, making follow-up call...")
                    
                    # Add tool results to conversation and ask for interpretation
                    follow_up_messages = messages + [
                        {
                            "role": "assistant",
                            "content": f"I've gathered the following information:\n\n" + "\n".join(tool_results)
                        },
                        {
                            "role": "user",
                            "content": f"Based on this information, please provide a conversational answer to my original question: {user_message}"
                        }
                    ]
                    
                    follow_up_response = self.client.chat.completions.create(
                        model="openai/gpt-4",
                        messages=follow_up_messages,
                        temperature=0.3
                    )
                    
                    assistant_content = follow_up_response.choices[0].message.content or ""
                    print(f"🔧 DEBUG: Follow-up response length: {len(assistant_content)}")
            else:
                print("🔧 DEBUG: No tool calls in response")
            
            # 🎯 COLLECT TRAINING DATA
            try:
                success = len(assistant_content) > 0 and "error" not in assistant_content.lower()
                await training_collector.collect_conversation_turn(
                    user_message=user_message,
                    assistant_response=assistant_content,
                    tool_results=tool_results,
                    success=success
                )
                print("🔧 DEBUG: Training data collected successfully")
            except Exception as e:
                print(f"🔧 DEBUG: Failed to collect training data: {e}")
            
            print(f"🔧 DEBUG: Final response length: {len(assistant_content)}")
            return assistant_content, triggered_flags
            
        except Exception as e:
            print(f"🔧 DEBUG: Exception in chat(): {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Still try to collect failed interactions for training
            try:
                training_collector = await self._ensure_training_collector_initialized()
                await training_collector.collect_conversation_turn(
                    user_message=user_message,
                    assistant_response=f"Error: {str(e)}",
                    tool_results=[],
                    success=False
                )
            except:
                pass  # Don't let training collection errors break the main flow
            
            return f"I encountered an error while processing your request: {str(e)}", []
