"""
TCGA (The Cancer Genome Atlas) Search Module

Example implementation for searching TCGA database.
This demonstrates how easy it is to add new databases to the search registry.
"""

import streamlit as st
from typing import Dict, Any, List


def tcga_search(query: str, page_size: int = 20) -> Dict[str, Any]:
    """
    Search TCGA database for cancer datasets
    
    Args:
        query: Search query
        page_size: Number of results to return
        
    Returns:
        Dictionary with search results
    """
    # Mock implementation - in reality you'd call TCGA GDC API
    # https://api.gdc.cancer.gov/cases?filters=...
    
    mock_results = [
        {
            "id": "tcga_001",
            "project": "TCGA-BRCA",
            "title": f"Breast invasive carcinoma dataset - {query}",
            "primary_site": "Breast", 
            "cases": 1098,
            "data_type": "Gene Expression Quantification",
            "experimental_strategy": "RNA-Seq",
            "access": "open"
        },
        {
            "id": "tcga_002", 
            "project": "TCGA-LUAD",
            "title": f"Lung adenocarcinoma dataset - {query}",
            "primary_site": "Lung",
            "cases": 515,
            "data_type": "Copy Number Variation",
            "experimental_strategy": "Genotyping Array",
            "access": "open"
        }
    ]
    
    return {
        "count": len(mock_results),
        "term": query,
        "page": 1,
        "page_size": page_size,
        "hits": mock_results,
        "provider": "tcga",
        "provider_display_name": "TCGA"
    }


def tcga_display(results: Dict[str, Any]):
    """
    Display TCGA search results in Streamlit
    
    Args:
        results: Search results from tcga_search()
    """
    hits = results.get("hits", [])
    
    if not hits:
        st.warning("No TCGA datasets found.")
        return
    
    for hit in hits:
        st.write(f"**{hit.get('title', 'Unknown')}**")
        
        # Create info line with project, cases, data type
        info_parts = []
        if hit.get("project"):
            info_parts.append(f"**Project:** `{hit['project']}`")
        if hit.get("cases"):
            info_parts.append(f"**Cases:** {hit['cases']}")
        if hit.get("data_type"):
            info_parts.append(f"**Type:** {hit['data_type']}")
        if hit.get("experimental_strategy"):
            info_parts.append(f"**Strategy:** {hit['experimental_strategy']}")
        if hit.get("access"):
            info_parts.append(f"**Access:** {hit['access']}")
            
        if info_parts:
            st.write(" &nbsp;|&nbsp; ".join(info_parts), unsafe_allow_html=True)
        
        # Add download link (mock)
        if hit.get("project"):
            st.write(f"[View in GDC Portal](https://portal.gdc.cancer.gov/projects/{hit['project']})")
        
        st.write("---")

