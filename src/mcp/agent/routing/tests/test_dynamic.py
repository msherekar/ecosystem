"""
Dynamic Integration Tests for Biological Context Analysis Module

Tests component interactions, async functionality, and end-to-end workflows.
"""

import asyncio
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

import sys
import os

# Use absolute imports from the routing package
from ..biological_context import BiologicalContext
from ..enhanced_context_analyzer import EnhancedBiologicalContextAnalyzer
from ..workflow_predictor import WorkflowPredictionEngine
from ..learning_engine import ContinuousLearningEngine
from ..multimodal_integrator import MultiModalContextIntegrator
from ..file_analyzer import DataFileAnalyzer
from ..temporal_analyzer import TemporalPatternAnalyzer


class TestAsyncFunctionality(unittest.IsolatedAsyncioTestCase):
    """Test async functionality of various components."""
    
    async def test_file_analyzer_async(self):
        """Test async file analysis."""
        analyzer = DataFileAnalyzer()
        
        # Create mock files
        class MockFile:
            def __init__(self, name, size, content):
                self.name = name
                self.size = size
                self.content = content
            
            def read(self, n):
                return self.content.encode('utf-8')
        
        files = [
            MockFile("data.csv", 1000, "gene,sample1,sample2\nGENE1,100,200"),
            MockFile("scrna.h5ad", 50000, "single cell data")
        ]
        
        result = await analyzer.analyze(files)
        self.assertIsInstance(result, dict)
        self.assertIn('file_count', result)
        self.assertEqual(result['file_count'], 2)
    
    async def test_temporal_analyzer_async(self):
        """Test async temporal analysis."""
        analyzer = TemporalPatternAnalyzer()
        
        now = datetime.now()
        temporal_context = {
            'session_start': now - timedelta(minutes=30),
            'interaction_times': [
                now - timedelta(minutes=30),
                now - timedelta(minutes=25),
                now - timedelta(minutes=15),
                now - timedelta(minutes=5)
            ],
            'query_types': ['upload', 'preprocess', 'analyze', 'visualize'],
            'completed_tasks': 2
        }
        
        result = await analyzer.analyze(temporal_context)
        self.assertIsInstance(result, dict)
        self.assertIn('session_duration', result)
        self.assertIn('interaction_pace', result)
    
    async def test_learning_engine_async(self):
        """Test async learning engine functionality."""
        engine = ContinuousLearningEngine()
        
        # Mock context
        context = BiologicalContext(
            primary_domain="transcriptomics",
            secondary_domains=[],
            data_types=["scrna_seq"],
            experimental_design="case_control",
            analysis_objectives=["clustering"],
            workflow_stage="analysis",
            complexity_score=0.7,
            tool_recommendations={"seurat": 0.9},
            integration_requirements={},
            confidence_metrics={"domain": 0.85}
        )
        
        # Test interaction recording
        await engine.record_interaction(
            query="Perform clustering analysis",
            predicted_context=context,
            user_actions=["run seurat clustering"],
            outcome_success=True,
            time_to_completion=300.0
        )
        
        self.assertEqual(len(engine.interaction_buffer), 1)
        self.assertEqual(engine.learning_metrics['total_interactions'], 1)


class TestComponentIntegration(unittest.IsolatedAsyncioTestCase):
    """Test integration between different components."""
    
    async def test_multimodal_integration(self):
        """Test multimodal context integration."""
        integrator = MultiModalContextIntegrator()
        
        # Test with text input
        text_input = "Analyze single-cell RNA-seq data"
        
        # Mock session data
        session_data = {
            'active_tools': ['seurat'],
            'loaded_data': 'scrna_matrix'
        }
        
        result = await integrator.integrate_context(
            text_input=text_input,
            session_data=session_data
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('confidence_score', result)
        self.assertIn('validation_score', result)


def main():
    """Main entry point for dynamic tests."""
    print("Running Dynamic Integration Tests...")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestAsyncFunctionality,
        TestComponentIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("Dynamic Test Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 