import streamlit as st
import requests
import base64
import requests
from Bio import Entrez

def pubmed_search(user_interest):
    

    Entrez.email = "agpranay@gmail.com"
    handle = Entrez.esearch(db="pubmed", term=user_interest, retmax=5)
    record = Entrez.read(handle)
    handle.close()

    pubmed_ids = record["IdList"]

    return pubmed_ids
    
def get_pmc_id(pmid):
    """Given a PubMed ID, get the linked PMC ID (if any)"""
    Entrez.email = "agpranay@gmail.com"
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
    Entrez.email = "agpranay@gmail.com"
    """
    Download the full text PDF from PMC given a PMC ID.
    PMC PDFs can often be accessed via:
    https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/pdf/
    """
    url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/pdf/"
    try:
        response = requests.get(url)
        if response.status_code == 200 and response.headers['Content-Type'] == 'application/pdf':
            return response.content
        else:
            st.warning(f"PDF not available at {url} (status {response.status_code})")
            return None
    except Exception as e:
        st.error(f"Error downloading PDF: {e}")
        return None

def display_pdf():
    st.session_state.setdefault("uploaded_pdf", None)
    st.session_state.setdefault("pdf_bytes", None)
    
    ######### Option 1: User is uploading a PDF file
    with st.expander("Click here to upload a PDF file"):
        file = st.file_uploader("Upload a PDF file", type=["pdf"])

    if file is not None:
        # Store uploaded file and its bytes in session state
        st.session_state.uploaded_pdf = file
        st.session_state.pdf_bytes = file.read()

    # Display PDF if uploaded
    if "uploaded_pdf" in st.session_state and st.session_state.uploaded_pdf:
        try:
            # Avoid re-reading: only use stored bytes
            base64_pdf = base64.b64encode(st.session_state.pdf_bytes).decode('utf-8')
            pdf_display = f"""
                <iframe src="data:application/pdf;base64,{base64_pdf}"
                width="100%" height="1000px"
                type="application/pdf"></iframe>
            """
            st.markdown(pdf_display, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error displaying PDF: {e}")    
    

 
    
    ######### Option 2: LLM is suggesting few articles based on the user's preference/query


def fetch_pubmed_with_abstract(user_interest):
    Entrez.email = "agpranay@gmail.com"
    with st.expander("Click here to see suggested articles"):
        pmids = pubmed_search(user_interest)
        if not pmids:
            st.info("No articles found.")
            return
        
        # Step 2: Fetch abstracts for those PMIDs
        handle = Entrez.efetch(db="pubmed", id=",".join(pmids), rettype="medline", retmode="xml")
        records = Entrez.read(handle)
        handle.close()
        
        articles_info = []
        for article in records["PubmedArticle"]:
            article_data = article["MedlineCitation"]["Article"]
            
            # PMID
            pmid = article["MedlineCitation"]["PMID"]
            pmc_id = get_pmc_id(pmid)
            # Title
            title = article_data.get("ArticleTitle", "No Title")
            
            # Authors
            authors = []
            for author in article_data.get("AuthorList", []):
                last = author.get("LastName", "")
                first = author.get("ForeName", "")
                full_name = f"{first} {last}".strip()
                if full_name:
                    authors.append(full_name)
            
            # Abstract
            abstract_parts = article_data.get("Abstract", {}).get("AbstractText", [])
            if isinstance(abstract_parts, list):
                abstract = " ".join(str(part) for part in abstract_parts)
            else:
                abstract = str(abstract_parts)

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
        st.write("**Abstract:**", paper["abstract"][0:])
        st.link_button("Link to PubMed", f"https://www.ncbi.nlm.nih.gov/pubmed/{paper['pmid']}")
        if paper["pmc_id"] is not None:
            st.link_button("Link to PMC", f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{paper['pmc_id']}/")
        st.markdown("---")

def reader(user_interest):
    
    display_pdf()
    articles_info = fetch_pubmed_with_abstract(user_interest)
    display_pubmed_with_abstract(articles_info)
    
    


if __name__ == "__main__":
    reader()
