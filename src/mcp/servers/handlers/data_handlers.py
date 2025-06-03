"""
Data Handlers

Modular data handlers for data validation, summary, and filtering.
This separates data logic from the main handler file.
"""

import streamlit as st
from typing import Any, Dict, List
from ...core.tool_registry import mcp_tool
from ...core.resource_registry import mcp_resource


class DataHandlerMixin:
    """Mixin providing data-related handlers"""
    
    @mcp_tool(
        description="Validate uploaded data",
        category="data"
    )
    async def validate_data(self) -> Dict[str, Any]:
        """Validate uploaded data"""
        validation_results = {
            "data_valid": False,
            "data_type": None,
            "issues": []
        }
        
        # Get technique-specific data validation
        data_check = self._check_data_availability()
        
        if data_check["available"]:
            validation_results["data_valid"] = True
            validation_results.update(data_check)
            
            # Perform additional validation
            additional_validation = self._perform_additional_validation()
            validation_results.update(additional_validation)
        else:
            validation_results["issues"].append(data_check["message"])
        
        return self._create_success_response(
            "Data validation completed",
            validation=validation_results
        )
    
    @mcp_tool(
        description="Get summary statistics of data",
        category="data"
    )
    async def get_data_summary(self) -> Dict[str, Any]:
        """Get summary of data"""
        summary = {}
        
        # Check data availability
        data_check = self._check_data_availability()
        if not data_check["available"]:
            return self._create_error_response(
                data_check["message"],
                error_type="no_data"
            )
        
        # Get technique-specific summary
        summary = self._generate_data_summary()
        
        return self._create_success_response(
            "Data summary generated",
            summary=summary
        )
    
    @mcp_tool(
        description="Filter cells and genes/features based on quality metrics",
        category="data"
    )
    async def filter_cells_genes(self, min_genes_per_cell: int = 200, 
                                max_genes_per_cell: int = 5000, 
                                min_cells_per_gene: int = 3) -> Dict[str, Any]:
        """Filter cells and genes"""
        self._log_operation("Filtering", 
                           min_genes_per_cell=min_genes_per_cell,
                           max_genes_per_cell=max_genes_per_cell,
                           min_cells_per_gene=min_cells_per_gene)
        
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
            # Perform technique-specific filtering
            result = await self._perform_filtering(
                min_genes_per_cell, max_genes_per_cell, min_cells_per_gene
            )
            
            self._update_progress("filtering", True)
            
            return self._create_success_response(
                "Filtering completed",
                **result
            )
        except Exception as e:
            return self._create_error_response(f"Filtering failed: {str(e)}")
    
    # Resource handlers
    @mcp_resource(
        uri="data://raw",
        name="Raw Data", 
        description="Raw data matrix"
    )
    async def get_raw_data(self) -> Dict[str, Any]:
        """Get raw data"""
        data_check = self._check_data_availability()
        if data_check["available"]:
            return self._get_raw_data_info()
        return {"available": False, "message": "No raw data uploaded"}
    
    @mcp_resource(
        uri="data://processed",
        name="Processed Data",
        description="Processed and normalized data"
    )
    async def get_processed_data(self) -> Dict[str, Any]:
        """Get processed data"""
        data_check = self._check_data_availability()
        if data_check["available"]:
            return self._get_processed_data_info()
        return {"available": False, "message": "No processed data available"}
    
    # Abstract methods that must be implemented by technique-specific handlers
    def _perform_additional_validation(self) -> Dict[str, Any]:
        """Perform technique-specific additional validation"""
        return {}
    
    def _generate_data_summary(self) -> Dict[str, Any]:
        """Generate technique-specific data summary"""
        raise NotImplementedError("Subclasses must implement _generate_data_summary")
    
    async def _perform_filtering(self, min_genes_per_cell, max_genes_per_cell, min_cells_per_gene):
        """Perform technique-specific filtering"""
        raise NotImplementedError("Subclasses must implement _perform_filtering")
    
    def _get_raw_data_info(self) -> Dict[str, Any]:
        """Get raw data information"""
        raise NotImplementedError("Subclasses must implement _get_raw_data_info")
    
    def _get_processed_data_info(self) -> Dict[str, Any]:
        """Get processed data information"""
        raise NotImplementedError("Subclasses must implement _get_processed_data_info")
    
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