"""
Modular Handler Components

This package contains modular handler components that can be mixed and matched
to create technique-specific handlers with minimal code duplication.

Components:
- BaseHandler: Common functionality for all handlers
- AnalysisHandlerMixin: Analysis-related tools (QC, clustering, etc.)
- DataHandlerMixin: Data validation, summary, and filtering tools
- VisualizationHandlerMixin: Visualization tools (UMAP, violin plots, etc.)
"""

from .base_handler import BaseHandler
from .analysis_handlers import AnalysisHandlerMixin
from .data_handlers import DataHandlerMixin
from .visualization_handlers import VisualizationHandlerMixin

__all__ = [
    "BaseHandler",
    "AnalysisHandlerMixin", 
    "DataHandlerMixin",
    "VisualizationHandlerMixin"
] 