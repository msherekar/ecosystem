import json
import openai
import streamlit as st
import asyncio
from typing import List
from src.mcp.core.registry import get_mcp_registry

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

    async def _ensure_mcp_initialized(self):
        """Ensure MCP registry is initialized"""
        if self.mcp_registry is None:
            self.mcp_registry = await get_mcp_registry()
        return self.mcp_registry

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

        # Get context asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            file_status = loop.run_until_complete(self.get_file_status_context())
        finally:
            loop.close()
            
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
            # Use available tools set by intelligent router, or get from MCP if not set
            tools = self.available_tools
            if not tools:
                # Fallback to getting tools from MCP
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    mcp_registry = loop.run_until_complete(self._ensure_mcp_initialized())
                    tools = mcp_registry.get_tool_definitions_for_agent()
                finally:
                    loop.close()

            # Make API call with tools
            response = self.client.chat.completions.create(
                model="anthropic/claude-3.5-sonnet",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.1,
                max_tokens=4000
            )

            assistant_message = response.choices[0].message
            actions = []

            # Handle tool calls
            if assistant_message.tool_calls:
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                    # Execute tool via MCP
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        mcp_registry = loop.run_until_complete(self._ensure_mcp_initialized())
                        tool_result = loop.run_until_complete(
                            mcp_registry.execute_tool(function_name, arguments)
                        )
                    finally:
                        loop.close()

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
                "tool_calls": len(assistant_message.tool_calls) if assistant_message.tool_calls else 0
            }

        except Exception as e:
            return {
                "response": f"I encountered an error: {str(e)}",
                "actions": [],
                "tool_calls": 0
            }

    def add_to_memory(self, item):
        self.memory.append(item)

    def get_memory(self):
        return self.memory

    async def chat(self, user_message: str) -> tuple[str, List[str]]:
        """Enhanced chat method - MCP disabled to fix tool count limit"""
        # MCP disabled to fix 135 tools error
        await self._ensure_mcp_initialized()
        
        # Get current context
        context = self.get_file_status_context()
        
        # Use legacy registry tools only (under 128 limit)
        available_tools = TOOL_DEFINITIONS
        
        messages = [
            {
                "role": "system",
                "content": f"""
                You are an intelligent bioinformatics assistant for a data analysis application. 
                You can run analysis pipelines and provide expert insights about the results.
                
                Your role is to:
                1. Execute analysis tools when requested
                2. Interpret and explain analysis results shown in the center panel
                3. Analyze plots and visualizations to provide biological insights
                4. Answer questions about specific plots, data patterns, and results
                5. Suggest next steps based on current progress
                6. Provide biological context and interpretation
                7. Help troubleshoot issues
                
                SCRNASEQ PIPELINE AWARENESS:
                When working with scRNA-seq data, follow the defined pipeline order:
                1. Data Summary → 2. Quality Control → 3. Filtering → 4. Normalization → 
                5. Dimensionality Reduction → 6. Clustering → 7. Visualization → 8. Differential Expression
                
                IMPORTANT: Always suggest the correct next step based on the current pipeline position.
                If the user asks to "perform the next step" or "advance", use the 'advance_scrnaseq_step' tool.
                
                PLOT ANALYSIS CAPABILITIES:
                - You can analyze QC metrics, filtering results, normalization plots
                - You can interpret PCA, UMAP, clustering visualizations
                - You can explain volcano plots, differential expression results
                - You can analyze GO enrichment and pathway results
                - You can answer specific questions about what users see in plots
                
                IMPORTANT: You can see what's happening in the analysis interface through the context below.
                The results of tool executions appear in the center panel, not in this chat.
                Focus on interpreting results and providing guidance.
                
                Current context:
                {context}
                
                When suggesting tools to run, use the available tools. Always explain what the tool will do and why it's useful.
                """
            },
            {
                "role": "user", 
                "content": user_message
            }
        ]
        
        # Add tools if available
        kwargs = {"messages": messages}
        if available_tools:
            kwargs["tools"] = available_tools
            kwargs["tool_choice"] = "auto"
        
        try:
            response = self.client.chat.completions.create(
                model="openai/gpt-4",
                **kwargs
            )
            
            assistant_message = response.choices[0].message
            assistant_content = assistant_message.content or ""
            
            # Handle tool calls via legacy registry
            triggered_flags = []
            if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
                for tool_call in assistant_message.tool_calls:
                    try:
                        tool_name = tool_call.function.name
                        parameters = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                        
                        # Execute tool via legacy registry
                        result = registry.execute_tool(tool_name, **parameters)
                        
                        if result.get("success"):
                            # Tool executed successfully - results will appear in center panel
                            assistant_content += f"\n\n✅ Executed {tool_name} successfully. Check the center panel for results."
                        else:
                            # Tool execution failed
                            error_msg = result.get("message", "Unknown error")
                            assistant_content += f"\n\n❌ Failed to execute {tool_name}: {error_msg}"
                        
                    except Exception as e:
                        assistant_content += f"\n\n❌ Error executing tool {tool_call.function.name}: {str(e)}"
            
            return assistant_content, triggered_flags
            
        except Exception as e:
            return f"Error: {str(e)}", []
