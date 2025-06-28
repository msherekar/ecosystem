"""
Enhanced tests for training utilities with performance and security testing.
"""

import unittest
import time
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import (
    EnhancedUserAnonymizer, EnhancedContextExtractor, EnhancedToolUsageExtractor,
    MockSessionProvider, StreamlitSessionProvider, ElectronSessionProvider,
    create_context_extractor, create_user_anonymizer, create_tool_extractor,
    monitor_performance
)

class TestEnhancedUserAnonymizer(unittest.TestCase):
    """Test enhanced user anonymizer with security and performance"""
    
    def setUp(self):
        """Set up test data"""
        self.anonymizer = EnhancedUserAnonymizer(cache_size=100)
    
    def test_enhanced_anonymization(self):
        """Test enhanced anonymization features"""
        user_id = "user@example.com"
        anonymized = self.anonymizer.anonymize_user_id(user_id)
        
        self.assertIsInstance(anonymized, str)
        self.assertTrue(anonymized.startswith("user_"))
        self.assertEqual(len(anonymized), 21)  # "user_" + 16 hex chars
        self.assertNotEqual(anonymized, user_id)
        
        # Same input should give same output (consistency)
        anonymized2 = self.anonymizer.anonymize_user_id(user_id)
        self.assertEqual(anonymized, anonymized2)
    
    def test_caching_behavior(self):
        """Test caching and performance"""
        user_id = "test_user_for_caching"
        
        # First call (should be cached)
        start_time = time.time()
        result1 = self.anonymizer.anonymize_user_id(user_id)
        first_call_time = time.time() - start_time
        
        # Second call (should be from cache, faster)
        start_time = time.time()
        result2 = self.anonymizer.anonymize_user_id(user_id)
        second_call_time = time.time() - start_time
        
        self.assertEqual(result1, result2)
        # Note: Due to @lru_cache, both should be very fast
        self.assertLess(second_call_time, 0.01)  # Should be very quick
    
    def test_cache_management(self):
        """Test cache size management and cleanup"""
        # Fill cache beyond limit
        for i in range(150):  # Exceed cache_size of 100
            self.anonymizer.anonymize_user_id(f"user{i}@example.com")
        
        stats = self.anonymizer.get_anonymization_stats()
        
        # Should have cleaned up old entries - cache may be smaller due to cleanup
        self.assertLessEqual(stats["cache_size"], 100)
        # Access log tracks all attempts, cache only current entries
        self.assertGreaterEqual(stats["total_anonymizations"], 100)
    
    def test_secure_salt_generation(self):
        """Test secure salt generation"""
        anonymizer1 = EnhancedUserAnonymizer()
        anonymizer2 = EnhancedUserAnonymizer()
        
        # Different instances should have different salts
        user_id = "test@example.com"
        result1 = anonymizer1.anonymize_user_id(user_id)
        result2 = anonymizer2.anonymize_user_id(user_id)
        
        self.assertNotEqual(result1, result2)
    
    def test_session_id_generation(self):
        """Test enhanced session ID generation"""
        session_id1 = self.anonymizer.generate_session_id()
        session_id2 = self.anonymizer.generate_session_id()
        
        self.assertNotEqual(session_id1, session_id2)
        self.assertEqual(len(session_id1), 16)
        self.assertEqual(len(session_id2), 16)
        
        # Test with custom data
        custom_id = self.anonymizer.generate_session_id("custom_data")
        same_custom_id = self.anonymizer.generate_session_id("custom_data")
        self.assertEqual(custom_id, same_custom_id)
    
    def test_anonymization_statistics(self):
        """Test anonymization statistics tracking"""
        # Generate some activity
        for i in range(10):
            self.anonymizer.anonymize_user_id(f"user{i}@test.com")
        
        stats = self.anonymizer.get_anonymization_stats()
        
        self.assertIn("cache_size", stats)
        self.assertIn("max_cache_size", stats)
        self.assertIn("total_anonymizations", stats)
        self.assertIn("recent_activity", stats)
        
        self.assertEqual(stats["total_anonymizations"], 10)
        self.assertEqual(stats["max_cache_size"], 100)
        self.assertGreaterEqual(stats["recent_activity"], 10)

class TestEnhancedContextExtractor(unittest.TestCase):
    """Test enhanced context extractor with caching and validation"""
    
    def setUp(self):
        """Set up test environment"""
        # Create comprehensive mock session data
        self.session_data = {
            "qc_done": True,
            "filtering_done": False,
            "normalization_done": True,
            "scrna_current_step": "normalization",
            "n_top_genes": 2000,
            "min_genes": 200,
            "target_sum": 10000,
            "analysis_started": True,
            "last_operation": "normalize_data",
            "operation_timestamp": datetime.now().isoformat(),
            "theme": "dark",
            "auto_save": True,
            "notifications_enabled": True
        }
        
        # Create mock AnnData object
        self.mock_anndata = Mock()
        self.mock_anndata.n_obs = 1000
        self.mock_anndata.n_vars = 2000
        self.mock_anndata.raw = None
        
        self.session_data["anndata"] = self.mock_anndata
        
        self.session_provider = MockSessionProvider(self.session_data)
        self.extractor = EnhancedContextExtractor(self.session_provider)
    
    def test_comprehensive_context_extraction(self):
        """Test comprehensive context extraction"""
        context = self.extractor.extract_analysis_context()
        
        # Check all major sections are present
        expected_sections = [
            "analysis_state", "available_tools", "pipeline_progress",
            "data_characteristics", "user_preferences", "system_state",
            "current_step", "analysis_params"
        ]
        
        for section in expected_sections:
            self.assertIn(section, context)
        
        # Check specific content
        self.assertEqual(context["current_step"], "normalization")
        self.assertTrue(context["pipeline_progress"]["qc_done"])
        self.assertFalse(context["pipeline_progress"]["filtering_done"])
        self.assertEqual(context["data_characteristics"]["n_cells"], 1000)
        self.assertEqual(context["data_characteristics"]["n_genes"], 2000)
        self.assertEqual(context["analysis_params"]["n_top_genes"], 2000)
    
    def test_context_caching(self):
        """Test context extraction caching"""
        # First call
        start_time = time.time()
        context1 = self.extractor.extract_analysis_context(use_cache=False)
        first_time = time.time() - start_time
        
        # Second call with cache
        start_time = time.time()
        context2 = self.extractor.extract_analysis_context(use_cache=True)
        cached_time = time.time() - start_time
        
        # Results should be identical
        self.assertEqual(context1, context2)
        
        # Cached call should be faster
        self.assertLess(cached_time, first_time)
    
    def test_analysis_type_determination(self):
        """Test enhanced analysis type determination"""
        # Test with AnnData - should return scrna_seq since AnnData is typically single-cell
        analysis_type = self.extractor.determine_analysis_type()
        self.assertEqual(analysis_type, "scrna_seq")
        
        # Test with DataFrame (no AnnData)
        self.session_provider.set("anndata", None)
        self.extractor.clear_cache()  # Clear cache to re-determine
        mock_df = Mock()
        mock_df.columns = ["Gene1", "Gene2", "ENSEMBL_ID"]
        self.session_provider.set("uploaded_df", mock_df)
        
        analysis_type = self.extractor.determine_analysis_type()
        self.assertEqual(analysis_type, "rna_seq")
        
        # Test with proteomics data
        mock_df.columns = ["Protein1", "Peptide_Intensity"]
        self.extractor.clear_cache()  # Clear cache to re-determine  
        analysis_type = self.extractor.determine_analysis_type()
        self.assertEqual(analysis_type, "proteomics")
    
    def test_parameter_validation(self):
        """Test analysis parameter validation"""
        # Test with valid parameters
        context = self.extractor.extract_analysis_context()
        params = context["analysis_params"]
        
        self.assertEqual(params["n_top_genes"], 2000)
        self.assertEqual(params["min_genes"], 200)
        
        # Test with invalid parameters
        self.session_provider.set("n_top_genes", "invalid")
        self.session_provider.set("min_genes", -10)  # Out of range
        
        self.extractor.clear_cache()  # Clear cache to re-extract
        context = self.extractor.extract_analysis_context()
        params = context["analysis_params"]
        
        # Should use defaults for invalid values
        self.assertEqual(params["n_top_genes"], 2000)  # Default
        self.assertEqual(params["min_genes"], 200)     # Default (out of range)
    
    def test_data_quality_metrics(self):
        """Test data quality metrics calculation"""
        context = self.extractor.extract_analysis_context()
        quality_metrics = context["data_characteristics"]["quality_metrics"]
        
        self.assertIsInstance(quality_metrics, dict)
        # More specific tests would require actual data
    
    def test_system_state_extraction(self):
        """Test system state information extraction"""
        context = self.extractor.extract_analysis_context()
        system_state = context["system_state"]
        
        self.assertIn("memory_usage", system_state)
        self.assertIn("active_sessions", system_state)
        self.assertIn("system_health", system_state)
        self.assertEqual(system_state["system_health"], "healthy")
    
    def test_cache_invalidation(self):
        """Test cache invalidation and TTL"""
        # Get initial context
        context1 = self.extractor.extract_analysis_context()
        
        # Wait for cache TTL (simulate time passage)
        self.extractor._cache_ttl = timedelta(seconds=0.1)
        time.sleep(0.2)
        
        # Should re-extract due to TTL expiration
        context2 = self.extractor.extract_analysis_context()
        
        # Main structure should be the same (ignore small variations in memory usage)
        self.assertEqual(context1.keys(), context2.keys())
        
        # Check that core data is consistent
        self.assertEqual(context1["analysis_params"], context2["analysis_params"])
        self.assertEqual(context1["pipeline_progress"], context2["pipeline_progress"])
        
        # Memory usage may vary slightly, so just check it's present
        self.assertIn("memory_usage", context1["system_state"])
        self.assertIn("memory_usage", context2["system_state"])
    
    def test_no_session_provider(self):
        """Test behavior without session provider"""
        extractor = EnhancedContextExtractor(None)
        
        context = extractor.extract_analysis_context()
        self.assertEqual(context, {})
        
        analysis_type = extractor.determine_analysis_type()
        self.assertEqual(analysis_type, "general")

class TestEnhancedToolUsageExtractor(unittest.TestCase):
    """Test enhanced tool usage extraction with performance monitoring"""
    
    def setUp(self):
        """Set up test data"""
        self.extractor = EnhancedToolUsageExtractor()
    
    def test_enhanced_tool_extraction(self):
        """Test enhanced tool usage extraction"""
        tool_results = [
            "Tool scanpy: Successfully normalized data in 1.23s",
            "Tool matplotlib: Created plot in 500ms",
            "Tool pandas: Failed to process data due to memory error"
        ]
        
        tools = self.extractor.extract_tools_used(tool_results)
        
        self.assertEqual(len(tools), 3)
        
        # Check scanpy tool
        scanpy_tool = tools[0]
        self.assertEqual(scanpy_tool["name"], "scanpy")
        self.assertEqual(scanpy_tool["category"], "data_processing")
        self.assertTrue(scanpy_tool["success"])
        self.assertEqual(scanpy_tool["execution_time_ms"], 1230)
        self.assertGreater(scanpy_tool["performance_score"], 0)
        
        # Check matplotlib tool
        matplotlib_tool = tools[1]
        self.assertEqual(matplotlib_tool["name"], "matplotlib")
        self.assertEqual(matplotlib_tool["category"], "visualization")
        self.assertEqual(matplotlib_tool["execution_time_ms"], 500)
        
        # Check pandas tool (failed)
        pandas_tool = tools[2]
        self.assertEqual(pandas_tool["name"], "pandas")
        self.assertFalse(pandas_tool["success"])
        self.assertTrue(pandas_tool["has_error"])
    
    def test_tool_categorization(self):
        """Test tool categorization"""
        test_cases = [
            ("scanpy", "data_processing"),
            ("matplotlib", "visualization"),
            ("sklearn", "analysis"),
            ("h5py", "io"),
            ("unknown_tool", "other")
        ]
        
        for tool_name, expected_category in test_cases:
            category = self.extractor._categorize_tool(tool_name)
            self.assertEqual(category, expected_category)
    
    def test_execution_time_extraction(self):
        """Test execution time extraction from various formats"""
        test_cases = [
            ("completed in 1.23s", 1230),
            ("took 500ms", 500),
            ("execution time: 2.5s", 2500),
            ("finished in 100ms", 100),
            ("no time information", None)
        ]
        
        for output, expected_time in test_cases:
            extracted_time = self.extractor._extract_execution_time(output)
            self.assertEqual(extracted_time, expected_time)
    
    def test_performance_tracking(self):
        """Test performance tracking and scoring"""
        # Run same tool multiple times to build history
        tool_results = [
            f"Tool test_tool: Completed in {i * 100}ms"
            for i in range(1, 6)  # 100ms, 200ms, 300ms, 400ms, 500ms
        ]
        
        tools = self.extractor.extract_tools_used(tool_results)
        
        # Check that performance is being tracked
        self.assertEqual(len(tools), 5)
        
        # Get performance stats
        stats = self.extractor.get_tool_performance_stats()
        self.assertIn("test_tool", stats)
        
        tool_stats = stats["test_tool"]
        self.assertEqual(tool_stats["usage_count"], 5)
        self.assertEqual(tool_stats["average_time_ms"], 300)  # (100+200+300+400+500)/5
        self.assertEqual(tool_stats["min_time_ms"], 100)
        self.assertEqual(tool_stats["max_time_ms"], 500)
        self.assertGreaterEqual(tool_stats["reliability_score"], 0)
    
    def test_performance_score_calculation(self):
        """Test performance score calculation logic"""
        # Test with no history (new tool)
        score = self.extractor._calculate_performance_score("new_tool", 500)
        self.assertEqual(score, 0.9)  # Fast execution (< 1 second)
        
        score = self.extractor._calculate_performance_score("new_tool", 3000)
        self.assertEqual(score, 0.7)  # Good execution (1-5 seconds)
        
        score = self.extractor._calculate_performance_score("new_tool", 10000)
        self.assertEqual(score, 0.5)  # Moderate execution (5-30 seconds)
        
        score = self.extractor._calculate_performance_score("new_tool", 60000)
        self.assertEqual(score, 0.3)  # Slow execution (> 30 seconds)
        
        # Build history for a tool
        self.extractor._tool_performance["existing_tool"] = [1000, 1200, 800, 1100, 900]  # avg = 1000
        
        # Test with good performance (below average)
        score = self.extractor._calculate_performance_score("existing_tool", 800)
        self.assertEqual(score, 1.0)  # Excellent (80% of average)
        
        # Test with poor performance (above average)
        score = self.extractor._calculate_performance_score("existing_tool", 3000)
        self.assertEqual(score, 0.3)  # Poor (3x average)
    
    def test_empty_tool_results(self):
        """Test handling of empty and invalid tool results"""
        # Test empty list
        tools = self.extractor.extract_tools_used([])
        self.assertEqual(tools, [])
        
        # Test invalid formats
        invalid_results = [
            "Not a tool result",
            "Tool without colon",
            "",
            "Tool : empty name"
        ]
        
        tools = self.extractor.extract_tools_used(invalid_results)
        self.assertEqual(len(tools), 1)  # Only the empty name one should parse
        self.assertEqual(tools[0]["name"], "")

class TestSessionProviders(unittest.TestCase):
    """Test various session providers"""
    
    def test_enhanced_mock_session_provider(self):
        """Test enhanced mock session provider with logging"""
        provider = MockSessionProvider({
            "initial_key": "initial_value"
        })
        
        # Test get with logging
        value = provider.get("initial_key")
        self.assertEqual(value, "initial_value")
        self.assertEqual(len(provider.access_log), 1)
        
        # Test set with logging
        provider.set("new_key", "new_value")
        self.assertEqual(len(provider.change_log), 1)
        self.assertEqual(provider.change_log[0]["action"], "set")
        
        # Test delete with logging
        provider.delete("new_key")
        self.assertEqual(len(provider.change_log), 2)
        self.assertEqual(provider.change_log[1]["action"], "delete")
        
        # Test clear with logging
        provider.clear()
        self.assertEqual(len(provider.change_log), 3)
        self.assertEqual(provider.change_log[2]["action"], "clear")
        
        # Test access statistics
        stats = provider.get_access_stats()
        self.assertIn("total_accesses", stats)
        self.assertIn("total_changes", stats)
        self.assertIn("most_accessed_keys", stats)
        self.assertIn("recent_activity", stats)
    
    def test_electron_session_provider(self):
        """Test Electron session provider with IPC simulation"""
        # Mock IPC handler
        mock_ipc = Mock()
        provider = ElectronSessionProvider(mock_ipc)
        
        # Test get with IPC notification
        provider.set("test_key", "test_value")
        value = provider.get("test_key")
        
        self.assertEqual(value, "test_value")
        mock_ipc.send.assert_called()
        
        # Test change listeners
        listener_called = False
        listener_args = None
        
        def test_listener(key, new_value, old_value):
            nonlocal listener_called, listener_args
            listener_called = True
            listener_args = (key, new_value, old_value)
        
        provider.add_change_listener(test_listener)
        provider.set("listener_test", "new_value")
        
        self.assertTrue(listener_called)
        self.assertEqual(listener_args[0], "listener_test")
        self.assertEqual(listener_args[1], "new_value")
        
        # Test listener removal
        provider.remove_change_listener(test_listener)
        listener_called = False
        provider.set("no_listener", "value")
        self.assertFalse(listener_called)
    
    def test_streamlit_session_provider_caching(self):
        """Test Streamlit session provider with caching"""
        # Mock Streamlit session state
        mock_session_state = Mock()
        mock_session_state.test_key = "test_value"
        
        provider = StreamlitSessionProvider(mock_session_state)
        
        # First get (should access session state)
        value1 = provider.get("test_key")
        self.assertEqual(value1, "test_value")
        
        # Second get (should use cache)
        value2 = provider.get("test_key")
        self.assertEqual(value2, "test_value")
        
        # Test cache invalidation
        provider._cache_ttl = timedelta(seconds=0.1)
        time.sleep(0.2)
        
        # Should re-access session state after TTL
        value3 = provider.get("test_key")
        self.assertEqual(value3, "test_value")

class TestFactoryFunctions(unittest.TestCase):
    """Test factory functions and utilities"""
    
    def test_enhanced_factory_functions(self):
        """Test enhanced factory functions"""
        # Test context extractor factory
        session_provider = MockSessionProvider({"test": "data"})
        extractor = create_context_extractor(session_provider)
        
        self.assertIsInstance(extractor, EnhancedContextExtractor)
        self.assertEqual(extractor.session_provider, session_provider)
        
        # Test without session provider
        extractor_no_session = create_context_extractor()
        self.assertIsInstance(extractor_no_session, EnhancedContextExtractor)
        self.assertIsNone(extractor_no_session.session_provider)
        
        # Test user anonymizer factory
        anonymizer = create_user_anonymizer("custom_salt", 500)
        self.assertIsInstance(anonymizer, EnhancedUserAnonymizer)
        self.assertEqual(anonymizer.salt, "custom_salt")
        self.assertEqual(anonymizer._cache_size, 500)
        
        # Test tool extractor factory
        tool_extractor = create_tool_extractor()
        self.assertIsInstance(tool_extractor, EnhancedToolUsageExtractor)
    
    def test_performance_monitoring_decorator(self):
        """Test performance monitoring decorator"""
        
        @monitor_performance
        def sync_test_function(delay=0.1):
            time.sleep(delay)
            return "sync_result"
        
        @monitor_performance
        async def async_test_function(delay=0.1):
            await asyncio.sleep(delay)
            return "async_result"
        
        # Test sync function
        with patch('logging.getLogger') as mock_logger:
            result = sync_test_function(0.05)
            self.assertEqual(result, "sync_result")
            mock_logger.assert_called_with("performance")
        
        # Test async function
        async def test_async():
            with patch('logging.getLogger') as mock_logger:
                result = await async_test_function(0.05)
                self.assertEqual(result, "async_result")
                mock_logger.assert_called_with("performance")
        
        asyncio.run(test_async())
    
    def test_performance_monitoring_with_errors(self):
        """Test performance monitoring with error handling"""
        
        @monitor_performance
        def failing_function():
            raise ValueError("Test error")
        
        with patch('logging.getLogger') as mock_logger:
            with self.assertRaises(ValueError):
                failing_function()
            
            # Should still log the error with timing
            mock_logger.assert_called_with("performance")

class TestIntegrationScenarios(unittest.TestCase):
    """Test integration scenarios between utilities"""
    
    def test_complete_workflow_integration(self):
        """Test complete workflow using all enhanced utilities"""
        # Setup
        session_data = {
            "anndata": Mock(n_obs=5000, n_vars=3000),
            "qc_done": True,
            "scrna_current_step": "clustering",
            "n_top_genes": 2500,
            "analysis_started": True
        }
        
        session_provider = MockSessionProvider(session_data)
        anonymizer = create_user_anonymizer()
        context_extractor = create_context_extractor(session_provider)
        tool_extractor = create_tool_extractor()
        
        # Simulate workflow
        user_id = "scientist@university.edu"
        anonymized_id = anonymizer.anonymize_user_id(user_id)
        session_id = anonymizer.generate_session_id()
        
        context = context_extractor.extract_analysis_context()
        analysis_type = context_extractor.determine_analysis_type()
        
        tool_results = [
            "Tool scanpy: Clustering completed in 2.1s",
            "Tool matplotlib: Generated UMAP plot in 800ms"
        ]
        tools_used = tool_extractor.extract_tools_used(tool_results)
        
        # Verify integration
        self.assertNotEqual(anonymized_id, user_id)
        self.assertEqual(analysis_type, "scrna_seq")
        self.assertIn("data_characteristics", context)
        self.assertEqual(len(tools_used), 2)
        
        # Check data consistency
        self.assertEqual(context["data_characteristics"]["n_cells"], 5000)
        self.assertEqual(context["current_step"], "clustering")
        self.assertTrue(context["pipeline_progress"]["qc_done"])
        
        # Check tool performance tracking
        performance_stats = tool_extractor.get_tool_performance_stats()
        self.assertIn("scanpy", performance_stats)
        self.assertIn("matplotlib", performance_stats)
    
    def test_performance_under_load(self):
        """Test performance under simulated load"""
        anonymizer = create_user_anonymizer(cache_size=1000)
        session_provider = MockSessionProvider()
        context_extractor = create_context_extractor(session_provider)
        tool_extractor = create_tool_extractor()
        
        # Simulate load
        start_time = time.time()
        
        for i in range(100):
            # Anonymize users
            user_id = f"user{i}@test.com"
            anonymized = anonymizer.anonymize_user_id(user_id)
            
            # Extract context
            session_provider.set("current_iteration", i)
            context = context_extractor.extract_analysis_context()
            
            # Process tools
            tool_results = [f"Tool test{i % 3}: Completed in {100 + i}ms"]
            tools = tool_extractor.extract_tools_used(tool_results)
        
        total_time = time.time() - start_time
        
        # Performance assertions
        self.assertLess(total_time, 5.0)  # Should complete in under 5 seconds
        
        # Verify data integrity under load
        stats = anonymizer.get_anonymization_stats()
        self.assertEqual(stats["total_anonymizations"], 100)
        
        tool_stats = tool_extractor.get_tool_performance_stats()
        self.assertGreater(len(tool_stats), 0)
    
    def test_error_handling_integration(self):
        """Test error handling across utilities"""
        # Test with invalid session data
        corrupted_session = MockSessionProvider({
            "n_top_genes": "invalid_number",
            "anndata": "not_an_anndata_object"
        })
        
        context_extractor = create_context_extractor(corrupted_session)
        
        # Should handle errors gracefully
        context = context_extractor.extract_analysis_context()
        self.assertIsInstance(context, dict)
        
        # Test with malformed tool results
        tool_extractor = create_tool_extractor()
        malformed_results = [
            "Not a proper tool result",
            "Tool : missing name",
            None,  # This should be handled gracefully
        ]
        
        # Should not crash on malformed input
        tools = tool_extractor.extract_tools_used(malformed_results)
        self.assertIsInstance(tools, list)
    
    def test_memory_efficiency(self):
        """Test memory efficiency of utilities"""
        import sys
        
        # Test anonymizer memory usage
        anonymizer = create_user_anonymizer(cache_size=10)
        
        initial_size = sys.getsizeof(anonymizer)
        
        # Generate many anonymizations
        for i in range(100):
            anonymizer.anonymize_user_id(f"user{i}@test.com")
        
        final_size = sys.getsizeof(anonymizer)
        
        # Memory usage should not grow excessively due to cache management
        memory_growth = final_size - initial_size
        self.assertLess(memory_growth, 10000)  # Less than 10KB growth
        
        # Test context extractor cache
        session_provider = MockSessionProvider()
        extractor = create_context_extractor(session_provider)
        
        # Multiple extractions should use cache efficiently
        for i in range(50):
            session_provider.set("iteration", i)
            context = extractor.extract_analysis_context()
        
        # Cache should be bounded
        self.assertLessEqual(len(extractor._context_cache), 10)

if __name__ == "__main__":
    def main():
        """Run all enhanced utility tests"""
        unittest.main(verbosity=2)
    
    main()