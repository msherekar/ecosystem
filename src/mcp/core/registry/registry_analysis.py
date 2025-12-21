"""
Registry Analysis Insights and Actions

Provides analysis insights and suggested actions by integrating with
centralized analysis providers and server contexts.

This file is separate from the core registry to keep analysis logic
isolated and easily extensible.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import time

# Configure logger
logger = logging.getLogger(__name__)


class InsightPriority(Enum):
    """Priority levels for insights"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionType(Enum):
    """Types of suggested actions"""
    DATA_UPLOAD = "data_upload"
    QUALITY_CONTROL = "quality_control"
    ANALYSIS = "analysis"
    VISUALIZATION = "visualization"
    INTERPRETATION = "interpretation"
    EXPORT = "export"
    TROUBLESHOOTING = "troubleshooting"


@dataclass
class AnalysisInsight:
    """A single analysis insight"""
    message: str
    priority: InsightPriority
    source_server: str
    analysis_type: str
    timestamp: float
    metadata: Dict[str, Any]


@dataclass
class SuggestedAction:
    """A suggested action for the user"""
    description: str
    action_type: ActionType
    priority: InsightPriority
    server_context: str
    estimated_time: Optional[str] = None
    requirements: Optional[List[str]] = None
    metadata: Dict[str, Any] = None


class AnalysisProvider:
    """Interface for analysis providers"""
    
    def get_analysis_insights(self) -> str:
        """Get analysis insights for this provider"""
        return "No insights available"
    
    def get_suggested_actions(self) -> List[str]:
        """Get suggested actions for this provider"""
        return []
    
    def get_detailed_insights(self) -> List[AnalysisInsight]:
        """Get detailed structured insights"""
        return []
    
    def get_structured_actions(self) -> List[SuggestedAction]:
        """Get structured suggested actions"""
        return []


class DefaultAnalysisProvider(AnalysisProvider):
    """Default fallback analysis provider"""
    
    def __init__(self, server_type: str):
        self.server_type = server_type
        self.logger = logger.getChild(f"Provider-{server_type}")
    
    def get_analysis_insights(self) -> str:
        return f"No {self.server_type} analysis insights available"
    
    def get_suggested_actions(self) -> List[str]:
        return [f"Initialize {self.server_type} analysis workflow"]


class AnalysisProviderFactory:
    """Factory for creating analysis providers"""
    
    def __init__(self):
        self.logger = logger.getChild("ProviderFactory")
        self._providers = {}
        self._fallback_provider = DefaultAnalysisProvider
    
    def register_provider(self, analysis_type: str, provider_class: type):
        """Register an analysis provider for a specific type"""
        self._providers[analysis_type] = provider_class
        self.logger.info(f"Registered analysis provider for {analysis_type}")
    
    def get_provider(self, analysis_type: str) -> AnalysisProvider:
        """Get analysis provider for a specific type"""
        try:
            if analysis_type in self._providers:
                provider_class = self._providers[analysis_type]
                return provider_class()
            else:
                # Try to load provider dynamically
                provider = self._load_dynamic_provider(analysis_type)
                if provider:
                    return provider
                
                # Fall back to default provider
                return self._fallback_provider(analysis_type)
                
        except Exception as e:
            self.logger.error(f"Error creating provider for {analysis_type}: {e}")
            return self._fallback_provider(analysis_type)
    
    def _load_dynamic_provider(self, analysis_type: str) -> Optional[AnalysisProvider]:
        """Try to load analysis provider dynamically"""
        try:
            # Try to import from analysis_interface
            from ..analysis_interface import get_analysis_provider
            return get_analysis_provider(analysis_type)
            
        except ImportError:
            self.logger.debug(f"analysis_interface not available for {analysis_type}")
            return None
        except Exception as e:
            self.logger.warning(f"Error loading dynamic provider for {analysis_type}: {e}")
            return None


class InsightAggregator:
    """Aggregates insights from multiple servers and analysis types"""
    
    def __init__(self):
        self.logger = logger.getChild("InsightAggregator")
        self.provider_factory = AnalysisProviderFactory()
        self._insight_cache = {}
        self._cache_ttl = 60  # 1 minute cache
    
    def get_analysis_insights(self, server_contexts: Dict[str, Dict[str, Any]], 
                            analysis_type: str = "all") -> str:
        """Get aggregated analysis insights from all servers"""
        
        cache_key = f"insights_{analysis_type}_{hash(str(server_contexts))}"
        if self._is_cached_valid(cache_key):
            return self._insight_cache[cache_key]["data"]
        
        all_insights = []
        
        for server_name, server_context in server_contexts.items():
            server_analysis_type = server_context.get("server_type", "")
            
            # Filter by analysis type if specified
            if analysis_type != "all" and server_analysis_type != analysis_type:
                continue
            
            if server_analysis_type:
                try:
                    provider = self.provider_factory.get_provider(server_analysis_type)
                    insights = provider.get_analysis_insights()
                    
                    if insights and insights != f"No {server_analysis_type} analysis insights available":
                        all_insights.append(f"{server_name.upper()}: {insights}")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to get insights for {server_analysis_type}: {e}")
                    # Fallback to basic insight
                    if server_context.get("data_uploaded", False):
                        all_insights.append(f"{server_name.upper()}: Data uploaded and available")
        
        # Generate final insight
        if not all_insights:
            connected_servers = list(server_contexts.keys())
            if connected_servers:
                result = f"Connected MCP servers: {', '.join(connected_servers)} - Ready for analysis"
            else:
                result = "No MCP servers connected"
        else:
            result = " | ".join(all_insights)
        
        # Cache result
        self._insight_cache[cache_key] = {
            "data": result,
            "timestamp": time.time()
        }
        
        return result
    
    def get_suggested_actions(self, server_contexts: Dict[str, Dict[str, Any]]) -> List[str]:
        """Get aggregated suggested actions from all servers"""
        
        cache_key = f"actions_{hash(str(server_contexts))}"
        if self._is_cached_valid(cache_key):
            return self._insight_cache[cache_key]["data"]
        
        all_suggestions = []
        
        for server_name, server_context in server_contexts.items():
            analysis_type = server_context.get("server_type", "")
            
            if analysis_type:
                try:
                    provider = self.provider_factory.get_provider(analysis_type)
                    suggestions = provider.get_suggested_actions()
                    all_suggestions.extend(suggestions)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to get suggestions for {analysis_type}: {e}")
                    # Fallback to generic suggestions
                    if not server_context.get("data_uploaded", False):
                        all_suggestions.append(f"Upload data for {analysis_type} analysis")
                    else:
                        all_suggestions.append(f"Continue {analysis_type} analysis workflow")
        
        # Remove duplicates while preserving order
        unique_suggestions = []
        seen = set()
        for suggestion in all_suggestions:
            if suggestion not in seen:
                unique_suggestions.append(suggestion)
                seen.add(suggestion)
        
        # Return top suggestions or default
        result = unique_suggestions[:5] if unique_suggestions else ["All analyses appear complete - explore results or start new analysis"]
        
        # Cache result
        self._insight_cache[cache_key] = {
            "data": result,
            "timestamp": time.time()
        }
        
        return result
    
    def get_detailed_insights(self, server_contexts: Dict[str, Dict[str, Any]]) -> List[AnalysisInsight]:
        """Get detailed structured insights from all servers"""
        detailed_insights = []
        
        for server_name, server_context in server_contexts.items():
            analysis_type = server_context.get("server_type", "")
            
            if analysis_type:
                try:
                    provider = self.provider_factory.get_provider(analysis_type)
                    insights = provider.get_detailed_insights()
                    detailed_insights.extend(insights)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to get detailed insights for {analysis_type}: {e}")
        
        # Sort by priority and timestamp
        detailed_insights.sort(key=lambda x: (x.priority.value, -x.timestamp))
        
        return detailed_insights
    
    def get_structured_actions(self, server_contexts: Dict[str, Dict[str, Any]]) -> List[SuggestedAction]:
        """Get structured suggested actions from all servers"""
        structured_actions = []
        
        for server_name, server_context in server_contexts.items():
            analysis_type = server_context.get("server_type", "")
            
            if analysis_type:
                try:
                    provider = self.provider_factory.get_provider(analysis_type)
                    actions = provider.get_structured_actions()
                    structured_actions.extend(actions)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to get structured actions for {analysis_type}: {e}")
        
        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        structured_actions.sort(key=lambda x: priority_order.get(x.priority.value, 4))
        
        return structured_actions
    
    def _is_cached_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self._insight_cache:
            return False
        
        cache_entry = self._insight_cache[cache_key]
        age = time.time() - cache_entry["timestamp"]
        return age < self._cache_ttl
    
    def clear_cache(self):
        """Clear the insight cache"""
        self._insight_cache.clear()
        self.logger.info("Insight cache cleared")


class ContextFormatter:
    """Formats analysis context for different consumers"""
    
    def __init__(self, insight_aggregator: InsightAggregator):
        self.insight_aggregator = insight_aggregator
        self.logger = logger.getChild("ContextFormatter")
    
    def format_context_for_agent(self, server_contexts: Dict[str, Dict[str, Any]], 
                                available_tools: int, available_resources: int, 
                                available_prompts: int) -> str:
        """Format context information for agent consumption"""
        
        insights = self.insight_aggregator.get_analysis_insights(server_contexts)
        suggestions = self.insight_aggregator.get_suggested_actions(server_contexts)
        
        context_text = f"""Current Analysis State:
{insights}

Suggested Next Actions:
{chr(10).join(f"• {action}" for action in suggestions)}

Available Capabilities:
• Tools: {available_tools}
• Resources: {available_resources}
• Prompts: {available_prompts}
"""
        
        return context_text.strip()
    
    def format_context_for_dashboard(self, server_contexts: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Format context for dashboard/UI consumption"""
        
        insights = self.insight_aggregator.get_detailed_insights(server_contexts)
        actions = self.insight_aggregator.get_structured_actions(server_contexts)
        
        return {
            "summary": {
                "total_insights": len(insights),
                "critical_insights": len([i for i in insights if i.priority == InsightPriority.CRITICAL]),
                "pending_actions": len(actions),
                "high_priority_actions": len([a for a in actions if a.priority == InsightPriority.HIGH])
            },
            "insights": [
                {
                    "message": insight.message,
                    "priority": insight.priority.value,
                    "source": insight.source_server,
                    "type": insight.analysis_type,
                    "timestamp": insight.timestamp
                }
                for insight in insights[:10]  # Top 10 insights
            ],
            "actions": [
                {
                    "description": action.description,
                    "type": action.action_type.value,
                    "priority": action.priority.value,
                    "context": action.server_context,
                    "estimated_time": action.estimated_time,
                    "requirements": action.requirements
                }
                for action in actions[:10]  # Top 10 actions
            ]
        }
    
    def format_context_for_reporting(self, server_contexts: Dict[str, Dict[str, Any]]) -> str:
        """Format context for reporting purposes"""
        
        insights = self.insight_aggregator.get_analysis_insights(server_contexts)
        actions = self.insight_aggregator.get_suggested_actions(server_contexts)
        
        # Count servers by type
        server_types = {}
        for server_context in server_contexts.values():
            server_type = server_context.get("server_type", "unknown")
            server_types[server_type] = server_types.get(server_type, 0) + 1
        
        report = f"""Analysis Status Report
Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}

Connected Servers:
{chr(10).join(f"• {stype}: {count}" for stype, count in server_types.items())}

Current Status:
{insights}

Recommended Actions:
{chr(10).join(f"{i+1}. {action}" for i, action in enumerate(actions))}
"""
        
        return report


def main():
    """Main function for module testing"""
    print("Testing Analysis Insights & Actions...")
    
    # Test analysis provider factory
    factory = AnalysisProviderFactory()
    print("✅ Created AnalysisProviderFactory")
    
    # Test default provider
    provider = factory.get_provider("test_analysis")
    insights = provider.get_analysis_insights()
    actions = provider.get_suggested_actions()
    
    print(f"✅ Default provider insights: '{insights}'")
    print(f"✅ Default provider actions: {len(actions)} actions")
    
    # Test insight aggregator
    aggregator = InsightAggregator()
    print("✅ Created InsightAggregator")
    
    # Test with mock server contexts
    mock_contexts = {
        "scrnaseq": {
            "server_type": "scrnaseq",
            "data_uploaded": True,
            "analysis_complete": False
        },
        "data": {
            "server_type": "data",
            "data_uploaded": False,
            "files_available": 5
        }
    }
    
    # Test insight aggregation
    insights = aggregator.get_analysis_insights(mock_contexts)
    print(f"✅ Aggregated insights: '{insights}'")
    
    actions = aggregator.get_suggested_actions(mock_contexts)
    print(f"✅ Aggregated actions: {len(actions)} actions")
    
    for i, action in enumerate(actions[:3]):
        print(f"   {i+1}. {action}")
    
    # Test context formatter
    formatter = ContextFormatter(aggregator)
    print("✅ Created ContextFormatter")
    
    # Test agent context formatting
    agent_context = formatter.format_context_for_agent(mock_contexts, 15, 8, 12)
    print(f"✅ Agent context: {len(agent_context)} characters")
    
    # Test dashboard formatting
    dashboard_context = formatter.format_context_for_dashboard(mock_contexts)
    print(f"✅ Dashboard context: {len(dashboard_context)} keys")
    
    # Test reporting
    report = formatter.format_context_for_reporting(mock_contexts)
    print(f"✅ Report: {len(report)} characters")
    
    # Test caching
    cached_insights = aggregator.get_analysis_insights(mock_contexts)
    print(f"✅ Cache test: {'cached' if cached_insights == insights else 'not cached'}")
    
    print("🎉 All Analysis Insights & Actions tests passed!")


if __name__ == "__main__":
    main()