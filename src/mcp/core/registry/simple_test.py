#!/usr/bin/env python3
"""
Comprehensive Test Runner for Registry Components

This script tests each registry component individually to verify they work correctly.
Tests all files in the registry folder for import issues and basic functionality.
"""

import os
import sys
import asyncio
import traceback
from typing import List, Tuple

def test_tool_registry() -> Tuple[bool, str]:
    """Test the tool registry module"""
    try:
        from tool_registry import (
            AutoToolRegistry, mcp_tool, get_auto_tool_configs, 
            ToolConfig, ToolParameter, ToolCategory, SecurityLevel
        )
        
        # Create a test handler
        class TestHandler:
            @mcp_tool(
                description="Test tool for validation",
                category=ToolCategory.ANALYSIS,
                security_level=SecurityLevel.PUBLIC
            )
            async def test_method(self, param1: str, param2: int = 10):
                return {"param1": param1, "param2": param2}
        
        # Test discovery
        registry = AutoToolRegistry()
        handler = TestHandler()
        tools = registry.discover_tools(handler)
        
        assert len(tools) == 1
        assert "test_method" in tools
        assert isinstance(tools["test_method"], ToolConfig)
        
        return True, "Tool registry works correctly"
    except Exception as e:
        return False, f"Tool registry failed: {e}\n{traceback.format_exc()}"

def test_resource_registry() -> Tuple[bool, str]:
    """Test the resource registry module"""
    try:
        from resource_registry import (
            AutoResourceRegistry, mcp_resource, get_auto_resource_configs,
            ResourceConfig, ResourceType, SecurityLevel
        )
        
        # Create a test handler
        class TestHandler:
            @mcp_resource(
                uri="test://data/sample",
                name="Test Data",
                description="Test resource for validation",
                resource_type=ResourceType.DATA
            )
            async def get_test_data(self):
                return {"data": "test"}
        
        # Test discovery
        registry = AutoResourceRegistry()
        handler = TestHandler()
        resources = registry.discover_resources(handler)
        
        assert len(resources) == 1
        assert "test://data/sample" in resources
        assert isinstance(resources["test://data/sample"], ResourceConfig)
        
        return True, "Resource registry works correctly"
    except Exception as e:
        return False, f"Resource registry failed: {e}\n{traceback.format_exc()}"

def test_prompt_registry() -> Tuple[bool, str]:
    """Test the prompt registry module"""
    try:
        from .prompt_registry import (
            AutoPromptRegistry, mcp_prompt, get_auto_prompt_configs,
            PromptConfig, PromptCategory, SecurityLevel
        )
        
        # Create a test handler
        class TestHandler:
            @mcp_prompt(
                name="test_prompt",
                description="Test prompt for validation",
                parameters={"param": "string"},
                category=PromptCategory.ANALYSIS
            )
            def test_prompt(self):
                return "Test prompt template with {param}"
        
        # Test discovery
        registry = AutoPromptRegistry()
        handler = TestHandler()
        prompts = registry.discover_prompts(handler)
        
        assert len(prompts) >= 1
        assert "test_prompt" in prompts
        assert isinstance(prompts["test_prompt"], PromptConfig)
        
        return True, "Prompt registry works correctly"
    except Exception as e:
        return False, f"Prompt registry failed: {e}\n{traceback.format_exc()}"

def test_prompt_templates() -> Tuple[bool, str]:
    """Test the prompt templates module"""
    try:
        from prompt_templates import CommonPromptTemplates, PromptTemplate, TemplateCategory
        
        # Test getting all templates
        templates = CommonPromptTemplates.get_all_templates()
        assert len(templates) > 0
        
        # Test specific template
        next_steps = CommonPromptTemplates.suggest_next_steps_template()
        assert isinstance(next_steps, PromptTemplate)
        assert next_steps.category == TemplateCategory.GUIDANCE
        
        # Test template rendering
        test_params = {param: f"test_{param}" for param in next_steps.parameters}
        rendered = next_steps.render(**test_params)
        assert len(rendered) > 0
        
        return True, "Prompt templates work correctly"
    except Exception as e:
        return False, f"Prompt templates failed: {e}\n{traceback.format_exc()}"

def test_prompt_domain_integration() -> Tuple[bool, str]:
    """Test the prompt domain integration module"""
    try:
        from prompt_domain_integration import (
            TechniqueDetector, DomainExpertMock, DomainExpertIntegration,
            get_domain_prompts_for_handler, get_supported_techniques
        )
        
        # Test technique detection
        detector = TechniqueDetector()
        technique = detector.extract_technique_from_class("scRNASeqHandler")
        assert technique == "scrnaseq"
        
        # Test domain expert mock
        expert = DomainExpertMock()
        prompts = expert.get_prompts("scrnaseq")
        assert len(prompts) > 0
        
        # Test supported techniques
        techniques = get_supported_techniques()
        assert len(techniques) > 0
        
        return True, "Prompt domain integration works correctly"
    except Exception as e:
        return False, f"Prompt domain integration failed: {e}\n{traceback.format_exc()}"

def test_registry_config() -> Tuple[bool, str]:
    """Test the registry configuration module"""
    try:
        from registry_config import (
            ConfigurationLoader, ServerClassLoader, ConfigurationManager,
            ServerConfiguration
        )
        
        # Test configuration loader
        loader = ConfigurationLoader()
        config = loader._get_default_configuration()
        assert "servers" in config
        assert len(config["servers"]) > 0
        
        # Test configuration manager
        manager = ConfigurationManager()
        servers = manager.get_enabled_servers()
        assert isinstance(servers, list)
        
        # Test validation
        issues = manager.validate_configuration()
        assert isinstance(issues, list)
        
        return True, "Registry configuration works correctly"
    except Exception as e:
        return False, f"Registry configuration failed: {e}\n{traceback.format_exc()}"

def test_registry_analysis() -> Tuple[bool, str]:
    """Test the registry analysis module"""
    try:
        from registry_analysis import (
            AnalysisProviderFactory, InsightAggregator, ContextFormatter,
            AnalysisInsight, SuggestedAction, InsightPriority, ActionType
        )
        
        # Test provider factory
        factory = AnalysisProviderFactory()
        provider = factory.get_provider("test_analysis")
        assert provider is not None
        
        # Test insight aggregator
        aggregator = InsightAggregator()
        mock_contexts = {"test": {"server_type": "test", "data_uploaded": True}}
        insights = aggregator.get_analysis_insights(mock_contexts)
        assert isinstance(insights, str)
        
        # Test context formatter
        formatter = ContextFormatter(aggregator)
        context = formatter.format_context_for_agent(mock_contexts, 5, 3, 2)
        assert isinstance(context, str)
        assert len(context) > 0
        
        return True, "Registry analysis works correctly"
    except Exception as e:
        return False, f"Registry analysis failed: {e}\n{traceback.format_exc()}"

def test_registry_health() -> Tuple[bool, str]:
    """Test the registry health monitoring module"""
    try:
        from registry_health import (
            HealthCheck, HealthResult, HealthStatus, HealthMonitor
        )
        
        # Test health check creation
        async def dummy_check():
            return HealthResult(
                name="test_check",
                status=HealthStatus.HEALTHY,
                message="Test passed",
                timestamp=0,
                duration_ms=10.0,
                critical=False
            )
        
        health_check = HealthCheck(
            name="test_check",
            description="Test health check",
            check_function=dummy_check
        )
        
        assert health_check.name == "test_check"
        assert health_check.timeout_seconds == 5.0
        
        return True, "Registry health monitoring works correctly"
    except Exception as e:
        return False, f"Registry health monitoring failed: {e}\n{traceback.format_exc()}"

def test_registry_metrics() -> Tuple[bool, str]:
    """Test the registry metrics module"""
    try:
        from registry_metrics import (
            MetricsCollector, MetricsAggregator, MetricType, MetricData,
            get_global_metrics, get_metrics_aggregator
        )
        
        # Test metrics collector
        metrics = MetricsCollector()
        metrics.increment_counter("test_counter", 5)
        metrics.set_gauge("test_gauge", 42.5)
        metrics.record_timer("test_timer", 123.4)
        
        # Test getting metrics
        summary = metrics.get_metric_summary("test_counter")
        assert summary["latest_value"] == 5
        
        # Test global metrics
        global_metrics = get_global_metrics()
        assert isinstance(global_metrics, MetricsCollector)
        
        return True, "Registry metrics work correctly"
    except Exception as e:
        return False, f"Registry metrics failed: {e}\n{traceback.format_exc()}"

def test_main_registry() -> Tuple[bool, str]:
    """Test the main registry module"""
    try:
        from registry import MCPRegistry, mcp_registry, get_mcp_registry
        
        # Test registry creation (without full initialization)
        registry = MCPRegistry()
        
        # Basic checks
        assert hasattr(registry, 'client')
        assert hasattr(registry, 'server_configs')
        assert hasattr(registry, 'connection_manager')
        assert hasattr(registry, 'capability_aggregator')
        
        # Test global registry
        assert mcp_registry is not None
        
        return True, "Main registry works correctly"
    except Exception as e:
        return False, f"Main registry failed: {e}\n{traceback.format_exc()}"

def test_main_orchestrator() -> Tuple[bool, str]:
    """Test the main orchestrator module"""
    try:
        # Import from the __main__.py file in the registry
        import sys
        import importlib.util
        
        # Get the path to __main__.py
        main_path = os.path.join(os.path.dirname(__file__), '__main__.py')
        
        # Load the module
        spec = importlib.util.spec_from_file_location("__main__", main_path)
        main_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_module)
        
        # Get the classes
        MCPRegistryOrchestrator = main_module.MCPRegistryOrchestrator
        get_orchestrator = main_module.get_orchestrator
        
        # Test orchestrator creation
        orchestrator = MCPRegistryOrchestrator()
        assert orchestrator is not None
        assert hasattr(orchestrator, 'registry')
        assert hasattr(orchestrator, 'startup_time')
        
        # Test global orchestrator
        global_orchestrator = get_orchestrator()
        assert global_orchestrator is not None
        
        return True, "Main orchestrator works correctly"
    except Exception as e:
        return False, f"Main orchestrator failed: {e}\n{traceback.format_exc()}"

def test_init_imports() -> Tuple[bool, str]:
    """Test that __init__.py imports work correctly"""
    try:
        # Test importing from the package by loading __init__.py
        import importlib.util
        
        # Get the path to __init__.py
        init_path = os.path.join(os.path.dirname(__file__), '__init__.py')
        
        # Load the module
        spec = importlib.util.spec_from_file_location("registry_init", init_path)
        init_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(init_module)
        
        # Get the imports
        MCPRegistry = init_module.MCPRegistry
        mcp_registry = init_module.mcp_registry
        get_mcp_registry = init_module.get_mcp_registry
        ToolConfig = init_module.ToolConfig
        ToolParameter = init_module.ToolParameter
        mcp_tool = init_module.mcp_tool
        AutoToolRegistry = init_module.AutoToolRegistry
        get_auto_tool_configs = init_module.get_auto_tool_configs
        ResourceConfig = init_module.ResourceConfig
        mcp_resource = init_module.mcp_resource
        AutoResourceRegistry = init_module.AutoResourceRegistry
        get_auto_resource_configs = init_module.get_auto_resource_configs
        PromptConfig = init_module.PromptConfig
        mcp_prompt = init_module.mcp_prompt
        AutoPromptRegistry = init_module.AutoPromptRegistry
        get_auto_prompt_configs = init_module.get_auto_prompt_configs
        CommonPromptTemplates = init_module.CommonPromptTemplates
        get_domain_prompts_for_handler = init_module.get_domain_prompts_for_handler
        get_supported_techniques = init_module.get_supported_techniques
        
        # Basic validation
        assert MCPRegistry is not None
        assert mcp_registry is not None
        assert CommonPromptTemplates is not None
        
        return True, "__init__.py imports work correctly"
    except Exception as e:
        return False, f"__init__.py imports failed: {e}\n{traceback.format_exc()}"

def main():
    """Run all tests"""
    print("🚀 Comprehensive Registry Components Test Suite")
    print("=" * 80)
    
    # Change to the registry directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Define all tests
    tests = [
        ("Tool Registry", test_tool_registry),
        ("Resource Registry", test_resource_registry),
        ("Prompt Registry", test_prompt_registry),
        ("Prompt Templates", test_prompt_templates),
        ("Prompt Domain Integration", test_prompt_domain_integration),
        ("Registry Configuration", test_registry_config),
        ("Registry Analysis", test_registry_analysis),
        ("Registry Health", test_registry_health),
        ("Registry Metrics", test_registry_metrics),
        ("Main Registry", test_main_registry),
        ("Main Orchestrator", test_main_orchestrator),
        ("__init__.py Imports", test_init_imports),
    ]
    
    # Run all tests
    results = []
    details = []
    
    for test_name, test_func in tests:
        print(f"\n🔧 Testing {test_name}...")
        try:
            success, message = test_func()
            results.append(success)
            
            if success:
                print(f"   ✅ {message}")
            else:
                print(f"   ❌ {message}")
                details.append(f"\n{test_name} Details:\n{message}")
                
        except Exception as e:
            results.append(False)
            error_msg = f"Test execution failed: {e}\n{traceback.format_exc()}"
            print(f"   ❌ {error_msg}")
            details.append(f"\n{test_name} Execution Error:\n{error_msg}")
    
    # Summary
    print("\n" + "=" * 80)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 All {total} tests passed!")
        print("✅ Registry system is ready for use!")
        success = True
    else:
        print(f"❌ {total - passed} out of {total} tests failed")
        
        # Show details for failed tests
        if details:
            print("\n📋 Failure Details:")
            for detail in details:
                print(detail)
        
        success = False
    
    print("\n" + "=" * 80)
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 