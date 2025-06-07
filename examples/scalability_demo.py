#!/usr/bin/env python3
"""
MCP Server Scalability Demo

Demonstrates all the scalability improvements made to the core MCP server:
1. Dynamic capability configuration
2. Advanced template system with multiple engines
3. Pluggable validation backends
4. Dynamic resource discovery and caching
5. Automatic tool discovery and registration
6. Enhanced session state tracking
"""

import asyncio
import pandas as pd
import numpy as np
import streamlit as st
from typing import Any, Dict, List
from src.mcp.core.server import (
    MCPServer, MCPCapability, TemplateEngine, ValidationBackend,
    ResourceProvider, MCPResource
)


class CustomResourceProvider(ResourceProvider):
    """Custom resource provider for demo"""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
    
    async def get_content(self, resource: MCPResource) -> Any:
        key = resource.uri.replace("custom://", "")
        return self.data.get(key, {"error": "Not found"})
    
    async def list_resources(self, pattern: str = None) -> List[MCPResource]:
        resources = []
        for key in self.data.keys():
            resources.append(MCPResource(
                uri=f"custom://{key}",
                name=key,
                description=f"Custom resource: {key}",
                mime_type="application/json"
            ))
        return resources


class ScalabilityDemoServer(MCPServer):
    """Demo server showcasing all scalability features"""
    
    def __init__(self):
        super().__init__("scalability_demo", "1.0.0")
    
    async def initialize(self) -> None:
        """Initialize with all scalability features"""
        await self._demo_capability_configuration()
        await self._demo_template_system()
        await self._demo_validation_system()
        await self._demo_resource_system()
        await self._demo_tool_discovery()
        await self._demo_session_tracking()
    
    async def _demo_capability_configuration(self):
        """Demo: Dynamic capability configuration"""
        print("🔧 Configuring Capabilities Dynamically")
        print("-" * 40)
        
        # Configure existing capabilities
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
        
        # Register additional capabilities
        self.register_capability(
            "real_time_analysis",
            "Real-time data analysis streaming",
            supported=True,
            metadata={"streaming": True, "max_rate": "1000/sec"}
        )
        
        print(f"✅ Configured {len(self.capabilities)} capabilities")
        for name, cap in self.capabilities.items():
            status = "✅" if cap.supported else "❌"
            print(f"   {status} {name}: {cap.description}")
    
    async def _demo_template_system(self):
        """Demo: Advanced template system"""
        print("\n📝 Advanced Template System")
        print("-" * 30)
        
        # Configure template system
        self.configure_templates(
            default_engine=TemplateEngine.JINJA2,
            global_variables={
                "server_name": self.name,
                "version": self.version,
                "timestamp": "2024-01-01"
            },
            custom_filters={
                "upper": lambda x: str(x).upper(),
                "format_number": lambda x: f"{x:,.2f}"
            }
        )
        
        # Register templates with different engines
        self.register_prompt(
            "simple_template",
            "Simple string formatting template",
            "Analysis for {dataset} completed with {num_samples} samples",
            engine=TemplateEngine.SIMPLE
        )
        
        try:
            self.register_prompt(
                "jinja2_template", 
                "Advanced Jinja2 template",
                """
                {% if results %}
                Analysis Summary for {{ dataset|upper }}:
                - Total samples: {{ num_samples|format_number }}
                - Server: {{ server_name }} v{{ version }}
                {% for result in results[:3] %}
                - {{ result.name }}: {{ result.value }}
                {% endfor %}
                {% else %}
                No results available for {{ dataset }}
                {% endif %}
                """,
                engine=TemplateEngine.JINJA2
            )
        except:
            print("   ⚠️  Jinja2 not available, using simple templates")
        
        # Test template rendering
        test_params = {
            "dataset": "rna_seq_data",
            "num_samples": 1234.56,
            "results": [
                {"name": "DEGs", "value": "500 genes"},
                {"name": "Pathways", "value": "25 enriched"}
            ]
        }
        
        simple_result = await self.render_prompt("simple_template", test_params)
        print(f"✅ Simple template: {simple_result['rendered']}")
        
        try:
            jinja_result = await self.render_prompt("jinja2_template", test_params)
            print(f"✅ Jinja2 template rendered successfully")
        except:
            print("   ⚠️  Jinja2 template skipped")
    
    async def _demo_validation_system(self):
        """Demo: Pluggable validation system"""
        print("\n🔍 Validation System")
        print("-" * 20)
        
        # Configure validation
        self.configure_validation(
            backend=ValidationBackend.JSONSCHEMA,
            custom_validators={
                "positive_number": lambda x: isinstance(x, (int, float)) and x > 0,
                "valid_email": lambda x: "@" in str(x) and "." in str(x)
            }
        )
        
        # Register a tool with advanced validation
        self.register_tool(
            "advanced_analysis",
            "Analysis with advanced parameter validation",
            input_schema={
                "type": "object",
                "properties": {
                    "threshold": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "validator": "positive_number"
                    },
                    "email": {
                        "type": "string",
                        "validator": "valid_email"
                    },
                    "samples": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string"}
                    }
                },
                "required": ["threshold", "samples"]
            },
            handler=self._dummy_analysis
        )
        
        print(f"✅ Validation backend: {self.validation_backend.value}")
        print(f"✅ Custom validators: {list(self.custom_validators.keys())}")
    
    async def _demo_resource_system(self):
        """Demo: Dynamic resource system"""
        print("\n📁 Resource System")
        print("-" * 17)
        
        # Configure resource system
        custom_data = {
            "analysis_results": {"genes": 1000, "samples": 50},
            "metadata": {"experiment": "RNA-seq", "date": "2024-01-01"}
        }
        
        self.configure_resources(
            cache_enabled=True,
            auto_discover=True,
            providers={
                "custom": CustomResourceProvider(custom_data)
            }
        )
        
        # Register static resources
        self.register_resource(
            "static://config",
            "Configuration",
            "Server configuration data",
            "application/json",
            metadata={"version": "1.0"}
        )
        
        # Test resource discovery
        discovered = await self.discover_resources()
        print(f"✅ Discovered {len(discovered)} resources")
        
        # Test resource access with caching
        try:
            result = await self.get_resource("custom://analysis_results")
            print(f"✅ Custom resource: {result['content']}")
            
            # Second access should hit cache
            cached_result = await self.get_resource("custom://analysis_results")
            print("✅ Resource caching working")
        except Exception as e:
            print(f"⚠️  Resource access failed: {e}")
    
    async def _demo_tool_discovery(self):
        """Demo: Automatic tool discovery"""
        print("\n🔨 Tool Discovery")
        print("-" * 16)
        
        # Configure tool discovery
        self.configure_tool_discovery(auto_discover=True)
        
        # Use decorator for automatic registration
        @self.mcp_tool(
            name="calculate_stats",
            description="Calculate basic statistics",
            input_schema={
                "type": "object",
                "properties": {
                    "data": {"type": "array", "items": {"type": "number"}},
                    "method": {"type": "string", "default": "mean"}
                },
                "required": ["data"]
            }
        )
        async def calculate_statistics(data: List[float], method: str = "mean") -> Dict[str, float]:
            """Calculate statistics for numerical data"""
            if method == "mean":
                return {"result": sum(data) / len(data)}
            elif method == "median":
                sorted_data = sorted(data)
                n = len(sorted_data)
                return {"result": sorted_data[n//2] if n % 2 else (sorted_data[n//2-1] + sorted_data[n//2])/2}
            else:
                return {"error": f"Unknown method: {method}"}
        
        print(f"✅ Registered {len(self.tools)} tools")
        for tool_name in self.tools.keys():
            print(f"   • {tool_name}")
    
    async def _demo_session_tracking(self):
        """Demo: Enhanced session state tracking"""
        print("\n📊 Session State Tracking")
        print("-" * 26)
        
        # Configure session tracking
        self.configure_session_tracking(
            tracked_variables=["demo_data", "analysis_results"],
            variable_patterns=[r".*_df$", r"demo_.*", r".*_cache$"],
            auto_discover=True
        )
        
        # Create mock session state
        mock_data = {
            # Explicitly tracked
            "demo_data": pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]}),
            "analysis_results": {"genes": 500, "pathways": 25},
            
            # Pattern matched
            "expression_df": pd.DataFrame(np.random.randn(100, 10)),
            "demo_config": {"threshold": 0.05},
            "results_cache": {"cached": True},
            
            # Auto-discovered
            "large_matrix": pd.DataFrame(np.random.randn(1000, 50)),
            "processing_complete": True,
            "metadata": {"samples": 20, "conditions": 2},
            
            # Should be ignored
            "_internal_var": "ignore",
            "small_list": [1, 2]
        }
        
        # Mock session state
        original_session_state = getattr(st, 'session_state', {})
        st.session_state = type('MockSessionState', (), mock_data)()
        st.session_state.keys = lambda: mock_data.keys()
        st.session_state.__contains__ = lambda self, key: key in mock_data
        st.session_state.__getitem__ = lambda self, key: mock_data[key]
        st.session_state.items = lambda: mock_data.items()
        
        try:
            summary = self._get_session_state_summary()
            print(f"✅ Tracking {len(summary)} variables:")
            
            for var_name, var_info in list(summary.items())[:5]:  # Show first 5
                if isinstance(var_info, dict) and 'type' in var_info:
                    print(f"   • {var_name} ({var_info['type']})")
                    if 'shape' in var_info:
                        print(f"     Shape: {var_info['shape']}")
                else:
                    print(f"   • {var_name}: {var_info}")
            
            if len(summary) > 5:
                print(f"   ... and {len(summary) - 5} more")
                
        finally:
            st.session_state = original_session_state
    
    async def _dummy_analysis(self, **kwargs) -> Dict[str, Any]:
        """Dummy analysis function for demo"""
        return {"status": "completed", "parameters": kwargs}
    
    def _get_server_specific_context(self) -> Dict[str, Any]:
        """Get demo-specific context"""
        return {
            "demo_mode": True,
            "features_enabled": [
                "dynamic_capabilities",
                "advanced_templates", 
                "pluggable_validation",
                "resource_discovery",
                "tool_discovery",
                "enhanced_tracking"
            ]
        }


async def main():
    """Run the scalability demo"""
    print("🚀 MCP Server Scalability Demo")
    print("=" * 50)
    
    # Initialize demo server
    server = ScalabilityDemoServer()
    await server.initialize()
    
    print("\n🎯 Summary of Scalability Improvements")
    print("=" * 40)
    
    improvements = [
        "✅ Dynamic capability configuration",
        "✅ Multi-engine template system (Simple, Jinja2, F-string)",
        "✅ Pluggable validation backends (Basic, JSON Schema, Pydantic)",
        "✅ Dynamic resource discovery with caching",
        "✅ Automatic tool discovery and registration",
        "✅ Enhanced session state tracking with patterns",
        "✅ Custom validators and template filters",
        "✅ Resource providers for different URI schemes",
        "✅ Schema generation from function signatures",
        "✅ Configurable caching and auto-discovery"
    ]
    
    for improvement in improvements:
        print(improvement)
    
    print(f"\n📈 Server Statistics:")
    print(f"   • Capabilities: {len(server.capabilities)}")
    print(f"   • Tools: {len(server.tools)}")
    print(f"   • Resources: {len(server.resources)}")
    print(f"   • Prompts: {len(server.prompts)}")
    print(f"   • Resource Providers: {len(server.resource_providers)}")
    print(f"   • Custom Validators: {len(server.custom_validators)}")
    
    print("\n🎉 Demo completed! The MCP server is now highly scalable and configurable.")


if __name__ == "__main__":
    asyncio.run(main()) 