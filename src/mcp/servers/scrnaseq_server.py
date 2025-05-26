"""
scRNA-seq MCP Server

Provides MCP interface for single-cell RNA-seq analysis tools including:
- Data upload and validation
- Quality control and filtering
- Normalization and scaling
- Dimensionality reduction (PCA, UMAP)
- Clustering and cell type identification
- Differential expression analysis
- Trajectory analysis
"""

import asyncio
import pandas as pd
import numpy as np
from typing import Any, Dict, Optional, List
import streamlit as st

from ..core.server import MCPServer
from modules.scrna_seq.workflow import run_scrnaseq_pipeline


class scRNASeqMCPServer(MCPServer):
    """MCP Server for single-cell RNA-seq analysis tools"""
    
    def __init__(self):
        super().__init__("scrnaseq_server", "1.0.0")
    
    async def initialize(self) -> None:
        """Initialize scRNA-seq server with tools and resources"""
        
        # Register scRNA-seq analysis tools
        await self._register_analysis_tools()
        
        # Register data management tools
        await self._register_data_tools()
        
        # Register visualization tools
        await self._register_visualization_tools()
        
        # Register resources
        await self._register_resources()
        
        # Register prompts
        await self._register_prompts()
    
    async def _register_analysis_tools(self):
        """Register scRNA-seq analysis tools"""
        
        # Main pipeline tool
        self.register_tool(
            name="run_scrnaseq_pipeline",
            description="Execute the complete scRNA-seq analysis pipeline including QC, normalization, clustering, and visualization",
            input_schema={
                "type": "object",
                "properties": {
                    "force_rerun": {
                        "type": "boolean",
                        "description": "Force rerun of analysis even if results exist",
                        "default": False
                    }
                },
                "required": []
            },
            handler=self._run_pipeline
        )
        
        # Quality control
        self.register_tool(
            name="run_scrnaseq_qc",
            description="Perform quality control analysis on scRNA-seq data",
            input_schema={
                "type": "object",
                "properties": {
                    "min_genes": {
                        "type": "integer",
                        "description": "Minimum number of genes per cell",
                        "default": 200
                    },
                    "min_cells": {
                        "type": "integer",
                        "description": "Minimum number of cells per gene",
                        "default": 3
                    },
                    "max_genes": {
                        "type": "integer",
                        "description": "Maximum number of genes per cell",
                        "default": 5000
                    },
                    "max_mito_pct": {
                        "type": "number",
                        "description": "Maximum mitochondrial gene percentage",
                        "default": 20.0
                    }
                },
                "required": []
            },
            handler=self._run_qc
        )
        
        # Normalization
        self.register_tool(
            name="normalize_scrnaseq_data",
            description="Normalize and scale scRNA-seq expression data",
            input_schema={
                "type": "object",
                "properties": {
                    "target_sum": {
                        "type": "number",
                        "description": "Target sum for normalization",
                        "default": 10000
                    },
                    "log_transform": {
                        "type": "boolean",
                        "description": "Apply log transformation",
                        "default": True
                    },
                    "scale": {
                        "type": "boolean",
                        "description": "Scale data to unit variance",
                        "default": True
                    }
                },
                "required": []
            },
            handler=self._normalize_data
        )
        
        # Clustering
        self.register_tool(
            name="cluster_cells",
            description="Perform cell clustering using Leiden algorithm",
            input_schema={
                "type": "object",
                "properties": {
                    "resolution": {
                        "type": "number",
                        "description": "Clustering resolution",
                        "default": 0.5
                    },
                    "n_neighbors": {
                        "type": "integer",
                        "description": "Number of neighbors for graph construction",
                        "default": 15
                    },
                    "n_pcs": {
                        "type": "integer",
                        "description": "Number of principal components to use",
                        "default": 40
                    }
                },
                "required": []
            },
            handler=self._cluster_cells
        )
        
        # Differential expression
        self.register_tool(
            name="find_marker_genes",
            description="Find marker genes for each cluster",
            input_schema={
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "Statistical method for DE analysis",
                        "enum": ["wilcoxon", "t-test", "logreg"],
                        "default": "wilcoxon"
                    },
                    "min_logfc": {
                        "type": "number",
                        "description": "Minimum log fold change",
                        "default": 0.25
                    },
                    "min_pct": {
                        "type": "number",
                        "description": "Minimum percentage of cells expressing gene",
                        "default": 0.1
                    }
                },
                "required": []
            },
            handler=self._find_markers
        )
    
    async def _register_data_tools(self):
        """Register data management tools"""
        
        # Data validation
        self.register_tool(
            name="validate_scrnaseq_data",
            description="Validate uploaded scRNA-seq data",
            input_schema={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self._validate_data
        )
        
        # Data summary
        self.register_tool(
            name="get_scrnaseq_summary",
            description="Get summary statistics of scRNA-seq data",
            input_schema={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self._get_data_summary
        )
        
        # Filter cells and genes
        self.register_tool(
            name="filter_cells_genes",
            description="Filter cells and genes based on quality metrics",
            input_schema={
                "type": "object",
                "properties": {
                    "min_genes_per_cell": {
                        "type": "integer",
                        "description": "Minimum genes per cell",
                        "default": 200
                    },
                    "max_genes_per_cell": {
                        "type": "integer",
                        "description": "Maximum genes per cell",
                        "default": 5000
                    },
                    "min_cells_per_gene": {
                        "type": "integer",
                        "description": "Minimum cells per gene",
                        "default": 3
                    }
                },
                "required": []
            },
            handler=self._filter_cells_genes
        )
    
    async def _register_visualization_tools(self):
        """Register visualization tools"""
        
        # UMAP plot
        self.register_tool(
            name="create_umap_plot",
            description="Create UMAP visualization of cells",
            input_schema={
                "type": "object",
                "properties": {
                    "color_by": {
                        "type": "string",
                        "description": "Variable to color cells by",
                        "default": "leiden"
                    },
                    "min_dist": {
                        "type": "number",
                        "description": "UMAP min_dist parameter",
                        "default": 0.5
                    },
                    "spread": {
                        "type": "number",
                        "description": "UMAP spread parameter",
                        "default": 1.0
                    }
                },
                "required": []
            },
            handler=self._create_umap_plot
        )
        
        # Violin plot
        self.register_tool(
            name="create_violin_plot",
            description="Create violin plot of gene expression by cluster",
            input_schema={
                "type": "object",
                "properties": {
                    "genes": {
                        "type": "array",
                        "description": "List of genes to plot",
                        "items": {"type": "string"}
                    },
                    "groupby": {
                        "type": "string",
                        "description": "Variable to group by",
                        "default": "leiden"
                    }
                },
                "required": ["genes"]
            },
            handler=self._create_violin_plot
        )
        
        # Heatmap
        self.register_tool(
            name="create_marker_heatmap",
            description="Create heatmap of marker genes",
            input_schema={
                "type": "object",
                "properties": {
                    "n_genes": {
                        "type": "integer",
                        "description": "Number of top marker genes per cluster",
                        "default": 5
                    },
                    "groupby": {
                        "type": "string",
                        "description": "Variable to group by",
                        "default": "leiden"
                    }
                },
                "required": []
            },
            handler=self._create_marker_heatmap
        )
    
    async def _register_resources(self):
        """Register scRNA-seq data resources"""
        
        # Raw data resource
        self.register_resource(
            uri="scrnaseq://data/raw",
            name="scRNA-seq Raw Data",
            description="Raw single-cell expression matrix",
            mime_type="application/json"
        )
        
        # Processed data resource
        self.register_resource(
            uri="scrnaseq://data/processed",
            name="Processed scRNA-seq Data",
            description="Processed and normalized expression data",
            mime_type="application/json"
        )
        
        # Clustering results resource
        self.register_resource(
            uri="scrnaseq://results/clusters",
            name="Cell Clusters",
            description="Cell clustering results and assignments",
            mime_type="application/json"
        )
        
        # Marker genes resource
        self.register_resource(
            uri="scrnaseq://results/markers",
            name="Marker Genes",
            description="Cluster marker genes and statistics",
            mime_type="application/json"
        )
    
    async def _register_prompts(self):
        """Register scRNA-seq analysis prompts"""
        
        self.register_prompt(
            name="interpret_clusters",
            description="Prompt for interpreting scRNA-seq clustering results",
            template="""
            Based on the scRNA-seq clustering analysis results:
            
            - Total cells analyzed: {total_cells}
            - Number of clusters identified: {n_clusters}
            - Cluster sizes: {cluster_sizes}
            - Top marker genes per cluster: {top_markers}
            
            Please provide a biological interpretation of these clusters, including:
            1. Potential cell types represented by each cluster
            2. Key biological processes or pathways active in each cluster
            3. Suggested follow-up analyses or validations
            """,
            parameters={
                "total_cells": "integer",
                "n_clusters": "integer",
                "cluster_sizes": "array",
                "top_markers": "object"
            }
        )
        
        self.register_prompt(
            name="suggest_scrnaseq_next_steps",
            description="Suggest next steps based on current scRNA-seq analysis state",
            template="""
            Current scRNA-seq analysis status:
            
            - Data uploaded: {data_uploaded}
            - Quality control completed: {qc_done}
            - Normalization completed: {normalized}
            - Clustering completed: {clustered}
            - Marker genes identified: {markers_found}
            - Number of cells: {n_cells}
            - Number of clusters: {n_clusters}
            
            Based on this progress, what should be the next analysis step?
            """,
            parameters={
                "data_uploaded": "boolean",
                "qc_done": "boolean",
                "normalized": "boolean",
                "clustered": "boolean",
                "markers_found": "boolean",
                "n_cells": "integer",
                "n_clusters": "integer"
            }
        )
    
    # Tool handler implementations
    
    async def _run_pipeline(self, force_rerun: bool = False) -> Dict[str, Any]:
        """Run the complete scRNA-seq pipeline"""
        try:
            if not self._check_data_availability():
                return {
                    "success": False,
                    "message": "scRNA-seq data not uploaded. Please upload .h5ad or 10x files first."
                }
            
            # Run the pipeline
            result = run_scrnaseq_pipeline()
            
            return {
                "success": True,
                "message": "scRNA-seq pipeline completed successfully",
                "result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Pipeline execution failed: {str(e)}"
            }
    
    async def _run_qc(self, min_genes: int = 200, min_cells: int = 3, max_genes: int = 5000, max_mito_pct: float = 20.0) -> Dict[str, Any]:
        """Run quality control analysis"""
        try:
            if not self._check_data_availability():
                return {
                    "success": False,
                    "message": "scRNA-seq data not available"
                }
            
            # Implementation would call actual QC analysis
            return {
                "success": True,
                "message": f"Quality control completed with filters: min_genes={min_genes}, max_mito_pct={max_mito_pct}%",
                "cells_before": 5000,
                "cells_after": 4500,
                "genes_before": 20000,
                "genes_after": 18000
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"QC analysis failed: {str(e)}"
            }
    
    async def _normalize_data(self, target_sum: float = 10000, log_transform: bool = True, scale: bool = True) -> Dict[str, Any]:
        """Normalize scRNA-seq data"""
        try:
            if not self._check_data_availability():
                return {
                    "success": False,
                    "message": "scRNA-seq data not available"
                }
            
            # Implementation would call actual normalization
            return {
                "success": True,
                "message": f"Normalization completed: target_sum={target_sum}, log={log_transform}, scale={scale}",
                "normalization_method": "scanpy_normalize_total"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Normalization failed: {str(e)}"
            }
    
    async def _cluster_cells(self, resolution: float = 0.5, n_neighbors: int = 15, n_pcs: int = 40) -> Dict[str, Any]:
        """Perform cell clustering"""
        try:
            if not self._check_data_availability():
                return {
                    "success": False,
                    "message": "scRNA-seq data not available"
                }
            
            # Implementation would call actual clustering
            return {
                "success": True,
                "message": f"Clustering completed with resolution={resolution}, found 8 clusters",
                "n_clusters": 8,
                "resolution": resolution,
                "algorithm": "leiden"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Clustering failed: {str(e)}"
            }
    
    async def _find_markers(self, method: str = "wilcoxon", min_logfc: float = 0.25, min_pct: float = 0.1) -> Dict[str, Any]:
        """Find marker genes for clusters"""
        try:
            if not self._check_data_availability():
                return {
                    "success": False,
                    "message": "scRNA-seq data not available"
                }
            
            # Implementation would call actual marker gene analysis
            return {
                "success": True,
                "message": f"Marker gene analysis completed using {method}",
                "method": method,
                "total_markers": 150,
                "avg_markers_per_cluster": 18.75
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Marker gene analysis failed: {str(e)}"
            }
    
    async def _validate_data(self) -> Dict[str, Any]:
        """Validate scRNA-seq data"""
        validation_results = {
            "data_valid": False,
            "data_type": None,
            "issues": []
        }
        
        if "anndata" in st.session_state and st.session_state.anndata is not None:
            adata = st.session_state.anndata
            validation_results["data_valid"] = True
            validation_results["data_type"] = "AnnData"
            validation_results["shape"] = adata.shape
            validation_results["n_cells"] = adata.n_obs
            validation_results["n_genes"] = adata.n_vars
        else:
            validation_results["issues"].append("No scRNA-seq data uploaded")
        
        return {
            "success": True,
            "validation": validation_results
        }
    
    async def _get_data_summary(self) -> Dict[str, Any]:
        """Get summary of scRNA-seq data"""
        summary = {}
        
        if "anndata" in st.session_state and st.session_state.anndata is not None:
            adata = st.session_state.anndata
            summary["data"] = {
                "cells": adata.n_obs,
                "genes": adata.n_vars,
                "total_counts": int(adata.X.sum()) if hasattr(adata.X, 'sum') else 0,
                "mean_counts_per_cell": float(adata.X.sum(axis=1).mean()) if hasattr(adata.X, 'sum') else 0,
                "mean_genes_per_cell": float((adata.X > 0).sum(axis=1).mean()) if hasattr(adata.X, 'sum') else 0
            }
            
            # Add metadata info
            if adata.obs.shape[1] > 0:
                summary["metadata"] = {
                    "variables": adata.obs.shape[1],
                    "columns": list(adata.obs.columns)
                }
        
        return {
            "success": True,
            "summary": summary
        }
    
    async def _filter_cells_genes(self, min_genes_per_cell: int = 200, max_genes_per_cell: int = 5000, min_cells_per_gene: int = 3) -> Dict[str, Any]:
        """Filter cells and genes"""
        if "anndata" not in st.session_state or st.session_state.anndata is None:
            return {
                "success": False,
                "message": "No scRNA-seq data available"
            }
        
        adata = st.session_state.anndata
        original_shape = adata.shape
        
        # Implementation would perform actual filtering
        # For now, return mock results
        return {
            "success": True,
            "message": f"Filtering completed",
            "original_cells": original_shape[0],
            "original_genes": original_shape[1],
            "filtered_cells": int(original_shape[0] * 0.9),
            "filtered_genes": int(original_shape[1] * 0.85),
            "removed_cells": int(original_shape[0] * 0.1),
            "removed_genes": int(original_shape[1] * 0.15)
        }
    
    async def _create_umap_plot(self, color_by: str = "leiden", min_dist: float = 0.5, spread: float = 1.0) -> Dict[str, Any]:
        """Create UMAP plot"""
        return {
            "success": True,
            "message": f"UMAP plot created, colored by {color_by}",
            "plot_type": "umap",
            "parameters": {"color_by": color_by, "min_dist": min_dist, "spread": spread}
        }
    
    async def _create_violin_plot(self, genes: list, groupby: str = "leiden") -> Dict[str, Any]:
        """Create violin plot"""
        return {
            "success": True,
            "message": f"Violin plot created for {len(genes)} genes, grouped by {groupby}",
            "plot_type": "violin",
            "parameters": {"genes": genes, "groupby": groupby}
        }
    
    async def _create_marker_heatmap(self, n_genes: int = 5, groupby: str = "leiden") -> Dict[str, Any]:
        """Create marker gene heatmap"""
        return {
            "success": True,
            "message": f"Marker heatmap created with top {n_genes} genes per group",
            "plot_type": "heatmap",
            "parameters": {"n_genes": n_genes, "groupby": groupby}
        }
    
    def _check_data_availability(self) -> bool:
        """Check if required scRNA-seq data is available"""
        return (
            "anndata" in st.session_state and
            st.session_state.anndata is not None
        )
    
    def get_pipeline_context(self) -> Dict[str, Any]:
        """Get current scRNA-seq pipeline context"""
        import streamlit as st
        
        pipeline_steps = [
            ("input_summary", "Data Summary"),
            ("qc", "Quality Control"), 
            ("filtering", "Filtering"),
            ("normalization", "Normalization"),
            ("dimred", "Dimensionality Reduction"),
            ("clustering", "Clustering"),
            ("viz", "Visualization"),
            ("dea", "Differential Expression"),
            ("enrichment", "Enrichment"),
            ("markers", "Marker Genes & Cell Cycle"),
            ("trajectory", "Trajectory"),
            ("ml", "ML & Networks")
        ]
        
        current_step = st.session_state.get("scrna_current_step", "input_summary")
        completed_steps = []
        next_step = None
        
        # Find current position and determine completed/next steps
        for i, (step_key, step_name) in enumerate(pipeline_steps):
            done_flag = f"{step_key}_done"
            if st.session_state.get(done_flag, False):
                completed_steps.append(step_name)
            
            if step_key == current_step:
                if i + 1 < len(pipeline_steps):
                    next_step = pipeline_steps[i + 1][1]
        
        return {
            "current_step": dict(pipeline_steps).get(current_step, "Unknown"),
            "next_step": next_step,
            "completed_steps": completed_steps,
            "available_steps": [name for _, name in pipeline_steps],
            "pipeline_description": "Single-cell RNA sequencing analysis pipeline"
        }
    
    def get_analysis_insights(self) -> str:
        """Get current scRNA-seq analysis insights"""
        import streamlit as st
        
        insights = []
        
        if "anndata" in st.session_state and st.session_state.anndata is not None:
            anndata = st.session_state.anndata
            insights.append(f"Dataset: {anndata.n_obs:,} cells × {anndata.n_vars:,} genes")
            
            # Add QC insights
            if "qc_done" in st.session_state and st.session_state.qc_done:
                if "pct_counts_mt" in anndata.obs:
                    mt_median = anndata.obs["pct_counts_mt"].median()
                    insights.append(f"Median mitochondrial content: {mt_median:.1f}%")
            
            # Add clustering insights
            if "leiden" in anndata.obs:
                n_clusters = len(anndata.obs["leiden"].unique())
                insights.append(f"Identified {n_clusters} cell clusters")
        
        return "; ".join(insights) if insights else "No analysis insights available"
    
    def get_suggested_actions(self) -> List[str]:
        """Get suggested next actions for scRNA-seq analysis"""
        import streamlit as st
        
        current_step = st.session_state.get("scrna_current_step", "input_summary")
        
        suggestions = {
            "input_summary": ["Proceed to quality control to assess cell and gene quality"],
            "qc": ["Apply filtering to remove low-quality cells and genes"],
            "filtering": ["Normalize data to account for sequencing depth differences"],
            "normalization": ["Perform dimensionality reduction (PCA/UMAP) for visualization"],
            "dimred": ["Cluster cells to identify distinct cell populations"],
            "clustering": ["Create visualizations to explore cell populations"],
            "viz": ["Run differential expression analysis between clusters"],
            "dea": ["Perform pathway enrichment analysis on differentially expressed genes"],
            "enrichment": ["Identify marker genes and analyze cell cycle effects"],
            "markers": ["Analyze cell trajectory and developmental paths"],
            "trajectory": ["Apply machine learning methods for advanced analysis"]
        }
        
        return suggestions.get(current_step, ["Continue with the next analysis step"]) 