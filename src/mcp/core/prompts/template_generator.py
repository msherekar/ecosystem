"""
Template Code Generator for Domain Prompts System

Provides code generation, file operations, and batch processing for creating
domain expert modules with enhanced security and Electron integration.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from .template_core import TemplateConfig, PromptTemplate, EnhancedTemplateFactory
from .core import ExpertiseLevel, BiologicalContext
from .security import SecurityValidator, SecurityLevel
from .events import get_event_emitter, emit_system_event, emit_ui_update, emit_error
from .performance import get_performance_monitor, time_it

logger = logging.getLogger(__name__)


class CodeGenerator:
    """Enhanced code generator for domain expert modules"""
    
    def __init__(self):
        self._events = get_event_emitter()
        self._perf = get_performance_monitor()
    
    @time_it("template_generate_code")
    async def generate_expert_module_async(self, config: TemplateConfig, 
                                         prompts: List[PromptTemplate],
                                         output_path: Optional[Path] = None) -> str:
        """Generate Python module code for domain expert asynchronously"""
        
        # Emit generation start event
        self._events.emit("code_generation_started", {
            "technique_name": config.technique_name,
            "display_name": config.display_name,
            "prompt_count": len(prompts)
        })
        
        try:
            # Generate code sections
            imports_section = self._generate_imports(config)
            class_section = await self._generate_class_async(config, prompts)
            registration_section = self._generate_registration(config)
            main_section = self._generate_main_section(config)
            
            # Combine all sections
            full_code = "\n".join([
                imports_section,
                class_section,
                registration_section,
                main_section
            ])
            
            # Validate generated code
            await self._validate_generated_code_async(full_code, config.technique_name)
            
            # Write to file if path provided
            if output_path:
                validated_path = SecurityValidator.validate_file_path(output_path, "write")
                await self._write_code_to_file_async(full_code, validated_path)
            
            # Emit success event
            self._events.emit("code_generation_completed", {
                "technique_name": config.technique_name,
                "code_length": len(full_code),
                "output_path": str(output_path) if output_path else None
            })
            
            return full_code
            
        except Exception as e:
            error_msg = f"Code generation failed for {config.technique_name}: {e}"
            self._events.emit("code_generation_failed", {
                "technique_name": config.technique_name,
                "error": str(e)
            })
            raise ValueError(error_msg)
    
    def _generate_imports(self, config: TemplateConfig) -> str:
        """Generate imports section"""
        return f'''"""
{config.display_name} Domain Expert

This module provides domain expertise for {config.description}.
Generated automatically by the Enhanced Template System.
"""

from typing import Dict
from ..core import (
    DomainExpert, DomainPrompt, TechniqueMetadata, 
    ExpertiseLevel, BiologicalContext
)
from ..registry import register_expert


'''
    
    async def _generate_class_async(self, config: TemplateConfig, 
                                   prompts: List[PromptTemplate]) -> str:
        """Generate the main expert class asynchronously"""
        class_name = self._generate_class_name(config.technique_name)
        
        # Generate metadata method
        metadata_method = await self._generate_metadata_method_async(config)
        
        # Generate prompts method
        prompts_method = await self._generate_prompts_method_async(prompts)
        
        return f'''class {class_name}(DomainExpert):
    """Domain expert for {config.display_name} analysis"""
    
{metadata_method}
    
{prompts_method}


'''
    
    async def _generate_metadata_method_async(self, config: TemplateConfig) -> str:
        """Generate get_metadata method"""
        # Generate typical applications
        applications = [
            f"Analysis of {config.display_name.lower()} data",
            f"Interpretation of {config.display_name.lower()} results",
            f"Quality control for {config.display_name.lower()} experiments"
        ]
        
        return f'''    def get_metadata(self) -> TechniqueMetadata:
        return TechniqueMetadata(
            name="{config.technique_name}",
            display_name="{config.display_name}",
            description="{config.description}",
            category="{config.category}",
            subcategory={f'"{config.subcategory}"' if config.subcategory else 'None'},
            aliases={config.aliases},
            related_techniques=[],  # TODO: Add related techniques
            typical_applications={applications},
            required_expertise=ExpertiseLevel.{config.expertise_level.name},
            version="{config.version}",
            author="{config.author or 'Enhanced Template System'}",
            security_level=SecurityLevel.{config.security_level.name}
        )'''
    
    async def _generate_prompts_method_async(self, prompts: List[PromptTemplate]) -> str:
        """Generate get_prompts method"""
        prompts_code = "    def get_prompts(self) -> Dict[str, DomainPrompt]:\n"
        prompts_code += "        \"\"\"Get all domain prompts for this technique\"\"\"\n"
        prompts_code += "        return {\n"
        
        for i, prompt in enumerate(prompts):
            prompt_code = f'''            "{prompt.name}": DomainPrompt(
                name="{prompt.name}",
                description="{prompt.description}",
                template="""{prompt.template}""",
                parameters={prompt.parameters},
                expertise_level=ExpertiseLevel.{prompt.expertise_level.name},
                biological_context=BiologicalContext.{prompt.biological_context.name},
                tags={{{', '.join(f'"{tag}"' for tag in prompt.tags)}}},
                security_level=SecurityLevel.{prompt.security_level.name}
            )'''
            
            if i < len(prompts) - 1:
                prompt_code += ","
            
            prompts_code += prompt_code + "\n"
        
        prompts_code += "        }"
        return prompts_code
    
    def _generate_registration(self, config: TemplateConfig) -> str:
        """Generate auto-registration code"""
        class_name = self._generate_class_name(config.technique_name)
        
        return f'''# Auto-register this expert when module is imported
register_expert({class_name})


'''
    
    def _generate_main_section(self, config: TemplateConfig) -> str:
        """Generate main section for testing"""
        class_name = self._generate_class_name(config.technique_name)
        
        return f'''if __name__ == "__main__":
    # Test the {config.display_name} expert
    print("Testing {config.display_name} Domain Expert")
    
    expert = {class_name}()
    metadata = expert.get_metadata()
    
    print(f"Expert: {{metadata.display_name}}")
    print(f"Category: {{metadata.category}}")
    print(f"Security Level: {{metadata.security_level.value}}")
    
    prompts = expert.get_prompts()
    print(f"Total prompts: {{len(prompts)}}")
    
    for name, prompt in prompts.items():
        print(f"  - {{name}}: {{prompt.description}}")
    
    # Validation
    errors = expert.validate_prompts()
    print(f"\\nValidation errors: {{len(errors)}}")
    if errors:
        for error in errors:
            print(f"  - {{error}}")
    else:
        print("✓ All prompts validated successfully")
'''
    
    def _generate_class_name(self, technique_name: str) -> str:
        """Generate appropriate class name from technique name"""
        # Convert to PascalCase and ensure it's a valid identifier
        clean_name = technique_name.replace('_', ' ').replace('-', ' ')
        words = [word.capitalize() for word in clean_name.split()]
        class_name = ''.join(words) + 'DomainExpert'
        
        # Validate as identifier
        return SecurityValidator.validate_identifier(class_name, "class_name")
    
    async def _validate_generated_code_async(self, code: str, technique_name: str):
        """Validate generated code for syntax and security"""
        # Basic syntax validation
        try:
            compile(code, f"<{technique_name}_generated>", "exec")
        except SyntaxError as e:
            raise ValueError(f"Generated code has syntax error: {e}")
        
        # Security validation
        dangerous_patterns = [
            'eval(', 'exec(', 'import os', 'import sys', 
            '__import__', 'getattr', 'setattr'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in code:
                raise ValueError(f"Generated code contains dangerous pattern: {pattern}")
    
    async def _write_code_to_file_async(self, code: str, file_path: Path):
        """Write generated code to file asynchronously"""
        def write_file():
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(code)
        
        await asyncio.get_event_loop().run_in_executor(None, write_file)
        logger.info(f"Generated code written to {file_path}")


class BatchGenerator:
    """Batch processing for multiple template generations"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = SecurityValidator.validate_file_path(output_dir, "write")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self._code_generator = CodeGenerator()
        self._template_factory = EnhancedTemplateFactory()
        self._events = get_event_emitter()
        self._perf = get_performance_monitor()
    
    @time_it("template_batch_generate")
    async def generate_batch_async(self, technique_configs: List[Dict[str, Any]], 
                                  max_concurrent: int = 3) -> List[Path]:
        """Generate multiple techniques concurrently"""
        # Emit batch start event
        self._events.emit("batch_generation_started", {
            "technique_count": len(technique_configs),
            "output_dir": str(self.output_dir),
            "max_concurrent": max_concurrent
        })
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def generate_single(config_dict: Dict[str, Any]) -> Path:
            async with semaphore:
                return await self._generate_single_technique_async(config_dict)
        
        try:
            # Process all techniques concurrently
            tasks = [generate_single(config) for config in technique_configs]
            generated_paths = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Separate successful paths from exceptions
            successful_paths = []
            failed_configs = []
            
            for i, result in enumerate(generated_paths):
                if isinstance(result, Exception):
                    failed_configs.append((technique_configs[i], str(result)))
                else:
                    successful_paths.append(result)
            
            # Emit completion event
            self._events.emit("batch_generation_completed", {
                "successful_count": len(successful_paths),
                "failed_count": len(failed_configs),
                "generated_files": [str(p) for p in successful_paths]
            })
            
            if failed_configs:
                emit_error("batch_generation_partial_failure", 
                          f"{len(failed_configs)} techniques failed", {
                              "failed_configs": failed_configs
                          })
            
            return successful_paths
            
        except Exception as e:
            emit_error("batch_generation_failed", str(e), {
                "technique_count": len(technique_configs)
            })
            raise
    
    async def _generate_single_technique_async(self, config_dict: Dict[str, Any]) -> Path:
        """Generate a single technique from configuration"""
        # Create config and prompts
        config = TemplateConfig.from_dict(config_dict)
        
        # Get prompts from config or use defaults
        prompt_configs = config_dict.get("prompts", [])
        if not prompt_configs:
            # Use default prompts
            from .template_core import COMMON_PROMPT_TEMPLATES
            prompts = [COMMON_PROMPT_TEMPLATES["basic_interpretation"]]
        else:
            prompts = [
                PromptTemplate(
                    name=p["name"],
                    description=p["description"],
                    template=p["template"],
                    parameters=p["parameters"],
                    biological_context=BiologicalContext(p.get("biological_context", "GENE_EXPRESSION")),
                    expertise_level=ExpertiseLevel(p.get("expertise_level", "INTERMEDIATE")),
                    tags=set(p.get("tags", [])),
                    security_level=SecurityLevel(p.get("security_level", "PUBLIC"))
                )
                for p in prompt_configs
            ]
        
        # Generate output path
        filename = f"{config.technique_name}.py"
        output_path = self.output_dir / filename
        
        # Generate code
        await self._code_generator.generate_expert_module_async(
            config, prompts, output_path
        )
        
        return output_path


if __name__ == "__main__":
    # Test template generator
    async def test_template_generator():
        print("Testing Template Code Generator")
        
        # Test configuration
        from .template_core import TemplateConfig, COMMON_PROMPT_TEMPLATES
        
        config = TemplateConfig(
            technique_name="test_technique",
            display_name="Test Technique",
            description="A test technique for code generation",
            category="Testing"
        )
        
        prompts = [COMMON_PROMPT_TEMPLATES["basic_interpretation"]]
        
        # Test code generation
        generator = CodeGenerator()
        code = await generator.generate_expert_module_async(config, prompts)
        print(f"✓ Generated code: {len(code)} characters")
        
        print("\n✅ Template generator test completed!")
    
    # Run test
    try:
        asyncio.run(test_template_generator())
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 