"""
Handlers Module Main Entry Point

Primary orchestration point for the modular handler system.
Provides comprehensive testing, validation, and demonstration of all handler components.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, List
import traceback

# Import all handler components
from . import (
    # Core components
    BaseHandler, OperationResult, SecurityValidator, ElectronBridge,
    
    # Mixins
    AnalysisHandlerMixin, QualityControlMixin, ClusteringMixin, PipelineMixin,
    DataHandlerMixin, DataValidationMixin, DataFilteringMixin, DataResourceMixin,
    VisualizationHandlerMixin, PlotCreationMixin, PlotAnalysisMixin, PlotExportMixin,
    
    # Technique handlers
    scRNASeqHandlers, ATACSeqHandlers, SpatialHandlers, ProteomicsHandlers,
    
    # Utility functions
    get_available_techniques, create_handler, DEFAULT_CONFIG
)

# Import integration components
from ..server_integration import MCPServerIntegration
from .config_manager import ConfigManager
from .error_handlers import ErrorHandler


class HandlersSystemTester:
    """Comprehensive testing system for all handler components"""
    
    def __init__(self):
        self.logger = self._setup_logger()
        self.test_results: Dict[str, Dict[str, Any]] = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for testing"""
        logger = logging.getLogger("handlers_test")
        logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(console_handler)
        
        return logger
    
    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run comprehensive tests of all handler components"""
        self.logger.info("🚀 Starting comprehensive handler system tests")
        start_time = time.time()
        
        try:
            # Test core components
            await self._test_core_components()
            
            # Test security system
            await self._test_security_system()
            
            # Test configuration management
            await self._test_configuration_system()
            
            # Test error handling
            await self._test_error_handling()
            
            # Test technique handlers
            await self._test_technique_handlers()
            
            # Test server integration
            await self._test_server_integration()
            
            # Test Electron integration (optional)
            await self._test_electron_integration()
            
            execution_time = time.time() - start_time
            
            # Generate summary
            summary = self._generate_test_summary(execution_time)
            
            # Log results
            self._log_test_results(summary)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ Test suite failed: {e}")
            self.logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "tests_completed": self.total_tests
            }
    
    async def _test_core_components(self):
        """Test core handler components"""
        self.logger.info("🔧 Testing core components...")
        
        # Test SecurityValidator
        await self._run_test("SecurityValidator", self._test_security_validator)
        
        # Test ElectronBridge
        await self._run_test("ElectronBridge", self._test_electron_bridge)
        
        # Test BaseHandler
        await self._run_test("BaseHandler", self._test_base_handler)
    
    async def _test_security_validator(self):
        """Test SecurityValidator functionality"""
        from .security_validator import SecurityValidator
        
        validator = SecurityValidator()
        
        # Test parameter validation
        safe_params = {"resolution": 0.5, "n_neighbors": 15}
        result = validator.validate_parameters(safe_params)
        assert result["valid"] is True, "Safe parameters should be valid"
        
        # Test dangerous parameters
        dangerous_params = {"evil": "__import__('os').system('rm -rf /')"}
        result = validator.validate_parameters(dangerous_params)
        assert result["valid"] is False, "Dangerous parameters should be invalid"
        
        # Test file validation
        result = validator.validate_file_upload("data.h5ad", 1024)
        assert result["valid"] is True, "Valid file should pass validation"
        
        # Test rate limiting
        for i in range(5):
            assert validator.check_rate_limit("test_op") is True, f"Rate limit check {i} should pass"
        
        return {"security_features": ["parameter_validation", "file_validation", "rate_limiting"]}
    
    async def _test_electron_bridge(self):
        """Test ElectronBridge functionality"""
        from .electron_bridge import ElectronBridge
        
        # Test bridge creation (don't start server in test)
        bridge = ElectronBridge(websocket_port=8766)
        
        # Test connection info
        info = bridge.get_connection_info()
        assert info["websocket_port"] == 8766, "Port should be set correctly"
        assert info["server_running"] is False, "Server should not be running initially"
        
        return {"websocket_port": 8766, "connection_ready": True}
    
    async def _test_base_handler(self):
        """Test BaseHandler functionality"""
        from .base_handler import BaseHandler
        
        class TestHandler(BaseHandler):
            def get_technique_name(self) -> str:
                return "test"
            
            def _check_data_availability(self) -> Dict[str, Any]:
                return {"available": True, "test": True}
        
        handler = TestHandler(self.logger)
        
        # Test parameter validation
        validation = handler._validate_parameters(resolution=0.5, n_neighbors=15)
        assert validation["valid"] is True, "Valid parameters should pass"
        
        # Test response creation
        response = handler._create_success_response("Test success")
        assert response["success"] is True, "Success response should be created"
        assert "operation_id" in response, "Response should have operation ID"
        
        # Test health check
        health = await handler.health_check()
        assert health["healthy"] is True, "Handler should be healthy"
        
        return {"basic_operations": True, "health_check": True}
    
    async def _test_security_system(self):
        """Test comprehensive security features"""
        self.logger.info("🔒 Testing security system...")
        
        await self._run_test("SecurityValidation", self._test_security_validation)
        await self._run_test("AuditLogging", self._test_audit_logging)
    
    async def _test_security_validation(self):
        """Test security validation features"""
        from .security_validator import SecurityValidator
        
        validator = SecurityValidator()
        
        # Test SQL injection prevention
        malicious_input = {"query": "'; DROP TABLE users; --"}
        result = validator.validate_parameters(malicious_input)
        assert result["valid"] is False, "SQL injection should be blocked"
        
        # Test XSS prevention
        xss_input = {"content": "<script>alert('xss')</script>"}
        result = validator.validate_parameters(xss_input)
        assert result["valid"] is False, "XSS should be blocked"
        
        return {"injection_protection": True, "xss_protection": True}
    
    async def _test_audit_logging(self):
        """Test audit logging functionality"""
        from .security_validator import SecurityValidator
        
        validator = SecurityValidator()
        
        # Test audit operation
        validator.audit_operation("test", "test_operation", {"param": "value"})
        
        # Test security report
        report = validator.get_security_report()
        assert "recent_operations_count" in report, "Security report should include operations count"
        
        return {"audit_logging": True, "security_reporting": True}
    
    async def _test_configuration_system(self):
        """Test configuration management"""
        self.logger.info("⚙️ Testing configuration system...")
        
        await self._run_test("ConfigManager", self._test_config_manager)
    
    async def _test_config_manager(self):
        """Test ConfigManager functionality"""
        import tempfile
        import yaml
        
        # Create temporary config with all required fields
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config = {
                "security": {
                    "max_operations_per_minute": 100,
                    "max_file_size_mb": 50
                },
                "electron": {"websocket_port": 8766},
                "analysis": {"pipeline_timeout": 300}
            }
            yaml.dump(config, f)
            config_path = f.name
        
        try:
            from .config_manager import ConfigManager
            
            config_manager = ConfigManager(config_path)
            
            # Test config access
            assert config_manager.get_config("security.max_operations_per_minute") == 100
            assert config_manager.get_config("electron.websocket_port") == 8766
            
            # Test config setting
            assert config_manager.set_config("test.new_key", "test_value") is True
            assert config_manager.get_config("test.new_key") == "test_value"
            
            return {"config_loading": True, "config_setting": True}
            
        finally:
            Path(config_path).unlink()
    
    async def _test_error_handling(self):
        """Test error handling system"""
        self.logger.info("🚨 Testing error handling...")
        
        await self._run_test("ErrorHandler", self._test_error_handler)
    
    async def _test_error_handler(self):
        """Test ErrorHandler functionality"""
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as f:
            log_path = f.name
        
        try:
            from .error_handlers import ErrorHandler
            
            error_handler = ErrorHandler(log_path)
            
            # Test error handling
            result = error_handler.handle_error(
                "parameter_validation",
                "Invalid parameter",
                {"param": "test"}
            )
            
            assert result["success"] is False, "Error should return failure"
            assert "error" in result, "Result should contain error details"
            
            # Test error statistics
            stats = error_handler.get_error_statistics()
            assert stats["total_errors"] >= 1, "Should track errors"
            
            return {"error_handling": True, "error_statistics": True}
            
        finally:
            Path(log_path).unlink()
    
    async def _test_technique_handlers(self):
        """Test all technique-specific handlers"""
        self.logger.info("🧬 Testing technique handlers...")
        
        techniques = get_available_techniques()
        
        for technique_info in techniques:
            technique_name = technique_info["name"]
            await self._run_test(f"{technique_name}Handler", 
                               lambda t=technique_name: self._test_single_technique(t))
    
    async def _test_single_technique(self, technique: str):
        """Test individual technique handler"""
        try:
            handler = create_handler(technique, self.logger)
            
            # Test basic functionality
            assert handler.get_technique_name() == technique, f"Technique name should be {technique}"
            
            # Test health check
            health = await handler.health_check()
            assert "healthy" in health, "Health check should return status"
            
            # Test data availability check
            data_check = handler._check_data_availability()
            assert "available" in data_check, "Data check should return availability"
            
            return {
                "handler_created": True,
                "health_check": health.get("healthy", False),
                "data_check": True
            }
            
        except Exception as e:
            raise AssertionError(f"Failed to test {technique} handler: {e}")
    
    async def _test_server_integration(self):
        """Test server integration layer"""
        self.logger.info("🖥️ Testing server integration...")
        
        await self._run_test("ServerIntegration", self._test_mcp_integration)
    
    async def _test_mcp_integration(self):
        """Test MCP server integration"""
        import tempfile
        import yaml
        
        # Create temporary config with valid values
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config = {
                "server": {"tool_timeout": 300},
                "electron": {"auto_start_server": False, "websocket_port": 8769},  # Don't start for test
                "security": {"max_operations_per_minute": 60, "max_file_size_mb": 100},
                "analysis": {"pipeline_timeout": 300},
                "logging": {"level": "INFO"}
            }
            yaml.dump(config, f)
            config_path = f.name
        
        try:
            integration = MCPServerIntegration(config_path)
            
            # Test initialization
            result = await integration.initialize_server()
            assert result["success"] is True, "Server should initialize successfully"
            
            # Test status
            status = await integration.get_server_status()
            assert status["server_started"] is True, "Server should be started"
            
            # Test shutdown
            shutdown_result = await integration.shutdown_server()
            assert shutdown_result["success"] is True, "Server should shutdown successfully"
            
            return {"initialization": True, "status_check": True, "shutdown": True}
            
        finally:
            Path(config_path).unlink()
    
    async def _test_electron_integration(self):
        """Test Electron integration (optional)"""
        self.logger.info("🖱️ Testing Electron integration...")
        
        await self._run_test("ElectronIntegration", self._test_electron_features)
    
    async def _test_electron_features(self):
        """Test Electron-specific features"""
        from .electron_bridge import ElectronBridge
        
        # Test without actually starting server
        bridge = ElectronBridge(websocket_port=8767)
        
        # Test message handling setup
        assert hasattr(bridge, 'message_handlers'), "Bridge should have message handlers"
        assert "ping" in bridge.message_handlers, "Bridge should have ping handler"
        
        # Test connection info
        info = bridge.get_connection_info()
        assert info["websocket_port"] == 8767, "Port should be configured correctly"
        
        return {"message_handlers": True, "connection_setup": True}
    
    async def _run_test(self, test_name: str, test_func):
        """Run individual test with error handling"""
        self.total_tests += 1
        
        try:
            self.logger.info(f"   Testing {test_name}...")
            result = await test_func()
            
            self.passed_tests += 1
            self.test_results[test_name] = {
                "status": "PASSED",
                "result": result,
                "error": None
            }
            self.logger.info(f"   ✅ {test_name} PASSED")
            
        except Exception as e:
            self.failed_tests += 1
            self.test_results[test_name] = {
                "status": "FAILED",
                "result": None,
                "error": str(e)
            }
            self.logger.error(f"   ❌ {test_name} FAILED: {e}")
    
    def _generate_test_summary(self, execution_time: float) -> Dict[str, Any]:
        """Generate comprehensive test summary"""
        return {
            "success": self.failed_tests == 0,
            "execution_time": round(execution_time, 2),
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "pass_rate": round((self.passed_tests / self.total_tests) * 100, 1) if self.total_tests > 0 else 0,
            "test_results": self.test_results,
            "system_info": {
                "python_version": sys.version,
                "available_techniques": [t["name"] for t in get_available_techniques()],
                "security_features": ["input_validation", "rate_limiting", "audit_logging"],
                "integration_features": ["electron_bridge", "mcp_server", "config_management"]
            }
        }
    
    def _log_test_results(self, summary: Dict[str, Any]):
        """Log comprehensive test results"""
        self.logger.info("\n" + "="*60)
        self.logger.info("🎯 HANDLER SYSTEM TEST SUMMARY")
        self.logger.info("="*60)
        
        if summary["success"]:
            self.logger.info("🎉 ALL TESTS PASSED!")
        else:
            self.logger.warning("⚠️  SOME TESTS FAILED")
        
        self.logger.info(f"📊 Tests: {summary['passed_tests']}/{summary['total_tests']} passed ({summary['pass_rate']}%)")
        self.logger.info(f"⏱️  Execution time: {summary['execution_time']}s")
        self.logger.info(f"🧬 Techniques: {', '.join(summary['system_info']['available_techniques'])}")
        
        # Log failed tests
        if summary["failed_tests"] > 0:
            self.logger.info("\n❌ FAILED TESTS:")
            for test_name, result in summary["test_results"].items():
                if result["status"] == "FAILED":
                    self.logger.error(f"   - {test_name}: {result['error']}")
        
        self.logger.info("="*60)


async def main():
    """Main entry point for handlers module"""
    print("🚀 Handlers Module - Comprehensive Testing Suite")
    print("="*60)
    
    # Initialize tester
    tester = HandlersSystemTester()
    
    try:
        # Run comprehensive tests
        summary = await tester.run_comprehensive_tests()
        
        # Exit with appropriate code
        if summary["success"]:
            print("\n✅ All handler components working correctly!")
            sys.exit(0)
        else:
            print(f"\n❌ {summary['failed_tests']} test(s) failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Test suite interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        sys.exit(1)


def run_basic_validation():
    """Run basic validation of module imports and configuration"""
    print("🔍 Running basic validation...")
    
    try:
        # Test imports
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
        return False


if __name__ == "__main__":
    # Check if running basic validation or full test suite
    if len(sys.argv) > 1 and sys.argv[1] == "--basic":
        success = run_basic_validation()
        sys.exit(0 if success else 1)
    else:
        # Run full test suite
        asyncio.run(main())