"""
Gliaent MCP Agent Package
===========================

A comprehensive bioinformatics agent system with intelligent routing, coordination,
decision-making, and provider management capabilities.

Key Components:
- Agent: Core conversational AI agent for bioinformatics
- IntelligentToolRouter: Context-aware tool selection and routing
- Coordination: Hybrid coordination and load balancing
- Decision: Intelligent provider selection and strategy management
- Providers: LLM provider management (local and external)
- Routing: Biological context analysis and workflow prediction

Usage:
    from src.mcp.agent import Agent, get_agent, IntelligentToolRouter
    
    # Get the main agent instance
    agent = get_agent()
    
    # Process a bioinformatics query
    result = agent.process_command("Analyze my scRNA-seq data")
"""

# Core agent components
from .core import Agent
from .brain import (
    get_agent,
    ask_agent,
    enhanced_ask_agent,
    get_available_tools,
    execute_tool,
    execute_tool_with_learning
)
from .intelligent_router import (
    IntelligentToolRouter,
    ContextualToolSet,
    enhanced_tool_execution
)

# Coordination components
from .coordination import (
    HybridCoordinator,
    get_hybrid_coordinator,
    ScalableHybridCoordinator,
    CoordinatorConfig,
    ProviderRegistry,
    ProviderConfig,
    AdvancedLoadBalancer,
    LoadBalancerConfig,
    CircuitBreaker,
    IntelligentCache,
    CacheConfig
)

# Decision components
from .decision import (
    ScalableProviderSelector,
    ProviderSelector,
    SelectionStrategy,
    SelectionContext,
    SelectionCriteria
)

# Provider components
from .providers import (
    BaseLLMProvider,
    ProviderType,
    ProviderStatus,
    ProviderConfig,
    ExternalLLMProvider,
    ExternalProviderConfig,
    LocalLLMProvider,
    LocalProviderConfig,
    RateLimiter,
    ResourceMonitor,
    create_external_provider,
    create_local_provider,
    initialize_providers,
    get_provider_summary
)

# Routing components
from .routing import (
    BiologicalContext,
    BiologicalOntologyGraph,
    EnhancedBiologicalContextAnalyzer,
    WorkflowPredictionEngine,
    ContinuousLearningEngine,
    MultiModalContextIntegrator,
    DataFileAnalyzer,
    TemporalPatternAnalyzer,
    ElectronRoutingBridge
)

# Package information
__version__ = "1.0.0"
__author__ = "Gliaent Team"
__description__ = "Intelligent Bioinformatics Agent with MCP Integration"

# Main public API
__all__ = [
    # Core agent functionality
    'Agent',
    'get_agent',
    'ask_agent',
    'enhanced_ask_agent',
    'get_available_tools',
    'execute_tool',
    'execute_tool_with_learning',
    
    # Intelligent routing
    'IntelligentToolRouter',
    'ContextualToolSet',
    'enhanced_tool_execution',
    
    # Coordination system
    'HybridCoordinator',
    'get_hybrid_coordinator',
    'ScalableHybridCoordinator',
    'CoordinatorConfig',
    'ProviderRegistry',
    'ProviderConfig',
    'AdvancedLoadBalancer',
    'LoadBalancerConfig',
    'CircuitBreaker',
    'IntelligentCache',
    'CacheConfig',
    
    # Decision engine
    'ScalableProviderSelector',
    'ProviderSelector',
    'SelectionStrategy',
    'SelectionContext',
    'SelectionCriteria',
    
    # LLM providers
    'BaseLLMProvider',
    'ProviderType',
    'ProviderStatus',
    'ProviderConfig',
    'ExternalLLMProvider',
    'ExternalProviderConfig',
    'LocalLLMProvider',
    'LocalProviderConfig',
    'RateLimiter',
    'ResourceMonitor',
    'create_external_provider',
    'create_local_provider',
    'initialize_providers',
    'get_provider_summary',
    
    # Biological routing
    'BiologicalContext',
    'BiologicalOntologyGraph',
    'EnhancedBiologicalContextAnalyzer',
    'WorkflowPredictionEngine',
    'ContinuousLearningEngine',
    'MultiModalContextIntegrator',
    'DataFileAnalyzer',
    'TemporalPatternAnalyzer',
    'ElectronRoutingBridge',
    
    # Package metadata
    '__version__',
    '__author__',
    '__description__'
]

# Convenience factory functions
async def create_complete_agent(api_key: str = None, config: dict = None) -> Agent:
    """
    Create a fully configured agent with all components initialized.
    
    Args:
        api_key: OpenRouter/OpenAI API key
        config: Configuration dictionary for various components
        
    Returns:
        Agent: Fully initialized agent instance
    """
    import os
    
    # Get API key from environment if not provided
    if not api_key:
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError("API key required. Set OPENROUTER_API_KEY or OPENAI_API_KEY environment variable.")
    
    # Create core agent
    agent = Agent(api_key=api_key)
    
    # Initialize intelligent router
    router = IntelligentToolRouter()
    
    # Set up coordination if config provided
    if config and config.get('coordination'):
        coordinator = await get_hybrid_coordinator()
    
    return agent


def get_agent_status() -> dict:
    """
    Get comprehensive status of the agent system.
    
    Returns:
        dict: Status information for all components
    """
    try:
        agent = get_agent()
        return {
            'agent_initialized': True,
            'memory_size': len(agent.memory),
            'available_tools_count': len(agent.available_tools),
            'status': 'healthy'
        }
    except Exception as e:
        return {
            'agent_initialized': False,
            'error': str(e),
            'status': 'error'
        }


# Quick start function for common use cases
async def quick_start_bioinformatics_agent():
    """
    Quick start function for bioinformatics workflows.
    Sets up agent with recommended configuration for biological data analysis.
    
    Returns:
        Agent: Configured agent ready for bioinformatics tasks
    """
    config = {
        'coordination': {
            'enable_load_balancing': True,
            'enable_caching': True,
            'cache_size': 1000
        },
        'routing': {
            'enable_biological_context': True,
            'enable_workflow_prediction': True,
            'enable_learning': True
        }
    }
    
    return await create_complete_agent(config=config) 