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


def display_pdf_uploader():
    st.session_state.setdefault("uploaded_pdf", None)
    st.session_state.setdefault("pdf_bytes", None)

    with st.expander("Click here to upload a PDF file"):
        file = st.file_uploader("Upload a PDF file", type=["pdf"])

    if file is not None:
        st.session_state.uploaded_pdf = file
        st.session_state.pdf_bytes = file.read()

    if st.session_state.uploaded_pdf:
        try:
            base64_pdf = base64.b64encode(st.session_state.pdf_bytes).decode('utf-8')
            pdf_display = f"""
                <iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="1000px" type="application/pdf"></iframe>
            """
            st.markdown(pdf_display, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error displaying PDF: {e}")


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
    with st.expander("Click here to see suggested articles"):
        for paper in articles_info:
            st.write("####", paper["title"])
            st.write("**Authors:**", ", ".join(paper["authors"]))
            st.write("**Abstract:**", paper["abstract"])
            st.link_button("Link to PubMed", f"https://www.ncbi.nlm.nih.gov/pubmed/{paper['pmid']}")
            if paper["pmc_id"]:
                st.link_button("Link to PMC", f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{paper['pmc_id']}/")
            st.markdown("---")


def reader(user_interest):
    display_pdf_uploader()
    articles_info = fetch_pubmed_with_abstract(user_interest)
    display_pubmed_with_abstract(articles_info)
