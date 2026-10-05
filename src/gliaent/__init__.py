"""Gliaent core.

A pure analysis core: no Streamlit, no FastAPI, no Electron. Every function
here takes explicit inputs and returns explicit outputs, so the same code is
callable from the Streamlit app, the FastAPI server, a notebook, a test, or an
MCP tool.

Nothing in this package may import `streamlit`. `tests/test_core_purity.py`
enforces that.
"""

__all__ = ["analysis", "io", "protein", "provenance"]
