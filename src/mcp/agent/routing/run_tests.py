#!/usr/bin/env python3
"""
Comprehensive Test Runner for Biological Context Analysis Module

This script runs all tests, provides performance metrics,
and demonstrates the system capabilities.
"""

import sys
import os
import time
import asyncio
from datetime import datetime

# Import test modules
from .tests.test_static import main as run_static_tests
from .tests.test_dynamic import main as run_dynamic_tests

# Import main module components
from .biological_context import BiologicalContext, BiologicalOntologyGraph
from .enhanced_context_analyzer import EnhancedBiologicalContextAnalyzer
from .workflow_predictor import WorkflowPredictionEngine
from .learning_engine import ContinuousLearningEngine
from .multimodal_integrator import MultiModalContextIntegrator
from .file_analyzer import DataFileAnalyzer
from .temporal_analyzer import TemporalPatternAnalyzer


class TestRunner:
    """Comprehensive test runner with performance metrics."""
    
    def __init__(self):
        self.start_time = None
        self.test_results = {}
        self.performance_metrics = {}
    
    def banner(self, text):
        """Print a formatted banner."""
        print("\n" + "=" * 80)
        print(f"  {text}")
        print("=" * 80)
    
    def section(self, text):
        """Print a formatted section header."""
        print("\n" + "-" * 60)
        print(f"  {text}")
        print("-" * 60)
    
    def time_operation(self, operation_name, func, *args, **kwargs):
        """Time an operation and store metrics."""
        start = time.time()
        try:
            if asyncio.iscoroutinefunction(func):
                result = asyncio.run(func(*args, **kwargs))
            else:
                result = func(*args, **kwargs)
            
            end = time.time()
            execution_time = end - start
            
            self.performance_metrics[operation_name] = {
                'execution_time': execution_time,
                'success': True,
                'result': result
            }
            
            print(f"✓ {operation_name}: {execution_time:.3f}s")
            return result
            
        except Exception as e:
            end = time.time()
            execution_time = end - start
            
            self.performance_metrics[operation_name] = {
                'execution_time': execution_time,
                'success': False,
                'error': str(e)
            }
            
            print(f"❌ {operation_name}: Failed after {execution_time:.3f}s - {e}")
            return None
    
    def run_component_tests(self):
        """Test individual components for basic functionality."""
        self.section("Component Functionality Tests")
        
        # Test BiologicalOntologyGraph
        def test_ontology():
            ontology = BiologicalOntologyGraph()
            nodes = ontology.graph.number_of_nodes()
            edges = ontology.graph.number_of_edges()
            related = ontology.get_related_concepts("transcriptomics", max_distance=2)
            return {'nodes': nodes, 'edges': edges, 'related_count': len(related)}
        
        ontology_result = self.time_operation("Ontology Graph Creation", test_ontology)
        if ontology_result:
            print(f"  - Nodes: {ontology_result['nodes']}")
            print(f"  - Edges: {ontology_result['edges']}")
            print(f"  - Related concepts found: {ontology_result['related_count']}")
        
        # Test WorkflowPredictionEngine
        def test_workflow_predictor():
            predictor = WorkflowPredictionEngine()
            workflows = list(predictor.workflow_graphs.keys())
            scrna_nodes = predictor.workflow_graphs['scrna_seq'].number_of_nodes()
            return {'workflows': workflows, 'scrna_nodes': scrna_nodes}
        
        workflow_result = self.time_operation("Workflow Predictor", test_workflow_predictor)
        if workflow_result:
            print(f"  - Available workflows: {workflow_result['workflows']}")
            print(f"  - scRNA-seq workflow nodes: {workflow_result['scrna_nodes']}")
        
        # Test DataFileAnalyzer
        def test_file_analyzer():
            analyzer = DataFileAnalyzer()
            
            class MockFile:
                def __init__(self, name, size, content):
                    self.name = name
                    self.size = size
                    self.content = content
                
                def read(self, n):
                    return self.content.encode('utf-8')
            
            files = [
                MockFile("test.csv", 1000, "gene_id,count\nGENE1,100"),
                MockFile("data.h5ad", 50000, "single cell data")
            ]
            
            async def analyze_files():
                return await analyzer.analyze(files)
            
            return asyncio.run(analyze_files())
        
        file_result = self.time_operation("File Analyzer", test_file_analyzer)
        if file_result:
            print(f"  - Files analyzed: {file_result['file_count']}")
            print(f"  - File types detected: {file_result['file_types']}")
        
        # Test EnhancedBiologicalContextAnalyzer
        def test_enhanced_analyzer():
            analyzer = EnhancedBiologicalContextAnalyzer()
            domain_result = analyzer._classify_primary_domain(['scrna_seq', 'differential'], [])
            patterns = list(analyzer.semantic_patterns.keys())
            return {'domain': domain_result, 'pattern_categories': len(patterns)}
        
        analyzer_result = self.time_operation("Enhanced Analyzer", test_enhanced_analyzer)
        if analyzer_result:
            print(f"  - Classified domain: {analyzer_result['domain']}")
            print(f"  - Pattern categories: {analyzer_result['pattern_categories']}")
    
    def run_integration_demo(self):
        """Run an integration demo showing component interaction."""
        self.section("Integration Demo")
        
        def integration_demo():
            # Initialize components
            analyzer = EnhancedBiologicalContextAnalyzer()
            workflow_predictor = WorkflowPredictionEngine()
            learning_engine = ContinuousLearningEngine()
            
            # Demo scenario
            query = "I want to analyze single-cell RNA-seq data for cell type identification"
            print(f"Demo Query: '{query}'")
            
            # Test domain classification
            domain = analyzer._classify_primary_domain(['scrna_seq', 'cell_type'], [])
            print(f"Predicted domain: {domain}")
            
            # Test workflow determination
            context = BiologicalContext(
                primary_domain=domain,
                secondary_domains=[],
                data_types=["scrna_seq"],
                experimental_design="case_control",
                analysis_objectives=["cell_type_identification"],
                workflow_stage="preprocessing",
                complexity_score=0.7,
                tool_recommendations={"seurat": 0.9, "scanpy": 0.8},
                integration_requirements={},
                confidence_metrics={"domain": 0.85}
            )
            
            workflow_type = workflow_predictor._determine_workflow_type(context)
            print(f"Workflow type: {workflow_type}")
            
            # Test tool recommendations
            tools = workflow_predictor._get_step_tools("clustering")
            print(f"Clustering tools: {tools}")
            
            # Test feature extraction
            features = learning_engine._extract_query_features(query)
            print(f"Query features (first 5): {features[:5]}")
            
            return {
                'domain': domain,
                'workflow_type': workflow_type,
                'tools': tools,
                'feature_count': len(features)
            }
        
        demo_result = self.time_operation("Integration Demo", integration_demo)
        return demo_result is not None
    
    def run_performance_tests(self):
        """Run performance tests on key operations."""
        self.section("Performance Tests")
        
        # Test ontology lookup performance
        def test_ontology_performance():
            ontology = BiologicalOntologyGraph()
            start = time.time()
            
            concepts = ['transcriptomics', 'genomics', 'proteomics', 'scrna_seq']
            total_related = 0
            
            for concept in concepts:
                related = ontology.get_related_concepts(concept, max_distance=2)
                total_related += len(related)
            
            end = time.time()
            return {
                'concepts_tested': len(concepts),
                'total_related_found': total_related,
                'avg_time_per_concept': (end - start) / len(concepts)
            }
        
        perf_result = self.time_operation("Ontology Lookup Performance", test_ontology_performance)
        if perf_result:
            print(f"  - Concepts tested: {perf_result['concepts_tested']}")
            print(f"  - Related concepts found: {perf_result['total_related_found']}")
            print(f"  - Avg time per concept: {perf_result['avg_time_per_concept']:.4f}s")
        
        # Test feature extraction performance
        def test_feature_extraction_performance():
            engine = ContinuousLearningEngine()
            
            queries = [
                "Analyze single-cell RNA-seq data",
                "Perform differential expression analysis",
                "Run pathway enrichment analysis",
                "Identify cell type markers",
                "Analyze protein-protein interactions"
            ]
            
            start = time.time()
            total_features = 0
            
            for query in queries:
                features = engine._extract_query_features(query)
                total_features += len(features)
            
            end = time.time()
            return {
                'queries_processed': len(queries),
                'total_features': total_features,
                'avg_time_per_query': (end - start) / len(queries)
            }
        
        feature_result = self.time_operation("Feature Extraction Performance", test_feature_extraction_performance)
        if feature_result:
            print(f"  - Queries processed: {feature_result['queries_processed']}")
            print(f"  - Total features extracted: {feature_result['total_features']}")
            print(f"  - Avg time per query: {feature_result['avg_time_per_query']:.4f}s")
    
    def run_all_tests(self):
        """Run complete test suite."""
        self.start_time = datetime.now()
        
        self.banner("BIOLOGICAL CONTEXT ANALYSIS MODULE - COMPREHENSIVE TESTING")
        print(f"Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run static tests
        self.section("Static Unit Tests")
        static_success = self.time_operation("Static Tests", run_static_tests)
        self.test_results['static'] = static_success
        
        # Run dynamic tests
        self.section("Dynamic Integration Tests")
        dynamic_success = self.time_operation("Dynamic Tests", run_dynamic_tests)
        self.test_results['dynamic'] = dynamic_success
        
        # Run component tests
        self.run_component_tests()
        
        # Run integration demo
        integration_success = self.run_integration_demo()
        self.test_results['integration'] = integration_success
        
        # Run performance tests
        self.run_performance_tests()
        
        # Generate summary
        self.generate_summary()
    
    def generate_summary(self):
        """Generate comprehensive test summary."""
        end_time = datetime.now()
        total_time = (end_time - self.start_time).total_seconds()
        
        self.banner("TEST SUMMARY REPORT")
        
        print(f"Total execution time: {total_time:.2f} seconds")
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Ended: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test results summary
        print("\nTest Results:")
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        for test_name, success in self.test_results.items():
            status = "✓ PASS" if success else "❌ FAIL"
            print(f"  {test_name.upper()}: {status}")
        
        print(f"\nOverall: {passed_tests}/{total_tests} test categories passed")
        
        # Performance metrics summary
        print("\nPerformance Metrics:")
        for operation, metrics in self.performance_metrics.items():
            if metrics['success']:
                print(f"  {operation}: {metrics['execution_time']:.3f}s")
            else:
                print(f"  {operation}: FAILED")
        
        # System health check
        print("\nSystem Health Check:")
        health_score = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        if health_score >= 90:
            health_status = "🟢 EXCELLENT"
        elif health_score >= 70:
            health_status = "🟡 GOOD"
        elif health_score >= 50:
            health_status = "🟠 FAIR"
        else:
            health_status = "🔴 POOR"
        
        print(f"  Overall Health: {health_status} ({health_score:.1f}%)")
        
        # Recommendations
        print("\nRecommendations:")
        if health_score < 100:
            print("  - Review failed test cases for potential issues")
            print("  - Check system dependencies and configurations")
        else:
            print("  - System is operating optimally")
            print("  - Ready for production deployment")
        
        return health_score >= 70  # Return True if system is healthy


def main():
    """Main entry point."""
    runner = TestRunner()
    
    try:
        success = runner.run_all_tests()
        
        print("\n" + "=" * 80)
        if success:
            print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
            print("The Biological Context Analysis Module is ready for use.")
        else:
            print("⚠️  SOME TESTS FAILED")
            print("Please review the test results and address any issues.")
        print("=" * 80)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\nTest execution interrupted by user.")
        return 1
    except Exception as e:
        print(f"\n\nUnexpected error during testing: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 