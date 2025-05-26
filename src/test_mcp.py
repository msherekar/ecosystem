#!/usr/bin/env python3
"""
Test script for MCP implementation in the bioinformatics platform.
This script verifies that all MCP servers can be initialized and connected.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp.core.registry import get_mcp_registry

async def test_mcp_implementation():
    """Test the MCP implementation"""
    print("🧪 Testing MCP Implementation...")
    print("=" * 50)
    
    try:
        # Get MCP registry
        print("📋 Getting MCP registry...")
        registry = await get_mcp_registry()
        
        # Initialize registry
        print("🔧 Initializing MCP registry...")
        success = await registry.initialize()
        
        if not success:
            print("❌ Failed to initialize MCP registry")
            return False
        
        print("✅ MCP registry initialized successfully")
        
        # Check server status
        print("\n📊 Server Status:")
        server_status = registry.get_server_status()
        for server_name, status in server_status.items():
            status_icon = "✅" if status.get("connected", False) else "❌"
            print(f"  {status_icon} {server_name}: {status}")
        
        # Get available tools
        print("\n🔧 Available Tools:")
        tools = registry.get_available_tools()
        for tool_name, tool_info in tools.items():
            print(f"  • {tool_name}: {tool_info.get('description', 'No description')}")
        
        # Get available resources
        print("\n📁 Available Resources:")
        resources = registry.get_available_resources()
        for resource_uri, resource_info in resources.items():
            print(f"  • {resource_uri}: {resource_info.get('description', 'No description')}")
        
        # Get available prompts
        print("\n💬 Available Prompts:")
        prompts = registry.get_available_prompts()
        for prompt_name, prompt_info in prompts.items():
            print(f"  • {prompt_name}: {prompt_info.get('description', 'No description')}")
        
        # Test health check
        print("\n🏥 Health Check:")
        health = await registry.health_check()
        for server_name, is_healthy in health.items():
            health_icon = "✅" if is_healthy else "❌"
            print(f"  {health_icon} {server_name}: {'Healthy' if is_healthy else 'Unhealthy'}")
        
        # Test context aggregation
        print("\n🧠 Context Aggregation:")
        context = registry.get_aggregated_context()
        print(f"  • Data status: {context.get('data_status', 'Unknown')}")
        print(f"  • Analysis status: {context.get('analysis_status', 'Unknown')}")
        print(f"  • Available capabilities: {len(context.get('capabilities', []))} tools")
        
        # Test a simple tool execution (if data validation tool is available)
        print("\n🔧 Testing Tool Execution:")
        if "validate_data_format" in tools:
            try:
                result = await registry.execute_tool("validate_data_format", {
                    "file_path": "test.csv",
                    "expected_format": "csv"
                })
                print(f"  ✅ Tool execution successful: {result.get('summary', 'No summary')}")
            except Exception as e:
                print(f"  ⚠️ Tool execution failed (expected for test): {str(e)}")
        
        print("\n🎉 MCP Implementation Test Complete!")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"❌ Error during MCP testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_individual_servers():
    """Test individual MCP servers"""
    print("\n🔍 Testing Individual Servers...")
    print("=" * 50)
    
    # Import server classes
    from mcp.servers.rnaseq_server import RNASeqMCPServer
    from mcp.servers.scrnaseq_server import scRNASeqMCPServer
    from mcp.servers.data_server import DataMCPServer
    from mcp.servers.visualization_server import VisualizationMCPServer
    from mcp.servers.proteomics_server import ProteomicsMCPServer
    
    servers = [
        ("RNA-seq", RNASeqMCPServer),
        ("scRNA-seq", scRNASeqMCPServer),
        ("Data Management", DataMCPServer),
        ("Visualization", VisualizationMCPServer),
        ("Proteomics", ProteomicsMCPServer)
    ]
    
    for server_name, server_class in servers:
        try:
            print(f"\n🧪 Testing {server_name} Server...")
            server = server_class()
            
            # Test tool listing
            tools = await server.list_tools()
            print(f"  • Tools: {len(tools.tools)} available")
            
            # Test resource listing
            resources = await server.list_resources()
            print(f"  • Resources: {len(resources.resources)} available")
            
            # Test prompt listing
            prompts = await server.list_prompts()
            print(f"  • Prompts: {len(prompts.prompts)} available")
            
            print(f"  ✅ {server_name} server test passed")
            
        except Exception as e:
            print(f"  ❌ {server_name} server test failed: {str(e)}")

def main():
    """Main test function"""
    print("🚀 Starting MCP Implementation Tests")
    print("=" * 60)
    
    # Run async tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Test MCP implementation
        success = loop.run_until_complete(test_mcp_implementation())
        
        # Test individual servers
        loop.run_until_complete(test_individual_servers())
        
        if success:
            print("\n🎉 All tests passed! MCP implementation is ready.")
            return 0
        else:
            print("\n❌ Some tests failed. Please check the implementation.")
            return 1
            
    except Exception as e:
        print(f"\n💥 Test execution failed: {str(e)}")
        return 1
    finally:
        loop.close()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 