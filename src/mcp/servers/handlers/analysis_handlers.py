"""
Analysis Handlers

Modular analysis handlers for different analysis types.
Split into smaller, focused components for better maintainability.
"""

import asyncio
import streamlit as st
from typing import Any, Dict, List
from ...core.registry.tool_registry import mcp_tool
from .analysis_qc import QualityControlMixin
from .analysis_clustering import ClusteringMixin
from .analysis_pipeline import PipelineMixin


class AnalysisHandlerMixin(QualityControlMixin, ClusteringMixin, PipelineMixin):
    """Combined analysis handlers using composition"""
    
    @mcp_tool(
        description="Normalize and scale expression data",
        category="analysis"
    )
    async def normalize_data(self, target_sum: float = 10000, log_transform: bool = True, 
                           scale: bool = True) -> Dict[str, Any]:
        """Normalize data"""
        self._log_operation("Normalization", target_sum=target_sum, log=log_transform, scale=scale)
        
        # Validate parameters
        validation = self._validate_normalization_parameters(target_sum, log_transform, scale)
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
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
        description="Find marker genes/features for each cluster",
        category="analysis"
    )
    async def find_markers(self, method: str = "wilcoxon", min_logfc: float = 0.25, 
                          min_pct: float = 0.1) -> Dict[str, Any]:
        """Find marker genes for clusters"""
        self._log_operation("Marker analysis", method=method, min_logfc=min_logfc, min_pct=min_pct)
        
        # Validate parameters
        validation = self._validate_marker_parameters(method, min_logfc, min_pct)
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
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
    async def _perform_normalization(self, target_sum, log_transform, scale):
        """Perform technique-specific normalization"""
        raise NotImplementedError("Subclasses must implement _perform_normalization")
    
    async def _perform_marker_analysis(self, method, min_logfc, min_pct):
        """Perform technique-specific marker analysis"""
        raise NotImplementedError("Subclasses must implement _perform_marker_analysis")
    
    def _validate_normalization_parameters(self, target_sum, log_transform, scale):
        """Validate normalization parameters"""
        validation_result = {"valid": True, "errors": []}
        
        if not isinstance(target_sum, (int, float)) or target_sum <= 0:
            validation_result["valid"] = False
            validation_result["errors"].append("target_sum must be a positive number")
        
        if not isinstance(log_transform, bool):
            validation_result["valid"] = False
            validation_result["errors"].append("log_transform must be boolean")
        
        if not isinstance(scale, bool):
            validation_result["valid"] = False
            validation_result["errors"].append("scale must be boolean")
        
        return validation_result
    
    def _validate_marker_parameters(self, method, min_logfc, min_pct):
        """Validate marker analysis parameters"""
        validation_result = {"valid": True, "errors": []}
        
        allowed_methods = ["wilcoxon", "t-test", "logreg"]
        if method not in allowed_methods:
            validation_result["valid"] = False
            validation_result["errors"].append(f"method must be one of {allowed_methods}")
        
        if not isinstance(min_logfc, (int, float)) or min_logfc < 0:
            validation_result["valid"] = False
            validation_result["errors"].append("min_logfc must be a non-negative number")
        
        if not isinstance(min_pct, (int, float)) or not 0 <= min_pct <= 1:
            validation_result["valid"] = False
            validation_result["errors"].append("min_pct must be between 0 and 1")
        
        return validation_result


def main():
    """Test analysis handlers functionality"""
    import logging
    from .base_handler import BaseHandler
    
    class TestAnalysisHandler(BaseHandler, AnalysisHandlerMixin):
        def get_technique_name(self) -> str:
            return "test"
        
        def _check_data_availability(self) -> Dict[str, Any]:
            return {"available": True}
        
        async def _perform_normalization(self, target_sum, log_transform, scale):
            return {"method": "test", "target_sum": target_sum}
        
        async def _perform_marker_analysis(self, method, min_logfc, min_pct):
            return {"total_markers": 100, "method": method}
    
    # Test functionality
    logger = logging.getLogger("test")
    handler = TestAnalysisHandler(logger)
    
    # Test parameter validation
    validation = handler._validate_normalization_parameters(10000, True, True)
    assert validation["valid"] is True
    
    validation = handler._validate_marker_parameters("wilcoxon", 0.25, 0.1)
    assert validation["valid"] is True
    
    print("✅ Analysis handlers tests passed")


if __name__ == "__main__":
    main()