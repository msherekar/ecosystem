"""
Metrics Collection System
Comprehensive metrics and analytics for provider selection.
"""

import time
import asyncio
from collections import defaultdict, deque
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import structlog

# Optional Prometheus integration
try:
    from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


@dataclass
class SelectionMetric:
    """Individual selection metric record."""
    timestamp: float
    user_id: str
    session_id: str
    provider: str
    strategy: str
    message_length: int
    complexity: str
    category: str
    duration: float
    success: bool
    cost: float = 0.0
    confidence: float = 1.0
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedMetrics:
    """Aggregated metrics for analysis."""
    total_selections: int = 0
    success_rate: float = 0.0
    avg_duration: float = 0.0
    avg_cost: float = 0.0
    provider_distribution: Dict[str, int] = field(default_factory=dict)
    strategy_distribution: Dict[str, int] = field(default_factory=dict)
    complexity_distribution: Dict[str, int] = field(default_factory=dict)
    hourly_volume: Dict[str, int] = field(default_factory=dict)
    error_rate: float = 0.0
    cost_efficiency: float = 0.0


class MetricsCollector:
    """
    Comprehensive metrics collection and analytics system.
    
    Features:
    - Real-time metrics collection
    - Prometheus integration
    - Historical data storage
    - Performance analytics
    - Cost tracking
    - User behavior analysis
    - A/B testing metrics
    - Export capabilities
    """
    
    def __init__(self, enable_prometheus: bool = True, retention_days: int = 30):
        self.logger = structlog.get_logger("metrics_collector")
        
        # Configuration
        self.enable_prometheus = enable_prometheus and PROMETHEUS_AVAILABLE
        self.retention_days = retention_days
        self.max_records = 10000  # Maximum records to keep in memory
        
        # Data storage
        self.selection_records: deque = deque(maxlen=self.max_records)
        self.aggregated_cache: Dict[str, AggregatedMetrics] = {}
        self.cache_expiry: Dict[str, float] = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Real-time counters
        self.counters = {
            'total_selections': 0,
            'successful_selections': 0,
            'failed_selections': 0,
            'total_cost': 0.0,
            'total_duration': 0.0
        }
        
        # Provider tracking
        self.provider_stats = defaultdict(lambda: {
            'selections': 0,
            'successes': 0,
            'total_duration': 0.0,
            'total_cost': 0.0,
            'last_used': 0.0
        })
        
        # User behavior tracking
        self.user_stats = defaultdict(lambda: {
            'selections': 0,
            'preferred_providers': defaultdict(int),
            'avg_message_length': 0.0,
            'total_cost': 0.0,
            'last_active': 0.0
        })
        
        # Prometheus metrics
        if self.enable_prometheus:
            self._setup_prometheus_metrics()
        
        # Background tasks
        self.cleanup_task = None
        self.aggregation_task = None
        self.is_running = False
    
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics collectors."""
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.registry = CollectorRegistry()
        
        # Selection metrics
        self.selection_counter = Counter(
            'provider_selections_total',
            'Total provider selections',
            ['provider', 'strategy', 'complexity', 'user_id'],
            registry=self.registry
        )
        
        self.selection_duration = Histogram(
            'provider_selection_duration_seconds',
            'Time spent selecting provider',
            ['strategy', 'provider'],
            registry=self.registry
        )
        
        self.selection_success_rate = Gauge(
            'provider_selection_success_rate',
            'Provider selection success rate',
            ['provider', 'strategy'],
            registry=self.registry
        )
        
        self.cost_per_selection = Histogram(
            'provider_selection_cost_dollars',
            'Cost per provider selection',
            ['provider', 'strategy'],
            registry=self.registry
        )
        
        self.active_users = Gauge(
            'active_users_count',
            'Number of active users',
            registry=self.registry
        )
        
        self.provider_health = Gauge(
            'provider_health_score',
            'Provider health score (0-1)',
            ['provider'],
            registry=self.registry
        )
    
    async def record_selection(
        self,
        context: 'SelectionContext',
        provider: str,
        strategy: str,
        duration: float,
        success: bool = True,
        additional_data: Dict[str, Any] = None
    ):
        """Record a provider selection event."""
        
        current_time = time.time()
        additional_data = additional_data or {}
        
        # Create selection record
        record = SelectionMetric(
            timestamp=current_time,
            user_id=context.user_id,
            session_id=context.session_id,
            provider=provider or "none",
            strategy=strategy,
            message_length=len(context.user_message),
            complexity=additional_data.get('complexity', 'unknown'),
            category=additional_data.get('category', 'unknown'),
            duration=duration,
            success=success,
            cost=additional_data.get('cost', 0.0),
            confidence=additional_data.get('confidence', 1.0),
            context=additional_data
        )
        
        # Store record
        self.selection_records.append(record)
        
        # Update real-time counters
        self.counters['total_selections'] += 1
        self.counters['total_duration'] += duration
        self.counters['total_cost'] += record.cost
        
        if success:
            self.counters['successful_selections'] += 1
        else:
            self.counters['failed_selections'] += 1
        
        # Update provider stats
        if provider:
            provider_stat = self.provider_stats[provider]
            provider_stat['selections'] += 1
            provider_stat['total_duration'] += duration
            provider_stat['total_cost'] += record.cost
            provider_stat['last_used'] = current_time
            
            if success:
                provider_stat['successes'] += 1
        
        # Update user stats
        user_stat = self.user_stats[context.user_id]
        user_stat['selections'] += 1
        user_stat['total_cost'] += record.cost
        user_stat['last_active'] = current_time
        
        if provider:
            user_stat['preferred_providers'][provider] += 1
        
        # Update average message length
        total_chars = user_stat['avg_message_length'] * (user_stat['selections'] - 1)
        user_stat['avg_message_length'] = (total_chars + record.message_length) / user_stat['selections']
        
        # Update Prometheus metrics
        if self.enable_prometheus:
            await self._update_prometheus_metrics(record)
        
        # Invalidate cache
        self._invalidate_cache()
        
        self.logger.debug("Selection recorded",
                         provider=provider,
                         strategy=strategy,
                         duration=duration,
                         success=success,
                         user_id=context.user_id)
    
    async def _update_prometheus_metrics(self, record: SelectionMetric):
        """Update Prometheus metrics with new record."""
        if not self.enable_prometheus:
            return
        
        # Increment selection counter
        self.selection_counter.labels(
            provider=record.provider,
            strategy=record.strategy,
            complexity=record.complexity,
            user_id=record.user_id
        ).inc()
        
        # Record duration
        self.selection_duration.labels(
            strategy=record.strategy,
            provider=record.provider
        ).observe(record.duration)
        
        # Record cost
        if record.cost > 0:
            self.cost_per_selection.labels(
                provider=record.provider,
                strategy=record.strategy
            ).observe(record.cost)
        
        # Update success rates
        provider_stat = self.provider_stats[record.provider]
        if provider_stat['selections'] > 0:
            success_rate = provider_stat['successes'] / provider_stat['selections']
            self.selection_success_rate.labels(
                provider=record.provider,
                strategy=record.strategy
            ).set(success_rate)
        
        # Update active users count
        recent_time = time.time() - 3600  # Last hour
        active_users = sum(1 for user_stat in self.user_stats.values()
                          if user_stat['last_active'] > recent_time)
        self.active_users.set(active_users)
    
    def get_aggregated_metrics(
        self, 
        time_window: Optional[Tuple[float, float]] = None,
        provider_filter: Optional[str] = None,
        user_filter: Optional[str] = None
    ) -> AggregatedMetrics:
        """Get aggregated metrics for specified filters."""
        
        # Create cache key
        cache_key = f"{time_window}_{provider_filter}_{user_filter}"
        
        # Check cache
        if (cache_key in self.aggregated_cache and 
            cache_key in self.cache_expiry and 
            time.time() < self.cache_expiry[cache_key]):
            return self.aggregated_cache[cache_key]
        
        # Filter records
        filtered_records = list(self.selection_records)
        
        if time_window:
            start_time, end_time = time_window
            filtered_records = [r for r in filtered_records 
                              if start_time <= r.timestamp <= end_time]
        
        if provider_filter:
            filtered_records = [r for r in filtered_records 
                              if r.provider == provider_filter]
        
        if user_filter:
            filtered_records = [r for r in filtered_records 
                              if r.user_id == user_filter]
        
        # Calculate aggregated metrics
        metrics = self._calculate_aggregated_metrics(filtered_records)
        
        # Cache result
        self.aggregated_cache[cache_key] = metrics
        self.cache_expiry[cache_key] = time.time() + self.cache_ttl
        
        return metrics
    
    def _calculate_aggregated_metrics(self, records: List[SelectionMetric]) -> AggregatedMetrics:
        """Calculate aggregated metrics from records."""
        
        if not records:
            return AggregatedMetrics()
        
        total_selections = len(records)
        successful_selections = sum(1 for r in records if r.success)
        
        # Basic metrics
        success_rate = successful_selections / total_selections if total_selections > 0 else 0
        avg_duration = sum(r.duration for r in records) / total_selections
        avg_cost = sum(r.cost for r in records) / total_selections
        
        # Distributions
        provider_dist = defaultdict(int)
        strategy_dist = defaultdict(int)
        complexity_dist = defaultdict(int)
        hourly_volume = defaultdict(int)
        
        for record in records:
            provider_dist[record.provider] += 1
            strategy_dist[record.strategy] += 1
            complexity_dist[record.complexity] += 1
            
            # Hour bucket
            hour = datetime.fromtimestamp(record.timestamp).strftime('%Y-%m-%d %H:00')
            hourly_volume[hour] += 1
        
        # Error rate
        error_rate = (total_selections - successful_selections) / total_selections if total_selections > 0 else 0
        
        # Cost efficiency (successful selections per dollar)
        total_cost = sum(r.cost for r in records)
        cost_efficiency = successful_selections / total_cost if total_cost > 0 else 0
        
        return AggregatedMetrics(
            total_selections=total_selections,
            success_rate=success_rate,
            avg_duration=avg_duration,
            avg_cost=avg_cost,
            provider_distribution=dict(provider_dist),
            strategy_distribution=dict(strategy_dist),
            complexity_distribution=dict(complexity_dist),
            hourly_volume=dict(hourly_volume),
            error_rate=error_rate,
            cost_efficiency=cost_efficiency
        )
    
    def get_provider_performance(self, provider_name: str) -> Dict[str, Any]:
        """Get detailed performance metrics for a specific provider."""
        
        provider_records = [r for r in self.selection_records if r.provider == provider_name]
        
        if not provider_records:
            return {}
        
        # Calculate metrics
        total_selections = len(provider_records)
        successful_selections = sum(1 for r in provider_records if r.success)
        success_rate = successful_selections / total_selections
        
        durations = [r.duration for r in provider_records]
        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)
        
        costs = [r.cost for r in provider_records]
        total_cost = sum(costs)
        avg_cost = total_cost / len(costs) if costs else 0
        
        # Recent performance (last 24 hours)
        recent_time = time.time() - 86400
        recent_records = [r for r in provider_records if r.timestamp > recent_time]
        recent_success_rate = (sum(1 for r in recent_records if r.success) / 
                             len(recent_records)) if recent_records else 0
        
        return {
            'provider': provider_name,
            'total_selections': total_selections,
            'success_rate': success_rate,
            'recent_success_rate': recent_success_rate,
            'avg_duration': avg_duration,
            'min_duration': min_duration,
            'max_duration': max_duration,
            'total_cost': total_cost,
            'avg_cost': avg_cost,
            'last_used': max(r.timestamp for r in provider_records),
            'usage_trend': self._calculate_usage_trend(provider_records)
        }
    
    def _calculate_usage_trend(self, records: List[SelectionMetric]) -> str:
        """Calculate usage trend for provider."""
        if len(records) < 10:
            return "insufficient_data"
        
        # Compare recent vs older usage
        mid_point = len(records) // 2
        recent_count = len(records[mid_point:])
        older_count = len(records[:mid_point])
        
        if recent_count > older_count * 1.2:
            return "increasing"
        elif recent_count < older_count * 0.8:
            return "decreasing"
        else:
            return "stable"
    
    def get_user_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get analytics for a specific user."""
        
        user_records = [r for r in self.selection_records if r.user_id == user_id]
        
        if not user_records:
            return {}
        
        # User-specific metrics
        total_selections = len(user_records)
        success_rate = sum(1 for r in user_records if r.success) / total_selections
        
        # Provider preferences
        provider_counts = defaultdict(int)
        for record in user_records:
            provider_counts[record.provider] += 1
        
        preferred_provider = max(provider_counts, key=provider_counts.get)
        
        # Usage patterns
        complexity_usage = defaultdict(int)
        for record in user_records:
            complexity_usage[record.complexity] += 1
        
        return {
            'user_id': user_id,
            'total_selections': total_selections,
            'success_rate': success_rate,
            'preferred_provider': preferred_provider,
            'provider_distribution': dict(provider_counts),
            'complexity_distribution': dict(complexity_usage),
            'avg_cost_per_selection': sum(r.cost for r in user_records) / total_selections,
            'total_cost': sum(r.cost for r in user_records),
            'first_seen': min(r.timestamp for r in user_records),
            'last_seen': max(r.timestamp for r in user_records)
        }
    
    def export_metrics(self, format: str = 'json') -> str:
        """Export metrics in specified format."""
        
        if format.lower() == 'prometheus' and self.enable_prometheus:
            return generate_latest(self.registry).decode('utf-8')
        
        elif format.lower() == 'json':
            export_data = {
                'timestamp': time.time(),
                'counters': self.counters,
                'provider_stats': dict(self.provider_stats),
                'recent_records': [
                    {
                        'timestamp': r.timestamp,
                        'provider': r.provider,
                        'strategy': r.strategy,
                        'success': r.success,
                        'duration': r.duration,
                        'cost': r.cost
                    }
                    for r in list(self.selection_records)[-100:]  # Last 100 records
                ]
            }
            return json.dumps(export_data, indent=2)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _invalidate_cache(self):
        """Invalidate aggregated metrics cache."""
        self.aggregated_cache.clear()
        self.cache_expiry.clear()
    
    async def start_background_tasks(self):
        """Start background maintenance tasks."""
        if self.is_running:
            return
        
        self.is_running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.aggregation_task = asyncio.create_task(self._aggregation_loop())
        
        self.logger.info("Background tasks started")
    
    async def stop_background_tasks(self):
        """Stop background maintenance tasks."""
        self.is_running = False
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
        if self.aggregation_task:
            self.aggregation_task.cancel()
        
        self.logger.info("Background tasks stopped")
    
    async def _cleanup_loop(self):
        """Background task for data cleanup."""
        while self.is_running:
            try:
                await self._cleanup_old_data()
                await asyncio.sleep(3600)  # Run every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Cleanup task error", error=str(e))
                await asyncio.sleep(60)
    
    async def _aggregation_loop(self):
        """Background task for metrics aggregation."""
        while self.is_running:
            try:
                await self._update_aggregated_metrics()
                await asyncio.sleep(300)  # Run every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Aggregation task error", error=str(e))
                await asyncio.sleep(60)
    
    async def _cleanup_old_data(self):
        """Clean up old data beyond retention period."""
        cutoff_time = time.time() - (self.retention_days * 86400)
        
        # Clean up selection records
        initial_count = len(self.selection_records)
        # Note: deque doesn't support efficient filtering, so we recreate it
        valid_records = [r for r in self.selection_records if r.timestamp > cutoff_time]
        self.selection_records.clear()
        self.selection_records.extend(valid_records)
        
        cleaned_count = initial_count - len(self.selection_records)
        
        if cleaned_count > 0:
            self.logger.info("Cleaned up old records", count=cleaned_count)
    
    async def _update_aggregated_metrics(self):
        """Update aggregated metrics cache."""
        # This could be expanded to pre-calculate common aggregations
        self._invalidate_cache()
        self.logger.debug("Aggregated metrics cache updated")


def main():
    """Main function for testing metrics collector."""
    import asyncio
    from dataclasses import dataclass
    
    @dataclass
    class MockContext:
        user_message: str
        user_id: str
        session_id: str
    
    async def test_metrics_collector():
        print("🧪 Testing Metrics Collector...")
        
        # Create metrics collector
        collector = MetricsCollector(enable_prometheus=False)
        
        # Start background tasks
        await collector.start_background_tasks()
        
        # Simulate selections
        contexts = [
            MockContext("What is RNA-seq?", "user1", "session1"),
            MockContext("Analyze my data", "user2", "session2"),
            MockContext("Help with clustering", "user1", "session3"),
            MockContext("Error in analysis", "user3", "session4"),
        ]
        
        providers = ["external", "local", "external", "local"]
        strategies = ["cost_optimized", "performance_optimized", "intelligent", "fallback"]
        
        print("📊 Recording test selections...")
        
        for i, (context, provider, strategy) in enumerate(zip(contexts, providers, strategies)):
            duration = 0.5 + (i * 0.2)
            success = i != 3  # Make last one fail
            cost = 0.01 if provider == "local" else 0.05
            
            await collector.record_selection(
                context=context,
                provider=provider,
                strategy=strategy,
                duration=duration,
                success=success,
                additional_data={
                    'complexity': 'moderate',
                    'category': 'analytical',
                    'cost': cost
                }
            )
            
            print(f"   Selection {i+1}: {provider} - {'✅' if success else '❌'}")
        
        # Get aggregated metrics
        print("\n📈 Aggregated Metrics:")
        metrics = collector.get_aggregated_metrics()
        
        print(f"   Total selections: {metrics.total_selections}")
        print(f"   Success rate: {metrics.success_rate:.2%}")
        print(f"   Avg duration: {metrics.avg_duration:.3f}s")
        print(f"   Avg cost: ${metrics.avg_cost:.4f}")
        print(f"   Provider distribution: {metrics.provider_distribution}")
        print(f"   Strategy distribution: {metrics.strategy_distribution}")
        
        # Get provider performance
        print("\n🔍 Provider Performance:")
        for provider in ["external", "local"]:
            perf = collector.get_provider_performance(provider)
            if perf:
                print(f"   {provider}: {perf['success_rate']:.2%} success, "
                      f"{perf['avg_duration']:.3f}s avg, ${perf['total_cost']:.4f} total")
        
        # Get user analytics
        print("\n👤 User Analytics:")
        for user_id in ["user1", "user2", "user3"]:
            analytics = collector.get_user_analytics(user_id)
            if analytics:
                print(f"   {user_id}: {analytics['total_selections']} selections, "
                      f"prefers {analytics['preferred_provider']}")
        
        # Export metrics
        print("\n📤 Export test:")
        json_export = collector.export_metrics('json')
        print(f"   JSON export size: {len(json_export)} bytes")
        
        # Stop background tasks
        await collector.stop_background_tasks()
        
        print("\n🎉 Metrics collector tests completed!")
    
    asyncio.run(test_metrics_collector())


if __name__ == "__main__":
    main() 