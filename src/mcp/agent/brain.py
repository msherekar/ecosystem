# Code for the brain of the agent

import json
import os

from src.mcp.agent.core import Agent
from src.mcp.agent.intelligent_router import IntelligentToolRouter
from src.mcp.core.registry import get_mcp_registry

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, continue without it
    pass

# Enhanced agent with intelligent routing - PATENT-WORTHY
async def enhanced_ask_agent(prompt: str, conversation_history=None, session_state=None):
    """
    Enhanced agent processing with intelligent tool routing.
    Solves the 128-tool limit problem using context-aware tool selection.
    """
    router = IntelligentToolRouter()
    
    # Analyze what tools are actually needed (use empty dict if no session state)
    session_data = session_state if session_state is not None else {}
    context = await router.analyze_biological_context(prompt, session_data)
    tool_set = await router.dynamic_tool_selection(context)
    
    # Get MCP registry and update with selected tools
    mcp_registry = await get_mcp_registry()
    
    # Process with reduced tool set via agent
    agent = get_agent()
    agent.set_available_tools(tool_set.tools)
    
    return agent.process_command(prompt, conversation_history)

# Initialize Agent lazily to avoid requiring API key at import time
_agent = None

def get_agent():
    """Get or create the agent instance"""
    global _agent
    if _agent is None:
        # Check for both OPENROUTER_API_KEY and OPENAI_API_KEY
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if api_key:
            _agent = Agent(api_key=api_key)
        else:
            # Return a mock agent or raise an error
            raise ValueError("OPENROUTER_API_KEY or OPENAI_API_KEY environment variable not set")
    return _agent

async def ask_agent(prompt: str, conversation_history=None):
    """
    Send a prompt to the agent and process tool calls if needed.
    Uses intelligent routing to stay within 128-tool limit.
    """
    # Use enhanced routing by default
    return await enhanced_ask_agent(prompt, conversation_history)

async def get_available_tools(analysis_type=None):
    """
    Get a list of tools compatible with OpenAI Function Calling from MCP registry.
    """
    mcp_registry = await get_mcp_registry()
    return mcp_registry.get_tool_definitions_for_agent()

async def execute_tool(tool_name, arguments):
    """
    Execute a tool via MCP registry.
    """
    mcp_registry = await get_mcp_registry()
    return await mcp_registry.execute_tool(tool_name, arguments)

# ✅ Option 1: Simple Print-Based Logging

def log_tool_call_console(tool_name, args, result):
    print(f"[TOOL CALL] Tool: {tool_name}")
    print(f"Arguments: {json.dumps(args, indent=2)}")
    print(f"Result: {result}\n")

# ✅ Option 2: Log to File

def log_tool_call_file(tool_name, args, result, log_path="logs/agent.log"):
    import os
    from datetime import datetime
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a") as f:
        f.write("\n--- TOOL CALL ---\n")
        f.write(f"Time: {datetime.now()}\n")
        f.write(f"Tool: {tool_name}\n")
        f.write(f"Args: {json.dumps(args)}\n")
        f.write(f"Result: {json.dumps(result)}\n")

# ✅ Option 3: SQLite Logging (for user feedback, memory, etc.)

def log_tool_call_db(tool_name, args, result, db_path="logs/agent.sqlite"):
    import sqlite3
    import os
    from datetime import datetime
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tool_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            tool_name TEXT,
            arguments TEXT,
            result TEXT
        )
    """)
    cursor.execute("""
        INSERT INTO tool_calls (timestamp, tool_name, arguments, result)
        VALUES (?, ?, ?, ?)
    """, (datetime.now().isoformat(), tool_name, json.dumps(args), json.dumps(result)))
    conn.commit()
    conn.close()

# ✅ Enhanced tool execution with logging and learning

async def execute_tool_with_learning(tool_name, arguments, context=None):
    """Execute tool with logging and learning for intelligent router"""
    import time
    start_time = time.time()
    
    try:
        result = await execute_tool(tool_name, arguments)
        execution_time = time.time() - start_time
        success = result.get("success", True)
        
        # Log the execution
        log_tool_call_file(tool_name, arguments, result)
        
        # Learn from usage for intelligent router
        if context:
            router = IntelligentToolRouter()
            await router.learn_from_usage(tool_name, context, success, execution_time)
        
        return result
        
    except Exception as e:
        execution_time = time.time() - start_time
        error_result = {"success": False, "error": str(e)}
        
        # Log the error
        log_tool_call_file(tool_name, arguments, error_result)
        
        # Learn from failure
        if context:
            router = IntelligentToolRouter()
            await router.learn_from_usage(tool_name, context, False, execution_time)
        
        raise e
