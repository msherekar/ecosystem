"""
Plot Export Mixin

Handles plot export and publication features for different visualization types.
Separated for better modularity and maintainability.
"""

from typing import Any, Dict, List, Optional
from ...core.registry.tool_registry import mcp_tool


class PlotExportMixin:
    """Mixin providing plot export and publication functionality"""
    
    @mcp_tool(
        description="Export current plot to file",
        category="visualization"
    )
    async def export_plot(self, filename: str = None, format: str = "png", 
                         dpi: int = 300, transparent: bool = False) -> Dict[str, Any]:
        """Export current plot to file"""
        self._log_operation("Plot export", filename=filename, format=format, dpi=dpi)
        
        # Validate parameters
        validation = self._validate_export_parameters(filename, format, dpi, transparent)
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        try:
            result = await self._export_current_plot(filename, format, dpi, transparent)
            
            return self._create_success_response(
                f"Plot exported to {result['filename']}",
                **result
            )
        except Exception as e:
            return self._create_error_response(f"Plot export failed: {str(e)}")
    
    @mcp_tool(
        description="Create publication-ready figure with multiple panels",
        category="visualization"
    )
    async def create_publication_figure(self, panels: List[Dict[str, Any]], 
                                      figure_size: tuple = (12, 8),
                                      dpi: int = 300, layout: str = "grid") -> Dict[str, Any]:
        """Create publication-ready figure"""
        self._log_operation("Publication figure", 
                           n_panels=len(panels), 
                           figure_size=figure_size, 
                           dpi=dpi,
                           layout=layout)
        
        # Validate parameters
        validation = self._validate_publication_parameters(panels, figure_size, dpi, layout)
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        try:
            result = await self._create_publication_figure(panels, figure_size, dpi, layout)
            
            return self._create_success_response(
                f"Publication figure created with {len(panels)} panels",
                **result
            )
        except Exception as e:
            return self._create_error_response(f"Publication figure creation failed: {str(e)}")
    
    @mcp_tool(
        description="Export plot data to CSV or other formats",
        category="visualization"
    )
    async def export_plot_data(self, plot_type: str, data_format: str = "csv",
                              include_metadata: bool = True) -> Dict[str, Any]:
        """Export underlying plot data"""
        self._log_operation("Plot data export", plot_type=plot_type, format=data_format)
        
        # Validate parameters
        validation = self._validate_data_export_parameters(plot_type, data_format, include_metadata)
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        try:
            result = await self._export_plot_data(plot_type, data_format, include_metadata)
            
            return self._create_success_response(
                f"Plot data exported as {data_format}",
                **result
            )
        except Exception as e:
            return self._create_error_response(f"Plot data export failed: {str(e)}")
    
    @mcp_tool(
        description="Create interactive web-based plot",
        category="visualization"
    )
    async def create_interactive_plot(self, plot_type: str, 
                                    output_format: str = "html",
                                    include_controls: bool = True) -> Dict[str, Any]:
        """Create interactive web-based plot"""
        self._log_operation("Interactive plot", plot_type=plot_type, format=output_format)
        
        # Validate parameters
        validation = self._validate_interactive_parameters(plot_type, output_format, include_controls)
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        try:
            result = await self._create_interactive_export(plot_type, output_format, include_controls)
            
            return self._create_success_response(
                f"Interactive {plot_type} plot created",
                **result
            )
        except Exception as e:
            return self._create_error_response(f"Interactive plot creation failed: {str(e)}")
    
    @mcp_tool(
        description="Batch export multiple plots with consistent formatting",
        category="visualization"
    )
    async def batch_export_plots(self, plot_configs: List[Dict[str, Any]],
                                export_format: str = "png", 
                                naming_pattern: str = "plot_{index}") -> Dict[str, Any]:
        """Batch export multiple plots"""
        self._log_operation("Batch export", n_plots=len(plot_configs), format=export_format)
        
        # Validate parameters
        validation = self._validate_batch_export_parameters(plot_configs, export_format, naming_pattern)
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        try:
            result = await self._batch_export_plots(plot_configs, export_format, naming_pattern)
            
            return self._create_success_response(
                f"Batch export completed: {result['exported_count']} plots",
                **result
            )
        except Exception as e:
            return self._create_error_response(f"Batch export failed: {str(e)}")
    
    # Abstract methods that must be implemented by technique-specific handlers
    async def _export_current_plot(self, filename: str, format: str, dpi: int, transparent: bool):
        """Export current plot with technique-specific implementation"""
        raise NotImplementedError("Subclasses must implement _export_current_plot")
    
    async def _create_publication_figure(self, panels: List[Dict], figure_size: tuple, dpi: int, layout: str):
        """Create publication figure with technique-specific implementation"""
        raise NotImplementedError("Subclasses must implement _create_publication_figure")
    
    async def _export_plot_data(self, plot_type: str, data_format: str, include_metadata: bool):
        """Export plot data with technique-specific implementation"""
        raise NotImplementedError("Subclasses must implement _export_plot_data")
    
    async def _create_interactive_export(self, plot_type: str, output_format: str, include_controls: bool):
        """Create interactive export with technique-specific implementation"""
        raise NotImplementedError("Subclasses must implement _create_interactive_export")
    
    async def _batch_export_plots(self, plot_configs: List[Dict], export_format: str, naming_pattern: str):
        """Batch export plots with technique-specific implementation"""
        raise NotImplementedError("Subclasses must implement _batch_export_plots")
    
    # Parameter validation methods
    def _validate_export_parameters(self, filename: str, format: str, dpi: int, transparent: bool):
        """Validate export parameters"""
        validation_result = {"valid": True, "errors": []}
        
        # Validate format
        allowed_formats = ["png", "pdf", "svg", "eps", "jpg", "tiff"]
        if format not in allowed_formats:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Format must be one of {allowed_formats}")
        
        # Validate DPI
        if not isinstance(dpi, int) or not 72 <= dpi <= 600:
            validation_result["valid"] = False
            validation_result["errors"].append("DPI must be between 72 and 600")
        
        # Validate filename if provided
        if filename and not self.security_validator._is_safe_filename(filename):
            validation_result["valid"] = False
            validation_result["errors"].append("Invalid filename")
        
        # Validate transparent parameter
        if not isinstance(transparent, bool):
            validation_result["valid"] = False
            validation_result["errors"].append("transparent must be boolean")
        
        return validation_result
    
    def _validate_publication_parameters(self, panels: List[Dict], figure_size: tuple, dpi: int, layout: str):
        """Validate publication figure parameters"""
        validation_result = {"valid": True, "errors": []}
        
        # Validate panels
        if not isinstance(panels, list) or not panels:
            validation_result["valid"] = False
            validation_result["errors"].append("panels must be a non-empty list")
        
        if len(panels) > 12:
            validation_result["valid"] = False
            validation_result["errors"].append("Maximum 12 panels allowed")
        
        # Validate each panel
        for i, panel in enumerate(panels):
            if not isinstance(panel, dict):
                validation_result["valid"] = False
                validation_result["errors"].append(f"Panel {i} must be a dictionary")
            elif "type" not in panel:
                validation_result["valid"] = False
                validation_result["errors"].append(f"Panel {i} must have 'type' field")
        
        # Validate figure_size
        if not isinstance(figure_size, (tuple, list)) or len(figure_size) != 2:
            validation_result["valid"] = False
            validation_result["errors"].append("figure_size must be a tuple/list of 2 numbers")
        
        # Validate layout
        allowed_layouts = ["grid", "row", "column", "custom"]
        if layout not in allowed_layouts:
            validation_result["valid"] = False
            validation_result["errors"].append(f"layout must be one of {allowed_layouts}")
        
        return validation_result
    
    def _validate_data_export_parameters(self, plot_type: str, data_format: str, include_metadata: bool):
        """Validate data export parameters"""
        validation_result = {"valid": True, "errors": []}
        
        # Validate plot_type
        if not isinstance(plot_type, str) or not plot_type:
            validation_result["valid"] = False
            validation_result["errors"].append("plot_type must be a non-empty string")
        
        # Validate data_format
        allowed_formats = ["csv", "tsv", "xlsx", "json", "parquet"]
        if data_format not in allowed_formats:
            validation_result["valid"] = False
            validation_result["errors"].append(f"data_format must be one of {allowed_formats}")
        
        # Validate include_metadata
        if not isinstance(include_metadata, bool):
            validation_result["valid"] = False
            validation_result["errors"].append("include_metadata must be boolean")
        
        return validation_result
    
    def _validate_interactive_parameters(self, plot_type: str, output_format: str, include_controls: bool):
        """Validate interactive plot parameters"""
        validation_result = {"valid": True, "errors": []}
        
        # Validate plot_type
        if not isinstance(plot_type, str) or not plot_type:
            validation_result["valid"] = False
            validation_result["errors"].append("plot_type must be a non-empty string")
        
        # Validate output_format
        allowed_formats = ["html", "json", "plotly", "bokeh"]
        if output_format not in allowed_formats:
            validation_result["valid"] = False
            validation_result["errors"].append(f"output_format must be one of {allowed_formats}")
        
        # Validate include_controls
        if not isinstance(include_controls, bool):
            validation_result["valid"] = False
            validation_result["errors"].append("include_controls must be boolean")
        
        return validation_result
    
    def _validate_batch_export_parameters(self, plot_configs: List[Dict], export_format: str, naming_pattern: str):
        """Validate batch export parameters"""
        validation_result = {"valid": True, "errors": []}
        
        # Validate plot_configs
        if not isinstance(plot_configs, list) or not plot_configs:
            validation_result["valid"] = False
            validation_result["errors"].append("plot_configs must be a non-empty list")
        
        if len(plot_configs) > 50:
            validation_result["valid"] = False
            validation_result["errors"].append("Maximum 50 plots allowed for batch export")
        
        # Validate export_format
        allowed_formats = ["png", "pdf", "svg", "jpg"]
        if export_format not in allowed_formats:
            validation_result["valid"] = False
            validation_result["errors"].append(f"export_format must be one of {allowed_formats}")
        
        # Validate naming_pattern
        if not isinstance(naming_pattern, str) or "{index}" not in naming_pattern:
            validation_result["valid"] = False
            validation_result["errors"].append("naming_pattern must contain {index} placeholder")
        
        return validation_result


def main():
    """Test plot export mixin functionality"""
    import logging
    import asyncio
    
    class TestPlotExportHandler(PlotExportMixin):
        def __init__(self):
            self.logger = logging.getLogger("test")
            self.security_validator = type('SecurityValidator', (), {
                '_is_safe_filename': lambda self, filename: True
            })()
            
        def _log_operation(self, operation, **params):
            pass
            
        def _create_error_response(self, message, error_type="unknown"):
            return {"success": False, "message": message, "error_type": error_type}
            
        def _create_success_response(self, message, **kwargs):
            return {"success": True, "message": message, **kwargs}
            
        async def _export_current_plot(self, filename, format, dpi, transparent):
            return {"filename": f"plot.{format}", "size_bytes": 1024}
            
        async def _create_publication_figure(self, panels, figure_size, dpi, layout):
            return {"filename": "publication_figure.pdf", "panels": len(panels)}
            
        async def _export_plot_data(self, plot_type, data_format, include_metadata):
            return {"filename": f"plot_data.{data_format}", "rows": 1000}
            
        async def _create_interactive_export(self, plot_type, output_format, include_controls):
            return {"filename": f"interactive_plot.{output_format}", "interactive": True}
            
        async def _batch_export_plots(self, plot_configs, export_format, naming_pattern):
            return {"exported_count": len(plot_configs), "format": export_format}
    
    async def test_export():
        handler = TestPlotExportHandler()
        
        # Test export parameter validation
        validation = handler._validate_export_parameters("test.png", "png", 300, False)
        assert validation["valid"] is True
        
        validation = handler._validate_export_parameters("test.png", "invalid", 300, False)
        assert validation["valid"] is False
        
        # Test publication parameter validation
        panels = [{"type": "umap"}, {"type": "violin"}]
        validation = handler._validate_publication_parameters(panels, (12, 8), 300, "grid")
        assert validation["valid"] is True
        
        print("✅ Plot export mixin tests passed")
    
    # Run async tests
    asyncio.run(test_export())


if __name__ == "__main__":
    main()