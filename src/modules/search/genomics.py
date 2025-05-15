import requests
import json
from typing import Optional, Dict, Any

def genomics_search(query: str,
                    repository: str = "ALL",
                    organism: Optional[str] = None
                   ) -> Dict[str, Any]:
    """
    Pull back a small summary of matching studies from GEO and/or TCGA.
    """
    results: Dict[str, Any] = {}

    # 1) NCBI GEO via E-utilities
    if repository in ("GEO", "ALL"):
        geo_hits = geo_ncbi_search(query, organism)
        results["GEO"] = geo_hits

    # 2) TCGA via GDC API
    if repository in ("TCGA", "ALL"):
        tcga_hits = tcga_gdc_search(query, organism)
        results["TCGA"] = tcga_hits

    return results


def geo_ncbi_search(query: str,
                    organism: Optional[str] = None,
                    retmax: int = 5
                   ) -> list:
    """
    Search NCBI GEO DataSets (GDS) using E-utilities and return basic info.
    """
    base_esearch = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    base_esummary = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    term = query
    if organism:
        term += f" AND \"{organism}\"[Organism]"

    params = {
        "db": "gds",
        "term": term,
        "retmode": "json",
        "retmax": retmax
    }
    resp = requests.get(base_esearch, params=params)
    resp.raise_for_status()
    ids = resp.json().get("esearchresult", {}).get("idlist", [])

    if not ids:
        return []

    summary_params = {
        "db": "gds",
        "id": ",".join(ids),
        "retmode": "json"
    }
    resp_sum = requests.get(base_esummary, params=summary_params)
    resp_sum.raise_for_status()
    docs = resp_sum.json().get("result", {})

    hits = []
    for uid in ids:
        item = docs.get(uid, {})
        hits.append({
            "accession": item.get("uid"),
            "title": item.get("title"),
            "summary": item.get("summary", "")
        })
    return hits


def tcga_gdc_search(query: str,
                    organism: Optional[str] = None,
                    size: int = 5
                   ) -> list:
    """
    Search TCGA projects via the GDC API and return basic info.
    """
    projects_url = "https://api.gdc.cancer.gov/projects"
    params = {
        "search": query,
        "size": size
    }
    resp = requests.get(projects_url, params=params)
    resp.raise_for_status()
    data = resp.json().get("data", {}).get("hits", [])

    hits = []
    for proj in data:
        hits.append({
            "project_id": proj.get("project_id"),
            "name": proj.get("name"),
            "full_name": proj.get("full_name")
        })
    return hits
