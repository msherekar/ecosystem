"""
Prompt Domain Integration

Handles integration with domain expert systems for biological knowledge.
Provides technique-specific prompts from domain experts.

This file is separate from the core prompt registry to keep concerns separated
and allow for easy testing and maintenance.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

try:
    from .prompt_registry import PromptConfig, PromptCategory, SecurityLevel
except ImportError:
    from prompt_registry import PromptConfig, PromptCategory, SecurityLevel

# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class DomainPrompt:
    """Domain expert prompt definition"""
    name: str
    description: str
    template: str
    parameters: list  # List of parameter names
    biological_context: str
    expertise_level: str


class TechniqueDetector:
    """Detects analysis technique from handler class names"""
    
    @staticmethod
    def extract_technique_from_class(class_name: str) -> Optional[str]:
        """Extract technique name from handler class name"""
        class_name_lower = class_name.lower()
        
        # Define technique patterns in order of specificity
        patterns = [
            ('scrnaseq', ['scrnaseq', 'scrna']),
            ('rnaseq', ['rnaseq']),  # Must come after scrnaseq
            ('atacseq', ['atacseq', 'atac']),
            ('proteomics', ['proteomics']),
            ('visualization', ['visualization', 'viz']),
            ('chipseq', ['chipseq', 'chip']),
            ('wgs', ['wgs', 'genome']),
            ('metabolomics', ['metabolomics', 'metab'])
        ]
        
        for technique, keywords in patterns:
            if any(keyword in class_name_lower for keyword in keywords):
                return technique
        
        return None


class DomainExpertMock:
    """Mock domain expert system for testing and fallback"""
    
    def __init__(self):
        self.prompts = {
            'scrnaseq': {
                'suggest_next_steps': DomainPrompt(
                    name='suggest_next_steps',
                    description='Suggest next steps for scRNA-seq analysis',
                    template='Based on your current scRNA-seq analysis:\n{current_state}\n\nI recommend these next steps:\n1. {step1}\n2. {step2}\n3. {step3}',
                    parameters=['current_state', 'step1', 'step2', 'step3'],
                    biological_context='single-cell RNA sequencing',
                    expertise_level='intermediate'
                ),
                'interpret_clusters': DomainPrompt(
                    name='interpret_clusters',
                    description='Help interpret scRNA-seq clustering results',
                    template='Your scRNA-seq clustering identified {n_clusters} clusters:\n{cluster_info}\n\nBiological interpretation:\n{interpretation}',
                    parameters=['n_clusters', 'cluster_info', 'interpretation'],
                    biological_context='cell type identification',
                    expertise_level='expert'
                )
            },
            'rnaseq': {
                'interpret_de_results': DomainPrompt(
                    name='interpret_de_results',
                    description='Interpret differential expression results',
                    template='Differential expression analysis found {n_genes} significant genes:\n{top_genes}\n\nBiological significance:\n{interpretation}',
                    parameters=['n_genes', 'top_genes', 'interpretation'],
                    biological_context='gene expression analysis',
                    expertise_level='intermediate'
                )
            },
            'visualization': {
                'improve_plot': DomainPrompt(
                    name='improve_plot',
                    description='Suggest improvements for biological data visualizations',
                    template='Current plot: {plot_type}\nData: {data_description}\n\nSuggested improvements:\n{improvements}',
                    parameters=['plot_type', 'data_description', 'improvements'],
                    biological_context='data visualization',
                    expertise_level='beginner'
                )
            }
        }
    
    def get_prompts(self, technique: str) -> Dict[str, DomainPrompt]:
        """Get prompts for a specific technique"""
        return self.prompts.get(technique, {})


class DomainExpertIntegration:
    """Integration layer for domain expert systems"""
    
    def __init__(self):
        self.logger = logger.getChild("DomainIntegration")
        self._expert_systems = {}
        self._fallback_expert = DomainExpertMock()
        
        # Try to load real domain expert systems
        self._load_expert_systems()
    
    def _load_expert_systems(self):
        """Load available domain expert systems"""
        try:
            # Try to import real domain expert systems
            from ..prompts import get_domain_prompts, DomainPrompt as RealDomainPrompt
            
            self._expert_systems['real'] = get_domain_prompts
            self.logger.info("Loaded real domain expert system")
            
        except ImportError:
            self.logger.debug("Real domain expert system not available, using fallback")
    
    def get_domain_prompts_for_technique(self, technique: str) -> Dict[str, PromptConfig]:
        """Get domain prompts for a specific technique"""
        try:
            # Try real expert system first
            if 'real' in self._expert_systems:
                domain_prompts = self._expert_systems['real'](technique)
                return self._convert_real_prompts(domain_prompts)
            
            # Fall back to mock system
            domain_prompts = self._fallback_expert.get_prompts(technique)
            return self._convert_mock_prompts(domain_prompts)
            
        except Exception as e:
            self.logger.warning(f"Error getting domain prompts for {technique}: {e}")
            return {}
    
    def _convert_real_prompts(self, domain_prompts: Dict[str, Any]) -> Dict[str, PromptConfig]:
        """Convert real domain prompts to PromptConfig objects"""
        converted = {}
        
        for prompt_name, domain_prompt in domain_prompts.items():
            try:
                # Convert parameters list to dictionary format
                parameters_dict = {}
                if hasattr(domain_prompt, 'parameters') and domain_prompt.parameters:
                    for param in domain_prompt.parameters:
                        parameters_dict[param] = "string"  # Default type
                
                converted[prompt_name] = PromptConfig(
                    name=domain_prompt.name,
                    description=domain_prompt.description,
                    template=domain_prompt.template,
                    parameters=parameters_dict,
                    category=PromptCategory.ANALYSIS,  # Default for domain prompts
                    security_level=SecurityLevel.PUBLIC,  # Domain prompts are typically public
                    domain_context=getattr(domain_prompt, 'biological_context', None),
                    expertise_level=getattr(domain_prompt, 'expertise_level', None),
                    version="1.0.0",
                    metadata={
                        "source": "domain_expert",
                        "technique": getattr(domain_prompt, 'technique', 'unknown')
                    }
                )
                
            except Exception as e:
                self.logger.warning(f"Error converting real prompt {prompt_name}: {e}")
                continue
        
        return converted
    
    def _convert_mock_prompts(self, domain_prompts: Dict[str, DomainPrompt]) -> Dict[str, PromptConfig]:
        """Convert mock domain prompts to PromptConfig objects"""
        converted = {}
        
        for prompt_name, domain_prompt in domain_prompts.items():
            try:
                # Convert parameters list to dictionary format
                parameters_dict = {}
                if domain_prompt.parameters:
                    for param in domain_prompt.parameters:
                        parameters_dict[param] = "string"  # Default type
                
                converted[prompt_name] = PromptConfig(
                    name=domain_prompt.name,
                    description=domain_prompt.description,
                    template=domain_prompt.template,
                    parameters=parameters_dict,
                    category=PromptCategory.ANALYSIS,
                    security_level=SecurityLevel.PUBLIC,
                    domain_context=domain_prompt.biological_context,
                    expertise_level=domain_prompt.expertise_level,
                    version="1.0.0",
                    metadata={
                        "source": "mock_domain_expert",
                        "biological_context": domain_prompt.biological_context
                    }
                )
                
            except Exception as e:
                self.logger.warning(f"Error converting mock prompt {prompt_name}: {e}")
                continue
        
        return converted


# Global integration instance
domain_integration = DomainExpertIntegration()


def get_domain_prompts_for_handler(handler_instance) -> Dict[str, PromptConfig]:
    """
    Get domain expert prompts for a handler instance
    
    Args:
        handler_instance: Handler instance to get prompts for
        
    Returns:
        Dictionary of domain expert prompts
    """
    try:
        # Extract technique from class name
        class_name = handler_instance.__class__.__name__
        technique = TechniqueDetector.extract_technique_from_class(class_name)
        
        if not technique:
            logger.debug(f"No technique detected for {class_name}")
            return {}
        
        # Get domain prompts for the technique
        return domain_integration.get_domain_prompts_for_technique(technique)
        
    except Exception as e:
        logger.error(f"Error getting domain prompts for handler {handler_instance.__class__.__name__}: {e}")
        return {}


def register_expert_system(name: str, expert_system: Any):
    """Register a new domain expert system"""
    domain_integration._expert_systems[name] = expert_system
    logger.info(f"Registered domain expert system: {name}")


def get_supported_techniques() -> List[str]:
    """Get list of supported analysis techniques"""
    return list(domain_integration._fallback_expert.prompts.keys())


def main():
    """Main function for module testing"""
    print("Testing Domain Integration...")
    
    # Test technique detection
    detector = TechniqueDetector()
    test_classes = [
        "scRNASeqHandlers",
        "RNASeqHandlers",
        "ATACSeqHandlers", 
        "ProteomicsHandlers",
        "VisualizationHandlers",
        "UnknownHandlers"
    ]
    
    for class_name in test_classes:
        technique = detector.extract_technique_from_class(class_name)
        print(f"✅ {class_name} → {technique}")
    
    # Test domain expert mock
    expert = DomainExpertMock()
    for technique in get_supported_techniques():
        prompts = expert.get_prompts(technique)
        print(f"✅ {technique}: {len(prompts)} prompts")
        
        for prompt_name, prompt in prompts.items():
            print(f"   - {prompt_name}: {len(prompt.parameters)} parameters")
    
    # Test integration
    integration = DomainExpertIntegration()
    
    # Create mock handler
    class MockscRNASeqHandler:
        pass
    
    handler = MockscRNASeqHandler()
    domain_prompts = get_domain_prompts_for_handler(handler)
    
    print(f"✅ Domain prompts for scRNA-seq handler: {len(domain_prompts)}")
    
    for name, config in domain_prompts.items():
        print(f"   - {name}: {config.expertise_level} level")
        print(f"     Context: {config.domain_context}")
        print(f"     Parameters: {list(config.parameters.keys())}")
    
    print("🎉 All Domain Integration tests passed!")


if __name__ == "__main__":
    main()