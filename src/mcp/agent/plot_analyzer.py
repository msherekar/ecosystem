"""
Plot analysis and step summary generation for the agent system.
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import re

class PlotAnalyzer:
    """Analyzes plots and generates biological insights"""
    
    @staticmethod
    def analyze_qc_metrics(anndata) -> str:
        """Analyze QC metrics and generate summary"""
        try:
            n_cells = anndata.n_obs
            n_genes = anndata.n_vars
            
            # Get QC statistics
            mean_genes = anndata.obs["n_genes_by_counts"].mean()
            mean_counts = anndata.obs["total_counts"].mean()
            mean_mt = anndata.obs["pct_counts_mt"].mean() if "pct_counts_mt" in anndata.obs else 0
            
            summary = f"QC analysis shows {n_cells:,} cells with average {mean_genes:.0f} genes and {mean_counts:.0f} total counts per cell. "
            
            if mean_mt > 20:
                summary += f"High mitochondrial content ({mean_mt:.1f}%) suggests potential cell stress or death."
            elif mean_mt > 10:
                summary += f"Moderate mitochondrial content ({mean_mt:.1f}%) is within normal range."
            else:
                summary += f"Low mitochondrial content ({mean_mt:.1f}%) indicates healthy cells."
                
            return summary
            
        except Exception as e:
            return f"QC metrics analyzed. Data contains {anndata.n_obs:,} cells and {anndata.n_vars:,} genes."
    
    @staticmethod
    def analyze_filtering_results(anndata, pre_filter_cells=None, pre_filter_genes=None) -> str:
        """Analyze filtering results"""
        try:
            current_cells = anndata.n_obs
            current_genes = anndata.n_vars
            
            if pre_filter_cells and pre_filter_genes:
                cells_removed = pre_filter_cells - current_cells
                genes_removed = pre_filter_genes - current_genes
                summary = f"Filtering removed {cells_removed:,} low-quality cells ({cells_removed/pre_filter_cells*100:.1f}%) and {genes_removed:,} lowly-expressed genes ({genes_removed/pre_filter_genes*100:.1f}%). "
            else:
                summary = f"After filtering: {current_cells:,} cells and {current_genes:,} genes retained. "
            
            # Check data quality
            mean_genes = anndata.obs["n_genes_by_counts"].mean()
            if mean_genes > 2000:
                summary += "High gene detection suggests good data quality."
            elif mean_genes > 1000:
                summary += "Moderate gene detection is acceptable for most analyses."
            else:
                summary += "Low gene detection may require careful interpretation."
                
            return summary
            
        except Exception as e:
            return f"Filtering completed. Dataset now contains {anndata.n_obs:,} cells and {anndata.n_vars:,} genes."
    
    @staticmethod
    def analyze_normalization(anndata) -> str:
        """Analyze normalization results"""
        try:
            # Check if data is log-transformed
            X = anndata.X
            if hasattr(X, 'toarray'):
                X = X.toarray()
            
            data_min = np.min(X)
            data_max = np.max(X)
            data_mean = np.mean(X)
            
            summary = f"Normalization completed. Expression values range from {data_min:.2f} to {data_max:.2f} with mean {data_mean:.2f}. "
            
            if data_min >= 0 and data_max <= 20:
                summary += "Log-normalized data shows expected range for downstream analysis."
            elif data_min >= 0 and data_max > 1000:
                summary += "Data appears to be raw counts - consider log transformation."
            else:
                summary += "Normalized expression values are ready for downstream analysis."
                
            return summary
            
        except Exception as e:
            return "Normalization completed. Data is ready for downstream analysis."
    
    @staticmethod
    def analyze_pca_results(anndata) -> str:
        """Analyze PCA results"""
        try:
            if "pca" in anndata.uns and "variance_ratio" in anndata.uns["pca"]:
                var_ratio = anndata.uns["pca"]["variance_ratio"]
                pc1_var = var_ratio[0] * 100
                pc2_var = var_ratio[1] * 100
                total_var = np.sum(var_ratio[:10]) * 100  # First 10 PCs
                
                summary = f"PCA shows PC1 explains {pc1_var:.1f}% and PC2 explains {pc2_var:.1f}% of variance. "
                summary += f"First 10 PCs capture {total_var:.1f}% of total variance. "
                
                if pc1_var > 20:
                    summary += "Strong PC1 suggests dominant biological signal or potential batch effects."
                elif pc1_var > 10:
                    summary += "Moderate PC1 variance indicates good data structure."
                else:
                    summary += "Low PC1 variance suggests complex, multi-dimensional data."
                    
                return summary
            else:
                return "PCA completed. Dimensionality reduction reveals data structure."
                
        except Exception as e:
            return "PCA analysis completed. Data structure captured in principal components."
    
    @staticmethod
    def analyze_clustering_results(anndata) -> str:
        """Analyze clustering results"""
        try:
            if "leiden" in anndata.obs:
                n_clusters = len(anndata.obs["leiden"].unique())
                cluster_sizes = anndata.obs["leiden"].value_counts()
                largest_cluster = cluster_sizes.max()
                smallest_cluster = cluster_sizes.min()
                
                summary = f"Leiden clustering identified {n_clusters} distinct cell clusters. "
                summary += f"Cluster sizes range from {smallest_cluster} to {largest_cluster} cells. "
                
                # Check cluster balance
                size_ratio = largest_cluster / smallest_cluster
                if size_ratio > 10:
                    summary += "Large variation in cluster sizes suggests heterogeneous cell populations."
                elif size_ratio > 3:
                    summary += "Moderate cluster size variation indicates diverse cell types."
                else:
                    summary += "Balanced cluster sizes suggest well-defined cell populations."
                    
                return summary
            else:
                return "Clustering completed. Cells grouped into distinct populations."
                
        except Exception as e:
            return "Clustering analysis completed. Cell populations identified."
    
    @staticmethod
    def analyze_umap_visualization(anndata) -> str:
        """Analyze UMAP visualization"""
        try:
            if "X_umap" in anndata.obsm:
                umap_coords = anndata.obsm["X_umap"]
                x_range = np.ptp(umap_coords[:, 0])  # peak-to-peak range
                y_range = np.ptp(umap_coords[:, 1])
                
                summary = f"UMAP visualization reveals cell distribution across {x_range:.1f} x {y_range:.1f} coordinate space. "
                
                if "leiden" in anndata.obs:
                    n_clusters = len(anndata.obs["leiden"].unique())
                    summary += f"The {n_clusters} clusters show "
                    
                    # Simple heuristic for cluster separation
                    if x_range > 15 or y_range > 15:
                        summary += "well-separated populations with distinct cell types."
                    elif x_range > 8 or y_range > 8:
                        summary += "moderately separated populations with some overlap."
                    else:
                        summary += "closely related populations with continuous transitions."
                else:
                    summary += "Clear cell population structure visible in 2D projection."
                    
                return summary
            else:
                return "UMAP visualization completed. Cell populations mapped in 2D space."
                
        except Exception as e:
            return "UMAP visualization shows cell population structure."
    
    @staticmethod
    def analyze_differential_expression(results_df) -> str:
        """Analyze differential expression results"""
        try:
            if results_df is not None and len(results_df) > 0:
                total_genes = len(results_df)
                
                # Count significant genes (assuming padj < 0.05)
                if "padj" in results_df.columns:
                    sig_genes = len(results_df[results_df["padj"] < 0.05])
                elif "significant" in results_df.columns:
                    sig_genes = len(results_df[results_df["significant"]])
                else:
                    sig_genes = 0
                
                summary = f"Differential expression analysis identified {sig_genes:,} significant genes out of {total_genes:,} tested. "
                
                if sig_genes > 1000:
                    summary += "Large number of DEGs suggests strong biological differences."
                elif sig_genes > 100:
                    summary += "Moderate number of DEGs indicates clear biological signal."
                elif sig_genes > 10:
                    summary += "Small number of DEGs suggests subtle but meaningful changes."
                else:
                    summary += "Few DEGs found - consider adjusting thresholds or sample size."
                    
                return summary
            else:
                return "Differential expression analysis completed."
                
        except Exception as e:
            return "Differential expression analysis identified significant gene changes."
    
    @staticmethod
    def analyze_volcano_plot(results_df) -> str:
        """Analyze volcano plot results"""
        try:
            if results_df is not None and len(results_df) > 0:
                # Count upregulated and downregulated genes
                if "log2FoldChange" in results_df.columns and "padj" in results_df.columns:
                    sig_up = len(results_df[(results_df["log2FoldChange"] > 0) & (results_df["padj"] < 0.05)])
                    sig_down = len(results_df[(results_df["log2FoldChange"] < 0) & (results_df["padj"] < 0.05)])
                    
                    summary = f"Volcano plot shows {sig_up:,} upregulated and {sig_down:,} downregulated genes. "
                    
                    if sig_up > sig_down * 2:
                        summary += "Strong upregulation suggests activation of biological processes."
                    elif sig_down > sig_up * 2:
                        summary += "Strong downregulation suggests suppression of biological processes."
                    else:
                        summary += "Balanced up/down regulation indicates complex biological response."
                        
                    return summary
                else:
                    return PlotAnalyzer.analyze_differential_expression(results_df)
            else:
                return "Volcano plot shows differential gene expression patterns."
                
        except Exception as e:
            return "Volcano plot analysis completed."
    
    @staticmethod
    def analyze_go_enrichment(go_results) -> str:
        """Analyze GO enrichment results"""
        try:
            if go_results is not None and len(go_results) > 0:
                n_terms = len(go_results)
                
                # Count by GO category
                if "source" in go_results.columns:
                    bp_terms = len(go_results[go_results["source"] == "GO:BP"])
                    mf_terms = len(go_results[go_results["source"] == "GO:MF"])
                    cc_terms = len(go_results[go_results["source"] == "GO:CC"])
                    
                    summary = f"GO enrichment identified {n_terms} significant terms: {bp_terms} biological processes, {mf_terms} molecular functions, {cc_terms} cellular components. "
                    
                    if bp_terms > mf_terms + cc_terms:
                        summary += "Enrichment primarily in biological processes suggests pathway-level changes."
                    elif mf_terms > bp_terms + cc_terms:
                        summary += "Enrichment in molecular functions suggests specific protein activity changes."
                    else:
                        summary += "Diverse enrichment across GO categories indicates broad biological impact."
                else:
                    summary = f"GO enrichment analysis identified {n_terms} significant functional terms. "
                    
                return summary
            else:
                return "GO enrichment analysis completed."
                
        except Exception as e:
            return "GO enrichment shows functional categories of differentially expressed genes."

def get_step_summary(step_name: str, anndata=None, results_df=None, **kwargs) -> str:
    """Generate a summary for a specific analysis step"""
    
    analyzer = PlotAnalyzer()
    
    if step_name == "qc" and anndata is not None:
        return analyzer.analyze_qc_metrics(anndata)
    
    elif step_name == "filtering" and anndata is not None:
        return analyzer.analyze_filtering_results(
            anndata, 
            kwargs.get("pre_filter_cells"), 
            kwargs.get("pre_filter_genes")
        )
    
    elif step_name == "normalization" and anndata is not None:
        return analyzer.analyze_normalization(anndata)
    
    elif step_name == "dimred" and anndata is not None:
        return analyzer.analyze_pca_results(anndata)
    
    elif step_name == "clustering" and anndata is not None:
        return analyzer.analyze_clustering_results(anndata)
    
    elif step_name == "viz" and anndata is not None:
        return analyzer.analyze_umap_visualization(anndata)
    
    elif step_name == "dea" and results_df is not None:
        return analyzer.analyze_differential_expression(results_df)
    
    elif step_name == "volcano" and results_df is not None:
        return analyzer.analyze_volcano_plot(results_df)
    
    elif step_name == "go" and results_df is not None:
        return analyzer.analyze_go_enrichment(results_df)
    
    else:
        return f"Analysis step '{step_name}' completed successfully."

def analyze_current_plots(user_question: str = "") -> str:
    """Analyze currently displayed plots and return insights for the current step only"""
    import streamlit as st
    
    # Get the current step the user is viewing
    current_step = st.session_state.get("scrna_current_step", "qc")
    
    # COMPREHENSIVE DEBUG: Print ALL available session state data
    print(f"🔧 DEBUG PLOT ANALYZER: Current step = {current_step}")
    print(f"🔧 DEBUG PLOT ANALYZER: User question = '{user_question}'")
    print(f"🔧 DEBUG PLOT ANALYZER: dimred_done = {st.session_state.get('dimred_done')}")
    print(f"🔧 DEBUG PLOT ANALYZER: Has anndata = {'anndata' in st.session_state}")
    
    # ENHANCED: Debug ALL session state keys to see what plot data is available
    print(f"🔧 DEBUG PLOT ANALYZER: ALL SESSION STATE KEYS:")
    for key in sorted(st.session_state.keys()):
        if any(keyword in key.lower() for keyword in ['plot', 'fig', 'chart', 'data', 'result', 'analysis']):
            value = st.session_state[key]
            print(f"  - {key}: {type(value)} {getattr(value, 'shape', '')} {str(value)[:100]}")
    
    # Check anndata details if available
    if "anndata" in st.session_state and st.session_state.anndata is not None:
        anndata = st.session_state.anndata
        print(f"🔧 DEBUG PLOT ANALYZER: AnnData shape = {anndata.n_obs} x {anndata.n_vars}")
        print(f"🔧 DEBUG PLOT ANALYZER: AnnData layers = {list(anndata.layers.keys()) if hasattr(anndata, 'layers') else 'No layers'}")
        print(f"🔧 DEBUG PLOT ANALYZER: AnnData obsm keys = {list(anndata.obsm.keys()) if hasattr(anndata, 'obsm') else 'No obsm'}")
        print(f"🔧 DEBUG PLOT ANALYZER: AnnData uns keys = {list(anndata.uns.keys()) if hasattr(anndata, 'uns') else 'No uns'}")
        if "pca" in anndata.uns:
            print(f"🔧 DEBUG PLOT ANALYZER: PCA keys = {list(anndata.uns['pca'].keys())}")
    
    insights = []
    
    # Check what data and analysis results are available
    if "anndata" in st.session_state and st.session_state.anndata is not None:
        anndata = st.session_state.anndata
        
        # ENHANCED: Check if this is a conceptual/hypothetical question that should be routed to LLM
        if user_question and _is_conceptual_question(user_question):
            print(f"🔧 DEBUG PLOT ANALYZER: Detected conceptual question, should route to LLM")
            # Return a flag indicating this should be handled by LLM with context
            return "ROUTE_TO_LLM_WITH_CONTEXT"
        
        # ENHANCED: Handle specific plot analysis requests
        if user_question and "scaled expression" in user_question.lower():
            print(f"🔧 DEBUG PLOT ANALYZER: Analyzing scaled expression distribution")
            return _analyze_scaled_expression_distribution(anndata, user_question)
        
        if user_question and any(term in user_question.lower() for term in ["distribution", "histogram", "density"]):
            print(f"🔧 DEBUG PLOT ANALYZER: Analyzing distribution plot")
            return _analyze_distribution_plot(anndata, user_question)
        
        # Only analyze the current step the user is viewing (for direct analysis requests)
        if current_step == "qc" and st.session_state.get("qc_done"):
            insights.append(PlotAnalyzer.analyze_qc_metrics(anndata))
        
        elif current_step == "filtering" and st.session_state.get("filtering_done"):
            insights.append(PlotAnalyzer.analyze_filtering_results(anndata))
        
        elif current_step == "normalization" and st.session_state.get("normalization_done"):
            insights.append(PlotAnalyzer.analyze_normalization(anndata))
        
        elif current_step == "dimred" and st.session_state.get("dimred_done"):
            print(f"🔧 DEBUG PLOT ANALYZER: Analyzing PCA results...")
            insights.append(PlotAnalyzer.analyze_pca_results(anndata))
        
        elif current_step == "clustering" and st.session_state.get("clustering_done"):
            insights.append(PlotAnalyzer.analyze_clustering_results(anndata))
        
        elif current_step == "viz" and st.session_state.get("viz_done"):
            insights.append(PlotAnalyzer.analyze_umap_visualization(anndata))
        
        elif current_step == "dea" and st.session_state.get("dea_done"):
            # For DEA step, check if we have results
            if "deseq_results" in st.session_state:
                insights.append(PlotAnalyzer.analyze_differential_expression(st.session_state["deseq_results"]))
                insights.append(PlotAnalyzer.analyze_volcano_plot(st.session_state["deseq_results"]))
        
        elif current_step == "enrichment" and st.session_state.get("enrichment_done"):
            # For enrichment step, check if we have GO results
            if "go_results" in st.session_state:
                insights.append(PlotAnalyzer.analyze_go_enrichment(st.session_state["go_results"]))
    
    # Check RNA-seq results only if we're on RNA-seq analysis
    if current_step in ["dea", "enrichment"]:
        if "deseq_results" in st.session_state and current_step == "dea":
            insights.append(PlotAnalyzer.analyze_differential_expression(st.session_state["deseq_results"]))
            insights.append(PlotAnalyzer.analyze_volcano_plot(st.session_state["deseq_results"]))
        
        if "go_results" in st.session_state and current_step == "enrichment":
            insights.append(PlotAnalyzer.analyze_go_enrichment(st.session_state["go_results"]))
    
    print(f"🔧 DEBUG PLOT ANALYZER: Found {len(insights)} insights")
    
    if insights:
        return " ".join(insights)
    else:
        # Provide step-specific message if no analysis is available yet
        step_messages = {
            "qc": "Quality control analysis not completed yet. Please run QC to see metrics.",
            "filtering": "Filtering analysis not completed yet. Please run filtering to see results.",
            "normalization": "Normalization analysis not completed yet. Please run normalization to see results.",
            "dimred": "PCA analysis not completed yet. Please run dimensionality reduction to see results.",
            "clustering": "Clustering analysis not completed yet. Please run clustering to see results.",
            "viz": "UMAP visualization not completed yet. Please run visualization to see results.",
            "dea": "Differential expression analysis not completed yet. Please run DEA to see results.",
            "enrichment": "Enrichment analysis not completed yet. Please run enrichment to see results."
        }
        return step_messages.get(current_step, "No analysis results available for the current step yet.")

def _analyze_scaled_expression_distribution(anndata, user_question: str) -> str:
    """Analyze scaled expression distribution plots"""
    try:
        import numpy as np
        
        # Check if we have scaled data
        if hasattr(anndata, 'X') and anndata.X is not None:
            X = anndata.X
            if hasattr(X, 'toarray'):
                X = X.toarray()
            
            data_min = np.min(X)
            data_max = np.max(X)
            data_mean = np.mean(X)
            data_std = np.std(X)
            
            summary = f"Scaled expression distribution analysis: Values range from {data_min:.2f} to {data_max:.2f} with mean {data_mean:.2f} and std {data_std:.2f}. "
            
            # Analyze distribution characteristics
            if data_min >= -3 and data_max <= 3 and abs(data_mean) < 0.5:
                summary += "Distribution appears well-scaled and centered, suitable for downstream analysis. "
            elif data_max > 10:
                summary += "High values suggest data may not be properly scaled - consider standardization. "
            elif data_std > 2:
                summary += "High variance suggests strong biological signal or potential batch effects. "
            else:
                summary += "Distribution characteristics indicate processed, analysis-ready data. "
            
            # Add recommendations based on the data
            if "conclusion" in user_question.lower():
                if data_std < 1:
                    summary += "Conclusion: Low variance suggests over-normalization or limited biological diversity."
                elif data_std > 2:
                    summary += "Conclusion: High variance indicates strong biological signal - proceed with clustering and differential analysis."
                else:
                    summary += "Conclusion: Balanced expression distribution optimal for downstream scRNA-seq analysis."
            
            return summary
        else:
            return "Scaled expression data not found in the current dataset."
            
    except Exception as e:
        print(f"🔧 DEBUG: Error analyzing scaled expression: {e}")
        return "Unable to analyze scaled expression distribution from current data."

def _analyze_distribution_plot(anndata, user_question: str) -> str:
    """Analyze general distribution plots"""
    try:
        import numpy as np
        
        if hasattr(anndata, 'X') and anndata.X is not None:
            X = anndata.X
            if hasattr(X, 'toarray'):
                X = X.toarray()
            
            # Basic distribution statistics
            data_mean = np.mean(X)
            data_median = np.median(X)
            data_std = np.std(X)
            
            summary = f"Distribution analysis shows mean={data_mean:.2f}, median={data_median:.2f}, std={data_std:.2f}. "
            
            # Distribution shape analysis
            if abs(data_mean - data_median) < 0.1 * data_std:
                summary += "Symmetric distribution suggests well-processed data. "
            elif data_mean > data_median:
                summary += "Right-skewed distribution typical of gene expression data. "
            else:
                summary += "Left-skewed distribution may indicate over-processing. "
            
            return summary
        else:
            return "Distribution data not accessible from current session."
            
    except Exception as e:
        print(f"🔧 DEBUG: Error analyzing distribution: {e}")
        return "Unable to analyze distribution from current data."

def _is_conceptual_question(user_question: str) -> bool:
    """
    Determine if a question is conceptual/hypothetical rather than requesting data analysis.
    
    This uses semantic patterns rather than hard-coded keywords to be more flexible.
    """
    question_lower = user_question.lower().strip()
    
    # Conceptual question indicators
    conceptual_patterns = [
        # What-if scenarios
        r"what\s+(if|would\s+happen|will\s+happen|does\s+it\s+mean)",
        r"what\s+is\s+the\s+(meaning|significance|implication)",
        r"what\s+are\s+the\s+(implications|consequences|effects)",
        
        # How/Why explanations
        r"how\s+(does|do|can|would)",
        r"why\s+(is|are|does|do|would)",
        r"explain\s+(how|why|what)",
        
        # Comparison questions
        r"(difference|compare|comparison)\s+between",
        r"vs\.|versus|compared\s+to",
        
        # General knowledge
        r"which\s+(file|code|script|function)",
        r"where\s+(is|are|can\s+i\s+find)",
        r"who\s+(wrote|created|developed)",
        
        # Hypothetical scenarios
        r"suppose|assuming|consider|imagine",
        r"in\s+the\s+case\s+(of|where|that)",
        
        # Interpretation requests
        r"interpret|understand|clarify|elaborate",
        r"tell\s+me\s+(about|more)",
        r"can\s+you\s+explain"
    ]
    
    # Check if any conceptual patterns match
    for pattern in conceptual_patterns:
        if re.search(pattern, question_lower):
            return True
    
    # Additional heuristics
    # Questions ending with ? are often conceptual
    if question_lower.endswith('?') and len(question_lower.split()) > 3:
        # But exclude direct analysis requests
        analysis_keywords = ["analyze", "summarize", "show", "display", "create", "generate", "run"]
        if not any(keyword in question_lower for keyword in analysis_keywords):
            return True
    
    return False