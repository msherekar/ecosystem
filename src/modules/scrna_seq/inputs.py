# show_inputs.py
import streamlit as st
from modules.scrna_seq.tracking import status, reset_steps
import scanpy as sc

def show_scrnaseq_inputs():
    anndata = st.session_state["anndata"]
    st.markdown("Here’s a quick summary of your uploaded data:")

    st.write(f"🧪 **Shape**: {anndata.shape[0]} cells × {anndata.shape[1]} genes")
    st.write(f"🔖 **Metadata fields**: {list(anndata.obs.columns)}")
    st.write(f"📦 **Gene features**: {list(anndata.var.columns)[:5]}...")

    st.session_state["input_summary_done"] = True




