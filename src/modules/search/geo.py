import requests
from datetime import datetime
from typing import Optional, Dict, Any, List

# Reuse HTTP connections for performance
session = requests.Session()


def _normalize_date(date_str: str) -> str:
    """
    Normalize a date string into YYYY/MM/DD format.

    Acceptable inputs:
      - "YYYY"
      - "YYYY/MM"
      - "YYYY/MM/DD"

    Returns:
        A string in YYYY/MM/DD form.
    """
    parts = date_str.split('/')
    if len(parts) == 1:
        year = parts[0]
        return f"{year}/01/01"
    elif len(parts) == 2:
        year, month = parts
        return f"{year}/{month.zfill(2)}/01"
    elif len(parts) == 3:
        year, month, day = parts
        return f"{year}/{month.zfill(2)}/{day.zfill(2)}"
    else:
        raise ValueError(f"Invalid date format: {date_str}")


def search_geo(
    query: str,
    organism: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    data_type: Optional[str] = None,
    page_size: int = 100,
    page: int = 1,
) -> Dict[str, Any]:
    """
    Search NCBI GEO DataSets via E-utilities (ESearch + ESummary).

    Args:
        query: Search keywords (will be minimally cleaned).
        organism: Filter by organism name (e.g., "Homo sapiens").
        date_from: Start publication date (YYYY, YYYY/MM, or YYYY/MM/DD).
        date_to: End publication date.
        data_type: One of ["rna-seq", "gse", "gds"], to filter by entry type.
        page_size: Number of records per page.
        page: Page number (1-indexed).

    Returns:
        A dict with keys: count, term, page, page_size, hits (list of records).
    """
    # 1) Build search terms
    terms: List[str] = []
    clean_query = query.strip() or "expression profiling"
    terms.append(clean_query)

    if organism:
        terms.append(f"{organism}[orgn]")

    # Date filters
    if date_from or date_to:
        # Normalize dates
        if date_from:
            df = _normalize_date(date_from)
        else:
            df = "2000/01/01"
        if date_to:
            dt = _normalize_date(date_to)
        else:
            now = datetime.now()
            dt = f"{now.year}/{now.month:02d}/{now.day:02d}"
        terms.append(f"{df}:{dt}[PDAT]")

    # Data type filters
    if data_type:
        dt_lower = data_type.lower()
        if "rna" in dt_lower:
            terms.append("(rna-seq OR rnaseq OR \"rna seq\" OR \"transcriptome sequencing\")[ETYP]")
        elif dt_lower == "gse":
            terms.append("gse[ETYP]")
        elif dt_lower == "gds":
            terms.append("gds[ETYP]")
    else:
        terms.append("(gse[ETYP] OR gds[ETYP])")

    term = " AND ".join(terms)

    # Calculate retstart offset
    retstart = (page - 1) * page_size

    # 2) ESearch
    esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    esearch_params = {
        "db": "gds",
        "term": term,
        "retmode": "json",
        "retmax": page_size,
        "retstart": retstart,
    }
    try:
        esr = session.get(esearch_url, params=esearch_params)
        esr.raise_for_status()
        esr_json = esr.json().get("esearchresult", {})
    except Exception as e:
        return {"error": str(e), "term": term}

    total_count = int(esr_json.get("count", 0))
    id_list = esr_json.get("idlist", [])

    if not id_list:
        return {"count": total_count, "term": term, "page": page, "page_size": page_size, "hits": []}

    # 3) ESummary
    esummary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    esummary_params = {
        "db": "gds",
        "id": ",".join(id_list),
        "retmode": "json",
    }
    try:
        esu = session.get(esummary_url, params=esummary_params)
        esu.raise_for_status()
        docs = esu.json().get("result", {})
    except Exception as e:
        return {"error": str(e), "term": term, "count": total_count}

    # Remove the 'uids' key
    docs.pop("uids", None)

    # 4) Build hits
    hits: List[Dict[str, Any]] = []
    for uid in id_list:
        entry = docs.get(uid, {})
        hits.append({
            "id": uid,
            "accession": entry.get("accession", ""),
            "title": entry.get("title", ""),
            "summary": entry.get("summary", ""),
            "gds_type": entry.get("gdstype", ""),
            "samples": entry.get("samples", ""),
            "organism": entry.get("organism", ""),
        })

    return {
        "count": total_count,
        "term": term,
        "page": page,
        "page_size": page_size,
        "hits": hits,
    }
