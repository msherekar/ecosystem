#!/usr/bin/env python3
"""
Dynamic Server Discovery Demonstration

This script demonstrates how the MCP architecture supports dynamic server discovery
and loading without requiring code changes to the core system.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp.core.registry import mcp_registry
from mcp.core.config import config_manager, ServerConfig


async def demonstrate_dynamic_discovery():
    """Demonstrate dynamic server discovery capabilities"""
    
    print("🔍 MCP Dynamic Server Discovery Demonstration")
    print("=" * 60)
    
    # 1. Show initial server configuration
    print("\n1. Initial Server Configuration:")
    print("-" * 40)
    
    enabled_servers = config_manager.get_enabled_servers()
    print(f"Enabled servers: {len(enabled_servers)}")
    for server in enabled_servers:
        print(f"  ✅ {server.name} ({server.class_path})")
    
    disabled_servers = [s for s in config_manager.server_configs.values() if not s.enabled]
    print(f"\nDisabled servers: {len(disabled_servers)}")
    for server in disabled_servers:
        print(f"  ❌ {server.name} ({server.class_path})")
    
    # 2. Initialize registry with current configuration
    print("\n2. Initializing MCP Registry:")
    print("-" * 40)
    
    success = await mcp_registry.initialize()
    print(f"Registry initialization: {'✅ Success' if success else '❌ Failed'}")
    
    # Show connected servers
    server_status = mcp_registry.get_server_status()
    print(f"Connected servers: {len(server_status)}")
    for name, status in server_status.items():
        print(f"  🔗 {name}: {status.get('status', 'unknown')}")
    
    # 3. Demonstrate dynamic server addition
    print("\n3. Dynamic Server Addition:")
    print("-" * 40)
    
    # Add a new server configuration dynamically
    new_server_config = ServerConfig(
        name="dynamic_test",
        class_path="src.mcp.servers.data_server.DataMCPServer",  # Reuse existing class for demo
        enabled=True,
        auto_connect=True,
        strategy="generic",
        priority=99,
        config={"demo_mode": True}
    )
    
    print(f"Adding new server: {new_server_config.name}")
    config_manager.register_server_config(new_server_config)
    
    # Add to registry
    success = mcp_registry.add_server_from_config("dynamic_test")
    print(f"Server addition: {'✅ Success' if success else '❌ Failed'}")
    
    # Connect the new server
    if success:
        connect_success = await mcp_registry.connect_server("dynamic_test")
        print(f"Server connection: {'✅ Success' if connect_success else '❌ Failed'}")
    
    # 4. Show updated server status
    print("\n4. Updated Server Status:")
    print("-" * 40)
    
    updated_status = mcp_registry.get_server_status()
    print(f"Total connected servers: {len(updated_status)}")
    for name, status in updated_status.items():
        print(f"  🔗 {name}: {status.get('status', 'unknown')}")
    
    # 5. Demonstrate configuration-based enabling
    print("\n5. Configuration-Based Server Enabling:")
    print("-" * 40)
    
    # Enable a previously disabled server
    rnaseq_config = config_manager.get_server_config("rnaseq")
    if rnaseq_config and not rnaseq_config.enabled:
        print("Enabling RNA-seq server...")
        rnaseq_config.enabled = True
        rnaseq_config.auto_connect = True
        
        # Add to registry and connect
        success = mcp_registry.add_server_from_config("rnaseq")
        if success:
            connect_success = await mcp_registry.connect_server("rnaseq")
            print(f"RNA-seq server: {'✅ Connected' if connect_success else '❌ Failed'}")
        else:
            print("❌ Failed to add RNA-seq server")
    
    # 6. Show available tools after dynamic changes
    print("\n6. Available Tools After Dynamic Changes:")
    print("-" * 40)
    
    available_tools = mcp_registry.get_available_tools()
    print(f"Total available tools: {len(available_tools)}")
    
    # Group tools by server
    tools_by_server = {}
    for tool_name, tool_info in available_tools.items():
        server = tool_info.get("server", "unknown")
        if server not in tools_by_server:
            tools_by_server[server] = []
        tools_by_server[server].append(tool_name)
    
    for server, tools in tools_by_server.items():
        print(f"  📦 {server}: {len(tools)} tools")
        for tool in tools[:3]:  # Show first 3 tools
            print(f"    - {tool}")
        if len(tools) > 3:
            print(f"    ... and {len(tools) - 3} more")
    
    # 7. Demonstrate health checking
    print("\n7. Health Check of All Servers:")
    print("-" * 40)
    
    health_status = await mcp_registry.health_check()
    for server, healthy in health_status.items():
        status_icon = "💚" if healthy else "💔"
        print(f"  {status_icon} {server}: {'Healthy' if healthy else 'Unhealthy'}")
    
    # 8. Show configuration validation
    print("\n8. Configuration Validation:")
    print("-" * 40)
    
    validation_issues = config_manager.validate_configuration()
    if validation_issues:
        print("⚠️  Configuration issues found:")
        for issue in validation_issues:
            print(f"  - {issue}")
    else:
        print("✅ Configuration is valid")
    
    # 9. Demonstrate saving configuration
    print("\n9. Saving Updated Configuration:")
    print("-" * 40)
    
    try:
        config_manager.save_configuration()
        print("✅ Configuration saved successfully")
        print("   - Updated servers.yaml with new configurations")
        print("   - Changes will persist across restarts")
    except Exception as e:
        print(f"❌ Failed to save configuration: {e}")


def demonstrate_class_loading():
    """Demonstrate dynamic class loading capabilities"""
    
    print("\n🔧 Dynamic Class Loading Demonstration")
    print("=" * 60)
    
    # Test loading different server classes
    test_classes = [
        "src.mcp.servers.scrnaseq_server.scRNASeqMCPServer",
        "src.mcp.servers.data_server.DataMCPServer",
        "src.mcp.servers.visualization_server.VisualizationMCPServer",
        "nonexistent.module.FakeServer"  # This should fail
    ]
    
    for class_path in test_classes:
        print(f"\nLoading: {class_path}")
        server_class = config_manager.load_server_class(class_path)
        
        if server_class:
            print(f"  ✅ Successfully loaded: {server_class.__name__}")
            print(f"  📝 Module: {server_class.__module__}")
            
            # Try to instantiate (if it's a real server class)
            try:
                if hasattr(server_class, '__init__'):
                    instance = server_class()
                    print(f"  🏗️  Instance created: {type(instance).__name__}")
            except Exception as e:
                print(f"  ⚠️  Cannot instantiate: {e}")
        else:
            print(f"  ❌ Failed to load class")


async def demonstrate_plugin_architecture():
    """Demonstrate how the system supports plugin-like architecture"""
    
    print("\n🔌 Plugin Architecture Demonstration")
    print("=" * 60)
    
    # Show how new analysis types can be added
    print("\n1. Adding New Analysis Type:")
    print("-" * 40)
    
    # This would be a real plugin in practice
    plugin_config = ServerConfig(
        name="example_plugin",
        class_path="src.mcp.servers.data_server.DataMCPServer",  # Using existing class for demo
        enabled=True,
        auto_connect=False,  # Manual connection for demo
        strategy="custom_analysis",
        priority=200,
        config={
            "plugin_name": "Example Analysis Plugin",
            "version": "1.0.0",
            "author": "Demo Developer",
            "capabilities": ["custom_analysis", "data_processing"]
        }
    )
    
    print(f"Plugin: {plugin_config.config['plugin_name']}")
    print(f"Version: {plugin_config.config['version']}")
    print(f"Author: {plugin_config.config['author']}")
    
    # Register the plugin
    config_manager.register_server_config(plugin_config)
    print("✅ Plugin registered in configuration")
    
    # Add to registry
    success = mcp_registry.add_server_from_config("example_plugin")
    print(f"Registry addition: {'✅ Success' if success else '❌ Failed'}")
    
    # Show all registered servers including plugins
    print("\n2. All Registered Servers:")
    print("-" * 40)
    
    all_servers = config_manager.server_configs
    for name, config in all_servers.items():
        status = "🟢 Enabled" if config.enabled else "🔴 Disabled"
        priority = f"Priority: {config.priority}"
        print(f"  {status} {name} ({priority})")
        if config.config:
            print(f"    Config: {list(config.config.keys())}")


if __name__ == "__main__":
    print("🚀 Starting MCP Dynamic Server Discovery Demo")
    print("This demonstrates how servers can be discovered and loaded dynamically")
    print("without requiring code changes to the core MCP system.\n")
    
    # Run demonstrations
    asyncio.run(demonstrate_dynamic_discovery())
    
    print("\n" + "=" * 80)
    demonstrate_class_loading()
    
    print("\n" + "=" * 80)
    asyncio.run(demonstrate_plugin_architecture())
    
    print("\n🎉 Demo completed!")
    print("\nKey takeaways:")
    print("- Servers are discovered from configuration files")
    print("- New servers can be added without code changes")
    print("- Classes are loaded dynamically using importlib")
    print("- Configuration changes can be saved and persisted")
    print("- The system supports plugin-like architecture")
    print("- Health checking ensures system reliability") 