"""
Enhanced Domain Expert Template System - Main Coordinator

Orchestrates template creation, code generation, and expert management with 
enhanced Electron integration, security validation, and scalable operations.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from .template_core import (
    TemplateConfig, PromptTemplate, EnhancedTemplateFactory, 
    COMMON_PROMPT_TEMPLATES
)
from .template_generator import CodeGenerator, BatchGenerator
from .core import BaseDomainExpert, ExpertiseLevel, BiologicalContext
from .security import SecurityValidator, SecurityLevel
from .events import get_event_emitter, emit_system_event, emit_ui_update
from .performance import get_performance_monitor, time_it

logger = logging.getLogger(__name__)


class DomainExpertTemplate:
    """Enhanced template system coordinator with Electron integration"""
    
    def __init__(self):
        self._factory = EnhancedTemplateFactory()
        self._code_generator = CodeGenerator()
        self._events = get_event_emitter()
        self._perf = get_performance_monitor()
    
    @staticmethod
    @time_it("template_create_basic_expert")
    def create_basic_expert(
        technique_name: str,
        display_name: str,
        description: str,
        category: str,
        subcategory: Optional[str] = None,
        aliases: Optional[List[str]] = None,
        expertise_level: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE,
        security_level: SecurityLevel = SecurityLevel.PUBLIC
    ) -> BaseDomainExpert:
        """Create a basic domain expert with enhanced validation and monitoring"""
        
        # Create enhanced template config
        config = TemplateConfig(
            technique_name=technique_name,
            display_name=display_name,
            description=description,
            category=category,
            subcategory=subcategory,
            aliases=aliases or [],
            expertise_level=expertise_level,
            security_level=security_level
        )
        
        # Create basic prompts
        basic_prompts = [
            PromptTemplate(
                name="basic_interpretation",
                description=f"Basic interpretation for {display_name} results",
                template=f"""
Based on the {display_name} analysis results:

- Analysis type: {technique_name}
- Key findings: {{key_findings}}
- Statistical significance: {{significance}}
- Sample information: {{sample_info}}

Please provide an interpretation of these results, including:
1. Biological significance of the findings
2. Potential implications for the research question
3. Suggested follow-up analyses or experiments
4. Any limitations or caveats to consider

Additional context: {{additional_context}}
""",
                parameters=["key_findings", "significance", "sample_info", "additional_context"],
                expertise_level=expertise_level,
                biological_context=BiologicalContext.GENE_EXPRESSION,
                tags={"basic", "interpretation"},
                security_level=security_level
            )
        ]
        
        # Use enhanced factory to create expert
        factory = EnhancedTemplateFactory()
        return factory.create_expert_sync(config, basic_prompts)
    
    @staticmethod
    async def generate_expert_module_code_async(
        technique_name: str,
        display_name: str,
        description: str,
        category: str,
        prompts_config: List[Dict[str, Any]],
        subcategory: Optional[str] = None,
        aliases: Optional[List[str]] = None,
        expertise_level: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE,
        security_level: SecurityLevel = SecurityLevel.PUBLIC,
        **kwargs
    ) -> str:
        """Generate Python code for a domain expert module asynchronously"""
        
        # Create template configuration
        config = TemplateConfig(
            technique_name=technique_name,
            display_name=display_name,
            description=description,
            category=category,
            subcategory=subcategory,
            aliases=aliases or [],
            expertise_level=expertise_level,
            security_level=security_level,
            author=kwargs.get("author"),
            version=kwargs.get("version", "1.0")
        )
        
        # Create prompt templates
        prompts = []
        for prompt_config in prompts_config:
            prompt = PromptTemplate(
                name=prompt_config["name"],
                description=prompt_config["description"],
                template=prompt_config["template"],
                parameters=prompt_config["parameters"],
                biological_context=BiologicalContext(prompt_config.get("biological_context", "GENE_EXPRESSION")),
                expertise_level=ExpertiseLevel(prompt_config.get("expertise_level", expertise_level.name)),
                tags=set(prompt_config.get("tags", [])),
                security_level=SecurityLevel(prompt_config.get("security_level", security_level.name))
            )
            prompts.append(prompt)
        
        # Generate code
        generator = CodeGenerator()
        return await generator.generate_expert_module_async(config, prompts)
    
    @staticmethod
    def generate_expert_module_code(
        technique_name: str,
        display_name: str,
        description: str,
        category: str,
        prompts_config: List[Dict[str, Any]],
        **kwargs
    ) -> str:
        """Synchronous wrapper for code generation"""
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                DomainExpertTemplate.generate_expert_module_code_async(
                    technique_name, display_name, description, category, 
                    prompts_config, **kwargs
                )
            )
        except RuntimeError:
            return asyncio.run(
                DomainExpertTemplate.generate_expert_module_code_async(
                    technique_name, display_name, description, category, 
                    prompts_config, **kwargs
                )
            )
    
    @staticmethod
    async def create_expert_from_config_async(config_path: Path) -> str:
        """Create a domain expert from a JSON configuration file asynchronously"""
        validated_path = SecurityValidator.validate_file_path(config_path, "read")
        
        def load_config():
            with open(validated_path) as f:
                return json.load(f)
        
        config = await asyncio.get_event_loop().run_in_executor(None, load_config)
        
        return await DomainExpertTemplate.generate_expert_module_code_async(
            technique_name=config["technique_name"],
            display_name=config["display_name"],
            description=config["description"],
            category=config["category"],
            prompts_config=config["prompts"],
            subcategory=config.get("subcategory"),
            aliases=config.get("aliases", []),
            expertise_level=ExpertiseLevel(config.get("expertise_level", "INTERMEDIATE")),
            security_level=SecurityLevel(config.get("security_level", "PUBLIC"))
        )
    
    @staticmethod
    def create_expert_from_config(config_path: Path) -> str:
        """Synchronous wrapper for config-based expert creation"""
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                DomainExpertTemplate.create_expert_from_config_async(config_path)
            )
        except RuntimeError:
            return asyncio.run(
                DomainExpertTemplate.create_expert_from_config_async(config_path)
            )
    
    @staticmethod
    async def generate_config_template_async(technique_name: str, output_path: Path) -> Dict[str, Any]:
        """Generate a configuration template for a new technique asynchronously"""
        validated_name = SecurityValidator.validate_identifier(technique_name, "technique_name")
        validated_path = SecurityValidator.validate_file_path(output_path, "write")
        
        template_config = {
            "technique_name": validated_name,
            "display_name": technique_name.replace('_', ' ').title(),
            "description": f"Analysis technique for {technique_name.replace('_', ' ').lower()}",
            "category": "TODO: Add category (e.g., Transcriptomics, Genomics, Proteomics)",
            "subcategory": None,
            "aliases": [],
            "expertise_level": "INTERMEDIATE",
            "security_level": "PUBLIC",
            "author": "Template System",
            "version": "1.0",
            "prompts": [
                {
                    "name": "interpret_results",
                    "description": f"Interpret {technique_name.replace('_', ' ')} analysis results",
                    "template": f"""
Based on the {technique_name.replace('_', ' ')} analysis results:

- Key metric 1: {{metric1}}
- Key metric 2: {{metric2}}
- Statistical significance: {{significance}}

Please provide an interpretation, including:
1. Biological significance of the results
2. Implications for the research question
3. Suggested follow-up analyses
""",
                    "parameters": ["metric1", "metric2", "significance"],
                    "biological_context": "GENE_EXPRESSION",
                    "expertise_level": "INTERMEDIATE",
                    "tags": ["interpretation", "results"],
                    "security_level": "PUBLIC"
                },
                {
                    "name": "troubleshoot_analysis",
                    "description": f"Help troubleshoot {technique_name.replace('_', ' ')} analysis issues",
                    "template": f"""
{technique_name.replace('_', ' ')} analysis troubleshooting:

- Problem description: {{problem_description}}
- Error message: {{error_message}}
- Analysis parameters: {{parameters}}

Please provide troubleshooting guidance:
1. Likely causes of the issue
2. Solutions to try
3. Parameter adjustments
""",
                    "parameters": ["problem_description", "error_message", "parameters"],
                    "biological_context": "TROUBLESHOOTING",
                    "expertise_level": "EXPERT",
                    "tags": ["troubleshooting", "debugging"],
                    "security_level": "PUBLIC"
                }
            ]
        }
        
        def write_config():
            with open(validated_path, 'w') as f:
                json.dump(template_config, f, indent=2)
        
        await asyncio.get_event_loop().run_in_executor(None, write_config)
        
        return template_config
    
    @staticmethod
    def generate_config_template(technique_name: str, output_path: Path) -> Dict[str, Any]:
        """Synchronous wrapper for config template generation"""
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                DomainExpertTemplate.generate_config_template_async(technique_name, output_path)
            )
        except RuntimeError:
            return asyncio.run(
                DomainExpertTemplate.generate_config_template_async(technique_name, output_path)
            )


class TechniqueGenerator:
    """Enhanced generator for creating multiple techniques with Electron integration"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = SecurityValidator.validate_file_path(output_dir, "write")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._batch_generator = BatchGenerator(self.output_dir)
        self._events = get_event_emitter()
        self._perf = get_performance_monitor()
    
    @time_it("technique_generate_from_list")
    async def generate_from_list_async(self, techniques: List[Dict[str, Any]], 
                                     max_concurrent: int = 3) -> List[Path]:
        """Generate multiple domain experts from a list of technique configurations"""
        
        # Emit generation start event for UI
        self._events.emit("technique_batch_started", {
            "technique_count": len(techniques),
            "output_dir": str(self.output_dir),
            "max_concurrent": max_concurrent
        })
        
        # Use batch generator for concurrent processing
        generated_files = await self._batch_generator.generate_batch_async(
            techniques, max_concurrent
        )
        
        # Emit completion event
        self._events.emit("technique_batch_completed", {
            "generated_count": len(generated_files),
            "generated_files": [str(f) for f in generated_files]
        })
        
        return generated_files
    
    def generate_from_list(self, techniques: List[Dict[str, Any]]) -> List[Path]:
        """Synchronous wrapper for batch generation"""
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.generate_from_list_async(techniques))
        except RuntimeError:
            return asyncio.run(self.generate_from_list_async(techniques))
    
    async def generate_batch_configs_async(self, technique_names: List[str]) -> List[Path]:
        """Generate configuration templates for multiple techniques"""
        configs_dir = self.output_dir / "configs"
        configs_dir.mkdir(exist_ok=True)
        generated_configs = []
        
        for technique_name in technique_names:
            config_filename = f"{technique_name.lower().replace(' ', '_')}_config.json"
            config_path = configs_dir / config_filename
            
            await DomainExpertTemplate.generate_config_template_async(technique_name, config_path)
            generated_configs.append(config_path)
        
        return generated_configs
    
    def generate_batch_configs(self, technique_names: List[str]) -> List[Path]:
        """Synchronous wrapper for batch config generation"""
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.generate_batch_configs_async(technique_names))
        except RuntimeError:
            return asyncio.run(self.generate_batch_configs_async(technique_names))


# Common technique templates for quick generation
COMMON_TECHNIQUES = [
    {
        "technique_name": "chip_seq",
        "display_name": "ChIP-seq",
        "description": "Chromatin immunoprecipitation followed by sequencing",
        "category": "Epigenomics",
        "aliases": ["chip-seq", "chromatin-ip"],
        "expertise_level": "EXPERT",
        "prompts": [
            {
                "name": "interpret_peaks",
                "description": "Interpret ChIP-seq peak calling results",
                "template": """
ChIP-seq peak analysis results:

- Total peaks identified: {total_peaks}
- Peak distribution: {peak_distribution}
- Top enriched regions: {top_regions}
- Motif analysis: {motif_results}

Please interpret these ChIP-seq results, including:
1. Quality of the ChIP-seq experiment
2. Biological significance of peak locations
3. Potential target genes and regulatory networks
4. Validation experiments to consider
""",
                "parameters": ["total_peaks", "peak_distribution", "top_regions", "motif_results"],
                "biological_context": "CHROMATIN_ACCESSIBILITY",
                "expertise_level": "EXPERT",
                "tags": ["peaks", "chromatin", "transcription-factors"]
            }
        ]
    },
    {
        "technique_name": "proteomics",
        "display_name": "Proteomics",
        "description": "Large-scale study of proteins and their modifications",
        "category": "Proteomics",
        "aliases": ["mass-spec", "protein-analysis"],
        "expertise_level": "EXPERT",
        "prompts": [
            {
                "name": "interpret_protein_changes",
                "description": "Interpret differential protein expression results",
                "template": """
Proteomics analysis results:

- Proteins identified: {proteins_identified}
- Significantly changed proteins: {changed_proteins}
- Top upregulated: {top_upregulated}
- Top downregulated: {top_downregulated}
- Pathway analysis: {pathway_results}

Please interpret these proteomics results, including:
1. Biological significance of protein changes
2. Correlation with transcriptomic data if available
3. Potential biomarkers identified
4. Functional implications of the findings
""",
                "parameters": ["proteins_identified", "changed_proteins", "top_upregulated", 
                              "top_downregulated", "pathway_results"],
                "biological_context": "PROTEIN_ANALYSIS",
                "expertise_level": "EXPERT",
                "tags": ["proteins", "differential-expression", "biomarkers"]
            }
        ]
    }
]


if __name__ == "__main__":
    # Enhanced template system testing
    async def test_enhanced_template_system():
        print("Testing Enhanced Domain Expert Template System")
        
        # Test basic expert creation
        basic_expert = DomainExpertTemplate.create_basic_expert(
            technique_name="enhanced_test_technique",
            display_name="Enhanced Test Technique",
            description="An enhanced test technique with security and monitoring",
            category="Testing",
            security_level=SecurityLevel.PUBLIC
        )
        
        print(f"✓ Enhanced basic expert: {basic_expert.get_technique_name()}")
        print(f"✓ Prompts: {list(basic_expert.get_prompts().keys())}")
        
        # Test async code generation
        chipseq_config = COMMON_TECHNIQUES[0]
        chipseq_code = await DomainExpertTemplate.generate_expert_module_code_async(
            **chipseq_config
        )
        
        print(f"✓ Generated ChIP-seq module code ({len(chipseq_code)} characters)")
        
        # Test config template generation
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            config = await DomainExpertTemplate.generate_config_template_async(
                "Enhanced Test Technique", config_path
            )
            print(f"✓ Generated config template: {config_path}")
        
        print("\n✅ Enhanced template system test completed successfully!")
    
    # Run test
    try:
        asyncio.run(test_enhanced_template_system())
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 