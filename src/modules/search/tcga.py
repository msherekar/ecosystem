from typing import Optional
from modules.search.utils import extract_search_terms

def search_tcga(query: str,
                    organism: Optional[str] = None,
                    size: int = 5
                   ) -> list:
    """
    Pull back a small summary of matching studies from TCGA.
    """
    # Nothing to search if the query is empty
    if not query.strip():
        return []
        
    # Extract search terms from the natural language query
    search_terms, metadata = extract_search_terms(query)
    
    # If no useful search terms were extracted, use a default term
    if not search_terms:
        search_terms = "cancer"  # fallback for TCGA
    
    # In a more complete implementation, we would query the GDC API here
    # For now, just return some dummy data
    sample_data = [
        {"name": "TCGA-LUAD", "project_id": "TCGA-LUAD", "full_name": "Lung Adenocarcinoma"},
        {"name": "TCGA-LUSC", "project_id": "TCGA-LUSC", "full_name": "Lung Squamous Cell Carcinoma"},
        {"name": "TCGA-PAAD", "project_id": "TCGA-PAAD", "full_name": "Pancreatic Adenocarcinoma"},
        {"name": "TCGA-LAML", "project_id": "TCGA-LAML", "full_name": "Acute Myeloid Leukemia"},
        {"name": "TCGA-GBM", "project_id": "TCGA-GBM", "full_name": "Glioblastoma Multiforme"}
    ]
    
    # Filter to only the requested number of results
    return sample_data[:size]

