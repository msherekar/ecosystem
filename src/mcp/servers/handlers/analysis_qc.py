"""
Quality Control Analysis Mixin

Handles QC-specific operations for different analysis techniques.
Separated for better modularity and maintainability.
"""

import asyncio
from typing import Any, Dict
from ...core.registry.tool_registry import mcp_tool


class QualityControlMixin:
    """Mixin providing quality control analysis functionality"""
    
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
        
        # Check rate limiting
        if not self.security_validator.check_rate_limit(f"qc_{self.get_technique_name()}"):
            return self._create_error_response(
                "Rate limit exceeded. Please wait before running QC again.",
                error_type="rate_limit"
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
        description="Calculate QC metrics without filtering",
        category="analysis"
    )
    async def calculate_qc_metrics(self) -> Dict[str, Any]:
        """Calculate QC metrics"""
        self._log_operation("QC metrics calculation")
        
        try:
            result = await self._calculate_qc_metrics()
            
            return self._create_success_response(
                "QC metrics calculated",
                **result
            )
        except Exception as e:
            return self._create_error_response(f"QC metrics calculation failed: {str(e)}")
    
    @mcp_tool(
        description="Get QC recommendations based on data",
        category="analysis"
    )
    async def get_qc_recommendations(self) -> Dict[str, Any]:
        """Get QC parameter recommendations"""
        try:
            # Check data availability
            data_check = self._check_data_availability()
            if not data_check["available"]:
                return self._create_error_response(
                    data_check["message"],
                    error_type="no_data"
                )
            
            recommendations = await self._generate_qc_recommendations()
            
            return self._create_success_response(
                "QC recommendations generated",
                recommendations=recommendations
            )
        except Exception as e:
            return self._create_error_response(f"QC recommendations failed: {str(e)}")
    
    # Abstract methods that must be implemented by technique-specific handlers
    async def _perform_qc(self, min_genes, min_cells, max_genes, max_mito_pct):
        """Perform technique-specific QC"""
        raise NotImplementedError("Subclasses must implement _perform_qc")
    
    async def _calculate_qc_metrics(self):
        """Calculate technique-specific QC metrics"""
        raise NotImplementedError("Subclasses must implement _calculate_qc_metrics")
    
    async def _generate_qc_recommendations(self):
        """Generate technique-specific QC recommendations"""
        raise NotImplementedError("Subclasses must implement _generate_qc_recommendations")
    
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
        
        # Additional validation for extreme values
        if min_genes > 10000:
            validation_result["valid"] = False
            validation_result["errors"].append("min_genes too high (>10000), may remove too many cells")
        
        if max_genes < 500:
            validation_result["valid"] = False
            validation_result["errors"].append("max_genes too low (<500), may be too restrictive")
        
        return validation_result


def main():
    """Test QC mixin functionality"""
    import logging
    
    class TestQCHandler(QualityControlMixin):
        def __init__(self):
            self.logger = logging.getLogger("test")
            
        def _log_operation(self, operation, **params):
            pass
            
        def _create_error_response(self, message, error_type="unknown"):
            return {"success": False, "message": message, "error_type": error_type}
            
        def _create_success_response(self, message, **kwargs):
            return {"success": True, "message": message, **kwargs}
            
        def get_technique_name(self):
            return "test"
            
        def _check_data_availability(self):
            return {"available": True}
            
        def _update_progress(self, step, completed):
            pass
            
        async def _perform_qc(self, min_genes, min_cells, max_genes, max_mito_pct):
            return {"cells_filtered": 100, "genes_filtered": 200}
            
        async def _calculate_qc_metrics(self):
            return {"mean_genes": 2000, "mean_counts": 5000}
            
        async def _generate_qc_recommendations(self):
            return {"min_genes": 200, "max_mito_pct": 20}
    
    # Test parameter validation
    handler = TestQCHandler()
    validation = handler._validate_qc_parameters(200, 3, 5000, 20.0)
    assert validation["valid"] is True
    
    # Test invalid parameters
    validation = handler._validate_qc_parameters(-1, 3, 5000, 20.0)
    assert validation["valid"] is False
    
    print("✅ QC mixin tests passed")


if __name__ == "__main__":
    main()