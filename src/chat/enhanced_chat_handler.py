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
            return await self._process_mcp_result(result.result)
        
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
    
    async def _process_mcp_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Process results from MCP routing"""
        
        tools_used = result.get("tools", [])
        
        return {
            "type": "mcp_analysis",
            "message": f"Analysis completed using {len(tools_used)} specialized tools",
            "tools": [tool.get("name", "Unknown") for tool in tools_used],
            "data": result
        }
    
    async def _process_llm_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Process results from LLM routing"""
        
        return {
            "type": "llm_response",
            "message": "Response generated using AI reasoning",
            "method": result.get("method", "unknown"),
            "data": result
        }
    
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