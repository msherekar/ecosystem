"""
Search Registry - Scalable Database Search Architecture

Provides a unified, extensible system for searching multiple biological databases.
Follows the registry pattern established in the codebase.
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod
import streamlit as st


@dataclass
class SearchProvider:
    """Configuration for a search provider"""
    name: str
    display_name: str
    description: str
    search_function: Callable
    display_function: Callable
    patterns: List[str]  # Regex patterns that trigger this search
    enabled: bool = True
    
    
class BaseSearchInterface(ABC):
    """Abstract base class for search interfaces"""
    
    @abstractmethod
    def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute search with given query"""
        pass
    
    @abstractmethod
    def display_results(self, results: Dict[str, Any]) -> None:
        """Display search results in Streamlit"""
        pass
    
    @abstractmethod
    def get_patterns(self) -> List[str]:
        """Get regex patterns that trigger this search"""
        pass


class SearchRegistry:
    """
    Registry for managing multiple database search providers.
    
    Enables easy addition of new databases without code changes.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("search_registry")
        self.providers: Dict[str, SearchProvider] = {}
        self._initialized = False
        
    def register_provider(self, provider: SearchProvider):
        """Register a new search provider"""
        self.providers[provider.name] = provider
        self.logger.info(f"Registered search provider: {provider.name}")
    
    def get_provider(self, name: str) -> Optional[SearchProvider]:
        """Get a specific search provider"""
        return self.providers.get(name)
    
    def get_all_providers(self) -> Dict[str, SearchProvider]:
        """Get all registered providers"""
        return {k: v for k, v in self.providers.items() if v.enabled}
    
    def find_provider_by_pattern(self, query: str) -> Optional[SearchProvider]:
        """Find appropriate provider based on query patterns"""
        import re
        
        query_lower = query.lower()
        
        # Check each provider's patterns
        for provider in self.providers.values():
            if not provider.enabled:
                continue
                
            for pattern in provider.patterns:
                if re.search(pattern, query_lower):
                    return provider
        
        return None
    
    def search(self, query: str, provider_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Execute search using specified provider or auto-detect
        
        Args:
            query: Search query
            provider_name: Specific provider to use (optional)
            **kwargs: Additional parameters for search
            
        Returns:
            Search results dictionary
        """
        try:
            # Use specified provider or auto-detect
            if provider_name:
                provider = self.get_provider(provider_name)
                if not provider:
                    raise ValueError(f"Provider {provider_name} not found")
            else:
                provider = self.find_provider_by_pattern(query)
                if not provider:
                    raise ValueError(f"No provider found for query: {query}")
            
            self.logger.info(f"Using {provider.name} for search: {query}")
            
            # Execute search
            results = provider.search_function(query, **kwargs)
            
            # Add metadata
            results["provider"] = provider.name
            results["provider_display_name"] = provider.display_name
            results["query"] = query
            
            return results
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return {
                "error": str(e),
                "query": query,
                "provider": provider_name if provider_name else "auto-detect"
            }
    
    def display_results(self, results: Dict[str, Any]) -> None:
        """Display search results using appropriate provider"""
        try:
            provider_name = results.get("provider")
            if not provider_name:
                st.error("No provider information in results")
                return
            
            provider = self.get_provider(provider_name)
            if not provider:
                st.error(f"Provider {provider_name} not found")
                return
            
            # Use provider's display function
            provider.display_function(results)
            
        except Exception as e:
            self.logger.error(f"Display failed: {e}")
            st.error(f"Error displaying results: {e}")
    
    def get_search_suggestions(self) -> List[str]:
        """Get search suggestions for all enabled providers"""
        suggestions = []
        for provider in self.providers.values():
            if provider.enabled:
                suggestions.append(f"Search {provider.display_name}")
        return suggestions


# Global registry instance
search_registry = SearchRegistry()


def initialize_search_registry():
    """Initialize the search registry with default providers"""
    if search_registry._initialized:
        return
    
    # Import search functions
    try:
        from .geo import geo_search, geo_display
        
        # Register GEO provider
        search_registry.register_provider(SearchProvider(
            name="geo",
            display_name="NCBI GEO",
            description="Search NCBI Gene Expression Omnibus",
            search_function=geo_search,
            display_function=geo_display,
            patterns=[
                r"search\s+(?:for\s+)?(.+?)\s+(?:in\s+)?geo(?:\s+database)?",
                r"find\s+(.+?)\s+(?:in\s+)?(?:ncbi\s+)?geo",
                r"geo\s+search\s+(?:for\s+)?(.+)",
                r"look\s+(?:up|for)\s+(.+?)\s+(?:in\s+)?geo"
            ]
        ))
        
    except ImportError as e:
        logging.warning(f"Failed to import GEO search: {e}")
    
    # Register additional providers as modules become available
    try:
        from .tcga import tcga_search, tcga_display
        
        search_registry.register_provider(SearchProvider(
            name="tcga",
            display_name="TCGA",
            description="Search The Cancer Genome Atlas",
            search_function=tcga_search,
            display_function=tcga_display,
            patterns=[
                r"search\s+(?:for\s+)?(.+?)\s+(?:in\s+)?tcga",
                r"find\s+(.+?)\s+(?:in\s+)?tcga(?:\s+database)?",
                r"tcga\s+search\s+(?:for\s+)?(.+)",
                r"find\s+(.+?)\s+(?:in\s+)?(?:cancer\s+)?genome\s+atlas",
                r"lookup\s+(.+?)\s+(?:in\s+)?tcga"
            ]
        ))
        
    except ImportError:
        pass  # TCGA module not available yet
    
    try:
        from .uniprot import uniprot_search, uniprot_display
        
        search_registry.register_provider(SearchProvider(
            name="uniprot",
            display_name="UniProt",
            description="Search UniProt protein database",
            search_function=uniprot_search,
            display_function=uniprot_display,
            patterns=[
                r"search\s+(?:for\s+)?(.+?)\s+(?:in\s+)?uniprot",
                r"find\s+(?:protein\s+)?(.+?)\s+(?:in\s+)?uniprot",
                r"uniprot\s+search\s+(?:for\s+)?(.+)",
                r"protein\s+search\s+(?:for\s+)?(.+)"
            ]
        ))
        
    except ImportError:
        pass  # UniProt module not available yet
    
    try:
        from .pubmed import pubmed_search, pubmed_display
        
        search_registry.register_provider(SearchProvider(
            name="pubmed",
            display_name="PubMed",
            description="Search PubMed database",
            search_function=pubmed_search,
            display_function=pubmed_display,
            patterns=[
                r"search\s+(?:for\s+)?(.+?)\s+(?:in\s+)?pubmed",
                r"find\s+(.+?)\s+(?:in\s+)?pubmed(?:\s+database)?",
                r"pubmed\s+search\s+(?:for\s+)?(.+)",
                r"lookup\s+(.+?)\s+(?:in\s+)?pubmed",
                r"search\s+pubmed\s+(?:for\s+)?(.+)"  # Handle "search pubmed for X"
            ]
        ))
    except ImportError:
        pass  # PubMed module not available yet
        
    search_registry._initialized = True
    logging.info(f"Search registry initialized with {len(search_registry.providers)} providers")


# Initialize on import
initialize_search_registry() 