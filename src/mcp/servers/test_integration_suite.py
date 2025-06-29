"""
Comprehensive Integration Test Suite

Orchestrates and runs all three high-priority integration tests:
1. MCP Server Integration Testing
2. Electron WebSocket Communication Testing  
3. Configuration Compatibility Testing

Provides unified reporting and CI/CD integration.
"""

import asyncio
import pytest
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

# Import test modules
from .test_mcp_server_integration import MCPServerIntegrationTester
from .test_electron_websocket import ElectronWebSocketTester
from .test_configuration_compatibility import ConfigurationCompatibilityTester


@dataclass
class TestSuiteResult:
    """Result of a test suite execution"""
    name: str
    success: bool
    tests_passed: int
    tests_failed: int
    execution_time: float
    errors: List[str] = None


class ComprehensiveIntegrationTester:
    """Orchestrates all high-priority integration tests"""
    
    def __init__(self):
        self.logger = logging.getLogger("integration.suite")
        self.setup_logging()
        self.results: List[TestSuiteResult] = []
    
    def setup_logging(self):
        """Setup comprehensive logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('logs/integration_tests.log')
            ]
        )
        
        # Create logs directory if it doesn't exist
        Path('logs').mkdir(exist_ok=True)

    # =============================================================================
    # INDIVIDUAL TEST SUITE RUNNERS
    # =============================================================================
    
    async def run_mcp_server_tests(self) -> TestSuiteResult:
        """Run MCP Server integration tests"""
        print("\n🔗 Running MCP Server Integration Tests")
        print("="*60)
        
        start_time = time.time()
        errors = []
        
        try:
            tester = MCPServerIntegrationTester()
            success = await tester.run_all_tests()
            
            execution_time = time.time() - start_time
            
            return TestSuiteResult(
                name="MCP Server Integration",
                success=success,
                tests_passed=7 if success else 0,  # Number of tests in MCP suite
                tests_failed=0 if success else 7,
                execution_time=execution_time,
                errors=errors
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"MCP Server test suite crashed: {str(e)}"
            errors.append(error_msg)
            self.logger.error(error_msg)
            
            return TestSuiteResult(
                name="MCP Server Integration",
                success=False,
                tests_passed=0,
                tests_failed=7,
                execution_time=execution_time,
                errors=errors
            )
    
    async def run_electron_websocket_tests(self) -> TestSuiteResult:
        """Run Electron WebSocket communication tests"""
        print("\n🖥️ Running Electron WebSocket Communication Tests")
        print("="*60)
        
        start_time = time.time()
        errors = []
        
        try:
            tester = ElectronWebSocketTester()
            success = await tester.run_all_tests()
            
            execution_time = time.time() - start_time
            
            return TestSuiteResult(
                name="Electron WebSocket Communication",
                success=success,
                tests_passed=11 if success else 0,  # Number of tests in WebSocket suite
                tests_failed=0 if success else 11,
                execution_time=execution_time,
                errors=errors
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Electron WebSocket test suite crashed: {str(e)}"
            errors.append(error_msg)
            self.logger.error(error_msg)
            
            return TestSuiteResult(
                name="Electron WebSocket Communication",
                success=False,
                tests_passed=0,
                tests_failed=11,
                execution_time=execution_time,
                errors=errors
            )
    
    async def run_configuration_tests(self) -> TestSuiteResult:
        """Run Configuration compatibility tests"""
        print("\n⚙️ Running Configuration Compatibility Tests")
        print("="*60)
        
        start_time = time.time()
        errors = []
        
        try:
            tester = ConfigurationCompatibilityTester()
            success = await tester.run_all_tests()
            
            execution_time = time.time() - start_time
            
            return TestSuiteResult(
                name="Configuration Compatibility",
                success=success,
                tests_passed=11 if success else 0,  # Number of tests in Config suite
                tests_failed=0 if success else 11,
                execution_time=execution_time,
                errors=errors
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Configuration test suite crashed: {str(e)}"
            errors.append(error_msg)
            self.logger.error(error_msg)
            
            return TestSuiteResult(
                name="Configuration Compatibility",
                success=False,
                tests_passed=0,
                tests_failed=11,
                execution_time=execution_time,
                errors=errors
            )

    # =============================================================================
    # COMPREHENSIVE TEST ORCHESTRATION
    # =============================================================================
    
    async def run_all_integration_tests(self, 
                                       run_mcp: bool = True,
                                       run_electron: bool = True, 
                                       run_config: bool = True,
                                       fail_fast: bool = False) -> Dict[str, Any]:
        """Run all integration test suites"""
        
        print("🧪 COMPREHENSIVE INTEGRATION TEST SUITE")
        print("="*70)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        overall_start_time = time.time()
        
        # Run test suites
        if run_mcp:
            mcp_result = await self.run_mcp_server_tests()
            self.results.append(mcp_result)
            
            if fail_fast and not mcp_result.success:
                return self._generate_final_report(overall_start_time, early_exit=True)
        
        if run_electron:
            electron_result = await self.run_electron_websocket_tests()
            self.results.append(electron_result)
            
            if fail_fast and not electron_result.success:
                return self._generate_final_report(overall_start_time, early_exit=True)
        
        if run_config:
            config_result = await self.run_configuration_tests()
            self.results.append(config_result)
            
            if fail_fast and not config_result.success:
                return self._generate_final_report(overall_start_time, early_exit=True)
        
        # Generate final report
        return self._generate_final_report(overall_start_time)
    
    def _generate_final_report(self, start_time: float, early_exit: bool = False) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_execution_time = time.time() - start_time
        
        # Calculate totals
        total_tests_passed = sum(result.tests_passed for result in self.results)
        total_tests_failed = sum(result.tests_failed for result in self.results)
        total_tests = total_tests_passed + total_tests_failed
        
        all_successful = all(result.success for result in self.results)
        
        # Generate detailed report
        report = {
            "overall_success": all_successful and not early_exit,
            "early_exit": early_exit,
            "total_execution_time": total_execution_time,
            "total_tests": total_tests,
            "total_tests_passed": total_tests_passed,
            "total_tests_failed": total_tests_failed,
            "pass_rate": (total_tests_passed / total_tests * 100) if total_tests > 0 else 0,
            "test_suites": len(self.results),
            "successful_suites": sum(1 for result in self.results if result.success),
            "failed_suites": sum(1 for result in self.results if not result.success),
            "results": [
                {
                    "name": result.name,
                    "success": result.success,
                    "tests_passed": result.tests_passed,
                    "tests_failed": result.tests_failed,
                    "execution_time": result.execution_time,
                    "errors": result.errors or []
                }
                for result in self.results
            ]
        }
        
        # Print final report
        self._print_final_report(report)
        
        # Save detailed report
        self._save_report_to_file(report)
        
        return report
    
    def _print_final_report(self, report: Dict[str, Any]):
        """Print comprehensive final report"""
        print("\n" + "="*70)
        print("🎯 COMPREHENSIVE INTEGRATION TEST SUMMARY")
        print("="*70)
        
        if report["overall_success"]:
            print("🎉 ALL INTEGRATION TESTS PASSED!")
        elif report["early_exit"]:
            print("⚠️  TESTS STOPPED EARLY DUE TO FAILURE")
        else:
            print("❌ SOME INTEGRATION TESTS FAILED")
        
        print(f"📊 Overall Results:")
        print(f"   • Total Tests: {report['total_tests']}")
        print(f"   • Passed: {report['total_tests_passed']}")
        print(f"   • Failed: {report['total_tests_failed']}")
        print(f"   • Pass Rate: {report['pass_rate']:.1f}%")
        print(f"   • Execution Time: {report['total_execution_time']:.2f}s")
        
        print(f"\n📋 Test Suite Breakdown:")
        for result in report["results"]:
            status_icon = "✅" if result["success"] else "❌"
            print(f"   {status_icon} {result['name']}")
            print(f"      Tests: {result['tests_passed']}/{result['tests_passed'] + result['tests_failed']} passed")
            print(f"      Time: {result['execution_time']:.2f}s")
            
            if result["errors"]:
                print(f"      Errors: {len(result['errors'])}")
                for error in result["errors"][:3]:  # Show first 3 errors
                    print(f"        - {error}")
        
        print("="*70)
        
        # System information
        print(f"📋 System Information:")
        print(f"   • Python Version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        print(f"   • Test Environment: Integration Testing")
        print(f"   • Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
    
    def _save_report_to_file(self, report: Dict[str, Any]):
        """Save detailed report to file"""
        try:
            import json
            
            # Save JSON report
            report_file = Path("logs") / f"integration_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            print(f"📄 Detailed report saved to: {report_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save report: {e}")

    # =============================================================================
    # CI/CD INTEGRATION METHODS
    # =============================================================================
    
    def generate_junit_xml(self, report: Dict[str, Any]) -> str:
        """Generate JUnit XML for CI/CD integration"""
        try:
            from xml.etree.ElementTree import Element, SubElement, tostring
            from xml.dom import minidom
            
            # Create root testsuites element
            testsuites = Element("testsuites")
            testsuites.set("tests", str(report["total_tests"]))
            testsuites.set("failures", str(report["total_tests_failed"]))
            testsuites.set("time", str(report["total_execution_time"]))
            
            # Add test suite for each result
            for result in report["results"]:
                testsuite = SubElement(testsuites, "testsuite")
                testsuite.set("name", result["name"])
                testsuite.set("tests", str(result["tests_passed"] + result["tests_failed"]))
                testsuite.set("failures", str(result["tests_failed"]))
                testsuite.set("time", str(result["execution_time"]))
                
                # Add test case
                testcase = SubElement(testsuite, "testcase")
                testcase.set("classname", result["name"].replace(" ", "_"))
                testcase.set("name", "integration_test")
                testcase.set("time", str(result["execution_time"]))
                
                if not result["success"]:
                    failure = SubElement(testcase, "failure")
                    failure.set("message", "Integration test failed")
                    failure.text = "\n".join(result["errors"])
            
            # Convert to pretty XML string
            rough_string = tostring(testsuites, 'unicode')
            reparsed = minidom.parseString(rough_string)
            return reparsed.toprettyxml(indent="  ")
            
        except ImportError:
            self.logger.warning("xml.etree.ElementTree not available, skipping JUnit XML generation")
            return ""
    
    def get_exit_code(self, report: Dict[str, Any]) -> int:
        """Get appropriate exit code for CI/CD"""
        if report["overall_success"]:
            return 0  # Success
        elif report["total_tests_failed"] > 0:
            return 1  # Test failures
        else:
            return 2  # System errors


# =============================================================================
# PYTEST INTEGRATION
# =============================================================================

@pytest.mark.asyncio
async def test_comprehensive_integration():
    """Pytest wrapper for comprehensive integration testing"""
    tester = ComprehensiveIntegrationTester()
    report = await tester.run_all_integration_tests()
    
    assert report["overall_success"], f"Integration tests failed: {report['total_tests_failed']} failures"

@pytest.mark.asyncio 
async def test_mcp_integration_only():
    """Run only MCP server integration tests"""
    tester = ComprehensiveIntegrationTester()
    report = await tester.run_all_integration_tests(
        run_mcp=True, run_electron=False, run_config=False
    )
    assert report["overall_success"], "MCP integration tests failed"

@pytest.mark.asyncio
async def test_electron_integration_only():
    """Run only Electron WebSocket tests"""
    tester = ComprehensiveIntegrationTester()
    report = await tester.run_all_integration_tests(
        run_mcp=False, run_electron=True, run_config=False
    )
    assert report["overall_success"], "Electron integration tests failed"

@pytest.mark.asyncio
async def test_config_integration_only():
    """Run only Configuration compatibility tests"""
    tester = ComprehensiveIntegrationTester()
    report = await tester.run_all_integration_tests(
        run_mcp=False, run_electron=False, run_config=True
    )
    assert report["overall_success"], "Configuration integration tests failed"


# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

def main():
    """Main entry point for integration testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Comprehensive Integration Test Suite")
    parser.add_argument("--mcp", action="store_true", help="Run MCP server integration tests only")
    parser.add_argument("--electron", action="store_true", help="Run Electron WebSocket tests only")
    parser.add_argument("--config", action="store_true", help="Run configuration compatibility tests only")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first test suite failure")
    parser.add_argument("--junit-xml", type=str, help="Save JUnit XML report to file")
    
    args = parser.parse_args()
    
    async def run_tests():
        tester = ComprehensiveIntegrationTester()
        
        # Determine which tests to run
        run_mcp = args.mcp or not (args.electron or args.config)
        run_electron = args.electron or not (args.mcp or args.config)
        run_config = args.config or not (args.mcp or args.electron)
        
        # Run tests
        report = await tester.run_all_integration_tests(
            run_mcp=run_mcp,
            run_electron=run_electron,
            run_config=run_config,
            fail_fast=args.fail_fast
        )
        
        # Generate JUnit XML if requested
        if args.junit_xml:
            junit_xml = tester.generate_junit_xml(report)
            with open(args.junit_xml, 'w') as f:
                f.write(junit_xml)
            print(f"📄 JUnit XML saved to: {args.junit_xml}")
        
        return tester.get_exit_code(report)
    
    exit_code = asyncio.run(run_tests())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()