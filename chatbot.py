from openai import OpenAI
import sys
import streamlit as st
from reader import reader
from function_schema import tools
# Model aliases
MODEL_MAP = {
    "gpt3": "openai/gpt-3.5-turbo",
    "gpt4": "openai/gpt-4-turbo",
    "o3mh": "openai/o3-mini-high",
    "deepseek": "deepseek/deepseek-r1",
    "claude": "anthropic/claude-3.5-sonnet-20240620",
    "gemini": "google/gemini-2.0-flash-001"
}

def ask_chatbot(user_question, model_choice = 'gpt4'):
    
    model_choice = model_choice.lower()
    if model_choice not in MODEL_MAP:
        raise ValueError(f"Invalid model choice: {model_choice}")
    
    client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=st.secrets['API_KEY']
    )
    
    model = MODEL_MAP[model_choice]
    
    response = client.chat.completions.create(
        model=model,
        messages=user_question,
        tools=tools,
        tool_choice="auto"
    )
    #st.write(response)
    if response and response.choices:
        return response.choices[0].message
    else:
    # Handle the case where response or response.choices is None
        return "Error: No valid response received from the model."