#!/usr/bin/env python3
"""
Simple Test Runner for Registry Components

This script tests each registry component individually to verify they work correctly.
"""

import os
import sys

def test_tool_registry():
    """Test the tool registry module"""
    print("🔧 Testing Tool Registry...")
    
    # Import and test tool registry 
    try:
        from tool_registry import AutoToolRegistry, mcp_tool, get_auto_tool_configs
        
        # Create a test handler
        class TestHandler:
            @mcp_tool(description="Test tool", category="test")
            async def test_method(self, param1: str, param2: int = 10):
                return {"param1": param1, "param2": param2}
        
        # Test discovery
        registry = AutoToolRegistry()
        handler = TestHandler()
        tools = registry.discover_tools(handler)
        
        assert len(tools) == 1
        assert "test_method" in tools
        
        print("   ✅ Tool registry works correctly")
        return True
    except Exception as e:
        print(f"   ❌ Tool registry failed: {e}")
        return False

def test_resource_registry():
    """Test the resource registry module"""
    print("🔧 Testing Resource Registry...")
    
    try:
        from resource_registry import AutoResourceRegistry, mcp_resource, get_auto_resource_configs
        
        # Create a test handler
        class TestHandler:
            @mcp_resource(uri="test://data", name="Test Data", description="Test resource")
            async def get_test_data(self):
                return {"data": "test"}
        
        # Test discovery
        registry = AutoResourceRegistry()
        handler = TestHandler()
        resources = registry.discover_resources(handler)
        
        assert len(resources) == 1
        assert "test://data" in resources
        
        print("   ✅ Resource registry works correctly")
        return True
    except Exception as e:
        print(f"   ❌ Resource registry failed: {e}")
        return False

def test_prompt_registry():
    """Test the prompt registry module"""
    print("🔧 Testing Prompt Registry...")
    
    try:
        from prompt_registry import AutoPromptRegistry, mcp_prompt, get_auto_prompt_configs, CommonPromptTemplates
        
        # Create a test handler
        class TestHandler:
            @mcp_prompt(name="test_prompt", description="Test prompt", parameters={"param": "string"})
            def test_prompt(self):
                return "Test prompt template"
        
        # Test discovery
        registry = AutoPromptRegistry()
        handler = TestHandler()
        prompts = registry.discover_prompts(handler)
        
        assert len(prompts) >= 1
        assert "test_prompt" in prompts
        
        # Test common templates
        template = CommonPromptTemplates.suggest_next_steps()
        assert len(template) > 0
        
        print("   ✅ Prompt registry works correctly")
        return True
    except Exception as e:
        print(f"   ❌ Prompt registry failed: {e}")
        return False

def test_main_registry():
    """Test the main registry module"""
    print("🔧 Testing Main Registry...")
    
    try:
        from registry import MCPRegistry
        
        # Test registry creation (without full initialization)
        registry = MCPRegistry()
        
        # Basic checks
        assert hasattr(registry, 'client')
        assert hasattr(registry, 'server_configs')
        
        print("   ✅ Main registry works correctly")
        return True
    except Exception as e:
        print(f"   ❌ Main registry failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Registry Components Test Suite")
    print("=" * 50)
    
    # Change to the registry directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Run all tests
    results = []
    results.append(test_tool_registry())
    results.append(test_resource_registry())
    results.append(test_prompt_registry())
    results.append(test_main_registry())
    
    # Summary
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 All {total} tests passed!")
        print("✅ Registry system is ready for use!")
        return True
    else:
        print(f"❌ {total - passed} out of {total} tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 