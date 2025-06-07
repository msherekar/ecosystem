"""
Hybrid Router - Orchestrates between Direct and LLM/MCP routing

This orchestrator decides whether to:
1. Route directly to local functions (fastest)
2. Route through MCP servers (structured)  
3. Route through LLM (most flexible)

Key Features:
- Performance optimization through route caching
- Context-aware routing decisions
- Fallback mechanisms
- Learning from routing success/failures
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

from .direct_router import DirectRouter, DirectRouteResult, RouteConfidence
from src.mcp.core.registry import get_mcp_registry
from src.mcp.agent.intelligent_router import IntelligentToolRouter


class RoutingStrategy(Enum):
    """Available routing strategies"""
    DIRECT = "direct"           # Direct to local functions
    MCP = "mcp"                # Through MCP servers
    LLM = "llm"                # Through LLM function calling
    HYBRID = "hybrid"           # Intelligent combination


@dataclass
class RouteDecision:
    """Result of routing decision analysis"""
    strategy: RoutingStrategy
    confidence: float
    reasoning: str
    estimated_latency: float  # in seconds
    fallback_strategies: List[RoutingStrategy]
    

@dataclass  
class ExecutionResult:
    """Result of route execution"""
    success: bool
    result: Any
    execution_time: float
    strategy_used: RoutingStrategy
    error: Optional[str] = None
    should_learn: bool = True


class HybridRouter:
    """
    Hybrid routing orchestrator that optimizes between different routing strategies.
    
    Routing Decision Logic:
    1. Try direct routing for simple, deterministic requests
    2. Use MCP for structured biological analysis
    3. Fall back to LLM for complex reasoning
    4. Learn from performance to optimize future decisions
    """
    
    def __init__(self):
        self.logger = logging.getLogger("hybrid_router")
        
        # Initialize routing components
        self.direct_router = DirectRouter()
        self.mcp_registry = None  # Will be initialized async
        self.intelligent_router = IntelligentToolRouter()
        
        # Performance tracking
        self.performance_metrics = {
            RoutingStrategy.DIRECT: {"total": 0, "success": 0, "avg_time": 0.0},
            RoutingStrategy.MCP: {"total": 0, "success": 0, "avg_time": 0.0}, 
            RoutingStrategy.LLM: {"total": 0, "success": 0, "avg_time": 0.0}
        }
        
        # Route caching for performance
        self.route_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Learning thresholds
        self.confidence_thresholds = {
            "direct_min": 0.6,
            "mcp_min": 0.4,
            "llm_fallback": 0.2
        }
    
    async def initialize(self) -> bool:
        """Initialize async components"""
        try:
            self.mcp_registry = await get_mcp_registry()
            await self.mcp_registry.initialize()
            self.logger.info("Hybrid router initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize hybrid router: {e}")
            return False
    
    async def route_request(self, user_input: str, context: Dict[str, Any] = None) -> ExecutionResult:
        """
        Main routing function - decides and executes the best routing strategy.
        
        Args:
            user_input: User's natural language request
            context: Session context (data, state, etc.)
            
        Returns:
            ExecutionResult with outcome and performance metrics
        """
        context = context or {}
        start_time = time.time()
        
        # Check cache first
        cache_key = self._generate_cache_key(user_input, context)
        if cache_key in self.route_cache:
            cached_decision = self.route_cache[cache_key]
            if time.time() - cached_decision["timestamp"] < self.cache_ttl:
                self.logger.debug(f"Using cached route decision for: {user_input[:50]}...")
                return await self._execute_cached_route(cached_decision, context)
        
        # Analyze routing options
        route_decision = await self._analyze_routing_options(user_input, context)
        
        # Cache the decision
        self.route_cache[cache_key] = {
            "decision": route_decision,
            "timestamp": time.time()
        }
        
        # Execute the chosen strategy
        result = await self._execute_route(route_decision, user_input, context)
        
        # Learn from the execution
        if result.should_learn:
            self._learn_from_execution(route_decision, result)
        
        # Update total execution time
        result.execution_time = time.time() - start_time
        
        return result
    
    async def _analyze_routing_options(self, user_input: str, context: Dict[str, Any]) -> RouteDecision:
        """
        Analyze all routing options and select the best strategy.
        
        Decision Process:
        1. Check if direct routing is viable (high confidence, simple request)
        2. Evaluate MCP routing for structured biological analysis
        3. Consider LLM routing for complex reasoning
        4. Apply performance-based learning adjustments
        """
        
        # Option 1: Direct routing analysis
        direct_result = self.direct_router.analyze_request(user_input, context)
        direct_score = self._score_direct_route(direct_result, context)
        
        # Option 2: MCP routing analysis  
        mcp_score = await self._score_mcp_route(user_input, context)
        
        # Option 3: LLM routing analysis
        llm_score = self._score_llm_route(user_input, context)
        
        # Apply performance-based adjustments
        adjusted_scores = self._adjust_scores_by_performance({
            RoutingStrategy.DIRECT: direct_score,
            RoutingStrategy.MCP: mcp_score,
            RoutingStrategy.LLM: llm_score
        })
        
        # Select best strategy
        best_strategy = max(adjusted_scores.items(), key=lambda x: x[1])
        strategy, confidence = best_strategy
        
        # Determine fallback strategies
        fallbacks = self._determine_fallbacks(strategy, adjusted_scores)
        
        # Estimate latency
        estimated_latency = self._estimate_latency(strategy, context)
        
        return RouteDecision(
            strategy=strategy,
            confidence=confidence,
            reasoning=self._generate_decision_reasoning(strategy, adjusted_scores),
            estimated_latency=estimated_latency,
            fallback_strategies=fallbacks
        )
    
    def _score_direct_route(self, direct_result: DirectRouteResult, context: Dict) -> float:
        """Score the viability of direct routing"""
        if not direct_result.should_route_direct:
            return 0.0
        
        # Base score from direct router confidence
        confidence_map = {
            RouteConfidence.HIGH: 0.9,
            RouteConfidence.MEDIUM: 0.7,
            RouteConfidence.LOW: 0.3,
            RouteConfidence.NONE: 0.0
        }
        base_score = confidence_map.get(direct_result.confidence, 0.0)
        
        # Boost for simple operations
        if direct_result.parameters and len(direct_result.parameters) <= 2:
            base_score += 0.1
        
        # Performance history boost
        if self.performance_metrics[RoutingStrategy.DIRECT]["success"] > 0:
            success_rate = (self.performance_metrics[RoutingStrategy.DIRECT]["success"] /
                           self.performance_metrics[RoutingStrategy.DIRECT]["total"])
            base_score *= (0.5 + 0.5 * success_rate)  # Boost based on historical success
        
        return min(base_score, 1.0)
    
    async def _score_mcp_route(self, user_input: str, context: Dict) -> float:
        """Score the viability of MCP routing"""
        if not self.mcp_registry:
            return 0.0
        
        base_score = 0.5  # Default MCP viability
        
        # Check if biological analysis is needed
        bio_keywords = ["scrna", "rnaseq", "proteomics", "cluster", "differential", "pathway"]
        if any(keyword in user_input.lower() for keyword in bio_keywords):
            base_score += 0.3
        
        # Check available MCP tools
        available_tools = self.mcp_registry.get_available_tools()
        if available_tools:
            base_score += 0.2
        
        # Context-based scoring
        if context.get("analysis_type") in ["scrnaseq", "rnaseq", "proteomics"]:
            base_score += 0.2
        
        if context.get("uploaded_data"):
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _score_llm_route(self, user_input: str, context: Dict) -> float:
        """Score the viability of LLM routing"""
        base_score = 0.6  # LLM can handle most requests
        
        # Boost for complex requests
        if len(user_input.split()) > 10:  # Longer requests might need reasoning
            base_score += 0.2
        
        # Boost for questions vs commands
        if user_input.strip().endswith('?'):
            base_score += 0.1
        
        # Reasoning keywords boost
        reasoning_keywords = ["why", "how", "explain", "compare", "analyze", "interpret"]
        if any(keyword in user_input.lower() for keyword in reasoning_keywords):
            base_score += 0.2
        
        return min(base_score, 1.0)
    
    def _adjust_scores_by_performance(self, scores: Dict[RoutingStrategy, float]) -> Dict[RoutingStrategy, float]:
        """Adjust scores based on historical performance"""
        adjusted = {}
        
        for strategy, score in scores.items():
            if self.performance_metrics[strategy]["total"] > 0:
                success_rate = (self.performance_metrics[strategy]["success"] /
                              self.performance_metrics[strategy]["total"])
                avg_time = self.performance_metrics[strategy]["avg_time"]
                
                # Adjust based on success rate
                score *= (0.3 + 0.7 * success_rate)
                
                # Adjust based on speed (prefer faster methods)
                if avg_time > 0:
                    speed_factor = max(0.5, 1.0 - (avg_time / 10.0))  # Penalize if >10s
                    score *= speed_factor
            
            adjusted[strategy] = score
        
        return adjusted
    
    def _determine_fallbacks(self, primary: RoutingStrategy, scores: Dict[RoutingStrategy, float]) -> List[RoutingStrategy]:
        """Determine fallback strategies in order of preference"""
        sorted_strategies = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        fallbacks = [s[0] for s in sorted_strategies if s[0] != primary and s[1] > 0.1]
        return fallbacks[:2]  # Top 2 fallbacks
    
    def _estimate_latency(self, strategy: RoutingStrategy, context: Dict) -> float:
        """Estimate execution latency for strategy"""
        base_latencies = {
            RoutingStrategy.DIRECT: 0.1,   # Very fast
            RoutingStrategy.MCP: 0.5,      # Medium
            RoutingStrategy.LLM: 2.0       # Slower due to LLM inference
        }
        
        base = base_latencies.get(strategy, 1.0)
        
        # Adjust based on historical performance
        if self.performance_metrics[strategy]["total"] > 0:
            avg_time = self.performance_metrics[strategy]["avg_time"]
            if avg_time > 0:
                return avg_time
        
        return base
    
    def _generate_decision_reasoning(self, strategy: RoutingStrategy, scores: Dict) -> str:
        """Generate human-readable reasoning for routing decision"""
        score = scores[strategy]
        
        if strategy == RoutingStrategy.DIRECT:
            return f"Direct routing selected (confidence: {score:.2f}) - simple, deterministic operation"
        elif strategy == RoutingStrategy.MCP:
            return f"MCP routing selected (confidence: {score:.2f}) - structured biological analysis"
        elif strategy == RoutingStrategy.LLM:
            return f"LLM routing selected (confidence: {score:.2f}) - complex reasoning required"
        else:
            return f"{strategy.value} routing selected (confidence: {score:.2f})"
    
    async def _execute_route(self, decision: RouteDecision, user_input: str, context: Dict) -> ExecutionResult:
        """Execute the chosen routing strategy with fallbacks"""
        strategies_to_try = [decision.strategy] + decision.fallback_strategies
        
        for strategy in strategies_to_try:
            try:
                start_time = time.time()
                result = await self._execute_strategy(strategy, user_input, context)
                execution_time = time.time() - start_time
                
                if result.get("success", False):
                    return ExecutionResult(
                        success=True,
                        result=result,
                        execution_time=execution_time,
                        strategy_used=strategy
                    )
                else:
                    # Log failure but try next strategy
                    self.logger.warning(f"{strategy.value} routing failed: {result.get('error', 'Unknown error')}")
                    continue
                    
            except Exception as e:
                self.logger.error(f"{strategy.value} routing exception: {e}")
                continue
        
        # All strategies failed
        return ExecutionResult(
            success=False,
            result={"error": "All routing strategies failed"},
            execution_time=0.0,
            strategy_used=decision.strategy,
            error="All strategies exhausted"
        )
    
    async def _execute_strategy(self, strategy: RoutingStrategy, user_input: str, context: Dict) -> Dict[str, Any]:
        """Execute a specific routing strategy"""
        
        if strategy == RoutingStrategy.DIRECT:
            # Execute direct routing
            direct_result = self.direct_router.analyze_request(user_input, context)
            if direct_result.should_route_direct:
                return await self.direct_router.execute_direct_route(direct_result)
            else:
                return {"success": False, "error": "Direct routing not viable"}
        
        elif strategy == RoutingStrategy.MCP:
            # Execute MCP routing
            if not self.mcp_registry:
                return {"success": False, "error": "MCP registry not available"}
            
            # Use intelligent tool selection and execution
            context_result = await self.intelligent_router.analyze_biological_context(user_input, context)
            tool_selection = await self.intelligent_router.dynamic_tool_selection(context_result)
            
            # Execute through MCP registry (simplified - you'd implement actual tool execution)
            return {"success": True, "result": "MCP execution completed", "tools": tool_selection.tools}
        
        elif strategy == RoutingStrategy.LLM:
            # Execute LLM routing (integrate with your existing LLM function calling)
            # This would use your existing schema.py tools with OpenAI function calling
            return {"success": True, "result": "LLM execution completed", "method": "function_calling"}
        
        else:
            return {"success": False, "error": f"Unknown strategy: {strategy}"}
    
    def _learn_from_execution(self, decision: RouteDecision, result: ExecutionResult):
        """Learn from execution results to improve future routing decisions"""
        strategy = result.strategy_used
        
        # Update performance metrics
        self.performance_metrics[strategy]["total"] += 1
        
        if result.success:
            self.performance_metrics[strategy]["success"] += 1
        
        # Update average execution time
        current_avg = self.performance_metrics[strategy]["avg_time"]
        total = self.performance_metrics[strategy]["total"]
        new_avg = (current_avg * (total - 1) + result.execution_time) / total
        self.performance_metrics[strategy]["avg_time"] = new_avg
        
        # Adjust confidence thresholds based on performance
        if strategy == RoutingStrategy.DIRECT:
            success_rate = (self.performance_metrics[strategy]["success"] / 
                           self.performance_metrics[strategy]["total"])
            if success_rate < 0.7 and self.confidence_thresholds["direct_min"] < 0.8:
                self.confidence_thresholds["direct_min"] += 0.05  # Be more conservative
            elif success_rate > 0.9 and self.confidence_thresholds["direct_min"] > 0.4:
                self.confidence_thresholds["direct_min"] -= 0.05  # Be more aggressive
    
    def _generate_cache_key(self, user_input: str, context: Dict) -> str:
        """Generate cache key for routing decisions"""
        # Simple hash-based key (you might want to use more sophisticated hashing)
        context_sig = str(sorted(context.items())) if context else ""
        return f"{user_input.lower().strip()}_{hash(context_sig)}"
    
    async def _execute_cached_route(self, cached_decision: Dict, context: Dict) -> ExecutionResult:
        """Execute a cached routing decision"""
        # This is a simplified implementation - you'd want to validate cache validity
        decision = cached_decision["decision"]
        return ExecutionResult(
            success=True,
            result={"cached": True, "strategy": decision.strategy.value},
            execution_time=0.01,  # Very fast cache hit
            strategy_used=decision.strategy
        )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for monitoring and optimization"""
        return {
            "metrics": self.performance_metrics,
            "thresholds": self.confidence_thresholds,
            "cache_size": len(self.route_cache),
            "routing_stats": self.direct_router.get_routing_stats()
        }


# Global instance
hybrid_router = HybridRouter() 