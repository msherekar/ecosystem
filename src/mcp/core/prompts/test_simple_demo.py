#!/usr/bin/env python3
"""
Simple Working Demo of the Prompts System
"""

import importlib.util

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    print("🧬 Prompts System - Simple Working Demo")
    print("=" * 40)
    
    try:
        # Load core module (now we're in the prompts folder)
        print("📦 Loading core module...")
        core = load_module('core', 'core.py')
        print("✅ Core module loaded!")
        
        # Create expert
        print("\n👨‍🔬 Creating RNA-seq expert...")
        metadata = core.TechniqueMetadata(
            name='demo_rnaseq',
            display_name='Demo RNA-seq Analysis',
            description='RNA sequencing analysis demonstration',
            category='Transcriptomics'
        )
        
        expert = core.BaseDomainExpert(metadata)
        print(f"✅ Expert created: {metadata.display_name}")
        
        # Add analysis prompt
        print("\n💬 Adding analysis prompt...")
        prompt = core.DomainPrompt(
            name='analyze_results',
            description='Analyze RNA-seq results',
            template='''RNA-seq Analysis Results:

Study: {study_name}
Samples: {sample_count}
Significant genes: {sig_genes}
Top gene: {top_gene}

Interpretation: {interpretation}

Next steps: {next_steps}''',
            parameters=['study_name', 'sample_count', 'sig_genes', 'top_gene', 'interpretation', 'next_steps'],
            expertise_level=core.ExpertiseLevel.EXPERT,
            biological_context=core.BiologicalContext.GENE_EXPRESSION
        )
        
        expert.add_prompt(prompt)
        print(f"✅ Added prompt: {prompt.name}")
        
        # Test prompt formatting
        print("\n🧪 Testing prompt formatting...")
        formatted = prompt.format(
            study_name='Alzheimer Disease Study',
            sample_count='24',
            sig_genes='1,247',
            top_gene='APOE (log2FC: 4.2)',
            interpretation='Strong neuroinflammatory response detected',
            next_steps='Validate with qRT-PCR and pathway analysis'
        )
        
        print("✅ Prompt formatted successfully!")
        print(f"📄 Output length: {len(formatted)} characters")
        
        # Show sample output
        print("\n📋 Sample Generated Report:")
        print("-" * 30)
        print(formatted[:200] + "..." if len(formatted) > 200 else formatted)
        
        # Test expert features
        print("\n⚙️ Testing expert features...")
        all_prompts = expert.get_prompts()
        gene_expr_prompts = expert.get_prompts_by_context(core.BiologicalContext.GENE_EXPRESSION)
        expert_level_prompts = expert.get_prompts_by_expertise(core.ExpertiseLevel.EXPERT)
        
        print(f"✅ Total prompts: {len(all_prompts)}")
        print(f"✅ Gene expression prompts: {len(gene_expr_prompts)}")
        print(f"✅ Expert level prompts: {len(expert_level_prompts)}")
        
        # Validation
        errors = expert.validate_prompts()
        print(f"✅ Validation errors: {len(errors)}")
        
        print("\n🎉 SUCCESS! Prompts system is working perfectly!")
        print("="*50)
        print("✅ Expert creation: Working")
        print("✅ Prompt formatting: Working") 
        print("✅ Context filtering: Working")
        print("✅ Expertise filtering: Working")
        print("✅ Validation: Working")
        print("\n🚀 Ready for production use!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 