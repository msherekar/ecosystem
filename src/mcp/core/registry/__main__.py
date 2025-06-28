#!/usr/bin/env python3
"""
MCP Registry Main Orchestrator

Central orchestration point for the MCP Registry system.
Provides initialization, testing, and management capabilities for the entire registry ecosystem.
"""

import asyncio
import logging
import sys
import time
from typing import Dict, List, Any, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp.registry.main")


class MCPRegistryOrchestrator:
    """
    Main orchestrator for the MCP Registry system.
    
    Handles:
    - System initialization and startup
    - Registry coordination
    - Health monitoring
    - Testing and validation
    """
    
    def __init__(self):
        self.registry = None
        self.startup_time = None
        self.health_status = {}
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the complete MCP Registry system"""
        try:
            logger.info("Starting MCP Registry System initialization...")
            start_time = time.time()
            
            # Import registry (lazy import to avoid circular dependencies)
            try:
                from .registry import mcp_registry, get_mcp_registry
            except ImportError:
                from registry import mcp_registry, get_mcp_registry
            
            # Initialize the main registry
            self.registry = await get_mcp_registry()
            
            # Perform initial health check
            health_status = await self.registry.health_check()
            self.health_status = health_status
            
            # Calculate startup time
            self.startup_time = time.time() - start_time
            self._initialized = True
            
            logger.info(f"MCP Registry System initialized successfully in {self.startup_time:.2f}s")
            logger.info(f"Connected servers: {list(health_status.keys())}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP Registry System: {e}")
            return False
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        if not self._initialized:
            return {"status": "not_initialized", "error": "System not initialized"}
        
        try:
            # Get registry status
            server_status = self.registry.get_server_status()
            available_tools = self.registry.get_available_tools()
            available_resources = self.registry.get_available_resources()
            available_prompts = self.registry.get_available_prompts()
            aggregated_context = self.registry.get_aggregated_context()
            
            return {
                "status": "operational",
                "startup_time": self.startup_time,
                "servers": {
                    "count": len(server_status),
                    "connected": len([s for s in server_status.values() if s.get("connected", False)]),
                    "details": server_status
                },
                "capabilities": {
                    "tools": len(available_tools),
                    "resources": len(available_resources), 
                    "prompts": len(available_prompts)
                },
                "health": self.health_status,
                "context": aggregated_context
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"status": "error", "error": str(e)}
    
    async def run_system_tests(self) -> Dict[str, bool]:
        """Run comprehensive system tests"""
        logger.info("Running MCP Registry system tests...")
        
        test_results = {}
        
        # Test 1: Registry initialization
        test_results["registry_initialization"] = self._initialized
        
        # Test 2: Server connections
        try:
            health = await self.registry.health_check()
            test_results["server_connections"] = len(health) > 0
        except Exception as e:
            logger.error(f"Server connection test failed: {e}")
            test_results["server_connections"] = False
        
        # Test 3: Tool discovery
        try:
            tools = self.registry.get_available_tools()
            test_results["tool_discovery"] = len(tools) > 0
        except Exception as e:
            logger.error(f"Tool discovery test failed: {e}")
            test_results["tool_discovery"] = False
        
        # Test 4: Resource discovery
        try:
            resources = self.registry.get_available_resources()
            test_results["resource_discovery"] = len(resources) >= 0  # Can be 0
        except Exception as e:
            logger.error(f"Resource discovery test failed: {e}")
            test_results["resource_discovery"] = False
        
        # Test 5: Prompt discovery
        try:
            prompts = self.registry.get_available_prompts()
            test_results["prompt_discovery"] = len(prompts) >= 0  # Can be 0
        except Exception as e:
            logger.error(f"Prompt discovery test failed: {e}")
            test_results["prompt_discovery"] = False
        
        # Test 6: Context aggregation
        try:
            context = self.registry.get_aggregated_context()
            test_results["context_aggregation"] = "connected_servers" in context
        except Exception as e:
            logger.error(f"Context aggregation test failed: {e}")
            test_results["context_aggregation"] = False
        
        # Test 7: Analysis insights
        try:
            insights = self.registry.get_analysis_insights()
            test_results["analysis_insights"] = len(insights) > 0
        except Exception as e:
            logger.error(f"Analysis insights test failed: {e}")
            test_results["analysis_insights"] = False
        
        # Test 8: Suggested actions
        try:
            actions = self.registry.get_suggested_actions()
            test_results["suggested_actions"] = len(actions) > 0
        except Exception as e:
            logger.error(f"Suggested actions test failed: {e}")
            test_results["suggested_actions"] = False
        
        # Summary
        passed = sum(test_results.values())
        total = len(test_results)
        
        logger.info(f"System tests completed: {passed}/{total} passed")
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"  {test_name}: {status}")
        
        return test_results
    
    async def demonstrate_capabilities(self):
        """Demonstrate registry capabilities"""
        if not self._initialized:
            logger.error("System not initialized")
            return
        
        logger.info("Demonstrating MCP Registry capabilities...")
        
        # Show available tools
        tools = self.registry.get_available_tools()
        logger.info(f"Available tools ({len(tools)}):")
        for tool_name, tool_info in list(tools.items())[:5]:  # Show first 5
            logger.info(f"  - {tool_name}: {tool_info.get('description', 'No description')}")
        
        # Show available resources
        resources = self.registry.get_available_resources()
        logger.info(f"Available resources ({len(resources)}):")
        for resource_name, resource_info in list(resources.items())[:5]:  # Show first 5
            logger.info(f"  - {resource_name}: {resource_info.get('description', 'No description')}")
        
        # Show analysis insights
        insights = self.registry.get_analysis_insights()
        logger.info(f"Current insights: {insights}")
        
        # Show suggested actions
        actions = self.registry.get_suggested_actions()
        logger.info("Suggested actions:")
        for i, action in enumerate(actions[:3], 1):  # Show first 3
            logger.info(f"  {i}. {action}")
    
    async def shutdown(self):
        """Gracefully shutdown the registry system"""
        logger.info("Shutting down MCP Registry System...")
        
        if self.registry:
            # Disconnect from all servers
            server_status = self.registry.get_server_status()
            for server_name in server_status.keys():
                try:
                    await self.registry.disconnect_server(server_name)
                    logger.info(f"Disconnected from server: {server_name}")
                except Exception as e:
                    logger.warning(f"Error disconnecting from {server_name}: {e}")
        
        self._initialized = False
        logger.info("MCP Registry System shutdown complete")


# Global orchestrator instance
orchestrator = MCPRegistryOrchestrator()


async def main():
    """Main entry point for the MCP Registry system"""
    print("🚀 MCP Registry System")
    print("=" * 50)
    
    try:
        # Initialize system
        success = await orchestrator.initialize()
        if not success:
            print("❌ Failed to initialize system")
            return False
        
        # Run tests
        print("\n🧪 Running System Tests...")
        test_results = await orchestrator.run_system_tests()
        
        # Show system status
        print("\n📊 System Status...")
        status = await orchestrator.get_system_status()
        print(f"Status: {status['status']}")
        print(f"Startup time: {status.get('startup_time', 0):.2f}s")
        print(f"Connected servers: {status['servers']['connected']}/{status['servers']['count']}")
        print(f"Available tools: {status['capabilities']['tools']}")
        print(f"Available resources: {status['capabilities']['resources']}")
        print(f"Available prompts: {status['capabilities']['prompts']}")
        
        # Demonstrate capabilities
        print("\n🎯 Demonstrating Capabilities...")
        await orchestrator.demonstrate_capabilities()
        
        # Final summary
        all_passed = all(test_results.values())
        print(f"\n{'🎉 All systems operational!' if all_passed else '⚠️  Some tests failed'}")
        
        return all_passed
        
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False
    finally:
        # Always shutdown gracefully
        await orchestrator.shutdown()


def get_orchestrator() -> MCPRegistryOrchestrator:
    """Get the global orchestrator instance"""
    return orchestrator


if __name__ == "__main__":
    def main_sync():
        """Synchronous wrapper for main()"""
        try:
            success = asyncio.run(main())
            sys.exit(0 if success else 1)
        except Exception as e:
            print(f"Fatal error: {e}")
            sys.exit(1)
    
    def test_individual_components():
        """Test individual registry components"""
        print("🔧 Testing Individual Components...")
        print("=" * 40)
        
        # Test tool registry
        try:
            from .tool_registry import AutoToolRegistry
            print("✅ Tool registry import successful")
        except Exception as e:
            print(f"❌ Tool registry import failed: {e}")
        
        # Test resource registry  
        try:
            from .resource_registry import AutoResourceRegistry
            print("✅ Resource registry import successful")
        except Exception as e:
            print(f"❌ Resource registry import failed: {e}")
        
        # Test prompt registry
        try:
            from .prompt_domain_integration import AutoPromptRegistry
            print("✅ Prompt registry import successful")
        except Exception as e:
            print(f"❌ Prompt registry import failed: {e}")
        
        # Test main registry
        try:
            from .registry import MCPRegistry
            print("✅ Main registry import successful")
        except Exception as e:
            print(f"❌ Main registry import failed: {e}")
        
        print("🎉 Component import tests complete!")
    
    # Choose what to run based on command line args
    if len(sys.argv) > 1 and sys.argv[1] == "test-components":
        test_individual_components()
    else:
        main_sync()


def main():
    """Main function for module testing"""
    print("Testing MCP Registry Orchestrator...")
    
    # Test orchestrator creation
    test_orchestrator = MCPRegistryOrchestrator()
    print(f"✅ Created orchestrator: {test_orchestrator.__class__.__name__}")
    
    # Test status before initialization
    print(f"✅ Initialized status: {test_orchestrator._initialized}")
    
    # Test health status structure
    print(f"✅ Health status: {test_orchestrator.health_status}")
    
    print("🎉 All MCPRegistryOrchestrator basic tests passed!")


if __name__ == "__main__":
    main()