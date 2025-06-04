import streamlit as st

def get_filter_settings():
    """
    Display Streamlit sliders for padj, log2FC, lfcSE, and number of genes to label.

    Returns:
    - padj_thresh: float
    - lfc_thresh: float
    - lfc_se_thresh: float
    - top_n_genes: int
    """
    st.markdown("### 🎛️ Volcano Plot Filters")

    padj_thresh = st.slider("Adjusted p-value threshold", 0.0, 1.0, 0.05, 0.01)
    lfc_thresh = st.slider("Absolute log2 Fold Change threshold", 0.0, 5.0, 1.0, 0.1)
    lfc_se_thresh = st.slider("Maximum Standard Error (lfcSE)", 0.0, 10.0, 1.0, 0.1)
    top_n_genes = st.slider("Top genes to label on plot", 0, 50, 10, 1)

    return padj_thresh, lfc_thresh, lfc_se_thresh, top_n_genes
