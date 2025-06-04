import streamlit as st
import os
import pandas as pd
import scanpy as sc
import tempfile
import zipfile
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

def handle_file_upload():
    """Browse Files button with clean file uploader in popover"""
    if st.button("Browse Files", use_container_width=True):
        st.session_state.show_file_uploader = True
    
    if st.session_state.get("show_file_uploader", False):
        with st.popover("Select a file", use_container_width=True):
            uploaded_file = st.file_uploader(
                "Choose file", 
                type=["csv", "txt", "xlsx", "pdf", "h5ad"],
                key="browse_files_popover",
                label_visibility="collapsed"
            )
            
            if uploaded_file is not None:
                file_name = uploaded_file.name
                
                if file_name.endswith(("csv", "txt", "xlsx")):
                    import src.modules.data.tabular as tabular
                    st.session_state.active_tab = 'tabular_analysis'
                    st.session_state.tabular_analysis = True
                    
                    # Save uploaded file temporarily to process it
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[1]) as tmp_file:
                        tmp_file.write(uploaded_file.read())
                        tmp_file_path = tmp_file.name
                    
                    df = tabular.process_uploaded_file(tmp_file_path)
                    st.session_state.original_df[file_name] = df
                    st.session_state.modified_df[file_name] = df.copy()
                    
                    # Clean up temporary file
                    os.unlink(tmp_file_path)
                    
                    st.session_state.show_file_uploader = False
                    st.success(f"✅ Loaded tabular file: {file_name}")
                    st.rerun()
                    
                elif file_name.endswith("pdf"):
                    st.session_state.active_tab = 'reader'
                    st.session_state.reader = True
                    
                    # Save PDF temporarily
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        tmp_file.write(uploaded_file.read())
                        tmp_file_path = tmp_file.name
                    
                    st.session_state.uploaded_pdf_path = tmp_file_path
                    from src.modules.reader.pubmed import display_pdf
                    display_pdf(tmp_file_path)
                    
                    st.session_state.show_file_uploader = False
                    st.success(f"✅ Loaded PDF file: {file_name}")
                    st.rerun()
                    
                elif file_name.endswith("h5ad"):
                    st.session_state.active_tab = 'scRNAseq_analysis'
                    st.session_state.scRNAseq_analysis = True
                    
                    # Save h5ad file temporarily
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".h5ad") as tmp_file:
                        tmp_file.write(uploaded_file.read())
                        tmp_file_path = tmp_file.name
                    
                    try:
                        anndata = sc.read_h5ad(tmp_file_path)
                        st.session_state.anndata = anndata
                        st.session_state.uploaded_scrna_file = tmp_file_path
                        
                        st.session_state.show_file_uploader = False
                        st.success(f"✅ Loaded scRNA-seq file: {file_name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to read h5ad file: {e}")
                        os.unlink(tmp_file_path)
                else:
                    st.info("Unsupported file type. Supported formats: CSV, TXT, XLSX, PDF, H5AD")
            
            if st.button("Cancel", key="cancel_file_upload"):
                st.session_state.show_file_uploader = False
                st.rerun()

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
