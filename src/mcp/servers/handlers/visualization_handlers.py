"""
Visualization Handlers

Modular visualization handlers for different plot types.
This separates visualization logic from the main handler file.
"""

from typing import Any, Dict, List
from ...core.tool_registry import mcp_tool


class VisualizationHandlerMixin:
    """Mixin providing visualization-related handlers"""
    
    @mcp_tool(
        description="Create UMAP visualization of cells",
        category="visualization"
    )
    async def create_umap_plot(self, color_by: str = "leiden", min_dist: float = 0.5, 
                              spread: float = 1.0) -> Dict[str, Any]:
        """Create UMAP plot"""
        self._log_operation("UMAP plot", color_by=color_by, min_dist=min_dist, spread=spread)
        
        # Validate parameters
        validation = self._validate_umap_parameters(color_by, min_dist, spread)
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        try:
            result = await self._create_umap_visualization(color_by, min_dist, spread)
            
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
    async def create_violin_plot(self, genes: List[str], groupby: str = "leiden") -> Dict[str, Any]:
        """Create violin plot"""
        self._log_operation("Violin plot", genes=genes, groupby=groupby)
        
        # Validate parameters
        validation = self._validate_violin_parameters(genes, groupby)
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        try:
            result = await self._create_violin_visualization(genes, groupby)
            
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
    async def create_marker_heatmap(self, n_genes: int = 5, groupby: str = "leiden") -> Dict[str, Any]:
        """Create marker gene heatmap"""
        self._log_operation("Marker heatmap", n_genes=n_genes, groupby=groupby)
        
        # Validate parameters
        validation = self._validate_heatmap_parameters(n_genes, groupby)
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        try:
            result = await self._create_heatmap_visualization(n_genes, groupby)
            
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
    async def create_pca_plot(self, color_by: str = "leiden", n_components: int = 2) -> Dict[str, Any]:
        """Create PCA plot"""
        self._log_operation("PCA plot", color_by=color_by, n_components=n_components)
        
        try:
            result = await self._create_pca_visualization(color_by, n_components)
            
            return self._create_success_response(
                f"PCA plot created, colored by {color_by}",
                plot_type="pca",
                parameters={"color_by": color_by, "n_components": n_components},
                **result
            )
        except Exception as e:
            return self._create_error_response(f"PCA plot creation failed: {str(e)}")
    
    @mcp_tool(
        description="REQUIRED when user asks about plots, charts, graphs, visualizations, or wants to summarize results on the current page. Analyzes currently displayed plots and provides biological insights about QC metrics, PCA results, clustering, UMAP, etc. Use this tool whenever user mentions 'plot', 'chart', 'graph', 'visualization', 'summarize', or asks about results on the current page.",
        category="context"
    )
    async def analyze_current_plots(self) -> Dict[str, Any]:
        """Analyze currently displayed plots and provide biological insights"""
        try:
            # Get clean biological insights without debug info
            insights = self._analyze_displayed_plots()
            
            return self._create_success_response(
                insights,
                summary="Analyzed current plots and provided biological insights"
            )
        except Exception as e:
            return self._create_error_response(f"Plot analysis failed: {str(e)}")
    
    # Abstract methods that must be implemented by technique-specific handlers
    async def _create_umap_visualization(self, color_by, min_dist, spread):
        """Create technique-specific UMAP visualization"""
        raise NotImplementedError("Subclasses must implement _create_umap_visualization")
    
    async def _create_violin_visualization(self, genes, groupby):
        """Create technique-specific violin plot"""
        raise NotImplementedError("Subclasses must implement _create_violin_visualization")
    
    async def _create_heatmap_visualization(self, n_genes, groupby):
        """Create technique-specific heatmap"""
        raise NotImplementedError("Subclasses must implement _create_heatmap_visualization")
    
    async def _create_pca_visualization(self, color_by, n_components):
        """Create technique-specific PCA plot"""
        raise NotImplementedError("Subclasses must implement _create_pca_visualization")
    
    def _analyze_displayed_plots(self) -> str:
        """Analyze currently displayed plots"""
        raise NotImplementedError("Subclasses must implement _analyze_displayed_plots")
    
    # Parameter validation methods
    def _validate_umap_parameters(self, color_by, min_dist, spread):
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
        
        return validation_result
    
    def _validate_violin_parameters(self, genes, groupby):
        """Validate violin plot parameters"""
        validation_result = {"valid": True, "errors": []}
        
        if not isinstance(genes, list) or not genes:
            validation_result["valid"] = False
            validation_result["errors"].append("genes must be a non-empty list")
        
        if not isinstance(groupby, str) or not groupby:
            validation_result["valid"] = False
            validation_result["errors"].append("groupby must be a non-empty string")
        
        if len(genes) > 20:
            validation_result["valid"] = False
            validation_result["errors"].append("Maximum 20 genes allowed for violin plot")
        
        return validation_result
    
    def _validate_heatmap_parameters(self, n_genes, groupby):
        """Validate heatmap parameters"""
        validation_result = {"valid": True, "errors": []}
        
        if not isinstance(n_genes, int) or not 1 <= n_genes <= 50:
            validation_result["valid"] = False
            validation_result["errors"].append("n_genes must be between 1 and 50")
        
        if not isinstance(groupby, str) or not groupby:
            validation_result["valid"] = False
            validation_result["errors"].append("groupby must be a non-empty string")
        
        return validation_result 