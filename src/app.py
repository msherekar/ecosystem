import streamlit as st
import asyncio
from src.interface.layout import layout_three_areas, layout_flexible_areas
from src.interface.left import render_left_panel
from src.interface.center import render_center_panel  
from src.interface.right import chat_interface
from src.modules.utils.session import initialize_session_state
from src.mcp.core.registry import get_mcp_registry

# ✅ 1. Set page config
st.set_page_config(page_title="Lab Assistant Chatbot", layout="wide")

# ✅ 2. Remove top whitespace and fix alignment
st.markdown("""
<style>
.block-container {
    padding-top: 0rem !important;
    padding-bottom: 0rem !important;
}

.main > div {
    padding-top: 0rem !important;
}

/* Force all columns to align at top */
[data-testid="column"] {
    vertical-align: top !important;
}

[data-testid="column"] > div {
    padding-top: 0rem !important;
}

/* Remove header space */
header[data-testid="stHeader"] {
    height: 0rem !important;
}

.main .block-container {
    max-width: 100% !important;
    padding: 0rem 1rem !important;
}
</style>
""", unsafe_allow_html=True)

# ✅ 3. Initialize session state
initialize_session_state()

# ✅ 4. Initialize MCP Registry
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

# ✅ 5. Create main container at top
main_container = st.container()

with main_container:
    # ✅ 6. Setup flexible layout inside container
    left_area, center_area, right_area = layout_three_areas(
        left_ratio=1, 
        center_ratio=2.5, 
        right_ratio=1, 
        gap="small"
    )

    # ✅ 7. Render all panels with their designated areas
    render_left_panel(left_area)
    render_center_panel(center_area)
    chat_interface(right_area)

