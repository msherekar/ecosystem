from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI
from chat.schema import tools
import streamlit as st
from datetime import datetime
import uuid

load_dotenv()

MODEL_MAP = {
    "gpt3": "openai/gpt-3.5-turbo",
    "gpt4": "openai/gpt-4-turbo",
    "o3mh": "openai/o3-mini-high",
    "deepseek": "deepseek/deepseek-r1",
    "claude": "anthropic/claude-3.5-sonnet-20240620",
    "gemini": "google/gemini-2.0-flash-001"
}


def format_geo_hits_markdown(hits: List[Dict[str, Any]], max_items: int = 10) -> str:
    """Format GEO hits as a bulleted markdown summary.
    
    Args:
        hits: List of GEO hit dictionaries
        max_items: Maximum number of hits to format
        
    Returns:
        Formatted markdown string
    """
    lines = []
    for i, hit in enumerate(hits[:max_items], 1):
        lines.append(f"""**{i}. [{hit['accession']}]** — {hit['title']}
- 🔬 Organism: {hit['organism']} | 🧪 Type: {hit['gds_type']} | 🧫 Samples: {hit['samples']}
- 📄 Summary: {hit['summary'][:200]}{'...' if len(hit['summary']) > 200 else ''}\n""")
    return "\n".join(lines)

def ask_chatbot(user_question: List[Dict[str, Any]], model_choice: str = 'gpt4') -> Optional[Any]:
    """Ask the chatbot a question and get a response.
    
    Args:
        user_question: List of message dictionaries for the chat
        model_choice: Model to use for the response
        
    Returns:
        Model response message or None if there's an error
        
    Raises:
        ValueError: If model choice is invalid or API key is missing
    """
    model_choice = model_choice.lower()
    if model_choice not in MODEL_MAP:
        raise ValueError(f"Invalid model choice: {model_choice}")

    try:
        api_key = st.secrets.get('API_KEY')
        if not api_key:
            raise ValueError("API_KEY not found in Streamlit secrets")
    except Exception as e:
        st.error(f"Error accessing API key: {str(e)}")
        return None

    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )

        model = MODEL_MAP[model_choice]
        
        response = client.chat.completions.create(
            model=model,
            messages=user_question,
            tools=tools,
            tool_choice="auto"
        )

        if response and response.choices:
            return response.choices[0].message
        else:
            st.error("No valid response received from the model")
            return None
            
    except Exception as e:
        st.error(f"Error communicating with the model: {str(e)}")
        return None




# if __name__ == "__main__":
#     response = ask_chatbot("Find me human breast cancer RNA-seq datasets")
#     print(format_geo_hits_markdown(response))

