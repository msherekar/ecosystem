"""
Enhanced Chat Handler - Integrates Hybrid Routing with Chat Interface

This handler demonstrates how to integrate the hybrid routing system
with your existing chat interface, providing optimal performance
through intelligent routing decisions.
"""

import asyncio
import logging
import streamlit as st
from typing import Dict, List, Any, Optional
import time
import json

from .hybrid_router import hybrid_router, RoutingStrategy, ExecutionResult
from .schema import tools as openai_tools  # Your existing OpenAI function schema
from src.modules.search.geo import geo_display


class EnhancedChatHandler:
    """
    Enhanced chat handler that intelligently routes user requests
    through the optimal execution path.
    
    Features:
    - Hybrid routing (Direct/MCP/LLM)
    - Performance monitoring
    - Context preservation
    - Fallback mechanisms
    - User feedback integration
    """
    
    def __init__(self):
        self.logger = logging.getLogger("enhanced_chat")
        self.router_initialized = False
        
        # Session state management
        self.session_context_keys = [
            "uploaded_data", "analysis_type", "current_project",
            "processing_pipeline", "user_preferences"
        ]
        
        # ENHANCED: Conversation memory for context-aware responses
        self.conversation_memory = {
            "recent_questions": [],  # Last 5 questions
            "analysis_context": {},  # Current analysis state
            "user_interests": set(),  # Topics user has asked about
            "last_analysis_topic": None  # What was last analyzed
        }
    
    async def initialize(self):
        """Initialize the hybrid router"""
        if not self.router_initialized:
            success = await hybrid_router.initialize()
            if success:
                self.router_initialized = True
                self.logger.info("Enhanced chat handler initialized")
            else:
                self.logger.error("Failed to initialize hybrid router")
                raise Exception("Router initialization failed")
    
    async def handle_user_message(self, user_input: str) -> Dict[str, Any]:
        """
        Main handler for user messages with intelligent routing.
        
        Args:
            user_input: User's natural language message
            
        Returns:
            Dict containing response, routing info, and performance metrics
        """
        # Ensure router is initialized
        if not self.router_initialized:
            await self.initialize()
        
        # Get current session context
        context = self._get_session_context()
        
        # ENHANCED: Add conversation memory context for better routing
        conversation_context = self._get_conversation_context_for_routing()
        context.update(conversation_context)
        
        # Log the request
        self.logger.info(f"Processing user request: {user_input[:100]}...")
        
        # Route and execute the request
        start_time = time.time()
        execution_result = await hybrid_router.route_request(user_input, context)
        total_time = time.time() - start_time
        
        # Process the result
        response = await self._process_execution_result(execution_result, user_input)
        
        # Update session context based on result
        self._update_session_context(execution_result, user_input)
        
        # ENHANCED: Update conversation memory for better follow-up handling
        self._update_conversation_memory(user_input, execution_result)
        
        # Prepare response with metadata
        return {
            "response": response,
            "routing_info": {
                "strategy_used": execution_result.strategy_used.value,
                "execution_time": execution_result.execution_time,
                "total_time": total_time,
                "success": execution_result.success
            },
            "performance": hybrid_router.get_performance_summary(),
            "suggestions": self._generate_follow_up_suggestions(execution_result, user_input)
        }
    
    def _get_session_context(self) -> Dict[str, Any]:
        """Extract relevant context from Streamlit session state"""
        context = {}
        
        for key in self.session_context_keys:
            if key in st.session_state:
                context[key] = st.session_state[key]
        
        # Add derived context
        if "uploaded_data" in st.session_state:
            context["has_data"] = True
            # Analyze data type if possible
            data = st.session_state["uploaded_data"]
            if hasattr(data, 'shape'):
                context["data_shape"] = data.shape
            if hasattr(data, 'columns'):
                context["data_columns"] = list(data.columns)[:10]  # First 10 columns
        
        # Add analysis-specific context for better routing
        if "anndata" in st.session_state and st.session_state.anndata is not None:
            context["analysis_type"] = "scrnaseq"
            context["uploaded_data"] = True
        
        if "rnaseq_counts_df" in st.session_state:
            context["analysis_type"] = "rnaseq"
            context["uploaded_data"] = True
            
        if "atacseq_peaks_df" in st.session_state:
            context["analysis_type"] = "atacseq"
            context["uploaded_data"] = True
        
        # Add current step context for scRNA-seq analysis
        if "scrna_current_step" in st.session_state:
            context["current_step"] = st.session_state["scrna_current_step"]
            
        # Add completion status for various analysis steps
        analysis_steps = ["qc", "filtering", "normalization", "dimred", "clustering", "viz", "dea", "enrichment"]
        for step in analysis_steps:
            done_key = f"{step}_done"
            if done_key in st.session_state:
                context[done_key] = st.session_state[done_key]
        
        return context
    
    async def _process_execution_result(self, result: ExecutionResult, user_input: str) -> Dict[str, Any]:
        """Process the execution result and format response"""
        
        if not result.success:
            return {
                "type": "error",
                "message": f"I encountered an error processing your request: {result.error}",
                "suggestion": "Please try rephrasing your request or check if all required data is uploaded."
            }
        
        # Process based on strategy used
        if result.strategy_used == RoutingStrategy.DIRECT:
            return await self._process_direct_result(result.result)
        
        elif result.strategy_used == RoutingStrategy.MCP:
            return await self._process_mcp_result(result.result, user_input, self._get_session_context())
        
        elif result.strategy_used == RoutingStrategy.LLM:
            return await self._process_llm_result(result.result)
        
        else:
            return {"type": "unknown", "message": "Unknown routing strategy used"}
    
    async def _process_direct_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Process results from direct routing"""
        
        result_type = result.get("type", "")
        
        # Handle all search types generically (geo_search, tcga_search, uniprot_search, etc.)
        if result_type.endswith("_search"):
            # Handle search results from any database
            search_results = result.get("results", {})
            provider_name = search_results.get("provider_display_name", result.get("provider", "Database"))
            
            # Return results data for main UI thread to display
            if search_results.get("hits"):
                return {
                    "type": "search_results",
                    "message": f"Found {len(search_results.get('hits', []))} {provider_name} datasets matching your query.",
                    "data": search_results,
                    "display_results": True,  # Flag to tell UI to display results
                    "count": search_results.get('count', 0),
                    "provider": result.get("provider")
                }
            else:
                return {
                    "type": "no_results",
                    "message": f"No {provider_name} datasets found matching your query. Try different keywords."
                }
        
        elif result.get("type") == "file_upload":
            # Handle file upload widget
            st.write("**Please upload your file:**")
            uploaded_file = st.file_uploader(
                "Choose a file",
                type=['csv', 'h5ad', 'xlsx', 'tsv', 'h5', 'txt']
            )
            
            if uploaded_file is not None:
                # Process the uploaded file (you'd implement actual file processing)
                st.session_state["uploaded_data"] = uploaded_file
                return {
                    "type": "file_uploaded",
                    "message": f"Successfully uploaded {uploaded_file.name}",
                    "filename": uploaded_file.name
                }
            else:
                return {
                    "type": "awaiting_upload",
                    "message": "Please select a file to upload."
                }
        
        elif result.get("type") == "create_project":
            project_name = result.get("project_name", "Unknown")
            return {
                "type": "project_created",
                "message": f"Successfully created project: {project_name}",
                "project_name": project_name
            }
        
        else:
            return {
                "type": "direct_success",
                "message": "Request processed successfully",
                "data": result
            }
    
    async def _process_mcp_result(self, result: Dict[str, Any], user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process results from MCP routing"""
        
        tools_used = result.get("tools", [])
        tools_count = result.get("tools_used", len(tools_used))
        
        # Check if this was a plot analysis
        plot_analysis_tools = ["analyze_current_plots", "create_pca_plot", "create_umap_plot", "create_volcano_plot"]
        was_plot_analysis = False
        
        if tools_used:
            tool_names = [tool.get("name") if isinstance(tool, dict) else str(tool) for tool in tools_used]
            was_plot_analysis = any(tool_name in plot_analysis_tools for tool_name in tool_names)
        
        # Extract the actual result content - FIXED: Handle quadruple-nested structure!
        # The complete nesting is: result["result"]["data"]["result"]["message"]
        # - Hybrid router wraps in "result" 
        # - MCP client wraps in "data"
        # - MCP handler puts insights in "message"
        mcp_result = result.get("result", {})
        
        # DEBUG: Log what we're extracting
        print(f"🔧 DEBUG CHAT HANDLER: Extracting from result keys: {list(result.keys())}")
        print(f"🔧 DEBUG CHAT HANDLER: MCP result keys: {list(mcp_result.keys()) if isinstance(mcp_result, dict) else 'Not a dict'}")
        
        # DEEP DEBUG: Print the entire nested structure
        print(f"🔧 DEEP DEBUG: Full result structure:")
        print(json.dumps(result, indent=2, default=str)[:2000])  # Limit to 2000 chars
        
        # Navigate through the nested structure to find the actual insights
        message_content = ""
        if isinstance(mcp_result, dict):
            # Try the quadruple-nested path: result["result"]["data"]["result"]["message"]
            data_layer = mcp_result.get("data", {})
            print(f"🔧 DEEP DEBUG: Data layer type: {type(data_layer)}")
            print(f"🔧 DEEP DEBUG: Data layer content: {data_layer}")
            
            if isinstance(data_layer, dict):
                # FIXED: The data layer contains another "result" field!
                inner_result = data_layer.get("result", {})
                if isinstance(inner_result, dict):
                    message_content = inner_result.get("message", "")
                    print(f"🔧 DEBUG CHAT HANDLER: Found message in inner result layer: '{message_content}'")
                    
                    # ENHANCED: Check if this is a conceptual question that should be re-routed to LLM
                    if message_content == "CONCEPTUAL_QUESTION_ROUTE_TO_LLM":
                        print(f"🔧 DEBUG CHAT HANDLER: Detected conceptual question, re-routing to LLM")
                        # Re-route this to LLM with proper context
                        return await self._handle_conceptual_question_with_llm(result, user_input, context)
                    
                else:
                    # Fallback: Try direct message in data layer (shouldn't happen)
                    message_content = data_layer.get("message", "")
                    print(f"🔧 DEBUG CHAT HANDLER: Found message in data layer: '{message_content}'")
            else:
                # Fallback: Try direct message in MCP result
                message_content = mcp_result.get("message", "")
                print(f"🔧 DEBUG CHAT HANDLER: Found message in direct layer: '{message_content}'")
        else:
            # Final fallback: try direct message (shouldn't happen with MCP)
            message_content = result.get("message", "")
            print(f"🔧 DEBUG CHAT HANDLER: Found message in fallback layer: '{message_content}'")
        
        print(f"🔧 DEBUG CHAT HANDLER: Final message content: '{message_content}'")
        print(f"🔧 DEBUG CHAT HANDLER: Final message length: {len(message_content)}")
        
        if message_content and not message_content.startswith("Analysis completed"):
            # Use the actual analysis content from the deeply nested MCP result
            response_message = message_content
        else:
            # Fallback logic
            if was_plot_analysis and tools_count > 0:
                response_message = f"🔍 Plot analysis completed using {tools_count} specialized bioinformatics tools"
            elif tools_count > 0:
                response_message = f"✅ Analysis completed using {tools_count} specialized tools"
            else:
                # No tools were used - might be a simple analysis
                response_message = message_content or "Analysis completed with available data"
        
        return {
            "type": "mcp_analysis",
            "message": response_message,
            "tools": [tool.get("name", "Unknown") if isinstance(tool, dict) else str(tool) for tool in tools_used],
            "tools_count": tools_count,
            "data": result,
            "was_plot_analysis": was_plot_analysis
        }
    
    async def _process_llm_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Process results from LLM routing"""
        
        # Extract the actual response content
        actual_result = result.get("result", "")
        method = result.get("method", "unknown")
        tools_used = result.get("tools_used", [])
        
        # Use the actual LLM response if available
        if isinstance(actual_result, str) and actual_result.strip():
            if actual_result != "LLM execution completed":
                response_message = actual_result
            else:
                response_message = "Response generated using AI reasoning"
        else:
            response_message = "Response generated using AI reasoning"
        
        response_data = {
            "type": "llm_response",
            "message": response_message,
            "method": method,
            "data": result
        }
        
        # Add tool information if function calling was used
        if tools_used:
            response_data["tools_used"] = tools_used
            response_data["message"] = f"🤖 {response_message}"
        
        # Add usage information if available
        usage = result.get("usage")
        if usage:
            response_data["usage"] = usage
        
        return response_data
    
    def _update_session_context(self, result: ExecutionResult, user_input: str):
        """Update session context based on execution result"""
        
        if result.success and result.result:
            # Update context based on what happened
            if result.strategy_used == RoutingStrategy.DIRECT:
                direct_result = result.result
                
                # Handle all search types generically
                if direct_result.get("type", "").endswith("_search"):
                    provider = direct_result.get("provider", "unknown")
                    st.session_state["last_search"] = {
                        "type": provider,
                        "query": user_input,
                        "results": direct_result.get("results")
                    }
                
                elif direct_result.get("type") == "file_upload":
                    if "uploaded_data" in st.session_state:
                        st.session_state["analysis_ready"] = True
                
                elif direct_result.get("type") == "create_project":
                    st.session_state["current_project"] = direct_result.get("project_name")
    
    def _generate_follow_up_suggestions(self, result: ExecutionResult, user_input: str) -> List[str]:
        """Generate intelligent follow-up suggestions based on the result"""
        
        suggestions = []
        
        if result.success and result.result:
            if result.strategy_used == RoutingStrategy.DIRECT:
                direct_result = result.result
                
                # Handle all search types generically
                if direct_result.get("type", "").endswith("_search"):
                    suggestions.extend([
                        "Download a dataset for analysis",
                        "Search for related datasets",
                        "Look up literature about these datasets"
                    ])
                
                elif direct_result.get("type") == "file_upload":
                    suggestions.extend([
                        "Perform quality control analysis",
                        "Show data summary",
                        "Start preprocessing pipeline"
                    ])
                
                elif direct_result.get("type") == "create_project":
                    suggestions.extend([
                        "Upload data files",
                        "Set up analysis parameters",
                        "Import existing analysis"
                    ])
            
            elif result.strategy_used == RoutingStrategy.MCP:
                suggestions.extend([
                    "Visualize the results",
                    "Export the analysis",
                    "Run additional analysis steps"
                ])
        
        else:
            # Error occurred - suggest alternatives
            suggestions.extend([
                "Try rephrasing your request",
                "Check if required data is uploaded",
                "Ask for help with specific analysis steps"
            ])
        
        return suggestions[:3]  # Limit to top 3 suggestions
    
    def display_routing_performance(self):
        """Display routing performance metrics in Streamlit sidebar"""
        
        if self.router_initialized:
            with st.sidebar:
                st.subheader("🚀 Routing Performance")
                
                perf = hybrid_router.get_performance_summary()
                metrics = perf["metrics"]
                
                # Display success rates
                for strategy, stats in metrics.items():
                    if stats["total"] > 0:
                        success_rate = stats["success"] / stats["total"]
                        avg_time = stats["avg_time"]
                        
                        st.metric(
                            label=f"{strategy.value.title()} Success Rate",
                            value=f"{success_rate:.1%}",
                            delta=f"{avg_time:.2f}s avg"
                        )
                
                # Display cache efficiency
                cache_size = perf["cache_size"]
                st.metric("Route Cache", f"{cache_size} entries")
                
                # Display routing stats
                routing_stats = perf["routing_stats"]
                if routing_stats["total_attempts"] > 0:
                    direct_rate = routing_stats["direct_routing_rate"]
                    st.metric("Direct Routing Rate", f"{direct_rate:.1%}")
    
    async def _handle_conceptual_question_with_llm(self, mcp_result: Dict[str, Any], user_input: str, context: Dict) -> Dict[str, Any]:
        """Handle conceptual questions by routing to LLM with current analysis context"""
        print(f"🔧 DEBUG CHAT HANDLER: Routing conceptual question to LLM with context")
        
        # Get current analysis context from session state
        analysis_context = self._build_analysis_context_for_llm()
        
        # Prepare context-enriched prompt for LLM
        enriched_user_input = self._create_context_aware_prompt(user_input, analysis_context)
        
        # Route to LLM with enhanced context
        from .hybrid_router import hybrid_router
        
        # Force LLM routing by providing a context that favors LLM
        llm_context = {
            **context,
            "force_llm": True,
            "conceptual_question": True,
            "analysis_context": analysis_context
        }
        
        # Execute LLM routing directly
        llm_result = await hybrid_router._execute_strategy(
            RoutingStrategy.LLM, 
            enriched_user_input, 
            llm_context
        )
        
        if llm_result.get("success"):
            return {
                "type": "conceptual_llm_response",
                "message": llm_result.get("result", "Conceptual explanation provided"),
                "method": "context_aware_llm",
                "was_rerouted": True,
                "original_route": "mcp",
                "context_used": analysis_context
            }
        else:
            # Fallback to a generic response if LLM fails
            return {
                "type": "conceptual_fallback",
                "message": "I understand you're asking a conceptual question about the analysis. Could you rephrase your question or be more specific?",
                "was_rerouted": True,
                "llm_error": llm_result.get("error", "Unknown error")
            }
    
    def _build_analysis_context_for_llm(self) -> Dict[str, Any]:
        """Build rich analysis context for LLM understanding"""
        import streamlit as st
        
        context = {
            "current_step": st.session_state.get("scrna_current_step", "unknown"),
            "analysis_type": "scRNA-seq",
            "data_available": False
        }
        
        # Add data information if available
        if "anndata" in st.session_state and st.session_state.anndata is not None:
            anndata = st.session_state.anndata
            context.update({
                "data_available": True,
                "n_cells": anndata.n_obs,
                "n_genes": anndata.n_vars,
                "has_pca": "pca" in anndata.uns,
                "processing_steps": {
                    "qc_done": st.session_state.get("qc_done", False),
                    "filtering_done": st.session_state.get("filtering_done", False),
                    "normalization_done": st.session_state.get("normalization_done", False),
                    "dimred_done": st.session_state.get("dimred_done", False),
                    "clustering_done": st.session_state.get("clustering_done", False),
                    "viz_done": st.session_state.get("viz_done", False)
                }
            })
            
            # Add PCA-specific context if available
            if "pca" in anndata.uns and "variance_ratio" in anndata.uns["pca"]:
                var_ratio = anndata.uns["pca"]["variance_ratio"]
                context["pca_info"] = {
                    "pc1_variance": float(var_ratio[0] * 100),
                    "pc2_variance": float(var_ratio[1] * 100),
                    "total_variance_10pcs": float(sum(var_ratio[:10]) * 100)
                }
        
        return context
    
    def _create_context_aware_prompt(self, user_input: str, analysis_context: Dict) -> str:
        """Create a context-enriched prompt for LLM"""
        
        # Base context about the current analysis
        context_prompt = f"""
Current Analysis Context:
- Analysis Type: {analysis_context.get('analysis_type', 'Unknown')}
- Current Step: {analysis_context.get('current_step', 'Unknown')}
- Cells: {analysis_context.get('n_cells', 'Unknown')}
- Genes: {analysis_context.get('n_genes', 'Unknown')}
"""
        
        # Add PCA-specific context if available
        if analysis_context.get("pca_info"):
            pca_info = analysis_context["pca_info"]
            context_prompt += f"""
- PCA Analysis Results:
  * PC1 explains {pca_info['pc1_variance']:.1f}% of variance
  * PC2 explains {pca_info['pc2_variance']:.1f}% of variance  
  * First 10 PCs capture {pca_info['total_variance_10pcs']:.1f}% of total variance
"""
        
        # Add processing status
        if analysis_context.get("processing_steps"):
            steps = analysis_context["processing_steps"]
            completed_steps = [step for step, done in steps.items() if done]
            context_prompt += f"- Completed Steps: {', '.join(completed_steps)}\n"
        
        # Combine with user question
        enriched_prompt = f"""{context_prompt}

User Question: {user_input}

Please provide a detailed, contextual answer considering the current analysis state and data characteristics above."""
        
        return enriched_prompt

    def _update_conversation_memory(self, user_input: str, execution_result: ExecutionResult):
        """Update conversation memory for better follow-up handling"""
        import streamlit as st
        
        # Update recent questions (keep last 5)
        self.conversation_memory["recent_questions"].append({
            "question": user_input,
            "strategy_used": execution_result.strategy_used.value,
            "success": execution_result.success,
            "timestamp": time.time()
        })
        
        # Keep only last 5 questions
        if len(self.conversation_memory["recent_questions"]) > 5:
            self.conversation_memory["recent_questions"] = self.conversation_memory["recent_questions"][-5:]
        
        # Extract and track user interests/topics
        interests = self._extract_topics_from_question(user_input)
        self.conversation_memory["user_interests"].update(interests)
        
        # Update analysis context based on current session state
        current_analysis_context = {
            "current_step": st.session_state.get("scrna_current_step"),
            "last_successful_strategy": execution_result.strategy_used.value if execution_result.success else None,
            "data_available": "anndata" in st.session_state and st.session_state.anndata is not None
        }
        
        # Track what was last analyzed
        if execution_result.success and execution_result.strategy_used == RoutingStrategy.MCP:
            if any(keyword in user_input.lower() for keyword in ["plot", "pca", "analysis", "results"]):
                self.conversation_memory["last_analysis_topic"] = "plot_analysis"
        
        self.conversation_memory["analysis_context"] = current_analysis_context
        
        # Store in session state for persistence across requests
        st.session_state["conversation_memory"] = self.conversation_memory
    
    def _extract_topics_from_question(self, user_input: str) -> set:
        """Extract topics/interests from user question"""
        topics = set()
        
        # Technical topics
        if any(term in user_input.lower() for term in ["pca", "principal component"]):
            topics.add("pca")
        if any(term in user_input.lower() for term in ["cluster", "clustering"]):
            topics.add("clustering")
        if any(term in user_input.lower() for term in ["umap", "tsne", "visualization"]):
            topics.add("visualization")
        if any(term in user_input.lower() for term in ["variance", "explained variance"]):
            topics.add("variance_analysis")
        if any(term in user_input.lower() for term in ["batch", "batch effect"]):
            topics.add("batch_effects")
        if any(term in user_input.lower() for term in ["quality", "qc", "mitochondrial"]):
            topics.add("quality_control")
        
        # Question types
        if any(term in user_input.lower() for term in ["what if", "what would happen", "what will happen"]):
            topics.add("hypothetical_questions")
        if any(term in user_input.lower() for term in ["why", "how", "explain"]):
            topics.add("explanatory_questions")
        if any(term in user_input.lower() for term in ["file", "code", "script"]):
            topics.add("code_questions")
        
        return topics
    
    def _get_conversation_context_for_routing(self) -> Dict[str, Any]:
        """Get conversation context for improved routing decisions"""
        import streamlit as st
        
        # Load from session state if available
        if "conversation_memory" in st.session_state:
            self.conversation_memory = st.session_state["conversation_memory"]
        
        context = {}
        
        # Check if this is a follow-up question
        if self.conversation_memory["recent_questions"]:
            last_question = self.conversation_memory["recent_questions"][-1]
            context["is_followup"] = time.time() - last_question["timestamp"] < 300  # 5 minutes
            context["last_question"] = last_question["question"]
            context["last_strategy"] = last_question["strategy_used"]
        
        # Add user interests for better routing
        context["user_interests"] = list(self.conversation_memory["user_interests"])
        context["last_analysis_topic"] = self.conversation_memory["last_analysis_topic"]
        
        return context

    def debug_conversation_memory(self) -> Dict[str, Any]:
        """Debug method to show current conversation memory"""
        import streamlit as st
        
        # Load from session state if available
        if "conversation_memory" in st.session_state:
            self.conversation_memory = st.session_state["conversation_memory"]
        
        return {
            "recent_questions": self.conversation_memory["recent_questions"],
            "user_interests": list(self.conversation_memory["user_interests"]),
            "last_analysis_topic": self.conversation_memory["last_analysis_topic"],
            "analysis_context": self.conversation_memory["analysis_context"]
        }


# Usage example function
async def demo_enhanced_chat():
    """Demonstration of how to use the enhanced chat handler"""
    
    chat_handler = EnhancedChatHandler()
    
    # Initialize
    await chat_handler.initialize()
    
    # Example user inputs
    test_inputs = [
        "search for cancer in geo",
        "upload a file",
        "create project my_analysis",
        "show me the data summary",
        "What is the best method for differential expression analysis?"
    ]
    
    for user_input in test_inputs:
        print(f"\n--- Processing: {user_input} ---")
        
        result = await chat_handler.handle_user_message(user_input)
        
        print(f"Strategy: {result['routing_info']['strategy_used']}")
        print(f"Time: {result['routing_info']['execution_time']:.3f}s")
        print(f"Success: {result['routing_info']['success']}")
        print(f"Response: {result['response']}")
        
        if result.get("suggestions"):
            print(f"Suggestions: {', '.join(result['suggestions'])}")


# Streamlit integration helper
def integrate_with_streamlit():
    """Helper function to integrate enhanced chat with Streamlit app"""
    
    # Initialize the chat handler
    if 'chat_handler' not in st.session_state:
        st.session_state['chat_handler'] = EnhancedChatHandler()
    
    chat_handler = st.session_state['chat_handler']
    
    # Initialize if needed
    if not chat_handler.router_initialized:
        with st.spinner("Initializing intelligent routing..."):
            asyncio.run(chat_handler.initialize())
    
    # Chat interface
    st.title("🧬 Intelligent Bioinformatics Assistant")
    
    # Display performance metrics in sidebar
    chat_handler.display_routing_performance()
    
    # Chat input
    user_input = st.chat_input("Ask me anything about your bioinformatics analysis...")
    
    if user_input:
        with st.spinner("Processing your request..."):
            # Process the message
            result = asyncio.run(chat_handler.handle_user_message(user_input))
            
            # Display the result
            st.chat_message("user").write(user_input)
            
            with st.chat_message("assistant"):
                response = result["response"]
                
                if response.get("type") == "error":
                    st.error(response["message"])
                    if response.get("suggestion"):
                        st.info(response["suggestion"])
                else:
                    st.write(response.get("message", "Response processed successfully"))
                
                # Show routing info
                routing_info = result["routing_info"]
                st.caption(
                    f"Processed via {routing_info['strategy_used']} routing "
                    f"in {routing_info['execution_time']:.3f}s"
                )
                
                # Show suggestions
                suggestions = result.get("suggestions", [])
                if suggestions:
                    st.write("**You might also want to:**")
                    for suggestion in suggestions:
                        st.write(f"• {suggestion}")


if __name__ == "__main__":
    # Run the demo
    asyncio.run(demo_enhanced_chat()) 