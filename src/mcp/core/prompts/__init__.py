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
    log_level: str = "INFO"
) -> Dict[str, Any]:
    """
    Initialize the domain prompts system
    
    Args:
        techniques_dir: Directory containing technique modules
        auto_discover: Whether to automatically discover experts
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    
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
    
    result = {
        "version": __version__,
        "discovered_experts": discovered_count,
        "total_experts": stats["total_experts"],
        "categories": list(stats["categories"].keys()),
        "techniques_available": list_techniques(),
        "initialization_success": True
    }
    
    logger.info(f"Domain Prompts System initialized successfully")
    logger.info(f"Version: {__version__}")
    logger.info(f"Experts available: {stats['total_experts']}")
    logger.info(f"Categories: {', '.join(stats['categories'].keys())}")
    
    return result


def get_system_info() -> Dict[str, Any]:
    """Get comprehensive information about the system"""
    stats = _registry.get_registry_stats()
    
    return {
        "version": __version__,
        "author": __author__,
        "description": __description__,
        "registry_stats": stats,
        "available_techniques": list_techniques(),
        "expertise_levels": list(ExpertiseLevel),
        "biological_contexts": list(BiologicalContext)
    }


def validate_system() -> Dict[str, Any]:
    """Validate the entire system and return results"""
    validation_results = _registry.validate_all_experts()
    
    total_errors = sum(len(errors) for errors in validation_results.values())
    experts_with_errors = len([name for name, errors in validation_results.items() if errors])
    
    return {
        "total_experts": len(validation_results),
        "experts_with_errors": experts_with_errors,
        "total_errors": total_errors,
        "validation_results": validation_results,
        "system_healthy": total_errors == 0
    }


def export_system_data(output_path: Path, include_prompts: bool = False):
    """Export system data for documentation or backup"""
    data = {
        "system_info": get_system_info(),
        "experts": {}
    }
    
    for technique_name in list_techniques():
        expert = get_expert(technique_name)
        if expert:
            metadata = expert.get_metadata()
            expert_data = {
                "metadata": metadata.__dict__,
                "prompt_count": len(expert.get_prompts())
            }
            
            if include_prompts:
                expert_data["prompts"] = {
                    name: prompt.to_dict() 
                    for name, prompt in expert.get_prompts().items()
                }
            
            data["experts"][technique_name] = expert_data
    
    # Export to JSON
    import json
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    logger.info(f"System data exported to {output_path}")


def create_new_technique(
    technique_name: str,
    display_name: str,
    description: str,
    category: str,
    output_dir: Optional[Path] = None,
    **kwargs
) -> Path:
    """Create a new technique using the template system"""
    if output_dir is None:
        output_dir = Path(__file__).parent / "techniques"
    
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


# Compatibility alias for get_domain_prompts
get_domain_prompts = get_expert

# Export main functions for easy access
__all__ = [
    # Core classes
    "DomainExpert", "DomainPrompt", "TechniqueMetadata",
    "ExpertiseLevel", "BiologicalContext", "BaseDomainExpert",
    
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
    print("Domain Prompts System - Package Test")
    print("=" * 50)
    
    # System info
    info = get_system_info()
    print(f"Version: {info['version']}")
    print(f"Available techniques: {len(info['available_techniques'])}")
    print(f"Categories: {', '.join(info['registry_stats']['categories'].keys())}")
    
    # Validation
    validation = validate_system()
    print(f"\nSystem validation:")
    print(f"- Total experts: {validation['total_experts']}")
    print(f"- Experts with errors: {validation['experts_with_errors']}")
    print(f"- System healthy: {validation['system_healthy']}")
    
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
    
    print("\nPackage test completed successfully!") 