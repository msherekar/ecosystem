import json
import openai
import streamlit as st
from modules.agent.registry import registry
# from mcp.core.registry import get_mcp_registry  # Disabled to fix 135 tools error

TOOL_DEFINITIONS = registry.get_tool_definitions()

class Agent:
    def __init__(self, api_key: str):
        # Use OpenRouter's API endpoint instead of OpenAI's direct API
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        self.mcp_registry = None
        self.memory = []

    async def _ensure_mcp_initialized(self):
        """Ensure MCP registry is initialized - DISABLED to fix 135 tools error"""
        # Temporarily disable MCP to fix tool count limit
        self.mcp_registry = None
        return

    def process_command(self, command, conversation_history=None):
        if conversation_history is None:
            conversation_history = []

        file_status = self.get_file_status_context()
        tool_summary = self.get_tool_memory_summary()

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
                Use this information to provide relevant, contextual advice.
                
                When users ask about plots or results, use your analysis tools to examine the current data
                and provide detailed biological interpretations.
                
                {file_status}

                Recent tool usage:
                {tool_summary}
                
                Guidelines:
                - Be conversational and helpful
                - Explain results in biological terms
                - Suggest logical next steps
                - Point out interesting findings
                - Help interpret plots and statistics
                - Answer questions about specific data patterns
                - Provide context for what users are seeing
                """
            }
        ]

        messages.extend(conversation_history)
        messages.append({"role": "user", "content": command})

        try:
            response = self.client.chat.completions.create(
                model="openai/gpt-4",
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto"
            )

            ai_message = response.choices[0].message
            result = {"response": ai_message.content, "actions": []}

            if ai_message.tool_calls:
                for tool_call in ai_message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)

                    tool_result = registry.execute_tool(function_name, **arguments)
                    summary = tool_result.get("summary")
                    if summary:
                        st.session_state.setdefault("agent_tool_history", []).append(summary)

                    result["actions"].append({
                        "tool": function_name,
                        "arguments": arguments,
                        "result": tool_result
                    })

            return result

        except Exception as e:
            return {"response": f"Error processing command: {str(e)}", "actions": []}

    def get_file_status_context(self):
        """Get comprehensive context about current analysis state - MCP disabled"""
        # Use basic context since MCP is disabled to fix tool count issue
        return self._get_basic_context()
    
    def _get_dynamic_context_from_mcp(self):
        """Get dynamic context from all connected MCP servers - DISABLED"""
        # Disabled to fix 135 tools error
        return "MCP context disabled to fix tool count limit."
    
    def _get_basic_context(self):
        """Fallback basic context when MCP is not available"""
        context = "Current analysis state:\n"
        
        # === Data Upload Status ===
        if "rnaseq_counts_df" in st.session_state:
            counts_df = st.session_state["rnaseq_counts_df"]
            context += f"- RNA-seq counts uploaded: {counts_df.shape[0]} genes x {counts_df.shape[1]} samples\n"
        if "rnaseq_metadata_df" in st.session_state:
            metadata_df = st.session_state["rnaseq_metadata_df"]
            context += f"- RNA-seq metadata uploaded: {metadata_df.shape[0]} samples\n"
        if "anndata" in st.session_state and st.session_state.anndata is not None:
            anndata = st.session_state.anndata
            context += f"- scRNA-seq data uploaded: {anndata.n_obs} cells x {anndata.n_vars} genes\n"
        
        # === Analysis Results ===
        if "deseq_results" in st.session_state:
            results_df = st.session_state["deseq_results"]
            sig_genes = len(results_df[results_df.get("significant", False)]) if "significant" in results_df.columns else 0
            context += f"- DESeq2 analysis completed: {sig_genes} significant genes found\n"
        
        if "go_results" in st.session_state:
            context += "- Gene Ontology enrichment analysis completed\n"
        
        # === scRNA-seq Pipeline Status ===
        if "scrna_current_step" in st.session_state:
            current_step = st.session_state["scrna_current_step"]
            # Define the step order for context
            step_order = [
                ("input_summary", "Data Summary"),
                ("qc", "Quality Control"), 
                ("filtering", "Filtering"),
                ("normalization", "Normalization"),
                ("dimred", "Dimensionality Reduction"),
                ("clustering", "Clustering"),
                ("viz", "Visualization"),
                ("dea", "Differential Expression"),
                ("enrichment", "Enrichment"),
                ("markers", "Marker Genes & Cell Cycle"),
                ("trajectory", "Trajectory"),
                ("ml", "ML & Networks")
            ]
            
            # Find current step and next step
            for i, (step_key, step_name) in enumerate(step_order):
                if step_key == current_step:
                    context += f"- scRNA-seq current step: {step_name} ({step_key})\n"
                    if i + 1 < len(step_order):
                        next_step_key, next_step_name = step_order[i + 1]
                        context += f"- scRNA-seq next step: {next_step_name} ({next_step_key})\n"
                    break
        
        if "qc_done" in st.session_state and st.session_state.qc_done:
            context += "- Quality control completed\n"
        
        if "filtered" in st.session_state and st.session_state.filtered:
            context += "- Data filtering completed\n"
        
        if "normalized" in st.session_state and st.session_state.normalized:
            context += "- Data normalization completed\n"
        
        if "clustered" in st.session_state and st.session_state.clustered:
            context += "- Cell clustering completed\n"
        
        # === Active Analysis Type ===
        active_analyses = []
        if st.session_state.get("rnaseq_analysis", False):
            active_analyses.append("RNA-seq")
        if st.session_state.get("scRNAseq_analysis", False):
            active_analyses.append("scRNA-seq")
        if st.session_state.get("tabular_analysis", False):
            active_analyses.append("Tabular")
        if st.session_state.get("image_analysis", False):
            active_analyses.append("Image")
        
        if active_analyses:
            context += f"- Active analysis types: {', '.join(active_analyses)}\n"
        
        return context

    def get_tool_memory_summary(self, n=3):
        recent = st.session_state.get("agent_tool_history", [])[-n:]
        if not recent:
            return "No tools used yet."
        return "\n".join(f"- {summary}" for summary in recent)

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
