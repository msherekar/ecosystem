"""
MCP Client Response Formatter

Handles response formatting for different output formats and error handling.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime


class ResponseFormatter(ABC):
    """Abstract base class for response formatters"""
    
    @abstractmethod
    def format_success(self, data: Any, **metadata) -> Dict[str, Any]:
        """Format a successful response"""
        pass
    
    @abstractmethod
    def format_error(self, error: str, **metadata) -> Dict[str, Any]:
        """Format an error response"""
        pass


class StandardResponseFormatter(ResponseFormatter):
    """Standard response formatter for MCP client responses"""
    
    def __init__(self, include_metadata: bool = True):
        """
        Initialize standard response formatter.
        
        Args:
            include_metadata: Whether to include metadata in responses
        """
        self.include_metadata = include_metadata
        self.logger = logging.getLogger("mcp.response_formatter")
    
    def format_success(self, data: Any, **metadata) -> Dict[str, Any]:
        """Format a successful response"""
        response = {
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        if self.include_metadata and metadata:
            response["metadata"] = metadata
        
        return response
    
    def format_error(self, error: str, **metadata) -> Dict[str, Any]:
        """Format an error response"""
        response = {
            "success": False,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        
        if self.include_metadata and metadata:
            response["metadata"] = metadata
        
        return response


class DetailedResponseFormatter(ResponseFormatter):
    """
    Detailed response formatter that includes extensive metadata and debugging information.
    """
    
    def __init__(self, include_debug: bool = False):
        """
        Initialize detailed response formatter.
        
        Args:
            include_debug: Whether to include debug information
        """
        self.include_debug = include_debug
        self.logger = logging.getLogger("mcp.detailed_response_formatter")
    
    def format_success(self, data: Any, **metadata) -> Dict[str, Any]:
        """Format a successful response with detailed information"""
        response = {
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "response_type": "success",
            "data_type": type(data).__name__
        }
        
        # Add metadata
        if metadata:
            response["metadata"] = metadata
        
        # Add debug information if enabled
        if self.include_debug:
            response["debug"] = {
                "formatter": "DetailedResponseFormatter",
                "metadata_keys": list(metadata.keys()) if metadata else [],
                "data_size": self._estimate_size(data)
            }
        
        return response
    
    def format_error(self, error: str, **metadata) -> Dict[str, Any]:
        """Format an error response with detailed information"""
        response = {
            "success": False,
            "error": error,
            "error_type": "unknown",
            "timestamp": datetime.now().isoformat(),
            "response_type": "error"
        }
        
        # Try to categorize error
        error_lower = error.lower()
        if "not found" in error_lower:
            response["error_type"] = "not_found"
        elif "validation" in error_lower:
            response["error_type"] = "validation_error"
        elif "connection" in error_lower or "timeout" in error_lower:
            response["error_type"] = "connection_error"
        elif "permission" in error_lower or "unauthorized" in error_lower:
            response["error_type"] = "permission_error"
        
        # Add metadata
        if metadata:
            response["metadata"] = metadata
        
        # Add debug information if enabled
        if self.include_debug:
            response["debug"] = {
                "formatter": "DetailedResponseFormatter",
                "error_length": len(error),
                "metadata_keys": list(metadata.keys()) if metadata else []
            }
        
        return response
    
    def _estimate_size(self, data: Any) -> int:
        """Estimate the size of data"""
        try:
            import sys
            return sys.getsizeof(data)
        except:
            return -1


class MinimalResponseFormatter(ResponseFormatter):
    """
    Minimal response formatter that returns only essential information.
    """
    
    def format_success(self, data: Any, **metadata) -> Dict[str, Any]:
        """Format a minimal successful response"""
        # For minimal responses, return data directly if it's already a dict
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
            return data
        
        return {
            "success": True,
            "result": data
        }
    
    def format_error(self, error: str, **metadata) -> Dict[str, Any]:
        """Format a minimal error response"""
        return {
            "success": False,
            "error": error
        }


class AgentResponseFormatter(ResponseFormatter):
    """
    Response formatter optimized for AI agent consumption.
    
    Formats responses in a way that's easy for AI agents to parse and understand.
    """
    
    def __init__(self, include_suggestions: bool = True):
        """
        Initialize agent response formatter.
        
        Args:
            include_suggestions: Whether to include suggestions for next actions
        """
        self.include_suggestions = include_suggestions
        self.logger = logging.getLogger("mcp.agent_response_formatter")
    
    def format_success(self, data: Any, **metadata) -> Dict[str, Any]:
        """Format a successful response for AI agents"""
        response = {
            "status": "success",
            "result": data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add context for agents
        if metadata:
            response["context"] = metadata
        
        # Add suggestions if enabled
        if self.include_suggestions:
            response["suggestions"] = self._generate_success_suggestions(data, metadata)
        
        return response
    
    def format_error(self, error: str, **metadata) -> Dict[str, Any]:
        """Format an error response for AI agents"""
        response = {
            "status": "error",
            "error_message": error,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add context for agents
        if metadata:
            response["context"] = metadata
        
        # Add suggestions if enabled
        if self.include_suggestions:
            response["suggestions"] = self._generate_error_suggestions(error, metadata)
        
        return response
    
    def _generate_success_suggestions(self, data: Any, metadata: Dict[str, Any]) -> List[str]:
        """Generate suggestions for successful responses"""
        suggestions = []
        
        if isinstance(data, dict):
            if "tools" in str(data).lower():
                suggestions.append("Consider using the available tools for further analysis")
            if "data" in str(data).lower() or "result" in str(data).lower():
                suggestions.append("You can analyze the returned data for insights")
        
        if metadata and "server_name" in metadata:
            suggestions.append(f"This result came from server: {metadata['server_name']}")
        
        if not suggestions:
            suggestions.append("Operation completed successfully")
        
        return suggestions
    
    def _generate_error_suggestions(self, error: str, metadata: Dict[str, Any]) -> List[str]:
        """Generate suggestions for error responses"""
        suggestions = []
        error_lower = error.lower()
        
        if "not found" in error_lower:
            suggestions.append("Check if the requested resource/tool exists")
            suggestions.append("Try listing available resources or tools first")
        elif "validation" in error_lower or "parameter" in error_lower:
            suggestions.append("Review the required parameters for this operation")
            suggestions.append("Check the parameter types and format")
        elif "connection" in error_lower:
            suggestions.append("Check server connection status")
            suggestions.append("Try reconnecting to the server")
        elif "permission" in error_lower:
            suggestions.append("Verify you have the required permissions")
            suggestions.append("Check authentication credentials")
        
        if metadata and "available_tools" in metadata:
            suggestions.append(f"Available alternatives: {', '.join(metadata['available_tools'][:3])}")
        
        if not suggestions:
            suggestions.append("Review the error message and try again")
        
        return suggestions


class JSONResponseFormatter(ResponseFormatter):
    """
    JSON response formatter that ensures responses are JSON-serializable.
    """
    
    def __init__(self, pretty_print: bool = False):
        """
        Initialize JSON response formatter.
        
        Args:
            pretty_print: Whether to format JSON with indentation
        """
        self.pretty_print = pretty_print
        self.logger = logging.getLogger("mcp.json_response_formatter")
    
    def format_success(self, data: Any, **metadata) -> Dict[str, Any]:
        """Format a successful response ensuring JSON compatibility"""
        response = {
            "success": True,
            "data": self._make_json_serializable(data),
            "timestamp": datetime.now().isoformat()
        }
        
        if metadata:
            response["metadata"] = self._make_json_serializable(metadata)
        
        return response
    
    def format_error(self, error: str, **metadata) -> Dict[str, Any]:
        """Format an error response ensuring JSON compatibility"""
        response = {
            "success": False,
            "error": str(error),
            "timestamp": datetime.now().isoformat()
        }
        
        if metadata:
            response["metadata"] = self._make_json_serializable(metadata)
        
        return response
    
    def _make_json_serializable(self, obj: Any) -> Any:
        """Convert object to JSON-serializable format"""
        if obj is None:
            return None
        elif isinstance(obj, (bool, int, float, str)):
            return obj
        elif isinstance(obj, dict):
            return {str(k): self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return self._make_json_serializable(obj.__dict__)
        else:
            return str(obj)
    
    def to_json_string(self, response: Dict[str, Any]) -> str:
        """Convert response to JSON string"""
        import json
        
        if self.pretty_print:
            return json.dumps(response, indent=2, ensure_ascii=False)
        else:
            return json.dumps(response, ensure_ascii=False)


class ResponseFormatterFactory:
    """
    Factory for creating response formatters based on configuration.
    """
    
    @staticmethod
    def create_formatter(formatter_type: str, **kwargs) -> ResponseFormatter:
        """
        Create a response formatter of the specified type.
        
        Args:
            formatter_type: Type of formatter to create
            **kwargs: Additional configuration options
            
        Returns:
            ResponseFormatter instance
        """
        formatter_type = formatter_type.lower()
        
        if formatter_type == "standard":
            return StandardResponseFormatter(**kwargs)
        elif formatter_type == "detailed":
            return DetailedResponseFormatter(**kwargs)
        elif formatter_type == "minimal":
            return MinimalResponseFormatter(**kwargs)
        elif formatter_type == "agent":
            return AgentResponseFormatter(**kwargs)
        elif formatter_type == "json":
            return JSONResponseFormatter(**kwargs)
        else:
            raise ValueError(f"Unknown formatter type: {formatter_type}")
    
    @staticmethod
    def get_available_formatters() -> List[str]:
        """Get list of available formatter types"""
        return ["standard", "detailed", "minimal", "agent", "json"]


# Test code to verify the module works independently
if __name__ == "__main__":
    import asyncio
    from datetime import datetime
    
    async def test_response_formatter():
        """Test response formatter functionality"""
        print("Testing Response Formatter...")
        
        # Test StandardResponseFormatter
        standard_formatter = StandardResponseFormatter()
        
        # Test successful response
        success_response = standard_formatter.format_success(
            {"data": [1, 2, 3], "count": 3},
            server="test_server",
            execution_time=0.123
        )
        
        assert success_response["success"] is True
        assert "data" in success_response["data"]
        assert "timestamp" in success_response
        assert success_response["metadata"]["server"] == "test_server"
        print("✅ StandardResponseFormatter success formatting works")
        
        # Test error response
        error_response = standard_formatter.format_error(
            "Test error message",
            error_code="TEST_001",
            server="test_server"
        )
        
        assert error_response["success"] is False
        assert error_response["error"] == "Test error message"
        assert error_response["metadata"]["error_code"] == "TEST_001"
        print("✅ StandardResponseFormatter error formatting works")
        
        # Test DetailedResponseFormatter
        detailed_formatter = DetailedResponseFormatter(include_debug=True)
        
        detailed_success = detailed_formatter.format_success(
            {"result": "test"},
            server="test_server",
            execution_time=0.456
        )
        
        assert "debug" in detailed_success  # DetailedResponseFormatter uses "debug" not "debug_info"
        assert "metadata" in detailed_success
        assert detailed_success["metadata"]["execution_time"] == 0.456
        print("✅ DetailedResponseFormatter works")
        
        # Test MinimalResponseFormatter
        minimal_formatter = MinimalResponseFormatter()
        
        minimal_success = minimal_formatter.format_success(
            {"result": "test"},
            server="test_server"
        )
        
        # Minimal should have fewer fields
        assert len(minimal_success) <= len(success_response)
        assert minimal_success["success"] is True
        print("✅ MinimalResponseFormatter works")
        
        # Test AgentResponseFormatter
        agent_formatter = AgentResponseFormatter(include_suggestions=True)
        
        agent_success = agent_formatter.format_success(
            {"tools_available": ["tool1", "tool2"]},
            server="test_server"
        )
        
        assert "suggestions" in agent_success
        assert isinstance(agent_success["suggestions"], list)
        print("✅ AgentResponseFormatter works")
        
        # Test JSONResponseFormatter
        json_formatter = JSONResponseFormatter(pretty_print=True)
        
        json_success = json_formatter.format_success(
            {"test": "data"},
            server="test_server"
        )
        
        # Should have properly formatted JSON
        json_string = json_formatter.to_json_string(json_success)
        assert isinstance(json_string, str)
        assert "test" in json_string
        print("✅ JSONResponseFormatter works")
        
        # Test ResponseFormatterFactory
        factory_formatter = ResponseFormatterFactory.create_formatter("standard")
        assert isinstance(factory_formatter, StandardResponseFormatter)
        
        factory_formatter = ResponseFormatterFactory.create_formatter("detailed", include_debug=True)
        assert isinstance(factory_formatter, DetailedResponseFormatter)
        
        available_formatters = ResponseFormatterFactory.get_available_formatters()
        assert "standard" in available_formatters
        assert "detailed" in available_formatters
        print("✅ ResponseFormatterFactory works")
        
        # Test complex data serialization
        complex_data = {
            "timestamp": datetime.now(),
            "nested": {"list": [1, 2, {"inner": "value"}]},
            "custom_object": type('CustomObj', (), {'attr': 'value'})()
        }
        
        json_complex = json_formatter.format_success(complex_data)
        json_string = json_formatter.to_json_string(json_complex)
        
        # Should not crash on complex data
        assert isinstance(json_string, str)
        print("✅ Complex data serialization works")
        
        # Test error handling
        try:
            ResponseFormatterFactory.create_formatter("unknown_formatter")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Unknown formatter type" in str(e)
            print("✅ Error handling works")
        
        # Test all formatter types
        for formatter_type in ResponseFormatterFactory.get_available_formatters():
            formatter = ResponseFormatterFactory.create_formatter(formatter_type)
            test_response = formatter.format_success({"test": "data"})
            # Different formatters use different success indicators
            success_indicators = ["success", "status", "result"]
            has_success_indicator = any(indicator in test_response for indicator in success_indicators)
            assert has_success_indicator, f"No success indicator found in {formatter_type} response"
            print(f"✅ {formatter_type} formatter works")
        
        print("🎉 All response formatter tests passed!")
    
    # Run test
    asyncio.run(test_response_formatter())
    print("Run with: python -m src.mcp.core.client.response_formatter") 