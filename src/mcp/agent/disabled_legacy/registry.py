"""
Registry system for agent tools and capabilities.
This enables dynamic registration of new analysis techniques and tools.
"""

import streamlit as st
from typing import Dict, Callable, Any, List, Optional

class ToolRegistry:
    """Registry for managing agent tools and capabilities."""
    
    def __init__(self):
        self.tools: Dict[str, Dict] = {}
        self.tool_definitions: List[Dict] = []
        self.executors: Dict[str, Callable] = {}
        self.analysis_flags: Dict[str, str] = {}
        self.analysis_messages: Dict[str, bool] = {}
    
    def register_tool(self, 
                     name: str, 
                     description: str, 
                     parameters: Dict[str, Any], 
                     executor: Callable,
                     analysis_type: str,
                     ui_message: str,
                     required_params: Optional[List[str]] = None):
        """
        Register a new tool with the registry.
        
        Parameters:
        - name: Tool name (e.g., "run_scrnaseq_clustering")
        - description: Tool description
        - parameters: Dictionary of parameters with their types and descriptions
        - executor: Function that will execute when the tool is called
        - analysis_type: Type of analysis (e.g., "rnaseq", "scrnaseq")
        - required_params: List of required parameter names
        """
        # Create tool definition in OpenAI tool format
        tool_def = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": parameters,
                    "required": required_params or []
                }
            }
        }
        
        # Store the tool definition
        self.tools[name] = tool_def
        self.tool_definitions.append(tool_def)
        self.executors[name] = executor
        self.analysis_flags[name] = f"agent_requested_{analysis_type}"
        
        flag = f"agent_requested_{analysis_type}"
        self.analysis_flags[name] = flag

        # ✅ Store UI message mapped to flag
        self.analysis_messages[flag] = ui_message or f"✅ {analysis_type.capitalize()} analysis activated. Please upload the required files."
    
    def get_tool_definitions(self) -> List[Dict]:
        """Get all tool definitions for use with OpenAI API."""
        return self.tool_definitions
    
    def get_executor(self, tool_name: str) -> Optional[Callable]:
        """Get the executor function for a specific tool."""
        return self.executors.get(tool_name)
    
    def get_analysis_flag(self, tool_name: str) -> Optional[str]:
        """Get the analysis flag associated with a tool."""
        return self.analysis_flags.get(tool_name)
    
    def get_ui_message(self, flag: str) -> Optional[str]:
        """Get the UI message associated with an analysis flag."""
        return self.analysis_messages.get(flag)
    
    def get_analysis_summary(self, analysis_type: str = "all") -> str:
        """Get detailed summary of analysis results for agent context."""
        summary = ""
        
        if analysis_type in ["all", "rnaseq"]:
            if "deseq_results" in st.session_state:
                results_df = st.session_state["deseq_results"]
                sig_up = len(results_df[(results_df.get("significant", False)) & (results_df["log2FoldChange"] > 0)])
                sig_down = len(results_df[(results_df.get("significant", False)) & (results_df["log2FoldChange"] < 0)])
                summary += f"RNA-seq DESeq2 Results: {sig_up} upregulated, {sig_down} downregulated genes. "
                
                if not results_df.empty:
                    top_gene = results_df.loc[results_df["log2FoldChange"].idxmax()]
                    summary += f"Most upregulated: {top_gene['gene']} (FC: {top_gene['log2FoldChange']:.2f}). "
        
        if analysis_type in ["all", "scrnaseq"]:
            if st.session_state.get("anndata") and st.session_state.get("clustered"):
                anndata = st.session_state.anndata
                if 'leiden' in anndata.obs:
                    clusters = anndata.obs['leiden'].value_counts()
                    summary += f"scRNA-seq: {len(clusters)} clusters, largest has {clusters.max()} cells. "
        
        return summary.strip()
    
    def execute_tool(self, tool_name: str, **kwargs) -> Dict:
        """
        Execute a tool by name with the provided arguments.
        
        Parameters:
        - tool_name: Name of the tool to execute
        - kwargs: Arguments to pass to the tool
        
        Returns:
        - Result dictionary from the tool execution
        """
        executor = self.get_executor(tool_name)
        if executor:
            # Set the associated analysis flag
            flag = self.get_analysis_flag(tool_name)
            if flag:
                st.session_state[flag] = True
                
            # Execute the tool
            return executor(**kwargs)
        else:
            return {"success": False, "message": f"Tool '{tool_name}' not found in registry"}

# Create a global registry instance
registry = ToolRegistry() 