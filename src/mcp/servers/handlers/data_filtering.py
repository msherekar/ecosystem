"""
Data Filtering Mixin

Handles data filtering operations for different analysis techniques.
Separated for better modularity and maintainability.
"""

from typing import Any, Dict, List
from ...core.registry.tool_registry import mcp_tool


class DataFilteringMixin:
    """Mixin providing data filtering functionality"""
    
    @mcp_tool(
        description="Filter cells and genes/features based on quality metrics",
        category="data"
    )
    async def filter_cells_genes(self, min_genes_per_cell: int = 200, 
                                max_genes_per_cell: int = 5000, 
                                min_cells_per_gene: int = 3,
                                preview_only: bool = False) -> Dict[str, Any]:
        """Filter cells and genes"""
        self._log_operation("Filtering", 
                           min_genes_per_cell=min_genes_per_cell,
                           max_genes_per_cell=max_genes_per_cell,
                           min_cells_per_gene=min_cells_per_gene,
                           preview_only=preview_only)
        
        # Validate parameters
        validation = self._validate_filter_parameters(
            min_genes_per_cell, max_genes_per_cell, min_cells_per_gene
        )
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        try:
            if preview_only:
                # Preview filtering effects without applying
                result = await self._preview_filtering(
                    min_genes_per_cell, max_genes_per_cell, min_cells_per_gene
                )
                message = "Filtering preview completed"
            else:
                # Apply actual filtering
                result = await self._perform_filtering(
                    min_genes_per_cell, max_genes_per_cell, min_cells_per_gene
                )
                self._update_progress("filtering", True)
                message = "Filtering completed"
            
            return self._create_success_response(message, **result)
            
        except Exception as e:
            return self._create_error_response(f"Filtering failed: {str(e)}")
    
    @mcp_tool(
        description="Filter cells based on mitochondrial gene percentage",
        category="data"
    )
    async def filter_mitochondrial(self, max_mito_pct: float = 20.0,
                                  preview_only: bool = False) -> Dict[str, Any]:
        """Filter cells by mitochondrial content"""
        self._log_operation("Mitochondrial filtering", max_mito_pct=max_mito_pct, preview_only=preview_only)
        
        # Validate parameters
        if not isinstance(max_mito_pct, (int, float)) or not 0 <= max_mito_pct <= 100:
            return self._create_error_response(
                "max_mito_pct must be between 0 and 100",
                error_type="parameter_validation"
            )
        
        try:
            if preview_only:
                result = await self._preview_mitochondrial_filtering(max_mito_pct)
                message = "Mitochondrial filtering preview completed"
            else:
                result = await self._perform_mitochondrial_filtering(max_mito_pct)
                message = "Mitochondrial filtering completed"
            
            return self._create_success_response(message, **result)
            
        except Exception as e:
            return self._create_error_response(f"Mitochondrial filtering failed: {str(e)}")
    
    @mcp_tool(
        description="Apply custom gene filtering based on expression patterns",
        category="data"
    )
    async def filter_genes_custom(self, expression_threshold: float = 0.1,
                                 min_expression_cells: int = 5,
                                 gene_list: List[str] = None,
                                 exclude_genes: bool = False) -> Dict[str, Any]:
        """Apply custom gene filtering"""
        self._log_operation("Custom gene filtering", 
                           expression_threshold=expression_threshold,
                           min_expression_cells=min_expression_cells,
                           gene_count=len(gene_list) if gene_list else 0,
                           exclude_genes=exclude_genes)
        
        # Validate parameters
        validation = self._validate_custom_filter_parameters(
            expression_threshold, min_expression_cells, gene_list, exclude_genes
        )
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        try:
            result = await self._perform_custom_gene_filtering(
                expression_threshold, min_expression_cells, gene_list, exclude_genes
            )
            
            return self._create_success_response(
                "Custom gene filtering completed",
                **result
            )
        except Exception as e:
            return self._create_error_response(f"Custom gene filtering failed: {str(e)}")
    
    @mcp_tool(
        description="Get filtering recommendations based on data distribution",
        category="data"
    )
    async def get_filtering_recommendations(self) -> Dict[str, Any]:
        """Get filtering recommendations"""
        try:
            # Check data availability
            data_check = self._check_data_availability()
            if not data_check["available"]:
                return self._create_error_response(
                    data_check["message"],
                    error_type="no_data"
                )
            
            recommendations = await self._generate_filtering_recommendations()
            
            return self._create_success_response(
                "Filtering recommendations generated",
                recommendations=recommendations
            )
        except Exception as e:
            return self._create_error_response(f"Failed to generate recommendations: {str(e)}")
    
    # Abstract methods that must be implemented by technique-specific handlers
    async def _perform_filtering(self, min_genes_per_cell, max_genes_per_cell, min_cells_per_gene):
        """Perform technique-specific filtering"""
        raise NotImplementedError("Subclasses must implement _perform_filtering")
    
    async def _preview_filtering(self, min_genes_per_cell, max_genes_per_cell, min_cells_per_gene):
        """Preview filtering effects"""
        raise NotImplementedError("Subclasses must implement _preview_filtering")
    
    async def _perform_mitochondrial_filtering(self, max_mito_pct):
        """Perform mitochondrial filtering"""
        raise NotImplementedError("Subclasses must implement _perform_mitochondrial_filtering")
    
    async def _preview_mitochondrial_filtering(self, max_mito_pct):
        """Preview mitochondrial filtering"""
        raise NotImplementedError("Subclasses must implement _preview_mitochondrial_filtering")
    
    async def _perform_custom_gene_filtering(self, expression_threshold, min_expression_cells, 
                                          gene_list, exclude_genes):
        """Perform custom gene filtering"""
        raise NotImplementedError("Subclasses must implement _perform_custom_gene_filtering")
    
    async def _generate_filtering_recommendations(self):
        """Generate filtering recommendations"""
        raise NotImplementedError("Subclasses must implement _generate_filtering_recommendations")
    
    def _validate_filter_parameters(self, min_genes_per_cell, max_genes_per_cell, min_cells_per_gene):
        """Validate filtering parameters"""
        validation_result = {"valid": True, "errors": []}
        
        if not isinstance(min_genes_per_cell, int) or min_genes_per_cell < 0:
            validation_result["valid"] = False
            validation_result["errors"].append("min_genes_per_cell must be a positive integer")
        
        if not isinstance(max_genes_per_cell, int) or max_genes_per_cell < min_genes_per_cell:
            validation_result["valid"] = False
            validation_result["errors"].append("max_genes_per_cell must be greater than min_genes_per_cell")
        
        if not isinstance(min_cells_per_gene, int) or min_cells_per_gene < 0:
            validation_result["valid"] = False
            validation_result["errors"].append("min_cells_per_gene must be a positive integer")
        
        return validation_result
    
    def _validate_custom_filter_parameters(self, expression_threshold, min_expression_cells, 
                                         gene_list, exclude_genes):
        """Validate custom filter parameters"""
        validation_result = {"valid": True, "errors": []}
        
        if not isinstance(expression_threshold, (int, float)) or expression_threshold < 0:
            validation_result["valid"] = False
            validation_result["errors"].append("expression_threshold must be non-negative")
        
        if not isinstance(min_expression_cells, int) or min_expression_cells < 0:
            validation_result["valid"] = False
            validation_result["errors"].append("min_expression_cells must be a positive integer")
        
        if gene_list is not None:
            if not isinstance(gene_list, list):
                validation_result["valid"] = False
                validation_result["errors"].append("gene_list must be a list")
            elif len(gene_list) > 10000:
                validation_result["valid"] = False
                validation_result["errors"].append("gene_list too large (>10000 genes)")
        
        if not isinstance(exclude_genes, bool):
            validation_result["valid"] = False
            validation_result["errors"].append("exclude_genes must be boolean")
        
        return validation_result


def main():
    """Test data filtering mixin functionality"""
    import logging
    
    class TestDataFilteringHandler(DataFilteringMixin):
        def __init__(self):
            self.logger = logging.getLogger("test")
            
        def _log_operation(self, operation, **params):
            pass
            
        def _create_error_response(self, message, error_type="unknown"):
            return {"success": False, "message": message, "error_type": error_type}
            
        def _create_success_response(self, message, **kwargs):
            return {"success": True, "message": message, **kwargs}
            
        def _check_data_availability(self):
            return {"available": True}
            
        def _update_progress(self, step, completed):
            pass
            
        async def _perform_filtering(self, min_genes, max_genes, min_cells):
            return {"filtered_cells": 100, "filtered_genes": 200}
            
        async def _preview_filtering(self, min_genes, max_genes, min_cells):
            return {"cells_to_remove": 10, "genes_to_remove": 20}
            
        async def _perform_mitochondrial_filtering(self, max_mito_pct):
            return {"cells_removed": 5}
            
        async def _preview_mitochondrial_filtering(self, max_mito_pct):
            return {"cells_to_remove": 5}
            
        async def _perform_custom_gene_filtering(self, threshold, min_cells, genes, exclude):
            return {"genes_filtered": 50}
            
        async def _generate_filtering_recommendations(self):
            return {"min_genes_per_cell": 200, "max_mito_pct": 20}
    
    # Test parameter validation
    handler = TestDataFilteringHandler()
    validation = handler._validate_filter_parameters(200, 5000, 3)
    assert validation["valid"] is True
    
    validation = handler._validate_custom_filter_parameters(0.1, 5, ["GENE1", "GENE2"], False)
    assert validation["valid"] is True
    
    print("✅ Data filtering mixin tests passed")


if __name__ == "__main__":
    main()