"""
Data Handlers

Modular data handlers for data validation, summary, and filtering.
Split into focused components for better maintainability.
"""

import streamlit as st
from typing import Any, Dict, List
from ...core.registry.tool_registry import mcp_tool
from ...core.registry.resource_registry import mcp_resource
from .data_validation import DataValidationMixin
from .data_filtering import DataFilteringMixin
from .data_resources import DataResourceMixin


class DataHandlerMixin(DataValidationMixin, DataFilteringMixin, DataResourceMixin):
    """Combined data handlers using composition"""
    
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
        
        try:
            # Get technique-specific summary
            summary = self._generate_data_summary()
            
            # Add metadata
            metadata = await self._get_data_metadata()
            summary["metadata"] = metadata
            
            return self._create_success_response(
                "Data summary generated",
                summary=summary
            )
        except Exception as e:
            return self._create_error_response(f"Data summary failed: {str(e)}")
    
    @mcp_tool(
        description="Export processed data to file",
        category="data"
    )
    async def export_data(self, format: str = "h5ad", filename: str = None) -> Dict[str, Any]:
        """Export processed data"""
        self._log_operation("Data export", format=format, filename=filename)
        
        # Validate parameters
        validation = self._validate_export_parameters(format, filename)
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        try:
            result = await self._export_data(format, filename)
            
            return self._create_success_response(
                f"Data exported to {result['filename']}",
                **result
            )
        except Exception as e:
            return self._create_error_response(f"Data export failed: {str(e)}")
    
    @mcp_tool(
        description="Compare current data with another dataset",
        category="data"
    )
    async def compare_datasets(self, reference_file: str) -> Dict[str, Any]:
        """Compare current data with reference dataset"""
        self._log_operation("Dataset comparison", reference_file=reference_file)
        
        try:
            # Validate reference file
            file_validation = self.security_validator.validate_file_upload(
                reference_file, 0  # Size will be checked during loading
            )
            if not file_validation["valid"]:
                return self._create_error_response(
                    f"Invalid reference file: {', '.join(file_validation['errors'])}",
                    error_type="file_validation"
                )
            
            result = await self._compare_with_reference(reference_file)
            
            return self._create_success_response(
                "Dataset comparison completed",
                **result
            )
        except Exception as e:
            return self._create_error_response(f"Dataset comparison failed: {str(e)}")
    
    # Abstract methods that must be implemented by technique-specific handlers
    def _generate_data_summary(self) -> Dict[str, Any]:
        """Generate technique-specific data summary"""
        raise NotImplementedError("Subclasses must implement _generate_data_summary")
    
    async def _get_data_metadata(self) -> Dict[str, Any]:
        """Get technique-specific data metadata"""
        return {}  # Default empty metadata
    
    async def _export_data(self, format: str, filename: str) -> Dict[str, Any]:
        """Export technique-specific data"""
        raise NotImplementedError("Subclasses must implement _export_data")
    
    async def _compare_with_reference(self, reference_file: str) -> Dict[str, Any]:
        """Compare with reference dataset"""
        raise NotImplementedError("Subclasses must implement _compare_with_reference")
    
    def _validate_export_parameters(self, format: str, filename: str) -> Dict[str, Any]:
        """Validate export parameters"""
        validation_result = {"valid": True, "errors": []}
        
        # Validate format
        allowed_formats = ["h5ad", "csv", "tsv", "xlsx", "h5"]
        if format not in allowed_formats:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Format must be one of {allowed_formats}")
        
        # Validate filename if provided
        if filename and not self.security_validator._is_safe_filename(filename):
            validation_result["valid"] = False
            validation_result["errors"].append("Invalid filename")
        
        return validation_result


def main():
    """Test data handlers functionality"""
    import logging
    from .base_handler import BaseHandler
    
    class TestDataHandler(BaseHandler, DataHandlerMixin):
        def get_technique_name(self) -> str:
            return "test"
        
        def _check_data_availability(self) -> Dict[str, Any]:
            return {"available": True}
        
        def _generate_data_summary(self) -> Dict[str, Any]:
            return {"cells": 1000, "genes": 2000}
        
        async def _export_data(self, format, filename):
            return {"filename": f"test_data.{format}", "size": 1024}
        
        async def _compare_with_reference(self, reference_file):
            return {"similarity": 0.85, "differences": ["gene_count"]}
    
    # Test functionality
    logger = logging.getLogger("test")
    handler = TestDataHandler(logger)
    
    # Test export parameter validation
    validation = handler._validate_export_parameters("h5ad", "test.h5ad")
    assert validation["valid"] is True
    
    validation = handler._validate_export_parameters("invalid", "test.txt")
    assert validation["valid"] is False
    
    print("✅ Data handlers tests passed")


if __name__ == "__main__":
    main()