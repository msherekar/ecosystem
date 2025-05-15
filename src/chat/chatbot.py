# Various chat functions

import os, sys, re, json
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from chat.schema import tools

from modules.search.omics import omics_search
from modules.data.tabular import tabular_data
from modules.reader.pdf import pdf_reader

load_dotenv()

MODEL_MAP = {
    'gpt4': "openai/gpt-4",
    'gpt-4': "openai/gpt-4",
    'gpt3.5': "openai/gpt-3.5-turbo",
    'claude': "anthropic/claude-3-haiku",
    # Add more if needed
}

def ask_chatbot(messages: list[dict], model_choice: str = 'gpt4'):
    """
    Send `messages` to the LLM with function‐calling enabled, dispatch
    any requested function locally, then return the final assistant message.
    """
    model_key = model_choice.lower()
    if model_key not in MODEL_MAP:
        raise ValueError(f"Invalid model choice: {model_choice}")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENAI_API_KEY")
    )

    # 1) initial chat call with tools enabled
    resp = client.chat.completions.create(
        model=MODEL_MAP[model_key],
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    msg = resp.choices[0].message

    # 2) if the model wants to call a function…
    if getattr(msg, "function_call", None):
        name = msg.function_call.name
        raw_args = msg.function_call.arguments or "{}"
        try:
            args = json.loads(raw_args)
        except json.JSONDecodeError:
            args = {}

        # 3) dispatch to the correct local function
        if name == "search":
            result = omics_search(
                query=args.get("query", ""),
                repository=args.get("repository", "ALL"),
                organism=args.get("organism")
            )
        
        elif name == "data":
            result = tabular_data(args)      # adjust signature as needed
        elif name == "reader":
            result = pdf_reader(args)
        else:
            result = {"error": f"Unknown function {name}"}

        # 4) append the function result back into the messages
        messages.append({
            "role": "function",
            "name": name,
            "content": json.dumps(result)
        })

        # 5) re‐call the LLM so it can produce the user‐facing reply
        resp2 = client.chat.completions.create(
            model=MODEL_MAP[model_key],
            messages=messages
        )
        return resp2.choices[0].message

    # 6) otherwise, it was just a normal text reply
    return msg