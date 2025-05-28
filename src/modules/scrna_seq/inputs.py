# show_inputs.py
import streamlit as st
from src.modules.scrna_seq.tracking import status, reset_steps
import scanpy as sc

import streamlit as st

def show_scrnaseq_inputs():
    anndata = st.session_state["anndata"]

    # Check if we're in automated mode
    automated_mode = st.session_state.get('automated_mode', False)
    
    if not automated_mode:
        # Compact metrics (only show in manual mode to avoid column nesting)
        col1, col2 = st.columns(2)
        col1.metric("Cells", f"{anndata.shape[0]:,}")
        col2.metric("Genes", f"{anndata.shape[1]:,}")

        # Gene features preview
        st.markdown("**Gene Features (first 20):**")
        st.code(", ".join(anndata.var_names[:20].tolist()) + " ...", language="text")

        # Metadata fields
        st.markdown("**Metadata:**")
        st.code("\n".join(anndata.obs.columns.tolist()), language="text")

    # Perform QC calculations if not already done
    if not st.session_state.get("qc_done", False):
        if not automated_mode:
            st.markdown("---")
            st.markdown("*Quality Control Analysis*")
        
        with st.spinner("Calculating QC metrics..."):
            try:
                # Identify mitochondrial genes
                anndata.var['mt'] = anndata.var_names.str.startswith('MT-')
                
                # Calculate QC metrics
                sc.pp.calculate_qc_metrics(anndata, percent_top=None, log1p=False, inplace=True)
                
                # Calculate mitochondrial gene percentage if MT genes exist
                if anndata.var['mt'].any():
                    sc.pp.calculate_qc_metrics(anndata, qc_vars=['mt'], percent_top=None, log1p=False, inplace=True)
                else:
                    # If no MT genes found, create dummy column
                    anndata.obs['pct_counts_mt'] = 0.0
                
                # Update session state
                st.session_state["anndata"] = anndata
                st.session_state["qc_done"] = True
                
                if not automated_mode:
                    st.success("✅ QC metrics calculated successfully!")
                
                # Show QC summary (only in manual mode to avoid column nesting)
                if not automated_mode:
                    st.markdown("**QC Metrics Summary:**")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Avg genes/cell", f"{anndata.obs['n_genes_by_counts'].mean():.0f}")
                    with col2:
                        st.metric("Avg counts/cell", f"{anndata.obs['total_counts'].mean():.0f}")
                    with col3:
                        if 'pct_counts_mt' in anndata.obs:
                            st.metric("Avg MT%", f"{anndata.obs['pct_counts_mt'].mean():.1f}%")
                        else:
                            st.metric("Avg MT%", "0.0%")
                    
                    st.rerun()
                
            except Exception as e:
                if not automated_mode:
                    st.error(f"❌ QC calculation failed: {e}")
                else:
                    raise e  # Re-raise in automated mode
                return
    else:
        # QC already done, show summary (only in manual mode)
        if not automated_mode:
            st.markdown("---")
            st.success("✅ Quality Control completed!")
            
            # Show QC summary
            st.markdown("**QC Metrics Summary:**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Avg genes/cell", f"{anndata.obs['n_genes_by_counts'].mean():.0f}")
            with col2:
                st.metric("Avg counts/cell", f"{anndata.obs['total_counts'].mean():.0f}")
            with col3:
                if 'pct_counts_mt' in anndata.obs:
                    st.metric("Avg MT%", f"{anndata.obs['pct_counts_mt'].mean():.1f}%")
                else:
                    st.metric("Avg MT%", "0.0%")

    # Optional: set done flag (already set above)
    st.session_state["input_summary_done"] = True






