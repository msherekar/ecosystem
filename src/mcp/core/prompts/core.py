"""
Core domain prompt system components.

This module provides the foundational classes and interfaces 
for the scalable domain prompt system.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path


class ExpertiseLevel(Enum):
    """Standardized expertise levels"""
    BASIC = "basic"
    INTERMEDIATE = "intermediate" 
    EXPERT = "expert"
    SPECIALIST = "specialist"


class BiologicalContext(Enum):
    """Standardized biological contexts"""
    CELL_TYPE_IDENTIFICATION = "cell_type_identification"
    QUALITY_CONTROL = "quality_control"
    DIMENSIONALITY_REDUCTION = "dimensionality_reduction"
    GENE_EXPRESSION = "gene_expression"
    TRAJECTORY_ANALYSIS = "trajectory_analysis"
    VISUALIZATION = "visualization"
    TROUBLESHOOTING = "troubleshooting"
    COMPARATIVE_ANALYSIS = "comparative_analysis"
    PATHWAY_ANALYSIS = "pathway_analysis"
    DIFFERENTIAL_EXPRESSION = "differential_expression"
    CHROMATIN_ACCESSIBILITY = "chromatin_accessibility"
    PROTEIN_ANALYSIS = "protein_analysis"
    METABOLIC_ANALYSIS = "metabolic_analysis"
    GENOMIC_VARIANTS = "genomic_variants"
    EPIGENETIC_MODIFICATIONS = "epigenetic_modifications"


@dataclass
class DomainPrompt:
    """Domain-specific prompt template with validation"""
    name: str
    description: str
    template: str
    parameters: List[str]
    expertise_level: ExpertiseLevel
    biological_context: BiologicalContext
    tags: Set[str] = field(default_factory=set)
    version: str = "1.0"
    author: Optional[str] = None
    references: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate prompt after initialization"""
        self._validate()
    
    def _validate(self):
        """Validate prompt template and parameters"""
        if not self.name or not self.template:
            raise ValueError("Name and template are required")
        
        # Check that all parameters in template are declared
        import re
        template_params = set(re.findall(r'\{(\w+)\}', self.template))
        declared_params = set(self.parameters)
        
        if template_params != declared_params:
            missing = template_params - declared_params
            extra = declared_params - template_params
            raise ValueError(
                f"Parameter mismatch in prompt '{self.name}': "
                f"Missing: {missing}, Extra: {extra}"
            )
    
    def format(self, **kwargs) -> str:
        """Format the prompt template with provided parameters"""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing parameter for prompt '{self.name}': {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "description": self.description,
            "template": self.template,
            "parameters": self.parameters,
            "expertise_level": self.expertise_level.value,
            "biological_context": self.biological_context.value,
            "tags": list(self.tags),
            "version": self.version,
            "author": self.author,
            "references": self.references
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DomainPrompt':
        """Create from dictionary"""
        return cls(
            name=data["name"],
            description=data["description"],
            template=data["template"],
            parameters=data["parameters"],
            expertise_level=ExpertiseLevel(data["expertise_level"]),
            biological_context=BiologicalContext(data["biological_context"]),
            tags=set(data.get("tags", [])),
            version=data.get("version", "1.0"),
            author=data.get("author"),
            references=data.get("references", [])
        )


@dataclass
class TechniqueMetadata:
    """Metadata for a biological technique"""
    name: str
    display_name: str
    description: str
    category: str
    subcategory: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    related_techniques: List[str] = field(default_factory=list)
    typical_applications: List[str] = field(default_factory=list)
    required_expertise: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE
    version: str = "1.0"
    author: Optional[str] = None
    
    def matches_query(self, query: str) -> bool:
        """Check if this technique matches a query string"""
        query_lower = query.lower()
        search_terms = [
            self.name.lower(),
            self.display_name.lower(),
            self.description.lower(),
            self.category.lower()
        ]
        search_terms.extend([alias.lower() for alias in self.aliases])
        search_terms.extend([app.lower() for app in self.typical_applications])
        
        return any(query_lower in term for term in search_terms)


class DomainExpert(ABC):
    """Abstract base class for domain experts"""
    
    def __init__(self):
        self._metadata = None
        self._prompts_cache = None
    
    @abstractmethod
    def get_metadata(self) -> TechniqueMetadata:
        """Get technique metadata"""
        pass
    
    @abstractmethod
    def get_prompts(self) -> Dict[str, DomainPrompt]:
        """Get all domain prompts for this technique"""
        pass
    
    def get_prompt_by_name(self, name: str) -> Optional[DomainPrompt]:
        """Get a specific prompt by name"""
        prompts = self.get_prompts()
        return prompts.get(name)
    
    def get_prompts_by_context(self, context: BiologicalContext) -> Dict[str, DomainPrompt]:
        """Get prompts filtered by biological context"""
        prompts = self.get_prompts()
        return {
            name: prompt for name, prompt in prompts.items()
            if prompt.biological_context == context
        }
    
    def get_prompts_by_expertise(self, level: ExpertiseLevel) -> Dict[str, DomainPrompt]:
        """Get prompts filtered by expertise level"""
        prompts = self.get_prompts()
        return {
            name: prompt for name, prompt in prompts.items()
            if prompt.expertise_level == level
        }
    
    def get_prompts_by_tags(self, tags: Set[str]) -> Dict[str, DomainPrompt]:
        """Get prompts that match any of the given tags"""
        prompts = self.get_prompts()
        return {
            name: prompt for name, prompt in prompts.items()
            if prompt.tags.intersection(tags)
        }
    
    def validate_prompts(self) -> List[str]:
        """Validate all prompts and return list of errors"""
        errors = []
        try:
            prompts = self.get_prompts()
            for name, prompt in prompts.items():
                try:
                    prompt._validate()
                except ValueError as e:
                    errors.append(f"Prompt '{name}': {e}")
        except Exception as e:
            errors.append(f"Failed to get prompts: {e}")
        return errors
    
    def get_technique_name(self) -> str:
        """Get the technique name (for backward compatibility)"""
        return self.get_metadata().name
    
    def export_prompts(self, filepath: Path, format: str = "json"):
        """Export prompts to file"""
        prompts = self.get_prompts()
        data = {
            "metadata": self.get_metadata().__dict__,
            "prompts": {name: prompt.to_dict() for name, prompt in prompts.items()}
        }
        
        if format.lower() == "json":
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")


class BaseDomainExpert(DomainExpert):
    """Base implementation with common functionality"""
    
    def __init__(self, metadata: TechniqueMetadata):
        super().__init__()
        self._metadata = metadata
        self._prompts = {}
    
    def get_metadata(self) -> TechniqueMetadata:
        return self._metadata
    
    def add_prompt(self, prompt: DomainPrompt):
        """Add a prompt to this expert"""
        self._prompts[prompt.name] = prompt
    
    def get_prompts(self) -> Dict[str, DomainPrompt]:
        return self._prompts.copy()


if __name__ == "__main__":
    # Example usage and testing
    print("Testing Core Domain Prompt System")
    
    # Test DomainPrompt
    prompt = DomainPrompt(
        name="test_prompt",
        description="A test prompt",
        template="Hello {name}, your score is {score}",
        parameters=["name", "score"],
        expertise_level=ExpertiseLevel.BASIC,
        biological_context=BiologicalContext.QUALITY_CONTROL
    )
    
    print(f"Prompt created: {prompt.name}")
    print(f"Formatted: {prompt.format(name='Alice', score=95)}")
    
    # Test TechniqueMetadata
    metadata = TechniqueMetadata(
        name="test_technique",
        display_name="Test Technique",
        description="A test technique for demonstration",
        category="Testing"
    )
    
    print(f"Metadata created: {metadata.display_name}")
    print(f"Matches 'test': {metadata.matches_query('test')}")
    
    # Test BaseDomainExpert
    expert = BaseDomainExpert(metadata)
    expert.add_prompt(prompt)
    
    print(f"Expert created for: {expert.get_technique_name()}")
    print(f"Prompts: {list(expert.get_prompts().keys())}")
    
    # Validation
    errors = expert.validate_prompts()
    print(f"Validation errors: {errors}") 