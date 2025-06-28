"""
Data Resource Management Mixin

Handles data resource exposure and management for MCP resources.
Provides standardized access to raw and processed data.
"""

from typing import Any, Dict, Optional
from datetime import datetime
from ...core.registry.resource_registry import mcp_resource


class DataResourceMixin:
    """Mixin providing data resource management functionality"""
    
    @mcp_resource(
        uri="data://raw",
        name="Raw Data", 
        description="Raw data matrix and metadata"
    )
    async def get_raw_data(self) -> Dict[str, Any]:
        """Get raw data resource"""
        try:
            data_check = self._check_data_availability()
            if not data_check["available"]:
                return {
                    "available": False, 
                    "message": data_check["message"],
                    "error_type": "no_data"
                }
            
            raw_info = self._get_raw_data_info()
            
            # Add resource metadata
            raw_info.update({
                "resource_type": "raw_data",
                "last_updated": datetime.now().isoformat(),
                "technique": self.get_technique_name(),
                "access_level": "read_only"
            })
            
            return raw_info
            
        except Exception as e:
            return {
                "available": False, 
                "message": f"Failed to access raw data: {str(e)}",
                "error_type": "access_error"
            }
    
    @mcp_resource(
        uri="data://processed",
        name="Processed Data",
        description="Processed and normalized data with analysis results"
    )
    async def get_processed_data(self) -> Dict[str, Any]:
        """Get processed data resource"""
        try:
            data_check = self._check_data_availability()
            if not data_check["available"]:
                return {
                    "available": False,
                    "message": data_check["message"],
                    "error_type": "no_data"
                }
            
            processed_info = self._get_processed_data_info()
            
            # Add processing metadata
            processing_steps = self._get_processing_history()
            processed_info.update({
                "resource_type": "processed_data",
                "processing_steps": processing_steps,
                "last_updated": datetime.now().isoformat(),
                "technique": self.get_technique_name(),
                "access_level": "read_write"
            })
            
            return processed_info
            
        except Exception as e:
            return {
                "available": False,
                "message": f"Failed to access processed data: {str(e)}",
                "error_type": "access_error"
            }
    
    @mcp_resource(
        uri="data://metadata", 
        name="Data Metadata",
        description="Data metadata including sample information and experimental conditions"
    )
    async def get_data_metadata(self) -> Dict[str, Any]:
        """Get data metadata resource"""
        try:
            metadata = await self._extract_metadata()
            
            metadata.update({
                "resource_type": "metadata",
                "last_updated": datetime.now().isoformat(),
                "technique": self.get_technique_name()
            })
            
            return metadata
            
        except Exception as e:
            return {
                "available": False,
                "message": f"Failed to access metadata: {str(e)}",
                "error_type": "metadata_error"
            }
    
    @mcp_resource(
        uri="data://results",
        name="Analysis Results", 
        description="Analysis results including clusters, markers, and visualizations"
    )
    async def get_analysis_results(self) -> Dict[str, Any]:
        """Get analysis results resource"""
        try:
            results = await self._collect_analysis_results()
            
            results.update({
                "resource_type": "analysis_results",
                "last_updated": datetime.now().isoformat(),
                "technique": self.get_technique_name()
            })
            
            return results
            
        except Exception as e:
            return {
                "available": False,
                "message": f"Failed to access analysis results: {str(e)}",
                "error_type": "results_error"
            }
    
    @mcp_resource(
        uri="data://quality_metrics",
        name="Quality Metrics",
        description="Data quality metrics and QC statistics"
    )
    async def get_quality_metrics(self) -> Dict[str, Any]:
        """Get quality metrics resource"""
        try:
            metrics = await self._calculate_quality_metrics()
            
            metrics.update({
                "resource_type": "quality_metrics",
                "last_updated": datetime.now().isoformat(),
                "technique": self.get_technique_name()
            })
            
            return metrics
            
        except Exception as e:
            return {
                "available": False,
                "message": f"Failed to calculate quality metrics: {str(e)}",
                "error_type": "metrics_error"
            }
    
    # Abstract methods that must be implemented by technique-specific handlers
    def _get_raw_data_info(self) -> Dict[str, Any]:
        """Get raw data information"""
        raise NotImplementedError("Subclasses must implement _get_raw_data_info")
    
    def _get_processed_data_info(self) -> Dict[str, Any]:
        """Get processed data information"""
        raise NotImplementedError("Subclasses must implement _get_processed_data_info")
    
    async def _extract_metadata(self) -> Dict[str, Any]:
        """Extract data metadata"""
        return {"available": False, "metadata_available": False}  # Default implementation
    
    async def _collect_analysis_results(self) -> Dict[str, Any]:
        """Collect analysis results"""
        return {"available": False, "results_available": False}  # Default implementation
    
    async def _calculate_quality_metrics(self) -> Dict[str, Any]:
        """Calculate quality metrics"""
        return {"available": False, "metrics_available": False}  # Default implementation
    
    def _get_processing_history(self) -> list:
        """Get processing step history"""
        # Default implementation - can be overridden
        progress_key = self._get_session_state_key("progress")
        if hasattr(self, '_get_session_state_key'):
            import streamlit as st
            if progress_key in st.session_state:
                completed_steps = [
                    step for step, completed in st.session_state[progress_key].items()
                    if completed
                ]
                return completed_steps
        return []


def main():
    """Test data resource mixin functionality"""
    import logging
    import asyncio
    
    class TestDataResourceHandler(DataResourceMixin):
        def __init__(self):
            self.logger = logging.getLogger("test")
            
        def get_technique_name(self):
            return "test"
            
        def _check_data_availability(self):
            return {"available": True}
            
        def _get_session_state_key(self, key):
            return f"test_{key}"
            
        def _get_raw_data_info(self):
            return {"shape": (1000, 2000), "available": True}
            
        def _get_processed_data_info(self):
            return {"shape": (900, 1800), "available": True}
            
        async def _extract_metadata(self):
            return {"sample_count": 10, "metadata_available": True}
            
        async def _collect_analysis_results(self):
            return {"clusters": 8, "results_available": True}
            
        async def _calculate_quality_metrics(self):
            return {"mean_genes": 2000, "metrics_available": True}
    
    async def test_resources():
        handler = TestDataResourceHandler()
        
        # Test raw data resource
        raw_data = await handler.get_raw_data()
        assert raw_data["available"] is True
        assert "resource_type" in raw_data
        
        # Test processed data resource
        processed_data = await handler.get_processed_data()
        assert processed_data["available"] is True
        assert "processing_steps" in processed_data
        
        # Test metadata resource
        metadata = await handler.get_data_metadata()
        assert metadata["metadata_available"] is True
        
        print("✅ Data resource mixin tests passed")
    
    # Run async tests
    asyncio.run(test_resources())


if __name__ == "__main__":
    main()