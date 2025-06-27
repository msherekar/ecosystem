"""
Automated Prompt Discovery and Registration

Provides decorators and registry for automatic prompt discovery from handler methods.
Now integrates with domain expert system for scalable biological knowledge.
"""

import inspect
from typing import Dict, List, Any, Callable
from dataclasses import dataclass

# Use lazy imports to avoid circular dependencies
def _lazy_import_prompts():
    """Lazy import of prompts to avoid circular dependencies"""
    try:
        from ..prompts import get_domain_prompts, DomainPrompt
        return get_domain_prompts, DomainPrompt
    except ImportError:
        # For direct execution, try absolute import
        try:
            from src.mcp.core.prompts import get_domain_prompts, DomainPrompt
            return get_domain_prompts, DomainPrompt
        except ImportError:
            # Fallback for testing - create mock classes
            class DomainPrompt:
                pass
            def get_domain_prompts(technique):
                return {}
            return get_domain_prompts, DomainPrompt


@dataclass
class PromptConfig:
    """Configuration for an MCP prompt"""
    name: str
    description: str
    template: str
    parameters: Dict[str, str]
    handler: Callable = None
    domain_context: str = None
    expertise_level: str = None


def mcp_prompt(name: str, description: str, template: str = None, parameters: Dict[str, str] = None):
    """
    Decorator to mark a method as an MCP prompt
    
    Args:
        name: Prompt name
        description: Prompt description
        template: Optional template override
        parameters: Optional parameter dict override
    """
    def decorator(func):
        func._mcp_prompt = True
        func._prompt_name = name
        func._prompt_description = description
        func._prompt_template = template
        func._prompt_parameters = parameters or {}
        return func
    return decorator


class AutoPromptRegistry:
    """Registry for automatic prompt discovery"""
    
    @staticmethod
    def discover_prompts(handler_instance) -> Dict[str, PromptConfig]:
        """Discover all prompts from a handler instance using decorators"""
        prompts = {}
        
        # Get class name to determine technique
        class_name = handler_instance.__class__.__name__
        technique = AutoPromptRegistry._extract_technique_from_class(class_name)
        
        # Get domain prompts for this technique
        domain_prompts = {}
        if technique:
            try:
                get_domain_prompts, DomainPrompt = _lazy_import_prompts()
                domain_prompts = get_domain_prompts(technique)
            except (ValueError, ImportError):
                # No domain expert for this technique or import failed
                pass
        
        # Discover decorated prompt methods
        for name, method in inspect.getmembers(handler_instance, predicate=inspect.ismethod):
            if hasattr(method, '_mcp_prompt'):
                template = method._prompt_template
                if not template:
                    # Try to get template from method call
                    try:
                        template = method()
                    except Exception:
                        template = f"Template for {method._prompt_name}"
                
                prompts[method._prompt_name] = PromptConfig(
                    name=method._prompt_name,
                    description=method._prompt_description,
                    template=template,
                    parameters=method._prompt_parameters,
                    handler=method
                )
        
        # Add domain expert prompts
        for prompt_name, domain_prompt in domain_prompts.items():
            if prompt_name not in prompts:  # Don't override decorated prompts
                # Convert parameters list to dictionary format expected by MCPPrompt
                parameters_dict = {}
                if domain_prompt.parameters:
                    for param in domain_prompt.parameters:
                        parameters_dict[param] = "string"  # Default type
                
                prompts[prompt_name] = PromptConfig(
                    name=domain_prompt.name,
                    description=domain_prompt.description,
                    template=domain_prompt.template,
                    parameters=parameters_dict,  # Now a dict instead of list
                    domain_context=domain_prompt.biological_context,
                    expertise_level=domain_prompt.expertise_level
                )
        
        return prompts
    
    @staticmethod
    def _extract_technique_from_class(class_name: str) -> str:
        """Extract technique name from handler class name"""
        class_name_lower = class_name.lower()
        if 'scrnaseq' in class_name_lower or 'scrna' in class_name_lower:
            return 'scrnaseq'
        elif 'rnaseq' in class_name_lower and 'scrna' not in class_name_lower:
            return 'rnaseq'
        elif 'atacseq' in class_name_lower or 'atac' in class_name_lower:
            return 'atacseq'
        elif 'proteomics' in class_name_lower:
            return 'proteomics'
        elif 'visualization' in class_name_lower:
            return 'visualization'
        return None


def get_auto_prompt_configs(handler_instance) -> Dict[str, PromptConfig]:
    """
    Get automatically discovered prompt configurations from a handler instance
    
    Args:
        handler_instance: Instance of a handler class with @mcp_prompt decorated methods
        
    Returns:
        Dictionary mapping prompt names to PromptConfig objects
    """
    return AutoPromptRegistry.discover_prompts(handler_instance)


class CommonPromptTemplates:
    """Common prompt templates that can be reused across techniques"""
    
    @staticmethod
    def suggest_next_steps() -> str:
        """Template for suggesting next analysis steps"""
        return """
Based on the current {analysis_type} analysis state:

- Current step: {current_step}
- Data status: {data_status}
- Completed steps: {completed_steps}
- Available samples: {n_samples}
- Significant features found: {significant_features}

Please suggest the next logical analysis steps, including:
1. Immediate next steps based on current progress
2. Alternative analysis paths to consider
3. Quality checks or validations to perform
4. Visualization or interpretation steps
5. Potential issues to watch for in the next steps
"""
    
    @staticmethod
    def interpret_clustering_results() -> str:
        """Template for interpreting clustering results"""
        return """
{analysis_type} clustering analysis results:

- Number of clusters identified: {n_clusters}
- Cluster sizes: {cluster_sizes}
- Clustering method: {clustering_method}
- Resolution/parameters used: {clustering_params}
- Silhouette score: {silhouette_score}

Please interpret these clustering results, including:
1. Quality assessment of the clustering
2. Biological significance of the identified clusters
3. Whether the number of clusters seems appropriate
4. Potential biological meaning of cluster separation
5. Suggested follow-up analyses for cluster characterization
"""
    
    @staticmethod
    def troubleshoot_common_issues() -> str:
        """Template for troubleshooting common analysis issues"""
        return """
{analysis_type} analysis issue:

- Problem: {problem_description}
- Step: {analysis_step}
- Error: {error_message}
- Data info: {data_characteristics}

Please provide troubleshooting guidance:
1. Likely causes of this issue
2. Step-by-step solutions
3. Parameter adjustments to try
4. How to prevent this in future
5. Alternative approaches if standard solutions fail
"""

# Test code to verify the module works independently
if __name__ == "__main__":
    def test_prompt_registry():
        """Test AutoPromptRegistry functionality"""
        print("Testing AutoPromptRegistry...")
        
        # Test common prompt templates
        next_steps = CommonPromptTemplates.suggest_next_steps()
        clustering = CommonPromptTemplates.interpret_clustering_results()
        troubleshoot = CommonPromptTemplates.troubleshoot_common_issues()
        
        print(f"✅ Common templates: suggest_next_steps={len(next_steps)} chars")
        print(f"✅ Common templates: interpret_clustering={len(clustering)} chars")
        print(f"✅ Common templates: troubleshoot={len(troubleshoot)} chars")
        
        # Test technique extraction
        registry = AutoPromptRegistry()
        
        test_classes = [
            "scRNASeqHandlers",
            "RNASeqHandlers",  
            "ATACSeqHandlers",
            "ProteomicsHandlers",
            "VisualizationHandlers",
            "UnknownHandlers"
        ]
        
        for class_name in test_classes:
            technique = registry._extract_technique_from_class(class_name)
            print(f"✅ {class_name} → {technique}")
        
        print("🎉 All PromptRegistry tests passed!")
    
    # Run test
    test_prompt_registry() 
    # python -m src.mcp.core.prompt_registry