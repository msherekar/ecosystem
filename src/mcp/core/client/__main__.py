#!/usr/bin/env python3
"""
MCP Client Package Main Entry Point

This module allows the MCP client package to be run directly:
    python -m src.mcp.core.client

It will run comprehensive demonstrations and tests of all client components.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Main entry point for the MCP client package"""
    print("🚀 MCP Client System - Main Entry Point")
    print("=" * 60)
    print("This will run demonstrations and tests of all MCP client components:")
    print("• MCPClient - Main client class")
    print("• ConnectionManager - Server connections and health monitoring")
    print("• CacheManager - Enterprise caching with security")
    print("• ExecutionEngine - Tool execution and load balancing")
    print("• ResponseFormatter - Response formatting and UI integration")
    print("• Integration Tests - Complete system testing")
    print("=" * 60)
    
    # Import components after logging setup
    try:
        from . import main as client_main
        from .connection_manager import main as connection_main
        from .cache_manager import main as cache_main
        from .execution_engine import main as execution_main
        from .response_formatter import main as formatter_main
        from .test_mcp_client_system import main as test_main
        
        print("\n📦 Running individual component demonstrations...")
        
        # Run each component's demo
        components = [
            ("Cache Manager", cache_main),
            ("Connection Manager", connection_main),
            ("Execution Engine", execution_main),
            ("Response Formatter", formatter_main),
            ("MCP Client", client_main),
        ]
        
        for component_name, component_main_func in components:
            print(f"\n{'='*20} {component_name} {'='*20}")
            try:
                result = component_main_func()
                if result:
                    print(f"✅ {component_name} demonstration completed successfully")
                else:
                    print(f"❌ {component_name} demonstration failed")
            except Exception as e:
                print(f"❌ {component_name} demonstration failed with error: {e}")
        
        # Run integration tests
        print(f"\n{'='*20} Integration Tests {'='*20}")
        try:
            asyncio.run(test_main())
            print("✅ Integration tests completed successfully")
        except Exception as e:
            print(f"❌ Integration tests failed with error: {e}")
        
        print(f"\n{'='*60}")
        print("🎉 MCP Client System demonstration completed!")
        print("📖 For detailed documentation, see:")
        print("   • src/mcp/core/client/readme_client.md")
        print("   • Individual module documentation")
        print(f"{'='*60}")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure all dependencies are installed and the Python path is correct.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
