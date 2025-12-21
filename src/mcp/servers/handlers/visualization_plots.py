"""
Plot Creation Mixin

Handles basic plot creation operations for different visualization types.
Separated for better modularity and maintainability.
"""

from typing import Any, Dict, List
from ...core.registry.tool_registry import mcp_tool


class PlotCreationMixin:
    """Mixin providing basic plot creation functionality"""
    
    @mcp_tool(
        description="Create UMAP visualization of cells",
        category="visualization"
    )
    async def create_umap_plot(self, color_by: str = "leiden", min_dist: float = 0.5, 
                              spread: float = 1.0, size: int = 50) -> Dict[str, Any]:
        """Create UMAP plot"""
        self._log_operation("UMAP plot", color_by=color_by, min_dist=min_dist, spread=spread)
        
        # Validate parameters
        validation = self._validate_umap_parameters(color_by, min_dist, spread, size)
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        try:
            result = await self._create_umap_visualization(color_by, min_dist, spread, size)
            
            return self._create_success_response(
                f"UMAP plot created, colored by {color_by}",
                plot_type="umap",
                parameters={"color_by": color_by, "min_dist": min_dist, "spread": spread},
                **result
            )
        except Exception as e:
            return self._create_error_response(f"UMAP plot creation failed: {str(e)}")
    
    @mcp_tool(
        description="Create violin plot of gene expression by cluster",
        category="visualization"
    )
    async def create_violin_plot(self, genes: List[str], groupby: str = "leiden",
                                rotation: int = 45) -> Dict[str, Any]:
        """Create violin plot"""
        self._log_operation("Violin plot", genes=genes, groupby=groupby)
        
        # Validate parameters
        validation = self._validate_violin_parameters(genes, groupby, rotation)
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        try:
            result = await self._create_violin_visualization(genes, groupby, rotation)
            
            return self._create_success_response(
                f"Violin plot created for {len(genes)} genes, grouped by {groupby}",
                plot_type="violin",
                parameters={"genes": genes, "groupby": groupby},
                **result
            )
        except Exception as e:
            return self._create_error_response(f"Violin plot creation failed: {str(e)}")
    
    @mcp_tool(
        description="Create heatmap of marker genes",
        category="visualization"
    )
    async def create_marker_heatmap(self, n_genes: int = 5, groupby: str = "leiden",
                                   cluster_rows: bool = True, cluster_cols: bool = True) -> Dict[str, Any]:
        """Create marker gene heatmap"""
        self._log_operation("Marker heatmap", n_genes=n_genes, groupby=groupby)
        
        # Validate parameters
        validation = self._validate_heatmap_parameters(n_genes, groupby, cluster_rows, cluster_cols)
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        try:
            result = await self._create_heatmap_visualization(n_genes, groupby, cluster_rows, cluster_cols)
            
            return self._create_success_response(
                f"Marker heatmap created with top {n_genes} genes per group",
                plot_type="heatmap",
                parameters={"n_genes": n_genes, "groupby": groupby},
                **result
            )
        except Exception as e:
            return self._create_error_response(f"Heatmap creation failed: {str(e)}")
    
    @mcp_tool(
        description="Create PCA plot for dimensionality reduction visualization",
        category="visualization"
    )
    async def create_pca_plot(self, color_by: str = "leiden", n_components: int = 2,
                             components: List[int] = None) -> Dict[str, Any]:
        """Create PCA plot"""
        if components is None:
            components = [1, 2]
            
        self._log_operation("PCA plot", color_by=color_by, n_components=n_components, components=components)
        
        # Validate parameters
        validation = self._validate_pca_parameters(color_by, n_components, components)
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        try:
            result = await self._create_pca_visualization(color_by, n_components, components)
            
            return self._create_success_response(
                f"PCA plot created, colored by {color_by}",
                plot_type="pca",
                parameters={"color_by": color_by, "components": components},
                **result
            )
        except Exception as e:
            return self._create_error_response(f"PCA plot creation failed: {str(e)}")
    
    @mcp_tool(
        description="Create scatter plot with custom axes",
        category="visualization"
    )
    async def create_scatter_plot(self, x_axis: str, y_axis: str, color_by: str = "leiden",
                                 size_by: str = None, alpha: float = 0.7) -> Dict[str, Any]:
        """Create custom scatter plot"""
        self._log_operation("Scatter plot", x_axis=x_axis, y_axis=y_axis, color_by=color_by)
        
        # Validate parameters
        validation = self._validate_scatter_parameters(x_axis, y_axis, color_by, size_by, alpha)
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        try:
            result = await self._create_scatter_visualization(x_axis, y_axis, color_by, size_by, alpha)
            
            return self._create_success_response(
                f"Scatter plot created: {x_axis} vs {y_axis}",
                plot_type="scatter",
                parameters={"x_axis": x_axis, "y_axis": y_axis, "color_by": color_by},
                **result
            )
        except Exception as e:
            return self._create_error_response(f"Scatter plot creation failed: {str(e)}")
    
    # Abstract methods that must be implemented by technique-specific handlers
    async def _create_umap_visualization(self, color_by, min_dist, spread, size):
        """Create technique-specific UMAP visualization"""
        raise NotImplementedError("Subclasses must implement _create_umap_visualization")
    
    async def _create_violin_visualization(self, genes, groupby, rotation):
        """Create technique-specific violin plot"""
        raise NotImplementedError("Subclasses must implement _create_violin_visualization")
    
    async def _create_heatmap_visualization(self, n_genes, groupby, cluster_rows, cluster_cols):
        """Create technique-specific heatmap"""
        raise NotImplementedError("Subclasses must implement _create_heatmap_visualization")
    
    async def _create_pca_visualization(self, color_by, n_components, components):
        """Create technique-specific PCA plot"""
        raise NotImplementedError("Subclasses must implement _create_pca_visualization")
    
    async def _create_scatter_visualization(self, x_axis, y_axis, color_by, size_by, alpha):
        """Create technique-specific scatter plot"""
        raise NotImplementedError("Subclasses must implement _create_scatter_visualization")
    
    # Parameter validation methods
    def _validate_umap_parameters(self, color_by, min_dist, spread, size):
        """Validate UMAP parameters"""
        validation_result = {"valid": True, "errors": []}
        
        if not isinstance(color_by, str) or not color_by:
            validation_result["valid"] = False
            validation_result["errors"].append("color_by must be a non-empty string")
        
        if not isinstance(min_dist, (int, float)) or not 0.0 <= min_dist <= 1.0:
            validation_result["valid"] = False
            validation_result["errors"].append("min_dist must be between 0.0 and 1.0")
        
        if not isinstance(spread, (int, float)) or spread <= 0:
            validation_result["valid"] = False
            validation_result["errors"].append("spread must be positive")
        
        if not isinstance(size, int) or not 1 <= size <= 500:
            validation_result["valid"] = False
            validation_result["errors"].append("size must be between 1 and 500")
        
        return validation_result
    
    def _validate_violin_parameters(self, genes, groupby, rotation):
        """Validate violin plot parameters"""
        validation_result = {"valid": True, "errors": []}
        
        if not isinstance(genes, list) or not genes:
            validation_result["valid"] = False
            validation_result["errors"].append("genes must be a non-empty list")
        
        if len(genes) > 20:
            validation_result["valid"] = False
            validation_result["errors"].append("Maximum 20 genes allowed for violin plot")
        
        if not isinstance(groupby, str) or not groupby:
            validation_result["valid"] = False
            validation_result["errors"].append("groupby must be a non-empty string")
        
        if not isinstance(rotation, int) or not 0 <= rotation <= 90:
            validation_result["valid"] = False
            validation_result["errors"].append("rotation must be between 0 and 90 degrees")
        
        return validation_result
    
    def _validate_heatmap_parameters(self, n_genes, groupby, cluster_rows, cluster_cols):
        """Validate heatmap parameters"""
        validation_result = {"valid": True, "errors": []}
        
        if not isinstance(n_genes, int) or not 1 <= n_genes <= 50:
            validation_result["valid"] = False
            validation_result["errors"].append("n_genes must be between 1 and 50")
        
        if not isinstance(groupby, str) or not groupby:
            validation_result["valid"] = False
            validation_result["errors"].append("groupby must be a non-empty string")
        
        if not isinstance(cluster_rows, bool):
            validation_result["valid"] = False
            validation_result["errors"].append("cluster_rows must be boolean")
        
        if not isinstance(cluster_cols, bool):
            validation_result["valid"] = False
            validation_result["errors"].append("cluster_cols must be boolean")
        
        return validation_result
    
    def _validate_pca_parameters(self, color_by, n_components, components):
        """Validate PCA parameters"""
        validation_result = {"valid": True, "errors": []}
        
        if not isinstance(color_by, str) or not color_by:
            validation_result["valid"] = False
            validation_result["errors"].append("color_by must be a non-empty string")
        
        if not isinstance(n_components, int) or not 2 <= n_components <= 10:
            validation_result["valid"] = False
            validation_result["errors"].append("n_components must be between 2 and 10")
        
        if not isinstance(components, list) or len(components) != 2:
            validation_result["valid"] = False
            validation_result["errors"].append("components must be a list of 2 integers")
        
        return validation_result
    
    def _validate_scatter_parameters(self, x_axis, y_axis, color_by, size_by, alpha):
        """Validate scatter plot parameters"""
        validation_result = {"valid": True, "errors": []}
        
        if not isinstance(x_axis, str) or not x_axis:
            validation_result["valid"] = False
            validation_result["errors"].append("x_axis must be a non-empty string")
        
        if not isinstance(y_axis, str) or not y_axis:
            validation_result["valid"] = False
            validation_result["errors"].append("y_axis must be a non-empty string")
        
        if not isinstance(color_by, str) or not color_by:
            validation_result["valid"] = False
            validation_result["errors"].append("color_by must be a non-empty string")
        
        if size_by is not None and (not isinstance(size_by, str) or not size_by):
            validation_result["valid"] = False
            validation_result["errors"].append("size_by must be None or a non-empty string")
        
        if not isinstance(alpha, (int, float)) or not 0.1 <= alpha <= 1.0:
            validation_result["valid"] = False
            validation_result["errors"].append("alpha must be between 0.1 and 1.0")
        
        return validation_result


def main():
    """Test plot creation mixin functionality"""
    import logging
    
    class TestPlotCreationHandler(PlotCreationMixin):
        def __init__(self):
            self.logger = logging.getLogger("test")
            
        def _log_operation(self, operation, **params):
            pass
            
        def _create_error_response(self, message, error_type="unknown"):
            return {"success": False, "message": message, "error_type": error_type}
            
        def _create_success_response(self, message, **kwargs):
            return {"success": True, "message": message, **kwargs}
            
        async def _create_umap_visualization(self, color_by, min_dist, spread, size):
            return {"plot_created": True, "color_by": color_by}
            
        async def _create_violin_visualization(self, genes, groupby, rotation):
            return {"plot_created": True, "genes_plotted": len(genes)}
            
        async def _create_heatmap_visualization(self, n_genes, groupby, cluster_rows, cluster_cols):
            return {"plot_created": True, "genes_per_group": n_genes}
            
        async def _create_pca_visualization(self, color_by, n_components, components):
            return {"plot_created": True, "components": components}
            
        async def _create_scatter_visualization(self, x_axis, y_axis, color_by, size_by, alpha):
            return {"plot_created": True, "axes": [x_axis, y_axis]}
    
    # Test parameter validation
    handler = TestPlotCreationHandler()
    
    # Test UMAP validation
    validation = handler._validate_umap_parameters("leiden", 0.5, 1.0, 50)
    assert validation["valid"] is True
    
    # Test violin validation
    validation = handler._validate_violin_parameters(["GENE1", "GENE2"], "leiden", 45)
    assert validation["valid"] is True
    
    # Test invalid parameters
    validation = handler._validate_umap_parameters("", 2.0, 1.0, 50)
    assert validation["valid"] is False
    
    print("✅ Plot creation mixin tests passed")


if __name__ == "__main__":
    main()