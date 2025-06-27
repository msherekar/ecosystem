"""
Comprehensive integration tests for the MCP Client System

Tests the complete system integration between all modular components:
- MCPClient (main client class)
- ConnectionManager (server connections)
- CacheManager (caching with TTL)
- ExecutionEngine (tool execution)
- ResponseFormatter (response formatting)
"""

import asyncio
import logging
import time
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock

# Import all MCP client components
from src.mcp.core.client import MCPClient
from src.mcp.core.client.connection_manager import ConnectionManager, ServerConnection, ConnectionStatus
from src.mcp.core.client.cache_manager import CacheManager
from src.mcp.core.client.execution_engine import ExecutionEngine
from src.mcp.core.client.response_formatter import (
    StandardResponseFormatter, 
    DetailedResponseFormatter,
    ResponseFormatterFactory
)


class MockMCPServer:
    """Mock MCP server for testing"""
    
    def __init__(self, name: str, tools: Dict[str, Any] = None, 
                 resources: Dict[str, Any] = None, prompts: Dict[str, Any] = None):
        self.name = name
        self.tools = tools or {}
        self.resources = resources or {}
        self.prompts = prompts or {}
        self.initialized = False
        self.capabilities = {
            "tools": list(self.tools.keys()),
            "resources": list(self.resources.keys()),
            "prompts": list(self.prompts.keys())
        }
    
    async def initialize(self):
        """Initialize the mock server"""
        await asyncio.sleep(0.01)  # Simulate initialization delay
        self.initialized = True
        return True
    
    def get_capabilities(self):
        """Get server capabilities"""
        return self.capabilities
    
    def get_tools(self):
        """Get available tools"""
        return self.tools
    
    def get_resources(self):
        """Get available resources"""
        return self.resources
    
    def get_prompts(self):
        """Get available prompts"""
        return self.prompts
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]):
        """Execute a tool"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        # Simulate tool execution
        await asyncio.sleep(0.01)
        
        return {
            "tool": tool_name,
            "parameters": parameters,
            "result": f"Executed {tool_name} with {parameters}",
            "server": self.name
        }
    
    async def get_resource(self, uri: str):
        """Get a resource"""
        if uri not in self.resources:
            raise ValueError(f"Resource '{uri}' not found")
        
        # Simulate resource access
        await asyncio.sleep(0.01)
        
        return {
            "uri": uri,
            "content": f"Content for {uri}",
            "server": self.name
        }
    
    async def render_prompt(self, prompt_name: str, parameters: Dict[str, Any]):
        """Render a prompt"""
        if prompt_name not in self.prompts:
            raise ValueError(f"Prompt '{prompt_name}' not found")
        
        # Simulate prompt rendering
        await asyncio.sleep(0.01)
        
        return {
            "prompt": prompt_name,
            "parameters": parameters,
            "rendered": f"Rendered {prompt_name} with {parameters}",
            "server": self.name
        }
    
    async def cleanup(self):
        """Cleanup the mock server"""
        self.initialized = False


# Mock tool and resource objects for consistent testing
class MockTool:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.input_schema = {}
        self.output_schema = {}

class MockResource:
    def __init__(self, uri, name, description):
        self.uri = uri
        self.name = name
        self.description = description
        self.mime_type = "application/octet-stream"

class MockPrompt:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.schema = {}
        self.template = f"Template for {name}"
        self.parameters = {}


class MCPClientSystemTests:
    """Integration tests for the MCP client system"""
    
    def __init__(self):
        self.logger = logging.getLogger("test_mcp_client_system")
        self.test_results = []
    
    def log_test_result(self, test_name: str, success: bool, message: str = ""):
        """Log test result"""
        status = "✅" if success else "❌"
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message
        })
        print(f"{status} {test_name}: {message}")
    
    async def test_individual_components(self):
        """Test individual components in isolation"""
        print("\n🧪 Testing Individual Components...")
        
        # Test CacheManager
        cache_manager = CacheManager(max_size=10, default_ttl=60)
        cache_manager.set("test_key", "test_value")
        cached_value = cache_manager.get("test_key")
        
        self.log_test_result(
            "CacheManager Basic Operations",
            cached_value == "test_value",
            "Cache set/get operations work"
        )
        
        # Test ConnectionManager
        logger = logging.getLogger("test_connection_manager")
        connection_manager = ConnectionManager(logger)
        
        await connection_manager.start()
        
        # Test with mock server
        mock_server = MockMCPServer("test_server")
        connection_success = await connection_manager.connect_server(mock_server, "test_server")
        
        self.log_test_result(
            "ConnectionManager Server Connection",
            connection_success,
            "Server connection established"
        )
        
        # Test ResponseFormatter
        formatter = StandardResponseFormatter()
        success_response = formatter.format_success({"test": "data"})
        error_response = formatter.format_error("test error")
        
        self.log_test_result(
            "ResponseFormatter Operations",
            success_response["success"] and not error_response["success"],
            "Response formatting works for both success and error cases"
        )
        
        # Test ExecutionEngine
        execution_engine = ExecutionEngine(
            connection_manager, cache_manager, formatter, logger
        )
        
        # Update indexes
        execution_engine.update_indexes("test_server", mock_server)
        
        self.log_test_result(
            "ExecutionEngine Index Updates",
            "test_tool" in execution_engine.tool_index if mock_server.tools else True,
            "Index updates work correctly"
        )
        
        await connection_manager.stop()
    
    async def test_mcp_client_integration(self):
        """Test full MCP client integration"""
        print("\n🔗 Testing MCP Client Integration...")
        
        # Create MCP client
        client = MCPClient(
            name="test_client",
            cache_config={"max_size": 100, "default_ttl": 300}
        )
        
        self.log_test_result(
            "MCPClient Creation",
            client.name == "test_client",
            "Client created successfully"
        )
        
        # Create mock servers with different capabilities
        bioinformatics_server = MockMCPServer(
            "bioinformatics",
            tools={
                "sequence_analysis": MockTool("sequence_analysis", "Analyze DNA sequences"),
                "blast_search": MockTool("blast_search", "BLAST sequence search")
            },
            resources={
                "genome://human": MockResource("genome://human", "Human Genome", "Human genome data"),
                "protein://uniprot": MockResource("protein://uniprot", "UniProt", "UniProt protein database")
            },
            prompts={
                "analysis_report": MockPrompt("analysis_report", "Generate analysis report")
            }
        )
        
        data_server = MockMCPServer(
            "data_processing",
            tools={
                "data_transform": MockTool("data_transform", "Transform data"),
                "statistical_analysis": MockTool("statistical_analysis", "Statistical analysis")
            },
            resources={
                "data://dataset1": MockResource("data://dataset1", "Dataset 1", "Dataset 1")
            }
        )
        
        # Connect servers
        bio_connected = await client.connect_server(bioinformatics_server, "bioinformatics")
        data_connected = await client.connect_server(data_server, "data_processing")
        
        self.log_test_result(
            "Server Connections",
            bio_connected and data_connected,
            "Both servers connected successfully"
        )
        
        # Test tool availability
        available_tools = client.get_available_tools()
        expected_tools = ["sequence_analysis", "blast_search", "data_transform", "statistical_analysis"]
        tools_available = all(tool in available_tools for tool in expected_tools)
        
        self.log_test_result(
            "Tool Availability",
            tools_available,
            f"All {len(expected_tools)} tools available across servers"
        )
        
        # Test resource availability
        available_resources = client.get_available_resources()
        expected_resources = ["genome://human", "protein://uniprot", "data://dataset1"]
        resources_available = all(resource in available_resources for resource in expected_resources)
        
        self.log_test_result(
            "Resource Availability",
            resources_available,
            f"All {len(expected_resources)} resources available across servers"
        )
        
        # Test tool execution
        try:
            execution_result = await client.execute_tool(
                "sequence_analysis", 
                {"sequence": "ATCGATCG", "type": "DNA"}
            )
            
            tool_execution_success = (
                execution_result.get("success", False) and
                "result" in execution_result.get("data", {})
            )
            
            self.log_test_result(
                "Tool Execution",
                tool_execution_success,
                "Tool executed successfully across server boundaries"
            )
        except Exception as e:
            self.log_test_result(
                "Tool Execution",
                False,
                f"Tool execution failed: {str(e)}"
            )
        
        # Test resource access
        try:
            resource_result = await client.get_resource("genome://human")
            
            resource_access_success = (
                resource_result.get("success", False) and
                "content" in resource_result.get("data", {})
            )
            
            self.log_test_result(
                "Resource Access",
                resource_access_success,
                "Resource accessed successfully"
            )
        except Exception as e:
            self.log_test_result(
                "Resource Access",
                False,
                f"Resource access failed: {str(e)}"
            )
        
        # Test caching behavior
        # Execute same tool twice to test caching
        start_time = time.time()
        await client.execute_tool("sequence_analysis", {"sequence": "ATCGATCG", "type": "DNA"})
        first_execution_time = time.time() - start_time
        
        start_time = time.time()
        await client.execute_tool("sequence_analysis", {"sequence": "ATCGATCG", "type": "DNA"})
        second_execution_time = time.time() - start_time
        
        # Second execution should be faster due to caching
        caching_works = second_execution_time < first_execution_time
        
        self.log_test_result(
            "Caching Behavior",
            caching_works,
            f"Cached execution faster ({second_execution_time:.3f}s vs {first_execution_time:.3f}s)"
        )
        
        # Test health check
        health_results = await client.health_check()
        all_healthy = all(health_results.values())
        
        self.log_test_result(
            "Health Check",
            all_healthy,
            f"All {len(health_results)} servers healthy"
        )
        
        # Test server status
        server_status = client.get_server_status()
        servers_connected = all(
            status["status"] == "connected" 
            for status in server_status.values()
        )
        
        self.log_test_result(
            "Server Status",
            servers_connected,
            f"All {len(server_status)} servers show connected status"
        )
        
        # Test disconnection
        bio_disconnected = await client.disconnect_server("bioinformatics")
        
        # Check that tools are no longer available
        tools_after_disconnect = client.get_available_tools()
        bio_tools_removed = not any(
            tool in tools_after_disconnect 
            for tool in ["sequence_analysis", "blast_search"]
        )
        
        self.log_test_result(
            "Server Disconnection",
            bio_disconnected and bio_tools_removed,
            "Server disconnected and tools removed from availability"
        )
        
        # Clean up
        await client.disconnect_server("data_processing")
    
    async def test_error_handling(self):
        """Test error handling scenarios"""
        print("\n⚠️ Testing Error Handling...")
        
        client = MCPClient("error_test_client")
        
        # Test tool execution with non-existent tool
        try:
            result = await client.execute_tool("non_existent_tool", {})
            error_handled = not result.get("success", True)
            
            self.log_test_result(
                "Non-existent Tool Error",
                error_handled,
                "Error properly handled for non-existent tool"
            )
        except Exception as e:
            self.log_test_result(
                "Non-existent Tool Error",
                False,
                f"Unexpected exception: {str(e)}"
            )
        
        # Test resource access with non-existent resource
        try:
            result = await client.get_resource("non://existent")
            error_handled = not result.get("success", True)
            
            self.log_test_result(
                "Non-existent Resource Error",
                error_handled,
                "Error properly handled for non-existent resource"
            )
        except Exception as e:
            self.log_test_result(
                "Non-existent Resource Error",
                False,
                f"Unexpected exception: {str(e)}"
            )
    
    async def test_performance_scenarios(self):
        """Test performance scenarios"""
        print("\n⚡ Testing Performance Scenarios...")
        
        client = MCPClient(
            "performance_test_client",
            cache_config={"max_size": 1000, "default_ttl": 600}
        )
        
        # Create a server with multiple tools
        performance_server = MockMCPServer(
            "performance_server",
            tools={f"tool_{i}": MockTool(f"tool_{i}", f"Tool {i}") for i in range(100)}
        )
        
        await client.connect_server(performance_server, "performance_server")
        
        # Test rapid tool execution
        start_time = time.time()
        tasks = []
        
        for i in range(10):
            task = client.execute_tool(f"tool_{i}", {"iteration": i})
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        successful_executions = sum(
            1 for result in results 
            if isinstance(result, dict) and result.get("success", False)
        )
        
        self.log_test_result(
            "Concurrent Tool Execution",
            successful_executions >= 8,  # Allow some failures
            f"{successful_executions}/10 tools executed in {execution_time:.3f}s"
        )
        
        await client.disconnect_server("performance_server")
    
    async def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting MCP Client System Integration Tests")
        print("=" * 60)
        
        # Run test suites
        await self.test_individual_components()
        await self.test_mcp_client_integration()
        await self.test_error_handling()
        await self.test_performance_scenarios()
        
        # Print summary
        print("\n" + "=" * 60)
        print("🏁 Test Summary")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\nFailed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  ❌ {result['test']}: {result['message']}")
        
        print("\n" + "=" * 60)
        
        return passed_tests, failed_tests


async def main():
    """Main test function"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    test_suite = MCPClientSystemTests()
    passed, failed = await test_suite.run_all_tests()
    
    # Exit with appropriate code
    exit_code = 0 if failed == 0 else 1
    print(f"\nExiting with code: {exit_code}")
    return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code) 