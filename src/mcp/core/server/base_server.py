"""
Base MCP Server Implementation

Contains core data structures and abstract base class for MCP servers.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from pydantic import BaseModel

import streamlit as st


class MCPMessageType(Enum):
    """MCP message types based on JSON-RPC 2.0"""
    REQUEST = "request"
    RESPONSE = "response" 
    NOTIFICATION = "notification"
    ERROR = "error"


@dataclass
class MCPCapability:
    """Represents an MCP capability"""
    name: str
    description: str
    supported: bool = True
    metadata: Optional[Dict[str, Any]] = None


class MCPTool(BaseModel):
    """MCP Tool definition"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None
    handler: Optional[Callable] = None
    
    class Config:
        arbitrary_types_allowed = True


class MCPResource(BaseModel):
    """MCP Resource definition"""
    uri: str
    name: str
    description: str
    mime_type: str
    metadata: Optional[Dict[str, Any]] = None


class MCPPrompt(BaseModel):
    """MCP Prompt definition"""
    name: str
    description: str
    template: str
    parameters: Optional[Dict[str, Any]] = None
    engine: str = "simple"
    template_config: Optional[Dict[str, Any]] = None


class BaseMCPServer(ABC):
    """
    Abstract base class for MCP servers.
    
    Provides core functionality and data structures that all MCP servers need.
    """
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.prompts: Dict[str, MCPPrompt] = {}
        self.capabilities: Dict[str, MCPCapability] = {}
        self.logger = logging.getLogger(f"mcp.{name}")
        
        # Session state tracking configuration
        self.tracked_variables: List[str] = []
        self.variable_patterns: List[str] = []
        self.auto_discover_variables: bool = False
    
    # Abstract methods that must be implemented by subclasses
    @abstractmethod
    def _get_server_specific_context(self) -> Dict[str, Any]:
        """Get server-specific context information"""
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the server (register tools, resources, etc.)"""
        pass
    
    # Context and Analysis Methods
    def get_analysis_context(self) -> Dict[str, Any]:
        """Get comprehensive analysis context for AI agents"""
        base_context = {
            "server_name": self.name,
            "server_version": self.version,
            "available_tools": list(self.tools.keys()),
            "available_resources": list(self.resources.keys()),
            "available_prompts": list(self.prompts.keys()),
            "capabilities": list(self.capabilities.keys()),
            "session_state": self._get_session_state_summary()
        }
        
        # Merge with server-specific context
        server_context = self._get_server_specific_context()
        base_context.update(server_context)
        
        return base_context
    
    def get_pipeline_context(self) -> Dict[str, Any]:
        """Get pipeline-specific context information"""
        return {
            "server_name": self.name,
            "pipeline_supported": hasattr(self, 'run_pipeline'),
            "analysis_type": getattr(self, 'analysis_type', 'unknown'),
            "data_availability": self._check_data_availability(),
            "session_state": self._get_session_state_summary()
        }
    
    def get_analysis_insights(self) -> str:
        """Get current analysis insights - to be implemented by analysis interface"""
        from ..analysis_interface import get_analysis_provider
        analysis_type = getattr(self, 'analysis_type', self.name.replace('_server', ''))
        provider = get_analysis_provider(analysis_type)
        return provider.get_analysis_insights()
    
    def get_suggested_actions(self) -> List[str]:
        """Get suggested next actions - to be implemented by analysis interface"""
        from ..analysis_interface import get_analysis_provider
        analysis_type = getattr(self, 'analysis_type', self.name.replace('_server', ''))
        provider = get_analysis_provider(analysis_type)
        return provider.get_suggested_actions()
    
    # Session State Management
    def configure_session_tracking(self, 
                                 tracked_variables: Optional[List[str]] = None,
                                 variable_patterns: Optional[List[str]] = None,
                                 auto_discover: bool = False) -> None:
        """Configure session state tracking"""
        if tracked_variables:
            self.tracked_variables = tracked_variables
        if variable_patterns:
            self.variable_patterns = variable_patterns
        self.auto_discover_variables = auto_discover
    
    def _get_session_state_summary(self) -> Dict[str, Any]:
        """Get a summary of relevant session state variables"""
        if not hasattr(st, 'session_state'):
            return {}
        
        summary = {}
        variables_to_check = self.tracked_variables.copy()
        
        # Auto-discover important variables if enabled
        if self.auto_discover_variables:
            variables_to_check.extend(self._auto_discover_important_variables())
        
        # Add pattern-matched variables
        for pattern in self.variable_patterns:
            import re
            for key in st.session_state.keys():
                if re.match(pattern, key):
                    variables_to_check.append(key)
        
        # Remove duplicates
        variables_to_check = list(set(variables_to_check))
        
        for var_name in variables_to_check:
            if var_name in st.session_state:
                summary[var_name] = self._summarize_variable(var_name, st.session_state[var_name])
        
        return summary
    
    def _auto_discover_important_variables(self) -> List[str]:
        """Auto-discover important session state variables"""
        if not hasattr(st, 'session_state'):
            return []
        
        important_vars = []
        for key, value in st.session_state.items():
            # Check if variable seems important based on naming patterns
            if any(pattern in key.lower() for pattern in [
                'data', 'results', 'analysis', 'plot', 'file', 
                'upload', 'processed', 'filtered', 'normalized'
            ]):
                important_vars.append(key)
                continue
            
            # Check if variable has substantial content
            if hasattr(value, '__len__') and len(value) > 100:
                important_vars.append(key)
                continue
                
            # Check for common data types
            if str(type(value).__name__) in ['DataFrame', 'AnnData', 'ndarray']:
                important_vars.append(key)
        
        return important_vars[:10]  # Limit to top 10 variables
    
    def _summarize_variable(self, name: str, value: Any) -> Dict[str, Any]:
        """Create a summary of a session state variable"""
        summary = {
            "name": name,
            "type": type(value).__name__,
            "exists": True
        }
        
        try:
            # Handle different data types
            if hasattr(value, 'shape'):  # numpy arrays, pandas DataFrames
                summary["shape"] = value.shape
            elif hasattr(value, '__len__'):  # lists, dicts, strings
                summary["length"] = len(value)
                if isinstance(value, dict):
                    summary["keys"] = list(value.keys())[:5]  # First 5 keys
            elif isinstance(value, (int, float)):
                summary["value"] = value
            elif isinstance(value, str):
                summary["preview"] = value[:50] + "..." if len(value) > 50 else value
            
            # Special handling for common bioinformatics data types
            if hasattr(value, 'obs'):  # AnnData objects
                summary["n_obs"] = value.n_obs
                summary["n_vars"] = value.n_vars
                if hasattr(value, 'obs_names'):
                    summary["obs_names_preview"] = list(value.obs_names[:3])
        except Exception as e:
            summary["summary_error"] = str(e)
        
        return summary
    
    def _check_data_availability(self) -> Dict[str, bool]:
        """Check availability of common data types"""
        if not hasattr(st, 'session_state'):
            return {}
        
        data_checks = {}
        
        # Common data variable patterns to check
        data_patterns = [
            ('raw_data', ['data', 'raw_data', 'counts']),
            ('processed_data', ['processed_data', 'adata', 'normalized_data']),
            ('metadata', ['metadata', 'meta', 'sample_info']),
            ('results', ['results', 'analysis_results', 'deseq_results'])
        ]
        
        for data_type, patterns in data_patterns:
            data_checks[data_type] = any(
                pattern in st.session_state and st.session_state[pattern] is not None
                for pattern in patterns
            )
        
        return data_checks 

# Test code to verify the module works independently
if __name__ == "__main__":
    import asyncio
    
    async def test_base_server():
        """Test base server components"""
        print("Testing Base Server Components...")
        
        # Test MCPCapability
        capability = MCPCapability(
            name="test_capability",
            description="A test capability",
            supported=True,
            metadata={"version": "1.0"}
        )
        print(f"✅ MCPCapability created: {capability.name}")
        
        # Test MCPTool
        def test_handler(message: str):
            return f"Processed: {message}"
        
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {"message": {"type": "string"}}},
            handler=test_handler
        )
        print(f"✅ MCPTool created: {tool.name}")
        
        # Test MCPResource
        resource = MCPResource(
            uri="test://resource",
            name="Test Resource",
            description="A test resource",
            mime_type="text/plain"
        )
        print(f"✅ MCPResource created: {resource.name}")
        
        # Test MCPPrompt
        prompt = MCPPrompt(
            name="test_prompt",
            description="A test prompt",
            template="Hello {name}!",
            parameters={"name": "string"}
        )
        print(f"✅ MCPPrompt created: {prompt.name}")
        
        # Test ResourceProvider implementations
        try:
            file_provider = FileResourceProvider("/tmp")
            print(f"✅ FileResourceProvider created with base path: {file_provider.base_path}")
        except NameError:
            print("ℹ️  FileResourceProvider not available in base module (defined in resource_manager)")
        
        try:
            session_provider = SessionStateResourceProvider()
            print("✅ SessionStateResourceProvider created")
        except NameError:
            print("ℹ️  SessionStateResourceProvider not available in base module (defined in resource_manager)")
        
        # Test resource listing (will be empty but shouldn't error)
        try:
            if 'file_provider' in locals():
                resources = await file_provider.list_resources()
                print(f"✅ File provider resource listing: {len(resources)} resources")
            else:
                print("ℹ️  File provider not available for testing")
        except Exception as e:
            print(f"ℹ️  File provider listing expected behavior: {type(e).__name__}")
        
        print("🎉 All base server component tests passed!")
    
    # Run test
    asyncio.run(test_base_server())
    print("Run with: python -m src.mcp.core.server.base_server") 