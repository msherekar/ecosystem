"""
Analysis Handlers

Modular analysis handlers for different analysis types.
This separates analysis logic from the main handler file.
"""

import asyncio
import streamlit as st
from typing import Any, Dict, List
from ..core.tool_registry import mcp_tool
from .base_handler import BaseHandler


class AnalysisHandlerMixin:
    """Mixin providing analysis-related handlers"""
    
    @mcp_tool(
        description="Execute the complete analysis pipeline including QC, normalization, clustering, and visualization",
        category="analysis"
    )
    async def run_pipeline(self, force_rerun: bool = False):
        """Execute the complete analysis pipeline"""
        try:
            # Get technique-specific pipeline function
            pipeline_func = self._get_pipeline_function()
            
            # Call actual pipeline
            result = await asyncio.to_thread(pipeline_func, force_rerun)
            
            return self._create_success_response(
                "Pipeline completed successfully",
                result=result,
                execution_time=result.get("execution_time"),
                steps_completed=result.get("steps_completed", [])
            )
        except Exception as e:
            return self._create_error_response(f"Pipeline failed: {str(e)}")
    
    @mcp_tool(
        description="Perform quality control analysis",
        category="analysis"
    )
    async def run_qc(self, min_genes: int = 200, min_cells: int = 3, 
                     max_genes: int = 5000, max_mito_pct: float = 20.0):
        """Perform quality control analysis"""
        self._log_operation("QC", min_genes=min_genes, max_mito_pct=max_mito_pct)
        
        # Validate parameters
        validation = self._validate_qc_parameters(min_genes, min_cells, max_genes, max_mito_pct)
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        try:
            # Perform technique-specific QC
            result = await self._perform_qc(min_genes, min_cells, max_genes, max_mito_pct)
            
            # Update progress
            self._update_progress("qc", True)
            
            return self._create_success_response(
                "QC completed",
                **result,
                progress_updated=True,
                next_step="filtering"
            )
        except Exception as e:
            return self._create_error_response(f"QC failed: {str(e)}")
    
    @mcp_tool(
        description="Normalize and scale expression data",
        category="analysis"
    )
    async def normalize_data(self, target_sum: float = 10000, log_transform: bool = True, 
                           scale: bool = True) -> Dict[str, Any]:
        """Normalize data"""
        self._log_operation("Normalization", target_sum=target_sum, log=log_transform, scale=scale)
        
        try:
            result = await self._perform_normalization(target_sum, log_transform, scale)
            self._update_progress("normalization", True)
            
            return self._create_success_response(
                f"Normalization completed: target_sum={target_sum}, log={log_transform}, scale={scale}",
                normalization_method=result.get("method", "standard"),
                **result
            )
        except Exception as e:
            return self._create_error_response(f"Normalization failed: {str(e)}")
    
    @mcp_tool(
        description="Perform cell clustering (requires normalization)",
        category="analysis"
    )
    async def cluster_cells(self, resolution: float = 0.5, n_neighbors: int = 15, n_pcs: int = 40):
        """Perform cell clustering"""
        # Validate parameters using base class method
        validation = self._validate_parameters(
            resolution=resolution, 
            n_neighbors=n_neighbors, 
            n_pcs=n_pcs
        )
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        self._log_operation("Clustering", resolution=resolution, n_neighbors=n_neighbors, n_pcs=n_pcs)
        
        try:
            result = await self._perform_clustering(resolution, n_neighbors, n_pcs)
            self._update_progress("clustering", True)
            
            return self._create_success_response(
                f"Clustering completed with resolution={resolution}, found {result.get('n_clusters', 'unknown')} clusters",
                n_clusters=result.get("n_clusters"),
                resolution=resolution,
                algorithm=result.get("algorithm", "leiden")
            )
        except Exception as e:
            return self._create_error_response(f"Clustering failed: {str(e)}")
    
    @mcp_tool(
        description="Find marker genes/features for each cluster",
        category="analysis"
    )
    async def find_markers(self, method: str = "wilcoxon", min_logfc: float = 0.25, 
                          min_pct: float = 0.1) -> Dict[str, Any]:
        """Find marker genes for clusters"""
        self._log_operation("Marker analysis", method=method, min_logfc=min_logfc, min_pct=min_pct)
        
        try:
            result = await self._perform_marker_analysis(method, min_logfc, min_pct)
            self._update_progress("markers", True)
            
            return self._create_success_response(
                f"Marker analysis completed using {method}",
                method=method,
                total_markers=result.get("total_markers"),
                avg_markers_per_cluster=result.get("avg_markers_per_cluster")
            )
        except Exception as e:
            return self._create_error_response(f"Marker analysis failed: {str(e)}")
    
    # Abstract methods that must be implemented by technique-specific handlers
    def _get_pipeline_function(self):
        """Get the pipeline function for this technique"""
        raise NotImplementedError("Subclasses must implement _get_pipeline_function")
    
    async def _perform_qc(self, min_genes, min_cells, max_genes, max_mito_pct):
        """Perform technique-specific QC"""
        raise NotImplementedError("Subclasses must implement _perform_qc")
    
    async def _perform_normalization(self, target_sum, log_transform, scale):
        """Perform technique-specific normalization"""
        raise NotImplementedError("Subclasses must implement _perform_normalization")
    
    async def _perform_clustering(self, resolution, n_neighbors, n_pcs):
        """Perform technique-specific clustering"""
        raise NotImplementedError("Subclasses must implement _perform_clustering")
    
    async def _perform_marker_analysis(self, method, min_logfc, min_pct):
        """Perform technique-specific marker analysis"""
        raise NotImplementedError("Subclasses must implement _perform_marker_analysis")
    
    def _validate_qc_parameters(self, min_genes, min_cells, max_genes, max_mito_pct):
        """Validate QC parameters"""
        validation_result = {"valid": True, "errors": []}
        
        if not isinstance(min_genes, int) or min_genes < 0:
            validation_result["valid"] = False
            validation_result["errors"].append("min_genes must be a positive integer")
        
        if not isinstance(min_cells, int) or min_cells < 0:
            validation_result["valid"] = False
            validation_result["errors"].append("min_cells must be a positive integer")
        
        if not isinstance(max_genes, int) or max_genes < min_genes:
            validation_result["valid"] = False
            validation_result["errors"].append("max_genes must be greater than min_genes")
        
        if not isinstance(max_mito_pct, (int, float)) or not 0 <= max_mito_pct <= 100:
            validation_result["valid"] = False
            validation_result["errors"].append("max_mito_pct must be between 0 and 100")
        
        return validation_result 