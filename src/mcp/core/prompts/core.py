"""
Core Domain Prompt System - Essential Components

This module provides the foundational classes and interfaces for the domain prompt system.
Keep this file focused on core data structures only.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
import json


class ExpertiseLevel(Enum):
    """Standardized expertise levels with numeric comparison"""
    BASIC = ("basic", 1)
    INTERMEDIATE = ("intermediate", 2) 
    EXPERT = ("expert", 3)
    SPECIALIST = ("specialist", 4)
    
    def __init__(self, value: str, level: int):
        self._value_ = value
        self.level = level
    
    def __lt__(self, other):
        if isinstance(other, ExpertiseLevel):
            return self.level < other.level
        return NotImplemented
    
    def __le__(self, other):
        if isinstance(other, ExpertiseLevel):
            return self.level <= other.level
        return NotImplemented


class BiologicalContext(Enum):
    """Standardized biological contexts with UI metadata"""
    CELL_TYPE_IDENTIFICATION = ("cell_type_identification", "Cell Type ID", "Identifying and classifying cell types")
    QUALITY_CONTROL = ("quality_control", "Quality Control", "Data quality assessment and filtering")
    DIMENSIONALITY_REDUCTION = ("dimensionality_reduction", "Dim Reduction", "PCA, UMAP, t-SNE analysis")
    GENE_EXPRESSION = ("gene_expression", "Gene Expression", "Expression analysis and interpretation")
    TRAJECTORY_ANALYSIS = ("trajectory_analysis", "Trajectory", "Pseudotime and developmental analysis")
    VISUALIZATION = ("visualization", "Visualization", "Data plotting and visual analysis")
    TROUBLESHOOTING = ("troubleshooting", "Troubleshooting", "Problem solving and debugging")
    COMPARATIVE_ANALYSIS = ("comparative_analysis", "Comparison", "Comparing conditions or groups")
    PATHWAY_ANALYSIS = ("pathway_analysis", "Pathways", "Functional and pathway enrichment")
    DIFFERENTIAL_EXPRESSION = ("differential_expression", "Diff Expression", "DE gene analysis")
    CHROMATIN_ACCESSIBILITY = ("chromatin_accessibility", "Chromatin", "ATAC-seq and accessibility")
    PROTEIN_ANALYSIS = ("protein_analysis", "Proteins", "Proteomic analysis")
    METABOLIC_ANALYSIS = ("metabolic_analysis", "Metabolism", "Metabolomic analysis")
    GENOMIC_VARIANTS = ("genomic_variants", "Variants", "SNP and variant analysis")
    EPIGENETIC_MODIFICATIONS = ("epigenetic_modifications", "Epigenetics", "DNA methylation and modifications")
    
    def __init__(self, value: str, display_name: str, description: str):
        self._value_ = value
        self.display_name = display_name
        self.description = description


class SecurityLevel(Enum):
    """Security levels for prompt access control"""
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"


@dataclass
class DomainPrompt:
    """Core domain-specific prompt template"""
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
    security_level: SecurityLevel = SecurityLevel.PUBLIC
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    usage_count: int = 0
    
    def __post_init__(self):
        """Basic initialization"""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        self._validate_basic()
    
    def _validate_basic(self):
        """Basic validation - enhanced validation in validation.py"""
        if not self.name or not self.template:
            raise ValueError("Name and template are required")
        
        # Basic parameter consistency check
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
        """Basic format - enhanced version in async_support.py"""
        try:
            result = self.template.format(**kwargs)
            self.usage_count += 1
            return result
        except KeyError as e:
            raise ValueError(f"Missing parameter for prompt '{self.name}': {e}")
    
    def to_dict(self, include_internal: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = {
            "name": self.name,
            "description": self.description,
            "template": self.template,
            "parameters": self.parameters,
            "expertise_level": self.expertise_level.value,
            "biological_context": self.biological_context.value,
            "tags": list(self.tags),
            "version": self.version,
            "author": self.author,
            "references": self.references,
            "security_level": self.security_level.value,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_internal:
            data["ui_metadata"] = {
                "expertise_level_numeric": self.expertise_level.level,
                "context_display_name": self.biological_context.display_name,
                "context_description": self.biological_context.description,
                "parameter_count": len(self.parameters),
                "template_length": len(self.template)
            }
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DomainPrompt':
        """Create from dictionary"""
        prompt = cls(
            name=data["name"],
            description=data["description"],
            template=data["template"],
            parameters=data["parameters"],
            expertise_level=ExpertiseLevel(data["expertise_level"]),
            biological_context=BiologicalContext(data["biological_context"]),
            tags=set(data.get("tags", [])),
            version=data.get("version", "1.0"),
            author=data.get("author"),
            references=data.get("references", []),
            security_level=SecurityLevel(data.get("security_level", "public")),
            usage_count=data.get("usage_count", 0)
        )
        
        # Restore timestamps
        if data.get("created_at"):
            prompt.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            prompt.updated_at = datetime.fromisoformat(data["updated_at"])
        
        return prompt


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
    security_level: SecurityLevel = SecurityLevel.PUBLIC
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Basic initialization"""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def matches_query(self, query: str) -> bool:
        """Basic query matching - enhanced version in search.py"""
        if not query:
            return True
        
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "subcategory": self.subcategory,
            "aliases": self.aliases,
            "related_techniques": self.related_techniques,
            "typical_applications": self.typical_applications,
            "required_expertise": self.required_expertise.value,
            "version": self.version,
            "author": self.author,
            "security_level": self.security_level.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class DomainExpert(ABC):
    """Abstract base class for domain experts"""
    
    def __init__(self):
        self._metadata: Optional[TechniqueMetadata] = None
        self._prompts_cache: Optional[Dict[str, DomainPrompt]] = None
    
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
        """Basic validation - enhanced version in validation.py"""
        errors = []
        try:
            prompts = self.get_prompts()
            for name, prompt in prompts.items():
                try:
                    prompt._validate_basic()
                except ValueError as e:
                    errors.append(f"Prompt '{name}': {e}")
        except Exception as e:
            errors.append(f"Failed to get prompts: {e}")
        return errors
    
    def get_technique_name(self) -> str:
        """Get the technique name (for backward compatibility)"""
        return self.get_metadata().name
    
    def export_prompts(self, filepath: Path, format: str = "json"):
        """Basic export - enhanced version in export.py"""
        prompts = self.get_prompts()
        metadata = self.get_metadata()
        
        data = {
            "metadata": metadata.to_dict(),
            "prompts": {name: prompt.to_dict() for name, prompt in prompts.items()},
            "export_metadata": {
                "exported_at": datetime.now().isoformat(),
                "format_version": "2.0",
                "prompt_count": len(prompts)
            }
        }
        
        if format.lower() == "json":
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Unsupported export format: {format}")


class BaseDomainExpert(DomainExpert):
    """Basic implementation with common functionality"""
    
    def __init__(self, metadata: TechniqueMetadata):
        super().__init__()
        self._metadata = metadata
        self._prompts: Dict[str, DomainPrompt] = {}
    
    def get_metadata(self) -> TechniqueMetadata:
        return self._metadata
    
    def add_prompt(self, prompt: DomainPrompt):
        """Add a prompt to this expert"""
        self._prompts[prompt.name] = prompt
    
    def remove_prompt(self, prompt_name: str):
        """Remove a prompt from this expert"""
        if prompt_name in self._prompts:
            del self._prompts[prompt_name]
    
    def get_prompts(self) -> Dict[str, DomainPrompt]:
        return self._prompts.copy()


if __name__ == "__main__":
    # Basic testing
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
    
    print(f"✓ Prompt created: {prompt.name}")
    print(f"✓ Formatted: {prompt.format(name='Alice', score=95)}")
    
    # Test TechniqueMetadata
    metadata = TechniqueMetadata(
        name="test_technique",
        display_name="Test Technique",
        description="A test technique for demonstration",
        category="Testing"
    )
    
    print(f"✓ Metadata created: {metadata.display_name}")
    print(f"✓ Matches 'test': {metadata.matches_query('test')}")
    
    # Test BaseDomainExpert
    expert = BaseDomainExpert(metadata)
    expert.add_prompt(prompt)
    
    print(f"✓ Expert created for: {expert.get_technique_name()}")
    print(f"✓ Prompts: {list(expert.get_prompts().keys())}")
    
    print("\n✅ Core system test completed!") 