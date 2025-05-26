import streamlit as st
import os
import pandas as pd
import streamlit as st
import scanpy as sc
import tempfile
import zipfile
import os
import shutil

def create_project():
    if st.session_state.get("create_project", False):
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
    if st.session_state.get("show_file_browser", False):
        with st.sidebar.popover("Select a file", use_container_width=True):
            current_dir = st.session_state.get("current_dir", os.getcwd())
            st.write(f"**Current directory:** `{current_dir}`")

            if not os.path.isdir(current_dir):
                st.error("Invalid directory. Please enter a valid path.")
                return

            entries = sorted(os.listdir(current_dir))
            folders = [f for f in entries if os.path.isdir(os.path.join(current_dir, f))]
            files = [f for f in entries if os.path.isfile(os.path.join(current_dir, f))]

            if folders:
                selected_folder = st.selectbox("Folders", [".. (go up)"] + folders)
                if st.button("Go to folder"):
                    if selected_folder == ".. (go up)":
                        st.session_state["current_dir"] = os.path.dirname(current_dir)
                    else:
                        st.session_state["current_dir"] = os.path.join(current_dir, selected_folder)
                    st.rerun()
            else:
                st.info("No subfolders found.")

            if files:
                selected_file = st.selectbox("Files", files)
                file_path = os.path.join(current_dir, selected_file)
                if st.button("Load File"):
                    file_name = os.path.basename(file_path)
                    if file_name.endswith(("csv", "txt", "xlsx")):
                        import modules.data.tabular as tabular
                        st.session_state.active_tab = 'tabular_analysis'
                        df = tabular.process_uploaded_file(file_path)
                        st.session_state.original_df[file_name] = df
                        st.session_state.modified_df[file_name] = df.copy()
                        st.session_state.show_file_browser = False
                        st.rerun()
                    elif file_name.endswith("pdf"):
                        st.session_state.active_tab = 'reader'
                        st.session_state.uploaded_pdf_path = file_path
                        from modules.reader.pubmed import display_pdf
                        display_pdf(file_path)
                        st.session_state.show_file_browser = False
                        st.rerun()
                    elif file_name.endswith("h5ad"):
                        st.session_state.active_tab = 'scrna_analysis'
                        st.session_state.uploaded_scrna_file = file_path
                        handle_scrnaseq_upload()
                        st.session_state.show_file_browser = False
                        st.rerun()
                    
                    else:
                        st.info("No files found in this directory.")

# --- Upload Helpers ---
def handle_rnaseq_upload():
    uploaded_file = st.file_uploader("Upload RNA-seq counts file (.csv or .tsv)", type=["csv", "tsv"], key="rnaseq_counts_uploader")

    if uploaded_file:
        try:
            sample = uploaded_file.read(1024).decode("utf-8")
            uploaded_file.seek(0)
            delimiter = "\t" if sample.count("\t") > sample.count(",") else ","
            df = pd.read_csv(uploaded_file, sep=delimiter)
            st.session_state["rnaseq_counts_df"] = df
            st.session_state["rnaseq_counts_filename"] = uploaded_file.name
            st.success("✅ RNA-seq counts uploaded successfully!")
        except Exception as e:
            st.error(f"Error loading counts file: {e}")

    metadata_file = st.file_uploader("Upload metadata file (CSV)", type=["csv"], key="rnaseq_metadata_uploader")
    if metadata_file:
        try:
            metadata_df = pd.read_csv(metadata_file, index_col=0)
            if "condition" not in metadata_df.columns:
                st.error("Metadata must include a column named 'condition'.")
            else:
                st.session_state["rnaseq_metadata_df"] = metadata_df
                st.session_state["rnaseq_metadata_filename"] = metadata_file.name
                st.success("✅ Metadata uploaded successfully.")
        except Exception as e:
            st.error(f"Failed to load metadata: {e}")



def handle_scrnaseq_upload():
    single_file = st.file_uploader("Upload a single-cell file (e.g. `.h5ad`)", type=["h5ad"], key="scrna_single_upload")

    multi_files = st.file_uploader("Or upload 10x files (`matrix.mtx`, `barcodes.tsv`, `features.tsv`)", 
                                   type=["mtx", "tsv", "gz"], accept_multiple_files=True, key="scrna_multi_upload")

    # --- Handle .h5ad upload ---
    if single_file:
        # Check if this file has already been processed
        current_file_name = single_file.name
        last_processed_file = st.session_state.get("last_processed_h5ad_file", None)
        
        if current_file_name != last_processed_file:
            try:
                # Save uploaded file to temporary location
                with tempfile.NamedTemporaryFile(delete=False, suffix=".h5ad") as tmp_file:
                    tmp_file.write(single_file.read())
                    tmp_file_path = tmp_file.name
                
                # Read the h5ad file from the temporary location
                anndata = sc.read_h5ad(tmp_file_path)
                st.session_state.anndata = anndata            
                st.session_state["last_processed_h5ad_file"] = current_file_name
                st.success(f"✅ Parsed AnnData object from: `{single_file.name}`")
                
                # Clean up temporary file
                os.unlink(tmp_file_path)
                st.rerun()
            except Exception as e:
                st.error(f"Failed to read `.h5ad` file: {e}")

    # --- Handle 10x uploads ---
    if multi_files and len(multi_files) >= 3:
        # Check if these files have already been processed
        current_file_names = sorted([f.name for f in multi_files])
        last_processed_files = st.session_state.get("last_processed_10x_files", [])
        
        if current_file_names != last_processed_files:
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    filenames = {"mtx": None, "barcodes": None, "features": None}

                    # Save files to temp directory
                    for file in multi_files:
                        filepath = os.path.join(tmpdir, file.name)
                        with open(filepath, "wb") as f:
                            f.write(file.read())

                        if "matrix.mtx" in file.name:
                            filenames["mtx"] = filepath
                        elif "barcodes" in file.name:
                            filenames["barcodes"] = filepath
                        elif "features" in file.name or "genes" in file.name:
                            filenames["features"] = filepath

                    # Check for required files
                    if not all(filenames.values()):
                        st.error("Missing one or more required 10x files: `matrix.mtx`, `barcodes.tsv`, `features.tsv` or `genes.tsv`.")
                        return

                    # Read using Scanpy
                    anndata = sc.read_10x_mtx(tmpdir, var_names="gene_symbols", cache=False)
                    st.session_state.anndata = anndata
                    st.session_state["last_processed_10x_files"] = current_file_names
                    st.success("✅ Parsed AnnData object from 10x Genomics files.")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to load 10x files: {e}")
