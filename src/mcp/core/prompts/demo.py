"""
Domain Prompts System - Demonstration Script

This script demonstrates the capabilities of the new scalable
domain prompts system for biological analysis.
"""

import sys
from pathlib import Path

# Add the parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from prompts import (
    # System functions
    initialize_system, get_system_info, validate_system,
    
    # Core functionality
    get_expert, list_techniques, search_techniques,
    
    # Convenience functions
    get_techniques_by_category, get_prompts_by_context,
    
    # Template system
    create_new_technique,
    
    # Core classes for advanced usage
    BiologicalContext, ExpertiseLevel
)


def demonstrate_basic_usage():
    """Demonstrate basic system usage"""
    print("🧬 Domain Prompts System - Basic Usage Demo")
    print("=" * 50)
    
    # Initialize system
    print("1. Initializing system...")
    init_result = initialize_system()
    print(f"   ✓ Initialized with {init_result['total_experts']} experts")
    print(f"   ✓ Categories: {', '.join(init_result['categories'])}")
    
    # List available techniques
    print("\n2. Available techniques:")
    techniques = list_techniques()
    for technique in sorted(techniques):
        expert = get_expert(technique)
        if expert:
            metadata = expert.get_metadata()
            print(f"   - {technique}: {metadata.display_name} ({metadata.category})")
    
    # Get specific expert
    print("\n3. Working with scRNA-seq expert:")
    scrna_expert = get_expert("scrnaseq")
    if scrna_expert:
        metadata = scrna_expert.get_metadata()
        prompts = scrna_expert.get_prompts()
        
        print(f"   Expert: {metadata.display_name}")
        print(f"   Description: {metadata.description}")
        print(f"   Prompts available: {len(prompts)}")
        print(f"   Expertise level: {metadata.required_expertise.value}")
        
        # Show a specific prompt
        marker_prompt = scrna_expert.get_prompt_by_name("interpret_markers")
        if marker_prompt:
            print(f"\n   Example prompt: {marker_prompt.name}")
            print(f"   Parameters: {marker_prompt.parameters}")
            print(f"   Context: {marker_prompt.biological_context.value}")


def demonstrate_search_and_filtering():
    """Demonstrate search and filtering capabilities"""
    print("\n🔍 Search and Filtering Demo")
    print("=" * 30)
    
    # Search for RNA-related techniques
    print("1. Searching for 'rna' techniques:")
    rna_experts = search_techniques("rna")
    for expert in rna_experts:
        metadata = expert.get_metadata()
        print(f"   - {metadata.name}: {metadata.display_name}")
    
    # Filter by category
    print("\n2. Techniques in 'Transcriptomics' category:")
    transcriptomics_techniques = get_techniques_by_category("Transcriptomics")
    for technique in transcriptomics_techniques:
        print(f"   - {technique}")
    
    # Filter by biological context
    print("\n3. Prompts for 'Quality Control' context:")
    qc_prompts = get_prompts_by_context(BiologicalContext.QUALITY_CONTROL)
    for technique, prompts in qc_prompts.items():
        print(f"   {technique}: {len(prompts)} prompt(s)")
        for prompt in prompts:
            print(f"     - {prompt.name}")


def demonstrate_prompt_usage():
    """Demonstrate how to use prompts with real data"""
    print("\n📝 Prompt Usage Demo")
    print("=" * 20)
    
    # Get scRNA-seq expert
    expert = get_expert("scrnaseq")
    if not expert:
        print("   scRNA-seq expert not available")
        return
    
    # Use marker interpretation prompt
    marker_prompt = expert.get_prompt_by_name("interpret_markers")
    if marker_prompt:
        print("1. Using marker interpretation prompt:")
        
        # Sample data
        sample_data = {
            "n_clusters": 8,
            "avg_markers_per_cluster": 25,
            "top_marker_genes": "CD3D, CD8A, CD4, MS4A1, LYZ",
            "cluster_with_most_markers": "Cluster_3 (T-cells)",
            "cluster_with_fewest_markers": "Cluster_7 (Unknown)",
            "pvalue_threshold": 0.05
        }
        
        try:
            formatted_prompt = marker_prompt.format(**sample_data)
            print("   ✓ Prompt formatted successfully")
            print("   First 200 characters:")
            print(f"   {formatted_prompt[:200]}...")
        except Exception as e:
            print(f"   ✗ Error formatting prompt: {e}")
    
    # Use QC interpretation prompt
    qc_prompt = expert.get_prompt_by_name("qc_interpretation")
    if qc_prompt:
        print("\n2. Using QC interpretation prompt:")
        
        qc_data = {
            "cells_before": 15000,
            "cells_after": 12500,
            "cells_removed": 2500,
            "removal_percentage": 16.7,
            "avg_genes_per_cell": 2500,
            "avg_umi_per_cell": 8500,
            "avg_mito_pct": 8.2,
            "high_mito_cells": 300,
            "doublet_rate": 3.2
        }
        
        try:
            formatted_qc_prompt = qc_prompt.format(**qc_data)  
            print("   ✓ QC prompt formatted successfully")
            print("   Parameters used:", list(qc_data.keys()))
        except Exception as e:
            print(f"   ✗ Error formatting QC prompt: {e}")


def demonstrate_system_management():
    """Demonstrate system management features"""
    print("\n⚙️ System Management Demo")
    print("=" * 25)
    
    # System info
    print("1. System information:")
    info = get_system_info()
    print(f"   Version: {info['version']}")
    print(f"   Total experts: {len(info['available_techniques'])}")
    print(f"   Categories: {list(info['registry_stats']['categories'].keys())}")
    
    # Validation
    print("\n2. System validation:")
    validation = validate_system()
    print(f"   Total experts: {validation['total_experts']}")
    print(f"   Experts with errors: {validation['experts_with_errors']}")
    print(f"   System healthy: {validation['system_healthy']}")
    
    if validation['experts_with_errors'] > 0:
        print("   Issues found:")
        for expert_name, errors in validation['validation_results'].items():
            if errors:
                print(f"   - {expert_name}: {len(errors)} error(s)")


def demonstrate_technique_creation():
    """Demonstrate creating new techniques"""
    print("\n🔬 Technique Creation Demo")
    print("=" * 27)
    
    # Note: This is a demonstration - in practice you'd want to 
    # save to a real techniques directory
    print("1. Creating a new technique (demo mode):")
    print("   Technique: CITE-seq")
    print("   Category: Multiomics")
    print("   Description: Simultaneous protein and RNA measurement")
    print("   (In demo mode - not actually creating files)")
    
    # Show what the template system can do
    from prompts.template import DomainExpertTemplate
    
    # Generate code for a new technique
    cite_seq_code = DomainExpertTemplate.generate_expert_module_code(
        technique_name="cite_seq",
        display_name="CITE-seq",
        description="Simultaneous measurement of proteins and RNA in single cells",
        category="Multiomics",
        prompts_config=[
            {
                "name": "interpret_protein_rna",
                "description": "Interpret combined protein and RNA measurements",
                "template": """
CITE-seq analysis results:

- Cells analyzed: {n_cells}
- Proteins measured: {n_proteins}
- RNA genes detected: {n_genes}
- Cell types identified: {cell_types}

Please interpret these multimodal results including:
1. Correlation between protein and RNA levels
2. Cell type identification confidence
3. Novel insights from protein-RNA integration
""",
                "parameters": ["n_cells", "n_proteins", "n_genes", "cell_types"],
                "biological_context": "CELL_TYPE_IDENTIFICATION",
                "expertise_level": "EXPERT",
                "tags": ["multimodal", "protein", "rna"]
            }
        ]
    )
    
    print(f"   ✓ Generated {len(cite_seq_code)} characters of Python code")
    print("   ✓ Code includes complete expert class with prompts")
    print("   ✓ Ready for customization and deployment")


def main():
    """Main demonstration"""
    print("🧬 Welcome to the Domain Prompts System Demo!")
    print("This demonstration shows the new scalable architecture")
    print("for managing biological analysis domain expertise.\n")
    
    try:
        # Run all demonstrations
        demonstrate_basic_usage()
        demonstrate_search_and_filtering()
        demonstrate_prompt_usage()
        demonstrate_system_management()
        demonstrate_technique_creation()
        
        print("\n" + "=" * 60)
        print("✅ Demo completed successfully!")
        print("\nKey takeaways:")
        print("• The system is now modular and scalable")
        print("• Each technique has its own dedicated module")
        print("• Auto-discovery makes adding techniques seamless")
        print("• Rich metadata and validation ensure quality")
        print("• Template system enables rapid development")
        print("• Command-line interface provides powerful management")
        
        print("\nNext steps:")
        print("• Try: python -m domain_prompts list")
        print("• Try: python -m domain_prompts info scrnaseq")
        print("• Try: python -m domain_prompts validate")
        print("• Add your own techniques using the template system")
        
    except Exception as e:
        print(f"\n❌ Demo encountered an error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 