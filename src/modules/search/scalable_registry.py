"""
Scalable Search Registry - Enterprise-Grade Architecture

Designed to handle 100+ databases efficiently with:
- Lazy loading
- Pattern indexing  
- Caching
- Plugin discovery
- Configuration-based registration
"""

import logging
import json
import importlib
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from pathlib import Path
import streamlit as st
from functools import lru_cache
import re
from collections import defaultdict


@dataclass
class DatabaseConfig:
    """Configuration for a database provider"""
    name: str
    display_name: str
    description: str
    module_path: str  # e.g., "src.modules.search.geo"
    search_function: str = "search"  # Function name in module
    display_function: str = "display"  # Function name in module
    patterns: List[str] = field(default_factory=list)
    category: str = "general"  # genomics, proteomics, literature, etc.
    priority: int = 1  # Higher = higher priority for pattern matching
    enabled: bool = True
    lazy_load: bool = True


class PatternIndex:
    """Efficient pattern matching using categorized indexing"""
    
    def __init__(self):
        self.keyword_index: Dict[str, List[DatabaseConfig]] = defaultdict(list)
        self.category_index: Dict[str, List[DatabaseConfig]] = defaultdict(list)
        self.compiled_patterns: Dict[str, re.Pattern] = {}
        
    def add_database(self, config: DatabaseConfig):
        """Add database to indices"""
        # Index by keywords in patterns
        for pattern in config.patterns:
            keywords = self._extract_keywords(pattern)
            for keyword in keywords:
                self.keyword_index[keyword].append(config)
                
        # Index by category
        self.category_index[config.category].append(config)
        
        # Pre-compile patterns for performance
        for pattern in config.patterns:
            if pattern not in self.compiled_patterns:
                try:
                    self.compiled_patterns[pattern] = re.compile(pattern, re.IGNORECASE)
                except re.error:
                    logging.warning(f"Invalid regex pattern: {pattern}")
    
    def _extract_keywords(self, pattern: str) -> Set[str]:
        """Extract searchable keywords from regex patterns"""
        # Simple keyword extraction - could be more sophisticated
        keywords = set()
        # Remove regex syntax and extract words
        cleaned = re.sub(r'[()\\?\*\+\[\]{}|^$]', ' ', pattern)
        words = cleaned.lower().split()
        for word in words:
            if len(word) > 2 and word not in ['for', 'the', 'and', 'search', 'find']:
                keywords.add(word)
        return keywords
    
    def find_matching_databases(self, query: str) -> List[DatabaseConfig]:
        """Find databases that might match the query using efficient indexing"""
        query_lower = query.lower()
        candidates = set()
        
        # Fast keyword-based pre-filtering
        words = query_lower.split()
        for word in words:
            if word in self.keyword_index:
                candidates.update(self.keyword_index[word])
        
        # If no keyword matches, check all databases (fallback)
        if not candidates:
            for configs in self.category_index.values():
                candidates.update(configs)
        
        # Sort by priority
        return sorted(candidates, key=lambda x: x.priority, reverse=True)
    
    def match_patterns(self, query: str, candidates: List[DatabaseConfig]) -> Optional[DatabaseConfig]:
        """Match actual regex patterns against query"""
        for config in candidates:
            if not config.enabled:
                continue
                
            for pattern in config.patterns:
                compiled_pattern = self.compiled_patterns.get(pattern)
                if compiled_pattern and compiled_pattern.search(query):
                    return config
        return None


class ScalableSearchRegistry:
    """
    Enterprise-grade search registry for 100+ databases
    
    Features:
    - Lazy loading of search modules
    - Efficient pattern matching with indexing
    - Configuration-based database registration
    - Caching for performance
    - Plugin discovery
    - Category-based organization
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger("scalable_search_registry")
        self.config_path = config_path or "config/databases.json"
        
        # Core components
        self.pattern_index = PatternIndex()
        self.database_configs: Dict[str, DatabaseConfig] = {}
        self.loaded_modules: Dict[str, Any] = {}  # Lazy-loaded modules
        
        # Performance caching
        self._search_cache: Dict[str, Any] = {}
        self._module_cache: Dict[str, Any] = {}
        
        self._initialized = False
    
    def initialize(self):
        """Initialize registry with database configurations"""
        if self._initialized:
            return
            
        self._load_database_configs()
        self._build_indices()
        self._initialized = True
        
        self.logger.info(f"Initialized scalable registry with {len(self.database_configs)} databases")
    
    def _load_database_configs(self):
        """Load database configurations from file and auto-discovery"""
        # Load from configuration file
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                    for db_config in config_data.get("databases", []):
                        config = DatabaseConfig(**db_config)
                        self.database_configs[config.name] = config
        except Exception as e:
            self.logger.warning(f"Failed to load config file {self.config_path}: {e}")
        
        # Auto-discovery fallback (current databases)
        self._auto_discover_databases()
    
    def _auto_discover_databases(self):
        """Auto-discover existing database modules"""
        known_databases = [
            {
                "name": "geo",
                "display_name": "NCBI GEO",
                "description": "Search NCBI Gene Expression Omnibus",
                "module_path": "src.modules.search.geo",
                "patterns": [
                    r"search\s+(?:for\s+)?(.+?)\s+(?:in\s+)?geo(?:\s+database)?",
                    r"find\s+(.+?)\s+(?:in\s+)?(?:ncbi\s+)?geo",
                    r"geo\s+search\s+(?:for\s+)?(.+)"
                ],
                "category": "genomics",
                "priority": 2
            },
            {
                "name": "tcga",
                "display_name": "TCGA",
                "description": "Search The Cancer Genome Atlas",
                "module_path": "src.modules.search.tcga",
                "patterns": [
                    r"search\s+(?:for\s+)?(.+?)\s+(?:in\s+)?tcga",
                    r"find\s+(.+?)\s+(?:in\s+)?(?:cancer\s+)?genome\s+atlas"
                ],
                "category": "genomics",
                "priority": 2
            },
            {
                "name": "uniprot",
                "display_name": "UniProt",
                "description": "Search UniProt protein database",
                "module_path": "src.modules.search.uniprot",
                "patterns": [
                    r"search\s+(?:for\s+)?(.+?)\s+(?:in\s+)?uniprot",
                    r"protein\s+search\s+(?:for\s+)?(.+)"
                ],
                "category": "proteomics",
                "priority": 2
            }
        ]
        
        for db_data in known_databases:
            if db_data["name"] not in self.database_configs:
                config = DatabaseConfig(**db_data)
                self.database_configs[config.name] = config
    
    def _build_indices(self):
        """Build efficient search indices"""
        for config in self.database_configs.values():
            self.pattern_index.add_database(config)
    
    @lru_cache(maxsize=128)
    def _get_module(self, module_path: str) -> Optional[Any]:
        """Lazy load search module with caching"""
        if module_path in self.loaded_modules:
            return self.loaded_modules[module_path]
        
        try:
            module = importlib.import_module(module_path)
            self.loaded_modules[module_path] = module
            return module
        except ImportError as e:
            self.logger.warning(f"Failed to import module {module_path}: {e}")
            return None
    
    def find_database_for_query(self, query: str) -> Optional[DatabaseConfig]:
        """Efficiently find the best database for a query"""
        # Use indexed search for performance
        candidates = self.pattern_index.find_matching_databases(query)
        return self.pattern_index.match_patterns(query, candidates)
    
    def search(self, query: str, database_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Execute search with lazy loading and caching"""
        # Check cache first
        cache_key = f"{database_name or 'auto'}:{query}:{str(sorted(kwargs.items()))}"
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]
        
        try:
            # Find database
            if database_name:
                config = self.database_configs.get(database_name)
                if not config:
                    raise ValueError(f"Database {database_name} not found")
            else:
                config = self.find_database_for_query(query)
                if not config:
                    raise ValueError(f"No database found for query: {query}")
            
            # Lazy load module
            module = self._get_module(config.module_path)
            if not module:
                raise ValueError(f"Failed to load module: {config.module_path}")
            
            # Get search function
            search_func = getattr(module, f"{config.name}_search", None)
            if not search_func:
                search_func = getattr(module, config.search_function, None)
            if not search_func:
                raise ValueError(f"Search function not found in {config.module_path}")
            
            # Execute search
            results = search_func(query, **kwargs)
            
            # Add metadata
            results["provider"] = config.name
            results["provider_display_name"] = config.display_name
            results["category"] = config.category
            results["query"] = query
            
            # Cache results
            self._search_cache[cache_key] = results
            
            return results
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return {
                "error": str(e),
                "query": query,
                "provider": database_name if database_name else "auto-detect"
            }
    
    def display_results(self, results: Dict[str, Any]) -> None:
        """Display results with lazy-loaded display function"""
        try:
            provider_name = results.get("provider")
            if not provider_name:
                st.error("No provider information in results")
                return
            
            config = self.database_configs.get(provider_name)
            if not config:
                st.error(f"Database config for {provider_name} not found")
                return
            
            # Lazy load module
            module = self._get_module(config.module_path)
            if not module:
                st.error(f"Failed to load display module: {config.module_path}")
                return
            
            # Get display function
            display_func = getattr(module, f"{config.name}_display", None)
            if not display_func:
                display_func = getattr(module, config.display_function, None)
            if not display_func:
                st.error(f"Display function not found in {config.module_path}")
                return
            
            # Display results
            display_func(results)
            
        except Exception as e:
            self.logger.error(f"Display failed: {e}")
            st.error(f"Error displaying results: {e}")
    
    def register_database(self, config: DatabaseConfig):
        """Dynamically register a new database"""
        self.database_configs[config.name] = config
        self.pattern_index.add_database(config)
        self.logger.info(f"Registered database: {config.name}")
    
    def get_database_categories(self) -> Dict[str, List[str]]:
        """Get databases organized by category"""
        categories = defaultdict(list)
        for config in self.database_configs.values():
            if config.enabled:
                categories[config.category].append(config.display_name)
        return dict(categories)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            "total_databases": len(self.database_configs),
            "loaded_modules": len(self.loaded_modules),
            "cache_size": len(self._search_cache),
            "enabled_databases": sum(1 for c in self.database_configs.values() if c.enabled),
            "categories": len(set(c.category for c in self.database_configs.values()))
        }


# Global scalable registry instance
scalable_search_registry = ScalableSearchRegistry()


def get_scalable_search_registry() -> ScalableSearchRegistry:
    """Get the global scalable search registry"""
    if not scalable_search_registry._initialized:
        scalable_search_registry.initialize()
    return scalable_search_registry 