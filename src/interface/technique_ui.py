"""
Generic Technique UI Components
Scalable UI system that can handle thousands of analysis techniques
using configuration-driven approach.
"""

import streamlit as st
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from src.mcp.core.registry import mcp_registry


@dataclass
class TechniqueConfig:
    """Configuration for any analysis technique"""
    name: str
    title: str
    description: str
    icon: str
    server_name: str
    upload_message: str
    data_check_function: callable
    workflow_function: callable


class GenericTechniqueUI:
    """
    Generic UI component that can render any analysis technique.
    Scales to thousands of techniques without code duplication.
    """
    
    def __init__(self, config: TechniqueConfig):
        self.config = config
        self.server_name = config.server_name
    
    def render(self) -> Dict[str, Any]:
        """
        Render the technique interface.
        Returns execution result for the calling interface.
        """
        # Check if data is ready
        if not self.config.data_check_function():
            st.info(f"{self.config.icon} {self.config.upload_message}")
            return {
                "success": False,
                "message": f"No {self.config.name} data uploaded",
                "show_upload_message": True
            }
        
        # Get technique context from MCP server
        context = self._get_technique_context()
        
        # Render technique-specific UI
        if context.get("has_pipeline", False):
            return self._render_pipeline_interface(context)
        else:
            return self._render_simple_interface(context)
    
    def _get_technique_context(self) -> Dict[str, Any]:
        """Get context from the technique's MCP server"""
        try:
            # Get server context through MCP registry
            server_context = mcp_registry.get_server_context(self.server_name)
            return server_context or {}
        except Exception as e:
            st.error(f"Failed to get {self.config.name} context: {e}")
            return {}
    
    def _render_pipeline_interface(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Render pipeline-based interface (like scRNA-seq)"""
        
        # Show technique header
        self._show_technique_header(context)
        
        # Show automated pipeline option if available
        if context.get("supports_automation", False):
            self._show_automated_section(context)
        
        # Show step-by-step interface
        self._show_step_by_step_section(context)
        
        # Execute current workflow
        return self.config.workflow_function()
    
    def _render_simple_interface(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Render simple interface for non-pipeline techniques"""
        
        # Show technique header
        st.markdown(f"## {self.config.icon} {self.config.title}")
        st.markdown(f"*{self.config.description}*")
        
        # Show available tools
        tools = context.get("available_tools", [])
        if tools:
            self._show_tool_interface(tools)
        
        # Execute workflow
        return self.config.workflow_function()
    
    def _show_technique_header(self, context: Dict[str, Any]):
        """Show technique header with progress if applicable"""
        st.markdown(f"## {self.config.icon} {self.config.title}")
        
        # Show progress if pipeline-based
        if context.get("has_pipeline", False):
            progress = context.get("progress", {})
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                progress_pct = progress.get("percentage", 0) / 100
                st.progress(progress_pct)
                completed = progress.get("completed", 0)
                total = progress.get("total", 1)
                st.caption(f"Progress: {completed}/{total} steps completed")
            
            with col2:
                current_step = context.get("current_step", {})
                if current_step:
                    st.metric("Current Step", current_step.get("title", "Unknown"))
            
            with col3:
                if st.button("🔄 Reset", help=f"Reset {self.config.name} pipeline"):
                    self._reset_technique()
    
    def _show_automated_section(self, context: Dict[str, Any]):
        """Show automated execution section"""
        st.markdown("### 🚀 Quick Start")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if st.button(
                "🚀 Run All Steps", 
                key=f"run_all_{self.server_name}", 
                help=f"Execute the entire {self.config.name} pipeline automatically"
            ):
                with st.spinner(f"Running {self.config.name} pipeline..."):
                    success = self._run_automated_pipeline()
                    if success:
                        st.success("🎉 Pipeline executed successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Pipeline execution failed. Try step-by-step.")
        
        with col2:
            st.info(f"💡 Click 'Run All Steps' to execute the entire {self.config.name} pipeline automatically.")
    
    def _show_step_by_step_section(self, context: Dict[str, Any]):
        """Show step-by-step interface"""
        st.markdown("### 📋 Step-by-Step Analysis")
        
        steps = context.get("pipeline_steps", [])
        if steps:
            self._show_step_navigation(steps, context)
    
    def _show_step_navigation(self, steps: List[Dict], context: Dict[str, Any]):
        """Show step navigation interface"""
        current_step_key = context.get("current_step", {}).get("key", "")
        
        # Create step options
        step_options = []
        step_keys = []
        
        for step in steps:
            status_icon = "✅" if step.get("completed", False) else "⏳"
            current_icon = "👉" if step["key"] == current_step_key else ""
            
            step_label = f"{status_icon} {current_icon} {step['title']}"
            step_options.append(step_label)
            step_keys.append(step["key"])
        
        # Step selector
        col1, col2 = st.columns([3, 1])
        
        with col1:
            selected_index = step_keys.index(current_step_key) if current_step_key in step_keys else 0
            selected_step = st.selectbox(
                "Navigate to step:",
                options=range(len(step_options)),
                format_func=lambda x: step_options[x],
                index=selected_index,
                key=f"step_navigator_{self.server_name}"
            )
            
            if step_keys[selected_step] != current_step_key:
                self._navigate_to_step(step_keys[selected_step])
        
        with col2:
            # Show step description
            current_step = next((s for s in steps if s["key"] == current_step_key), None)
            if current_step:
                st.caption(f"📝 {current_step.get('description', '')}")
    
    def _show_tool_interface(self, tools: List[Dict]):
        """Show available tools for simple techniques"""
        st.markdown("### 🛠️ Available Tools")
        
        for tool in tools:
            with st.expander(f"🔧 {tool.get('name', 'Unknown Tool')}"):
                st.markdown(tool.get('description', 'No description available'))
                
                if st.button(f"Run {tool.get('name', 'Tool')}", key=f"tool_{tool.get('name', 'unknown')}"):
                    self._execute_tool(tool.get('name'))
    
    def _run_automated_pipeline(self) -> bool:
        """Run automated pipeline through MCP"""
        try:
            result = mcp_registry.execute_tool(f"run_automated_{self.server_name}")
            return result.get("success", False)
        except Exception as e:
            st.error(f"Automated pipeline failed: {e}")
            return False
    
    def _navigate_to_step(self, step_key: str):
        """Navigate to a specific step"""
        try:
            mcp_registry.execute_tool(f"navigate_to_step", step_key=step_key, server=self.server_name)
            st.rerun()
        except Exception as e:
            st.error(f"Navigation failed: {e}")
    
    def _reset_technique(self):
        """Reset the technique pipeline"""
        try:
            mcp_registry.execute_tool(f"reset_{self.server_name}_pipeline")
            st.success(f"🔄 {self.config.name} pipeline reset!")
            st.rerun()
        except Exception as e:
            st.error(f"Reset failed: {e}")
    
    def _execute_tool(self, tool_name: str):
        """Execute a specific tool"""
        try:
            result = mcp_registry.execute_tool(tool_name, server=self.server_name)
            if result.get("success"):
                st.success(f"✅ {tool_name} executed successfully!")
            else:
                st.error(f"❌ {tool_name} failed: {result.get('message', 'Unknown error')}")
        except Exception as e:
            st.error(f"Tool execution failed: {e}")


# Technique Registry - Configuration-driven approach
class TechniqueRegistry:
    """Registry for all analysis techniques"""
    
    def __init__(self):
        self.techniques: Dict[str, TechniqueConfig] = {}
        self._register_default_techniques()
    
    def _register_default_techniques(self):
        """Register default techniques"""
        
        # scRNA-seq
        self.register_technique(
            name="scrnaseq",
            title="scRNA-seq Analysis Pipeline",
            description="Single-cell RNA sequencing analysis",
            icon="🧬",
            server_name="scrnaseq",
            upload_message="Please upload your `.h5ad` or 10x files to begin.",
            data_check_function=lambda: st.session_state.get("anndata") is not None,
            workflow_function=self._get_scrnaseq_workflow()
        )
        
        # RNA-seq
        self.register_technique(
            name="rnaseq",
            title="RNA-seq Analysis Pipeline", 
            description="Bulk RNA sequencing analysis",
            icon="🧬",
            server_name="rnaseq",
            upload_message="Please upload both RNA-seq counts and metadata files to begin analysis.",
            data_check_function=lambda: (
                "rnaseq_counts_df" in st.session_state and 
                "rnaseq_metadata_df" in st.session_state
            ),
            workflow_function=self._get_rnaseq_workflow()
        )
    
    def register_technique(self, **kwargs):
        """Register a new technique"""
        config = TechniqueConfig(**kwargs)
        self.techniques[config.name] = config
    
    def get_technique(self, name: str) -> Optional[TechniqueConfig]:
        """Get technique configuration"""
        return self.techniques.get(name)
    
    def get_technique_ui(self, name: str) -> Optional[GenericTechniqueUI]:
        """Get UI component for a technique"""
        config = self.get_technique(name)
        if config:
            return GenericTechniqueUI(config)
        return None
    
    def _get_scrnaseq_workflow(self):
        """Get scRNA-seq workflow function"""
        from src.modules.scrna_seq.workflow import run_scrnaseq_pipeline
        return run_scrnaseq_pipeline
    
    def _get_rnaseq_workflow(self):
        """Get RNA-seq workflow function"""
        from src.modules.rna_seq.workflow import run_rnaseq_pipeline
        return run_rnaseq_pipeline


# Global technique registry
technique_registry = TechniqueRegistry()
 