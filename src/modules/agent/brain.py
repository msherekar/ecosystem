# Code for the brain of the agent

import json
import os
from modules.agent.core import Agent
from modules.agent.registry import registry

# Initialize Agent with OpenRouter API key
# use .env file to store the API key
agent = Agent(api_key=os.getenv("OPENROUTER_API_KEY"))  # Replace or inject securely

def ask_agent(prompt: str, conversation_history=None):
    """
    Send a prompt to the agent and process tool calls if needed.
    """
    response_data = agent.process_command(prompt, conversation_history)
    return response_data

def get_available_tools(analysis_type=None):
    """
    Get a list of tools compatible with OpenAI Function Calling.
    """
    return registry.get_tool_definitions()

def get_tool_executor(tool_name):
    """
    Retrieve the executor function for a tool.
    """
    return registry.get_executor(tool_name)

def execute_tool(tool_name, arguments):
    """
    Execute a registered tool by name and arguments.
    """
    return registry.execute_tool(tool_name, **arguments)

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

# ✅ Plug this into agent_brain.py execution flow

def execute_tool(tool_name, arguments):
    result = registry.execute_tool(tool_name, **arguments)

    # Choose ONE logger
    #log_tool_call_console(tool_name, arguments, result)  # Option 1
    log_tool_call_file(tool_name, arguments, result)   # Option 2
    # log_tool_call_db(tool_name, arguments, result)     # Option 3

    return result
