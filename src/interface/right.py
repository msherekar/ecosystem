import streamlit as st
import json
from chat.chatbot import ask_chatbot

def chat_interface(chat_col):
    with chat_col:
        st.markdown("""
            <div style="text-align: center">
                <p>Hi there! I'm your AI assistant for biological data insights — how can I help analyze your data today?</p>
            </div>
        """, unsafe_allow_html=True)

        # Display past messages
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if st.session_state.clicked_button == "Code-writer":
            prompt = st.chat_input("Ask to write a code here")

            # Only add system prompt once at the start
            if not st.session_state.tabular_coding:
                st.session_state.tabular_coding.append({
                    "role": "assistant", 
                    "content": """
Prompt:

Return only valid raw Python code (no markdown, no explanations).

You are writing Streamlit code to manipulate a pandas DataFrame.

Multiple DataFrames are stored as dictionaries inside st.session_state.modified_df, like:

python
Copy
Edit
{"df1": df1_dict, "df2": df2_dict, ...}
To load a selected DataFrame, use:

python
Copy
Edit
df = pd.DataFrame(st.session_state.modified_df[chosen_df])
All Streamlit UI widgets, including:

st.selectbox("Select a dataframe", ...)

st.selectbox("Select a column", ...)
must be wrapped inside a single st.form("...") block followed by a st.form_submit_button("...").

Do not place any widgets outside the form.
Only process and display output after the user clicks the submit button.
Do not return markdown or code fences — only raw Python code.
"""
                })

            if prompt:
                st.session_state.tabular_coding.append({"role": "user", "content": prompt})

                with st.chat_message("user"):
                    st.markdown(prompt)

                message = ask_chatbot(user_question=st.session_state.tabular_coding, model_choice='gpt4')

                with st.chat_message("assistant"):
                    st.code(message.content, language="python")

                st.session_state.tabular_coding.append({"role": "assistant", "content": message.content})
                st.session_state.ai_code = message.content
                st.session_state.ai_coder = True
                #st.write(st.session_state.tabular_coding)
                

        else:
            prompt = st.chat_input("What can I help you with?")

            if prompt:
                st.session_state.messages.append({"role": "user", "content": prompt})

                with st.chat_message("user"):
                    st.markdown(prompt)

                message = ask_chatbot(user_question=st.session_state.messages, model_choice='gpt4')

                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        args = json.loads(tool_call.function.arguments)
                        if tool_call.function.name == "pubmed_search":
                            st.session_state.pubmed_search_query = args.get("query", "")
                            st.session_state.pubmed_search = True
                        elif tool_call.function.name == "geo_search":
                            st.session_state.geo_search_query = args.get("query", "")
                            st.session_state.geo_search = True

                assistant_content = message.content
                st.session_state.messages.append({"role": "assistant", "content": assistant_content})
                with st.chat_message("assistant"):
                    st.markdown(assistant_content)
