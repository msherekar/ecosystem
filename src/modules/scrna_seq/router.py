import scanpy as sc
import streamlit as st



def run_scanpy_workflow(adata):
    st.markdown("### 🔬 Scanpy Workflow (Preview)")
    st.write(f"Number of cells: {adata.n_obs}")
    st.write(f"Number of genes: {adata.n_vars}")
    st.dataframe(adata.obs.head())

def dispatch_sc_rnaseq_pipeline():
    if not st.session_state.get("upload_ready"):
        return

    upload_type = st.session_state.get("upload_type")
    try:
        if upload_type == "scRNAseq_h5ad":
            adata = sc.read_h5ad(st.session_state["uploaded_file_path"])
            st.session_state["adata"] = adata

        elif upload_type == "scRNAseq_10x":
            adata = sc.read_10x_mtx("data/", var_names='gene_symbols', cache=True)
            st.session_state["adata"] = adata
    except Exception as e:
        st.error(f"❌ Failed to load data: {e}")
    finally:
        st.session_state["upload_ready"] = False  # reset

