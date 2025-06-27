"""
Tests for training utilities.
"""

import unittest
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import (
    UserAnonymizer, ContextExtractor, ToolUsageExtractor,
    MockSessionProvider, StreamlitSessionProvider,
    create_context_extractor, create_user_anonymizer
)

class TestUserAnonymizer(unittest.TestCase):
    """Test UserAnonymizer class"""
    
    def setUp(self):
        """Set up test data"""
        self.anonymizer = UserAnonymizer()
    
    def test_anonymize_user_id(self):
        """Test user ID anonymization"""
        user_id = "user@example.com"
        anonymized = self.anonymizer.anonymize_user_id(user_id)
        
        self.assertIsInstance(anonymized, str)
        self.assertEqual(len(anonymized), 16)
        self.assertNotEqual(anonymized, user_id)
        
        # Same input should give same output
        anonymized2 = self.anonymizer.anonymize_user_id(user_id)
        self.assertEqual(anonymized, anonymized2)
    
    def test_anonymize_empty_user_id(self):
        """Test anonymization of empty user ID"""
        result = self.anonymizer.anonymize_user_id("")
        self.assertEqual(result, "anonymous")
        
        result = self.anonymizer.anonymize_user_id(None)
        self.assertEqual(result, "anonymous")
    
    def test_custom_salt(self):
        """Test anonymization with custom salt"""
        anonymizer1 = UserAnonymizer("salt1")
        anonymizer2 = UserAnonymizer("salt2")
        
        user_id = "test@example.com"
        result1 = anonymizer1.anonymize_user_id(user_id)
        result2 = anonymizer2.anonymize_user_id(user_id)
        
        self.assertNotEqual(result1, result2)
    
    def test_generate_session_id(self):
        """Test session ID generation"""
        session_id = self.anonymizer.generate_session_id()
        
        self.assertIsInstance(session_id, str)
        self.assertEqual(len(session_id), 12)
        
        # Should generate different IDs
        session_id2 = self.anonymizer.generate_session_id()
        self.assertNotEqual(session_id, session_id2)
    
    def test_generate_session_id_with_data(self):
        """Test session ID generation with custom data"""
        data = "custom_session_data"
        session_id1 = self.anonymizer.generate_session_id(data)
        session_id2 = self.anonymizer.generate_session_id(data)
        
        # Same data should give same session ID
        self.assertEqual(session_id1, session_id2)

class TestMockSessionProvider(unittest.TestCase):
    """Test MockSessionProvider class"""
    
    def setUp(self):
        """Set up test data"""
        self.session_data = {
            "qc_done": True,
            "filtering_done": False,
            "n_top_genes": 2000
        }
        self.provider = MockSessionProvider(self.session_data)
    
    def test_get_existing_key(self):
        """Test getting existing key"""
        self.assertTrue(self.provider.get("qc_done"))
        self.assertFalse(self.provider.get("filtering_done"))
        self.assertEqual(self.provider.get("n_top_genes"), 2000)
    
    def test_get_non_existing_key(self):
        """Test getting non-existing key"""
        self.assertIsNone(self.provider.get("non_existing"))
        self.assertEqual(self.provider.get("non_existing", "default"), "default")
    
    def test_set_value(self):
        """Test setting value"""
        self.provider.set("new_key", "new_value")
        self.assertEqual(self.provider.get("new_key"), "new_value")
        
        # Update existing key
        self.provider.set("qc_done", False)
        self.assertFalse(self.provider.get("qc_done"))
    
    def test_empty_provider(self):
        """Test provider with no initial data"""
        empty_provider = MockSessionProvider()
        self.assertIsNone(empty_provider.get("any_key"))
        
        empty_provider.set("test", "value")
        self.assertEqual(empty_provider.get("test"), "value")

class TestContextExtractor(unittest.TestCase):
    """Test ContextExtractor class"""
    
    def setUp(self):
        """Set up test data"""
        # Create mock session with bioinformatics data
        self.session_data = {
            "qc_done": True,
            "filtering_done": False,
            "normalization_done": True,
            "scrna_current_step": "normalization",
            "n_top_genes": 2000,
            "min_genes": 200,
            "target_sum": 10000
        }
        self.session_provider = MockSessionProvider(self.session_data)
        self.extractor = ContextExtractor(self.session_provider)
    
    def test_extract_analysis_context(self):
        """Test analysis context extraction"""
        context = self.extractor.extract_analysis_context()
        
        self.assertIsInstance(context, dict)
        self.assertIn("analysis_state", context)
        self.assertIn("available_tools", context)
        self.assertIn("pipeline_progress", context)
        self.assertIn("data_characteristics", context)
        self.assertIn("current_step", context)
        self.assertIn("analysis_params", context)
    
    def test_pipeline_progress_extraction(self):
        """Test pipeline progress extraction"""
        context = self.extractor.extract_analysis_context()
        pipeline_progress = context["pipeline_progress"]
        
        self.assertTrue(pipeline_progress["qc_done"])
        self.assertFalse(pipeline_progress["filtering_done"])
        self.assertTrue(pipeline_progress["normalization_done"])
        self.assertFalse(pipeline_progress["dimred_done"])  # Default False
    
    def test_current_step_extraction(self):
        """Test current step extraction"""
        context = self.extractor.extract_analysis_context()
        self.assertEqual(context["current_step"], "normalization")
    
    def test_analysis_parameters_extraction(self):
        """Test analysis parameters extraction"""
        context = self.extractor.extract_analysis_context()
        params = context["analysis_params"]
        
        self.assertEqual(params["n_top_genes"], 2000)
        self.assertEqual(params["min_genes"], 200)
        self.assertEqual(params["target_sum"], 10000)
    
    def test_determine_analysis_type(self):
        """Test analysis type determination"""
        # Test with no specific data
        analysis_type = self.extractor.determine_analysis_type()
        self.assertEqual(analysis_type, "general")
        
        # Test with anndata
        self.session_provider.set("anndata", "mock_anndata")
        analysis_type = self.extractor.determine_analysis_type()
        self.assertEqual(analysis_type, "scrna_seq")
        
        # Test with tabular data
        self.session_provider.set("anndata", None)
        self.session_provider.set("uploaded_df", "mock_dataframe")
        analysis_type = self.extractor.determine_analysis_type()
        self.assertEqual(analysis_type, "tabular")
        
        # Test with RNA-seq data
        self.session_provider.set("uploaded_df", None)
        self.session_provider.set("rna_seq_data", "mock_rna_data")
        analysis_type = self.extractor.determine_analysis_type()
        self.assertEqual(analysis_type, "rna_seq")
    
    def test_no_session_provider(self):
        """Test extractor without session provider"""
        extractor = ContextExtractor(None)
        
        context = extractor.extract_analysis_context()
        self.assertEqual(context, {})
        
        analysis_type = extractor.determine_analysis_type()
        self.assertEqual(analysis_type, "general")

class TestToolUsageExtractor(unittest.TestCase):
    """Test ToolUsageExtractor class"""
    
    def setUp(self):
        """Set up test data"""
        self.extractor = ToolUsageExtractor()
    
    def test_extract_tools_used(self):
        """Test tool usage extraction"""
        tool_results = [
            "Tool scanpy: Successfully normalized data",
            "Tool matplotlib: Created plot successfully",
            "Tool pandas: Failed to process data"
        ]
        
        tools = self.extractor.extract_tools_used(tool_results)
        
        self.assertEqual(len(tools), 3)
        
        # Check scanpy tool
        scanpy_tool = tools[0]
        self.assertEqual(scanpy_tool["name"], "scanpy")
        self.assertTrue(scanpy_tool["success"])
        self.assertFalse(scanpy_tool["has_error"])
        
        # Check matplotlib tool
        matplotlib_tool = tools[1]
        self.assertEqual(matplotlib_tool["name"], "matplotlib")
        self.assertTrue(matplotlib_tool["success"])
        
        # Check pandas tool (failed)
        pandas_tool = tools[2]
        self.assertEqual(pandas_tool["name"], "pandas")
        self.assertFalse(pandas_tool["success"])
        self.assertTrue(pandas_tool["has_error"])
    
    def test_extract_tools_empty_results(self):
        """Test extraction with empty results"""
        tools = self.extractor.extract_tools_used([])
        self.assertEqual(tools, [])
        
        tools = self.extractor.extract_tools_used(None)
        self.assertEqual(tools, [])
    
    def test_extract_tools_invalid_format(self):
        """Test extraction with invalid format"""
        tool_results = [
            "Not a tool result",
            "Tool without colon",
            "Tool scanpy: Valid result"
        ]
        
        tools = self.extractor.extract_tools_used(tool_results)
        
        # Should only extract the valid one
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["name"], "scanpy")
    
    def test_parse_tool_result(self):
        """Test individual tool result parsing"""
        # Valid result
        result = "Tool scanpy: Successfully processed data"
        parsed = self.extractor._parse_tool_result(result)
        
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["name"], "scanpy")
        self.assertTrue(parsed["success"])
        self.assertGreater(parsed["output_length"], 0)
        
        # Invalid result
        invalid_result = "Not a tool result"
        parsed = self.extractor._parse_tool_result(invalid_result)
        self.assertIsNone(parsed)

class TestFactoryFunctions(unittest.TestCase):
    """Test factory functions"""
    
    def test_create_context_extractor(self):
        """Test context extractor factory"""
        session_provider = MockSessionProvider({"test": "data"})
        extractor = create_context_extractor(session_provider)
        
        self.assertIsInstance(extractor, ContextExtractor)
        self.assertEqual(extractor.session_provider, session_provider)
        
        # Test without session provider
        extractor_no_session = create_context_extractor()
        self.assertIsInstance(extractor_no_session, ContextExtractor)
        self.assertIsNone(extractor_no_session.session_provider)
    
    def test_create_user_anonymizer(self):
        """Test user anonymizer factory"""
        anonymizer = create_user_anonymizer("custom_salt")
        
        self.assertIsInstance(anonymizer, UserAnonymizer)
        self.assertEqual(anonymizer.salt, "custom_salt")
        
        # Test without salt
        anonymizer_default = create_user_anonymizer()
        self.assertIsInstance(anonymizer_default, UserAnonymizer)

class TestStreamlitSessionProvider(unittest.TestCase):
    """Test StreamlitSessionProvider class"""
    
    def setUp(self):
        """Set up test data"""
        # Mock streamlit session state
        class MockStreamlitSession:
            def __init__(self):
                self.qc_done = True
                self.filtering_done = False
        
        self.mock_session = MockStreamlitSession()
        self.provider = StreamlitSessionProvider(self.mock_session)
    
    def test_get_existing_attribute(self):
        """Test getting existing attribute"""
        self.assertTrue(self.provider.get("qc_done"))
        self.assertFalse(self.provider.get("filtering_done"))
    
    def test_get_non_existing_attribute(self):
        """Test getting non-existing attribute"""
        self.assertIsNone(self.provider.get("non_existing"))
        self.assertEqual(self.provider.get("non_existing", "default"), "default")
    
    def test_set_attribute(self):
        """Test setting attribute"""
        self.provider.set("new_attr", "new_value")
        self.assertEqual(getattr(self.mock_session, "new_attr"), "new_value")

if __name__ == "__main__":
    unittest.main(verbosity=2) 