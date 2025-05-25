import streamlit as st
from modules.reader.pubmed import fetch_pubmed_with_abstract, display_pubmed_with_abstract
<<<<<<< HEAD
from modules.search.geo import geo_search, geo_display
from modules.reader.pubmed import reader
from chat.chatbot import ask_chatbot
from interface.welcome import show_welcome_message
from modules.rna_seq.input_preview import show_rnaseq_inputs
from modules.rna_seq.workflow import (do_preprocessing,run_deseq2,make_volcano_plot,run_go_enrichment)
from modules.scrna_seq.workflow import *
from modules.scrna_seq.router import dispatch_sc_rnaseq_pipeline
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

def render_center_panel(data_col):
    with data_col:
        if not any([
            st.session_state.tabular_analysis,
            st.session_state.image_analysis,
            st.session_state.scRNAseq_analysis,
            st.session_state.rnaseq_analysis,
            st.session_state.reader,
            st.session_state.search
        ]):
            show_welcome_message(data_col)  # ✅ Use the new modular function
            return  # Optional: stop further rendering if no module is selected

def render_center_panel(data_col):
    with data_col:
        if not any([
            st.session_state.tabular_analysis,
            st.session_state.image_analysis,
            st.session_state.scRNAseq_analysis,
            st.session_state.rnaseq_analysis,
            st.session_state.reader,
            st.session_state.search
        ]):
            from chat.chatbot import ask_chatbot
            if st.session_state.welcome_message == "":
                message = ask_chatbot(
                    [{"role": "user", "content": "Write an inspiration story in 300 words about a scientist or a discovery. Please format it as a markdown document."}],
                    model_choice='gpt4'
                )
                st.session_state.welcome_message = message.content
            st.markdown(st.session_state.welcome_message)

        if st.session_state.reader:
            reader(st.session_state.user_interest)

        if st.session_state.pubmed_search:
            if st.session_state.pubmed_search_query.strip():
                articles_info = fetch_pubmed_with_abstract(st.session_state.pubmed_search_query)
                display_pubmed_with_abstract(articles_info)
=======
from modules.reader.pubmed import reader
from modules.search.geo import geo_search, geo_display

from chat.chatbot import ask_chatbot
from interface.welcome import show_welcome_message

def render_center_panel(data_col):
    with data_col:
        tab = st.session_state.active_tab
        if tab not in ["tabular_analysis", "image_analysis", "scRNAseq_analysis", "reader", "search"]: 
            show_welcome_message(data_col)  # ✅ Use the new modular function

        if tab == "tabular_analysis":

            from modules.data import tabular
            tabular.tabular_data()
        elif tab == "reader":
            from modules.reader.pubmed import reader, display_pdf
            if st.session_state.uploaded_pdf_path is None:
                user_interest = st.session_state.user_interest
                reader(user_interest)
            else: display_pdf(st.session_state.uploaded_pdf_path)

        if st.session_state.pubmed_search:
            if st.session_state.pubmed_search_query.strip():
                st.write(st.session_state.pubmed_search_query)
                articles_info = fetch_pubmed_with_abstract(st.session_state.pubmed_search_query)
                display_pubmed_with_abstract(articles_info)
                
>>>>>>> origin/feature/pdf-viewer
            else:
                st.warning("Search query cannot be empty.")
            st.session_state.pubmed_search = False
            st.session_state.pubmed_search_query = ''
<<<<<<< HEAD

=======
'''
>>>>>>> origin/feature/pdf-viewer
        if st.session_state.search:
            if st.session_state.geo_search_query.strip():
                results = geo_search(st.session_state.geo_search_query)
                geo_display(results)
            else:
                st.warning("Search query cannot be empty.")
            st.session_state.geo_search = False
            st.session_state.geo_search_query = ''
<<<<<<< HEAD
        
        # RNA-seq analysis
        if st.session_state.rnaseq_analysis:
            show_rnaseq_inputs() 
            do_preprocessing()
            run_deseq2()
            make_volcano_plot()
            run_go_enrichment()

        # scRNA-seq analysis
        if st.session_state.scRNAseq_analysis:
            dispatch_sc_rnaseq_pipeline()
            run_scrnaseq_pipeline()

=======
'''
>>>>>>> origin/feature/pdf-viewer
