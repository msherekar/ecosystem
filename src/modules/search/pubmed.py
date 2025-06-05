from typing import Any, Dict, List, Optional
from Bio import Entrez
import logging
import streamlit as st
import re
import requests
from bs4 import BeautifulSoup
from xml.etree import ElementTree as ET
import time
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set your email for Entrez API
Entrez.email = "mukulsherekar@gmail.com"
# Entrez.api_key = "your_ncbi_api_key"  # Optional

# Rate limiting
def rate_limit_sleep():
    """Add a small delay to avoid hitting rate limits"""
    time.sleep(random.uniform(0.5, 1.5))

# --- GitHub Link Detection Helpers ---

def extract_github_links(text: str) -> List[str]:
    if not text:
        return []
    # Enhanced regex to catch more variations
    patterns = [
        r"https?://github\.com/[^\s)\"\'<>\]]+",
        r"github\.com/[^\s)\"\'<>\]]+",  # Without protocol
    ]
    links = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            # Ensure we have the full URL
            if not match.startswith('http'):
                match = 'https://' + match
            links.append(match)
    return list(set(links))  # Remove duplicates

def fetch_pmc_fulltext_links(pmid: str) -> List[str]:
    """Enhanced PMC fulltext extraction with better error handling and more comprehensive searching"""
    try:
        # Try to get PMC ID
        with Entrez.elink(dbfrom="pubmed", db="pmc", id=pmid, linkname="pubmed_pmc") as handle:
            linkset = Entrez.read(handle)
        
        pmcid = None
        if linkset and len(linkset) > 0:
            for linksetdb in linkset[0].get("LinkSetDb", []):
                for link in linksetdb.get("Link", []):
                    pmcid = link["Id"]
                    break
                if pmcid:
                    break
        
        if not pmcid:
            logger.debug(f"No PMC ID found for PMID {pmid}")
            return []
        
        # Try multiple PMC URL formats
        pmc_urls = [
            f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/",
            f"https://europepmc.org/article/PMC/{pmcid}",
            f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"  # Fallback to PubMed page
        ]
        
        for url in pmc_urls:
            try:
                logger.debug(f"Trying PMC URL: {url}")
                
                # Add user agent to avoid being blocked
                headers = {
                    'User-Agent': 'Mozilla/5.0 (compatible; Scientific Research Tool; +mailto:mukulsherekar@gmail.com)'
                }
                
                response = requests.get(url, timeout=15, headers=headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Look for GitHub links in various sections
                github_links = set()
                
                # 1. Look in all text content
                full_text = soup.get_text()
                github_links.update(extract_github_links(full_text))
                
                # 2. Look specifically in href attributes
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    if "github.com" in href.lower():
                        if not href.startswith('http'):
                            href = 'https://' + href.lstrip('/')
                        github_links.add(href)
                
                # 3. Look in data/code availability sections specifically
                availability_patterns = [
                    re.compile(r'(data|code)\s+availability', re.IGNORECASE),
                    re.compile(r'availability\s+of\s+(data|code)', re.IGNORECASE),
                    re.compile(r'software\s+availability', re.IGNORECASE),
                    re.compile(r'source\s+code', re.IGNORECASE)
                ]
                
                for pattern in availability_patterns:
                    data_sections = soup.find_all(['div', 'section', 'p', 'span'], 
                                                 string=pattern)
                    for section in data_sections:
                        # Get the parent container and search within it
                        container = section.parent if section.parent else section
                        section_text = container.get_text()
                        github_links.update(extract_github_links(section_text))
                
                # 4. Look for links in specific sections by ID or class
                selectors = [
                    '#data-availability', '.data-availability', 
                    '#code-availability', '.code-availability',
                    '#supplementary-material', '.supplementary-material',
                    '.availability', '#availability'
                ]
                for selector in selectors:
                    sections = soup.select(selector)
                    for section in sections:
                        github_links.update(extract_github_links(section.get_text()))
                
                # Remove any NCBI-specific links that aren't relevant
                filtered_links = [link for link in github_links 
                                if not any(ncbi_domain in link.lower() 
                                         for ncbi_domain in ['github.com/ncbi', 'github.com/NCBI'])]
                
                if filtered_links:
                    logger.debug(f"Found {len(filtered_links)} GitHub links from {url}")
                    return filtered_links
                    
            except requests.exceptions.RequestException as e:
                logger.debug(f"Failed to fetch {url}: {e}")
                continue
            except Exception as e:
                logger.debug(f"Error processing {url}: {e}")
                continue
        
        logger.debug(f"No GitHub links found in any PMC source for PMID {pmid}")
        return []
        
    except Exception as e:
        logger.warning(f"PMC fulltext fetch failed for PMID {pmid}: {e}")
        return []

def fetch_pubmed_fulltext_links(pmid: str) -> List[str]:
    """Alternative method: Try to get links from the PubMed page itself"""
    try:
        pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        logger.debug(f"Fetching PubMed page: {pubmed_url}")
        
        response = requests.get(pubmed_url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        github_links = set()
        
        # Look for GitHub links in the full page
        full_text = soup.get_text()
        github_links.update(extract_github_links(full_text))
        
        # Look specifically in href attributes
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if "github.com" in href.lower():
                if not href.startswith('http'):
                    href = 'https://' + href.lstrip('/')
                github_links.add(href)
        
        logger.debug(f"Found {len(github_links)} GitHub links on PubMed page for PMID {pmid}")
        return list(github_links)
        
    except Exception as e:
        logger.warning(f"PubMed page fetch failed for PMID {pmid}: {e}")
        return []

def get_github_links(abstract: str, pmid: str) -> List[str]:
    """Enhanced GitHub link extraction from multiple sources"""
    links = set()
    
    # 1. Search in abstract
    abstract_links = extract_github_links(abstract)
    links.update(abstract_links)
    logger.debug(f"Found {len(abstract_links)} GitHub links in abstract")
    
    # 2. Search in PMC fulltext
    pmc_links = fetch_pmc_fulltext_links(pmid)
    links.update(pmc_links)
    logger.debug(f"Found {len(pmc_links)} GitHub links in PMC fulltext")
    
    # 3. Search in PubMed page (fallback)
    if not links:  # Only try this if we haven't found any links yet
        pubmed_links = fetch_pubmed_fulltext_links(pmid)
        links.update(pubmed_links)
        logger.debug(f"Found {len(pubmed_links)} GitHub links on PubMed page")
    
    final_links = list(links)
    logger.info(f"Total GitHub links found for PMID {pmid}: {len(final_links)}")
    
    return final_links

# --- Entrez API Functions ---

def entrez_search(term: str, db: str = "pubmed", retmax: int = 1, retstart: int = 0, usehistory: bool = False) -> Dict[str, Any]:
    if not term or term.strip() == "":
        raise ValueError("Search term cannot be empty")
    params = {
        "db": db,
        "term": term,
        "retmax": retmax,
        "retstart": retstart,
        "usehistory": "y" if usehistory else None,
        "retmode": "xml"
    }
    params = {k: v for k, v in params.items() if v is not None}
    try:
        rate_limit_sleep()  # Add rate limiting
        with Entrez.esearch(**params) as handle:
            record = Entrez.read(handle)
        return record
    except Exception as e:
        logger.error("Entrez.esearch failed: %s", e)
        raise

def entrez_summary(ids: List[str], db: str = "pubmed") -> Dict[str, Any]:
    if not ids:
        raise ValueError("No IDs provided for summary fetch")
    try:
        rate_limit_sleep()  # Add rate limiting
        with Entrez.esummary(db=db, id=",".join(ids), retmode="xml") as handle:
            summary = Entrez.read(handle)
        return summary
    except Exception as e:
        logger.error("Entrez.esummary failed: %s", e)
        raise

def entrez_fetch_abstracts(ids: List[str]) -> List[Dict[str, Any]]:
    if not ids:
        return []
    try:
        rate_limit_sleep()  # Add rate limiting
        with Entrez.efetch(db="pubmed", id=",".join(ids), retmode="xml") as handle:
            tree = ET.parse(handle)
            root = tree.getroot()
        abstracts = []
        for article in root.findall(".//PubmedArticle"):
            pmid = article.findtext(".//PMID")
            title = article.findtext(".//ArticleTitle")
            abstract = " ".join(elem.text or "" for elem in article.findall(".//AbstractText")).strip()
            abstracts.append({
                "pmid": pmid,
                "title": title,
                "abstract": abstract
            })
        return abstracts
    except Exception as e:
        logger.error("Entrez.efetch failed: %s", e)
        raise

# --- Main Search Function ---

def pubmed_search(query: str, page_size: int = 1) -> Dict[str, Any]:
    search_result = entrez_search(term=query, db="pubmed", retmax=page_size)
    id_list = search_result.get("IdList", [])
    if not id_list:
        return {
            "count": 0,
            "term": query,
            "hits": [],
            "provider": "pubmed",
            "provider_display_name": "PubMed"
        }
    summaries = entrez_summary(ids=id_list, db="pubmed")
    abstracts = {entry["pmid"]: entry["abstract"] for entry in entrez_fetch_abstracts(id_list)}

    hits = []
    for doc in summaries:
        uid = doc["Id"]
        github_links = get_github_links(abstracts.get(uid, ""), uid)
        hits.append({
            "uid": uid,
            "title": doc.get("Title", "No title"),
            "authors": [a["Name"] for a in doc.get("Authors", [])],
            "journal": doc.get("FullJournalName", "Unknown journal"),
            "pubdate": doc.get("PubDate", "Unknown date"),
            "doi": doc.get("DOI", "N/A"),
            "pubtypes": doc.get("PubTypeList", []),
            "abstract": abstracts.get(uid, "No abstract available"),
            "github_links": github_links
        })
    return {
        "count": len(hits),
        "term": query,
        "hits": hits,
        "provider": "pubmed",
        "provider_display_name": "PubMed"
    }

# --- Terminal Output ---

def print_results(results: Dict[str, Any]):
    print(f"\n🔍 Results from {results['provider_display_name']} for '{results['term']}':\n")
    if not results["hits"]:
        print("No results found.")
        return
    for i, hit in enumerate(results["hits"], 1):
        print(f"{i}. {hit['title']}")
        print(f"   Journal: {hit.get('journal', '')} ({hit.get('pubdate', '')})")
        print(f"   Abstract: {hit.get('abstract', '')[:500]}...")
        if hit.get("github_links"):
            for link in hit["github_links"]:
                print(f"   🔗 GitHub: {link}")
        print("")

# --- Streamlit Output ---

def pubmed_display(results: Dict[str, Any]):
    """Display PubMed search results using Streamlit"""
    if not results["hits"]:
        st.write("No results found.")
        return

    #st.write(f"### Results from {results['provider_display_name']} for '{results['term']}'")

    for i, hit in enumerate(results["hits"], 1):
        # Title, journal, date in one line
        st.markdown(f"**{i}. {hit['title']}** — *{hit['journal']}*, {hit['pubdate']}")

        # Build inline PubMed + GitHub links
        pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{hit['uid']}/"
        github_links = hit.get("github_links", [])

        link_html = f'<a href="{pubmed_url}" target="_blank">View on PubMed</a>'
        if github_links:
            for link in github_links:
                link_html += f' &nbsp;&nbsp;|&nbsp;&nbsp; <a href="{link}" target="_blank">GitHub Repository</a>'

        st.markdown(link_html, unsafe_allow_html=True)

        # Abstract
        st.markdown(f"**Abstract**: {hit.get('abstract', 'No abstract available')}")
        st.markdown("---")


# --- CLI Entry Point ---

if __name__ == "__main__":
    results = pubmed_search("Pacpaint: a histology-based deep learning model uncovers the extensive intratumor molecular heterogeneity of pancreatic adenocarcinoma.")
    print_results(results)
