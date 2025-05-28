# Extending the Agent System

This guide explains how to add new analysis techniques to the agent system.

## Adding a New Analysis Type

To add a new analysis type (e.g., proteomics, spatial transcriptomics), follow these steps:

### 1. Create a Tools Module

Create a new Python module in `src/modules/agent/` with tools for your analysis type:

```python
# src/modules/agent/proteomics_tools.py
"""
Proteomics-specific tools for the agent system.
"""

import streamlit as st
from modules.agent.registry import registry

def upload_proteomics_file_tool(file_format="mzML"):
    """Tool implementation for uploading proteomics files"""
    # Implementation...
    return {"success": True, "message": "..."}

def run_proteomics_analysis_tool(params):
    """Tool implementation for proteomics analysis"""
    # Implementation...
    return {"success": True, "message": "..."}

# Register tools with the registry
def register_proteomics_tools():
    registry.register_tool(
        name="upload_proteomics_file",
        description="Upload proteomics data file",
        parameters={
            "file_format": {
                "type": "string",
                "enum": ["mzML", "raw", "mzXML"],
                "description": "File format to upload"
            }
        },
        executor=upload_proteomics_file_tool,
        analysis_type="proteomics"
    )
    
    # Register more tools...
```

### 2. Update Session State

Add relevant session state variables in `src/modules/utils/session.py`:

```python
# In initialize_session_state function
defaults = {
    # Existing defaults...
    
    # Add new analysis type flags
    "agent_requested_proteomics": False,
    "show_proteomics_uploader": False,
    "proteomics_data": None
}
```

### 3. Update App Entry Point

Register your tools in `src/app.py`:

```python
# Add import
from modules.agent.proteomics_tools import register_proteomics_tools

# After initialize_session_state()
register_proteomics_tools()
```

### 4. Update User Interface

Update the interface components in `src/interface/center.py` and `src/interface/left.py`:

```python
# In center.py
if st.session_state.get("agent_requested_proteomics", False):
    # Display proteomics analysis UI
    run_proteomics_workflow()

# In left.py
if st.session_state.get("agent_requested_proteomics", False):
    # Display proteomics file upload UI
    st.sidebar.markdown("### Proteomics File Upload")
    # ...
```

### 5. Update Agent Context

Enhance the agent's file status context in `src/modules/agent/core.py`:

```python
# In get_file_status_context method
# Add proteomics data check
if "proteomics_data" in st.session_state and st.session_state.get("proteomics_data") is not None:
    context += "- Proteomics data is uploaded\n"
    # Add details about the data
else:
    context += "- Proteomics data is NOT uploaded\n"
```

## Tool Registry API

The tool registry provides the following methods:

- `registry.register_tool(name, description, parameters, executor, analysis_type, required_params=None)`: Register a new tool
- `registry.get_tool_definitions()`: Get all tool definitions for the OpenAI API
- `registry.execute_tool(tool_name, **kwargs)`: Execute a registered tool

## Best Practices

1. **Modular Design**: Keep each analysis type in its own module
2. **Consistent Naming**: Use consistent naming for flags: `agent_requested_X`, `show_X_uploader`
3. **Clear Descriptions**: Write clear tool descriptions for the AI to understand when to use them
4. **Error Handling**: Include proper error handling in all tool implementations
5. **Session State**: Store data in session state for persistence across reruns
6. **UI Integration**: Ensure the UI reflects the current state of analysis

## Example Workflow

1. User types: "Analyze my proteomics data"
2. Agent calls `set_analysis_mode` with mode="proteomics"
3. This sets `agent_requested_proteomics=True`
4. UI shows proteomics upload interface
5. User uploads data
6. Agent can now call proteomics analysis tools

By following this pattern, the system remains extensible and can grow to include any number of analysis techniques. 