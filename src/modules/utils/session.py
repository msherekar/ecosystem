import streamlit as st
import os

def initialize_session_state():
    defaults = {
        "welcome_message": "",
        "messages": [],
        "uploaded_df": {},
        "project_name": "",
        "uploaded_pdf_path": None,
        "temp": {},
        "current_dir": os.getcwd(),
        "show_file_browser": False,
        "active_tab": "Main",
        "pubmed_search": False,
        "pubmed_search_query": "",
        "search": False,
        "geo_search": False,
        "geo_search_query": "",
        "create_project": False,
        "user_interest": "cancer biomarkers"
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

def create_project():
    if st.session_state.create_project:
        project_name = st.sidebar.text_input("Enter the project name", key="enter_project_name")
        if project_name:
            try:
                os.makedirs(project_name, exist_ok=False)
                st.session_state.project_name = project_name
                st.sidebar.success(f"Project '{project_name}' created successfully.")
            except FileExistsError:
                st.sidebar.error(f"A folder named '{project_name}' already exists.")
            except Exception as e:
                st.sidebar.error(f"An error occurred: {e}")
            else:
                st.session_state.create_project = False
                st.rerun()

def browse_to_open_file():
    if st.session_state.show_file_browser:
        with st.sidebar.popover("Select a file", use_container_width=True):
            current_dir = st.session_state['current_dir']
            st.write(f"**Current directory:** `{current_dir}`")

            if os.path.isdir(current_dir):
                entries = os.listdir(current_dir)
                entries.sort()
                folders = [f for f in entries if os.path.isdir(os.path.join(current_dir, f))]
                files = [f for f in entries if os.path.isfile(os.path.join(current_dir, f))]

                # Navigate to a folder
                selected_folder = st.selectbox("Folders", [".. (go up)"] + folders)
                if st.button("Go to folder"):
                    if selected_folder == ".. (go up)":
                        st.session_state['current_dir'] = os.path.dirname(current_dir)
                    else:
                        st.session_state['current_dir'] = os.path.join(current_dir, selected_folder)
                    st.rerun()

                # File selection
                if files:
                    selected_file = st.selectbox("Files", files)
                    file_path = os.path.join(current_dir, selected_file)
                    if st.button("Load File"):
                        # Load files from the path
                        file_name = os.path.basename(file_path)
                        if file_name.endswith(("csv", "txt", "xlsx")):
                            import modules.data.tabular as tabular
                            #st.write(file_name)
                            st.session_state.active_tab == 'tabular_analysis'
                            df = tabular.process_uploaded_file(file_path)
                            st.session_state.original_df[file_name] = df
                            st.session_state.modified_df[file_name] = df.copy()
                            #st.dataframe(st.session_state.original_df[file_name])
                            st.session_state.show_file_browser = False
                            st.rerun()
                        if file_name.endswith("pdf"):
                            st.session_state.active_tab = 'reader'
                            st.session_state.uploaded_pdf_path = file_path
                            from modules.reader.pubmed import display_pdf
                            display_pdf(st.session_state.uploaded_pdf_path)
                            
                    st.error("Invalid directory. Please enter a valid path.")

