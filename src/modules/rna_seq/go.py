from gprofiler import GProfiler
import pandas as pd

def gprofiler_enrichment(gene_list, organism='hsapiens'):
    """
    Run GO enrichment analysis using g:Profiler.
    
    Args:
        gene_list (list of str): Gene symbols (e.g., ['TP53', 'BRCA1'])
        organism (str): Ensembl species name (default: human)
    
    Returns:
        pd.DataFrame: Enrichment results
    """
    gp = GProfiler(return_dataframe=True)
    result = gp.profile(
        organism=organism,
        query=gene_list,
        sources=["GO:BP", "GO:MF", "GO:CC"]
    )
    return result
