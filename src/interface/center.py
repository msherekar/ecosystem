import streamlit as st
from modules.reader.pubmed import fetch_pubmed_with_abstract, display_pubmed_with_abstract
from modules.reader.pubmed import reader
from modules.search.geo import geo_search, geo_display

from chat.chatbot import ask_chatbot
from interface.welcome import show_welcome_message

def render_center_panel(data_col):
    with data_col:
        tab = st.session_state.active_tab
        if tab not in ["tabular_analysis", "image_analysis", "scRNAseq_analysis", "reader", "bulk", "terminal"]: 
            show_welcome_message(data_col)  # ✅ Use the new modular function

        elif tab == "tabular_analysis":

            from modules.data import tabular
            tabular.tabular_data()
        elif tab == "bulk":
            from modules.rna_seq.workflow import run_rnaseq_pipeline
            run_rnaseq_pipeline()
        elif tab == 'scRNAseq_analysis':
            from modules.scrna_seq.workflow import run_scrnaseq_pipeline
            run_scrnaseq_pipeline()
        elif tab == 'image_analysis':
            from modules.image_analysis.image import image_main
            image_main()
        elif tab == "reader":
            from modules.reader.pubmed import reader, display_pdf
            if st.session_state.uploaded_pdf_path is None:
                user_interest = st.session_state.user_interest
                reader(user_interest)
            else: display_pdf(st.session_state.uploaded_pdf_path)
        elif tab == "terminal":
            from modules.terminal import terminal
            terminal.terminal()


        elif st.session_state.pubmed_search:
            if st.session_state.pubmed_search_query.strip():
                st.write(st.session_state.pubmed_search_query)
                articles_info = fetch_pubmed_with_abstract(st.session_state.pubmed_search_query)
                display_pubmed_with_abstract(articles_info)
                
            else:
                st.warning("Search query cannot be empty.")
            st.session_state.pubmed_search = False
            st.session_state.pubmed_search_query = ''
'''
        if st.session_state.search:
            if st.session_state.geo_search_query.strip():
                results = geo_search(st.session_state.geo_search_query)
                geo_display(results)
            else:
                st.warning("Search query cannot be empty.")
            st.session_state.geo_search = False
            st.session_state.geo_search_query = ''
'''
