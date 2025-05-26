import streamlit as st
from modules.reader.pubmed import fetch_pubmed_with_abstract, display_pubmed_with_abstract
from modules.search.geo import geo_search, geo_display
from modules.reader.pubmed import reader
from chat.chatbot import ask_chatbot
from interface.welcome import show_welcome_message
from modules.rna_seq.input_preview import show_rnaseq_inputs
from modules.rna_seq.workflow import run_rnaseq_pipeline
from modules.scrna_seq.workflow import run_scrnaseq_pipeline
from modules.scrna_seq.router import dispatch_sc_rnaseq_pipeline
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io


def is_rnaseq_ready():
    return (
        "rnaseq_counts_df" in st.session_state and
        "rnaseq_metadata_df" in st.session_state
    )

def is_scrnaseq_ready():
    return (
        "anndata" in st.session_state and
        st.session_state.anndata is not None
    )

def render_center_panel(data_col):
    with data_col:
        if not any([
            st.session_state.tabular_analysis,
            st.session_state.image_analysis,
            st.session_state.scRNAseq_analysis,
            st.session_state.rnaseq_analysis,
            st.session_state.reader,
            st.session_state.search,
            st.session_state.get("agent_requested_rnaseq", False),
            st.session_state.get("agent_requested_scrnaseq", False),
            st.session_state.get("agent_requested_tabular", False),
            st.session_state.get("agent_requested_image", False),
            st.session_state.get("agent_requested_reader", False),
            st.session_state.get("agent_requested_search", False)
        ]):
            
            if st.session_state.welcome_message == "":
                message = ask_chatbot(
                    [{"role": "user", "content": "Write an inspiration story in 300 words about a scientist or a discovery. Please format it as a markdown document."}],
                    model_choice='gpt4'
                )
                st.session_state.welcome_message = message.content
            st.markdown(st.session_state.welcome_message)

        if st.session_state.reader or st.session_state.get("agent_requested_reader", False):
            reader(st.session_state.user_interest)

        if st.session_state.pubmed_search:
            if st.session_state.pubmed_search_query.strip():
                articles_info = fetch_pubmed_with_abstract(st.session_state.pubmed_search_query)
                display_pubmed_with_abstract(articles_info)
            else:
                st.warning("Search query cannot be empty.")
            st.session_state.pubmed_search = False
            st.session_state.pubmed_search_query = ''

        if st.session_state.search or st.session_state.get("agent_requested_search", False):
            if st.session_state.geo_search_query.strip():
                results = geo_search(st.session_state.geo_search_query)
                geo_display(results)
            else:
                st.warning("Search query cannot be empty.")
            st.session_state.geo_search = False
            st.session_state.geo_search_query = ''
        
        # RNA-seq analysis
        if st.session_state.get("rnaseq_analysis") or st.session_state.get("agent_requested_rnaseq"):
            if is_rnaseq_ready():
                run_rnaseq_pipeline()
            else:
                st.warning("🧬 Please upload both RNA-seq counts and metadata files to begin analysis.")

        if st.session_state.get("scRNAseq_analysis") or st.session_state.get("agent_requested_scrnaseq"):
            if is_scrnaseq_ready():
                run_scrnaseq_pipeline()
            else:
                st.info("🧬 scRNA-seq analysis activated. Please upload your `.h5ad` or 10x files in the left panel to proceed.")


            
        # Tabular analysis
        if st.session_state.tabular_analysis or st.session_state.get("agent_requested_tabular", False):
            st.info("Tabular analysis mode is active")
            
        # Image analysis
        if st.session_state.image_analysis or st.session_state.get("agent_requested_image", False):
            st.info("Image analysis mode is active")

