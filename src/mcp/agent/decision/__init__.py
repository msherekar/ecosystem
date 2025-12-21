"""
Decision Engine Package
Intelligent decision making components for LLM provider selection.
"""

from .provider_selector import (
    ScalableProviderSelector, 
    SelectionStrategy, 
    SelectionContext, 
    SelectionCriteria
)

# Keep backward compatibility
ProviderSelector = ScalableProviderSelector

__all__ = [
    'ScalableProviderSelector',
    'ProviderSelector',  # Backward compatibility
    'SelectionStrategy',
    'SelectionContext',
    'SelectionCriteria'
] 