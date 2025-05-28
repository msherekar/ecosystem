import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from src.chat.schema import tools
import streamlit as st
from datetime import datetime
import uuid

load_dotenv()

MODEL_MAPPING = {
    "gpt3": "openai/gpt-3.5-turbo",
    "gpt4": "openai/gpt-3.5-turbo",  # Use cheaper model for prototyping
    "o3mh": "openai/gpt-3.5-turbo",  # Use cheaper model for prototyping
    "o1": "openai/gpt-3.5-turbo",   # Use cheaper model for prototyping
    "claude": "openai/gpt-3.5-turbo",  # Use cheaper model for prototyping
}


def format_geo_hits_markdown(hits, max_items=10):
    """Format GEO hits as a bulleted markdown summary."""
    lines = []
    for i, hit in enumerate(hits[:max_items], 1):
        lines.append(f"""**{i}. [{hit['accession']}]** — {hit['title']}
- 🔬 Organism: {hit['organism']} | 🧪 Type: {hit['gds_type']} | 🧫 Samples: {hit['samples']}
- 📄 Summary: {hit['summary'][:200]}{'...' if len(hit['summary']) > 200 else ''}\n""")
    return "\n".join(lines)

def ask_chatbot(user_question, model_choice='gpt4'):
    model_choice = model_choice.lower()
    if model_choice not in MODEL_MAPPING:
        raise ValueError(f"Invalid model choice: {model_choice}")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env or environment")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )

    model = MODEL_MAPPING[model_choice]
    
    response = client.chat.completions.create(
        model=model,
        messages=user_question,
        tools=tools,
        tool_choice="auto",
        max_tokens=800,  # Reduced from default for cost savings
        temperature=0.7
    )

    if response and response.choices:
        return response.choices[0].message
    else:
    # Handle the case where response or response.choices is None
        return "Error: No valid response received from the model."

    



# if __name__ == "__main__":
#     response = ask_chatbot("Find me human breast cancer RNA-seq datasets")
#     print(format_geo_hits_markdown(response))
