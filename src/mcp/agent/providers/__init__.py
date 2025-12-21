"""
Enhanced LLM Providers Package
Modular LLM provider implementations with scalability, security, and Electron integration.

This package provides a comprehensive set of LLM providers with:
- Base provider interface with health monitoring
- External LLM provider with connection pooling and resilience patterns  
- Local LLM provider with resource monitoring and security
- Configuration management with Pydantic validation
- Electron UI/UX integration capabilities
"""

from .base_provider import (
    BaseLLMProvider, 
    ProviderType, 
    ProviderStatus, 
    ProviderConfig
)
from .external_provider import (
    ExternalLLMProvider, 
    ExternalProviderConfig,
    RateLimiter,
    CircuitBreaker
)
from .local_provider import (
    LocalLLMProvider, 
    LocalProviderConfig,
    ResourceMonitor
)

# Version information
__version__ = "2.0.0"
__author__ = "Gliaent Team"

# Public API
__all__ = [
    # Base classes
    'BaseLLMProvider',
    'ProviderType', 
    'ProviderStatus',
    
    # Configuration classes
    'ProviderConfig',
    'ExternalProviderConfig',
    'LocalProviderConfig',
    
    # Provider implementations
    'ExternalLLMProvider',
    'LocalLLMProvider',
    
    # Utility classes
    'RateLimiter',
    'CircuitBreaker', 
    'ResourceMonitor',
    
    # Package metadata
    '__version__'
]

# Convenience functions for provider creation
def create_external_provider(api_key: str = None, **config) -> ExternalLLMProvider:
    """
    Create and initialize an external LLM provider.
    
    Args:
        api_key: API key for external LLM service
        **config: Additional configuration parameters
        
    Returns:
        ExternalLLMProvider: Configured external provider
    """
    if api_key:
        config['api_key'] = api_key
    return ExternalLLMProvider(config)


def create_local_provider(**config) -> LocalLLMProvider:
    """
    Create and initialize a local LLM provider.
    
    Args:
        **config: Configuration parameters
        
    Returns:
        LocalLLMProvider: Configured local provider
    """
    return LocalLLMProvider(config)


async def initialize_providers(*providers: BaseLLMProvider) -> list[bool]:
    """
    Initialize multiple providers concurrently.
    
    Args:
        *providers: Provider instances to initialize
        
    Returns:
        list[bool]: Initialization results for each provider
    """
    import asyncio
    
    tasks = [provider.initialize() for provider in providers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return [
        result if isinstance(result, bool) else False 
        for result in results
    ]


def get_provider_summary(*providers: BaseLLMProvider) -> dict:
    """
    Get a summary of provider capabilities and status.
    
    Args:
        *providers: Provider instances to summarize
        
    Returns:
        dict: Summary of all providers
    """
    summary = {
        'total_providers': len(providers),
        'available_providers': 0,
        'providers': []
    }
    
    for provider in providers:
        provider_info = {
            'type': provider.provider_type.value,
            'status': provider.status.value,
            'available': provider.is_available(),
            'capabilities': provider.get_capabilities()
        }
        
        if provider.is_available():
            summary['available_providers'] += 1
            
        summary['providers'].append(provider_info)
    
    return summary 