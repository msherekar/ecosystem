"""
Demo Scenarios for Domain Prompts System

Individual demo scenarios showcasing system capabilities with enhanced
Electron integration, security validation, and structured output.
"""

import asyncio
from typing import Dict, List, Any

from .demo_core import BaseDemoScenario, DemoResult, DemoConfig, DemoProgressReporter
from .security import SecurityValidator, SecurityLevel
from . import (
    initialize_system, get_system_info, validate_system,
    get_expert, list_techniques, search_techniques,
    get_techniques_by_category, get_prompts_by_context,
    create_new_technique, BiologicalContext, ExpertiseLevel
)

import logging
logger = logging.getLogger(__name__)


class BasicUsageDemoScenario(BaseDemoScenario):
    """Demonstrate basic system usage and functionality"""
    
    def __init__(self):
        super().__init__(
            "basic_usage_demo",
            "Demonstrates basic system initialization and expert usage"
        )
        self.category = "system"
        self.difficulty = "beginner"
        self.duration_estimate = "30 seconds"
    
    def get_estimated_steps(self) -> int:
        return 4
    
    async def execute_async(self, config: DemoConfig) -> DemoResult:
        """Execute basic usage demonstration"""
        progress = DemoProgressReporter(self.name, self.get_estimated_steps(), config)
        result_data = {}
        
        try:
            # Step 1: Initialize system
            progress.update("Initializing system")
            init_result = initialize_system()
            result_data["initialization"] = {
                "total_experts": init_result['total_experts'],
                "categories": init_result['categories']
            }
            
            # Step 2: List techniques
            progress.update("Listing available techniques")
            techniques = list_techniques()
            result_data["techniques"] = {
                "count": len(techniques),
                "names": sorted(techniques)[:5]  # First 5 for brevity
            }
            
            # Step 3: Get specific expert
            progress.update("Loading scRNA-seq expert")
            if "scrnaseq" in techniques:
                expert = get_expert("scrnaseq")
                if expert:
                    metadata = expert.get_metadata()
                    prompts = expert.get_prompts()
                    result_data["scrnaseq_expert"] = {
                        "display_name": metadata.display_name,
                        "description": metadata.description,
                        "prompt_count": len(prompts),
                        "expertise_level": metadata.required_expertise.value
                    }
                else:
                    result_data["scrnaseq_expert"] = {"error": "Could not load expert"}
            else:
                result_data["scrnaseq_expert"] = {"error": "scRNA-seq not available"}
            
            # Step 4: Test prompt formatting
            progress.update("Testing prompt formatting")
            if "scrnaseq" in techniques:
                expert = get_expert("scrnaseq")
                if expert:
                    marker_prompt = expert.get_prompt_by_name("interpret_markers")
                    if marker_prompt:
                        # Sample data with security validation
                        sample_data = SecurityValidator.validate_parameters({
                            "n_clusters": "8",
                            "avg_markers_per_cluster": "25",
                            "top_marker_genes": "CD3D, CD8A, CD4, MS4A1, LYZ",
                            "cluster_with_most_markers": "Cluster_3 (T-cells)",
                            "cluster_with_fewest_markers": "Cluster_7 (Unknown)",
                            "pvalue_threshold": "0.05"
                        })
                        
                        formatted_prompt = marker_prompt.format(**sample_data)
                        result_data["prompt_test"] = {
                            "prompt_name": marker_prompt.name,
                            "output_length": len(formatted_prompt),
                            "success": True
                        }
                    else:
                        result_data["prompt_test"] = {"error": "Marker prompt not found"}
            
            progress.complete(True, f"Basic usage demo completed - {len(techniques)} techniques available")
            
            return DemoResult(
                demo_name=self.name,
                success=True,
                duration=0.0,  # Will be set by safe_execute
                data=result_data,
                metadata={"category": self.category}
            )
            
        except Exception as e:
            progress.complete(False, f"Demo failed: {e}")
            return DemoResult(
                demo_name=self.name,
                success=False,
                duration=0.0,
                errors=[str(e)],
                data=result_data
            )


class SearchAndFilteringDemoScenario(BaseDemoScenario):
    """Demonstrate search and filtering capabilities"""
    
    def __init__(self):
        super().__init__(
            "search_filtering_demo", 
            "Demonstrates search functionality and technique filtering"
        )
        self.category = "search"
        self.difficulty = "intermediate"
        self.duration_estimate = "45 seconds"
    
    def get_estimated_steps(self) -> int:
        return 3
    
    async def execute_async(self, config: DemoConfig) -> DemoResult:
        """Execute search and filtering demonstration"""
        progress = DemoProgressReporter(self.name, self.get_estimated_steps(), config)
        result_data = {}
        
        try:
            # Step 1: Search for RNA techniques
            progress.update("Searching for RNA-related techniques")
            rna_experts = search_techniques("rna")
            result_data["rna_search"] = {
                "query": "rna",
                "results_count": len(rna_experts),
                "techniques": [expert.get_metadata().name for expert in rna_experts]
            }
            
            # Step 2: Filter by category
            progress.update("Filtering by category")
            try:
                transcriptomics_techniques = get_techniques_by_category("Transcriptomics")
                result_data["category_filter"] = {
                    "category": "Transcriptomics",
                    "count": len(transcriptomics_techniques),
                    "techniques": [t for t in transcriptomics_techniques]
                }
            except Exception as e:
                result_data["category_filter"] = {
                    "error": f"Category filtering failed: {e}"
                }
            
            # Step 3: Filter by biological context
            progress.update("Filtering by biological context")
            qc_prompts = get_prompts_by_context(BiologicalContext.QUALITY_CONTROL)
            result_data["context_filter"] = {
                "context": "Quality Control",
                "techniques_with_qc_prompts": len(qc_prompts),
                "total_qc_prompts": sum(len(prompts) for prompts in qc_prompts.values())
            }
            
            progress.complete(True, f"Search demo completed - found {len(rna_experts)} RNA techniques")
            
            return DemoResult(
                demo_name=self.name,
                success=True,
                duration=0.0,
                data=result_data,
                metadata={"category": self.category}
            )
            
        except Exception as e:
            progress.complete(False, f"Search demo failed: {e}")
            return DemoResult(
                demo_name=self.name,
                success=False,
                duration=0.0,
                errors=[str(e)],
                data=result_data
            )


class SystemManagementDemoScenario(BaseDemoScenario):
    """Demonstrate system management features"""
    
    def __init__(self):
        super().__init__(
            "system_management_demo",
            "Demonstrates system info, validation, and health monitoring"
        )
        self.category = "management"
        self.difficulty = "advanced"
        self.duration_estimate = "20 seconds"
    
    def get_estimated_steps(self) -> int:
        return 2
    
    async def execute_async(self, config: DemoConfig) -> DemoResult:
        """Execute system management demonstration"""
        progress = DemoProgressReporter(self.name, self.get_estimated_steps(), config)
        result_data = {}
        
        try:
            # Step 1: System information
            progress.update("Gathering system information")
            info = get_system_info()
            result_data["system_info"] = {
                "version": info['version'],
                "total_experts": len(info['available_techniques']),
                "categories": list(info['registry_stats']['categories'].keys()),
                "features": list(info['features'].keys())
            }
            
            # Step 2: System validation
            progress.update("Running system validation")
            validation = validate_system()
            result_data["validation"] = {
                "total_experts": validation['total_experts'],
                "experts_with_errors": validation['experts_with_errors'],
                "system_healthy": validation['system_healthy'],
                "validation_passed": validation['experts_with_errors'] == 0
            }
            
            progress.complete(True, f"System management demo completed - {info['version']}")
            
            return DemoResult(
                demo_name=self.name,
                success=True,
                duration=0.0,
                data=result_data,
                metadata={"category": self.category}
            )
            
        except Exception as e:
            progress.complete(False, f"System management demo failed: {e}")
            return DemoResult(
                demo_name=self.name,
                success=False,
                duration=0.0,
                errors=[str(e)],
                data=result_data
            )


if __name__ == "__main__":
    # Test demo scenarios
    async def test_scenarios():
        print("Testing Demo Scenarios")
        
        # Import demo config
        from .demo_core import DemoConfig
        
        config = DemoConfig(
            enable_events=False,  # Disable events for testing
            output_format="text"
        )
        
        # Test basic usage scenario
        basic_demo = BasicUsageDemoScenario()
        basic_result = await basic_demo.safe_execute(config)
        print(f"✓ Basic demo: {basic_result.success}")
        
        # Test search scenario
        search_demo = SearchAndFilteringDemoScenario()
        search_result = await search_demo.safe_execute(config)
        print(f"✓ Search demo: {search_result.success}")
        
        # Test metadata
        metadata = basic_demo.get_metadata()
        print(f"✓ Demo metadata: {metadata['name']} ({metadata['difficulty']})")
        
        print("\n✅ Demo scenarios test completed!")
    
    # Run test
    try:
        asyncio.run(test_scenarios())
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 