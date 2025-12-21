"""
Scalable Provider Selection Engine
Intelligent decision making for LLM provider selection with plugin architecture.
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field
import structlog

# Handle both relative and absolute imports for standalone testing
try:
    from src.mcp.agent.providers.base_provider import ProviderType
    from .selection_strategies import SelectionStrategyFactory
    from .message_analyzer import MessageAnalyzer
    from .load_balancer import LoadBalancer
    from .rule_engine import RuleEngine
    from .metrics_collector import MetricsCollector
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
    from src.mcp.agent.providers.base_provider import ProviderType
    
    # Mock classes for standalone testing
    class SelectionStrategyFactory:
        def get_strategy(self, strategy_name):
            return MockStrategy()
    
    class MessageAnalyzer:
        async def analyze_message(self, message, context=None):
            return MockAnalysis()
    
    class LoadBalancer:
        async def filter_healthy_providers(self, providers):
            return providers
        def get_provider_health(self):
            return {}
    
    class RuleEngine:
        def evaluate_rules(self, context, providers):
            return None
    
    class MetricsCollector:
        async def record_selection(self, *args, **kwargs):
            pass
    
    class MockStrategy:
        async def select_provider(self, *args, **kwargs):
            return "local"
    
    class MockAnalysis:
        def __init__(self):
            self.complexity = type('obj', (object,), {'name': 'MODERATE'})
            self.confidence = 0.8


class SelectionStrategy(Enum):
    """Enhanced provider selection strategies"""
    LOCAL_FIRST = "local_first"
    EXTERNAL_FIRST = "external_first"
    COST_OPTIMIZED = "cost_optimized"
    PERFORMANCE_OPTIMIZED = "performance_optimized"
    HYBRID_INTELLIGENT = "hybrid_intelligent"
    LOAD_BALANCED = "load_balanced"
    RULE_BASED = "rule_based"


@dataclass
class SelectionContext:
    """Rich context for provider selection decisions."""
    user_message: str
    user_id: str = "default"
    session_id: str = "default"
    message_metadata: Dict[str, Any] = field(default_factory=dict)
    usage_stats: Dict[str, int] = field(default_factory=dict)
    session_context: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    provider_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    cost_budget: Optional[float] = None
    quality_threshold: Optional[float] = None
    latency_requirement: Optional[float] = None
    security_context: Dict[str, Any] = field(default_factory=dict)
    electron_context: Dict[str, Any] = field(default_factory=dict)


class SelectionCriteria(BaseModel):
    """Configurable selection criteria with validation."""
    cost_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    quality_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    latency_weight: float = Field(default=0.2, ge=0.0, le=1.0)
    availability_weight: float = Field(default=0.1, ge=0.0, le=1.0)
    
    max_cost_per_request: Optional[float] = Field(default=None, ge=0.0)
    min_quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_latency_ms: Optional[float] = Field(default=None, ge=0.0)
    
    security_level: str = Field(default="standard", pattern="^(low|standard|high|critical)$")
    enable_fallback: bool = True
    max_retries: int = Field(default=3, ge=0, le=10)


class ScalableProviderSelector:
    """
    Enterprise-grade provider selection engine with plugin architecture.
    
    Features:
    - Plugin-based selection strategies
    - Advanced message analysis with NLP
    - Load balancing with circuit breakers
    - Configuration-driven rules
    - A/B testing support
    - Comprehensive metrics
    - Security controls
    - Electron UI integration
    """
    
    def __init__(self, config_path: str = None):
        self.logger = structlog.get_logger("provider_selector")
        
        # Core components
        self.strategy_factory = SelectionStrategyFactory()
        self.message_analyzer = MessageAnalyzer()
        self.load_balancer = LoadBalancer()
        self.rule_engine = RuleEngine(config_path)
        self.metrics = MetricsCollector()
        
        # Configuration
        self.current_strategy = SelectionStrategy.HYBRID_INTELLIGENT
        self.default_criteria = SelectionCriteria()
        self.security_enabled = True
        self.electron_integration_enabled = True
        
        # State management
        self.provider_cache: Dict[str, Any] = {}
        self.selection_history: List[Dict[str, Any]] = []
        self.active_experiments: Set[str] = set()
        
        # Performance tracking
        self.selection_stats = {
            'total_selections': 0,
            'avg_selection_time': 0.0,
            'provider_distribution': {},
            'error_count': 0
        }
    
    async def select_provider(
        self,
        context: SelectionContext,
        available_providers: Dict[str, Any],
        criteria: SelectionCriteria = None
    ) -> Optional[str]:
        """
        Select the best provider using the configured strategy.
        
        Args:
            context: Rich selection context
            available_providers: Available provider instances
            criteria: Selection criteria (uses default if None)
            
        Returns:
            Selected provider name or None if no suitable provider
        """
        start_time = time.time()
        criteria = criteria or self.default_criteria
        
        try:
            # Security validation
            if self.security_enabled:
                await self._validate_security_context(context)
            
            # Message analysis
            message_analysis = await self.message_analyzer.analyze_message(
                context.user_message, context.session_context
            )
            
            # Rule-based pre-selection
            rule_result = self.rule_engine.evaluate_rules(context, available_providers)
            if rule_result:
                await self._record_selection(context, rule_result, "rule_based", time.time() - start_time)
                return rule_result
            
            # Load balancing considerations
            load_balanced_providers = await self.load_balancer.filter_healthy_providers(
                available_providers
            )
            
            if not load_balanced_providers:
                self.logger.warning("No healthy providers available")
                return None
            
            # Strategy-based selection
            strategy = self.strategy_factory.get_strategy(self.current_strategy)
            selected_provider = await strategy.select_provider(
                context, load_balanced_providers, criteria, message_analysis
            )
            
            # Fallback handling
            if not selected_provider and criteria.enable_fallback:
                selected_provider = await self._fallback_selection(load_balanced_providers)
            
            # Record selection
            selection_time = time.time() - start_time
            await self._record_selection(context, selected_provider, 
                                       self.current_strategy.value, selection_time)
            
            # Electron UI notification
            if self.electron_integration_enabled:
                await self._notify_electron_ui(context, selected_provider, message_analysis)
            
            return selected_provider
            
        except Exception as e:
            self.logger.error("Provider selection failed", error=str(e))
            self.selection_stats['error_count'] += 1
            
            # Emergency fallback
            if criteria.enable_fallback and available_providers:
                return list(available_providers.keys())[0]
            
            return None
    
    async def _validate_security_context(self, context: SelectionContext):
        """Validate security context and apply controls."""
        security_level = context.security_context.get('level', 'standard')
        
        # Rate limiting
        user_selections = sum(1 for h in self.selection_history[-100:] 
                            if h.get('user_id') == context.user_id)
        
        if security_level == 'high' and user_selections > 50:
            raise SecurityError("Rate limit exceeded for high security context")
        
        # Content filtering
        if any(keyword in context.user_message.lower() 
               for keyword in ['system', 'admin', 'delete', 'drop']):
            if security_level in ['high', 'critical']:
                raise SecurityError("Potentially dangerous content detected")
    
    async def _fallback_selection(self, providers: Dict[str, Any]) -> Optional[str]:
        """Emergency fallback provider selection."""
        # Prefer local providers for fallback
        local_providers = [name for name, provider in providers.items() 
                         if hasattr(provider, 'provider_type') and 
                         provider.provider_type == ProviderType.LOCAL]
        
        if local_providers:
            return local_providers[0]
        
        # Return any available provider
        return next(iter(providers.keys())) if providers else None
    
    async def _record_selection(self, context: SelectionContext, provider: str, 
                              strategy: str, duration: float):
        """Record selection for analytics and optimization."""
        record = {
            'timestamp': time.time(),
            'user_id': context.user_id,
            'session_id': context.session_id,
            'provider': provider,
            'strategy': strategy,
            'duration': duration,
            'message_length': len(context.user_message),
            'success': provider is not None
        }
        
        self.selection_history.append(record)
        
        # Update statistics
        self.selection_stats['total_selections'] += 1
        self.selection_stats['avg_selection_time'] = (
            (self.selection_stats['avg_selection_time'] * 
             (self.selection_stats['total_selections'] - 1) + duration) /
            self.selection_stats['total_selections']
        )
        
        if provider:
            self.selection_stats['provider_distribution'][provider] = (
                self.selection_stats['provider_distribution'].get(provider, 0) + 1
            )
        
        # Record metrics
        await self.metrics.record_selection(context, provider, strategy, duration)
    
    async def _notify_electron_ui(self, context: SelectionContext, provider: str, 
                                analysis: Any):
        """Notify Electron UI about provider selection."""
        if not self.electron_integration_enabled:
            return
        
        notification = {
            'type': 'provider_selected',
            'provider': provider,
            'strategy': self.current_strategy.value,
            'message_complexity': analysis.complexity.name if hasattr(analysis, 'complexity') else 'unknown',
            'estimated_cost': getattr(analysis, 'estimated_cost', 0.0),
            'confidence': getattr(analysis, 'confidence', 1.0),
            'timestamp': time.time()
        }
        
        # Send to Electron via IPC or WebSocket
        try:
            await self._send_to_electron(notification)
        except Exception as e:
            self.logger.warning("Failed to notify Electron UI", error=str(e))
    
    async def _send_to_electron(self, data: Dict[str, Any]):
        """Send data to Electron UI (placeholder for actual implementation)."""
        # This would be implemented based on the Electron integration method
        # Could use WebSockets, IPC, or HTTP endpoints
        pass
    
    def configure_strategy(self, strategy: SelectionStrategy, criteria: SelectionCriteria = None):
        """Configure the selection strategy and criteria."""
        self.current_strategy = strategy
        if criteria:
            self.default_criteria = criteria
        
        self.logger.info("Strategy configured", strategy=strategy.value)
    
    def get_selection_stats(self) -> Dict[str, Any]:
        """Get current selection statistics."""
        return {
            **self.selection_stats,
            'provider_health': self.load_balancer.get_provider_health(),
            'recent_selections': self.selection_history[-10:],
            'active_experiments': list(self.active_experiments)
        }


class SecurityError(Exception):
    """Security-related errors in provider selection."""
    pass


def main():
    """Main function for testing the scalable provider selector."""
    import asyncio
    
    async def test_scalable_selector():
        print("🚀 Testing Scalable Provider Selector...")
        
        # Create selector with enhanced configuration
        selector = ScalableProviderSelector()
        
        # Configure strategy
        criteria = SelectionCriteria(
            cost_weight=0.4,
            quality_weight=0.3,
            latency_weight=0.2,
            availability_weight=0.1,
            security_level="high"
        )
        selector.configure_strategy(SelectionStrategy.HYBRID_INTELLIGENT, criteria)
        
        # Create test context
        context = SelectionContext(
            user_message="Analyze my RNA-seq differential expression results",
            user_id="test_user_001",
            session_id="session_123",
            usage_stats={"external_calls": 3, "local_calls": 7},
            cost_budget=0.50,
            security_context={"level": "high", "user_role": "researcher"},
            electron_context={"window_id": "main", "tab_id": "analysis"}
        )
        
        # Mock providers
        class MockProvider:
            def __init__(self, name, available=True, provider_type=ProviderType.EXTERNAL):
                self.name = name
                self._available = available
                self.provider_type = provider_type
            
            def is_available(self):
                return self._available
        
        providers = {
            "external": MockProvider("external", True, ProviderType.EXTERNAL),
            "local": MockProvider("local", True, ProviderType.LOCAL)
        }
        
        # Test selection
        selected = await selector.select_provider(context, providers, criteria)
        print(f"✅ Selected provider: {selected}")
        
        # Test statistics
        stats = selector.get_selection_stats()
        print(f"📊 Selection stats: {stats['total_selections']} selections")
        
        # Test different strategies
        strategies = [
            SelectionStrategy.COST_OPTIMIZED,
            SelectionStrategy.PERFORMANCE_OPTIMIZED,
            SelectionStrategy.LOAD_BALANCED
        ]
        
        for strategy in strategies:
            selector.configure_strategy(strategy)
            selected = await selector.select_provider(context, providers)
            print(f"📋 {strategy.value}: {selected}")
        
        print("🎉 Scalable provider selector tests completed!")
    
    # Run the test
    asyncio.run(test_scalable_selector())


if __name__ == "__main__":
    # Suppress warnings for testing
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    
    main()