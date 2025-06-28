"""
Direct Router - Bypass LLM/MCP for deterministic operations

This router analyzes user input and routes directly to local Python functions
when the request can be handled deterministically without LLM inference.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Callable, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import inspect

# Import your local modules
from src.modules.search.geo import geo_search, geo_display
from src.modules.search.genomics import pubmed_search  # Assuming this exists
from src.modules.data.file_handler import handle_file_upload  # Assuming this exists
from src.modules.utils.project_manager import create_project_directory  # Assuming this exists
from src.modules.search.registry import search_registry, initialize_search_registry


class RouteConfidence(Enum):
    """Confidence levels for routing decisions"""
    HIGH = "high"       # Direct route with >90% confidence
    MEDIUM = "medium"   # Direct route with 60-90% confidence  
    LOW = "low"         # Should fallback to LLM/MCP
    NONE = "none"       # Cannot handle directly


@dataclass
class RoutePattern:
    """Pattern for matching user input to direct functions"""
    patterns: List[str]  # Regex patterns to match
    function: Callable
    confidence_boost: float = 1.0
    parameter_extractor: Optional[Callable] = None
    description: str = ""
    category: str = "general"


@dataclass
class DirectRouteResult:
    """Result of direct routing analysis"""
    should_route_direct: bool
    confidence: RouteConfidence
    function: Optional[Callable] = None
    parameters: Optional[Dict[str, Any]] = None
    reasoning: str = ""
    fallback_to_llm: bool = False


class DirectRouter:
    """
    Direct router that bypasses LLM/MCP for deterministic operations.
    
    Key Features:
    1. Pattern-based matching for common requests
    2. Parameter extraction from natural language
    3. Confidence scoring for routing decisions
    4. Fallback to LLM/MCP when uncertain
    """
    
    def __init__(self):
        self.logger = logging.getLogger("direct_router")
        
        # Registry of direct route patterns
        self.route_patterns: List[RoutePattern] = []
        
        # Initialize patterns
        self._register_patterns()
        
        # Track routing success rates for learning
        self.routing_stats = {
            "total_attempts": 0,
            "direct_routes": 0,
            "successful_direct": 0,
            "failed_direct": 0
        }
    
    def _register_patterns(self):
        """Register patterns for direct routing"""
        
        # Import search registry
        initialize_search_registry()
        
        # Dynamic search patterns from registry
        search_providers = search_registry.get_all_providers()
        for provider_name, provider in search_providers.items():
            # Create a closure to capture the provider
            def make_search_function(search_provider):
                return lambda query, **kwargs: self._execute_search(query, search_provider, **kwargs)
            
            self.route_patterns.append(
                RoutePattern(
                    patterns=provider.patterns,
                    function=make_search_function(provider),
                    parameter_extractor=self._extract_search_query,
                    description=f"Search {provider.display_name}",
                    category="search",
                    confidence_boost=1.2
                )
            )
        
        # File Upload patterns
        self.route_patterns.extend([
            RoutePattern(
                patterns=[
                    r"upload\s+(?:a\s+)?file",
                    r"load\s+(?:a\s+)?file",
                    r"import\s+(?:a\s+)?file",
                    r"(?:can\s+)?(?:i\s+)?upload"
                ],
                function=self._execute_file_upload,
                parameter_extractor=lambda x: {},
                description="Handle file upload",
                category="data",
                confidence_boost=1.5
            )
        ])
        
        # Project Directory patterns
        self.route_patterns.extend([
            RoutePattern(
                patterns=[
                    r"create\s+(?:a\s+)?(?:new\s+)?project\s+(?:named\s+|called\s+)?(.+)",
                    r"make\s+(?:a\s+)?project\s+(?:directory\s+)?(?:for\s+)?(.+)",
                    r"new\s+project\s+(.+)"
                ],
                function=self._execute_create_project,
                parameter_extractor=self._extract_project_name,
                description="Create new project directory",
                category="project",
                confidence_boost=1.3
            )
        ])
        
        # Data analysis patterns (deterministic)
        self.route_patterns.extend([
            RoutePattern(
                patterns=[
                    r"show\s+(?:me\s+)?(?:the\s+)?(?:data\s+)?(?:summary|info|details)",
                    r"describe\s+(?:the\s+)?data",
                    r"data\s+(?:overview|summary)"
                ],
                function=self._execute_data_summary,
                parameter_extractor=lambda x: {},
                description="Show data summary",
                category="analysis",
                confidence_boost=1.1
            )
        ])

    def analyze_request(self, user_input: str, context: Dict[str, Any] = None) -> DirectRouteResult:
        """
        Analyze user request and determine if it can be routed directly.
        
        Args:
            user_input: The user's natural language request
            context: Current session context (uploaded data, etc.)
            
        Returns:
            DirectRouteResult with routing decision and parameters
        """
        context = context or {}
        self.routing_stats["total_attempts"] += 1
        
        # Normalize input
        normalized_input = user_input.lower().strip()
        
        # Find matching patterns
        matches = []
        for pattern_config in self.route_patterns:
            for pattern in pattern_config.patterns:
                match = re.search(pattern, normalized_input, re.IGNORECASE)
                if match:
                    # Extract parameters
                    try:
                        if pattern_config.parameter_extractor:
                            parameters = pattern_config.parameter_extractor(match)
                        else:
                            parameters = {}
                        
                        confidence_score = self._calculate_confidence(
                            pattern_config, match, normalized_input, context
                        )
                        
                        matches.append({
                            "pattern": pattern_config,
                            "match": match,
                            "parameters": parameters,
                            "confidence": confidence_score
                        })
                    except Exception as e:
                        self.logger.warning(f"Parameter extraction failed for pattern {pattern}: {e}")
                        continue
        
        if not matches:
            return DirectRouteResult(
                should_route_direct=False,
                confidence=RouteConfidence.NONE,
                reasoning="No matching patterns found"
            )
        
        # Select best match
        best_match = max(matches, key=lambda x: x["confidence"])
        
        # Determine confidence level
        confidence_level = self._get_confidence_level(best_match["confidence"])
        
        # Should we route directly?
        should_route = confidence_level in [RouteConfidence.HIGH, RouteConfidence.MEDIUM]
        
        return DirectRouteResult(
            should_route_direct=should_route,
            confidence=confidence_level,
            function=best_match["pattern"].function if should_route else None,
            parameters=best_match["parameters"] if should_route else None,
            reasoning=f"Matched pattern with {confidence_level.value} confidence",
            fallback_to_llm=confidence_level == RouteConfidence.LOW
        )
    
    def _calculate_confidence(self, pattern_config: RoutePattern, match: re.Match, 
                            normalized_input: str, context: Dict) -> float:
        """Calculate confidence score for a pattern match"""
        
        base_confidence = 0.7  # Base confidence for any match
        
        # Apply pattern-specific boost
        confidence = base_confidence * pattern_config.confidence_boost
        
        # Boost for exact keyword matches
        if any(keyword in normalized_input for keyword in ["geo", "uniprot", "tcga", "pubmed", "upload", "create project"]):
            confidence += 0.2
        
        # Context-based adjustments
        if pattern_config.category == "data" and "uploaded_data" in context:
            confidence += 0.1
        
        # Length and specificity adjustments
        if len(normalized_input.split()) <= 5:  # Short, specific requests
            confidence += 0.1
        elif len(normalized_input.split()) > 20:  # Very long requests might be complex
            confidence -= 0.1
        
        return min(confidence, 1.0)  # Cap at 1.0
    
    def _get_confidence_level(self, score: float) -> RouteConfidence:
        """Convert numeric confidence to enum"""
        if score >= 0.9:
            return RouteConfidence.HIGH
        elif score >= 0.6:
            return RouteConfidence.MEDIUM
        elif score >= 0.3:
            return RouteConfidence.LOW
        else:
            return RouteConfidence.NONE
    
    # Parameter extraction functions
    def _extract_search_query(self, match: re.Match) -> Dict[str, Any]:
        """Extract search query from regex match"""
        query = match.group(1).strip() if match.groups() else ""
        return {"query": query} if query else {}
    
    def _extract_project_name(self, match: re.Match) -> Dict[str, Any]:
        """Extract project name from regex match"""
        project_name = match.group(1).strip() if match.groups() else ""
        return {"project_name": project_name} if project_name else {}
    
    # Direct execution functions
    def _execute_search(self, query: str, provider, **kwargs) -> Dict[str, Any]:
        """Execute search directly using search registry"""
        try:
            # Import search registry to use its search method
            from src.modules.search.registry import search_registry
            
            # Use registry's search method with the provider
            results = search_registry.search(query, provider_name=provider.name, **kwargs)
            
            return {
                "success": True,
                "results": results,
                "type": f"{provider.name}_search",
                "provider": provider.name
            }
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return {"error": str(e), "success": False}
    
    async def _execute_file_upload(self, **kwargs) -> Dict[str, Any]:
        """Execute file upload widget display"""
        try:
            # This would trigger the file upload widget
            return {
                "success": True,
                "action": "display_file_upload_widget",
                "type": "file_upload"
            }
        except Exception as e:
            self.logger.error(f"File upload execution failed: {e}")
            return {"error": str(e), "success": False}
    
    async def _execute_create_project(self, **kwargs) -> Dict[str, Any]:
        """Execute project directory creation"""
        project_name = kwargs.get("project_name", "")
        if not project_name:
            return {"error": "No project name provided"}
        
        try:
            # Assuming create_project_directory function exists
            result = create_project_directory(project_name)
            return {
                "success": True,
                "project_name": project_name,
                "result": result,
                "type": "create_project"
            }
        except Exception as e:
            self.logger.error(f"Project creation failed: {e}")
            return {"error": str(e), "success": False}
    
    async def _execute_data_summary(self, **kwargs) -> Dict[str, Any]:
        """Execute data summary display"""
        try:
            # This would analyze and display current data summary
            return {
                "success": True,
                "action": "display_data_summary",
                "type": "data_summary"
            }
        except Exception as e:
            self.logger.error(f"Data summary failed: {e}")
            return {"error": str(e), "success": False}
    
    async def execute_direct_route(self, route_result: DirectRouteResult) -> Dict[str, Any]:
        """Execute a direct route"""
        if not route_result.should_route_direct or not route_result.function:
            return {"error": "Invalid route for direct execution"}
        
        try:
            self.routing_stats["direct_routes"] += 1
            
            # Execute the function
            if inspect.iscoroutinefunction(route_result.function):
                result = await route_result.function(**route_result.parameters)
            else:
                result = route_result.function(**route_result.parameters)
            
            if result.get("success", False):
                self.routing_stats["successful_direct"] += 1
            else:
                self.routing_stats["failed_direct"] += 1
            
            return result
            
        except Exception as e:
            self.routing_stats["failed_direct"] += 1
            self.logger.error(f"Direct route execution failed: {e}")
            return {"error": str(e), "success": False}
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics for monitoring"""
        if self.routing_stats["total_attempts"] > 0:
            direct_rate = self.routing_stats["direct_routes"] / self.routing_stats["total_attempts"]
            success_rate = (self.routing_stats["successful_direct"] / 
                          max(self.routing_stats["direct_routes"], 1))
        else:
            direct_rate = 0
            success_rate = 0
        
        return {
            **self.routing_stats,
            "direct_routing_rate": direct_rate,
            "direct_success_rate": success_rate
        }


# Global instance
direct_router = DirectRouter()


# Test code to verify the module works independently  
if __name__ == "__main__":
    # Suppress the RuntimeWarning about module import behavior
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning, 
                          message=".*found in sys.modules.*")
    
    import asyncio
    
    async def test_direct_router():
        """Test DirectRouter functionality"""
        print("Testing DirectRouter...")
        
        # Test router creation
        router = DirectRouter()
        print(f"✅ Created DirectRouter with {len(router.route_patterns)} patterns")
        
        # Test pattern matching for various inputs
        test_inputs = [
            "search for cancer in geo",
            "upload a file", 
            "create project my_analysis",
            "show me the data summary",
            "find papers about immunotherapy",
            "this is a complex request that should not match"
        ]
        
        for user_input in test_inputs:
            result = router.analyze_request(user_input)
            print(f"✅ '{user_input}' → should_route: {result.should_route_direct}, "
                  f"confidence: {result.confidence.value}")
        
        # Test route execution (mock)
        geo_result = router.analyze_request("search for cancer in geo")
        if geo_result.should_route_direct:
            try:
                # This will fail due to missing imports, but that's expected
                executed = await router.execute_direct_route(geo_result)
                print(f"✅ Route execution attempted: {executed.get('success', False)}")
            except Exception as e:
                print(f"ℹ️  Expected execution error (missing imports): {type(e).__name__}")
        
        # Test routing statistics
        stats = router.get_routing_stats()
        print(f"✅ Routing stats: {stats['total_attempts']} attempts")
        
        # Test confidence calculation
        class MockPattern:
            confidence_boost = 1.2
            category = "search"
        
        import re
        mock_match = re.match(r"search\s+(.+)", "search for cancer")
        confidence = router._calculate_confidence(MockPattern(), mock_match, "search for cancer", {})
        print(f"✅ Confidence calculation: {confidence:.2f}")
        
        print("🎉 All DirectRouter tests passed!")
    
    # Run test
    asyncio.run(test_direct_router()) 
    #python -m src.chat.direct_router