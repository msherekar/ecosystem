import streamlit as st
from Bio import Entrez

Entrez.email = "your_email@example.com"  # Replace with your actual email

def parse_query(query: str) -> str:
    organism = "Homo sapiens"
    if "mouse" in query.lower():
        organism = "Mus musculus"

    disease = query  # Simple placeholder
    if "scRNA" in query.lower() or "single cell" in query.lower():
        technique = '"single cell"[All Fields] OR "scRNA-seq"[All Fields]'
    else:
        technique = '"bulk RNA"[All Fields] OR "bulk RNA-seq"[All Fields]'

    final_query = (
        f'({disease}[Description]) AND "{organism}"[Organism] '
        f'AND ({technique}) AND "Expression profiling by high throughput sequencing"[Filter] '
        f'AND "gse"[Filter]'
    )
    return final_query

def geo_search(query_text: str, retmax=5):
    query = parse_query(query_text)

    st.subheader("🔍 GEO Search Results")
    st.code(f"Query: {query}", language="text")

    try:
        handle = Entrez.esearch(db="gds", term=query, retmax=retmax)
        result = Entrez.read(handle)
        ids = result["IdList"]
        handle.close()
    except Exception as e:
        st.error(f"Search failed: {e}")
        return

    if not ids:
        st.warning("No GEO results found.")
        st.session_state.geo_query_triggered = False
        return

    try:
        handle = Entrez.esummary(db="gds", id=",".join(ids))
        summaries = Entrez.read(handle)
        handle.close()
    except Exception as e:
        st.error(f"Summary fetch failed: {e}")
        return

    for record in summaries["DocumentSummarySet"]["DocumentSummary"]:
        st.markdown(f"### {record['Accession']}: {record['title']}")
        st.markdown(f"**Samples**: {record['n_samples']}, **Organism**: {record['taxon']}")
        st.markdown(record["summary"])
        st.markdown("---")

    st.session_state.geo_query_triggered = False
