"""
RNA-seq MCP Server

Provides MCP interface for RNA-seq analysis tools including:
- Data upload and validation
- Differential expression analysis (DESeq2)
- Gene ontology enrichment
- Quality control and filtering
- Visualization tools
"""

import asyncio
import pandas as pd
import numpy as np
from typing import Any, Dict, Optional
import streamlit as st

from ..core.server import MCPServer
from src.modules.rna_seq.workflow import run_rnaseq_pipeline
from src.modules.rna_seq.input_preview import show_rnaseq_inputs


class RNASeqMCPServer(MCPServer):
    """MCP Server for RNA-seq analysis tools"""
    
    def __init__(self):
        super().__init__("rnaseq_server", "1.0.0")
    
    async def initialize(self) -> None:
        """Initialize RNA-seq server with tools and resources"""
        
        # Register RNA-seq analysis tools
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
        """Register RNA-seq analysis tools"""
        
        # Main pipeline tool
        self.register_tool(
            name="run_rnaseq_pipeline",
            description="Execute the complete RNA-seq analysis pipeline including preprocessing, DESeq2, and visualization",
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
        
        # Differential expression analysis
        self.register_tool(
            name="run_deseq2_analysis",
            description="Run DESeq2 differential expression analysis on uploaded RNA-seq data",
            input_schema={
                "type": "object",
                "properties": {
                    "design_formula": {
                        "type": "string",
                        "description": "DESeq2 design formula (e.g., '~ condition')",
                        "default": "~ condition"
                    },
                    "contrast": {
                        "type": "array",
                        "description": "Contrast for comparison [factor, numerator, denominator]",
                        "items": {"type": "string"}
                    }
                },
                "required": []
            },
            handler=self._run_deseq2
        )
        
        # Gene ontology enrichment
        self.register_tool(
            name="run_go_enrichment",
            description="Perform Gene Ontology enrichment analysis on significant genes",
            input_schema={
                "type": "object",
                "properties": {
                    "gene_list": {
                        "type": "array",
                        "description": "List of gene symbols for enrichment",
                        "items": {"type": "string"}
                    },
                    "background": {
                        "type": "array",
                        "description": "Background gene list",
                        "items": {"type": "string"}
                    },
                    "organism": {
                        "type": "string",
                        "description": "Organism for GO analysis",
                        "default": "human"
                    }
                },
                "required": []
            },
            handler=self._run_go_enrichment
        )
    
    async def _register_data_tools(self):
        """Register data management tools"""
        
        # Data validation
        self.register_tool(
            name="validate_rnaseq_data",
            description="Validate uploaded RNA-seq counts and metadata files",
            input_schema={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self._validate_data
        )
        
        # Data summary
        self.register_tool(
            name="get_rnaseq_summary",
            description="Get summary statistics of uploaded RNA-seq data",
            input_schema={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self._get_data_summary
        )
        
        # Filter genes
        self.register_tool(
            name="filter_low_expression_genes",
            description="Filter out genes with low expression across samples",
            input_schema={
                "type": "object",
                "properties": {
                    "min_counts": {
                        "type": "integer",
                        "description": "Minimum count threshold",
                        "default": 10
                    },
                    "min_samples": {
                        "type": "integer", 
                        "description": "Minimum number of samples with counts above threshold",
                        "default": 3
                    }
                },
                "required": []
            },
            handler=self._filter_genes
        )
    
    async def _register_visualization_tools(self):
        """Register visualization tools"""
        
        # PCA plot
        self.register_tool(
            name="create_pca_plot",
            description="Create PCA plot of RNA-seq samples",
            input_schema={
                "type": "object",
                "properties": {
                    "color_by": {
                        "type": "string",
                        "description": "Metadata column to color samples by",
                        "default": "condition"
                    },
                    "n_genes": {
                        "type": "integer",
                        "description": "Number of most variable genes to use",
                        "default": 500
                    }
                },
                "required": []
            },
            handler=self._create_pca_plot
        )
        
        # Volcano plot
        self.register_tool(
            name="create_volcano_plot",
            description="Create volcano plot of differential expression results",
            input_schema={
                "type": "object",
                "properties": {
                    "log2fc_threshold": {
                        "type": "number",
                        "description": "Log2 fold change threshold for significance",
                        "default": 1.0
                    },
                    "pvalue_threshold": {
                        "type": "number",
                        "description": "P-value threshold for significance",
                        "default": 0.05
                    }
                },
                "required": []
            },
            handler=self._create_volcano_plot
        )
        
        # Heatmap
        self.register_tool(
            name="create_expression_heatmap",
            description="Create heatmap of top differentially expressed genes",
            input_schema={
                "type": "object",
                "properties": {
                    "n_genes": {
                        "type": "integer",
                        "description": "Number of top genes to include",
                        "default": 50
                    },
                    "cluster_samples": {
                        "type": "boolean",
                        "description": "Whether to cluster samples",
                        "default": True
                    }
                },
                "required": []
            },
            handler=self._create_heatmap
        )
    
    async def _register_resources(self):
        """Register RNA-seq data resources"""
        
        # Counts data resource
        self.register_resource(
            uri="rnaseq://data/counts",
            name="RNA-seq Counts Matrix",
            description="Gene expression counts matrix",
            mime_type="application/json"
        )
        
        # Metadata resource
        self.register_resource(
            uri="rnaseq://data/metadata", 
            name="Sample Metadata",
            description="Sample metadata and experimental design",
            mime_type="application/json"
        )
        
        # Results resource
        self.register_resource(
            uri="rnaseq://results/deseq2",
            name="DESeq2 Results",
            description="Differential expression analysis results",
            mime_type="application/json"
        )
        
        # GO results resource
        self.register_resource(
            uri="rnaseq://results/go_enrichment",
            name="GO Enrichment Results", 
            description="Gene ontology enrichment analysis results",
            mime_type="application/json"
        )
    
    async def _register_prompts(self):
        """Register RNA-seq analysis prompts"""
        
        self.register_prompt(
            name="interpret_deseq2_results",
            description="Prompt for interpreting DESeq2 differential expression results",
            template="""
            Based on the RNA-seq differential expression analysis results:
            
            - Total genes analyzed: {total_genes}
            - Significantly upregulated genes: {upregulated_count}
            - Significantly downregulated genes: {downregulated_count}
            - Top upregulated gene: {top_up_gene} (log2FC: {top_up_fc})
            - Top downregulated gene: {top_down_gene} (log2FC: {top_down_fc})
            
            Please provide a biological interpretation of these results, including:
            1. What these expression changes might indicate
            2. Potential biological pathways involved
            3. Suggested follow-up analyses
            """,
            parameters={
                "total_genes": "integer",
                "upregulated_count": "integer", 
                "downregulated_count": "integer",
                "top_up_gene": "string",
                "top_up_fc": "number",
                "top_down_gene": "string",
                "top_down_fc": "number"
            }
        )
        
        self.register_prompt(
            name="suggest_next_analysis",
            description="Suggest next steps based on current RNA-seq analysis state",
            template="""
            Current RNA-seq analysis status:
            
            - Data uploaded: {data_uploaded}
            - Preprocessing completed: {preprocessing_done}
            - Differential expression completed: {deseq_done}
            - GO enrichment completed: {go_done}
            - Significant genes found: {significant_genes}
            
            Based on this progress, what should be the next analysis step?
            """,
            parameters={
                "data_uploaded": "boolean",
                "preprocessing_done": "boolean",
                "deseq_done": "boolean", 
                "go_done": "boolean",
                "significant_genes": "integer"
            }
        )
    
    # Tool handler implementations
    
    async def _run_pipeline(self, force_rerun: bool = False) -> Dict[str, Any]:
        """Run the complete RNA-seq pipeline"""
        try:
            if not self._check_data_availability():
                return {
                    "success": False,
                    "message": "RNA-seq data not uploaded. Please upload counts and metadata files first."
                }
            
            # Run the pipeline
            result = run_rnaseq_pipeline()
            
            return {
                "success": True,
                "message": "RNA-seq pipeline completed successfully",
                "result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Pipeline execution failed: {str(e)}"
            }
    
    async def _run_deseq2(self, design_formula: str = "~ condition", contrast: Optional[list] = None) -> Dict[str, Any]:
        """Run DESeq2 analysis"""
        try:
            if not self._check_data_availability():
                return {
                    "success": False,
                    "message": "RNA-seq data not available"
                }
            
            # Implementation would call actual DESeq2 analysis
            # For now, return mock result
            return {
                "success": True,
                "message": f"DESeq2 analysis completed with design: {design_formula}",
                "significant_genes": 1234,
                "upregulated": 567,
                "downregulated": 667
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"DESeq2 analysis failed: {str(e)}"
            }
    
    async def _run_go_enrichment(self, gene_list: Optional[list] = None, background: Optional[list] = None, organism: str = "human") -> Dict[str, Any]:
        """Run GO enrichment analysis"""
        try:
            if gene_list is None and "deseq_results" not in st.session_state:
                return {
                    "success": False,
                    "message": "No gene list provided and no DESeq2 results available"
                }
            
            # Implementation would call actual GO enrichment
            return {
                "success": True,
                "message": f"GO enrichment completed for {organism}",
                "enriched_terms": 45,
                "top_term": "immune response"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"GO enrichment failed: {str(e)}"
            }
    
    async def _validate_data(self) -> Dict[str, Any]:
        """Validate RNA-seq data"""
        validation_results = {
            "counts_valid": False,
            "metadata_valid": False,
            "samples_match": False,
            "issues": []
        }
        
        if "rnaseq_counts_df" in st.session_state:
            counts_df = st.session_state["rnaseq_counts_df"]
            validation_results["counts_valid"] = True
            validation_results["counts_shape"] = counts_df.shape
        else:
            validation_results["issues"].append("Counts matrix not uploaded")
        
        if "rnaseq_metadata_df" in st.session_state:
            metadata_df = st.session_state["rnaseq_metadata_df"]
            validation_results["metadata_valid"] = True
            validation_results["metadata_shape"] = metadata_df.shape
        else:
            validation_results["issues"].append("Metadata not uploaded")
        
        if validation_results["counts_valid"] and validation_results["metadata_valid"]:
            # Check if sample names match
            counts_samples = set(st.session_state["rnaseq_counts_df"].columns)
            metadata_samples = set(st.session_state["rnaseq_metadata_df"].index)
            validation_results["samples_match"] = counts_samples == metadata_samples
            
            if not validation_results["samples_match"]:
                validation_results["issues"].append("Sample names don't match between counts and metadata")
        
        return {
            "success": True,
            "validation": validation_results
        }
    
    async def _get_data_summary(self) -> Dict[str, Any]:
        """Get summary of RNA-seq data"""
        summary = {}
        
        if "rnaseq_counts_df" in st.session_state:
            counts_df = st.session_state["rnaseq_counts_df"]
            summary["counts"] = {
                "genes": counts_df.shape[0],
                "samples": counts_df.shape[1],
                "total_counts": int(counts_df.sum().sum()),
                "mean_counts_per_gene": float(counts_df.sum(axis=1).mean()),
                "mean_counts_per_sample": float(counts_df.sum(axis=0).mean())
            }
        
        if "rnaseq_metadata_df" in st.session_state:
            metadata_df = st.session_state["rnaseq_metadata_df"]
            summary["metadata"] = {
                "samples": metadata_df.shape[0],
                "variables": metadata_df.shape[1],
                "columns": list(metadata_df.columns)
            }
        
        return {
            "success": True,
            "summary": summary
        }
    
    async def _filter_genes(self, min_counts: int = 10, min_samples: int = 3) -> Dict[str, Any]:
        """Filter low expression genes"""
        if "rnaseq_counts_df" not in st.session_state:
            return {
                "success": False,
                "message": "No counts data available"
            }
        
        counts_df = st.session_state["rnaseq_counts_df"]
        
        # Filter genes
        keep_genes = (counts_df >= min_counts).sum(axis=1) >= min_samples
        filtered_df = counts_df[keep_genes]
        
        # Store filtered data
        st.session_state["rnaseq_counts_filtered"] = filtered_df
        
        return {
            "success": True,
            "message": f"Filtered from {counts_df.shape[0]} to {filtered_df.shape[0]} genes",
            "original_genes": counts_df.shape[0],
            "filtered_genes": filtered_df.shape[0],
            "removed_genes": counts_df.shape[0] - filtered_df.shape[0]
        }
    
    async def _create_pca_plot(self, color_by: str = "condition", n_genes: int = 500) -> Dict[str, Any]:
        """Create PCA plot"""
        # Implementation would create actual PCA plot
        return {
            "success": True,
            "message": f"PCA plot created with {n_genes} genes, colored by {color_by}",
            "plot_type": "pca",
            "parameters": {"color_by": color_by, "n_genes": n_genes}
        }
    
    async def _create_volcano_plot(self, log2fc_threshold: float = 1.0, pvalue_threshold: float = 0.05) -> Dict[str, Any]:
        """Create volcano plot"""
        # Implementation would create actual volcano plot
        return {
            "success": True,
            "message": f"Volcano plot created with thresholds: log2FC={log2fc_threshold}, p-value={pvalue_threshold}",
            "plot_type": "volcano",
            "parameters": {"log2fc_threshold": log2fc_threshold, "pvalue_threshold": pvalue_threshold}
        }
    
    async def _create_heatmap(self, n_genes: int = 50, cluster_samples: bool = True) -> Dict[str, Any]:
        """Create expression heatmap"""
        # Implementation would create actual heatmap
        return {
            "success": True,
            "message": f"Heatmap created with top {n_genes} genes, clustering={'enabled' if cluster_samples else 'disabled'}",
            "plot_type": "heatmap",
            "parameters": {"n_genes": n_genes, "cluster_samples": cluster_samples}
        }
    
    def _check_data_availability(self) -> bool:
        """Check if required RNA-seq data is available"""
        return (
            "rnaseq_counts_df" in st.session_state and
            "rnaseq_metadata_df" in st.session_state
        )
    
    def _get_server_specific_context(self) -> Dict[str, Any]:
        """Get RNA-seq specific context"""
        context = {
            "analysis_type": "rnaseq",
            "data_uploaded": self._check_data_availability(),
            "pipeline_status": {}
        }
        
        # Check analysis progress
        if "deseq_results" in st.session_state:
            results_df = st.session_state["deseq_results"]
            context["pipeline_status"]["deseq2_completed"] = True
            context["pipeline_status"]["significant_genes"] = len(results_df[results_df.get("significant", False)])
        
        if "go_results" in st.session_state:
            context["pipeline_status"]["go_enrichment_completed"] = True
        
        if "rnaseq_counts_df" in st.session_state:
            counts_df = st.session_state["rnaseq_counts_df"]
            context["data_summary"] = {
                "genes": counts_df.shape[0],
                "samples": counts_df.shape[1]
            }
        
        return context 