"""
Static Unit Tests for Biological Context Analysis Module

Tests individual components and their methods without external dependencies.
"""

import unittest
from datetime import datetime
from unittest.mock import Mock, patch

import sys
import os

# Use absolute imports from the routing package  
from ..biological_context import BiologicalContext, BiologicalOntologyGraph
from ..workflow_predictor import WorkflowPredictionEngine
from ..learning_engine import ContinuousLearningEngine
from ..file_analyzer import DataFileAnalyzer
from ..temporal_analyzer import TemporalPatternAnalyzer


class TestBiologicalContext(unittest.TestCase):
    """Test BiologicalContext data structure."""
    
    def test_context_creation(self):
        """Test basic context creation."""
        context = BiologicalContext(
            primary_domain="transcriptomics",
            secondary_domains=["genomics"],
            data_types=["scrna_seq"],
            experimental_design="case_control",
            analysis_objectives=["differential_expression"],
            workflow_stage="preprocessing",
            complexity_score=0.7,
            tool_recommendations={"seurat": 0.9},
            integration_requirements={},
            confidence_metrics={"domain": 0.8}
        )
        
        self.assertEqual(context.primary_domain, "transcriptomics")
        self.assertEqual(context.data_types, ["scrna_seq"])
        self.assertEqual(context.complexity_score, 0.7)
        self.assertIn("seurat", context.tool_recommendations)
    
    def test_default_values(self):
        """Test default field values."""
        context = BiologicalContext(
            primary_domain="genomics",
            secondary_domains=[],
            data_types=["wgs"],
            experimental_design="unknown",
            analysis_objectives=[],
            workflow_stage="initial",
            complexity_score=0.5,
            tool_recommendations={},
            integration_requirements={},
            confidence_metrics={}
        )
        
        self.assertEqual(context.expertise_level, "intermediate")
        self.assertEqual(context.estimated_time_remaining, 0.0)
        self.assertEqual(context.statistical_power, 0.0)
        self.assertIsInstance(context.preferred_tools, list)


class TestBiologicalOntologyGraph(unittest.TestCase):
    """Test BiologicalOntologyGraph functionality."""
    
    def setUp(self):
        """Set up test ontology."""
        self.ontology = BiologicalOntologyGraph()
    
    def test_graph_creation(self):
        """Test ontology graph creation."""
        self.assertIsNotNone(self.ontology.graph)
        self.assertGreater(self.ontology.graph.number_of_nodes(), 0)
        self.assertGreater(self.ontology.graph.number_of_edges(), 0)
    
    def test_related_concepts(self):
        """Test related concepts retrieval."""
        # Test with a concept that should exist
        related = self.ontology.get_related_concepts("transcriptomics", max_distance=1)
        self.assertIsInstance(related, list)
        
        # Test with non-existent concept
        related_empty = self.ontology.get_related_concepts("nonexistent", max_distance=1)
        self.assertEqual(related_empty, [])
    
    def test_concept_path(self):
        """Test concept path finding."""
        # Test path between related concepts
        path = self.ontology.get_concept_path("omics_data", "transcriptomics")
        self.assertIsInstance(path, list)
        
        # Test path between unrelated concepts
        path_empty = self.ontology.get_concept_path("nonexistent1", "nonexistent2")
        self.assertEqual(path_empty, [])


class TestWorkflowPredictionEngine(unittest.TestCase):
    """Test WorkflowPredictionEngine functionality."""
    
    def setUp(self):
        """Set up test workflow predictor."""
        self.predictor = WorkflowPredictionEngine()
    
    def test_workflow_graphs(self):
        """Test workflow graph creation."""
        graphs = self.predictor.workflow_graphs
        self.assertIn('scrna_seq', graphs)
        self.assertIn('bulk_rnaseq', graphs)
        self.assertIn('proteomics', graphs)
        
        # Test graph structure
        scrna_graph = graphs['scrna_seq']
        self.assertGreater(scrna_graph.number_of_nodes(), 0)
        self.assertGreater(scrna_graph.number_of_edges(), 0)
    
    def test_workflow_type_determination(self):
        """Test workflow type determination."""
        # Mock context for scRNA-seq
        context = BiologicalContext(
            primary_domain="transcriptomics",
            secondary_domains=[],
            data_types=["scrna_seq"],
            experimental_design="case_control",
            analysis_objectives=[],
            workflow_stage="initial",
            complexity_score=0.5,
            tool_recommendations={},
            integration_requirements={},
            confidence_metrics={}
        )
        
        workflow_type = self.predictor._determine_workflow_type(context)
        self.assertEqual(workflow_type, "scrna_seq")
        
        # Test bulk RNA-seq
        context.data_types = ["bulk_rnaseq"]
        workflow_type = self.predictor._determine_workflow_type(context)
        self.assertEqual(workflow_type, "bulk_rnaseq")
    
    def test_step_tools(self):
        """Test step tool retrieval."""
        tools = self.predictor._get_step_tools("clustering")
        self.assertIsInstance(tools, list)
        self.assertIn("seurat", tools)
        
        # Test unknown step
        unknown_tools = self.predictor._get_step_tools("unknown_step")
        self.assertEqual(unknown_tools, [])
    
    def test_step_difficulty(self):
        """Test step difficulty assessment."""
        difficulty = self.predictor._assess_step_difficulty("data_loading", None)
        self.assertEqual(difficulty, "easy")
        
        difficulty = self.predictor._assess_step_difficulty("pathway_analysis", None)
        self.assertEqual(difficulty, "hard")


class TestContinuousLearningEngine(unittest.TestCase):
    """Test ContinuousLearningEngine functionality."""
    
    def setUp(self):
        """Set up test learning engine."""
        self.engine = ContinuousLearningEngine()
    
    def test_feature_extraction(self):
        """Test query feature extraction."""
        query = "Perform differential expression analysis on RNA-seq data"
        features = self.engine._extract_query_features(query)
        
        self.assertIsInstance(features, list)
        self.assertGreater(len(features), 0)
        self.assertIsInstance(features[0], (int, float))
    
    def test_tool_action_detection(self):
        """Test tool action detection."""
        self.assertTrue(self.engine._is_tool_action("run seurat analysis"))
        self.assertTrue(self.engine._is_tool_action("execute deseq2"))
        self.assertFalse(self.engine._is_tool_action("check data quality"))
    
    def test_learning_metrics(self):
        """Test learning metrics initialization."""
        metrics = self.engine.get_adaptation_insights()
        self.assertIsInstance(metrics, dict)
        self.assertIn('total_interactions', metrics)
        self.assertIn('successful_predictions', metrics)


class TestDataFileAnalyzer(unittest.TestCase):
    """Test DataFileAnalyzer functionality."""
    
    def setUp(self):
        """Set up test file analyzer."""
        self.analyzer = DataFileAnalyzer()
    
    def test_file_type_detection(self):
        """Test file type detection."""
        # Create mock files
        class MockFile:
            def __init__(self, name):
                self.name = name
        
        # Test known file types
        csv_file = MockFile("expression_data.csv")
        self.assertEqual(self.analyzer._detect_file_type(csv_file), "csv")
        
        h5ad_file = MockFile("single_cell.h5ad")
        self.assertEqual(self.analyzer._detect_file_type(h5ad_file), "h5ad")
        
        # Test unknown file type
        unknown_file = MockFile("data.xyz")
        self.assertEqual(self.analyzer._detect_file_type(unknown_file), "unknown")
    
    def test_experiment_type_inference(self):
        """Test experiment type inference."""
        # Test RNA-seq detection
        filename = "rnaseq_counts.csv"
        content = "gene expression data for RNA sequencing"
        exp_type = self.analyzer._infer_experiment_type(filename, content)
        self.assertEqual(exp_type, "rnaseq")
        
        # Test scRNA-seq detection
        filename = "single_cell_data.h5ad"
        content = "single cell RNA-seq analysis"
        exp_type = self.analyzer._infer_experiment_type(filename, content)
        self.assertEqual(exp_type, "scrna_seq")
    
    def test_data_complexity_assessment(self):
        """Test data complexity assessment."""
        # High complexity (large files, many types)
        high_complexity_files = [
            {'size': 2e9, 'type': 'fastq'},  # 2GB
            {'size': 1e9, 'type': 'bam'},    # 1GB
            {'size': 5e8, 'type': 'vcf'},    # 500MB
            {'size': 1e8, 'type': 'csv'}     # 100MB
        ]
        complexity = self.analyzer._assess_data_complexity(high_complexity_files)
        self.assertEqual(complexity, "high")
        
        # Low complexity
        low_complexity_files = [
            {'size': 1e6, 'type': 'csv'}  # 1MB
        ]
        complexity = self.analyzer._assess_data_complexity(low_complexity_files)
        self.assertEqual(complexity, "low")


class TestTemporalPatternAnalyzer(unittest.TestCase):
    """Test TemporalPatternAnalyzer functionality."""
    
    def setUp(self):
        """Set up test temporal analyzer."""
        self.analyzer = TemporalPatternAnalyzer()
    
    def test_interaction_pace_classification(self):
        """Test interaction pace classification."""
        # Fast pace (< 30 seconds)
        pace = self.analyzer._classify_interaction_pace(20)
        self.assertEqual(pace, "fast")
        
        # Moderate pace (30-120 seconds)
        pace = self.analyzer._classify_interaction_pace(60)
        self.assertEqual(pace, "moderate")
        
        # Slow pace (> 120 seconds)
        pace = self.analyzer._classify_interaction_pace(300)
        self.assertEqual(pace, "slow")
    
    def test_session_stage_determination(self):
        """Test session stage determination."""
        # Initial stage
        stage = self.analyzer._determine_session_stage(3)  # 3 minutes
        self.assertEqual(stage, "initial")
        
        # Exploration stage
        stage = self.analyzer._determine_session_stage(15)  # 15 minutes
        self.assertEqual(stage, "exploration")
        
        # Deep work stage
        stage = self.analyzer._determine_session_stage(90)  # 90 minutes
        self.assertEqual(stage, "deep_work")
    
    def test_productivity_score_calculation(self):
        """Test productivity score calculation."""
        temporal_context = {
            'interaction_times': [datetime.now()],
            'completed_tasks': 3,
            'session_start': datetime.now()
        }
        
        score = self.analyzer._calculate_productivity_score(temporal_context)
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)


def main():
    """Run all static tests."""
    print("Running Static Unit Tests...")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestBiologicalContext,
        TestBiologicalOntologyGraph,
        TestWorkflowPredictionEngine,
        TestContinuousLearningEngine,
        TestDataFileAnalyzer,
        TestTemporalPatternAnalyzer
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("Static Test Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 