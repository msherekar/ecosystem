"""
Scalable Hybrid Router - Combines multiple routing approaches

This solves the scalability problem by:
1. Configuration-driven rules (no hardcoded keywords)
2. ML-based intent classification 
3. Semantic similarity matching
4. Plugin architecture for new routing strategies
5. Learning from user feedback
"""

import asyncio
import logging
import yaml
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from .intent_classifier import intent_classifier, IntentResult
from .semantic_router import semantic_router, SemanticResult
from .hybrid_router import HybridRouter, RoutingStrategy, ExecutionResult

@dataclass
class ScalableRoutingResult:
    strategy: RoutingStrategy
    confidence: float
    reasoning: str
    method_used: str  # "config", "ml", "semantic", "hybrid"
    fallback_strategies: List[RoutingStrategy]

class ScalableRouter:
    """
    Scalable routing system that eliminates the need for hardcoded keywords.
    
    Features:
    - Configuration-driven routing rules
    - ML-based intent classification
    - Semantic similarity matching
    - Automatic learning from feedback
    - Plugin architecture for extensibility
    """
    
    def __init__(self, config_path: str = "src/chat/routing_config.yaml"):
        self.logger = logging.getLogger("scalable_router")
        self.config = {}
        self.hybrid_router = HybridRouter()
        
        # Load configuration
        self.load_config(config_path)
        
        # Performance tracking for different methods
        self.method_performance = {
            "config": {"success": 0, "total": 0},
            "ml": {"success": 0, "total": 0}, 
            "semantic": {"success": 0, "total": 0},
            "hybrid": {"success": 0, "total": 0}
        }
    
    def load_config(self, config_path: str):
        """Load routing configuration from YAML file"""
        try:
            if Path(config_path).exists():
                with open(config_path, 'r') as f:
                    self.config = yaml.safe_load(f)
                self.logger.info(f"Loaded routing config from {config_path}")
            else:
                self.logger.warning(f"Config file {config_path} not found, using defaults")
                self.config = self._get_default_config()
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            self.config = self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Get default configuration if file doesn't exist"""
        return {
            "routing_rules": {
                "plot_analysis": {
                    "priority": "high",
                    "strategy": "mcp",
                    "confidence_boost": 0.5,
                    "keywords": ["plot", "chart", "graph", "visualization"],
                    "patterns": ["analyze.*plot", "what.*plot", "explain.*chart"],
                    "tools_required": ["analyze_current_plots"]
                },
                "search_operations": {
                    "priority": "highest", 
                    "strategy": "direct",
                    "confidence_boost": 0.3,
                    "keywords": ["search", "find", "lookup"],
                    "patterns": ["search.*geo", "find.*uniprot"]
                }
            },
            "settings": {
                "cache_ttl": 300,
                "fallback_strategy": "llm",
                "enable_learning": True,
                "prefer_method": "auto"  # "config", "ml", "semantic", "auto"
            }
        }
    
    async def route_request(self, user_input: str, context: Dict = None) -> ScalableRoutingResult:
        """
        Route request using the most appropriate method.
        
        Method selection priority:
        1. Config-based rules (if high confidence match)
        2. ML intent classification
        3. Semantic similarity
        4. Fallback to hybrid router
        """
        context = context or {}
        
        # Try methods in order of preference
        methods = self._get_method_order()
        
        for method in methods:
            try:
                result = await self._try_routing_method(method, user_input, context)
                
                if result and result.confidence >= self._get_min_confidence(method):
                    self.logger.info(f"Routing via {method}: {result.strategy.value} (confidence: {result.confidence:.2f})")
                    return result
                
            except Exception as e:
                self.logger.error(f"Method {method} failed: {e}")
                continue
        
        # All methods failed - use fallback
        fallback_strategy = RoutingStrategy(self.config["settings"]["fallback_strategy"])
        return ScalableRoutingResult(
            strategy=fallback_strategy,
            confidence=0.3,
            reasoning="All routing methods failed, using fallback",
            method_used="fallback",
            fallback_strategies=[]
        )
    
    def _get_method_order(self) -> List[str]:
        """Get the order in which to try routing methods"""
        prefer_method = self.config["settings"].get("prefer_method", "auto")
        
        if prefer_method == "auto":
            # Dynamic ordering based on performance
            methods = ["config", "ml", "semantic", "hybrid"]
            
            # Sort by success rate
            def success_rate(method):
                perf = self.method_performance[method]
                if perf["total"] == 0:
                    return 0.5  # Unknown performance
                return perf["success"] / perf["total"]
            
            methods.sort(key=success_rate, reverse=True)
            return methods
        
        elif prefer_method in ["config", "ml", "semantic", "hybrid"]:
            # Prefer specific method but try others as fallback
            methods = [prefer_method]
            methods.extend([m for m in ["config", "ml", "semantic", "hybrid"] if m != prefer_method])
            return methods
        
        else:
            return ["config", "ml", "semantic", "hybrid"]
    
    def _get_min_confidence(self, method: str) -> float:
        """Get minimum confidence threshold for method"""
        thresholds = {
            "config": 0.7,
            "ml": 0.6,
            "semantic": 0.6,
            "hybrid": 0.4
        }
        return thresholds.get(method, 0.5)
    
    async def _try_routing_method(self, method: str, user_input: str, context: Dict) -> Optional[ScalableRoutingResult]:
        """Try a specific routing method"""
        
        if method == "config":
            return await self._config_based_routing(user_input, context)
        
        elif method == "ml":
            return await self._ml_based_routing(user_input, context)
        
        elif method == "semantic":
            return await self._semantic_based_routing(user_input, context)
        
        elif method == "hybrid":
            return await self._hybrid_based_routing(user_input, context)
        
        else:
            self.logger.error(f"Unknown routing method: {method}")
            return None
    
    async def _config_based_routing(self, user_input: str, context: Dict) -> Optional[ScalableRoutingResult]:
        """Route based on configuration rules"""
        
        user_lower = user_input.lower()
        best_match = None
        best_score = 0.0
        
        for rule_name, rule in self.config["routing_rules"].items():
            score = 0.0
            
            # Check keywords
            keywords = rule.get("keywords", [])
            keyword_matches = sum(1 for kw in keywords if kw in user_lower)
            if keywords:
                score += (keyword_matches / len(keywords)) * 0.5
            
            # Check patterns
            import re
            patterns = rule.get("patterns", [])
            pattern_matches = sum(1 for pattern in patterns if re.search(pattern, user_lower))
            if patterns:
                score += (pattern_matches / len(patterns)) * 0.3
            
            # Check context requirements
            context_req = rule.get("context_required", {})
            if context_req:
                context_matches = all(
                    context.get(key) in values if isinstance(values, list) else context.get(key) == values
                    for key, values in context_req.items()
                )
                if context_matches:
                    score += 0.2
            
            # Apply confidence boost
            confidence_boost = rule.get("confidence_boost", 0.0)
            score += confidence_boost
            
            if score > best_score:
                best_score = score
                best_match = rule
                best_match["rule_name"] = rule_name
        
        if best_match and best_score >= 0.6:
            strategy = RoutingStrategy(best_match["strategy"])
            reasoning = f"Config rule '{best_match['rule_name']}' matched (score: {best_score:.2f})"
            
            return ScalableRoutingResult(
                strategy=strategy,
                confidence=best_score,
                reasoning=reasoning,
                method_used="config",
                fallback_strategies=[RoutingStrategy.LLM]
            )
        
        return None
    
    async def _ml_based_routing(self, user_input: str, context: Dict) -> Optional[ScalableRoutingResult]:
        """Route using ML intent classification"""
        
        try:
            ml_result = intent_classifier.classify_intent(user_input, context)
            
            strategy = RoutingStrategy(ml_result.strategy)
            
            return ScalableRoutingResult(
                strategy=strategy,
                confidence=ml_result.confidence,
                reasoning=f"ML classification: {ml_result.intent} -> {ml_result.strategy}",
                method_used="ml",
                fallback_strategies=[RoutingStrategy.LLM]
            )
            
        except Exception as e:
            self.logger.error(f"ML routing failed: {e}")
            return None
    
    async def _semantic_based_routing(self, user_input: str, context: Dict) -> Optional[ScalableRoutingResult]:
        """Route using semantic similarity"""
        
        try:
            semantic_result = semantic_router.route_request(user_input, context)
            
            strategy = RoutingStrategy(semantic_result.strategy)
            
            return ScalableRoutingResult(
                strategy=strategy,
                confidence=semantic_result.confidence,
                reasoning=f"Semantic similarity: {semantic_result.reasoning}",
                method_used="semantic", 
                fallback_strategies=[RoutingStrategy.LLM]
            )
            
        except Exception as e:
            self.logger.error(f"Semantic routing failed: {e}")
            return None
    
    async def _hybrid_based_routing(self, user_input: str, context: Dict) -> Optional[ScalableRoutingResult]:
        """Route using original hybrid router as fallback"""
        
        try:
            # Initialize hybrid router if needed
            if not self.hybrid_router.router_initialized:
                await self.hybrid_router.initialize()
            
            # Use the existing hybrid router logic
            decision = await self.hybrid_router._analyze_routing_options(user_input, context)
            
            return ScalableRoutingResult(
                strategy=decision.strategy,
                confidence=decision.confidence,
                reasoning=f"Hybrid router: {decision.reasoning}",
                method_used="hybrid",
                fallback_strategies=decision.fallback_strategies
            )
            
        except Exception as e:
            self.logger.error(f"Hybrid routing failed: {e}")
            return None
    
    def learn_from_feedback(self, user_input: str, actual_strategy: str, success: bool, method_used: str):
        """Learn from user feedback to improve routing"""
        
        # Update performance metrics
        self.method_performance[method_used]["total"] += 1
        if success:
            self.method_performance[method_used]["success"] += 1
        
        # Add training examples based on feedback
        if success and method_used in ["ml", "semantic"]:
            if method_used == "ml":
                # Add to ML training data
                intent = self._strategy_to_intent(actual_strategy)
                intent_classifier.add_training_example(user_input, intent)
            
            elif method_used == "semantic":
                # Add to semantic examples
                intent = self._strategy_to_intent(actual_strategy)
                semantic_router.add_example(user_input, actual_strategy, intent)
        
        self.logger.info(f"Learned from feedback: '{user_input}' -> {actual_strategy} ({'success' if success else 'failure'})")
    
    def _strategy_to_intent(self, strategy: str) -> str:
        """Convert routing strategy to intent for learning"""
        mapping = {
            "mcp": "bio_analysis",
            "direct": "search_query", 
            "llm": "reasoning"
        }
        return mapping.get(strategy, "general")
    
    def add_routing_rule(self, rule_name: str, rule_config: Dict):
        """Add a new routing rule without code changes"""
        self.config["routing_rules"][rule_name] = rule_config
        self.logger.info(f"Added routing rule: {rule_name}")
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary for all routing methods"""
        summary = {}
        
        for method, perf in self.method_performance.items():
            if perf["total"] > 0:
                success_rate = perf["success"] / perf["total"]
                summary[method] = {
                    "success_rate": success_rate,
                    "total_requests": perf["total"],
                    "performance": "excellent" if success_rate > 0.9 else "good" if success_rate > 0.7 else "needs_improvement"
                }
            else:
                summary[method] = {"success_rate": 0.0, "total_requests": 0, "performance": "no_data"}
        
        return summary

# Global instance
scalable_router = ScalableRouter()

# Example of how to extend without code changes
async def demo_extensibility():
    """Demonstrate how easy it is to extend the router"""
    
    # Add new routing rule via configuration
    scalable_router.add_routing_rule("protein_analysis", {
        "priority": "high",
        "strategy": "mcp", 
        "confidence_boost": 0.4,
        "keywords": ["protein", "proteomics", "mass_spec"],
        "patterns": ["analyze.*protein", "proteomics.*pipeline"],
        "context_required": {"analysis_type": ["proteomics"]}
    })
    
    # Add new semantic examples
    semantic_router.add_example("analyze protein expression", "mcp", "protein_analysis", 0.9)
    semantic_router.add_example("run proteomics workflow", "mcp", "protein_analysis", 0.9)
    
    # Test the new capability
    result = await scalable_router.route_request(
        "analyze protein expression patterns",
        {"analysis_type": "proteomics"}
    )
    
    print(f"New capability: {result.strategy.value} via {result.method_used}")
    
if __name__ == "__main__":
    # Suppress the RuntimeWarning about module import behavior
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning, 
                          message=".*found in sys.modules.*")
    
    asyncio.run(demo_extensibility()) 