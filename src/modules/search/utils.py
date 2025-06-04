import re, os
from typing import Tuple, Dict
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Set, Tuple
import yaml
from dateparser import parse
from flashtext import KeywordProcessor

def parse_timeframe_to_dates(timeframe: str) -> Dict[str, str]:
    """
    Parse natural language timeframe into dates for E-Utils.
    
    Args:
        timeframe: String with timeframe description (e.g., "last 3 months")
        
    Returns:
        Dictionary with date_from and date_to
    """
    today = datetime.now()
    result = {"date_from": None, "date_to": None}
    
    # Set end date to current month
    result["date_to"] = f"{today.year}/{today.month:02d}"
    
    # Parse "last X months/years/days"
    last_period_match = re.search(r"last\s+(\d+)\s+(month|months|year|years|day|days)", timeframe, re.IGNORECASE)
    if last_period_match:
        num = int(last_period_match.group(1))
        unit = last_period_match.group(2).lower()
        
        if unit in ["month", "months"]:
            start_date = today - timedelta(days=30 * num)
        elif unit in ["year", "years"]:
            start_date = today - timedelta(days=365 * num)
        elif unit in ["day", "days"]:
            start_date = today - timedelta(days=num)
        else:
            # Default to 3 months if unit not recognized
            start_date = today - timedelta(days=90)
            
        result["date_from"] = f"{start_date.year}/{start_date.month:02d}"
    
    # Parse specific year ranges like "2020-2022" or "from 2020 to 2022"
    year_range_match = re.search(r"(from\s+)?(\d{4})(\s+to\s+|\s*-\s*)(\d{4})", timeframe, re.IGNORECASE)
    if year_range_match:
        start_year = year_range_match.group(2)
        end_year = year_range_match.group(4)
        result["date_from"] = f"{start_year}/01"
        result["date_to"] = f"{end_year}/12"
    
    # Parse specific dates like "January 2022" or "Jan 2022"
    month_year_match = re.search(
        r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t)?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{4})",
        timeframe, 
        re.IGNORECASE
    )
    if month_year_match:
        month_name = month_year_match.group(1).lower()
        year = month_year_match.group(2)
        
        month_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
        }
        
        for prefix, month_num in month_map.items():
            if month_name.startswith(prefix):
                result["date_from"] = f"{year}/{month_num:02d}"
                result["date_to"] = f"{year}/{month_num:02d}"
                break
    
    return result
# Get the directory of the current file

# Load controlled-vocab maps using absolute paths
_species_map = yaml.safe_load(open("/Users/mukulsherekar/pythonProject/RA-Project/src/config/species.yaml"))
_data_type_map = yaml.safe_load(open("/Users/mukulsherekar/pythonProject/RA-Project/src/config/data_types.yaml"))
_inst_map = yaml.safe_load(open("/Users/mukulsherekar/pythonProject/RA-Project/src/config/instruments.yaml"))


# # Load controlled‑vocab maps
# _species_map = yaml.safe_load(open("config/species.yaml"))
# _data_type_map = yaml.safe_load(open("config/data_types.yaml"))
# _inst_map = yaml.safe_load(open("config/instruments.yaml"))

# Build keyword processors (trie-based)
_species_kw = KeywordProcessor(case_sensitive=False)
for canon, syns in _species_map.items():
    for s in syns:
        _species_kw.add_keyword(s, canon)

data_type_kw = KeywordProcessor(case_sensitive=False)
for canon, syns in _data_type_map.items():
    for s in syns:
        data_type_kw.add_keyword(s, canon)

_inst_kw = KeywordProcessor(case_sensitive=False)
for canon, syns in _inst_map.items():
    for s in syns:
        _inst_kw.add_keyword(s, canon)

# Stopwords to strip from free text
_STOPWORDS = {"find","show","me","datasets","in","geo","using","from","to"}


def extract_terms(user_q: str) -> dict:
    """
    Extract species, data type, instruments, date range, and free-text keywords.
    """
    # 1) Controlled vocab extraction
    species    = set(_species_kw.extract_keywords(user_q))
    data_types = set(data_type_kw.extract_keywords(user_q))
    insts      = set(_inst_kw.extract_keywords(user_q))

    # 2) Remove those tokens to isolate remainder
    remainder = user_q
    for token in species | data_types | insts:
        remainder = re.sub(rf"\b{re.escape(token)}\b", "", remainder, flags=re.IGNORECASE)

    # 3) Date parsing
    dates = parse(user_q, settings={"PREFER_DAY_OF_MONTH": "first"}) or []
    date_from = date_to = None
    if len(dates) >= 2:
        date_from = dates[0][1].strftime("%Y/%m/%d")
        date_to   = dates[1][1].strftime("%Y/%m/%d")

    # 4) Free-text keywords
    words = re.findall(r"\b[\w\-]+\b", remainder)
    keywords = [w for w in words if w.lower() not in _STOPWORDS]
    if not keywords:
        keywords = ["expression", "profiling"]

    return {
        "species":    list(species),
        "data_type":  list(data_types),
        "instruments": list(insts),
        "date_from":  date_from,
        "date_to":    date_to,
        "keywords":   keywords
    }


def build_eutils_terms(parsed: dict) -> List[str]:
    terms = []

    # 1) Free-text keywords
    if parsed.get("keywords"):
        terms += parsed["keywords"]

    # 2) Organism
    for sp in parsed.get("species", []):
        terms.append(f"{sp}[orgn]")

    # 3) Data types
    etyp_terms = []
    for dt in parsed.get("data_type", []):
        if dt.lower() in ("gse", "gds"):
            etyp_terms.append(f"{dt}[ETYP]")
        else:
            terms.append(dt)  # treat as a free-text keyword
    
    # Always restrict to Series or DataSets if no ETYP explicitly mentioned
    if not etyp_terms:
        etyp_terms = ["gse[ETYP]", "gds[ETYP]"]

    terms.append(f"({' OR '.join(etyp_terms)})")

    # 4) Instruments (as general keywords, since E-Utils doesn't support [instrument] field)
    for inst in parsed.get("instruments", []):
        terms.append(inst)

    # 5) Date filtering (convert YYYY/MM to YYYY/MM/DD for E-Utils [PDAT])
    date_from = parsed.get("date_from")
    date_to = parsed.get("date_to")
    if date_from or date_to:
        date_from_fmt = date_from + "/01" if date_from else "1900/01/01"
        date_to_fmt = date_to + "/31" if date_to else datetime.now().strftime("%Y/%m/%d")
        terms.append(f"{date_from_fmt}:{date_to_fmt}[PDAT]")

    return terms
