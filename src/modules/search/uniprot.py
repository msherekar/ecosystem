"""
UniProt Protein Database Search Module

Example implementation for searching UniProt protein database.
This demonstrates how easy it is to add new databases to the search registry.
"""

import streamlit as st
from typing import Dict, Any, List


def uniprot_search(query: str, page_size: int = 20) -> Dict[str, Any]:
    """
    Search UniProt database for proteins
    
    Args:
        query: Search query
        page_size: Number of results to return
        
    Returns:
        Dictionary with search results
    """
    # Mock implementation - in reality you'd call UniProt REST API
    # https://rest.uniprot.org/uniprotkb/search?query=...
    
    mock_results = [
        {
            "id": "P04637",
            "accession": "P04637",
            "name": "P53_HUMAN",
            "protein_name": f"Cellular tumor antigen p53 - {query}",
            "organism": "Homo sapiens (Human)",
            "gene_name": "TP53",
            "length": 393,
            "function": "Acts as a tumor suppressor in many tumor types",
            "subcellular_location": "Nucleus",
            "reviewed": True
        },
        {
            "id": "P01023",
            "accession": "P01023", 
            "name": "A2MG_HUMAN",
            "protein_name": f"Alpha-2-macroglobulin - {query}",
            "organism": "Homo sapiens (Human)",
            "gene_name": "A2M",
            "length": 1474,
            "function": "Protease inhibitor and cytokine transporter",
            "subcellular_location": "Secreted",
            "reviewed": True
        }
    ]
    
    return {
        "count": len(mock_results),
        "term": query,
        "page": 1, 
        "page_size": page_size,
        "hits": mock_results,
        "provider": "uniprot",
        "provider_display_name": "UniProt"
    }


def uniprot_display(results: Dict[str, Any]):
    """
    Display UniProt search results in Streamlit
    
    Args:
        results: Search results from uniprot_search()
    """
    hits = results.get("hits", [])
    
    if not hits:
        st.warning("No UniProt proteins found.")
        return
    
    for hit in hits:
        st.write(f"**{hit.get('protein_name', 'Unknown')}**")
        
        # Create info line with accession, gene, organism, etc.
        info_parts = []
        if hit.get("accession"):
            info_parts.append(f"**Accession:** `{hit['accession']}`")
        if hit.get("gene_name"):
            info_parts.append(f"**Gene:** {hit['gene_name']}")
        if hit.get("length"):
            info_parts.append(f"**Length:** {hit['length']} aa")
        if hit.get("organism"):
            info_parts.append(f"**Organism:** {hit['organism']}")
        if hit.get("reviewed"):
            status = "Reviewed" if hit["reviewed"] else "Unreviewed"
            info_parts.append(f"**Status:** {status}")
            
        if info_parts:
            st.write(" &nbsp;|&nbsp; ".join(info_parts), unsafe_allow_html=True)
        
        # Function description
        if hit.get("function"):
            st.write(f"*Function:* {hit['function']}")
        
        # Add UniProt link
        if hit.get("accession"):
            st.write(f"[View in UniProt](https://www.uniprot.org/uniprot/{hit['accession']})")
        
        st.write("---") 