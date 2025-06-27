"""
Domain Expert Registry System

This module provides automatic discovery and registration of domain experts,
making it easy to scale to hundreds of techniques.
"""

import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List, Optional, Set, Type, Any
import logging
from dataclasses import dataclass
import threading
import json

from .core import DomainExpert, TechniqueMetadata, BiologicalContext, ExpertiseLevel


logger = logging.getLogger(__name__)


@dataclass
class RegistryEntry:
    """Entry in the domain expert registry"""
    expert_class: Type[DomainExpert]
    expert_instance: Optional[DomainExpert] = None
    metadata: Optional[TechniqueMetadata] = None
    module_path: Optional[str] = None
    last_loaded: Optional[str] = None
    
    def get_expert(self) -> DomainExpert:
        """Get expert instance, creating if necessary"""
        if self.expert_instance is None:
            self.expert_instance = self.expert_class()
            self.metadata = self.expert_instance.get_metadata()
        return self.expert_instance


class DomainExpertRegistry:
    """Registry for automatically discovering and managing domain experts"""
    
    def __init__(self):
        self._experts: Dict[str, RegistryEntry] = {}
        self._lock = threading.Lock()
        self._discovery_paths: List[Path] = []
        self._loaded_modules: Set[str] = set()
    
    def add_discovery_path(self, path: Path):
        """Add a path to search for domain experts"""
        if path.exists() and path.is_dir():
            self._discovery_paths.append(path)
            logger.info(f"Added discovery path: {path}")
        else:
            logger.warning(f"Discovery path does not exist: {path}")
    
    def register_expert(self, expert_class: Type[DomainExpert], 
                       technique_name: Optional[str] = None) -> bool:
        """Manually register a domain expert class"""
        with self._lock:
            try:
                # Create instance to get metadata
                instance = expert_class()
                metadata = instance.get_metadata()
                name = technique_name or metadata.name.lower()
                
                entry = RegistryEntry(
                    expert_class=expert_class,
                    expert_instance=instance,
                    metadata=metadata,
                    module_path=expert_class.__module__
                )
                
                self._experts[name] = entry
                logger.info(f"Registered expert: {name} ({metadata.display_name})")
                return True
                
            except Exception as e:
                logger.error(f"Failed to register expert {expert_class.__name__}: {e}")
                return False
    
    def discover_experts(self, package_name: str = "techniques") -> int:
        """Automatically discover experts in the techniques package"""
        discovered_count = 0
        
        with self._lock:
            for discovery_path in self._discovery_paths:
                try:
                    discovered_count += self._discover_in_path(discovery_path, package_name)
                except Exception as e:
                    logger.error(f"Failed to discover experts in {discovery_path}: {e}")
        
        logger.info(f"Discovered {discovered_count} new experts")
        return discovered_count
    
    def _discover_in_path(self, path: Path, package_name: str) -> int:
        """Discover experts in a specific path"""
        discovered_count = 0
        
        # Look for technique modules
        techniques_path = path / package_name
        if not techniques_path.exists():
            return 0
        
        for module_file in techniques_path.glob("*.py"):
            if module_file.name.startswith("_"):
                continue
                
            module_name = module_file.stem
            full_module_path = f"{package_name}.{module_name}"
            
            if full_module_path in self._loaded_modules:
                continue
            
            try:
                # Import the module
                spec = importlib.util.spec_from_file_location(full_module_path, module_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Look for DomainExpert subclasses
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, DomainExpert) and 
                            attr is not DomainExpert):
                            
                            # Auto-register the expert
                            if self.register_expert(attr):
                                discovered_count += 1
                    
                    self._loaded_modules.add(full_module_path)
                    
            except Exception as e:
                logger.error(f"Failed to load module {full_module_path}: {e}")
        
        return discovered_count
    
    def get_expert(self, technique_name: str) -> Optional[DomainExpert]:
        """Get a domain expert by technique name"""
        with self._lock:
            entry = self._experts.get(technique_name.lower())
            if entry:
                return entry.get_expert()
            return None
    
    def get_expert_by_alias(self, alias: str) -> Optional[DomainExpert]:
        """Get expert by any of its aliases"""
        alias_lower = alias.lower()
        with self._lock:
            for entry in self._experts.values():
                if entry.metadata and alias_lower in [a.lower() for a in entry.metadata.aliases]:
                    return entry.get_expert()
        return None
    
    def list_techniques(self) -> List[str]:
        """List all registered technique names"""
        with self._lock:
            return list(self._experts.keys())
    
    def list_experts(self) -> List[DomainExpert]:
        """List all registered experts"""
        with self._lock:
            return [entry.get_expert() for entry in self._experts.values()]
    
    def search_techniques(self, query: str) -> List[DomainExpert]:
        """Search for techniques matching a query"""
        query_lower = query.lower()
        matches = []
        
        with self._lock:
            for entry in self._experts.values():
                if entry.metadata and entry.metadata.matches_query(query):
                    matches.append(entry.get_expert())
        
        return matches
    
    def get_techniques_by_category(self, category: str) -> List[DomainExpert]:
        """Get all techniques in a specific category"""
        category_lower = category.lower()
        matches = []
        
        with self._lock:
            for entry in self._experts.values():
                if (entry.metadata and 
                    entry.metadata.category.lower() == category_lower):
                    matches.append(entry.get_expert())
        
        return matches
    
    def get_techniques_by_expertise(self, level: ExpertiseLevel) -> List[DomainExpert]:
        """Get techniques requiring specific expertise level"""
        matches = []
        
        with self._lock:
            for entry in self._experts.values():
                if (entry.metadata and 
                    entry.metadata.required_expertise == level):
                    matches.append(entry.get_expert())
        
        return matches
    
    def validate_all_experts(self) -> Dict[str, List[str]]:
        """Validate all registered experts"""
        validation_results = {}
        
        with self._lock:
            for name, entry in self._experts.items():
                try:
                    expert = entry.get_expert()
                    errors = expert.validate_prompts()
                    validation_results[name] = errors
                except Exception as e:
                    validation_results[name] = [f"Failed to validate: {e}"]
        
        return validation_results
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get statistics about the registry"""
        with self._lock:
            stats = {
                "total_experts": len(self._experts),
                "loaded_modules": len(self._loaded_modules),
                "discovery_paths": len(self._discovery_paths),
                "categories": {},
                "expertise_levels": {},
                "contexts": {}
            }
            
            for entry in self._experts.values():
                if entry.metadata:
                    # Count by category
                    cat = entry.metadata.category
                    stats["categories"][cat] = stats["categories"].get(cat, 0) + 1
                    
                    # Count by expertise level
                    level = entry.metadata.required_expertise.value
                    stats["expertise_levels"][level] = stats["expertise_levels"].get(level, 0) + 1
                    
                    # Count prompts by context
                    try:
                        expert = entry.get_expert()
                        prompts = expert.get_prompts()
                        for prompt in prompts.values():
                            context = prompt.biological_context.value
                            stats["contexts"][context] = stats["contexts"].get(context, 0) + 1
                    except Exception:
                        pass
            
            return stats
    
    def export_registry(self, filepath: Path):
        """Export registry metadata to JSON"""
        data = {
            "experts": {},
            "stats": self.get_registry_stats()
        }
        
        with self._lock:
            for name, entry in self._experts.items():
                if entry.metadata:
                    data["experts"][name] = {
                        "metadata": entry.metadata.__dict__,
                        "module_path": entry.module_path,
                        "prompt_count": len(entry.get_expert().get_prompts())
                    }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def clear_registry(self):
        """Clear all registered experts (for testing)"""
        with self._lock:
            self._experts.clear()
            self._loaded_modules.clear()


# Global registry instance
_registry = DomainExpertRegistry()


def get_registry() -> DomainExpertRegistry:
    """Get the global registry instance"""
    return _registry


def register_expert(expert_class: Type[DomainExpert], 
                   technique_name: Optional[str] = None) -> bool:
    """Register a domain expert class with the global registry"""
    return _registry.register_expert(expert_class, technique_name)


def get_expert(technique_name: str) -> Optional[DomainExpert]:
    """Get a domain expert by technique name"""
    return _registry.get_expert(technique_name)


def discover_experts(package_name: str = "techniques") -> int:
    """Discover experts in the techniques package"""
    return _registry.discover_experts(package_name)


def list_techniques() -> List[str]:
    """List all registered technique names"""
    return _registry.list_techniques()


def search_techniques(query: str) -> List[DomainExpert]:
    """Search for techniques matching a query"""
    return _registry.search_techniques(query)


if __name__ == "__main__":
    # Test the registry system
    print("Testing Domain Expert Registry")
    
    # Initialize registry
    registry = get_registry()
    
    # Add current directory as discovery path
    current_dir = Path(__file__).parent
    registry.add_discovery_path(current_dir)
    
    print(f"Registry stats: {registry.get_registry_stats()}")
    print(f"Available techniques: {list_techniques()}")
    
    # Test search
    print(f"Search for 'rna': {[e.get_technique_name() for e in search_techniques('rna')]}")
    
    # Validation
    validation_results = registry.validate_all_experts()
    print(f"Validation results: {validation_results}") 