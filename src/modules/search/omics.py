# Local handling of omics search

import re
from typing import Optional, Dict, Any

def omics_search(query: str,
                 repository: str = "ALL",
                 organism: Optional[str] = None
                ) -> Dict[str, Any]:
    """
    Pull back a small summary of matching studies from GEO and/or TCGA.
    """
    results = {}

    # 1) NCBI GEO via E-utilities (you might wrap Biopython or requests)
    if repository in ("GEO", "ALL"):
        geo_hits = geo_ncbi_search(query, organism)
        results["GEO"] = geo_hits  # e.g. list of {accession, title, summary}

    # 2) TCGA via GDC API (you can use pythongdc or requests)
    if repository in ("TCGA", "ALL"):
        tcga_hits = tcga_gdc_search(query, organism)
        results["TCGA"] = tcga_hits

    return results


def geo_ncbi_search(query: str, organism: Optional[str]) -> list:
    # your existing GEO E-utilities code here
    # returns list of dicts
    pass

def tcga_gdc_search(query: str, organism: Optional[str]) -> list:
    # your existing GDC API code here
    pass
