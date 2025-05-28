"""
scRNA-seq Step Manager
Handles step-by-step workflow execution and navigation.
"""

import streamlit as st
from src.modules.scrna_seq.pipeline_config import SCRNA_STEP_ORDER, get_step_by_key, get_next_step


class StepManager:
    """Manages step-by-step execution of the scRNA-seq pipeline."""
    
    def __init__(self):
        if "scrna_current_step" not in st.session_state:
            st.session_state.scrna_current_step = "input_summary"
    
    def run_current_step(self):
        """Execute the current step in the pipeline."""
        current_step_key = st.session_state.scrna_current_step
        current_step = get_step_by_key(current_step_key)
        
        if not current_step:
            st.error(f"❌ Unknown step: {current_step_key}")
            return
        
        # Execute the step function
        current_step["function"]()
        
        # Check if step is completed and show navigation
        self._handle_step_completion(current_step)
    
    def _handle_step_completion(self, current_step):
        """Handle step completion and navigation."""
        step_key = current_step["key"]
        done_flag = current_step["done_flag"]
        step_title = current_step["title"]
        
        if st.session_state.get(done_flag):
            # Generate step summary if not already done
            self._generate_step_summary(step_key, step_title)
            
            # Show continue button if there's a next step
            next_step = get_next_step(step_key)
            if next_step:
                if st.button(f"✅ Continue to {next_step['title']}", key=f"continue_step_{step_key}"):
                    st.session_state.scrna_current_step = next_step["key"]
                    st.rerun()
            else:
                st.success("🎉 All steps complete!")
    
    def _generate_step_summary(self, step_key, step_title):
        """Generate and store step summary."""
        # Only generate summary once per step completion
        if st.session_state.get("scrna_last_completed_step") != step_key:
            st.session_state.scrna_last_completed_step = step_key
            
            # Store the summary for later reference
            auto_summary = f"✅ Step {step_key} completed successfully"
            st.session_state.setdefault("scrna_step_summaries", {})[step_key] = auto_summary

            # Find next step for guidance
            next_step = get_next_step(step_key)
            next_step_name = next_step["title"] if next_step else "completion"
            
            # Generate agent message
            summary_text = f"✅ {step_title} completed. Ready for {next_step_name}."
            st.session_state.setdefault("scrna_agent_thoughts", {})[step_key] = summary_text
            st.session_state.messages.append({"role": "assistant", "content": summary_text})
    
    def get_current_step_info(self):
        """Get information about the current step."""
        current_step_key = st.session_state.scrna_current_step
        return get_step_by_key(current_step_key)
    
    def navigate_to_step(self, step_key):
        """Navigate to a specific step."""
        if get_step_by_key(step_key):
            st.session_state.scrna_current_step = step_key
            st.rerun()
        else:
            st.error(f"❌ Invalid step: {step_key}")
    
    def get_pipeline_progress(self):
        """Get overall pipeline progress."""
        completed_steps = 0
        total_steps = len(SCRNA_STEP_ORDER)
        
        for step in SCRNA_STEP_ORDER:
            if st.session_state.get(step["done_flag"], False):
                completed_steps += 1
        
        return {
            "completed": completed_steps,
            "total": total_steps,
            "percentage": int((completed_steps / total_steps) * 100)
        }
    
    def reset_pipeline(self):
        """Reset the entire pipeline."""
        # Clear all step completion flags
        for step in SCRNA_STEP_ORDER:
            st.session_state.pop(step["done_flag"], None)
        
        # Clear other pipeline state
        st.session_state.pop("scrna_last_completed_step", None)
        st.session_state.pop("scrna_step_summaries", None)
        st.session_state.pop("scrna_agent_thoughts", None)
        
        # Reset to first step
        st.session_state.scrna_current_step = "input_summary"
        
        st.success("🔄 Pipeline reset successfully!")
        st.rerun()


def get_step_manager():
    """Get or create a step manager instance."""
    if "step_manager" not in st.session_state:
        st.session_state.step_manager = StepManager()
    return st.session_state.step_manager 