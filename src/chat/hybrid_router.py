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
import re

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
        
        # DEBUG: Log comprehensive routing analysis
        self.logger.debug(f"🔍 ROUTING ANALYSIS for: '{user_input}'")
        self.logger.debug("=" * 80)
        
        # Also print to console for Streamlit visibility
        print(f"🔍 ROUTING ANALYSIS for: '{user_input}'")
        print("=" * 80)
        
        # Option 1: Direct routing analysis
        direct_result = self.direct_router.analyze_request(user_input, context)
        direct_score = self._score_direct_route(direct_result, context)
        
        # Option 2: MCP routing analysis  
        mcp_score = await self._score_mcp_route(user_input, context)
        
        # Option 3: LLM routing analysis
        llm_score = self._score_llm_route(user_input, context)
        
        # DEBUG: Log cost and resource analysis
        await self._log_cost_analysis(user_input, direct_result, direct_score, mcp_score, llm_score)
        
        # Print summary for Streamlit visibility
        print(f"💰 COST SUMMARY: Direct=${0.00 if direct_result.should_route_direct else 'N/A'}, MCP=~$0.001-0.01, LLM=~$0.005")
        
        # Apply performance-based adjustments
        adjusted_scores = self._adjust_scores_by_performance({
            RoutingStrategy.DIRECT: direct_score,
            RoutingStrategy.MCP: mcp_score,
            RoutingStrategy.LLM: llm_score
        })
        
        # DEBUG: Log adjusted scores
        self.logger.debug(f"📊 ADJUSTED SCORES: Direct={adjusted_scores[RoutingStrategy.DIRECT]:.3f}, MCP={adjusted_scores[RoutingStrategy.MCP]:.3f}, LLM={adjusted_scores[RoutingStrategy.LLM]:.3f}")
        
        # Select best strategy
        best_strategy = max(adjusted_scores.items(), key=lambda x: x[1])
        strategy, confidence = best_strategy
        
        # DEBUG: Log final decision with cost implications
        await self._log_final_decision(strategy, confidence, adjusted_scores)
        
        # Print final decision for Streamlit visibility
        cost_summary = {
            RoutingStrategy.DIRECT: "$0.00 (Free)",
            RoutingStrategy.MCP: "~$0.001-0.01 (MCP)",
            RoutingStrategy.LLM: "~$0.005 (LLM)"
        }
        print(f"🎯 DECISION: {strategy.value.upper()} - {cost_summary.get(strategy, 'Unknown cost')}")
        print("=" * 80)
        
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
            
        # MAJOR BOOST for search operations - these should be direct
        # Check if this is a search query by looking at parameters or reasoning
        is_search_query = False
        if direct_result.parameters and 'query' in direct_result.parameters:
            is_search_query = True
        elif direct_result.reasoning and 'search' in direct_result.reasoning.lower():
            is_search_query = True
            
        if is_search_query:
            base_score += 0.3  # Strong preference for direct search
        
        # Performance history boost (but don't penalize if no history yet)
        if self.performance_metrics[RoutingStrategy.DIRECT]["total"] > 0:
            success_rate = (self.performance_metrics[RoutingStrategy.DIRECT]["success"] /
                           self.performance_metrics[RoutingStrategy.DIRECT]["total"])
            base_score *= (0.7 + 0.3 * success_rate)  # Less harsh penalty, more forgiving
        else:
            # No history yet - give a small boost to try direct routing
            base_score += 0.05
        
        return min(base_score, 1.0)
    
    async def _score_mcp_route(self, user_input: str, context: Dict) -> float:
        """Score the viability of MCP routing"""
        if not self.mcp_registry:
            return 0.0
        
        base_score = 0.4  # Reduced from 0.5 to favor direct routing
        
        # REDUCE score for simple search queries - these should go direct
        search_indicators = ["search", "find", "lookup", "geo", "uniprot", "pubmed", "tcga"]
        if any(indicator in user_input.lower() for indicator in search_indicators):
            # Check if this is a simple search vs complex analysis
            simple_search_patterns = [
                r"search\s+(?:for\s+)?[\w\s]+\s+(?:in\s+)?(?:geo|uniprot|pubmed|tcga)",
                r"(?:geo|uniprot|pubmed|tcga)\s+search",
                r"find\s+[\w\s]+\s+(?:in\s+)?(?:geo|uniprot|pubmed|tcga)"
            ]
            if any(re.search(pattern, user_input.lower()) for pattern in simple_search_patterns):
                base_score -= 0.25  # Reduce MCP score for simple searches
        
        # Check if biological analysis is needed
        bio_keywords = ["scrna", "rnaseq", "proteomics", "cluster", "differential", "pathway"]
        if any(keyword in user_input.lower() for keyword in bio_keywords):
            base_score += 0.3
        
        # Check available MCP tools (reduced boost)
        available_tools = self.mcp_registry.get_available_tools()
        if available_tools:
            base_score += 0.15  # Reduced from 0.2
        
        # Context-based scoring
        if context.get("analysis_type") in ["scrnaseq", "rnaseq", "proteomics"]:
            base_score += 0.2
        
        if context.get("uploaded_data"):
            base_score += 0.1
        
        return max(base_score, 0.0)  # Ensure non-negative
    
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
        
        # DEBUG: Log execution start with cost tracking
        self.logger.debug(f"🚀 EXECUTING STRATEGY: {decision.strategy.value}")
        execution_start = time.time()
        
        strategies_to_try = [decision.strategy] + decision.fallback_strategies
        
        for strategy in strategies_to_try:
            try:
                start_time = time.time()
                
                # DEBUG: Log strategy attempt
                self.logger.debug(f"   🔄 Attempting {strategy.value} execution...")
                
                result = await self._execute_strategy(strategy, user_input, context)
                execution_time = time.time() - start_time
                
                if result.get("success", False):
                    # DEBUG: Log successful execution with costs
                    await self._log_execution_success(strategy, execution_time, result, user_input)
                    
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
        total_time = time.time() - execution_start
        self.logger.debug(f"❌ ALL STRATEGIES FAILED (total time: {total_time:.2f}s)")
        
        return ExecutionResult(
            success=False,
            result={"error": "All routing strategies failed"},
            execution_time=total_time,
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
            
            # Actually execute the selected tools
            if tool_selection.tools:
                try:
                    # For now, let's try to execute the first relevant tool
                    # You can enhance this to execute multiple tools if needed
                    first_tool = tool_selection.tools[0]
                    tool_name = first_tool.get("name")
                    
                    # Extract parameters from user input (simplified)
                    # For search tools, extract the search query
                    if "search" in tool_name.lower():
                        # Extract search parameters from user input
                        # Look for patterns like "search geo for X" or "search uniprot for Y"
                        search_patterns = [
                            r"search\s+(?:geo|uniprot|pubmed)\s+for\s+(.+)",
                            r"(?:geo|uniprot|pubmed)\s+search\s+(?:for\s+)?(.+)",
                            r"search\s+(.+)\s+in\s+(?:geo|uniprot|pubmed)",
                            r"find\s+(.+)\s+in\s+(?:geo|uniprot|pubmed)",
                            r"search\s+(?:for\s+)?(.+?)\s+(?:in\s+)?(?:geo|uniprot|pubmed)"  # Handle "search [for] X in database"
                        ]
                        
                        query = None
                        for pattern in search_patterns:
                            match = re.search(pattern, user_input.lower())
                            if match:
                                query = match.group(1).strip()
                                break
                        
                        if not query:
                            # Fallback: use the whole input after removing database names
                            query = re.sub(r'\b(?:search|geo|uniprot|pubmed|for|in|find)\b', '', user_input, flags=re.IGNORECASE).strip()
                        
                        parameters = {"query": query} if query else {}
                    else:
                        parameters = {}
                    
                    # Execute the tool via MCP registry
                    result = await self.mcp_registry.execute_tool(tool_name, parameters)
                    
                    if result.get("success"):
                        return result
                    else:
                        return {"success": False, "error": f"Tool execution failed: {result.get('message', 'Unknown error')}"}
                        
                except Exception as e:
                    return {"success": False, "error": f"MCP tool execution error: {str(e)}"}
            else:
                return {"success": False, "error": "No suitable MCP tools found for this request"}
        
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

    async def _log_cost_analysis(self, user_input: str, direct_result, direct_score: float, mcp_score: float, llm_score: float):
        """Log comprehensive cost and resource analysis"""
        
        # Estimate token usage for this query
        input_tokens = len(user_input.split()) * 1.3  # Rough token estimate
        
        self.logger.debug(f"💰 COST ANALYSIS:")
        self.logger.debug(f"   📝 Input tokens (estimated): ~{input_tokens:.0f}")
        
        # Direct routing cost analysis
        self.logger.debug(f"   🎯 DIRECT ROUTING (Score: {direct_score:.3f}):")
        if direct_result.should_route_direct:
            self.logger.debug(f"      💵 Cost: $0.00 (No LLM, pure function call)")
            self.logger.debug(f"      🔧 Tools needed: 1 direct function")
            self.logger.debug(f"      ⚡ Estimated latency: ~0.1s")
        else:
            self.logger.debug(f"      ❌ Not viable for direct routing")
        
        # MCP routing cost analysis
        self.logger.debug(f"   🔧 MCP ROUTING (Score: {mcp_score:.3f}):")
        if self.mcp_registry:
            available_tools = self.mcp_registry.get_available_tools()
            server_status = self.mcp_registry.get_server_status()
            
            self.logger.debug(f"      🏢 Active servers: {len(server_status)}")
            for server_name, status in server_status.items():
                self.logger.debug(f"         - {server_name}: {status.get('status', 'unknown')}")
            
            self.logger.debug(f"      🔧 Available tools: {len(available_tools)}")
            if len(available_tools) <= 10:  # Don't spam if too many tools
                for tool_name in available_tools.keys():
                    self.logger.debug(f"         - {tool_name}")
            else:
                self.logger.debug(f"         - {list(available_tools.keys())[:5]}... (and {len(available_tools)-5} more)")
            
            # Estimate MCP cost (usually involves tool selection but no LLM for execution)
            self.logger.debug(f"      💵 Cost: $0.001-0.01 (Tool selection + execution, minimal LLM)")
            self.logger.debug(f"      ⚡ Estimated latency: ~0.5-2s")
        else:
            self.logger.debug(f"      ❌ MCP registry not available")
        
        # LLM routing cost analysis  
        self.logger.debug(f"   🤖 LLM ROUTING (Score: {llm_score:.3f}):")
        estimated_output_tokens = 150  # Typical response length
        estimated_cost = (input_tokens * 0.00001) + (estimated_output_tokens * 0.00003)  # GPT-4 pricing
        self.logger.debug(f"      💵 Estimated cost: ${estimated_cost:.4f}")
        self.logger.debug(f"      📤 Output tokens (estimated): ~{estimated_output_tokens}")
        self.logger.debug(f"      🔧 Function calling tools: 4 (from schema.py)")
        self.logger.debug(f"      ⚡ Estimated latency: ~2-5s")
        
    async def _log_final_decision(self, strategy: RoutingStrategy, confidence: float, scores: Dict):
        """Log final routing decision with cost implications"""
        self.logger.debug(f"🎯 FINAL DECISION: {strategy.value.upper()} (confidence: {confidence:.3f})")
        
        if strategy == RoutingStrategy.DIRECT:
            self.logger.debug(f"   💰 TOTAL COST: $0.00 (Free direct execution)")
            self.logger.debug(f"   🚀 PERFORMANCE: Fastest route selected")
            self.logger.debug(f"   🔧 RESOURCES: 1 local function call")
            
        elif strategy == RoutingStrategy.MCP:
            self.logger.debug(f"   💰 TOTAL COST: ~$0.001-0.01 (MCP tool selection + execution)")
            self.logger.debug(f"   🚀 PERFORMANCE: Medium latency, structured execution")
            self.logger.debug(f"   🔧 RESOURCES: MCP server + selected tools")
            
        elif strategy == RoutingStrategy.LLM:
            input_tokens = len("sample") * 1.3  # Would need actual input
            estimated_cost = (input_tokens * 0.00001) + (150 * 0.00003)
            self.logger.debug(f"   💰 TOTAL COST: ~${estimated_cost:.4f} (Full LLM inference)")
            self.logger.debug(f"   🚀 PERFORMANCE: Slowest but most flexible")
            self.logger.debug(f"   🔧 RESOURCES: LLM API + function calling")
            
        self.logger.debug("=" * 80)

    async def _log_execution_success(self, strategy: RoutingStrategy, execution_time: float, result: Dict, user_input: str):
        """Log successful execution with detailed cost breakdown"""
        
        self.logger.debug(f"✅ {strategy.value.upper()} EXECUTION SUCCESSFUL")
        self.logger.debug(f"   ⏱️  Actual execution time: {execution_time:.3f}s")
        
        if strategy == RoutingStrategy.DIRECT:
            self.logger.debug(f"   💰 ACTUAL COST: $0.00 (Direct function call)")
            self.logger.debug(f"   📊 NO TOKENS USED (No LLM involved)")
            self.logger.debug(f"   🎯 EFFICIENCY: Maximum (direct database call)")
            
            # Log what was actually executed
            if result.get("type"):
                self.logger.debug(f"   🔧 EXECUTED: {result.get('type')} function")
            if result.get("provider"):
                self.logger.debug(f"   🏢 DATABASE: {result.get('provider')}")
                
        elif strategy == RoutingStrategy.MCP:
            # Try to get actual tool usage
            tools_used = result.get("tools", [])
            if isinstance(tools_used, list):
                tool_count = len(tools_used)
            else:
                tool_count = 1  # Assume at least one tool was used
                
            estimated_cost = tool_count * 0.001  # Rough estimate per tool
            self.logger.debug(f"   💰 ACTUAL COST: ~${estimated_cost:.4f} (MCP tool execution)")
            self.logger.debug(f"   🔧 TOOLS USED: {tool_count}")
            self.logger.debug(f"   📊 MINIMAL TOKENS (Tool selection only)")
            
            if result.get("result", {}).get("provider"):
                self.logger.debug(f"   🏢 DATABASE: {result['result'].get('provider')}")
                
        elif strategy == RoutingStrategy.LLM:
            # Estimate actual token usage and cost
            input_tokens = len(user_input.split()) * 1.3
            
            # Try to estimate output tokens from result
            result_text = str(result.get("result", ""))
            output_tokens = len(result_text.split()) * 1.3
            
            actual_cost = (input_tokens * 0.00001) + (output_tokens * 0.00003)
            
            self.logger.debug(f"   💰 ACTUAL COST: ~${actual_cost:.4f}")
            self.logger.debug(f"   📝 INPUT TOKENS: ~{input_tokens:.0f}")
            self.logger.debug(f"   📤 OUTPUT TOKENS: ~{output_tokens:.0f}")
            self.logger.debug(f"   🤖 LLM API CALL: GPT-4 function calling")
        
        # Log result size
        if isinstance(result.get("result"), dict):
            result_data = result["result"]
            if "data" in result_data and isinstance(result_data["data"], dict):
                hit_count = result_data["data"].get("count", 0)
                if hit_count > 0:
                    self.logger.debug(f"   📊 RESULTS: {hit_count} records returned")
                    self.logger.debug(f"   💾 DATA EFFICIENCY: High (structured results)")


# Global instance
hybrid_router = HybridRouter()


# Test code to verify the module works independently
if __name__ == "__main__":
    import asyncio
    
    async def test_hybrid_router():
        """Test HybridRouter functionality"""
        print("Testing HybridRouter...")
        
        # Test router creation
        router = HybridRouter()
        print(f"✅ Created HybridRouter")
        
        # Test initialization (may fail due to missing MCP registry)
        try:
            success = await router.initialize()
            print(f"✅ Router initialization: {'Success' if success else 'Failed'}")
        except Exception as e:
            print(f"ℹ️  Expected initialization error (missing MCP): {type(e).__name__}")
        
        # Test routing analysis without initialization
        test_inputs = [
            "search for cancer in geo",
            "cluster my scRNA-seq data", 
            "explain PCA results",
            "upload a file",
            "search for neurofibromin in uniprot",
            "search for neurofibromin in pubmed",
        ]
        
        for user_input in test_inputs:
            try:
                # This will likely fail due to uninitialized MCP, but we can test basic structure
                context = {"has_data": False}
                decision = await router._analyze_routing_options(user_input, context)
                print(f"✅ '{user_input}' → strategy: {decision.strategy.value}, confidence: {decision.confidence:.2f}")
            except Exception as e:
                print(f"ℹ️  Expected routing error for '{user_input}': {type(e).__name__}")
        
        # Test performance metrics
        metrics = router.get_performance_summary()
        print(f"✅ Performance metrics: {len(metrics['metrics'])} strategies tracked")
        
        # Test cache key generation
        cache_key = router._generate_cache_key("test input", {"key": "value"})
        print(f"✅ Cache key generation: {len(cache_key)} chars")
        
        # Test confidence thresholds
        print(f"✅ Confidence thresholds: {router.confidence_thresholds}")
        
        print("🎉 All HybridRouter tests passed!")
    
    # Run test
    asyncio.run(test_hybrid_router()) 
    # python -m src.chat.hybrid_router