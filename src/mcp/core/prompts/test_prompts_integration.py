#!/usr/bin/env python3
"""
Comprehensive test script for the Domain Prompts System
"""

import sys
import importlib.util
from pathlib import Path

def load_module_direct(module_name, file_path):
    """Load a module directly from file path"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_core_modules():
    """Test core prompts modules"""
    print("🧪 Testing Core Modules...")
    
    # Load core modules (now we're in the prompts folder)
    core = load_module_direct('core', 'core.py')
    security = load_module_direct('security', 'security.py')
    events = load_module_direct('events', 'events.py')
    performance = load_module_direct('performance', 'performance.py')
    
    print("✅ Core modules loaded successfully")
    
    # Test DomainPrompt
    prompt = core.DomainPrompt(
        name='test_prompt',
        description='Test prompt for integration',
        template='Analyze {data_type} with {method} showing {result}',
        parameters=['data_type', 'method', 'result'],
        expertise_level=core.ExpertiseLevel.INTERMEDIATE,
        biological_context=core.BiologicalContext.GENE_EXPRESSION
    )
    
    formatted = prompt.format(
        data_type='RNA-seq data',
        method='DESeq2',
        result='differential expression'
    )
    print(f"✅ DomainPrompt: {prompt.name} - formatted successfully")
    
    # Test TechniqueMetadata
    metadata = core.TechniqueMetadata(
        name='test_integration',
        display_name='Integration Test Technique',
        description='A comprehensive technique for testing system integration',
        category='Bioinformatics',
        aliases=['integration-test', 'test-tech'],
        typical_applications=['Testing', 'Validation', 'Quality Assurance']
    )
    print(f"✅ TechniqueMetadata: {metadata.display_name}")
    
    # Test BaseDomainExpert
    expert = core.BaseDomainExpert(metadata)
    expert.add_prompt(prompt)
    
    # Add a few more prompts to test variety
    qc_prompt = core.DomainPrompt(
        name='quality_control',
        description='Quality control assessment',
        template='QC Status: {status}, Metrics: {metrics}',
        parameters=['status', 'metrics'],
        expertise_level=core.ExpertiseLevel.BASIC,
        biological_context=core.BiologicalContext.QUALITY_CONTROL
    )
    expert.add_prompt(qc_prompt)
    
    expert_prompts = expert.get_prompts()
    print(f"✅ BaseDomainExpert: {len(expert_prompts)} prompts")
    
    # Test filtering by context
    qc_prompts = expert.get_prompts_by_context(core.BiologicalContext.QUALITY_CONTROL)
    print(f"✅ Context filtering: {len(qc_prompts)} QC prompts")
    
    # Test validation
    errors = expert.validate_prompts()
    print(f"✅ Validation: {len(errors)} errors")
    
    # Test security
    safe_input = security.SecurityValidator.validate_string('test_data_123', 200, 'test_field')
    print(f"✅ Security validation: {safe_input}")
    
    # Test events
    emitter = events.EventEmitter()
    event_count = 0
    
    def count_events(event):
        nonlocal event_count
        event_count += 1
    
    emitter.on('test_event', count_events)
    emitter.emit('test_event', {'test': 'data'})
    print(f"✅ Events: {event_count} events processed")
    
    # Test performance
    monitor = performance.PerformanceMonitor()
    monitor.record_timing('test_operation', 0.123)
    perf_stats = monitor.get_stats()
    print(f"✅ Performance: {perf_stats['system']['tracked_operations']} operations")
    
    return {
        'core': core,
        'security': security,
        'events': events,
        'performance': performance,
        'test_expert': expert
    }

def test_technique_creation(core_modules):
    """Test creating a technique manually"""
    print("\n🧬 Testing Technique Creation...")
    
    core = core_modules['core']
    
    # Create a custom technique
    custom_metadata = core.TechniqueMetadata(
        name='custom_rnaseq',
        display_name='Custom RNA-seq Analysis',
        description='Custom RNA sequencing analysis with enhanced features',
        category='Transcriptomics',
        aliases=['custom-rna', 'enhanced-rnaseq'],
        typical_applications=[
            'Differential expression analysis',
            'Pathway enrichment',
            'Gene set analysis',
            'Biomarker discovery'
        ]
    )
    
    custom_expert = core.BaseDomainExpert(custom_metadata)
    
    # Add various prompts
    prompts_to_add = [
        {
            'name': 'interpret_degs',
            'description': 'Interpret differentially expressed genes',
            'template': 'DEG Analysis: {n_degs} genes, Top upregulated: {top_up}, Top downregulated: {top_down}, Pathways: {pathways}',
            'parameters': ['n_degs', 'top_up', 'top_down', 'pathways'],
            'context': core.BiologicalContext.DIFFERENTIAL_EXPRESSION,
            'level': core.ExpertiseLevel.EXPERT
        },
        {
            'name': 'quality_assessment',
            'description': 'Assess RNA-seq data quality',
            'template': 'Quality: {quality_score}, Read depth: {read_depth}, Alignment: {alignment_rate}%, rRNA: {rrna_pct}%',
            'parameters': ['quality_score', 'read_depth', 'alignment_rate', 'rrna_pct'],
            'context': core.BiologicalContext.QUALITY_CONTROL,
            'level': core.ExpertiseLevel.INTERMEDIATE
        },
        {
            'name': 'pathway_interpretation',
            'description': 'Interpret pathway enrichment results',
            'template': 'Pathways: {significant_pathways}, Top pathway: {top_pathway}, P-value: {pvalue}, Genes: {gene_count}',
            'parameters': ['significant_pathways', 'top_pathway', 'pvalue', 'gene_count'],
            'context': core.BiologicalContext.PATHWAY_ANALYSIS,
            'level': core.ExpertiseLevel.EXPERT
        }
    ]
    
    for prompt_config in prompts_to_add:
        prompt = core.DomainPrompt(
            name=prompt_config['name'],
            description=prompt_config['description'],
            template=prompt_config['template'],
            parameters=prompt_config['parameters'],
            expertise_level=prompt_config['level'],
            biological_context=prompt_config['context'],
            tags={'custom', 'rnaseq', prompt_config['context'].value}
        )
        custom_expert.add_prompt(prompt)
    
    # Test the custom expert
    custom_prompts = custom_expert.get_prompts()
    print(f"✅ Custom expert created: {len(custom_prompts)} prompts")
    
    # Test prompt by context
    for context in [core.BiologicalContext.DIFFERENTIAL_EXPRESSION, 
                   core.BiologicalContext.QUALITY_CONTROL, 
                   core.BiologicalContext.PATHWAY_ANALYSIS]:
        context_prompts = custom_expert.get_prompts_by_context(context)
        print(f"✅ {context.display_name}: {len(context_prompts)} prompts")
    
    # Test prompt formatting
    deg_prompt = custom_expert.get_prompt_by_name('interpret_degs')
    if deg_prompt:
        formatted = deg_prompt.format(
            n_degs='1,247',
            top_up='APOE, CLU, TREM2',
            top_down='SYN1, SNAP25, GRIN1',
            pathways='Alzheimer disease, synaptic transmission'
        )
        print(f"✅ DEG prompt formatted: {len(formatted)} characters")
    
    return custom_expert

def test_system_integration():
    """Test overall system integration"""
    print("\n🔗 Testing System Integration...")
    
    # Test core functionality
    core_modules = test_core_modules()
    
    # Test technique creation
    custom_expert = test_technique_creation(core_modules)
    
    # Test expert collection
    experts = {
        'test_integration': core_modules['test_expert'],
        'custom_rnaseq': custom_expert
    }
    
    print(f"\n📊 Integration Summary:")
    print(f"✅ Experts created: {len(experts)}")
    
    total_prompts = 0
    for name, expert in experts.items():
        prompts = expert.get_prompts()
        total_prompts += len(prompts)
        metadata = expert.get_metadata()
        print(f"  - {name}: {metadata.display_name} ({len(prompts)} prompts)")
    
    print(f"✅ Total prompts available: {total_prompts}")
    
    # Test cross-expert functionality
    core = core_modules['core']
    all_contexts = set()
    all_levels = set()
    
    for expert in experts.values():
        for prompt in expert.get_prompts().values():
            all_contexts.add(prompt.biological_context)
            all_levels.add(prompt.expertise_level)
    
    print(f"✅ Biological contexts used: {len(all_contexts)}")
    print(f"✅ Expertise levels used: {len(all_levels)}")
    
    return True

if __name__ == "__main__":
    print("🧬 Domain Prompts System - Comprehensive Integration Test")
    print("=" * 60)
    
    try:
        success = test_system_integration()
        if success:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ Core modules work independently")
            print("✅ Techniques can be created and used")
            print("✅ System integration is functional")
            print("✅ Ready for advanced features testing")
        else:
            print("\n❌ Some tests failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 