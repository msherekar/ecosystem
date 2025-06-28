"""
Core MCP Client Implementation

Provides client functionality for connecting to and interacting with MCP servers.
Handles connection management, caching, and request routing.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

# Import all core components
from .connection_manager import ConnectionManager, ServerConnection, ConnectionStatus
from .cache_manager import CacheManager
from .execution_engine import ExecutionEngine
from .response_formatter import ResponseFormatter, StandardResponseFormatter

# Re-export commonly used classes for backward compatibility
from .connection_manager import ConnectionStatus
from .response_formatter import (
    ResponseFormatter, 
    StandardResponseFormatter,
    DetailedResponseFormatter,
    MinimalResponseFormatter,
    AgentResponseFormatter,
    JSONResponseFormatter,
    ResponseFormatterFactory
)

# Import the main client class from a separate module
from .mcp_client import MCPClient, ClientConfiguration

# Version info
__version__ = "1.0.0"
__all__ = [
    "MCPClient",
    "ClientConfiguration",
    "ConnectionManager", 
    "CacheManager",
    "ExecutionEngine",
    "ResponseFormatter",
    "StandardResponseFormatter",
    "DetailedResponseFormatter", 
    "MinimalResponseFormatter",
    "AgentResponseFormatter",
    "JSONResponseFormatter",
    "ResponseFormatterFactory",
    "ConnectionStatus",
    "ServerConnection"
]


def main():
    """
    Main function for testing MCP Client functionality.
    
    This function demonstrates basic usage of the MCP Client system
    and can be used for integration testing.
    """
    print("🚀 MCP Client System - Main Entry Point")
    print("=" * 50)
    
    async def run_main_demo():
        """Run the main demonstration"""
        # Create client with custom configuration
        from .mcp_client import ClientConfiguration
        client_config = ClientConfiguration(
            name="demo_client",
            cache_max_size=100,
            cache_default_ttl=300
        )
        client = MCPClient(
            config=client_config,
            response_formatter=StandardResponseFormatter()
        )
        
        print(f"✅ Created MCP Client: {client.config.name}")
        
        # Demonstrate client capabilities
        print("\n📊 Client Information:")
        client_status = client.get_client_status()
        print(f"  • Client Name: {client_status['client_name']}")
        print(f"  • Client State: {client_status['state']}")
        available_tools = client.get_available_tools()
        available_resources = client.get_available_resources()
        print(f"  • Available Tools: {len(available_tools)}")
        print(f"  • Available Resources: {len(available_resources)}")
        
        # Demonstrate cache functionality
        print("\n🗄️ Testing Cache:")
        client.cache_manager.set("demo_key", "demo_value", ttl=60)
        cached_value = client.cache_manager.get("demo_key")
        print(f"  • Cache Test: {'✅ PASS' if cached_value == 'demo_value' else '❌ FAIL'}")
        
        cache_stats = client.cache_manager.get_stats()
        print(f"  • Cache Stats: {cache_stats.get('memory_entries', 0)} entries, {cache_stats.get('hit_rate_percent', 0)}% hit rate")
        
        # Demonstrate connection manager
        print("\n🔗 Testing Connection Manager:")
        conn_stats = client.connection_manager.get_connection_stats()
        print(f"  • Total Connections: {conn_stats['total_connections']}")
        print(f"  • Healthy Connections: {conn_stats['healthy']}")
        print(f"  • Manager Running: {'✅ YES' if conn_stats.get('manager_running', False) else '❌ NO'}")
        
        # Test response formatting
        print("\n📝 Testing Response Formatters:")
        formatters = ResponseFormatterFactory.get_available_formatters()
        for formatter_type in formatters:
            try:
                formatter = ResponseFormatterFactory.create_formatter(formatter_type)
                test_response = formatter.format_success({"test": "data"})
                success_indicators = ["success", "status", "result"]
                has_indicator = any(indicator in test_response for indicator in success_indicators)
                status = "✅ PASS" if has_indicator else "❌ FAIL"
                print(f"  • {formatter_type.capitalize()} Formatter: {status}")
            except Exception as e:
                print(f"  • {formatter_type.capitalize()} Formatter: ❌ ERROR - {e}")
        
        print("\n🎉 Demo completed successfully!")
        return client
    
    # Run the demo
    try:
        client = asyncio.run(run_main_demo())
        return client
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        return None


def run_static_tests():
    """
    Run static tests that don't require async operations.
    
    Returns:
        bool: True if all static tests pass, False otherwise
    """
    print("\n🧪 Running Static Tests...")
    test_results = []
    
    # Test 1: Import verification
    try:
        from .connection_manager import ConnectionStatus
        from .response_formatter import StandardResponseFormatter
        test_results.append(("Import Test", True, "All required modules imported successfully"))
    except ImportError as e:
        test_results.append(("Import Test", False, f"Import failed: {e}"))
    
    # Test 2: Class instantiation
    try:
        cache_manager = CacheManager({"max_memory_size": 10, "default_ttl": 60})
        logger = logging.getLogger("test")
        connection_manager = ConnectionManager(logger)
        formatter = StandardResponseFormatter()
        test_results.append(("Class Instantiation", True, "All classes instantiate correctly"))
    except Exception as e:
        test_results.append(("Class Instantiation", False, f"Instantiation failed: {e}"))
    
    # Test 3: Response formatter factory
    try:
        formatter = ResponseFormatterFactory.create_formatter("standard")
        available = ResponseFormatterFactory.get_available_formatters()
        is_valid = isinstance(formatter, StandardResponseFormatter) and len(available) > 0
        test_results.append(("Formatter Factory", is_valid, f"Factory works, {len(available)} formatters available"))
    except Exception as e:
        test_results.append(("Formatter Factory", False, f"Factory test failed: {e}"))
    
    # Test 4: Cache basic operations
    try:
        cache = CacheManager({"max_memory_size": 5, "default_ttl": 300})
        cache.set("test_key", "test_value")
        value = cache.get("test_key")
        is_valid = value == "test_value"
        test_results.append(("Cache Operations", is_valid, "Cache set/get operations work"))
    except Exception as e:
        test_results.append(("Cache Operations", False, f"Cache test failed: {e}"))
    
    # Test 5: Connection status enum
    try:
        status = ConnectionStatus.CONNECTED
        is_valid = status.value == "connected"
        test_results.append(("ConnectionStatus Enum", is_valid, "Enum values are correct"))
    except Exception as e:
        test_results.append(("ConnectionStatus Enum", False, f"Enum test failed: {e}"))
    
    # Print results
    passed = 0
    for test_name, success, message in test_results:
        status = "✅" if success else "❌"
        print(f"  {status} {test_name}: {message}")
        if success:
            passed += 1
    
    success_rate = (passed / len(test_results)) * 100
    print(f"\n📊 Static Tests Summary: {passed}/{len(test_results)} passed ({success_rate:.1f}%)")
    
    return passed == len(test_results)


def run_dynamic_tests():
    """
    Run dynamic tests that require async operations.
    
    Returns:
        bool: True if all dynamic tests pass, False otherwise
    """
    print("\n⚡ Running Dynamic Tests...")
    
    async def async_test_suite():
        test_results = []
        
        # Test 1: Client creation and configuration
        try:
            client_config = ClientConfiguration(
                name="test_client",
                cache_max_size=50,
                cache_default_ttl=120
            )
            client = MCPClient(config=client_config)
            is_valid = (
                client.config.name == "test_client" and 
                client.config.cache_max_size == 50 and
                client.config.cache_default_ttl == 120
            )
            test_results.append(("Client Creation", is_valid, "Client created with correct configuration"))
        except Exception as e:
            test_results.append(("Client Creation", False, f"Client creation failed: {e}"))
        
        # Test 2: Health check (no servers connected)
        try:
            health_results = await client.health_check()
            is_valid = isinstance(health_results, dict)
            test_results.append(("Health Check", is_valid, f"Health check returned {len(health_results)} results"))
        except Exception as e:
            test_results.append(("Health Check", False, f"Health check failed: {e}"))
        
        # Test 3: Get available tools (empty initially)
        try:
            tools = client.get_available_tools()
            is_valid = isinstance(tools, dict)
            test_results.append(("Get Available Tools", is_valid, f"Retrieved {len(tools)} available tools"))
        except Exception as e:
            test_results.append(("Get Available Tools", False, f"Get tools failed: {e}"))
        
        # Test 4: Get client status
        try:
            status = client.get_client_status()
            required_keys = ["name", "state"]
            has_required_keys = all(key in status for key in required_keys)
            test_results.append(("Client Status", has_required_keys, "Status contains all required keys"))
        except Exception as e:
            test_results.append(("Client Status", False, f"Status test failed: {e}"))
        
        # Test 5: Cache operations with TTL
        try:
            client.cache_manager.set("ttl_test", "ttl_value", ttl=1)
            immediate_value = client.cache_manager.get("ttl_test")
            
            await asyncio.sleep(1.1)  # Wait for expiration
            expired_value = client.cache_manager.get("ttl_test")
            
            is_valid = immediate_value == "ttl_value" and expired_value is None
            test_results.append(("TTL Cache Test", is_valid, "TTL expiration works correctly"))
        except Exception as e:
            test_results.append(("TTL Cache Test", False, f"TTL test failed: {e}"))
        
        # Test 6: Tool execution (should fail gracefully with no servers)
        try:
            result = await client.execute_tool("nonexistent_tool", {})
            is_valid = isinstance(result, dict) and "success" in result and not result["success"]
            test_results.append(("Tool Execution Error Handling", is_valid, "Tool execution handles missing tools gracefully"))
        except Exception as e:
            test_results.append(("Tool Execution Error Handling", False, f"Tool execution test failed: {e}"))
        
        return test_results
    
    # Run async tests
    try:
        test_results = asyncio.run(async_test_suite())
        
        # Print results
        passed = 0
        for test_name, success, message in test_results:
            status = "✅" if success else "❌"
            print(f"  {status} {test_name}: {message}")
            if success:
                passed += 1
        
        success_rate = (passed / len(test_results)) * 100
        print(f"\n📊 Dynamic Tests Summary: {passed}/{len(test_results)} passed ({success_rate:.1f}%)")
        
        return passed == len(test_results)
        
    except Exception as e:
        print(f"❌ Dynamic test suite failed: {e}")
        return False


if __name__ == "__main__":
    """
    Main execution block for testing the MCP Client system locally.
    
    This block runs when the module is executed directly and includes:
    - Static tests (imports, instantiation, basic operations)
    - Dynamic tests (async operations, integration tests) 
    - Main demonstration function
    """
    print("🏃 Running MCP Client System Tests")
    print("=" * 60)
    
    # Run static tests first
    static_passed = run_static_tests()
    
    # Run dynamic tests
    dynamic_passed = run_dynamic_tests()
    
    # Run main demo if tests pass
    if static_passed and dynamic_passed:
        print("\n✅ All tests passed! Running main demo...")
        main()
    else:
        print("\n❌ Some tests failed. Skipping main demo.")
        print("Please check the test results above and fix any issues.")
    
    # Final summary
    print("\n" + "=" * 60)
    print("🏁 Test Execution Summary")
    print("=" * 60)
    print(f"Static Tests: {'✅ PASSED' if static_passed else '❌ FAILED'}")
    print(f"Dynamic Tests: {'✅ PASSED' if dynamic_passed else '❌ FAILED'}")
    print(f"Overall Status: {'✅ SUCCESS' if static_passed and dynamic_passed else '❌ FAILURE'}")
    
    # Set exit code
    exit_code = 0 if (static_passed and dynamic_passed) else 1
    print(f"Exit Code: {exit_code}")
    
    # In a real scenario, you might want to exit with the code
    # exit(exit_code)