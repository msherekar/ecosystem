import streamlit as st
import asyncio
from src.interface.layout import (layout_columns, layout_sidebar_header, layout_sidebar_spacer)
from src.interface.left import sidebar_controls
from src.interface.center import render_center_panel
from src.interface.right import chat_interface
from src.modules.utils.session import initialize_session_state
from src.mcp.core.registry import get_mcp_registry

# ✅ 1. Set page config
st.set_page_config(page_title="Lab Assistant Chatbot", layout="wide")

# ✅ 2. Initialize session state
initialize_session_state()

# ✅ 3. Initialize MCP Registry
@st.cache_resource
def initialize_mcp():
    """Initialize MCP registry and connect to servers"""
    async def _init():
        registry = await get_mcp_registry()
        await registry.initialize()
        return registry
    
    # Run async initialization
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        registry = loop.run_until_complete(_init())
        # st.success("🔗 MCP servers connected successfully")  # Removed for cleaner UI
        return registry
    except Exception as e:
        st.error(f"❌ Failed to initialize MCP: {str(e)}")
        return None
    finally:
        loop.close()

# Initialize MCP
mcp_registry = initialize_mcp()

# ✅ 4. Setup layout
data_col, chat_col = layout_columns()

# ✅ 5. Sidebar setup
layout_sidebar_header()
layout_sidebar_spacer(1)
sidebar_controls()

# ✅ 6. Render center and right panels
render_center_panel(data_col)
chat_interface(chat_col)
