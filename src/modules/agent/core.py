import re
import json
from openai import OpenAI
import streamlit as st
from modules.agent.registry import registry

TOOL_DEFINITIONS = registry.get_tool_definitions()

class Agent:
    def __init__(self, api_key, model="openai/gpt-4-turbo"):
        self.client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        self.model = model
        self.memory = []

    def process_command(self, command, conversation_history=None):
        if conversation_history is None:
            conversation_history = []

        file_status = self.get_file_status_context()
        tool_summary = self.get_tool_memory_summary()

        messages = [
            {
                "role": "system",
                "content": f"""
                You are an intelligent agent for a bioinformatics application. 
                You can run all the transcriptomics and proteomics analysis pipelines and tools.
                Only invoke tools when needed. Request missing inputs if required.

                {file_status}

                Recent tool usage:
                {tool_summary}
                """
            }
        ]

        messages.extend(conversation_history)
        messages.append({"role": "user", "content": command})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto"
            )

            ai_message = response.choices[0].message
            result = {"response": ai_message.content, "actions": []}

            if ai_message.tool_calls:
                for tool_call in ai_message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)

                    tool_result = registry.execute_tool(function_name, **arguments)
                    summary = tool_result.get("summary")
                    if summary:
                        st.session_state.setdefault("agent_tool_history", []).append(summary)

                    result["actions"].append({
                        "tool": function_name,
                        "arguments": arguments,
                        "result": tool_result
                    })

            return result

        except Exception as e:
            return {"response": f"Error processing command: {str(e)}", "actions": []}

    def get_file_status_context(self):
        context = "Current file status:\n"
        if "rnaseq_counts_df" in st.session_state:
            context += "- RNA-seq counts uploaded\n"
        if "rnaseq_metadata_df" in st.session_state:
            context += "- RNA-seq metadata uploaded\n"
        if "deseq_results" in st.session_state:
            context += "- DESeq2 has been run\n"
        if "go_results" in st.session_state:
            context += "- GO enrichment has been run\n"
        if "anndata" in st.session_state:
            context += "- scRNA-seq data uploaded\n"
        return context

    def get_tool_memory_summary(self, n=3):
        recent = st.session_state.get("agent_tool_history", [])[-n:]
        if not recent:
            return "No tools used yet."
        return "\n".join(f"- {summary}" for summary in recent)

    def add_to_memory(self, item):
        self.memory.append(item)

    def get_memory(self):
        return self.memory
