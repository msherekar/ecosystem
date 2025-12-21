"""
Clustering Analysis Mixin

Handles clustering-specific operations for different analysis techniques.
Separated for better modularity and maintainability.
"""

import asyncio
from typing import Any, Dict, List
from ...core.registry.tool_registry import mcp_tool


class ClusteringMixin:
    """Mixin providing clustering analysis functionality"""
    
    @mcp_tool(
        description="Perform cell clustering (requires normalization)",
        category="analysis"
    )
    async def cluster_cells(self, resolution: float = 0.5, n_neighbors: int = 15, n_pcs: int = 40):
        """Perform cell clustering"""
        # Validate parameters using base class method
        validation = self._validate_clustering_parameters(
            resolution=resolution, 
            n_neighbors=n_neighbors, 
            n_pcs=n_pcs
        )
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        self._log_operation("Clustering", resolution=resolution, n_neighbors=n_neighbors, n_pcs=n_pcs)
        
        # Check prerequisites
        prereq_check = self._check_clustering_prerequisites()
        if not prereq_check["ready"]:
            return self._create_error_response(
                prereq_check["message"],
                error_type="prerequisites_not_met",
                suggestion=prereq_check.get("suggestion")
            )
        
        try:
            result = await self._perform_clustering(resolution, n_neighbors, n_pcs)
            self._update_progress("clustering", True)
            
            return self._create_success_response(
                f"Clustering completed with resolution={resolution}, found {result.get('n_clusters', 'unknown')} clusters",
                n_clusters=result.get("n_clusters"),
                resolution=resolution,
                algorithm=result.get("algorithm", "leiden"),
                silhouette_score=result.get("silhouette_score"),
                modularity=result.get("modularity")
            )
        except Exception as e:
            return self._create_error_response(f"Clustering failed: {str(e)}")
    
    @mcp_tool(
        description="Optimize clustering resolution automatically",
        category="analysis"
    )
    async def optimize_clustering_resolution(self, min_resolution: float = 0.1, 
                                           max_resolution: float = 2.0, 
                                           step: float = 0.1) -> Dict[str, Any]:
        """Find optimal clustering resolution"""
        self._log_operation("Resolution optimization", 
                           min_resolution=min_resolution, 
                           max_resolution=max_resolution, 
                           step=step)
        
        # Validate parameters
        validation = self._validate_resolution_optimization_parameters(
            min_resolution, max_resolution, step
        )
        if not validation["valid"]:
            return self._create_error_response(
                f"Invalid parameters: {', '.join(validation['errors'])}",
                error_type="parameter_validation"
            )
        
        try:
            result = await self._optimize_clustering_resolution(min_resolution, max_resolution, step)
            
            return self._create_success_response(
                f"Optimal resolution found: {result.get('optimal_resolution')}",
                **result
            )
        except Exception as e:
            return self._create_error_response(f"Resolution optimization failed: {str(e)}")
    
    @mcp_tool(
        description="Evaluate clustering quality metrics",
        category="analysis"
    )
    async def evaluate_clustering(self) -> Dict[str, Any]:
        """Evaluate clustering quality"""
        try:
            # Check if clustering has been performed
            if not self._has_clustering_results():
                return self._create_error_response(
                    "No clustering results found. Please run clustering first.",
                    error_type="no_clustering"
                )
            
            result = await self._evaluate_clustering_quality()
            
            return self._create_success_response(
                "Clustering evaluation completed",
                **result
            )
        except Exception as e:
            return self._create_error_response(f"Clustering evaluation failed: {str(e)}")
    
    # Abstract methods that must be implemented by technique-specific handlers
    async def _perform_clustering(self, resolution, n_neighbors, n_pcs):
        """Perform technique-specific clustering"""
        raise NotImplementedError("Subclasses must implement _perform_clustering")
    
    async def _optimize_clustering_resolution(self, min_resolution, max_resolution, step):
        """Optimize clustering resolution for technique"""
        raise NotImplementedError("Subclasses must implement _optimize_clustering_resolution")
    
    async def _evaluate_clustering_quality(self):
        """Evaluate clustering quality for technique"""
        raise NotImplementedError("Subclasses must implement _evaluate_clustering_quality")
    
    def _check_clustering_prerequisites(self):
        """Check if prerequisites for clustering are met"""
        # Default implementation - subclasses can override
        return {"ready": True, "message": "Prerequisites met"}
    
    def _has_clustering_results(self):
        """Check if clustering results exist"""
        # Default implementation - subclasses can override
        return True
    
    def _validate_clustering_parameters(self, **kwargs):
        """Validate clustering parameters"""
        validation_result = {"valid": True, "errors": []}
        
        if "resolution" in kwargs:
            resolution = kwargs["resolution"]
            if not isinstance(resolution, (int, float)) or not 0.1 <= resolution <= 2.0:
                validation_result["valid"] = False
                validation_result["errors"].append("Resolution must be between 0.1 and 2.0")
        
        if "n_neighbors" in kwargs:
            n_neighbors = kwargs["n_neighbors"]
            if not isinstance(n_neighbors, int) or not 5 <= n_neighbors <= 100:
                validation_result["valid"] = False
                validation_result["errors"].append("n_neighbors must be between 5 and 100")
        
        if "n_pcs" in kwargs:
            n_pcs = kwargs["n_pcs"]
            if not isinstance(n_pcs, int) or not 10 <= n_pcs <= 100:
                validation_result["valid"] = False
                validation_result["errors"].append("n_pcs must be between 10 and 100")
        
        return validation_result
    
    def _validate_resolution_optimization_parameters(self, min_resolution, max_resolution, step):
        """Validate resolution optimization parameters"""
        validation_result = {"valid": True, "errors": []}
        
        if not isinstance(min_resolution, (int, float)) or min_resolution <= 0:
            validation_result["valid"] = False
            validation_result["errors"].append("min_resolution must be positive")
        
        if not isinstance(max_resolution, (int, float)) or max_resolution <= min_resolution:
            validation_result["valid"] = False
            validation_result["errors"].append("max_resolution must be greater than min_resolution")
        
        if not isinstance(step, (int, float)) or step <= 0:
            validation_result["valid"] = False
            validation_result["errors"].append("step must be positive")
        
        # Check if range is reasonable
        n_steps = (max_resolution - min_resolution) / step
        if n_steps > 50:
            validation_result["valid"] = False
            validation_result["errors"].append("Too many steps (>50), consider larger step size")
        
        return validation_result


def main():
    """Test clustering mixin functionality"""
    import logging
    
    class TestClusteringHandler(ClusteringMixin):
        def __init__(self):
            self.logger = logging.getLogger("test")
            
        def _log_operation(self, operation, **params):
            pass
            
        def _create_error_response(self, message, error_type="unknown", suggestion=None):
            return {"success": False, "message": message, "error_type": error_type}
            
        def _create_success_response(self, message, **kwargs):
            return {"success": True, "message": message, **kwargs}
            
        def _update_progress(self, step, completed):
            pass
            
        async def _perform_clustering(self, resolution, n_neighbors, n_pcs):
            return {"n_clusters": 8, "algorithm": "leiden"}
            
        async def _optimize_clustering_resolution(self, min_res, max_res, step):
            return {"optimal_resolution": 0.5, "scores": [0.3, 0.5, 0.4]}
            
        async def _evaluate_clustering_quality(self):
            return {"silhouette_score": 0.45, "modularity": 0.62}
    
    # Test parameter validation
    handler = TestClusteringHandler()
    validation = handler._validate_clustering_parameters(resolution=0.5, n_neighbors=15, n_pcs=40)
    assert validation["valid"] is True
    
    # Test invalid parameters
    validation = handler._validate_clustering_parameters(resolution=5.0)
    assert validation["valid"] is False
    
    print("✅ Clustering mixin tests passed")


if __name__ == "__main__":
    main()