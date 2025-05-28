import json
import openai
import streamlit as st
import asyncio
from typing import List, Dict, Any, Optional
from openai import OpenAI
import os
from pathlib import Path
import logging

from .tools import get_tool_registry

logger = logging.getLogger(__name__)

class BioinformaticsAgent:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        self.tool_registry = get_tool_registry()
        self.available_tools = self.tool_registry.get_tool_definitions_for_agent()

    def _get_simple_file_status(self):
        """Get simple file status for context"""
        try:
            # Check for data files
            data_files = []
            if Path("data").exists():
                data_files = list(Path("data").glob("*.h5ad")) + list(Path("data").glob("*.csv"))
            
            # Check for results
            results_files = []
            if Path("results").exists():
                results_files = list(Path("results").glob("**/*.png"))
            
            status = f"Data files: {len(data_files)}, Generated plots: {len(results_files)}"
            return status
        except Exception as e:
            return f"Error getting file status: {e}"

    def process_command(self, command, conversation_history=None):
        if conversation_history is None:
            conversation_history = []

        # Limit conversation history to last 3 messages to reduce costs
        if len(conversation_history) > 6:  # 3 user + 3 assistant messages
            conversation_history = conversation_history[-6:]

        # Get context synchronously to avoid event loop issues
        file_status = self._get_simple_file_status()

        # Shorter, cost-effective system prompt
        system_prompt = f"""You are a bioinformatics assistant for data analysis.

Current Analysis State:
{file_status}

Your role:
1. Interpret analysis results and plots
2. Provide biological insights
3. Suggest next steps
4. Help with bioinformatics workflows

Be concise and focus on actionable insights."""

        # Prepare messages for the API
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add limited conversation history
        for msg in conversation_history:
            messages.append(msg)
        
        # Add current command
        messages.append({"role": "user", "content": command})

        try:
            # Use simple tool registry
            tools = self.available_tools
            
            # Make API call with tools - using cheaper model and lower max_tokens
            if tools:
                response = self.client.chat.completions.create(
                    model="openai/gpt-3.5-turbo",  # Much cheaper than Claude
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=0.1,
                    max_tokens=1000  # Reduced from 4000
                )
            else:
                # No tools available, just chat
                response = self.client.chat.completions.create(
                    model="openai/gpt-3.5-turbo",  # Much cheaper than Claude
                    messages=messages,
                    temperature=0.1,
                    max_tokens=1000  # Reduced from 4000
                )

            # Handle tool calls
            if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
                tool_calls = response.choices[0].message.tool_calls
                tool_results = []
                
                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                        # Execute tool synchronously by running async in event loop
                        result = asyncio.run(self.tool_registry.execute_tool(tool_name, arguments))
                        tool_results.append(f"Tool {tool_name}: {result}")
                    except Exception as e:
                        tool_results.append(f"Tool {tool_name} error: {str(e)}")
                
                # If we have tool results, make another call to get the final response
                if tool_results:
                    messages.append({"role": "assistant", "content": response.choices[0].message.content or ""})
                    messages.append({"role": "user", "content": f"Tool results: {'; '.join(tool_results)}"})
                    
                    final_response = self.client.chat.completions.create(
                        model="openai/gpt-3.5-turbo",
                        messages=messages,
                        temperature=0.1,
                        max_tokens=1000
                    )
                    return final_response.choices[0].message.content
            
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error in process_command: {e}")
            return f"I encountered an error: {str(e)}. Please try again."

    async def chat(self, user_message: str) -> tuple[str, List[str]]:
        """Enhanced chat method using simple tools"""
        try:
            # Get current context
            context = self._get_simple_file_status()
            
            # Get available tools from simple registry
            available_tools = self.available_tools
            
            messages = [
                {
                    "role": "system",
                    "content": f"""You are a bioinformatics assistant for data analysis.
                    
                    Current context: {context}
                    
                    Your role:
                    1. Interpret analysis results and plots
                    2. Analyze visualizations and provide biological insights
                    3. Answer questions about plots and data patterns
                    4. Suggest next steps
                    
                    IMPORTANT: When users ask about plots or results, use the 'analyze_current_plots' tool 
                    to get insights about the current analysis state.
                    
                    Be concise and focus on actionable biological insights."""
                },
                {
                    "role": "user", 
                    "content": user_message
                }
            ]
            
            # Add tools if available
            kwargs = {"messages": messages}
            if available_tools:
                kwargs["tools"] = available_tools
                kwargs["tool_choice"] = "auto"
            
            response = self.client.chat.completions.create(
                model="openai/gpt-3.5-turbo",  # Much cheaper than GPT-4
                max_tokens=1000,  # Reduced from 4000
                temperature=0.1,
                **kwargs
            )
            
            actions = []
            
            # Handle tool calls
            if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
                tool_calls = response.choices[0].message.tool_calls
                tool_results = []
                
                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                        result = await self.tool_registry.execute_tool(tool_name, arguments)
                        tool_results.append(f"Tool {tool_name}: {result}")
                        actions.append(f"Used {tool_name}")
                    except Exception as e:
                        tool_results.append(f"Tool {tool_name} error: {str(e)}")
                        actions.append(f"Error with {tool_name}")
                
                # If we have tool results, make another call to get the final response
                if tool_results:
                    messages.append({"role": "assistant", "content": response.choices[0].message.content or ""})
                    messages.append({"role": "user", "content": f"Tool results: {'; '.join(tool_results)}"})
                    
                    final_response = self.client.chat.completions.create(
                        model="openai/gpt-3.5-turbo",
                        messages=messages,
                        temperature=0.1,
                        max_tokens=1000
                    )
                    return final_response.choices[0].message.content, actions
            
            return response.choices[0].message.content, actions
            
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return f"I encountered an error: {str(e)}. Please try again.", []
