import streamlit as st
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Streamlit page
st.set_page_config(
    page_title="Bioinformatics Analysis Platform",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import interface components
from src.interface.welcome import display_welcome_page
from src.interface.left import display_left_panel
from src.interface.center import display_center_panel
from src.interface.right import display_right_panel

def main():
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Create three-column layout
    left_col, center_col, right_col = st.columns([1, 2, 1])
    
    # Display panels
    with left_col:
        display_left_panel()
    
    with center_col:
        # Show welcome page if no analysis is active
        if not st.session_state.get("analysis_active", False):
            display_welcome_page()
        else:
            display_center_panel()
    
    with right_col:
        display_right_panel()

if __name__ == "__main__":
    main()
