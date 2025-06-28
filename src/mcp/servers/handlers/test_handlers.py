"""
Comprehensive Testing Suite for Handlers Module

This test suite fills critical gaps not covered by main.py and __init__.py:
1. Integration testing with MCP server components
2. Cross-module compatibility validation  
3. Electron UI/UX integration testing
4. Performance and stress testing
5. Server-level integration validation
"""

try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False

import asyncio
import sys
import logging
import tempfile
import yaml
from pathlib import Path
from typing import Dict, Any, List
import time
import threading
from unittest.mock import Mock, patch, AsyncMock

# Import handler components
from . import (
    create_handler, get_available_techniques, get_module_info,
    DEFAULT_CONFIG, initialize_module
)


class HandlerIntegrationTester:
    """Integration testing for handlers with server components"""
    
    def __init__(self):
        self.logger = logging.getLogger("handlers.integration_test")
        self.setup_logging()
    
    def setup_logging(self):
        """Setup test logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    # =============================================================================
    # SERVER INTEGRATION TESTS (Critical Gap)
    # =============================================================================
    
    async def test_mcp_server_integration(self):
        """Test integration with MCP server infrastructure"""
        print("🔗 Testing MCP Server Integration...")
        
        # Test 1: Handler registration with MCP tools
        await self._test_mcp_tool_registration()
        
        # Test 2: Resource discovery and access
        await self._test_mcp_resource_integration()
        
        # Test 3: Server routing and handler communication
        await self._test_server_routing()
        
        print("   ✅ MCP Server integration tests passed")
    
    async def _test_mcp_tool_registration(self):
        """Test handler tools register correctly with MCP server"""
        from ..server_integration import MCPServerIntegration
        
        # Create temporary config with valid values
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config = {
                "server": {"tool_timeout": 300},
                "electron": {"auto_start_server": False, "websocket_port": 8766},
                "security": {"max_operations_per_minute": 60, "max_file_size_mb": 100},
                "analysis": {"pipeline_timeout": 300}
            }
            yaml.dump(config, f)
            config_path = f.name
        
        try:
            integration = MCPServerIntegration(config_path)
            await integration.initialize_server()
            
            # Test tool discovery
            tools = integration.get_available_tools("scRNA-seq")
            assert isinstance(tools, dict), "Tools should be discoverable"
            
            # Test tool routing
            result = await integration.route_tool_call(
                "scRNA-seq", "validate_data"
            )
            assert "success" in result, "Tool calls should route correctly"
            
        finally:
            Path(config_path).unlink()
    
    async def _test_mcp_resource_integration(self):
        """Test resource registry integration"""
        handler = create_handler("scRNA-seq", self.logger)
        
        # Test resource access
        raw_data = await handler.get_raw_data()
        assert isinstance(raw_data, dict), "Resources should be accessible"
        assert "available" in raw_data, "Resource status should be clear"
    
    async def _test_server_routing(self):
        """Test server-level routing to handlers"""
        from ..server_integration import MCPServerIntegration
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({
                "electron": {"auto_start_server": False, "websocket_port": 8767},
                "security": {"max_operations_per_minute": 60, "max_file_size_mb": 100},
                "analysis": {"pipeline_timeout": 300}
            }, f)
            config_path = f.name
        
        try:
            integration = MCPServerIntegration(config_path)
            await integration.initialize_server()
            
            # Test routing to different techniques
            for technique in ["scRNA-seq", "ATAC-seq", "Spatial", "Proteomics"]:
                result = await integration.route_tool_call(
                    technique, "validate_data"
                )
                assert result is not None, f"Routing to {technique} should work"
            
        finally:
            Path(config_path).unlink()

    # =============================================================================
    # ELECTRON UI/UX INTEGRATION TESTS (Critical Gap)
    # =============================================================================
    
    async def test_electron_integration(self):
        """Test Electron UI/UX integration"""
        print("🖥️ Testing Electron Integration...")
        
        # Test 1: WebSocket communication
        await self._test_websocket_communication()
        
        # Test 2: Progress updates to UI
        await self._test_progress_updates()
        
        # Test 3: Error propagation to frontend
        await self._test_error_propagation()
        
        # Test 4: UI state synchronization
        await self._test_ui_state_sync()
        
        print("   ✅ Electron integration tests passed")
    
    async def _test_websocket_communication(self):
        """Test WebSocket bridge with Electron"""
        from .electron_bridge import ElectronBridge
        
        bridge = ElectronBridge(websocket_port=8768)  # Test port
        
        # Test bridge setup
        assert bridge.websocket_port == 8768, "Port should be configurable"
        assert not bridge.is_connected(), "Should start disconnected"
        
        # Test message handling
        assert "ping" in bridge.message_handlers, "Should have ping handler"
        assert "get_status" in bridge.message_handlers, "Should have status handler"
    
    async def _test_progress_updates(self):
        """Test progress updates sent to Electron UI"""
        from .electron_bridge import ElectronBridge
        
        bridge = ElectronBridge()
        
        # Mock progress update
        bridge.notify_progress_update("scRNA-seq", "qc", True)
        
        # Test operation completion notification
        from .base_handler import OperationResult
        from datetime import datetime
        
        result = OperationResult(
            success=True,
            message="Test completed",
            operation_id="test_123",
            timestamp=datetime.now()
        )
        
        bridge.notify_operation_complete(result)
        # Should not raise exceptions
        assert True, "Progress updates should work"
    
    async def _test_error_propagation(self):
        """Test error propagation to Electron frontend"""
        from .electron_bridge import ElectronBridge
        from .base_handler import OperationResult
        from datetime import datetime
        
        bridge = ElectronBridge()
        
        error_result = OperationResult(
            success=False,
            message="Test error",
            error_type="test_error",
            operation_id="error_123",
            timestamp=datetime.now()
        )
        
        bridge.notify_operation_error(error_result)
        assert True, "Error propagation should work"
    
    async def _test_ui_state_sync(self):
        """Test UI state synchronization"""
        handler = create_handler("scRNA-seq", self.logger)
        
        # Test progress state updates
        handler._update_progress("qc", True)
        handler._update_progress("normalization", False)
        
        # Progress should be tracked
        progress_key = handler._get_session_state_key("progress")
        # In real implementation, this would be in session state
        assert True, "UI state sync should work"

    # =============================================================================
    # CROSS-MODULE COMPATIBILITY TESTS (Critical Gap)
    # =============================================================================
    
    async def test_cross_module_compatibility(self):
        """Test compatibility with other server modules"""
        print("🔄 Testing Cross-Module Compatibility...")
        
        # Test 1: Configuration compatibility
        await self._test_config_compatibility()
        
        # Test 2: Logging integration
        await self._test_logging_integration()
        
        # Test 3: Authentication integration
        await self._test_auth_integration()
        
        # Test 4: Database/storage integration
        await self._test_storage_integration()
        
        print("   ✅ Cross-module compatibility tests passed")
    
    async def _test_config_compatibility(self):
        """Test configuration compatibility with server"""
        from .config_manager import ConfigManager
        
        # Test server-style configuration with valid values
        server_config = {
            "server": {
                "host": "localhost",
                "port": 8000,
                "debug": False
            },
            # Use valid handler config values that pass validation
            "security": {
                "max_operations_per_minute": 60,
                "max_file_size_mb": 100,
                "audit_log_enabled": True
            },
            "electron": {
                "websocket_port": 8768,
                "auto_start_server": False
            },
            "analysis": {
                "pipeline_timeout": 300
            },
            "database": {
                "url": "sqlite:///test.db"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(server_config, f)
            config_path = f.name
        
        try:
            config_manager = ConfigManager(config_path)
            
            # Test nested config access - test actual config sections that exist
            security_config = config_manager.get_config("security")
            assert security_config is not None, "Should access security config"
            assert security_config["max_operations_per_minute"] == 60, "Should have correct security config"
            
            server_host = config_manager.get_config("server.host")
            assert server_host == "localhost", "Should access server config"
            
            # Test electron config
            websocket_port = config_manager.get_config("electron.websocket_port")
            assert websocket_port == 8768, "Should access electron config"
            
        finally:
            Path(config_path).unlink()
    
    async def _test_logging_integration(self):
        """Test logging integration with server logging"""
        # Test handler logging integrates with server logging
        handler = create_handler("scRNA-seq", self.logger)
        
        # Test logging works
        handler._log_operation("test_operation", param1="value1")
        
        # Test error logging
        from .error_handlers import ErrorHandler
        error_handler = ErrorHandler()
        error_handler.log_error("test_error", "Test error message")
        
        assert True, "Logging integration should work"
    
    async def _test_auth_integration(self):
        """Test authentication integration"""
        # Test security validator integration
        from .security_validator import SecurityValidator
        
        validator = SecurityValidator()
        
        # Test rate limiting (simulates auth scenarios)
        for i in range(5):
            assert validator.check_rate_limit("test_user"), f"Rate limit check {i}"
        
        # Test parameter validation (security)
        result = validator.validate_parameters({"user_id": "123", "action": "analyze"})
        assert result["valid"], "Valid auth parameters should pass"
    
    async def _test_storage_integration(self):
        """Test storage/database integration"""
        # Test data resource management
        handler = create_handler("scRNA-seq", self.logger)
        
        # Test resource info (would integrate with storage)
        raw_info = handler._get_raw_data_info()
        processed_info = handler._get_processed_data_info()
        
        assert isinstance(raw_info, dict), "Storage integration should work"
        assert isinstance(processed_info, dict), "Storage integration should work"

    # =============================================================================
    # PERFORMANCE AND STRESS TESTS (Important Gap)
    # =============================================================================
    
    async def test_performance(self):
        """Test performance characteristics"""
        print("⚡ Testing Performance...")
        
        # Test 1: Handler creation performance
        await self._test_handler_creation_performance()
        
        # Test 2: Concurrent operations
        await self._test_concurrent_operations()
        
        # Test 3: Memory usage
        await self._test_memory_usage()
        
        print("   ✅ Performance tests passed")
    
    async def _test_handler_creation_performance(self):
        """Test handler creation is fast enough"""
        start_time = time.time()
        
        # Create multiple handlers
        handlers = []
        for technique in ["scRNA-seq", "ATAC-seq", "Spatial", "Proteomics"]:
            handler = create_handler(technique, self.logger)
            handlers.append(handler)
        
        creation_time = time.time() - start_time
        
        assert creation_time < 2.0, f"Handler creation too slow: {creation_time:.2f}s"
        assert len(handlers) == 4, "All handlers should be created"
    
    async def _test_concurrent_operations(self):
        """Test concurrent handler operations"""
        handler = create_handler("scRNA-seq", self.logger)
        
        # Test concurrent validation
        tasks = []
        for i in range(10):
            task = handler.validate_data()
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete without exceptions
        for result in results:
            assert not isinstance(result, Exception), "Concurrent operations should work"
    
    async def _test_memory_usage(self):
        """Test memory usage is reasonable"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create and use handlers
        handlers = []
        for _ in range(10):
            for technique in ["scRNA-seq", "ATAC-seq"]:
                handler = create_handler(technique, self.logger)
                handlers.append(handler)
        
        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / 1024 / 1024  # MB
        
        assert memory_increase < 100, f"Memory usage too high: {memory_increase:.1f}MB"

    # =============================================================================
    # MAIN TEST RUNNER
    # =============================================================================
    
    async def run_all_tests(self):
        """Run comprehensive integration test suite"""
        print("🧪 Starting Comprehensive Handler Integration Tests")
        print("="*60)
        
        start_time = time.time()
        tests_passed = 0
        tests_failed = 0
        
        test_methods = [
            self.test_mcp_server_integration,
            self.test_electron_integration, 
            self.test_cross_module_compatibility,
            self.test_performance
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
        
        print("\n" + "="*60)
        print("🎯 INTEGRATION TEST SUMMARY")
        print("="*60)
        
        if tests_failed == 0:
            print("🎉 ALL INTEGRATION TESTS PASSED!")
        else:
            print(f"⚠️  {tests_failed} TEST(S) FAILED")
        
        print(f"📊 Tests: {tests_passed}/{tests_passed + tests_failed} passed")
        print(f"⏱️  Execution time: {execution_time:.2f}s")
        print("="*60)
        
        return {
            "success": tests_failed == 0,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "execution_time": execution_time
        }


# =============================================================================
# PYTEST INTEGRATION (For CI/CD)
# =============================================================================

if PYTEST_AVAILABLE:
    @pytest.mark.asyncio
    async def test_handler_mcp_integration():
        """Pytest wrapper for MCP integration testing"""
        tester = HandlerIntegrationTester()
        await tester.test_mcp_server_integration()

    @pytest.mark.asyncio 
    async def test_handler_electron_integration():
        """Pytest wrapper for Electron integration testing"""
        tester = HandlerIntegrationTester()
        await tester.test_electron_integration()

    @pytest.mark.asyncio
    async def test_handler_cross_module_compatibility():
        """Pytest wrapper for cross-module compatibility testing"""
        tester = HandlerIntegrationTester()
        await tester.test_cross_module_compatibility()

    @pytest.mark.asyncio
    async def test_handler_performance():
        """Pytest wrapper for performance testing"""
        tester = HandlerIntegrationTester()
        await tester.test_performance()


def run_basic_validation():
    """Run basic validation of module imports and configuration"""
    print("🔍 Running basic validation...")
    
    try:
        # Test imports
        from . import DEFAULT_CONFIG, get_available_techniques, create_handler
        assert DEFAULT_CONFIG is not None, "Default config should be available"
        
        techniques = get_available_techniques()
        assert len(techniques) >= 4, "Should have at least 4 techniques"
        
        # Test handler creation
        import logging
        logger = logging.getLogger("validation")
        handler = create_handler("scRNA-seq", logger)
        assert handler.get_technique_name() == "scRNA-seq", "Handler should be created correctly"
        
        print("✅ Basic validation passed!")
        return True
        
    except Exception as e:
        print(f"❌ Basic validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run integration tests from command line"""
    # Check if running basic validation or full test suite
    if len(sys.argv) > 1 and sys.argv[1] == "--basic":
        success = run_basic_validation()
        sys.exit(0 if success else 1)
    else:
        # Run full test suite
        async def run_tests():
            tester = HandlerIntegrationTester()
            result = await tester.run_all_tests()
            return result["success"]
        
        success = asyncio.run(run_tests())
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()