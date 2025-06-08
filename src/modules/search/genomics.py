import requests
import json
from typing import Optional, Dict, Any, List, Set, Tuple
import re
from datetime import datetime, timedelta

try:
    from src.modules.search.geo import geo_search
except ImportError:
    geo_search = None

try:
    from src.modules.search.tcga import search_tcga
except ImportError:
    search_tcga = None


def genomics_search(query: str,
                    repository: str = "ALL",
                    organism: Optional[str] = None
                   ) -> Dict[str, Any]:
    """
    Pull back a small summary of matching studies from GEO and/or TCGA.
    """
    results: Dict[str, Any] = {}
    repo = repository.strip().upper()
    # 1) NCBI GEO via E-utilities
    if repository in ("GEO", "ALL"):
        if geo_search:
            geo_hits = geo_search(query)
            results["GEO"] = geo_hits
        else:
            results["GEO"] = {"error": "GEO search not available"}

    # 2) TCGA via GDC API
    if repository in ("TCGA", "ALL"):
        if search_tcga:
            tcga_hits = search_tcga(query)
            results["TCGA"] = tcga_hits
        else:
            results["TCGA"] = {"error": "TCGA search not available"}

    return results

# Common biomedical and scientific terms that should be preserved


def pubmed_search(query: str, max_results: int = 20) -> Dict[str, Any]:
    """
    Search PubMed for articles using the query
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        
    Returns:
        Dictionary with search results
    """
    try:
        from Bio import Entrez
        
        # Set email for Entrez (required by NCBI)
        Entrez.email = "mukulsherekar@gmail.com"
        
        # Search PubMed
        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
        search_results = Entrez.read(handle)
        handle.close()
        
        # Get article IDs
        id_list = search_results["IdList"]
        
        if not id_list:
            return {
                "count": 0,
                "query": query,
                "results": []
            }
        
        # Fetch article summaries
        handle = Entrez.esummary(db="pubmed", id=",".join(id_list))
        summaries = Entrez.read(handle)
        handle.close()
        
        # Format results
        articles = []
        for summary in summaries:
            articles.append({
                "pmid": summary.get("Id", ""),
                "title": summary.get("Title", ""),
                "authors": summary.get("AuthorList", ""),
                "journal": summary.get("Source", ""),
                "pub_date": summary.get("PubDate", ""),
                "doi": summary.get("DOI", ""),
                "abstract": summary.get("Abstract", "")
            })
        
        return {
            "count": len(articles),
            "query": query,
            "results": articles
        }
        
    except ImportError:
        # Fallback if BioPython not available
        return {
            "count": 0,
            "query": query,
            "results": [],
            "error": "BioPython not available for PubMed search"
        }
    except Exception as e:
        return {
            "count": 0,
            "query": query,
            "results": [],
            "error": str(e)
        }
