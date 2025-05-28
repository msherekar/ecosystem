import streamlit as st
import scanpy as sc
import matplotlib.pyplot as plt
import numpy as np
from scipy import sparse
from src.modules.scrna_seq.tracking import status, log_shape
from src.modules.scrna_seq.plot import plot_filtering_qc

def do_filtering():
    anndata = st.session_state.get("anndata")
    if anndata is None:
        st.error("⚠️ No AnnData loaded. Please complete the Input step first.")
        return

    # Check if QC has been completed first
    if not st.session_state.get("qc_done", False):
        st.error("⚠️ Please complete Quality Control step first. QC metrics are required for filtering.")
        return

    # Check if QC metrics exist
    required_qc_metrics = ["n_genes_by_counts", "total_counts", "pct_counts_mt"]
    missing_metrics = [metric for metric in required_qc_metrics if metric not in anndata.obs.columns]
    if missing_metrics:
        st.error(f"⚠️ Missing QC metrics: {missing_metrics}. Please run QC step first.")
        return

    # Show current data dimensions
    st.info(f"📊 Current data: {anndata.shape[0]:,} cells × {anndata.shape[1]:,} genes")

    # Only show form if filtering hasn't been done yet
    if not st.session_state.get("filtering_done", False):
        with st.form(key="filter_form"):
            st.markdown("**Set Filtering Thresholds:**")
            
            col1, col2 = st.columns(2)
            with col1:
                min_genes = st.number_input("Minimum genes per cell", min_value=0, value=200, step=1, 
                                          help="Remove cells with fewer than this many genes")
                max_genes = st.number_input("Maximum genes per cell", min_value=0, value=5000, step=1,
                                          help="Remove cells with more than this many genes (likely doublets)")
            
            with col2:
                min_cells = st.number_input("Minimum cells per gene", min_value=0, value=3, step=1,
                                          help="Remove genes expressed in fewer than this many cells")
                max_mito_pct = st.number_input("Maximum mitochondrial %", min_value=0.0, max_value=100.0, value=20.0, step=0.5,
                                             help="Remove cells with high mitochondrial gene percentage")
            
            submitted = st.form_submit_button("▶️ Apply Filtering")

        if submitted:
            try:
                log_shape("Before Filtering", anndata)
                
                # Apply cell filters
                initial_cells = anndata.shape[0]
                sc.pp.filter_cells(anndata, min_genes=min_genes)
                after_min_genes = anndata.shape[0]
                
                # Filter by max genes
                if max_genes > 0:
                    sc.pp.filter_cells(anndata, max_genes=max_genes)
                after_max_genes = anndata.shape[0]
                
                # Filter by mitochondrial percentage
                if max_mito_pct < 100:
                    anndata = anndata[anndata.obs.pct_counts_mt < max_mito_pct, :]
                after_mito = anndata.shape[0]
                
                # Apply gene filters
                initial_genes = anndata.shape[1]
                sc.pp.filter_genes(anndata, min_cells=min_cells)
                after_gene_filter = anndata.shape[1]
                
                # Update session state
                st.session_state["anndata"] = anndata
                st.session_state["filtering_done"] = True
                
                # Show filtering summary
                st.success("✅ Filtering completed!")
                st.info(f"""
                **Filtering Summary:**
                - Cells: {initial_cells:,} → {after_mito:,} ({initial_cells - after_mito:,} removed)
                  - Min genes filter: {initial_cells - after_min_genes:,} cells removed
                  - Max genes filter: {after_min_genes - after_max_genes:,} cells removed  
                  - Mitochondrial filter: {after_max_genes - after_mito:,} cells removed
                - Genes: {initial_genes:,} → {after_gene_filter:,} ({initial_genes - after_gene_filter:,} removed)
                """)
                
                log_shape("After Filtering", anndata)
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Filtering failed: {e}")
                return

    # Show results if filtering is done
    if st.session_state.get("filtering_done", False):
        st.success("✅ Filtering applied successfully.")
        plot_filtering_qc(anndata)
        
        # Option to reset filtering
        if st.button("♻️ Reset Filtering", key="reset_filtering"):
            st.session_state.pop("filtering_done", None)
            st.warning("⚠️ Filtering reset. You'll need to re-upload your data or restart from QC.")
            st.rerun()
