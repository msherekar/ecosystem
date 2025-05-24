import os
import pandas as pd
import streamlit as st

def save_uploaded_file(file, folder="data"):
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, file.name)
    with open(file_path, "wb") as f:
        f.write(file.getbuffer())
    return file_path

def is_10x_mtx(file_list):
    required_suffixes = {"matrix.mtx", "genes.tsv", "features.tsv", "barcodes.tsv"}
    uploaded_suffixes = set(f.name.split("/")[-1] for f in file_list)
    return any(suffix in uploaded_suffixes for suffix in required_suffixes)

def handle_uploaded_files(single_file, multi_files):
    st.session_state.setdefault("uploaded_file_path", None)
    st.session_state.setdefault("uploaded_df", None)
    st.session_state.setdefault("upload_type", None)
    st.session_state.setdefault("10x_mtx_files", None)
    st.session_state["upload_ready"] = False  # reset at start

    if single_file:
        ext = os.path.splitext(single_file.name)[1].lower()
        file_path = save_uploaded_file(single_file)

        st.session_state["uploaded_file_path"] = file_path

        if ext in [".csv", ".tsv"]:
            sep = "\t" if ext == ".tsv" else ","
            try:
                df = pd.read_csv(single_file, sep=sep)
                st.session_state["uploaded_df"] = df
                st.session_state["upload_type"] = "tabular"
                st.session_state["upload_ready"] = True  # ✅ set if tabular
                st.sidebar.success(f"✅ Loaded {single_file.name} as tabular data.")
                st.sidebar.dataframe(df.head())
            except Exception as e:
                st.sidebar.error(f"❌ Failed to load tabular data: {e}")
        elif ext in [".h5ad", ".h5"]:
            st.session_state["upload_type"] = "scRNAseq_h5ad"
            st.session_state["upload_ready"] = True  # ✅ set for h5ad
            st.sidebar.success(f"✅ Detected scRNA-seq HDF5 file: {single_file.name}")
        else:
            st.sidebar.warning("⚠️ File format not recognized.")

    elif multi_files and is_10x_mtx(multi_files):
        mtx_files = {}
        for file in multi_files:
            filename = file.name.split("/")[-1]
            file_path = save_uploaded_file(file)
            mtx_files[filename] = file_path

        st.session_state["10x_mtx_files"] = mtx_files
        st.session_state["upload_type"] = "scRNAseq_10x"
        st.session_state["upload_ready"] = True  # ✅ set for 10x
        st.sidebar.success(f"✅ Uploaded {len(mtx_files)} 10x-format files.")
        st.sidebar.markdown("\n".join(f"- {f}" for f in mtx_files))

    else:
        st.sidebar.info("ℹ️ Upload a CSV/TSV, HDF5, or 10x format files to begin.")
        st.session_state["upload_type"] = None
        st.session_state["uploaded_file_path"] = None
        st.session_state["uploaded_df"] = None
        st.session_state["10x_mtx_files"] = None

