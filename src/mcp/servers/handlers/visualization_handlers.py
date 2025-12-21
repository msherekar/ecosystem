"""
Visualization Handlers

Modular visualization handlers for different plot types.
Split into focused components for better maintainability.
"""

from typing import Any, Dict, List
from ...core.registry.tool_registry import mcp_tool
from .visualization_plots import PlotCreationMixin
from .visualization_analysis import PlotAnalysisMixin
from .visualization_export import PlotExportMixin


class VisualizationHandlerMixin(PlotCreationMixin, PlotAnalysisMixin, PlotExportMixin):
    """Combined visualization handlers using composition"""
    
    @mcp_tool(
        description="Create interactive plot with custom parameters",
        category="visualization"
    )
    async def create_interactive_plot(self, plot_type: str, 
                                    color_by: str = "leiden",
                                    interactive: bool = True,
                                    save_plot: bool = False) -> Dict[str, Any]:
        """Create interactive plot"""
        self._log_operation("Interactive plot", 
                           plot_type=plot_type, 
                           color_by=color_by, 
                           interactive=interactive)
        
        # Validate parameters
        validation = self._validate_interactive_plot_parameters(plot_type, color_by, interactive)
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        try:
            result = await self._create_interactive_visualization(
                plot_type, color_by, interactive, save_plot
            )
            
            return self._create_success_response(
                f"Interactive {plot_type} plot created",
                plot_type=plot_type,
                **result
            )
        except Exception as e:
            return self._create_error_response(f"Interactive plot creation failed: {str(e)}")
    
    @mcp_tool(
        description="Generate publication-ready figure with multiple panels",
        category="visualization"
    )
    async def create_publication_figure(self, panels: List[Dict[str, Any]], 
                                      figure_size: tuple = (12, 8),
                                      dpi: int = 300) -> Dict[str, Any]:
        """Create publication-ready figure"""
        self._log_operation("Publication figure", 
                           n_panels=len(panels), 
                           figure_size=figure_size, 
                           dpi=dpi)
        
        # Validate parameters
        validation = self._validate_publication_figure_parameters(panels, figure_size, dpi)
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        try:
            result = await self._create_publication_figure(panels, figure_size, dpi)
            
            return self._create_success_response(
                f"Publication figure created with {len(panels)} panels",
                **result
            )
        except Exception as e:
            return self._create_error_response(f"Publication figure creation failed: {str(e)}")
    
    # Abstract methods that must be implemented by technique-specific handlers
    async def _create_interactive_visualization(self, plot_type, color_by, interactive, save_plot):
        """Create technique-specific interactive visualization"""
        raise NotImplementedError("Subclasses must implement _create_interactive_visualization")
    
    async def _create_publication_figure(self, panels, figure_size, dpi):
        """Create technique-specific publication figure"""
        raise NotImplementedError("Subclasses must implement _create_publication_figure")
    
    def _validate_interactive_plot_parameters(self, plot_type, color_by, interactive):
        """Validate interactive plot parameters"""
        validation_result = {"valid": True, "errors": []}
        
        # Validate plot type
        allowed_plot_types = ["umap", "pca", "violin", "heatmap", "scatter", "histogram"]
        if plot_type not in allowed_plot_types:
            validation_result["valid"] = False
            validation_result["errors"].append(f"plot_type must be one of {allowed_plot_types}")
        
        # Validate color_by
        if not isinstance(color_by, str) or not color_by:
            validation_result["valid"] = False
            validation_result["errors"].append("color_by must be a non-empty string")
        
        # Validate interactive
        if not isinstance(interactive, bool):
            validation_result["valid"] = False
            validation_result["errors"].append("interactive must be boolean")
        
        return validation_result
    
    def _validate_publication_figure_parameters(self, panels, figure_size, dpi):
        """Validate publication figure parameters"""
        validation_result = {"valid": True, "errors": []}
        
        # Validate panels
        if not isinstance(panels, list) or not panels:
            validation_result["valid"] = False
            validation_result["errors"].append("panels must be a non-empty list")
        
        if len(panels) > 10:
            validation_result["valid"] = False
            validation_result["errors"].append("Maximum 10 panels allowed")
        
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
        
        # Validate dpi
        if not isinstance(dpi, int) or not 72 <= dpi <= 600:
            validation_result["valid"] = False
            validation_result["errors"].append("dpi must be between 72 and 600")
        
        return validation_result


def main():
    """Test visualization handlers functionality"""
    import logging
    from .base_handler import BaseHandler
    
    class TestVisualizationHandler(BaseHandler, VisualizationHandlerMixin):
        def get_technique_name(self) -> str:
            return "test"
        
        def _check_data_availability(self) -> Dict[str, Any]:
            return {"available": True}
        
        async def _create_interactive_visualization(self, plot_type, color_by, interactive, save_plot):
            return {"plot_created": True, "interactive": interactive}
        
        async def _create_publication_figure(self, panels, figure_size, dpi):
            return {"figure_created": True, "n_panels": len(panels)}
    
    # Test functionality
    logger = logging.getLogger("test")
    handler = TestVisualizationHandler(logger)
    
    # Test interactive plot parameter validation
    validation = handler._validate_interactive_plot_parameters("umap", "leiden", True)
    assert validation["valid"] is True
    
    validation = handler._validate_interactive_plot_parameters("invalid_type", "leiden", True)
    assert validation["valid"] is False
    
    # Test publication figure parameter validation
    panels = [{"type": "umap"}, {"type": "violin"}]
    validation = handler._validate_publication_figure_parameters(panels, (12, 8), 300)
    assert validation["valid"] is True
    
    print("✅ Visualization handlers tests passed")


if __name__ == "__main__":
    main()