"""
Domain Prompts System

A scalable system for managing domain-specific biological analysis prompts.
This package provides expert knowledge for hundreds of biological techniques.

Usage:
    from domain_prompts import get_expert, list_techniques, search_techniques
    
    # Get an expert for a specific technique
    expert = get_expert("scrnaseq")
    
    # List all available techniques
    techniques = list_techniques()
    
    # Search for techniques
    rna_experts = search_techniques("rna")
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

# Import core components
from .core import (
    DomainExpert, DomainPrompt, TechniqueMetadata,
    ExpertiseLevel, BiologicalContext, BaseDomainExpert
)

from .registry import (
    DomainExpertRegistry, get_registry, register_expert,
    get_expert, discover_experts, list_techniques, search_techniques
)

from .template import DomainExpertTemplate, TechniqueGenerator

# Import enhanced features
from .security import SecurityValidator, SecurityLevel, SecurityContext
from .events import EventEmitter, get_event_emitter, emit_system_event, emit_ui_update, emit_error
from .performance import PerformanceMonitor, get_performance_monitor, time_it
from .async_support import AsyncDomainPrompt, AsyncDomainExpert, create_async_expert, async_timer

# Set up logging
logger = logging.getLogger(__name__)

# Package metadata
__version__ = "2.0.0"
__author__ = "Gliaent Bioinformatics Team"
__description__ = "Scalable domain expert system for biological analysis"

# Global registry instance
_registry = get_registry()

def initialize_system(
    techniques_dir: Optional[Path] = None,
    auto_discover: bool = True,
    log_level: str = "INFO",
    security_level: SecurityLevel = SecurityLevel.PUBLIC,
    enable_events: bool = True,
    enable_performance_monitoring: bool = True
) -> Dict[str, Any]:
    """
    Initialize the enhanced domain prompts system
    
    Args:
        techniques_dir: Directory containing technique modules
        auto_discover: Whether to automatically discover experts
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        security_level: Default security level for the system
        enable_events: Whether to enable event system for Electron integration
        enable_performance_monitoring: Whether to enable performance monitoring
    
    Returns:
        Dictionary with initialization results
    """
    # Set up logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Add discovery paths
    if techniques_dir is None:
        techniques_dir = Path(__file__).parent / "techniques"
    
    _registry.add_discovery_path(techniques_dir.parent)
    
    # Configure event system
    event_emitter = get_event_emitter()
    event_emitter.set_enabled(enable_events)
    
    # Emit system initialization event
    if enable_events:
        emit_system_event("system_initializing", {
            "version": __version__,
            "security_level": security_level.value,
            "performance_monitoring": enable_performance_monitoring
        })
    
    # Import technique modules to trigger auto-registration
    if auto_discover:
        try:
            # Import the techniques package to trigger module loading
            from . import techniques
            discovered_count = discover_experts()
        except ImportError as e:
            logger.warning(f"Could not import techniques package: {e}")
            discovered_count = 0
    else:
        discovered_count = 0
    
    # Get initialization stats
    stats = _registry.get_registry_stats()
    
    # Performance monitoring setup
    perf_stats = {}
    if enable_performance_monitoring:
        perf_monitor = get_performance_monitor()
        perf_stats = perf_monitor.get_stats()
    
    result = {
        "version": __version__,
        "discovered_experts": discovered_count,
        "total_experts": stats["total_experts"],
        "categories": list(stats["categories"].keys()),
        "techniques_available": list_techniques(),
        "initialization_success": True,
        "security_level": security_level.value,
        "events_enabled": enable_events,
        "performance_monitoring_enabled": enable_performance_monitoring,
        "performance_stats": perf_stats
    }
    
    logger.info(f"Domain Prompts System initialized successfully")
    logger.info(f"Version: {__version__}")
    logger.info(f"Experts available: {stats['total_experts']}")
    logger.info(f"Categories: {', '.join(stats['categories'].keys())}")
    logger.info(f"Security level: {security_level.value}")
    logger.info(f"Events enabled: {enable_events}")
    logger.info(f"Performance monitoring: {enable_performance_monitoring}")
    
    # Emit completion event
    if enable_events:
        emit_system_event("system_initialized", result)
    
    return result


def get_system_info() -> Dict[str, Any]:
    """Get comprehensive information about the system"""
    stats = _registry.get_registry_stats()
    event_stats = get_event_emitter().get_stats()
    perf_stats = get_performance_monitor().get_stats()
    
    return {
        "version": __version__,
        "author": __author__,
        "description": __description__,
        "registry_stats": stats,
        "available_techniques": list_techniques(),
        "expertise_levels": [level.value for level in ExpertiseLevel],
        "biological_contexts": [context.value for context in BiologicalContext],
        "security_levels": [level.value for level in SecurityLevel],
        "event_stats": event_stats,
        "performance_stats": perf_stats,
        "features": {
            "async_support": True,
            "caching": True,
            "security_validation": True,
            "electron_integration": True,
            "performance_monitoring": True
        }
    }


def validate_system() -> Dict[str, Any]:
    """Validate the entire system and return results"""
    validation_results = _registry.validate_all_experts()
    
    total_errors = sum(len(errors) for errors in validation_results.values())
    experts_with_errors = len([name for name, errors in validation_results.items() if errors])
    
    # Emit validation event
    emit_system_event("system_validated", {
        "total_experts": len(validation_results),
        "experts_with_errors": experts_with_errors,
        "total_errors": total_errors,
        "system_healthy": total_errors == 0
    })
    
    return {
        "total_experts": len(validation_results),
        "experts_with_errors": experts_with_errors,
        "total_errors": total_errors,
        "validation_results": validation_results,
        "system_healthy": total_errors == 0
    }


def export_system_data(output_path: Path, include_prompts: bool = False, 
                      include_performance: bool = False):
    """Export system data for documentation or backup"""
    # Validate output path for security
    validated_path = SecurityValidator.validate_file_path(output_path, "write")
    
    data = {
        "system_info": get_system_info(),
        "experts": {}
    }
    
    # Add performance data if requested
    if include_performance:
        data["performance_data"] = get_performance_monitor().get_stats()
        data["event_data"] = get_event_emitter().get_stats()
    
    for technique_name in list_techniques():
        expert = get_expert(technique_name)
        if expert:
            metadata = expert.get_metadata()
            expert_data = {
                "metadata": metadata.to_dict(),
                "prompt_count": len(expert.get_prompts())
            }
            
            if include_prompts:
                expert_data["prompts"] = {
                    name: prompt.to_dict(include_internal=True) 
                    for name, prompt in expert.get_prompts().items()
                }
            
            data["experts"][technique_name] = expert_data
    
    # Export to JSON
    import json
    with open(validated_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    logger.info(f"System data exported to {validated_path}")
    emit_system_event("system_exported", {
        "output_path": str(validated_path),
        "include_prompts": include_prompts,
        "include_performance": include_performance
    })


def create_new_technique(
    technique_name: str,
    display_name: str,
    description: str,
    category: str,
    output_dir: Optional[Path] = None,
    **kwargs
) -> Path:
    """Create a new technique using the template system with security validation"""
    # Validate inputs
    technique_name = SecurityValidator.validate_identifier(technique_name, "technique_name")
    display_name = SecurityValidator.validate_string(display_name, 200, "display_name")
    description = SecurityValidator.validate_string(description, 2000, "description")
    category = SecurityValidator.validate_string(category, 100, "category")
    
    if output_dir is None:
        output_dir = Path(__file__).parent / "techniques"
    
    # Validate output directory
    output_dir = SecurityValidator.validate_file_path(output_dir, "write")
    
    # Create basic expert
    expert = DomainExpertTemplate.create_basic_expert(
        technique_name=technique_name,
        display_name=display_name,
        description=description,
        category=category,
        **kwargs
    )
    
    # Generate module code
    module_code = DomainExpertTemplate.generate_expert_module_code(
        technique_name=technique_name,
        display_name=display_name,
        description=description,
        category=category,
        prompts_config=[
            {
                "name": "basic_interpretation",
                "description": f"Basic interpretation for {display_name}",
                "template": f"Basic interpretation template for {display_name}",
                "parameters": ["key_findings", "significance"],
                "biological_context": "GENE_EXPRESSION",
                "expertise_level": "INTERMEDIATE",
                "tags": ["basic", "interpretation"]
            }
        ],
        **kwargs
    )
    
    # Write to file
    filename = f"{technique_name.lower().replace(' ', '_').replace('-', '_')}.py"
    output_path = output_dir / filename
    
    with open(output_path, 'w') as f:
        f.write(module_code)
    
    logger.info(f"Created new technique module: {output_path}")
    emit_system_event("technique_created", {
        "technique_name": technique_name,
        "output_path": str(output_path)
    })
    
    return output_path


# Convenience functions for common operations
def get_prompts_by_context(context: BiologicalContext) -> Dict[str, List[DomainPrompt]]:
    """Get all prompts grouped by technique for a specific biological context"""
    results = {}
    
    for technique_name in list_techniques():
        expert = get_expert(technique_name)
        if expert:
            context_prompts = expert.get_prompts_by_context(context)
            if context_prompts:
                results[technique_name] = list(context_prompts.values())
    
    return results


def get_techniques_by_category(category: str) -> List[str]:
    """Get technique names for a specific category"""
    experts = _registry.get_techniques_by_category(category)
    return [expert.get_technique_name() for expert in experts]


def find_related_techniques(technique_name: str) -> List[str]:
    """Find techniques related to the given technique"""
    expert = get_expert(technique_name)
    if expert:
        metadata = expert.get_metadata()
        return metadata.related_techniques
    return []


# Async convenience functions
async def get_expert_async(technique_name: str) -> Optional[AsyncDomainExpert]:
    """Get async wrapper for a domain expert"""
    expert = get_expert(technique_name)
    if expert:
        return await create_async_expert(expert)
    return None


# Compatibility alias for get_domain_prompts
get_domain_prompts = get_expert

# Export main functions for easy access
__all__ = [
    # Core classes
    "DomainExpert", "DomainPrompt", "TechniqueMetadata",
    "ExpertiseLevel", "BiologicalContext", "BaseDomainExpert",
    
    # Enhanced features
    "SecurityValidator", "SecurityLevel", "SecurityContext",
    "EventEmitter", "get_event_emitter", "emit_system_event", "emit_ui_update", "emit_error",
    "PerformanceMonitor", "get_performance_monitor", "time_it",
    "AsyncDomainPrompt", "AsyncDomainExpert", "create_async_expert", "async_timer",
    
    # Registry functions
    "register_expert", "get_expert", "list_techniques", "search_techniques",
    "discover_experts", "get_registry",
    
    # Compatibility functions
    "get_domain_prompts",  # Alias for get_expert
    
    # Template system
    "DomainExpertTemplate", "TechniqueGenerator",
    
    # System functions
    "initialize_system", "get_system_info", "validate_system",
    "export_system_data", "create_new_technique",
    
    # Convenience functions
    "get_prompts_by_context", "get_techniques_by_category", "find_related_techniques",
    "get_expert_async",
    
    # Package metadata
    "__version__", "__author__", "__description__"
]


# Auto-initialize when package is imported
try:
    _init_result = initialize_system()
    logger.debug(f"Auto-initialization completed: {_init_result}")
except Exception as e:
    logger.warning(f"Auto-initialization failed: {e}")
    logger.info("System can still be used, but manual initialization may be needed")


if __name__ == "__main__":
    # Package testing and demonstration
    print("Domain Prompts System - Enhanced Package Test")
    print("=" * 55)
    
    # System info
    info = get_system_info()
    print(f"Version: {info['version']}")
    print(f"Available techniques: {len(info['available_techniques'])}")
    print(f"Categories: {', '.join(info['registry_stats']['categories'].keys())}")
    print(f"Features: {', '.join(info['features'].keys())}")
    
    # Validation
    validation = validate_system()
    print(f"\nSystem validation:")
    print(f"- Total experts: {validation['total_experts']}")
    print(f"- Experts with errors: {validation['experts_with_errors']}")
    print(f"- System healthy: {validation['system_healthy']}")
    
    # Event system test
    event_stats = get_event_emitter().get_stats()
    print(f"\nEvent system:")
    print(f"- Events emitted: {event_stats['events_emitted']}")
    print(f"- Queue size: {event_stats['main_queue_size']}")
    
    # Performance monitoring test
    perf_stats = get_performance_monitor().get_stats()
    print(f"\nPerformance monitoring:")
    print(f"- Tracked operations: {perf_stats['system']['tracked_operations']}")
    print(f"- Uptime: {perf_stats['system']['uptime_seconds']:.2f}s")
    
    # Example usage
    print(f"\nExample usage:")
    
    # Get scRNA-seq expert if available
    if "scrnaseq" in list_techniques():
        expert = get_expert("scrnaseq")
        print(f"- scRNA-seq expert loaded: {expert.get_metadata().display_name}")
        print(f"- Available prompts: {len(expert.get_prompts())}")
        
        # Test a prompt
        marker_prompt = expert.get_prompt_by_name("interpret_markers")
        if marker_prompt:
            print(f"- Example prompt: {marker_prompt.name}")
    
    print("\n✅ Enhanced package test completed successfully!") 