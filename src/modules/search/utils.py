import re
from typing import Tuple, Dict
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Set, Tuple

# def route_search(query: str, repository: str = "ALL", **kwargs) -> Dict[str, Any]:
#     search_terms, _ = extract_search_terms(query)
#     results = {}

#     if repository in ("GEO", "ALL"):
#         results["GEO"] = genomics_search(query=search_terms, repository="GEO", organism=kwargs.get("organism"))

#     if repository in ("TCGA", "ALL"):
#         results["TCGA"] = genomics_search(query=search_terms, repository="TCGA", organism=kwargs.get("organism"))

#     if repository in ("UNIPROT", "ALL"):
#         results["UniProt"] = protein_search(
#             query=search_terms,
#             organism=kwargs.get("organism"),
#             protein_type=kwargs.get("protein_type"),
#             reviewed=kwargs.get("reviewed", False)
#         )

#     return results

BIOMEDICAL_TERMS: Set[str] = {
    # Nucleic acids and sequencing
    "rna", "dna", "rna-seq", "rnaseq", "chip-seq", "chipseq", "scrna-seq", "scrnaseq", 
    "mrna", "mirna", "lncrna", "snp", "snv", "cnv", "methylation", "microarray",
    "transcriptome", "proteome", "genome", "genomic", "proteomics", "transcriptomics",
    "sequencing", "expression", "gene", "genes", "transcript", "transcripts",
    "high-throughput", "deep-sequencing", "next-generation", "ngs", "illumina", "hiseq", "miseq", "novaseq",
    "exome", "exon", "intron", "splicing", "alternative", "polya", "polymerase",
    
    # Cancer and disease terms
    "cancer", "tumor", "tumour", "carcinoma", "sarcoma", "leukemia", "lymphoma", 
    "breast", "lung", "prostate", "colon", "pancreatic", "ovarian", "liver", "brain",
    "glioblastoma", "melanoma", "metastasis", "metastatic", "invasion", "invasive",
    "malignant", "benign", "stage", "grade", "er+", "er-", "pr+", "pr-", "her2+", "her2-",
    "triple-negative", "tnbc", "ductal", "lobular", "neoplasm", "neoplastic",
    
    # Organisms
    "homo", "sapiens", "human", "humans", "mus", "musculus", "mouse", "mice",
    "rattus", "norvegicus", "rat", "rats", "yeast", "cerevisiae", "arabidopsis", "thaliana",
    "drosophila", "melanogaster",
    
    # Cell/tissue terminology
    "cell", "cells", "tissue", "tissues", "sample", "samples", "control", "controls",
    "line", "lines", "normal", "stroma", "epithelium", "epithelial", "mesenchymal",
    "fibroblast", "lymphocyte", "macrophage", "t-cell", "b-cell", "stem", "progenitor"
}

# Words that indicate search context but shouldn't be part of the actual search
STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", 
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", 
    "but", "by", "can", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", 
    "doesn't", "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "get", 
    "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", 
    "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", 
    "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", 
    "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", 
    "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", 
    "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", 
    "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there", "there's", 
    "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", 
    "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", 
    "were", "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", 
    "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", 
    "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves",
    
    # Additional search-related stopwords
    "find", "search", "query", "look", "get", "retrieve", "show", "tell", "about", "please", 
    "looking", "searching", "finding", "need", "want", "like", "related", "regarding",
    "database", "databases", "geo", "ncbi", "tcga", "uniprot", "dataset", "datasets",
    "study", "studies", "experiment", "experiments", "series", "accession", "data", 
    "information", "results", "analysis", "analyses"
}






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

def extract_search_terms(query: str) -> Tuple[str, Dict[str, str]]:
    """
    Extract relevant search terms from a natural language query.
    This function is more robust than the regex-based approach.
    
    Args:
        query: Natural language query
        
    Returns:
        Tuple of (clean_query, metadata)
    """
    # First, handle database-specific identifiers with regex
    # Look for patterns like GEO accessions (GSE12345, etc.)
    accession_patterns = {
        "geo_accession": r'(?:GSE|GDS|GSM)\d+',
        "ensembl_id": r'ENS[GT]\d+',
        "tcga_id": r'TCGA-[A-Za-z0-9]+-[A-Za-z0-9]+-[A-Za-z0-9]+',
        "sra_id": r'SRR\d+|SRX\d+|SRP\d+'
    }
    
    # Extract special identifiers
    metadata = {}
    for id_type, pattern in accession_patterns.items():
        matches = re.findall(pattern, query)
        if matches:
            metadata[id_type] = matches[0]  # Store the first match
            # Remove the ID from the query to avoid duplicate search
            query = re.sub(pattern, '', query)
    
    # Convert to lowercase and split into words
    words = query.lower().split()
    
    # Remove stopwords but preserve biomedical terms
    filtered_words = []
    for word in words:
        # Clean punctuation from the word
        clean_word = re.sub(r'[^\w\-]', '', word)
        
        # Skip empty strings after cleaning
        if not clean_word:
            continue
            
        # Keep biomedical terms and non-stopwords
        if clean_word in BIOMEDICAL_TERMS or (clean_word not in STOPWORDS and len(clean_word) > 2):
            filtered_words.append(clean_word)
    
    # Join the filtered words back into a query string
    clean_query = " ".join(filtered_words)
    
    # If we have a specific identifier, prioritize it by adding it to the clean query
    for id_type, identifier in metadata.items():
        if id_type == "geo_accession":
            # For GEO accessions, make them the primary search term
            clean_query = identifier
            break  # A direct ID search is most specific
    
    return clean_query, metadata