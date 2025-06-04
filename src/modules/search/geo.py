# src/modules/search/geo.py

from typing import List, Dict, Any, Optional
from Bio import Entrez
import logging

# Setup Entrez
Entrez.email = "mukulsherekar@gmail.com"
logger = logging.getLogger(__name__)


def entrez_search(term: str, db: str = "gds", retmax: int = 20, retstart: int = 0, usehistory: bool = False) -> Dict[str, Any]:
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
        with Entrez.esearch(**params) as handle:
            record = Entrez.read(handle)
        return record
    except Exception as e:
        logger.error("Entrez.esearch failed: %s", e)
        raise


def entrez_summary(ids: Optional[List[str]] = None, webenv: Optional[str] = None, query_key: Optional[str] = None, db: str = "gds", retmax: int = 20) -> Dict[str, Any]:
    if not (ids or (webenv and query_key)):
        raise ValueError("Must provide either ids or (webenv+query_key)")

    params: Dict[str, Any] = {"db": db, "retmode": "xml", "retmax": retmax}
    if ids:
        params["id"] = ids
    else:
        params.update({"WebEnv": webenv, "query_key": query_key})

    try:
        with Entrez.esummary(**params) as handle:
            summary = Entrez.read(handle)
        return summary
    except Exception as e:
        logger.error("Entrez.esummary failed: %s", e)
        raise


def geo_search(term: str, page: int = 1, page_size: int = 20, use_history: bool = False) -> Dict[str, Any]:
    if not term or term.strip() == "":
        return {"count": 0, "term": "", "page": page, "page_size": page_size, "hits": []}

    retstart = (page - 1) * page_size
    esr = entrez_search(term, retmax=page_size, retstart=retstart, usehistory=use_history)

    total = int(esr["Count"])
    ids = esr["IdList"]
    if not ids:
        return {"count": total, "term": term, "hits": []}

    summary = entrez_summary(
        ids=ids if not use_history else None,
        webenv=esr.get("WebEnv"),
        query_key=esr.get("QueryKey"),
        retmax=page_size
    )

    hits = [{
        "id": doc.get("Id", ""),
        "accession": doc.get("Accession", ""),
        "title": doc.get("title", ""),
        "summary": doc.get("summary", ""),
        "gds_type": doc.get("gdsType", ""),
        "samples": int(doc["n_samples"]) if "n_samples" in doc else "–",
        "organism": doc.get("taxon", "")
    } for doc in summary]

    return {
        "count": total,
        "term": term,
        "page": page,
        "page_size": page_size,
        "hits": hits
    }


def geo_display(results: Dict[str, Any]):
    import streamlit as st
    for hit in results.get("hits", []):
        st.write(hit.get("title"))
        st.write(
            f"[GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={hit.get('accession')}) &nbsp;|&nbsp; "
            f"**Accession:** `{hit.get('accession')}` &nbsp;|&nbsp; "
            f"**Type:** {hit.get('gds_type')} &nbsp;|&nbsp; "
            f"**Samples:** {hit.get('samples')} &nbsp;|&nbsp; "
            f"**Organism:** {hit.get('organism')}",
            unsafe_allow_html=True
        )
        st.write(hit.get("summary"))
        st.write("---")
