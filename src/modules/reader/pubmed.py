# src/modules/reader/pubmed.py

import streamlit as st
from Bio import Entrez
import requests
import base64

Entrez.email = "agpranay@gmail.com"  # You can later move this to a config file


def pubmed_search(user_interest):
    handle = Entrez.esearch(db="pubmed", term=user_interest, retmax=5)
    record = Entrez.read(handle)
    handle.close()
    return record["IdList"]


def get_pmc_id(pmid):
    handle = Entrez.elink(dbfrom="pubmed", db="pmc", id=pmid)
    records = Entrez.read(handle)
    handle.close()

    linksets = records[0].get("LinkSetDb", [])
    for linkset in linksets:
        if linkset["DbTo"] == "pmc":
            pmc_ids = [link["Id"] for link in linkset["Link"]]
            if pmc_ids:
                return pmc_ids[0]
    return None


def download_pmc_pdf(pmc_id):
    url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/pdf/"
    try:
        response = requests.get(url)
        if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
            return response.content
        else:
            st.warning(f"PDF not available at {url} (status {response.status_code})")
    except Exception as e:
        st.error(f"Error downloading PDF: {e}")
    return None


def get_pdf_page_as_base64(file_path, page_number):
    from pypdf import PdfReader, PdfWriter
    from io import BytesIO
    """Extract a single page from PDF and return as base64-encoded string."""
    reader = PdfReader(file_path)
    writer_obj = PdfWriter()
    writer_obj.add_page(reader.pages[page_number])
    
    buffer = BytesIO()
    writer_obj.write(buffer)
    buffer.seek(0)
    
    return base64.b64encode(buffer.read()).decode("utf-8")

# Function: Update page number based on button
def update_page(increment, total_pages):
    new_page = st.session_state.page + increment
    if 0 <= new_page < total_pages:
        st.session_state.page = new_page


def display_pdf(file_path):
    from pypdf import PdfReader
    try: 
        reader = PdfReader(file_path)
        total_pages = len(reader.pages)
        # Session state init
        if 'page' not in st.session_state:
            st.session_state.page = 1
        
        # Controls: prev/next
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            st.button("⬅️ Previous", on_click=update_page, args=(-1, total_pages))
        
        with col3:
            st.button("Next ➡️", on_click=update_page, args=(1, total_pages))
        st.slider("Page", min_value=0, max_value=total_pages-1,key="page", label_visibility="collapsed")
        # Get and display page
        b64_pdf = get_pdf_page_as_base64(file_path, st.session_state.page)
        #pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="700px" type="application/pdf"></iframe>'
        pdf_display = f"""
        <div style='border:1px solid #ddd; border-radius: 8px; padding: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);'>
            <iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="700px" style="border:none;"></iframe>
        </div>
        """
        
        st.markdown(pdf_display, unsafe_allow_html=True)

        st.caption(f"Page {st.session_state.page + 1} of {total_pages}")
    
    except Exception as e:
        st.error(f"Failed to read PDF: {e}")
    


def fetch_pubmed_with_abstract(user_interest):
    pmids = pubmed_search(user_interest)
    if not pmids:
        st.info("No articles found.")
        return []

    handle = Entrez.efetch(db="pubmed", id=",".join(pmids), rettype="medline", retmode="xml")
    records = Entrez.read(handle)
    handle.close()

    articles_info = []
    for article in records["PubmedArticle"]:
        article_data = article["MedlineCitation"]["Article"]
        pmid = article["MedlineCitation"]["PMID"]
        pmc_id = get_pmc_id(pmid)
        title = article_data.get("ArticleTitle", "No Title")

        authors = []
        for author in article_data.get("AuthorList", []):
            full_name = f"{author.get('ForeName', '')} {author.get('LastName', '')}".strip()
            if full_name:
                authors.append(full_name)

        abstract_parts = article_data.get("Abstract", {}).get("AbstractText", [])
        abstract = " ".join(str(part) for part in abstract_parts) if isinstance(abstract_parts, list) else str(abstract_parts)

        articles_info.append({
            "pmid": pmid,
            "pmc_id": pmc_id,
            "title": title,
            "authors": authors,
            "abstract": abstract
        })

    return articles_info


def display_pubmed_with_abstract(articles_info):

    for paper in articles_info:
        st.write("####", paper["title"])
        st.write("**Authors:**", ", ".join(paper["authors"]))
        st.write("**Abstract:**", paper["abstract"])
        st.link_button("Link to PubMed", f"https://www.ncbi.nlm.nih.gov/pubmed/{paper['pmid']}")
        if paper["pmc_id"]:
            st.link_button("Link to PMC", f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{paper['pmc_id']}/")
        st.markdown("---")


def reader(user_interest):

    articles_info = fetch_pubmed_with_abstract(user_interest)
    display_pubmed_with_abstract(articles_info)
