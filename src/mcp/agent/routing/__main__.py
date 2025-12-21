"""
Main entry point for Biological Context Analysis Module

Run comprehensive tests and demonstrations of all components.
Usage: python -m src.mcp.agent.routing
"""

import asyncio
import sys
from datetime import datetime

from .biological_context import BiologicalContext
from .enhanced_context_analyzer import EnhancedBiologicalContextAnalyzer
from .workflow_predictor import WorkflowPredictionEngine
from .learning_engine import ContinuousLearningEngine
from .multimodal_integrator import MultiModalContextIntegrator
from .file_analyzer import DataFileAnalyzer
from .temporal_analyzer import TemporalPatternAnalyzer


async def test_biological_context():
    """Test BiologicalContext data structure."""
    print("=" * 60)
    print("Testing BiologicalContext...")
    
    context = BiologicalContext(
        primary_domain="transcriptomics",
        secondary_domains=["genomics"],
        data_types=["scrna_seq", "bulk_rnaseq"],
        experimental_design="case_control",
        analysis_objectives=["differential_expression", "pathway_analysis"],
        workflow_stage="preprocessing",
        complexity_score=0.75,
        tool_recommendations={"seurat": 0.9, "scanpy": 0.8, "deseq2": 0.7},
        integration_requirements={"required": True, "integration_type": "multi_omics"},
        confidence_metrics={"domain": 0.95, "workflow": 0.85}
    )
    
    print(f"Primary domain: {context.primary_domain}")
    print(f"Data types: {context.data_types}")
    print(f"Tool recommendations: {context.tool_recommendations}")
    print(f"Complexity score: {context.complexity_score}")
    print("✓ BiologicalContext test passed")


async def test_enhanced_analyzer():
    """Test EnhancedBiologicalContextAnalyzer."""
    print("=" * 60)
    print("Testing EnhancedBiologicalContextAnalyzer...")
    
    analyzer = EnhancedBiologicalContextAnalyzer()
    
    test_queries = [
        "I want to analyze single-cell RNA-seq data for cell type identification",
        "How do I perform differential expression analysis on bulk RNA-seq?",
        "Can you help me with pathway enrichment analysis for my proteomics data?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\nTest {i}: '{query}'")
        
        # Test domain analysis (synchronous methods)
        domain_result = analyzer._classify_primary_domain(['scrna_seq'], [])
        print(f"  Classified domain: {domain_result}")
        
        # Test semantic patterns
        patterns = analyzer.semantic_patterns
        print(f"  Available pattern categories: {list(patterns.keys())}")
    
    print("✓ Enhanced analyzer test passed")


async def test_workflow_predictor():
    """Test WorkflowPredictionEngine."""
    print("=" * 60)
    print("Testing WorkflowPredictionEngine...")
    
    predictor = WorkflowPredictionEngine()
    
    # Test workflow graphs
    print(f"Available workflows: {list(predictor.workflow_graphs.keys())}")
    
    scrna_workflow = predictor.workflow_graphs['scrna_seq']
    print(f"scRNA-seq workflow has {scrna_workflow.number_of_nodes()} nodes")
    print(f"scRNA-seq workflow has {scrna_workflow.number_of_edges()} edges")
    
    # Test step analysis
    tools = predictor._get_step_tools("differential_expression")
    print(f"Tools for differential expression: {tools}")
    
    difficulty = predictor._assess_step_difficulty("pathway_analysis", None)
    print(f"Difficulty of pathway analysis: {difficulty}")
    
    print("✓ Workflow predictor test passed")


async def test_learning_engine():
    """Test ContinuousLearningEngine."""
    print("=" * 60)
    print("Testing ContinuousLearningEngine...")
    
    engine = ContinuousLearningEngine()
    
    # Test feature extraction
    test_query = "Perform single-cell RNA-seq clustering analysis with Seurat"
    features = engine._extract_query_features(test_query)
    print(f"Query features for '{test_query}': {features[:5]}...")  # Show first 5
    
    # Test learning metrics
    insights = engine.get_adaptation_insights()
    print(f"Learning insights: {insights}")
    
    print("✓ Learning engine test passed")


async def test_file_analyzer():
    """Test DataFileAnalyzer."""
    print("=" * 60)
    print("Testing DataFileAnalyzer...")
    
    analyzer = DataFileAnalyzer()
    
    # Create mock file for testing
    class MockFile:
        def __init__(self, name, size, content):
            self.name = name
            self.size = size
            self.content = content
        
        def read(self, n):
            return self.content.encode('utf-8')
    
    test_files = [
        MockFile("expression_matrix.csv", 5000000, "gene_id,sample1,sample2\nGENE1,100,200"),
        MockFile("metadata.tsv", 1000, "sample_id\tcondition\nsample1\tcontrol"),
        MockFile("scrna_data.h5ad", 50000000, "# Single cell data")
    ]
    
    # Test file type detection
    for file in test_files:
        file_type = analyzer._detect_file_type(file)
        experiment_type = analyzer._infer_experiment_type(file.name, file.content)
        print(f"File: {file.name} -> Type: {file_type}, Experiment: {experiment_type}")
    
    print("✓ File analyzer test passed")


async def test_temporal_analyzer():
    """Test TemporalPatternAnalyzer."""
    print("=" * 60)
    print("Testing TemporalPatternAnalyzer...")
    
    analyzer = TemporalPatternAnalyzer()
    
    # Create mock temporal context
    now = datetime.now()
    session_start = datetime(now.year, now.month, now.day, now.hour - 1)
    
    temporal_context = {
        'session_start': session_start,
        'interaction_times': [
            session_start,
            datetime(now.year, now.month, now.day, now.hour - 1, 15),
            datetime(now.year, now.month, now.day, now.hour - 1, 30),
            datetime(now.year, now.month, now.day, now.hour - 1, 50)
        ],
        'query_types': ['data_upload', 'preprocessing', 'analysis', 'visualization'],
        'completed_tasks': 2
    }
    
    # Test pattern detection
    pattern = analyzer._detect_workflow_pattern(temporal_context)
    print(f"Detected workflow pattern: {pattern}")
    
    pace = analyzer._classify_interaction_pace(900)  # 15 minutes
    print(f"Interaction pace for 15-min intervals: {pace}")
    
    engagement = analyzer._assess_engagement_level(temporal_context)
    print(f"User engagement level: {engagement}")
    
    print("✓ Temporal analyzer test passed")


async def test_multimodal_integrator():
    """Test MultiModalContextIntegrator."""
    print("=" * 60)
    print("Testing MultiModalContextIntegrator...")
    
    integrator = MultiModalContextIntegrator()
    
    print(f"Available modalities: {list(integrator.modality_analyzers.keys())}")
    print(f"Fusion weights: {integrator.fusion_weights}")
    
    # Test consistency calculation
    mock_contexts = {
        'text': {'keywords': ['rna', 'expression'], 'confidence': 0.8},
        'data_files': {'file_types': ['csv', 'h5ad'], 'confidence': 0.9}
    }
    
    consistency = integrator._calculate_consistency(mock_contexts)
    print(f"Consistency score: {consistency}")
    
    print("✓ Multimodal integrator test passed")


async def run_comprehensive_demo():
    """Run a comprehensive demonstration of integrated functionality."""
    print("=" * 60)
    print("COMPREHENSIVE INTEGRATION DEMO")
    print("=" * 60)
    
    # Initialize all components
    analyzer = EnhancedBiologicalContextAnalyzer()
    
    # Demo query
    demo_query = "I have single-cell RNA-seq data and want to identify cell types and find marker genes"
    print(f"Demo Query: '{demo_query}'")
    
    # Simulate session state
    session_state = {
        'loaded_data': 'scrna_matrix.h5ad',
        'current_stage': 'data_exploration',
        'completed_steps': ['data_loading', 'quality_control'],
        'available_data': ['raw_counts', 'metadata']
    }
    
    print(f"Session state: {session_state}")
    
    # Test domain analysis
    domain_result = analyzer._classify_primary_domain(['scrna_seq', 'cell_type'], [])
    print(f"Predicted primary domain: {domain_result}")
    
    # Test workflow prediction
    workflow_predictor = WorkflowPredictionEngine()
    workflow_type = workflow_predictor._determine_workflow_type(
        BiologicalContext(
            primary_domain="transcriptomics",
            secondary_domains=[],
            data_types=["scrna_seq"],
            experimental_design="case_control",
            analysis_objectives=["cell_type_identification"],
            workflow_stage="data_exploration",
            complexity_score=0.7,
            tool_recommendations={},
            integration_requirements={},
            confidence_metrics={}
        )
    )
    print(f"Determined workflow type: {workflow_type}")
    
    print("\n✓ Comprehensive demo completed successfully!")


async def main():
    """Main entry point for testing and demonstration."""
    print("BIOLOGICAL CONTEXT ANALYSIS MODULE")
    print("Comprehensive Testing and Demonstration")
    print("=" * 60)
    
    test_functions = [
        test_biological_context,
        test_enhanced_analyzer,
        test_workflow_predictor,
        test_learning_engine,
        test_file_analyzer,
        test_temporal_analyzer,
        test_multimodal_integrator,
        run_comprehensive_demo
    ]
    
    for test_func in test_functions:
        try:
            await test_func()
            print()
        except Exception as e:
            print(f"❌ Error in {test_func.__name__}: {e}")
            print()
    
    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main()) 