"""
Plot Analysis Mixin

Handles plot analysis and biological insights for different visualization types.
Separated for better modularity and maintainability.
"""

from typing import Any, Dict, List
from ...core.registry.tool_registry import mcp_tool


class PlotAnalysisMixin:
    """Mixin providing plot analysis and insights functionality"""
    
    @mcp_tool(
        description="REQUIRED when user asks about plots, charts, graphs, visualizations, or wants to summarize results on the current page. Analyzes currently displayed plots and provides biological insights about QC metrics, PCA results, clustering, UMAP, etc. Use this tool whenever user mentions 'plot', 'chart', 'graph', 'visualization', 'summarize', or asks about results on the current page.",
        category="context"
    )
    async def analyze_current_plots(self, user_question: str = "") -> Dict[str, Any]:
        """Analyze currently displayed plots and provide biological insights"""
        try:
            # Get context-aware biological insights that consider the user's specific question
            insights = self._analyze_displayed_plots(user_question)
            
            # Check if this should be routed to LLM with context
            if insights == "CONCEPTUAL_QUESTION_ROUTE_TO_LLM":
                return self._create_success_response(
                    "ROUTE_TO_LLM_WITH_CONTEXT",
                    route_to_llm=True,
                    context_type="conceptual_question",
                    user_question=user_question
                )
            
            # Parse insights if they contain structured data
            parsed_insights = self._parse_plot_insights(insights)
            
            result = self._create_success_response(
                insights,
                summary="Analyzed current plots and provided biological insights",
                insights_type="biological_analysis",
                **parsed_insights
            )
            
            return result
        except Exception as e:
            return self._create_error_response(f"Plot analysis failed: {str(e)}")
    
    @mcp_tool(
        description="Get statistical summary of plot data",
        category="visualization"
    )
    async def get_plot_statistics(self, plot_type: str = "current") -> Dict[str, Any]:
        """Get statistical summary of plot data"""
        self._log_operation("Plot statistics", plot_type=plot_type)
        
        try:
            stats = await self._calculate_plot_statistics(plot_type)
            
            return self._create_success_response(
                f"Plot statistics calculated for {plot_type}",
                statistics=stats,
                plot_type=plot_type
            )
        except Exception as e:
            return self._create_error_response(f"Plot statistics calculation failed: {str(e)}")
    
    @mcp_tool(
        description="Compare multiple plots or plot versions",
        category="visualization"
    )
    async def compare_plots(self, plot_ids: List[str], 
                           comparison_metrics: List[str] = None) -> Dict[str, Any]:
        """Compare multiple plots"""
        if comparison_metrics is None:
            comparison_metrics = ["clustering_quality", "separation", "variance_explained"]
            
        self._log_operation("Plot comparison", plot_ids=plot_ids, metrics=comparison_metrics)
        
        # Validate parameters
        validation = self._validate_comparison_parameters(plot_ids, comparison_metrics)
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        try:
            comparison_result = await self._perform_plot_comparison(plot_ids, comparison_metrics)
            
            return self._create_success_response(
                f"Plot comparison completed for {len(plot_ids)} plots",
                comparison=comparison_result,
                metrics_used=comparison_metrics
            )
        except Exception as e:
            return self._create_error_response(f"Plot comparison failed: {str(e)}")
    
    @mcp_tool(
        description="Generate biological interpretation of clustering results",
        category="visualization"
    )
    async def interpret_clustering(self, cluster_id: str = None) -> Dict[str, Any]:
        """Generate biological interpretation of clustering"""
        self._log_operation("Clustering interpretation", cluster_id=cluster_id)
        
        try:
            interpretation = await self._generate_clustering_interpretation(cluster_id)
            
            return self._create_success_response(
                "Clustering interpretation generated",
                interpretation=interpretation,
                cluster_analyzed=cluster_id or "all_clusters"
            )
        except Exception as e:
            return self._create_error_response(f"Clustering interpretation failed: {str(e)}")
    
    @mcp_tool(
        description="Identify potential data quality issues from visualizations",
        category="visualization"
    )
    async def detect_visualization_issues(self) -> Dict[str, Any]:
        """Detect potential issues in current visualizations"""
        try:
            issues = await self._detect_plot_quality_issues()
            
            return self._create_success_response(
                f"Visualization quality check completed, found {len(issues.get('issues', []))} potential issues",
                quality_check=issues
            )
        except Exception as e:
            return self._create_error_response(f"Visualization quality check failed: {str(e)}")
    
    # Abstract methods that must be implemented by technique-specific handlers
    def _analyze_displayed_plots(self, user_question: str = "") -> str:
        """Analyze currently displayed plots with optional context from user question"""
        raise NotImplementedError("Subclasses must implement _analyze_displayed_plots")
    
    async def _calculate_plot_statistics(self, plot_type: str) -> Dict[str, Any]:
        """Calculate statistics for specific plot type"""
        raise NotImplementedError("Subclasses must implement _calculate_plot_statistics")
    
    async def _perform_plot_comparison(self, plot_ids: List[str], metrics: List[str]) -> Dict[str, Any]:
        """Perform comparison between multiple plots"""
        raise NotImplementedError("Subclasses must implement _perform_plot_comparison")
    
    async def _generate_clustering_interpretation(self, cluster_id: str = None) -> Dict[str, Any]:
        """Generate biological interpretation of clustering results"""
        raise NotImplementedError("Subclasses must implement _generate_clustering_interpretation")
    
    async def _detect_plot_quality_issues(self) -> Dict[str, Any]:
        """Detect quality issues in current plots"""
        raise NotImplementedError("Subclasses must implement _detect_plot_quality_issues")
    
    def _parse_plot_insights(self, insights: str) -> Dict[str, Any]:
        """Parse insights string for structured data"""
        parsed = {
            "insight_categories": [],
            "key_findings": [],
            "recommendations": []
        }
        
        # Simple parsing logic - can be enhanced
        if "cluster" in insights.lower():
            parsed["insight_categories"].append("clustering")
        if "quality" in insights.lower() or "qc" in insights.lower():
            parsed["insight_categories"].append("quality_control")
        if "expression" in insights.lower():
            parsed["insight_categories"].append("gene_expression")
        if "dimension" in insights.lower() or "pca" in insights.lower() or "umap" in insights.lower():
            parsed["insight_categories"].append("dimensionality_reduction")
        
        # Extract key findings (simplified)
        sentences = insights.split('.')
        key_sentences = [s.strip() for s in sentences if len(s.strip()) > 20][:3]
        parsed["key_findings"] = key_sentences
        
        # Generate recommendations based on content
        if "outlier" in insights.lower():
            parsed["recommendations"].append("Consider investigating outlier cells")
        if "batch" in insights.lower():
            parsed["recommendations"].append("Consider batch correction methods")
        if "resolution" in insights.lower():
            parsed["recommendations"].append("Optimize clustering resolution")
        
        return parsed
    
    def _validate_comparison_parameters(self, plot_ids: List[str], metrics: List[str]) -> Dict[str, Any]:
        """Validate plot comparison parameters"""
        validation_result = {"valid": True, "errors": []}
        
        if not isinstance(plot_ids, list) or len(plot_ids) < 2:
            validation_result["valid"] = False
            validation_result["errors"].append("At least 2 plot IDs required for comparison")
        
        if len(plot_ids) > 10:
            validation_result["valid"] = False
            validation_result["errors"].append("Maximum 10 plots allowed for comparison")
        
        if not isinstance(metrics, list) or not metrics:
            validation_result["valid"] = False
            validation_result["errors"].append("At least one comparison metric required")
        
        valid_metrics = [
            "clustering_quality", "separation", "variance_explained", 
            "silhouette_score", "modularity", "homogeneity"
        ]
        
        for metric in metrics:
            if metric not in valid_metrics:
                validation_result["valid"] = False
                validation_result["errors"].append(f"Invalid metric: {metric}")
        
        return validation_result


def main():
    """Test plot analysis mixin functionality"""
    import logging
    import asyncio
    
    class TestPlotAnalysisHandler(PlotAnalysisMixin):
        def __init__(self):
            self.logger = logging.getLogger("test")
            
        def _log_operation(self, operation, **params):
            pass
            
        def _create_error_response(self, message, error_type="unknown"):
            return {"success": False, "message": message, "error_type": error_type}
            
        def _create_success_response(self, message, **kwargs):
            return {"success": True, "message": message, **kwargs}
            
        def _analyze_displayed_plots(self, user_question=""):
            return "Test analysis: The UMAP shows clear cluster separation with 8 distinct groups."
            
        async def _calculate_plot_statistics(self, plot_type):
            return {"mean_expression": 2.5, "variance": 1.2}
            
        async def _perform_plot_comparison(self, plot_ids, metrics):
            return {"best_plot": plot_ids[0], "scores": {"clustering_quality": 0.85}}
            
        async def _generate_clustering_interpretation(self, cluster_id=None):
            return {"interpretation": "Cluster shows high expression of marker genes"}
            
        async def _detect_plot_quality_issues(self):
            return {"issues": [], "overall_quality": "good"}
    
    async def test_analysis():
        handler = TestPlotAnalysisHandler()
        
        # Test insights parsing
        insights = "The clustering shows good separation. Quality control metrics look good."
        parsed = handler._parse_plot_insights(insights)
        assert "clustering" in parsed["insight_categories"]
        assert "quality_control" in parsed["insight_categories"]
        
        # Test comparison validation
        validation = handler._validate_comparison_parameters(["plot1", "plot2"], ["clustering_quality"])
        assert validation["valid"] is True
        
        validation = handler._validate_comparison_parameters(["plot1"], ["clustering_quality"])
        assert validation["valid"] is False
        
        print("✅ Plot analysis mixin tests passed")
    
    # Run async tests
    asyncio.run(test_analysis())


if __name__ == "__main__":
    main()