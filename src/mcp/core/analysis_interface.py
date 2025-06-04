"""
Analysis Interface

Common interface for analysis insights and suggested actions across all MCP servers.
This eliminates redundancy and provides a consistent API.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
import streamlit as st


class AnalysisProvider(ABC):
    """Abstract interface for providing analysis insights and suggested actions"""
    
    @abstractmethod
    def get_analysis_insights(self) -> str:
        """Get current analysis insights as a formatted string"""
        pass
    
    @abstractmethod
    def get_suggested_actions(self) -> List[str]:
        """Get suggested next actions as a list of strings"""
        pass
    
    @abstractmethod
    def get_analysis_context(self) -> Dict[str, Any]:
        """Get full analysis context for the registry"""
        pass


class BaseAnalysisProvider(AnalysisProvider):
    """Base implementation with common functionality"""
    
    def __init__(self, server_type: str):
        self.server_type = server_type
    
    def get_analysis_insights(self) -> str:
        """Default implementation - override in specific providers"""
        return f"No {self.server_type} analysis insights available"
    
    def get_suggested_actions(self) -> List[str]:
        """Default implementation - override in specific providers"""
        return [f"Start {self.server_type} analysis"]
    
    def get_analysis_context(self) -> Dict[str, Any]:
        """Get basic analysis context"""
        return {
            "server_type": self.server_type,
            "data_uploaded": self._check_data_uploaded(),
            "analysis_insights": self.get_analysis_insights(),
            "suggested_actions": self.get_suggested_actions()
        }
    
    def _check_data_uploaded(self) -> bool:
        """Check if any data is uploaded - override in specific providers"""
        return False


class scRNASeqAnalysisProvider(BaseAnalysisProvider):
    """scRNA-seq specific analysis provider"""
    
    def __init__(self):
        super().__init__("scrnaseq")
    
    def get_analysis_insights(self) -> str:
        """Get scRNA-seq specific analysis insights"""
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
        
        return "; ".join(insights) if insights else "No scRNA-seq analysis insights available"
    
    def get_suggested_actions(self) -> List[str]:
        """Get scRNA-seq specific suggested actions"""
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
    
    def get_analysis_context(self) -> Dict[str, Any]:
        """Get scRNA-seq specific analysis context"""
        context = super().get_analysis_context()
        
        # Add scRNA-seq specific context
        if "anndata" in st.session_state and st.session_state.anndata is not None:
            context["data_uploaded"] = True
            adata = st.session_state.anndata
            context["data_summary"] = {
                "n_cells": adata.n_obs,
                "n_genes": adata.n_vars,
                "shape": adata.shape
            }
            
            # Pipeline status
            pipeline_steps = [
                "input_summary", "qc", "filtering", "normalization", 
                "dimred", "clustering", "viz", "dea", "enrichment", 
                "markers", "trajectory", "ml"
            ]
            
            context["pipeline_status"] = {}
            for step in pipeline_steps:
                done_flag = f"{step}_done"
                context["pipeline_status"][step] = st.session_state.get(done_flag, False)
            
            context["current_step"] = st.session_state.get("scrna_current_step", "input_summary")
        
        return context
    
    def _check_data_uploaded(self) -> bool:
        """Check if scRNA-seq data is uploaded"""
        return "anndata" in st.session_state and st.session_state.anndata is not None


class ATACSeqAnalysisProvider(BaseAnalysisProvider):
    """ATAC-seq specific analysis provider"""
    
    def __init__(self):
        super().__init__("atacseq")
    
    def get_analysis_insights(self) -> str:
        """Get ATAC-seq specific analysis insights"""
        # Implementation would be similar to scRNA-seq but for ATAC-seq data
        return "ATAC-seq analysis insights would go here"
    
    def get_suggested_actions(self) -> List[str]:
        """Get ATAC-seq specific suggested actions"""
        # Implementation would be similar to scRNA-seq but for ATAC-seq workflow
        return ["Start ATAC-seq analysis workflow"]


# Registry for analysis providers
analysis_providers = {
    "scrnaseq": scRNASeqAnalysisProvider,
    "atacseq": ATACSeqAnalysisProvider,
}


def get_analysis_provider(server_type: str) -> AnalysisProvider:
    """Factory function to get analysis provider for a server type"""
    provider_class = analysis_providers.get(server_type, BaseAnalysisProvider)
    
    if provider_class == BaseAnalysisProvider:
        return provider_class(server_type)
    else:
        return provider_class()


def register_analysis_provider(server_type: str, provider_class: type):
    """Register a new analysis provider for a server type"""
    analysis_providers[server_type] = provider_class 