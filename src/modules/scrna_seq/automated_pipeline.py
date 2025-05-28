"""
Automated scRNA-seq Pipeline
Handles the "Run All Steps" functionality with progress tracking.
"""

import streamlit as st
import scanpy as sc
import numpy as np
import scipy.sparse as sp
from gprofiler import GProfiler

from src.modules.scrna_seq.tracking import log_shape
from src.modules.scrna_seq.clean import clean_invalid_values
from src.modules.scrna_seq.pipeline_config import get_automated_steps


class AutomatedPipeline:
    """Handles automated execution of the scRNA-seq pipeline."""
    
    def __init__(self):
        self.progress_bar = None
        self.status_text = None
        
    def run_all_steps(self):
        """
        Run the entire scRNA-seq pipeline automatically with default parameters.
        Returns True if successful, False otherwise.
        """
        anndata = st.session_state.get("anndata")
        if anndata is None:
            st.error("⚠️ No AnnData loaded. Please upload scRNA-seq data first.")
            return False

        try:
            self.progress_bar = st.progress(0)
            self.status_text = st.empty()
            
            automated_steps = get_automated_steps()
            total_steps = len(automated_steps)
            
            for i, step_config in enumerate(automated_steps):
                step_key = step_config["key"]
                step_title = step_config["title"]
                done_flag = step_config["done_flag"]
                
                # Skip if already done
                if st.session_state.get(done_flag, False):
                    continue
                    
                # Update progress
                progress = int((i / total_steps) * 100)
                self.status_text.text(f"{step_title}...")
                self.progress_bar.progress(progress)
                
                # Execute step
                success = self._execute_step(step_key, anndata)
                if not success:
                    return False
                    
                # Mark as done
                st.session_state[done_flag] = True
                st.session_state["anndata"] = anndata

            # Complete
            self.progress_bar.progress(100)
            self.status_text.text("✅ All steps completed successfully!")
            
            # Set current step to visualization to show results
            st.session_state.scrna_current_step = "viz"
            
            # Add completion message to chat
            self._add_completion_message(anndata)
            
            return True
            
        except Exception as e:
            st.error(f"❌ Automated pipeline failed: {e}")
            return False
    
    def _execute_step(self, step_key, anndata):
        """Execute a specific pipeline step."""
        try:
            if step_key == "qc":
                return self._run_qc(anndata)
            elif step_key == "filtering":
                return self._run_filtering(anndata)
            elif step_key == "normalization":
                return self._run_normalization(anndata)
            elif step_key == "dimred":
                return self._run_dimensionality_reduction(anndata)
            elif step_key == "clustering":
                return self._run_clustering(anndata)
            elif step_key == "viz":
                return self._run_visualization(anndata)
            elif step_key == "dea":
                return self._run_differential_expression(anndata)
            elif step_key == "enrichment":
                return self._run_enrichment(anndata)
            else:
                st.warning(f"⚠️ Step {step_key} not implemented in automated pipeline")
                return True
                
        except Exception as e:
            st.error(f"❌ Step {step_key} failed: {e}")
            return False
    
    def _run_qc(self, anndata):
        """Run quality control step."""
        log_shape("Before QC", anndata)
        
        # Calculate QC metrics
        anndata.var['mt'] = anndata.var_names.str.startswith('MT-')
        sc.pp.calculate_qc_metrics(anndata, percent_top=None, log1p=False, inplace=True)
        
        # Calculate mitochondrial gene percentage
        if 'mt' in anndata.var.columns:
            sc.pp.calculate_qc_metrics(anndata, qc_vars=['mt'], percent_top=None, log1p=False, inplace=True)
        
        log_shape("After QC", anndata)
        return True
    
    def _run_filtering(self, anndata):
        """Run filtering step with default parameters."""
        log_shape("Before Filtering", anndata)
        
        # Filter cells
        sc.pp.filter_cells(anndata, min_genes=200)  # Remove cells with < 200 genes
        sc.pp.filter_cells(anndata, max_genes=5000)  # Remove cells with > 5000 genes (doublets)
        
        # Filter by mitochondrial percentage if available
        if 'pct_counts_mt' in anndata.obs:
            anndata = anndata[anndata.obs.pct_counts_mt < 20, :]
        
        # Filter genes
        sc.pp.filter_genes(anndata, min_cells=3)  # Remove genes expressed in < 3 cells
        
        log_shape("After Filtering", anndata)
        return True
    
    def _run_normalization(self, anndata):
        """Run normalization step."""
        log_shape("Before Normalization", anndata)
        
        sc.pp.normalize_total(anndata, target_sum=1e4)
        sc.pp.log1p(anndata)
        anndata = clean_invalid_values(anndata)
        
        log_shape("After Normalization", anndata)
        return True
    
    def _run_dimensionality_reduction(self, anndata):
        """Run dimensionality reduction step."""
        # Clean inf/nan values
        if sp.issparse(anndata.X):
            data = anndata.X.data
            data[np.isinf(data)] = np.nan
            anndata.X.data = np.nan_to_num(data, nan=0.0)
        else:
            X = anndata.X
            X[np.isinf(X)] = np.nan
            anndata.X = np.nan_to_num(X)

        anndata = clean_invalid_values(anndata)

        # Identify highly variable genes
        try:
            sc.pp.highly_variable_genes(anndata, flavor='seurat_v3')
        except:
            sc.pp.highly_variable_genes(anndata, flavor='seurat')

        # Filter to HVGs
        anndata = anndata[:, anndata.var.get('highly_variable', False)]
        anndata = clean_invalid_values(anndata)

        # Scale and run PCA
        sc.pp.scale(anndata, max_value=10)
        sc.tl.pca(anndata, svd_solver='arpack')
        
        return True
    
    def _run_clustering(self, anndata):
        """Run clustering step."""
        log_shape("Before Clustering", anndata)
        
        sc.pp.neighbors(anndata)
        sc.tl.umap(anndata)
        sc.tl.leiden(anndata, resolution=1.0)  # Default resolution
        
        log_shape("After Clustering", anndata)
        return True
    
    def _run_visualization(self, anndata):
        """Run visualization step."""
        # UMAP should already be computed in clustering step
        return True
    
    def _run_differential_expression(self, anndata):
        """Run differential expression step."""
        log_shape("Before DEG", anndata)
        
        sc.tl.rank_genes_groups(anndata, groupby='leiden', method='t-test')
        
        log_shape("After DEG", anndata)
        return True
    
    def _run_enrichment(self, anndata):
        """Run enrichment analysis step."""
        # Gather top genes across clusters
        groups = anndata.uns['rank_genes_groups']['names'].dtype.names
        genes = []
        for g in groups:
            genes.extend(anndata.uns['rank_genes_groups']['names'][g].tolist())
        genes = list(set(genes))

        # GO Enrichment
        gp = GProfiler(return_dataframe=True)
        go_res = gp.profile(
            organism='hsapiens',
            query=genes,
            sources=['GO:BP', 'GO:CC', 'GO:MF']
        )
        st.session_state['go_results'] = go_res
        st.session_state['go_enriched'] = True

        # Pathway Enrichment
        path_res = gp.profile(
            organism='hsapiens',
            query=genes,
            sources=['KEGG', 'REAC']
        )
        st.session_state['path_results'] = path_res
        st.session_state['pathway_enriched'] = True
        
        return True
    
    def _add_completion_message(self, anndata):
        """Add completion message to chat."""
        n_clusters = len(anndata.obs["leiden"].unique())
        completion_message = (
            f"🎉 Complete scRNA-seq analysis finished! "
            f"Analyzed {anndata.shape[0]:,} cells × {anndata.shape[1]:,} genes, "
            f"identified {n_clusters} clusters, and performed enrichment analysis."
        )
        st.session_state.messages.append({"role": "assistant", "content": completion_message})


def run_automated_pipeline():
    """Convenience function to run the automated pipeline."""
    pipeline = AutomatedPipeline()
    return pipeline.run_all_steps() 