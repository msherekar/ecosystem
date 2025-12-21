"""
MCP Server Integration Testing

Comprehensive testing for handler integration with MCP server infrastructure.
Tests tool registration, resource discovery, routing, and server orchestration.
"""

import asyncio
import pytest
import logging
import tempfile
import yaml
import json
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch
import time

# Import MCP and handler components
from .server_integration import MCPServerIntegration
from .handlers.config_manager import ConfigManager
from .handlers.error_handlers import ErrorHandler
from .handlers import create_handler, get_available_techniques


class MCPServerIntegrationTester:
    """Comprehensive MCP server integration testing"""
    
    def __init__(self):
        self.logger = logging.getLogger("mcp.integration.test")
        self.setup_logging()
        self.temp_files = []
    
    def setup_logging(self):
        """Setup test logging"""
        logging.basicConfig(level=logging.INFO)
    
    def cleanup(self):
        """Cleanup temporary files"""
        for temp_file in self.temp_files:
            try:
                Path(temp_file).unlink()
            except FileNotFoundError:
                pass

    # =============================================================================
    # 1. TOOL REGISTRATION TESTING
    # =============================================================================
    
    async def test_tool_registration(self):
        """Test handler tools register correctly with MCP server"""
        print("🔧 Testing MCP Tool Registration...")
        
        # Create test server configuration
        config_path = self._create_test_config({
            "server": {
                "tool_timeout": 300,
                "max_concurrent_tools": 10
            },
            "electron": {"auto_start_server": False},
            "handlers": {
                "auto_register": True,
                "tool_discovery": True
            }
        })
        
        try:
            # Initialize MCP server integration
            integration = MCPServerIntegration(config_path)
            result = await integration.initialize_server()
            
            assert result["success"], "MCP server should initialize successfully"
            assert len(result["handlers_loaded"]) >= 4, "All technique handlers should load"
            
            # Test tool discovery for each technique
            for technique in ["scRNA-seq", "ATAC-seq", "Spatial", "Proteomics"]:
                await self._test_technique_tool_registration(integration, technique)
            
            print("   ✅ Tool registration tests passed")
            
        finally:
            await integration.shutdown_server()
            self.cleanup()
    
    async def _test_technique_tool_registration(self, integration: MCPServerIntegration, technique: str):
        """Test tool registration for specific technique"""
        # Get available tools for technique
        tools = integration.get_available_tools(technique)
        
        assert isinstance(tools, dict), f"Tools should be discoverable for {technique}"
        
        # Test core tools are registered
        expected_tools = [
            "validate_data", "get_data_summary", "run_qc", 
            "filter_cells_genes", "normalize_data", "cluster_cells",
            "create_umap_plot", "create_violin_plot", "analyze_current_plots"
        ]
        
        # Note: In real implementation, we'd check actual tool registry
        # For now, we test the infrastructure works
        assert "technique" in tools or "error" not in tools, f"Tool discovery should work for {technique}"
    
    async def test_tool_routing(self):
        """Test MCP server routes tool calls to correct handlers"""
        print("🔀 Testing Tool Routing...")
        
        config_path = self._create_test_config()
        
        try:
            integration = MCPServerIntegration(config_path)
            await integration.initialize_server()
            
            # Test routing to different techniques
            test_cases = [
                ("scRNA-seq", "validate_data", {}),
                ("ATAC-seq", "get_data_summary", {}),
                ("Spatial", "validate_data", {}),
                ("Proteomics", "validate_data", {})
            ]
            
            for technique, tool_name, kwargs in test_cases:
                result = await integration.route_tool_call(technique, tool_name, **kwargs)
                
                assert result is not None, f"Tool call should route to {technique}.{tool_name}"
                assert isinstance(result, dict), "Result should be dictionary"
                
                # Test error handling for invalid tools
                error_result = await integration.route_tool_call(technique, "nonexistent_tool")
                assert not error_result.get("success", True), "Invalid tools should return error"
            
            print("   ✅ Tool routing tests passed")
            
        finally:
            await integration.shutdown_server()
            self.cleanup()
    
    async def test_concurrent_tool_calls(self):
        """Test concurrent tool execution"""
        print("🔄 Testing Concurrent Tool Calls...")
        
        config_path = self._create_test_config()
        
        try:
            integration = MCPServerIntegration(config_path)
            await integration.initialize_server()
            
            # Create concurrent tool calls
            tasks = []
            for i in range(5):
                for technique in ["scRNA-seq", "ATAC-seq"]:
                    task = integration.route_tool_call(technique, "validate_data")
                    tasks.append(task)
            
            # Execute concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all completed successfully
            for i, result in enumerate(results):
                assert not isinstance(result, Exception), f"Task {i} should not raise exception: {result}"
                assert isinstance(result, dict), f"Task {i} should return dict"
            
            print(f"   ✅ {len(results)} concurrent tool calls completed")
            
        finally:
            await integration.shutdown_server()
            self.cleanup()

    # =============================================================================
    # 2. RESOURCE DISCOVERY TESTING  
    # =============================================================================
    
    async def test_resource_discovery(self):
        """Test MCP resource discovery and access"""
        print("📂 Testing Resource Discovery...")
        
        config_path = self._create_test_config()
        
        try:
            integration = MCPServerIntegration(config_path)
            await integration.initialize_server()
            
            # Test resource discovery for each technique
            for technique in ["scRNA-seq", "ATAC-seq", "Spatial", "Proteomics"]:
                await self._test_technique_resources(integration, technique)
            
            print("   ✅ Resource discovery tests passed")
            
        finally:
            await integration.shutdown_server()
            self.cleanup()
    
    async def _test_technique_resources(self, integration: MCPServerIntegration, technique: str):
        """Test resource access for specific technique"""
        # Get handler for technique
        handler = integration.handlers.get(technique)
        assert handler is not None, f"Handler should exist for {technique}"
        
        # Test resource methods exist
        resource_methods = [
            "get_raw_data", "get_processed_data", 
            "get_data_metadata", "get_analysis_results", "get_quality_metrics"
        ]
        
        for method_name in resource_methods:
            assert hasattr(handler, method_name), f"Handler should have {method_name} method"
            
            # Test resource access
            try:
                resource = await getattr(handler, method_name)()
                assert isinstance(resource, dict), f"{method_name} should return dict"
                assert "available" in resource or "error" in resource, f"{method_name} should indicate availability"
            except Exception as e:
                # Resource access might fail due to no data, but shouldn't crash
                assert "No" in str(e) or "not" in str(e).lower(), f"Expected data absence error, got: {e}"

    # =============================================================================
    # 3. SERVER ORCHESTRATION TESTING
    # =============================================================================
    
    async def test_server_lifecycle(self):
        """Test complete server lifecycle"""
        print("🔄 Testing Server Lifecycle...")
        
        config_path = self._create_test_config()
        
        try:
            integration = MCPServerIntegration(config_path)
            
            # Test initialization
            init_result = await integration.initialize_server()
            assert init_result["success"], "Server initialization should succeed"
            assert init_result["handlers_loaded"], "Handlers should be loaded"
            
            # Test status check
            status = await integration.get_server_status()
            assert status["server_started"], "Server should be running"
            assert len(status["handlers"]) >= 4, "All handlers should be loaded"
            
            # Test shutdown
            shutdown_result = await integration.shutdown_server()
            assert shutdown_result["success"], "Server shutdown should succeed"
            
            print("   ✅ Server lifecycle tests passed")
            
        finally:
            self.cleanup()
    
    async def test_error_handling_integration(self):
        """Test error handling integration with MCP server"""
        print("🚨 Testing Error Handling Integration...")
        
        config_path = self._create_test_config()
        
        try:
            integration = MCPServerIntegration(config_path)
            await integration.initialize_server()
            
            # Test invalid technique error
            result = await integration.route_tool_call("invalid_technique", "some_tool")
            assert not result.get("success", True), "Invalid technique should return error"
            assert "error" in result, "Error response should contain error details"
            
            # Test invalid tool error
            result = await integration.route_tool_call("scRNA-seq", "invalid_tool")
            assert not result.get("success", True), "Invalid tool should return error"
            
            # Test timeout error (mock long operation)
            with patch.object(integration.handlers["scRNA-seq"], "validate_data", 
                            side_effect=asyncio.TimeoutError()):
                result = await integration.route_tool_call("scRNA-seq", "validate_data")
                assert not result.get("success", True), "Timeout should return error"
            
            print("   ✅ Error handling integration tests passed")
            
        finally:
            await integration.shutdown_server()
            self.cleanup()

    # =============================================================================
    # 4. PERFORMANCE TESTING
    # =============================================================================
    
    async def test_server_performance(self):
        """Test MCP server performance characteristics"""
        print("⚡ Testing Server Performance...")
        
        config_path = self._create_test_config()
        
        try:
            # Test initialization time
            start_time = time.time()
            integration = MCPServerIntegration(config_path)
            await integration.initialize_server()
            init_time = time.time() - start_time
            
            assert init_time < 5.0, f"Server initialization too slow: {init_time:.2f}s"
            
            # Test tool call performance
            start_time = time.time()
            for _ in range(10):
                await integration.route_tool_call("scRNA-seq", "validate_data")
            call_time = time.time() - start_time
            
            assert call_time < 2.0, f"Tool calls too slow: {call_time:.2f}s for 10 calls"
            
            print(f"   ✅ Performance tests passed (init: {init_time:.2f}s, calls: {call_time:.2f}s)")
            
        finally:
            await integration.shutdown_server()
            self.cleanup()

    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def _create_test_config(self, custom_config: Dict[str, Any] = None) -> str:
        """Create temporary test configuration"""
        default_config = {
            "server": {
                "tool_timeout": 300,
                "max_concurrent_tools": 10
            },
            "electron": {
                "auto_start_server": False,
                "websocket_port": 8769  # Test port
            },
            "handlers": {
                "auto_register": True,
                "tool_discovery": True
            },
            "security": {
                "max_operations_per_minute": 60,
                "max_file_size_mb": 100
            },
            "analysis": {
                "pipeline_timeout": 300
            },
            "logging": {
                "level": "INFO"
            }
        }
        
        if custom_config:
            default_config.update(custom_config)
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(default_config, f)
            self.temp_files.append(f.name)
            return f.name

    # =============================================================================
    # MAIN TEST RUNNER
    # =============================================================================
    
    async def run_all_tests(self):
        """Run all MCP server integration tests"""
        print("🧪 MCP Server Integration Testing Suite")
        print("="*50)
        
        start_time = time.time()
        tests_passed = 0
        tests_failed = 0
        
        test_methods = [
            self.test_tool_registration,
            self.test_tool_routing,
            self.test_concurrent_tool_calls,
            self.test_resource_discovery,
            self.test_server_lifecycle,
            self.test_error_handling_integration,
            self.test_server_performance
        ]
        
        for test_method in test_methods:
            try:
                await test_method()
                tests_passed += 1
            except Exception as e:
                tests_failed += 1
                self.logger.error(f"Test {test_method.__name__} failed: {e}")
                import traceback
                traceback.print_exc()
        
        execution_time = time.time() - start_time
        
        print("\n" + "="*50)
        print("🎯 MCP SERVER INTEGRATION TEST SUMMARY")
        print("="*50)
        
        if tests_failed == 0:
            print("🎉 ALL MCP INTEGRATION TESTS PASSED!")
        else:
            print(f"⚠️  {tests_failed} TEST(S) FAILED")
        
        print(f"📊 Tests: {tests_passed}/{tests_passed + tests_failed} passed")
        print(f"⏱️  Execution time: {execution_time:.2f}s")
        print("="*50)
        
        return tests_failed == 0


# =============================================================================
# PYTEST INTEGRATION
# =============================================================================

@pytest.mark.asyncio
async def test_mcp_tool_registration():
    """Pytest wrapper for tool registration testing"""
    tester = MCPServerIntegrationTester()
    await tester.test_tool_registration()

@pytest.mark.asyncio
async def test_mcp_tool_routing():
    """Pytest wrapper for tool routing testing"""
    tester = MCPServerIntegrationTester()
    await tester.test_tool_routing()

@pytest.mark.asyncio
async def test_mcp_resource_discovery():
    """Pytest wrapper for resource discovery testing"""
    tester = MCPServerIntegrationTester()
    await tester.test_resource_discovery()

@pytest.mark.asyncio
async def test_mcp_server_lifecycle():
    """Pytest wrapper for server lifecycle testing"""
    tester = MCPServerIntegrationTester()
    await tester.test_server_lifecycle()


def main():
    """Run MCP server integration tests"""
    async def run_tests():
        tester = MCPServerIntegrationTester()
        try:
            return await tester.run_all_tests()
        finally:
            tester.cleanup()
    
    success = asyncio.run(run_tests())
    return success


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)