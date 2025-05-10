import streamlit as st
import pandas as pd
import os
import json
from chatbot import ask_chatbot  # Your custom chatbot handler

# --- Session State Initialization ---
def initialize_session():
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("show_uploader", False)
    st.session_state.setdefault("uploaded_df", [])
    st.session_state.setdefault("make_project_dir", False)
    st.session_state.setdefault("project_name", "")


# --- Chat Interface (Left Column) ---
def render_chat_interface():
    st.markdown("### I am a helpful lab assistant")

    # Display past messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Initial greeting
    if not st.session_state.messages:
        with st.chat_message("assistant"):
            st.markdown("Hello Pranay! How can I assist you today?")

    # Chat input
    prompt = st.chat_input("What can I help you with?")
    if prompt:
        handle_user_prompt(prompt)


# --- Handle User Input & Tool Calls ---
def handle_user_prompt(prompt):
    with st.chat_message("user"):
        st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

    message = ask_chatbot(user_question=st.session_state.messages, model_choice='gpt4')
    content = message.content
    tool_calls = getattr(message, "tool_calls", [])

    if tool_calls:
        handle_tool_calls(tool_calls)
    else:
        with st.chat_message("assistant"):
            st.markdown(content)
            st.session_state.messages.append({"role": "assistant", "content": content})


# --- Tool Handlers ---
def handle_tool_calls(tool_calls):
    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)

        if tool_name == "file_upload":
            handle_file_upload()

        elif tool_name == "make_project_dir":
            project_name = arguments.get("project_name")
            if project_name:
                os.makedirs(project_name, exist_ok=True)
                st.session_state.project_name = project_name
                with st.chat_message("assistant"):
                    st.markdown(f"Project directory created: **{project_name}**")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Project directory created: **{project_name}**"
                })


def handle_file_upload():
    with st.chat_message("assistant"):
        st.markdown("Please upload your file below:")
        file = st.file_uploader("Upload a file", type=["csv", "xlsx", "txt"])
        if file is not None:
            try:
                if file.name.endswith(".csv"):
                    df = pd.read_csv(file)
                elif file.name.endswith(".xlsx"):
                    df = pd.read_excel(file)
                elif file.name.endswith(".txt"):
                    df = pd.read_csv(file, delimiter="\t")
                else:
                    st.error("Unsupported file format.")
                    return

                st.session_state.uploaded_df.append(df)
                st.markdown(f"File **{file.name}** uploaded successfully. See the preview in the right panel.")
                render_data_panel()
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"File **{file.name}** uploaded successfully. See the preview in the right panel."
                })

            except Exception as e:
                st.error(f"Error reading file: {e}")


# --- Data Preview (Right Column) ---
def render_data_panel():
    if not st.session_state.get("uploaded_df"):
        return

    st.markdown("### Uploaded File Preview")

    for i, df in enumerate(st.session_state.uploaded_df):
        st.dataframe(df.head())
        column_names = df.columns.tolist()
        sorting_options = st.multiselect(f"Select columns to sort File #{i+1}", column_names, key=f"sort_{i}")
        if sorting_options:
            sorted_df = df.sort_values(by=sorting_options)
            st.session_state.uploaded_df[i] = sorted_df
            st.dataframe(sorted_df.head())

    if st.button("Merge all uploaded dataframes"):
        merged_df = pd.concat(st.session_state.uploaded_df, ignore_index=True)
        st.session_state.uploaded_df = [merged_df]
        st.dataframe(merged_df.head())
        st.session_state.messages.append({
            "role": "assistant",
            "content": "All uploaded dataframes have been merged successfully."
        })

    if st.button("Clear all uploaded data"):
        st.session_state.uploaded_df = []
        st.success("All uploaded data has been cleared.")


# --- Main ---
def main():
    st.set_page_config(page_title="Lab Assistant Chatbot", layout="wide")
    initialize_session()
    chat_col, data_col = st.columns([1, 1])
    with chat_col:
        render_chat_interface()
    with data_col:
        render_data_panel()


if __name__ == "__main__":
    main()
