"""
Utility functions for the agent system.
"""

import streamlit as st

def set_analysis_mode(mode):
    """Set the analysis mode in the Streamlit interface"""
    result = {"success": False, "message": ""}
    
    try:
        # Map mode names to their agent flag names
        mode_map = {
            "rnaseq": "agent_requested_rnaseq",
            "scrnaseq": "agent_requested_scrnaseq",
            "image": "agent_requested_image",
            "tabular": "agent_requested_tabular",
            "reader": "agent_requested_reader",
            "search": "agent_requested_search"
        }
        
        if mode in mode_map:
            # First, reset all agent request flags
            for flag in mode_map.values():
                st.session_state[flag] = False
                
            # Then set the requested mode flag
            st.session_state[mode_map[mode]] = True
                
            result["success"] = True
            result["message"] = f"Analysis mode set to {mode}"
        else:
            result["message"] = f"Unknown analysis mode: {mode}"
            
        return result
        
    except Exception as e:
        result["message"] = f"Error setting analysis mode: {str(e)}"
        return result 