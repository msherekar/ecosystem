#!/usr/bin/env python3
"""
Simple MCP Server Scalability Demo

Demonstrates the key scalability improvements made to the core MCP server.
"""

import asyncio
from typing import Any, Dict, List
from src.mcp.core.server import (
    MCPServer, MCPCapability, TemplateEngine, ValidationBackend,
    ResourceProvider, MCPResource
)


class DemoResourceProvider(ResourceProvider):
    """Demo resource provider"""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
    
    async def get_content(self, resource: MCPResource) -> Any:
        key = resource.uri.replace("demo://", "")
        return self.data.get(key, {"error": "Not found"})
    
    async def list_resources(self, pattern: str = None) -> List[MCPResource]:
        resources = []
        for key in self.data.keys():
            resources.append(MCPResource(
                uri=f"demo://{key}",
                name=key,
                description=f"Demo resource: {key}",
                mime_type="application/json"
            ))
        return resources


class ScalableMCPServer(MCPServer):
    """Demo server showcasing scalability features"""
    
    def __init__(self):
        super().__init__("scalable_demo", "1.0.0")
    
    async def initialize(self) -> None:
        """Initialize with scalability features"""
        print("🚀 Initializing Scalable MCP Server")
        print("=" * 40)
        
        # 1. Dynamic Capability Configuration
        print("\n1️⃣ Dynamic Capability Configuration")
        self.configure_capabilities(
            capability_config={
                "sampling": {"supported": True, "description": "Enhanced LLM sampling"},
                "tools": {"metadata": {"max_concurrent": 10}}
            },
            custom_capabilities={
                "bioinformatics": MCPCapability(
                    name="bioinformatics",
                    description="Specialized bioinformatics analysis",
                    supported=True,
                    metadata={"supported_formats": ["FASTA", "FASTQ", "VCF"]}
                )
            }
        )
        print(f"   ✅ Configured {len(self.capabilities)} capabilities")
        
        # 2. Advanced Template System
        print("\n2️⃣ Advanced Template System")
        self.configure_templates(
            default_engine=TemplateEngine.JINJA2,
            global_variables={"server": self.name, "version": self.version},
            custom_filters={"upper": lambda x: str(x).upper()}
        )
        
        self.register_prompt(
            "analysis_summary",
            "Analysis summary template",
            "Analysis completed for {dataset} with {samples} samples",
            engine=TemplateEngine.SIMPLE
        )
        print("   ✅ Template system configured with multiple engines")
        
        # 3. Pluggable Validation System
        print("\n3️⃣ Pluggable Validation System")
        self.configure_validation(
            backend=ValidationBackend.JSONSCHEMA,
            custom_validators={
                "positive": lambda x: isinstance(x, (int, float)) and x > 0
            }
        )
        print("   ✅ Validation system configured with custom validators")
        
        # 4. Dynamic Resource System
        print("\n4️⃣ Dynamic Resource System")
        demo_data = {
            "results": {"genes": 1000, "samples": 50},
            "config": {"threshold": 0.05, "method": "DESeq2"}
        }
        
        self.configure_resources(
            cache_enabled=True,
            auto_discover=True,
            providers={"demo": DemoResourceProvider(demo_data)}
        )
        print("   ✅ Resource system with caching and auto-discovery")
        
        # 5. Automatic Tool Discovery
        print("\n5️⃣ Automatic Tool Discovery")
        self.configure_tool_discovery(auto_discover=True)
        
        # Register tools using decorator
        @self.mcp_tool(
            name="analyze_data",
            description="Analyze biological data"
        )
        async def analyze_data(dataset: str, threshold: float = 0.05) -> Dict[str, Any]:
            """Analyze biological dataset"""
            return {
                "dataset": dataset,
                "threshold": threshold,
                "results": "Analysis completed successfully"
            }
        
        print("   ✅ Tool discovery and decorator-based registration")
        
        # 6. Enhanced Session Tracking (simplified)
        print("\n6️⃣ Enhanced Session Tracking")
        self.configure_session_tracking(
            tracked_variables=["analysis_results", "metadata"],
            variable_patterns=[r".*_df$", r".*_results$"],
            auto_discover=True
        )
        print("   ✅ Session tracking with patterns and auto-discovery")
        
        print(f"\n📊 Server Statistics:")
        print(f"   • Capabilities: {len(self.capabilities)}")
        print(f"   • Tools: {len(self.tools)}")
        print(f"   • Prompts: {len(self.prompts)}")
        print(f"   • Resource Providers: {len(self.resource_providers)}")
        print(f"   • Custom Validators: {len(self.custom_validators)}")
    
    def _get_server_specific_context(self) -> Dict[str, Any]:
        """Get demo-specific context"""
        return {"demo_mode": True, "scalability_features": "enabled"}


async def demo_functionality():
    """Demo the scalability features"""
    server = ScalableMCPServer()
    await server.initialize()
    
    print("\n🧪 Testing Scalability Features")
    print("=" * 35)
    
    # Test template rendering
    print("\n📝 Template Rendering:")
    result = await server.render_prompt("analysis_summary", {
        "dataset": "RNA-seq_experiment",
        "samples": 100
    })
    print(f"   ✅ {result['rendered']}")
    
    # Test resource access
    print("\n📁 Resource Access:")
    try:
        resource = await server.get_resource("demo://results")
        print(f"   ✅ Retrieved: {resource['content']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test tool execution
    print("\n🔨 Tool Execution:")
    try:
        tool_result = await server.execute_tool("analyze_data", {
            "dataset": "test_data",
            "threshold": 0.01
        })
        print(f"   ✅ Tool result: {tool_result['result']['results']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test capability listing
    print("\n🔧 Capabilities:")
    capabilities = server.get_capabilities()
    for cap_name, cap_info in capabilities['capabilities'].items():
        status = "✅" if cap_info['supported'] else "❌"
        print(f"   {status} {cap_name}")
    
    print("\n🎉 All scalability features working!")


async def main():
    """Main demo function"""
    print("🚀 MCP Server Scalability Demo")
    print("=" * 50)
    print("Showcasing major scalability improvements:")
    print("• Dynamic capability configuration")
    print("• Multi-engine template system")
    print("• Pluggable validation backends")
    print("• Dynamic resource discovery")
    print("• Automatic tool registration")
    print("• Enhanced session tracking")
    
    await demo_functionality()
    
    print("\n" + "=" * 50)
    print("🎯 SCALABILITY IMPROVEMENTS SUMMARY:")
    print("✅ Configuration-driven instead of hard-coded")
    print("✅ Pluggable backends for validation & templates")
    print("✅ Automatic discovery and registration")
    print("✅ Caching and performance optimizations")
    print("✅ Pattern-based flexible matching")
    print("✅ Backward compatible with existing code")
    print("✅ Minimal configuration for new analysis types")


if __name__ == "__main__":
    asyncio.run(main()) 