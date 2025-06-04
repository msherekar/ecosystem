import streamlit as st
import pandas as pd
from src.modules.utils.upload import create_project, handle_file_upload, handle_rnaseq_upload, handle_scrnaseq_upload

def render_left_panel(left_area):
    """
    Renders the left panel content (modules, file system, controls) in the provided layout area
    
    Args:
        left_area: Streamlit column/container for the left panel
    """
    with left_area:
        # Add spacing to align with center panel content
        st.markdown("""
        <style>
        /* Push left panel content down */
        div[data-testid="column"]:first-child .element-container:first-child {
            margin-top: 8rem !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Add spacing div to push content down
        st.markdown("<div style='height: 120px;'></div>", unsafe_allow_html=True)
        
        # Panel header
        # Panel content starts here - below the center heading level
        
        # --- Module Navigation Buttons ---
        for label, key in [
            ("📊 Tabular Analysis", "tabular_analysis"),
            ("🖼️ Image Analysis", "image_analysis"), 
            ("🧬 RNAseq Analysis", "rnaseq_analysis"),
            ("🔬 scRNAseq Analysis", "scRNAseq_analysis"),
            ("📚 Reader", "reader"),
            ("🔍 Search", "search"),
        ]:
            if st.button(label, use_container_width=True, key=f"{key}_btn"):
                # Reset all analysis flags first
                st.session_state.tabular_analysis = False
                st.session_state.image_analysis = False
                st.session_state.rnaseq_analysis = False
                st.session_state.scRNAseq_analysis = False
                st.session_state.reader = False
                st.session_state.search = False
                
                # Set the active tab and corresponding analysis flag
                st.session_state.active_tab = key
                st.session_state[key] = True

       

        # --- Project & File Management ---
        
        
        if st.button("📁 Create Project", use_container_width=True):
            st.session_state.create_project = True
        create_project()

        # File upload with new system
        handle_file_upload()

        

        # --- Utility Buttons ---
        
        
        if st.button("🗑️ Clear Uploaded Files", use_container_width=True):
            st.session_state.original_df = {}
            st.session_state.modified_df = {}
            st.session_state.uploaded_pdf = None

        if st.button("💬 Clear Chat History", use_container_width=True):
            st.session_state.messages = []

       

        # --- Context-Specific Uploads ---
        # RNAseq Upload - appears when RNAseq analysis is active
        if st.session_state.get("active_tab") == "rnaseq_analysis":
            st.markdown("**🧬 RNAseq Data:**")
            handle_rnaseq_upload()

        # scRNAseq Upload - appears when scRNAseq analysis is active  
        if st.session_state.get("active_tab") == "scRNAseq_analysis":
            st.markdown("**🔬 scRNAseq Data:**")
            handle_scrnaseq_upload()

        # # --- Status Section ---
        # with st.expander("📊 Current Status", expanded=False):
        #     active_analysis = st.session_state.get("active_tab", "None")
        #     st.write(f"**Active Analysis:** {active_analysis}")
            
        #     # Show uploaded files count
        #     file_count = len(st.session_state.get("original_df", {}))
        #     st.write(f"**Uploaded Files:** {file_count}")
            
        #     # Show chat message count
        #     chat_count = len(st.session_state.get("messages", []))
        #     st.write(f"**Chat Messages:** {chat_count}")

# Legacy function for backward compatibility
def sidebar_controls():
    """
    Legacy function that uses sidebar - kept for backward compatibility
    """
    with st.sidebar:
        st.markdown("### 🔧 Modules")
        for label, key in [
            ("Tabular Analysis", "tabular_analysis"),
            ("Image Analysis", "image_analysis"),
            ("RNAseq Analysis", "rnaseq_analysis"),
            ("scRNAseq Analysis", "scRNAseq_analysis"),
            ("Reader", "reader"),
            ("Search", "search"),
        ]:
            if st.button(label, use_container_width=True, key=f"{key}_sidebar_btn"):
                # Reset all analysis flags first
                st.session_state.tabular_analysis = False
                st.session_state.image_analysis = False
                st.session_state.rnaseq_analysis = False
                st.session_state.scRNAseq_analysis = False
                st.session_state.reader = False
                st.session_state.search = False
                
                # Set the active tab and corresponding analysis flag
                st.session_state.active_tab = key
                st.session_state[key] = True

        st.divider()

        if st.button("Create Project", use_container_width=True):
            st.session_state.create_project = True
        create_project()

        handle_file_upload()

        if st.button("Clear Uploaded Files", use_container_width=True):
            st.session_state.original_df = {}
            st.session_state.modified_df = {}
            st.session_state.uploaded_pdf = None

        if st.button("Clear Chat History", use_container_width=True):
            st.session_state.messages = []

        if st.session_state.get("active_tab") == "rnaseq_analysis":
            handle_rnaseq_upload()

        if st.session_state.get("active_tab") == "scRNAseq_analysis":
            handle_scrnaseq_upload()


