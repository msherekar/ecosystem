"""
Template Core Infrastructure for Domain Prompts System

Provides core template classes, validation, and infrastructure for creating
new domain experts with enhanced security and scalability.
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import logging

from .core import (
    DomainExpert, DomainPrompt, TechniqueMetadata, 
    ExpertiseLevel, BiologicalContext, BaseDomainExpert
)
from .security import SecurityValidator, SecurityLevel
from .events import get_event_emitter, emit_system_event, emit_ui_update
from .performance import get_performance_monitor, time_it

logger = logging.getLogger(__name__)


@dataclass
class TemplateConfig:
    """Enhanced configuration for template generation"""
    technique_name: str
    display_name: str
    description: str
    category: str
    subcategory: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    expertise_level: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE
    security_level: SecurityLevel = SecurityLevel.PUBLIC
    author: Optional[str] = None
    version: str = "1.0"
    tags: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        """Validate configuration on creation"""
        self.technique_name = SecurityValidator.validate_identifier(
            self.technique_name, "technique_name"
        )
        self.display_name = SecurityValidator.validate_string(
            self.display_name, 200, "display_name"
        )
        self.description = SecurityValidator.validate_string(
            self.description, 2000, "description"
        )
        self.category = SecurityValidator.validate_string(
            self.category, 100, "category"
        )
        
        # Validate aliases
        validated_aliases = []
        for alias in self.aliases:
            validated_aliases.append(
                SecurityValidator.validate_identifier(alias, "alias")
            )
        self.aliases = validated_aliases
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "technique_name": self.technique_name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "subcategory": self.subcategory,
            "aliases": self.aliases,
            "expertise_level": self.expertise_level.value,
            "security_level": self.security_level.value,
            "author": self.author,
            "version": self.version,
            "tags": list(self.tags)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TemplateConfig':
        """Create from dictionary with validation"""
        return cls(
            technique_name=data["technique_name"],
            display_name=data["display_name"],
            description=data["description"],
            category=data["category"],
            subcategory=data.get("subcategory"),
            aliases=data.get("aliases", []),
            expertise_level=ExpertiseLevel(data.get("expertise_level", "INTERMEDIATE")),
            security_level=SecurityLevel(data.get("security_level", "PUBLIC")),
            author=data.get("author"),
            version=data.get("version", "1.0"),
            tags=set(data.get("tags", []))
        )


@dataclass
class PromptTemplate:
    """Template for individual prompts with enhanced validation"""
    name: str
    description: str
    template: str
    parameters: List[str]
    biological_context: BiologicalContext = BiologicalContext.GENE_EXPRESSION
    expertise_level: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE
    tags: Set[str] = field(default_factory=set)
    security_level: SecurityLevel = SecurityLevel.PUBLIC
    
    def __post_init__(self):
        """Validate prompt template on creation"""
        self.name = SecurityValidator.validate_identifier(self.name, "prompt_name")
        self.description = SecurityValidator.validate_string(
            self.description, 500, "prompt_description"
        )
        self.template = SecurityValidator.validate_template(self.template)
        
        # Validate parameters
        validated_params = []
        for param in self.parameters:
            validated_params.append(
                SecurityValidator.validate_identifier(param, "parameter")
            )
        self.parameters = validated_params
        
        # Check template parameter consistency
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "template": self.template,
            "parameters": self.parameters,
            "biological_context": self.biological_context.value,
            "expertise_level": self.expertise_level.value,
            "tags": list(self.tags),
            "security_level": self.security_level.value
        }
    
    def create_domain_prompt(self) -> DomainPrompt:
        """Create a DomainPrompt instance from this template"""
        return DomainPrompt(
            name=self.name,
            description=self.description,
            template=self.template,
            parameters=self.parameters,
            expertise_level=self.expertise_level,
            biological_context=self.biological_context,
            tags=self.tags.copy(),
            security_level=self.security_level
        )


class EnhancedTemplateFactory:
    """Enhanced factory for creating domain experts from templates"""
    
    def __init__(self):
        self._events = get_event_emitter()
        self._perf = get_performance_monitor()
        self._template_cache: Dict[str, TemplateConfig] = {}
        self._validation_cache: Dict[str, bool] = {}
    
    @time_it("template_create_expert")
    async def create_expert_async(self, config: TemplateConfig, 
                                 prompts: List[PromptTemplate]) -> BaseDomainExpert:
        """Create domain expert asynchronously with validation"""
        # Emit creation start event
        self._events.emit("template_creation_started", {
            "technique_name": config.technique_name,
            "display_name": config.display_name,
            "prompt_count": len(prompts)
        })
        
        try:
            # Create metadata
            metadata = await self._create_metadata_async(config)
            
            # Create expert instance
            expert = BaseDomainExpert(metadata)
            
            # Add prompts
            for prompt_template in prompts:
                domain_prompt = prompt_template.create_domain_prompt()
                expert.add_prompt(domain_prompt)
            
            # Validate the created expert
            validation_errors = await asyncio.get_event_loop().run_in_executor(
                None, expert.validate_prompts
            )
            
            if validation_errors:
                raise ValueError(f"Expert validation failed: {validation_errors}")
            
            # Cache the template config
            self._template_cache[config.technique_name] = config
            
            # Emit success event
            self._events.emit("template_creation_completed", {
                "technique_name": config.technique_name,
                "success": True,
                "prompt_count": len(prompts)
            })
            
            logger.info(f"Created expert template: {config.technique_name}")
            return expert
            
        except Exception as e:
            # Emit error event
            self._events.emit("template_creation_failed", {
                "technique_name": config.technique_name,
                "error": str(e)
            })
            raise
    
    async def _create_metadata_async(self, config: TemplateConfig) -> TechniqueMetadata:
        """Create metadata from template configuration"""
        return TechniqueMetadata(
            name=config.technique_name,
            display_name=config.display_name,
            description=config.description,
            category=config.category,
            subcategory=config.subcategory,
            aliases=config.aliases,
            related_techniques=[],  # Could be enhanced to auto-detect
            typical_applications=[
                f"Analysis of {config.display_name.lower()} data",
                f"Interpretation of {config.display_name.lower()} results"
            ],
            required_expertise=config.expertise_level,
            version=config.version,
            author=config.author,
            security_level=config.security_level
        )
    
    def create_expert_sync(self, config: TemplateConfig, 
                          prompts: List[PromptTemplate]) -> BaseDomainExpert:
        """Synchronous wrapper for expert creation"""
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.create_expert_async(config, prompts))
        except RuntimeError:
            return asyncio.run(self.create_expert_async(config, prompts))
    
    def get_cached_template(self, technique_name: str) -> Optional[TemplateConfig]:
        """Get cached template configuration"""
        return self._template_cache.get(technique_name)
    
    def clear_cache(self):
        """Clear template cache"""
        self._template_cache.clear()
        self._validation_cache.clear()


# Common prompt templates for reuse
COMMON_PROMPT_TEMPLATES = {
    "basic_interpretation": PromptTemplate(
        name="basic_interpretation",
        description="Basic interpretation of analysis results",
        template="""
Based on the {technique_name} analysis results:

- Key findings: {key_findings}
- Statistical significance: {significance}
- Sample information: {sample_info}

Please provide an interpretation of these results, including:
1. Biological significance of the findings
2. Potential implications for the research question
3. Suggested follow-up analyses or experiments
4. Any limitations or caveats to consider

Additional context: {additional_context}
""",
        parameters=["technique_name", "key_findings", "significance", "sample_info", "additional_context"],
        biological_context=BiologicalContext.GENE_EXPRESSION,
        expertise_level=ExpertiseLevel.INTERMEDIATE,
        tags={"interpretation", "basic", "results"}
    ),
    
    "troubleshooting": PromptTemplate(
        name="troubleshooting",
        description="Troubleshoot analysis issues",
        template="""
{technique_name} analysis troubleshooting:

- Problem description: {problem_description}
- Error message: {error_message}
- Analysis parameters: {parameters}
- Data characteristics: {data_info}

Please provide troubleshooting guidance:
1. Likely causes of the issue
2. Step-by-step solutions to try
3. Parameter adjustments to consider
4. When to seek additional help

Context: {context}
""",
        parameters=["technique_name", "problem_description", "error_message", 
                   "parameters", "data_info", "context"],
        biological_context=BiologicalContext.TROUBLESHOOTING,
        expertise_level=ExpertiseLevel.EXPERT,
        tags={"troubleshooting", "debugging", "help"}
    )
}


if __name__ == "__main__":
    # Test template core infrastructure
    async def test_template_core():
        print("Testing Template Core Infrastructure")
        
        # Test template config
        config = TemplateConfig(
            technique_name="test_technique",
            display_name="Test Technique",
            description="A test technique for demonstration",
            category="Testing",
            aliases=["test-tech", "test_method"]
        )
        print(f"✓ Template config: {config.technique_name}")
        
        # Test prompt template
        prompt_template = COMMON_PROMPT_TEMPLATES["basic_interpretation"]
        domain_prompt = prompt_template.create_domain_prompt()
        print(f"✓ Prompt template: {domain_prompt.name}")
        
        # Test enhanced factory
        factory = EnhancedTemplateFactory()
        expert = await factory.create_expert_async(config, [prompt_template])
        print(f"✓ Expert created: {expert.get_technique_name()}")
        
        print("\n✅ Template core infrastructure test completed!")
    
    # Run test
    try:
        asyncio.run(test_template_core())
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 