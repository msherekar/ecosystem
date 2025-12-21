"""
Search and Filtering System for Registry

Provides advanced search and filtering capabilities for domain experts
with caching and performance optimization.
"""

import asyncio
import threading
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta

from .core import DomainExpert, ExpertiseLevel, BiologicalContext
from .registry_core import EnhancedRegistryEntry
from .security import SecurityValidator, SecurityContext
from .events import get_event_emitter, emit_system_event
from .async_support import async_cached

import logging
logger = logging.getLogger(__name__)


class SearchFilter:
    """Search filter configuration"""
    
    def __init__(self):
        self.category: Optional[str] = None
        self.subcategory: Optional[str] = None
        self.expertise_level: Optional[ExpertiseLevel] = None
        self.biological_context: Optional[BiologicalContext] = None
        self.security_level: Optional[str] = None
        self.tags: Set[str] = set()
        self.aliases: Set[str] = set()
        self.include_related: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert filter to dictionary"""
        return {
            "category": self.category,
            "subcategory": self.subcategory,
            "expertise_level": self.expertise_level.value if self.expertise_level else None,
            "biological_context": self.biological_context.value if self.biological_context else None,
            "security_level": self.security_level,
            "tags": list(self.tags),
            "aliases": list(self.aliases),
            "include_related": self.include_related
        }


class RegistrySearch:
    """Advanced search system for domain experts"""
    
    def __init__(self):
        self._search_cache: Dict[str, List[DomainExpert]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=5)
        self._lock = threading.RLock()
        self._events = get_event_emitter()
    
    @async_cached(ttl_minutes=5)
    async def search_techniques_async(self, registry_entries: Dict[str, EnhancedRegistryEntry],
                                    query: str, 
                                    search_filter: Optional[SearchFilter] = None,
                                    security_context: Optional[SecurityContext] = None) -> List[DomainExpert]:
        """
        Enhanced async search with filtering and caching
        
        Args:
            registry_entries: Registry entries to search
            query: Search query string
            search_filter: Additional filters to apply
            security_context: Security context for access control
            
        Returns:
            List of matching domain experts
        """
        # Validate query
        validated_query = SecurityValidator.validate_string(query, 200, "search_query")
        
        matches = []
        search_stats = {
            "total_entries": len(registry_entries),
            "security_filtered": 0,
            "query_matches": 0,
            "filter_matches": 0
        }
        
        with self._lock:
            for entry in registry_entries.values():
                # Security filtering
                if security_context and not SecurityValidator.check_security_level_access(
                    security_context.level, entry.security_level
                ):
                    search_stats["security_filtered"] += 1
                    continue
                
                # Basic query matching
                if entry.metadata and self._matches_query(entry, validated_query):
                    search_stats["query_matches"] += 1
                    
                    # Apply additional filters
                    if self._matches_filter(entry, search_filter):
                        search_stats["filter_matches"] += 1
                        try:
                            expert = entry.get_expert(security_context)
                            matches.append(expert)
                        except PermissionError:
                            continue
        
        # Sort results by relevance
        sorted_matches = self._sort_by_relevance(matches, validated_query)
        
        # Emit search event
        if self._events:
            emit_system_event("experts_searched", {
                "query": validated_query,
                "filter": search_filter.to_dict() if search_filter else None,
                "result_count": len(sorted_matches),
                "search_stats": search_stats
            })
        
        return sorted_matches
    
    def _matches_query(self, entry: EnhancedRegistryEntry, query: str) -> bool:
        """Check if entry matches basic query"""
        if not entry.metadata:
            return False
        
        metadata = entry.metadata
        query_lower = query.lower()
        
        # Search in various fields
        search_fields = [
            metadata.name.lower(),
            metadata.display_name.lower(),
            metadata.description.lower(),
            metadata.category.lower()
        ]
        
        # Add subcategory if present
        if metadata.subcategory:
            search_fields.append(metadata.subcategory.lower())
        
        # Add aliases
        search_fields.extend([alias.lower() for alias in metadata.aliases])
        
        # Add typical applications
        search_fields.extend([app.lower() for app in metadata.typical_applications])
        
        # Check for query match in any field
        return any(query_lower in field for field in search_fields)
    
    def _matches_filter(self, entry: EnhancedRegistryEntry, 
                       search_filter: Optional[SearchFilter]) -> bool:
        """Check if entry matches additional filters"""
        if not search_filter or not entry.metadata:
            return True
        
        metadata = entry.metadata
        
        # Category filter
        if search_filter.category and metadata.category.lower() != search_filter.category.lower():
            return False
        
        # Subcategory filter
        if search_filter.subcategory:
            if not metadata.subcategory or \
               metadata.subcategory.lower() != search_filter.subcategory.lower():
                return False
        
        # Expertise level filter
        if search_filter.expertise_level and metadata.required_expertise != search_filter.expertise_level:
            return False
        
        # Security level filter
        if search_filter.security_level and entry.security_level.value != search_filter.security_level:
            return False
        
        # Tags filter (any tag match)
        if search_filter.tags and not entry.expert_instance:
            # Can't check prompt tags without instantiated expert
            return True
        
        # Aliases filter (any alias match)
        if search_filter.aliases:
            alias_intersection = set(alias.lower() for alias in metadata.aliases) & \
                               set(alias.lower() for alias in search_filter.aliases)
            if not alias_intersection:
                return False
        
        return True
    
    def _sort_by_relevance(self, experts: List[DomainExpert], query: str) -> List[DomainExpert]:
        """Sort experts by relevance to query"""
        query_lower = query.lower()
        
        def relevance_score(expert: DomainExpert) -> float:
            metadata = expert.get_metadata()
            score = 0.0
            
            # Exact name match gets highest score
            if metadata.name.lower() == query_lower:
                score += 100
            elif query_lower in metadata.name.lower():
                score += 50
            
            # Display name match
            if query_lower in metadata.display_name.lower():
                score += 30
            
            # Category match
            if query_lower in metadata.category.lower():
                score += 20
            
            # Description match
            if query_lower in metadata.description.lower():
                score += 10
            
            # Alias match
            for alias in metadata.aliases:
                if query_lower in alias.lower():
                    score += 25
            
            # Application match
            for app in metadata.typical_applications:
                if query_lower in app.lower():
                    score += 15
            
            return score
        
        return sorted(experts, key=relevance_score, reverse=True)
    
    def get_techniques_by_category(self, registry_entries: Dict[str, EnhancedRegistryEntry],
                                 category: str, 
                                 security_context: Optional[SecurityContext] = None) -> List[DomainExpert]:
        """Get all techniques in a specific category"""
        category_lower = category.lower()
        matches = []
        
        with self._lock:
            for entry in registry_entries.values():
                if entry.metadata and entry.metadata.category.lower() == category_lower:
                    # Check security access
                    if security_context and not SecurityValidator.check_security_level_access(
                        security_context.level, entry.security_level
                    ):
                        continue
                    
                    try:
                        expert = entry.get_expert(security_context)
                        matches.append(expert)
                    except PermissionError:
                        continue
        
        # Sort by display name
        return sorted(matches, key=lambda e: e.get_metadata().display_name)
    
    def get_categories_stats(self, registry_entries: Dict[str, EnhancedRegistryEntry]) -> Dict[str, int]:
        """Get statistics about categories"""
        categories = {}
        
        with self._lock:
            for entry in registry_entries.values():
                if entry.metadata:
                    category = entry.metadata.category
                    categories[category] = categories.get(category, 0) + 1
        
        return categories
    
    def clear_search_cache(self):
        """Clear search cache"""
        with self._lock:
            self._search_cache.clear()
            self._cache_timestamps.clear()
            logger.debug("Search cache cleared")


if __name__ == "__main__":
    # Test search system
    async def test_search():
        print("Testing Registry Search System")
        
        search = RegistrySearch()
        
        # Test search filter
        search_filter = SearchFilter()
        search_filter.category = "Transcriptomics"
        search_filter.expertise_level = ExpertiseLevel.INTERMEDIATE
        print(f"✓ Created search filter: {search_filter.to_dict()}")
        
        # Test empty registry search
        empty_results = await search.search_techniques_async({}, "test_query", search_filter)
        print(f"✓ Empty registry search: {len(empty_results)} results")
        
        # Test category stats
        stats = search.get_categories_stats({})
        print(f"✓ Category stats: {len(stats)} categories")
        
        # Clear cache
        search.clear_search_cache()
        print("✓ Search cache cleared")
        
        print("\n✅ Search system test completed!")
    
    # Run test
    try:
        asyncio.run(test_search())
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 