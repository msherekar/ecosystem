import requests
import json
from typing import Optional, Dict, Any, List, Set, Tuple
import re
from datetime import datetime, timedelta
from src.modules.search.geo import search_geo
from src.modules.search.tcga import search_tcga


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
        geo_hits = search_geo(query, organism)
        results["GEO"] = geo_hits

    # 2) TCGA via GDC API
    if repository in ("TCGA", "ALL"):
        tcga_hits = search_tcga(query, organism)
        results["TCGA"] = tcga_hits

    return results

# Common biomedical and scientific terms that should be preserved
