#!/usr/bin/env python3
"""
MCP FastAPI Server Launcher
"""
import os
import sys
import uvicorn
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def main():
    """Run the FastAPI server"""
    # Set environment variables if needed
    os.environ.setdefault("PYTHONPATH", str(Path(__file__).parent / "src"))
    
    # Run the server
    uvicorn.run(
        "mcp.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main() 