# Various chat functions

import os, json, logging
from dotenv import load_dotenv
from openai import OpenAI
from chat.schema import tools
from chat.dispatch import dispatch_tool_call

load_dotenv()

# Initialize the local query processor

# Revert to original models
MODEL_MAP = {
    'gpt4': "openai/gpt-4",
    'gpt-4': "openai/gpt-4",
    'gpt3.5': "openai/gpt-3.5-turbo",
    'claude': "anthropic/claude-3-haiku",
    'deepseek': "deepseek/deepseek-chat",
    # Add more if needed
}

def ask_chatbot(messages: list[dict], model_choice: str = 'deepseek'):
    """
    Ask the chatbot a question
    """

    model_key = model_choice.lower()
    if model_key not in MODEL_MAP:
        raise ValueError(f"Invalid model choice: {model_choice}")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENAI_API_KEY")
    )

    try:
        resp = client.chat.completions.create(
            model=MODEL_MAP[model_key],
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=200
        )

        if hasattr(resp, 'error') and resp.error:
            return {"content": f"Error from API: {resp.error.get('message', 'Unknown error')}"}

        if not resp or not hasattr(resp, 'choices') or not resp.choices:
            return {"content": "Error: Invalid response from LLM"}

        msg = resp.choices[0].message
        
        tool_calls = getattr(msg, "tool_calls", None)

        if tool_calls:
            print(f'Tool calls: {tool_calls}')
            return dispatch_tool_call(tool_calls[0])

        return msg  # normal LLM message
    
    except Exception as e:
        logging.error(f"Exception in ask_chatbot: {str(e)}", exc_info=True)
        return {"content": f"Error: {str(e)}", "source": "error"}