import requests, os
from datetime import datetime
from typing import List, Dict, Any
from requests.adapters import HTTPAdapter, Retry
import logging
import json
from modules.search.utils import extract_terms, build_eutils_terms  
import yaml
from typing import Optional


# Set up HTTP session with retries/backoff
session = requests.Session()
retries = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429,500,502,503,504],
    allowed_methods=["GET"]
)
adapter = HTTPAdapter(max_retries=retries)
session.mount("https://", adapter)
session.mount("http://", adapter)

logger = logging.getLogger(__name__)



def search_geo(query: str, organism: Optional[str] = None, page: int = 1, page_size: int = 20, use_history: bool = False) -> Dict:
    term = query
    logger.debug("GEO ESearch term: %s", term)

    retstart = (page - 1) * page_size

    esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    esearch_params = {
        "db": "gds",
        "term": term,
        "retmode": "json",
        "retmax": page_size,
        "retstart": retstart
    }
    if use_history:
        esearch_params["usehistory"] = "y"

    try:
        r1 = session.get(esearch_url, params=esearch_params)
        r1.raise_for_status()
        jr = r1.json().get("esearchresult", {})
    except Exception as e:
        logger.error("ESearch failed: %s", e)
        return {"error": str(e), "term": term}

    total = int(jr.get("count", 0))
    ids = jr.get("idlist", [])
    if not ids:
        return {"count": total, "term": term, "page": page, "page_size": page_size, "hits": []}

    # ESummary
    esummary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    if use_history and jr.get("webenv") and jr.get("querykey"):
        summary_params = {
            "db": "gds",
            "WebEnv": jr["webenv"],
            "query_key": jr["querykey"],
            "retmode": "json",
            "retmax": page_size
        }
    else:
        summary_params = {"db": "gds", "id": ",".join(ids), "retmode": "json"}

    try:
        r2 = session.get(esummary_url, params=summary_params)
        r2.raise_for_status()
        docs = r2.json().get("result", {})
    except Exception as e:
        logger.error("ESummary failed: %s", e)
        return {"error": str(e), "term": term, "count": total}

    docs.pop("uids", None)
    hits: List[Dict[str, Any]] = []
    for uid in ids:
        entry = docs.get(uid, {})
        hits.append({
            "id": uid,
            "accession": entry.get("accession", ""),
            "title": entry.get("title", ""),
            "summary": entry.get("summary", ""),
            "gds_type": entry.get("gdstype", ""),
            "samples": entry.get("samples", ""),
            "organism": entry.get("organism", "")
        })

    return {"count": total, "term": term, "page": page, "page_size": page_size, "hits": hits}



if __name__ == "__main__":
    user_q = "Find me homo sapiens breast cancer RNA-seq"
    parsed = extract_terms(user_q)
    terms  = build_eutils_terms(parsed)
    query  = " AND ".join(terms)
    result = search_geo(query, page_size=20)
    print(json.dumps(result, indent=2))
