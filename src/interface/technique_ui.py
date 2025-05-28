"""
Generic Technique UI Components
Scalable UI system that can handle thousands of analysis techniques
using configuration-driven approach.
"""

import streamlit as st
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from src.modules.scrna_seq.workflow import run_automated_pipeline


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
        
        # Get technique context (fallback for now)
        context = self._get_technique_context()
        
        # Render technique-specific UI
        if context.get("has_pipeline", True):  # Default to pipeline interface
            return self._render_pipeline_interface(context)
        else:
            return self._render_simple_interface(context)
    
    def _get_technique_context(self) -> Dict[str, Any]:
        """Get context for the technique (fallback implementation)"""
        # For now, provide a fallback context based on technique type
        if self.config.name == "scrnaseq":
            return self._get_scrnaseq_context()
        elif self.config.name == "rnaseq":
            return self._get_rnaseq_context()
        else:
            return {
                "has_pipeline": False,
                "supports_automation": False,
                "available_tools": []
            }
    
    def _get_scrnaseq_context(self) -> Dict[str, Any]:
        """Get scRNA-seq specific context"""
        # Check pipeline progress from session state
        steps = [
            {"key": "qc", "title": "Quality Control", "completed": st.session_state.get("qc_done", False)},
            {"key": "filtering", "title": "Cell/Gene Filtering", "completed": st.session_state.get("filtered", False)},
            {"key": "normalization", "title": "Normalization", "completed": st.session_state.get("normalized", False)},
            {"key": "dimred", "title": "PCA", "completed": st.session_state.get("dimred_done", False)},
            {"key": "clustering", "title": "Clustering", "completed": st.session_state.get("clustered", False)},
            {"key": "umap", "title": "UMAP", "completed": st.session_state.get("umap_done", False)},
            {"key": "dea", "title": "Differential Expression", "completed": st.session_state.get("dea_done", False)},
            {"key": "enrichment", "title": "Enrichment Analysis", "completed": st.session_state.get("enrichment_done", False)}
        ]
        
        completed_steps = sum(1 for step in steps if step["completed"])
        
        # Determine current step: use manual navigation if set, otherwise use completion-based logic
        manual_step = st.session_state.get("scrna_current_step")
        if manual_step:
            current_step = next((step for step in steps if step["key"] == manual_step), steps[0])
        else:
            current_step = next((step for step in steps if not step["completed"]), steps[-1])
        
        return {
            "has_pipeline": True,
            "supports_automation": True,
            "pipeline_steps": steps,
            "current_step": current_step,
            "progress": {
                "completed": completed_steps,
                "total": len(steps),
                "percentage": (completed_steps / len(steps)) * 100
            }
        }
    
    def _get_rnaseq_context(self) -> Dict[str, Any]:
        """Get RNA-seq specific context"""
        # Check pipeline progress from session state
        steps = [
            {"key": "deseq2", "title": "Differential Expression", "completed": st.session_state.get("deseq_results") is not None},
            {"key": "go_enrichment", "title": "GO Enrichment", "completed": st.session_state.get("go_results") is not None},
            {"key": "visualization", "title": "Visualization", "completed": st.session_state.get("plots_generated", False)}
        ]
        
        completed_steps = sum(1 for step in steps if step["completed"])
        current_step = next((step for step in steps if not step["completed"]), steps[-1])
        
        return {
            "has_pipeline": True,
            "supports_automation": True,
            "pipeline_steps": steps,
            "current_step": current_step,
            "progress": {
                "completed": completed_steps,
                "total": len(steps),
                "percentage": (completed_steps / len(steps)) * 100
            }
        }
    
    def _render_pipeline_interface(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Render pipeline-based interface (like scRNA-seq)"""
        
        # Show clean title and progress at top
        self._show_technique_header(context)
        
        # Show run all button and step selector at top
        self._show_top_controls(context)
        
        # Show current step content
        self._show_step_by_step_section(context)
        
        # Return success status without calling old workflow
        return {
            "success": True,
            "message": f"{self.config.name} pipeline interface rendered",
            "summary": f"Using scalable technique UI for {self.config.name}",
            "show_upload_message": False
        }
    
    def _render_simple_interface(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Render simple interface for non-pipeline techniques"""
        
        # Show technique header
        st.markdown(f"## {self.config.icon} {self.config.title}")
        st.markdown(f"*{self.config.description}*")
        
        # Show available tools
        tools = context.get("available_tools", [])
        if tools:
            self._show_tool_interface(tools)
        
        # Return success status without calling old workflow
        return {
            "success": True,
            "message": f"{self.config.name} interface rendered",
            "summary": f"Using scalable technique UI for {self.config.name}",
            "show_upload_message": False
        }
    
    def _show_technique_header(self, context: Dict[str, Any]):
        """Show clean technique header at the top"""
        st.markdown(f"## {self.config.icon} {self.config.title}")
        
        # Show simple progress bar without clutter
        if context.get("has_pipeline", False):
            progress = context.get("progress", {})
            progress_pct = progress.get("percentage", 0) / 100
            st.progress(progress_pct)
            completed = progress.get("completed", 0)
            total = progress.get("total", 1)
            st.caption(f"Progress: {completed}/{total} steps completed")
    
    def _show_top_controls(self, context: Dict[str, Any]):
        """Show run all button and step selector at the top"""
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Run All Steps button
            if st.button("Run All Steps", key=f"run_all_{self.server_name}"):
                # Clear previous outputs
                st.empty()
                with st.spinner(f"Running {self.config.name} pipeline..."):
                    success = self._run_automated_pipeline()
                    if success:
                        st.success("Pipeline executed successfully!")
                        st.rerun()
                    else:
                        st.error("Pipeline execution failed. Try step-by-step.")
        
        with col2:
            # Step selector dropdown
            steps = context.get("pipeline_steps", [])
            if steps:
                current_step = context.get("current_step", {})
                current_step_key = current_step.get("key", "")
                current_index = next((i for i, step in enumerate(steps) if step["key"] == current_step_key), 0)
                
                step_options = [f"{i+1}. {step['title']}" for i, step in enumerate(steps)]
                selected_index = st.selectbox(
                    "Jump to step:",
                    options=range(len(step_options)),
                    format_func=lambda x: step_options[x],
                    index=current_index,
                    key=f"step_jump_{self.server_name}"
                )
                
                if selected_index != current_index:
                    self._navigate_to_step(steps[selected_index]["key"])
        
        st.markdown("---")
    
    def _show_automated_section(self, context: Dict[str, Any]):
        """This method is no longer used - controls moved to _show_top_controls"""
        pass
    
    def _show_step_by_step_section(self, context: Dict[str, Any]):
        """Show step content and navigation"""
        steps = context.get("pipeline_steps", [])
        if steps:
            current_step = context.get("current_step", {})
            if current_step:
                # Show current step content
                self._execute_current_step(current_step)
                
                # Show navigation at bottom
                st.markdown("---")
                self._show_bottom_navigation(steps, current_step)
    
    def _show_bottom_navigation(self, steps: List[Dict], current_step: Dict[str, Any]):
        """Show centered navigation buttons at the bottom"""
        current_step_key = current_step.get("key", "")
        current_index = next((i for i, step in enumerate(steps) if step["key"] == current_step_key), 0)
        
        # Center the navigation buttons
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
        
        with col2:
            # Go Back button (only show if not first step)
            if current_index > 0:
                if st.button("⬅️ Go Back", key=f"go_back_{self.server_name}"):
                    prev_step = steps[current_index - 1]
                    self._navigate_to_step(prev_step["key"])
        
        with col3:
            # Next Step button (only show if not last step)
            if current_index < len(steps) - 1:
                if st.button("➡️ Next Step", key=f"next_step_{self.server_name}"):
                    next_step = steps[current_index + 1]
                    self._navigate_to_step(next_step["key"])
        
        with col4:
            # Reset button
            if st.button("🔄 Reset Pipeline", key=f"reset_{self.server_name}"):
                self._reset_technique()
    
    def _show_tool_interface(self, tools: List[Dict]):
        """Show available tools for simple techniques"""
        st.markdown("### 🛠️ Available Tools")
        
        for tool in tools:
            with st.expander(f"🔧 {tool.get('name', 'Unknown Tool')}"):
                st.markdown(tool.get('description', 'No description available'))
                
                if st.button(f"Run {tool.get('name', 'Tool')}", key=f"tool_{tool.get('name', 'unknown')}"):
                    self._execute_tool(tool.get('name'))
    
    def _run_automated_pipeline(self) -> bool:
        """Run automated pipeline"""
        try:
            if self.config.name == "scrnaseq":
                return self._run_scrnaseq_automated()
            elif self.config.name == "rnaseq":
                return self._run_rnaseq_automated()
            else:
                st.error("Automated pipeline not implemented for this technique")
                return False
        except Exception as e:
            st.error(f"Automated pipeline failed: {e}")
            return False
    
    def _run_scrnaseq_automated(self) -> bool:
        """Run automated scRNA-seq pipeline"""
        try:
            # Set the automated flag
            st.session_state.run_automated_pipeline = True
            
            # Run the automated pipeline - it returns a boolean directly
            result = run_automated_pipeline()
            
            return result  # result is already a boolean
        except Exception as e:
            st.error(f"scRNA-seq automated pipeline failed: {e}")
            return False
    
    def _run_rnaseq_automated(self) -> bool:
        """Run automated RNA-seq pipeline"""
        try:
            # For RNA-seq, run DESeq2 and GO enrichment automatically
            from src.modules.rna_seq.deseq2 import run_deseq2_analysis
            from src.modules.rna_seq.go_enrichment import run_go_enrichment
            
            # Run DESeq2
            if not st.session_state.get("deseq_results"):
                deseq_result = run_deseq2_analysis()
                if not deseq_result.get("success"):
                    return False
            
            # Run GO enrichment
            if not st.session_state.get("go_results"):
                go_result = run_go_enrichment()
                if not go_result.get("success"):
                    return False
            
            return True
        except Exception as e:
            st.error(f"RNA-seq automated pipeline failed: {e}")
            return False
    
    def _navigate_to_step(self, step_key: str):
        """Navigate to a specific step"""
        try:
            # Set the current step in session state (use correct key)
            st.session_state.scrna_current_step = step_key
            st.rerun()
        except Exception as e:
            st.error(f"Navigation failed: {e}")
    
    def _reset_technique(self):
        """Reset the technique pipeline"""
        try:
            if self.config.name == "scrnaseq":
                # Reset scRNA-seq pipeline state
                reset_keys = [
                    "qc_done", "filtered", "normalized", "dimred_done", 
                    "clustered", "umap_done", "dea_done", "enrichment_done",
                    "current_step", "run_automated_pipeline"
                ]
                for key in reset_keys:
                    if key in st.session_state:
                        del st.session_state[key]
                        
            elif self.config.name == "rnaseq":
                # Reset RNA-seq pipeline state
                reset_keys = [
                    "deseq_results", "go_results", "plots_generated",
                    "current_step"
                ]
                for key in reset_keys:
                    if key in st.session_state:
                        del st.session_state[key]
            
            st.success(f"🔄 {self.config.name} pipeline reset!")
            st.rerun()
        except Exception as e:
            st.error(f"Reset failed: {e}")
    
    def _execute_tool(self, tool_name: str):
        """Execute a specific tool"""
        try:
            st.info(f"Executing {tool_name}...")
            # Tool execution would be implemented here
            st.success(f"✅ {tool_name} executed successfully!")
        except Exception as e:
            st.error(f"Tool execution failed: {e}")
    
    def _execute_current_step(self, current_step: Dict[str, Any]):
        """Execute the current step's functionality"""
        step_key = current_step.get("key", "")
        step_title = current_step.get("title", "Unknown Step")
        
        # Show main step title
        st.markdown(f"### {step_title}")
        
        if self.config.name == "scrnaseq":
            self._execute_scrnaseq_step(step_key)
        elif self.config.name == "rnaseq":
            self._execute_rnaseq_step(step_key)
    
    def _execute_scrnaseq_step(self, step_key: str):
        """Execute a specific scRNA-seq step"""
        try:
            if step_key == "qc":
                from src.modules.scrna_seq.qc import do_qc
                do_qc()
            elif step_key == "filtering":
                from src.modules.scrna_seq.filtering import do_filtering
                do_filtering()
            elif step_key == "normalization":
                from src.modules.scrna_seq.normalization import do_normalization
                do_normalization()
            elif step_key == "dimred":
                from src.modules.scrna_seq.reduction import perform_dimensionality_reduction
                perform_dimensionality_reduction()
            elif step_key == "clustering":
                from src.modules.scrna_seq.clustering import perform_clustering
                perform_clustering()
            elif step_key == "umap":
                from src.modules.scrna_seq.visualization import create_visualization
                create_visualization()
            elif step_key == "dea":
                from src.modules.scrna_seq.dea import run_differential_expression
                run_differential_expression()
            elif step_key == "enrichment":
                from src.modules.scrna_seq.enrichment import run_enrichment_analysis
                run_enrichment_analysis()
            else:
                st.info(f"Step '{step_key}' implementation not found.")
        except ImportError as e:
            st.error(f"❌ Step module not found: {e}")
        except Exception as e:
            st.error(f"❌ Step execution failed: {e}")
    
    def _execute_rnaseq_step(self, step_key: str):
        """Execute a specific RNA-seq step"""
        try:
            if step_key == "deseq2":
                from src.modules.rna_seq.deseq2 import run_deseq2_analysis
                run_deseq2_analysis()
            elif step_key == "go_enrichment":
                from src.modules.rna_seq.go_enrichment import run_go_enrichment
                run_go_enrichment()
            elif step_key == "visualization":
                from src.modules.rna_seq.visualization import create_rna_visualizations
                create_rna_visualizations()
            else:
                st.info(f"Step '{step_key}' implementation not found.")
        except ImportError as e:
            st.error(f"❌ Step module not found: {e}")
        except Exception as e:
            st.error(f"❌ Step execution failed: {e}")


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
            workflow_function=lambda: {"success": True, "message": "Handled by technique UI"}
        )
        
        # RNA-seq - RE-ENABLED: Local analysis doesn't use API tokens
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
            workflow_function=lambda: {"success": True, "message": "Handled by technique UI"}
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


# Global technique registry
technique_registry = TechniqueRegistry()
 