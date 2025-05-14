# Various chat functions

import os, sys, re
import streamlit as st
from dotenv import load_dotenv
import re
from openai import OpenAI
# Imports from
load_dotenv()
# Define your available models here
MODEL_MAP = {
    'gpt4': "openai/gpt-4",
    'gpt-4': "openai/gpt-4",
    'gpt3.5': "openai/gpt-3.5-turbo",
    'claude': "anthropic/claude-3-haiku",
    # Add more if needed
}

def ask_chat_model(
    user_text,
    model_choice='gpt4',
    build_prompt=False,
    temperature=0.2
):
    """
    General function to ask any chat model.

    Args:
        user_text (str): Text to send to the model.
        model_choice (str): Which model to use ('gpt4', 'claude', etc.)
        build_prompt (bool): Whether to automatically build system/user messages.
        temperature (float): Sampling temperature.

    Returns:
        str: The model's response text.
    """
    model_choice = model_choice.lower()
    if model_choice not in MODEL_MAP:
        raise ValueError(f"Invalid model choice: {model_choice}")
    
    # Create client
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENAI_API_KEY")
    )

    model = MODEL_MAP[model_choice]
    
    def build_strict_prompt(user_text):
        return [
            {"role": "system", "content": "Reply ONLY in 'param=value' format."},
            {"role": "user", "content": f"User says: {user_text}"}
        ]

    def build_flexible_prompt(user_text):
        return [
            {"role": "system", "content": "Suggest which parameters to adjust and how."},
            {"role": "user", "content": f"Result description: {user_text}"}
        ]

    messages = build_strict_prompt(user_text) if build_prompt else build_flexible_prompt(user_text)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"API error: {e}")
        return ""

def ask_chatbot(user_question, model_choice = 'gpt4'):
    model_choice = model_choice.lower()
    if model_choice not in MODEL_MAP:
        raise ValueError(f"Invalid model choice: {model_choice}")
    
    client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENAI_API_KEY")
    )
    
    model = MODEL_MAP[model_choice]
    
    response = client.chat.completions.create(
        model=model,
        messages=user_question
    )

    return response.choices[0].message.content  # ✅ correct for openai>=1.0.0

def ask_chatgpt_for_params(user_text):
    """
    Send user text to ChatGPT to get parameter updates.
    """
    print(f"Asking ChatGPT for parameters: {user_text}")
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an assistant that helps adjust circle detection parameters for images. Reply ONLY in the format: 'param1=value1, param2=value2'"},
                {"role": "user", "content": f"User says: {user_text}. What parameter updates would you suggest?"}
            ],
            temperature=0.2  # Keep answers more deterministic
        )
        content = response['choices'][0]['message']['content']
        return content
    except Exception as e:
        print(f"ChatGPT API error: {e}")
        return ""