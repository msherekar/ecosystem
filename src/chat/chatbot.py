# Various chat functions

import os, sys, re, json
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from chat.schema import tools

from modules.search.genomics import genomics_search
from modules.data.tabular import tabular_data
from modules.reader.pdf import pdf_reader

load_dotenv()

# Revert to original models
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
    import logging
    
    model_key = model_choice.lower()
    if model_key not in MODEL_MAP:
        raise ValueError(f"Invalid model choice: {model_choice}")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENAI_API_KEY")
    )

    try:
        # Log the request parameters
        logging.info(f"Making API request with model: {MODEL_MAP[model_key]}")
        
        # 1) initial chat call with tools enabled
        try:
            resp = client.chat.completions.create(
                model=MODEL_MAP[model_key],
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=1000  # Set a lower max_tokens to avoid credit issues
            )
        except Exception as e:
            logging.error(f"Error during API call: {str(e)}")
            return {"content": f"Error during API call: {str(e)}"}
        
        # Log the full response for debugging
        logging.info(f"API response received: {resp}")
        
        # Check for error field in the response (OpenRouter specific)
        if hasattr(resp, 'error') and resp.error:
            error_msg = resp.error.get('message', 'Unknown error')
            logging.error(f"API returned error: {error_msg}")
            
            # Handle credit limit error specifically
            if "requires more credits" in error_msg:
                return {"content": "Sorry, the service has reached its credit limit. Please try again later or use a different model."}
            
            return {"content": f"Error from API: {error_msg}"}
        
        # Safety check - if resp is None, return an error
        if resp is None:
            logging.error("API response is None")
            return {"content": "Error: API response is None"}
            
        # Now we know resp is not None, check if it has the expected structure
        if not hasattr(resp, 'choices'):
            logging.error(f"API response has no 'choices' attribute. Response type: {type(resp)}")
            return {"content": "Error: API response has no 'choices' attribute"}
            
        if not resp.choices or len(resp.choices) == 0:
            logging.error("API response has empty choices list")
            return {"content": "Error: API response has empty choices list"}
            
        msg = resp.choices[0].message

        # 2) Check if there are tool calls in the response
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            logging.info(f"Found tool_calls in response: {tool_calls}")
            
            # Process the first tool call (currently only supporting one at a time)
            tool_call = tool_calls[0]
            function_name = tool_call.function.name
            
            try:
                function_args = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                function_args = {}
                
            logging.info(f"Function call: {function_name} with args: {function_args}")
                
            # 3) Dispatch to the correct local function
            try:
                if function_name == "search" or function_name == "omics_search":
                    logging.info("Calling genomics_search function")
                    result = genomics_search(
                        query=function_args.get("query", ""),
                        repository=function_args.get("repository", "ALL"),
                        organism=function_args.get("organism")
                    )
                    logging.info(f"Genomics search result: {result}")
                elif function_name == "data":
                    result = tabular_data(function_args)
                elif function_name == "reader":
                    result = pdf_reader(function_args)
                else:
                    result = {"error": f"Unknown function {function_name}"}
                    
                # Format the result for better display
                formatted_result = format_search_results(result) if function_name == "search" else json.dumps(result, indent=2)
                
                # 4) Return formatted results directly
                return {"content": formatted_result}
                
            except Exception as e:
                logging.error(f"Error calling function {function_name}: {str(e)}", exc_info=True)
                return {"content": f"Error executing {function_name}: {str(e)}"}

        # 6) Otherwise, it was just a normal text reply
        return msg
    except Exception as e:
        # Log the full exception for debugging
        logging.error(f"Exception in ask_chatbot: {str(e)}", exc_info=True)
        return {"content": f"Error: {str(e)}"}
        
def format_search_results(results):
    """Format search results in a readable way for display"""
    output = "## Search Results\n\n"
    
    if "GEO" in results:
        output += "### GEO Results\n\n"
        if results["GEO"]:
            for i, hit in enumerate(results["GEO"], 1):
                output += f"**{i}. {hit.get('title', 'No title')}**\n"
                output += f"Accession: {hit.get('accession', 'Unknown')}\n"
                output += f"{hit.get('summary', 'No summary available')[:200]}...\n\n"
        else:
            output += "No GEO results found.\n\n"
            
    if "TCGA" in results:
        output += "### TCGA Results\n\n"
        if results["TCGA"]:
            for i, hit in enumerate(results["TCGA"], 1):
                output += f"**{i}. {hit.get('name', 'No name')}**\n"
                output += f"Project ID: {hit.get('project_id', 'Unknown')}\n"
                output += f"Full name: {hit.get('full_name', 'No full name available')}\n\n"
        else:
            output += "No TCGA results found.\n\n"
            
    return output

