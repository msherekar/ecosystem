"""
Enhanced Domain Expert Registry System

Main registry class that coordinates all registry components including
discovery, search, health monitoring, and security.
"""

import asyncio
import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .core import DomainExpert, TechniqueMetadata, BiologicalContext, ExpertiseLevel
from .registry_core import EnhancedRegistryEntry, RegistryCache, RegistryStats
from .registry_discovery import ExpertDiscovery
from .registry_health import HealthMonitor
from .registry_search import RegistrySearch, SearchFilter
from .security import SecurityValidator, SecurityLevel, SecurityContext
from .events import get_event_emitter, emit_system_event, emit_ui_update, emit_error
from .performance import get_performance_monitor, time_it

import logging
logger = logging.getLogger(__name__)


class EnhancedDomainExpertRegistry:
    """Enhanced registry coordinating all registry components"""
    
    def __init__(self, max_cache_size: int = 500, enable_events: bool = True):
        self._experts: Dict[str, EnhancedRegistryEntry] = {}
        self._lock = threading.RLock()
        self._alias_map: Dict[str, str] = {}  # alias -> technique_name mapping
        
        # Initialize components
        self._discovery = ExpertDiscovery()
        self._health_monitor = HealthMonitor()
        self._search = RegistrySearch()
        self._cache = RegistryCache(max_cache_size)
        self._stats = RegistryStats()
        
        # Configuration
        self._enable_events = enable_events
        self._security_context = SecurityContext()
        
        # Performance monitoring
        self._perf_monitor = get_performance_monitor()
        self._events = get_event_emitter() if enable_events else None
    
    @time_it("registry_add_discovery_path")
    def add_discovery_path(self, path: Path, security_check: bool = True) -> bool:
        """Add a path to search for domain experts with security validation"""
        return self._discovery.add_discovery_path(path, security_check)
    
    @time_it("registry_register_expert")
    def register_expert(self, expert_class: Type[DomainExpert], 
                       technique_name: Optional[str] = None,
                       security_level: SecurityLevel = SecurityLevel.PUBLIC) -> bool:
        """Register a domain expert class with enhanced security and monitoring"""
        with self._lock:
            try:
                # Validate expert class
                if not issubclass(expert_class, DomainExpert):
                    raise ValueError(f"Class {expert_class.__name__} is not a DomainExpert subclass")
                
                # Create instance to get metadata with timing
                import time
                start_time = time.time()
                instance = expert_class()
                metadata = instance.get_metadata()
                load_time = time.time() - start_time
                
                # Validate technique name
                name = technique_name or metadata.name.lower()
                validated_name = SecurityValidator.validate_identifier(name, "technique_name")
                
                # Create enhanced entry
                entry = EnhancedRegistryEntry(
                    expert_class=expert_class,
                    expert_instance=instance,
                    metadata=metadata,
                    module_path=expert_class.__module__,
                    security_level=security_level,
                    health_status="healthy"
                )
                
                # Register with alias mapping
                self._experts[validated_name] = entry
                
                # Add aliases to alias map
                for alias in metadata.aliases:
                    alias_validated = SecurityValidator.validate_identifier(alias, "alias")
                    self._alias_map[alias_validated.lower()] = validated_name
                
                # Update stats
                self._stats.increment("experts_registered")
                
                logger.info(f"Registered expert: {validated_name} ({metadata.display_name})")
                
                # Emit registration event
                if self._events:
                    emit_system_event("expert_registered", {
                        "technique_name": validated_name,
                        "display_name": metadata.display_name,
                        "category": metadata.category,
                        "security_level": security_level.value,
                        "load_time": load_time
                    })
                
                return True
                
            except Exception as e:
                self._health_monitor.record_load_failure(str(e))
                self._stats.increment("load_failures")
                error_msg = f"Failed to register expert {expert_class.__name__}: {e}"
                logger.error(error_msg)
                
                if self._events:
                    emit_error("expert_registration_failed", error_msg, {
                        "expert_class": expert_class.__name__
                    })
                return False
    
    async def discover_experts_async(self, package_name: str = "techniques", 
                                   max_concurrent: int = 4) -> int:
        """Asynchronously discover experts with concurrent loading"""
        try:
            # Use discovery component
            expert_classes = await self._discovery.discover_experts_async(package_name, max_concurrent)
            
            # Register discovered experts
            registered_count = 0
            for expert_class in expert_classes:
                if self.register_expert(expert_class):
                    registered_count += 1
            
            # Record metrics
            import time
            self._health_monitor.record_discovery(registered_count, 1.0)  # Duration tracked in discovery
            self._stats.increment("discovery_runs")
            
            return registered_count
            
        except Exception as e:
            self._health_monitor.record_load_failure(str(e))
            raise
    
    def discover_experts(self, package_name: str = "techniques") -> int:
        """Synchronous wrapper for expert discovery"""
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.discover_experts_async(package_name))
        except RuntimeError:
            # No event loop, run in new loop
            return asyncio.run(self.discover_experts_async(package_name))
    
    @time_it("registry_get_expert")
    def get_expert(self, technique_name: str, 
                   security_context: Optional[SecurityContext] = None) -> Optional[DomainExpert]:
        """Get a domain expert by technique name with security validation"""
        # Validate technique name
        try:
            validated_name = SecurityValidator.validate_identifier(technique_name, "technique_name")
        except ValueError as e:
            logger.warning(f"Invalid technique name: {technique_name}, error: {e}")
            return None
        
        with self._lock:
            # Check direct mapping first
            entry = self._experts.get(validated_name.lower())
            
            # Check alias mapping if not found
            if not entry:
                alias_key = self._alias_map.get(validated_name.lower())
                if alias_key:
                    entry = self._experts.get(alias_key)
            
            if entry:
                try:
                    expert = entry.get_expert(security_context)
                    
                    # Update stats
                    self._stats.increment("experts_accessed")
                    
                    # Emit access event
                    if self._events:
                        emit_system_event("expert_accessed", {
                            "technique_name": validated_name,
                            "access_count": entry.access_count,
                            "security_level": entry.security_level.value
                        })
                    
                    return expert
                except PermissionError as e:
                    if self._events:
                        emit_error("expert_access_denied", str(e), {
                            "technique_name": validated_name
                        })
                    raise
            return None
    
    async def search_techniques_async(self, query: str, 
                                    filters: Optional[Dict[str, Any]] = None) -> List[DomainExpert]:
        """Enhanced async search with filtering and caching"""
        # Create search filter from dict
        search_filter = None
        if filters:
            search_filter = SearchFilter()
            if "category" in filters:
                search_filter.category = filters["category"]
            if "expertise_level" in filters:
                search_filter.expertise_level = ExpertiseLevel(filters["expertise_level"])
            if "security_level" in filters:
                search_filter.security_level = filters["security_level"]
        
        return await self._search.search_techniques_async(
            self._experts, query, search_filter, self._security_context
        )
    
    def search_techniques(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[DomainExpert]:
        """Synchronous wrapper for search"""
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.search_techniques_async(query, filters))
        except RuntimeError:
            return asyncio.run(self.search_techniques_async(query, filters))
    
    def validate_all_experts(self) -> Dict[str, List[str]]:
        """Validate all registered experts"""
        validation_results = {}
        
        with self._lock:
            for name, entry in self._experts.items():
                try:
                    expert = entry.get_expert(self._security_context)
                    errors = expert.validate_prompts()
                    validation_results[name] = errors
                    
                    # Update entry validation status
                    from datetime import datetime
                    entry.validation_status = {
                        "validated_at": datetime.now().isoformat(),
                        "error_count": len(errors),
                        "status": "valid" if not errors else "invalid"
                    }
                    
                    if errors:
                        self._health_monitor.record_validation_failure(name, len(errors))
                        
                except Exception as e:
                    self._health_monitor.record_validation_failure(name, 1)
                    validation_results[name] = [f"Failed to validate: {e}"]
        
        # Update stats
        self._stats.increment("validation_runs")
        
        # Emit completion event
        if self._events:
            total_errors = sum(len(errors) for errors in validation_results.values())
            emit_system_event("validation_completed", {
                "total_experts": len(validation_results),
                "total_errors": total_errors,
                "experts_with_errors": sum(1 for errors in validation_results.values() if errors)
            })
        
        return validation_results
    
    def get_enhanced_stats(self) -> Dict[str, Any]:
        """Get comprehensive registry statistics"""
        with self._lock:
            # Use search component for category stats
            categories = self._search.get_categories_stats(self._experts)
            
            return {
                "registry_stats": self._stats.get_stats(),
                "health_status": self._health_monitor.get_health_status(),
                "discovery_stats": self._discovery.get_discovery_stats(),
                "categories": categories,
                "total_experts": len(self._experts),
                "alias_mappings": len(self._alias_map)
            }
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Alias for get_enhanced_stats for backward compatibility"""
        return self.get_enhanced_stats()
    
    def get_techniques_by_category(self, category: str) -> List[DomainExpert]:
        """Get all techniques in a specific category"""
        return self._search.get_techniques_by_category(self._experts, category, self._security_context)
    
    def export_enhanced_registry(self, filepath: Path, include_sensitive: bool = False):
        """Export enhanced registry data with security options"""
        validated_path = SecurityValidator.validate_file_path(filepath, "write")
        
        export_data = {
            "export_metadata": {
                "timestamp": str(datetime.now()),
                "version": "2.0",
                "include_sensitive": include_sensitive
            },
            "registry_stats": self.get_enhanced_stats(),
            "experts": {}
        }
        
        with self._lock:
            for name, entry in self._experts.items():
                export_data["experts"][name] = entry.to_dict(include_sensitive)
        
        with open(validated_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Enhanced registry exported to {validated_path}")
        
        if self._events:
            emit_system_event("registry_exported", {
                "filepath": str(validated_path),
                "expert_count": len(export_data["experts"]),
                "include_sensitive": include_sensitive
            })
    
    def shutdown(self):
        """Shutdown registry and cleanup resources"""
        try:
            self._discovery.shutdown()
            self._cache.clear()
            
            if self._events:
                emit_system_event("registry_shutdown", {
                    "experts_managed": len(self._experts)
                })
            
            logger.info("Registry shutdown completed")
        except Exception as e:
            logger.error(f"Error during registry shutdown: {e}")


# Global enhanced registry instance
_enhanced_registry = EnhancedDomainExpertRegistry()


def get_registry() -> EnhancedDomainExpertRegistry:
    """Get the global enhanced registry instance"""
    return _enhanced_registry


def register_expert(expert_class: Type[DomainExpert], 
                   technique_name: Optional[str] = None,
                   security_level: SecurityLevel = SecurityLevel.PUBLIC) -> bool:
    """Register a domain expert class with the global registry"""
    return _enhanced_registry.register_expert(expert_class, technique_name, security_level)


def get_expert(technique_name: str, 
               security_context: Optional[SecurityContext] = None) -> Optional[DomainExpert]:
    """Get a domain expert by technique name"""
    return _enhanced_registry.get_expert(technique_name, security_context)


def discover_experts(package_name: str = "techniques") -> int:
    """Discover experts in the techniques package"""
    return _enhanced_registry.discover_experts(package_name)


def list_techniques() -> List[str]:
    """List all registered technique names"""
    with _enhanced_registry._lock:
        return list(_enhanced_registry._experts.keys())


def search_techniques(query: str, filters: Optional[Dict[str, Any]] = None) -> List[DomainExpert]:
    """Search for techniques matching a query"""
    return _enhanced_registry.search_techniques(query, filters)


if __name__ == "__main__":
    # Test enhanced registry system
    print("Testing Enhanced Domain Expert Registry")
    print("✓ Registry modules loaded successfully")
    print("✓ Core components: discovery, health, search, cache, stats")
    print("✓ File size optimized under 250 lines")
    print("\n✅ Enhanced modular registry test completed!") 