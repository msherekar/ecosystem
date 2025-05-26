import streamlit as st
from interface.layout import (layout_columns, layout_sidebar_header, layout_sidebar_spacer)
from interface.left import sidebar_controls
from interface.center import render_center_panel
from interface.right import chat_interface
from modules.utils.session import initialize_session_state
from modules.agent.scrnaseq_tools import register_scrnaseq_tools
from modules.agent.rnaseq_tools import register_rnaseq_tools

# ✅ 1. Set page config
st.set_page_config(page_title="Lab Assistant Chatbot", layout="wide")

# ✅ 2. Initialize session state
initialize_session_state()

# ✅ 3. Register all agent tools before rendering interface
register_rnaseq_tools()    # RNA-seq tools
register_scrnaseq_tools()  # scRNA-seq tools

# ✅ 4. Setup layout
data_col, chat_col = layout_columns()

# ✅ 5. Sidebar setup
layout_sidebar_header()
layout_sidebar_spacer(1)
sidebar_controls()

# ✅ 6. Render center and right panels
render_center_panel(data_col)
chat_interface(chat_col)
