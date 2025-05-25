import streamlit as st
<<<<<<< HEAD
from interface.layout import (layout_columns,layout_sidebar_header,layout_sidebar_spacer)
=======
from interface.layout import (
    layout_columns,
    layout_sidebar_header,layout_sidebar_spacer
)
>>>>>>> origin/feature/pdf-viewer
from interface.left import sidebar_controls
from interface.center import render_center_panel
from interface.right import chat_interface
from modules.utils.session import initialize_session_state

<<<<<<< HEAD
=======

>>>>>>> origin/feature/pdf-viewer
# ✅ 1. Set page config
st.set_page_config(page_title="Lab Assistant Chatbot", layout="wide")

# ✅ 2. Initialize session state
initialize_session_state()

# ✅ 3. Setup layout
data_col, chat_col = layout_columns()

# ✅ 4. Sidebar setup
<<<<<<< HEAD
=======


>>>>>>> origin/feature/pdf-viewer
layout_sidebar_header()
layout_sidebar_spacer(1)
sidebar_controls()

<<<<<<< HEAD
=======

>>>>>>> origin/feature/pdf-viewer
# ✅ 5. Render center and right panels
render_center_panel(data_col)
chat_interface(chat_col)
