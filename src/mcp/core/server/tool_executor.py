"""
MCP Server Tool Executor

Handles tool execution with validation and error handling.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Callable

from .base_server import MCPTool
from .validation_system import ValidationSystem, ValidationError


class ToolExecutionError(Exception):
    """Tool execution error"""
    def __init__(self, message: str, tool_name: str = None, parameters: Dict[str, Any] = None):
        self.message = message
        self.tool_name = tool_name
        self.parameters = parameters
        super().__init__(message)


class ToolExecutor:
    """
    Handles tool execution for MCP servers.
    
    Provides validation, error handling, and execution monitoring.
    """
    
    def __init__(self, validation_system: ValidationSystem):
        self.validation_system = validation_system
        self.execution_stats: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger("mcp.tool_executor")
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any], 
                          tools: Dict[str, MCPTool]) -> Dict[str, Any]:
        """
        Execute a tool with validation and error handling.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters to pass to the tool
            tools: Dictionary of available tools
            
        Returns:
            Dict with execution result and metadata
        """
        start_time = time.time()
        
        # Validate tool exists
        if tool_name not in tools:
            return self._create_error_response(
                f"Tool '{tool_name}' not found",
                tool_name,
                parameters,
                available_tools=list(tools.keys())
            )
        
        tool = tools[tool_name]
        
        try:
            # Validate parameters
            self.validation_system.validate_parameters(parameters, tool.input_schema)
            
            # Execute the tool
            result = await self._execute_handler(tool.handler, parameters)
            
            # Track execution stats
            execution_time = time.time() - start_time
            self._update_execution_stats(tool_name, True, execution_time)
            
            # Format successful response
            return self._create_success_response(
                result,
                tool_name,
                parameters,
                execution_time
            )
            
        except ValidationError as e:
            execution_time = time.time() - start_time
            self._update_execution_stats(tool_name, False, execution_time, "validation_error")
            
            return self._create_error_response(
                f"Parameter validation failed: {e.message}",
                tool_name,
                parameters,
                error_type="validation_error",
                field=e.field,
                value=e.value
            )
            
        except ToolExecutionError as e:
            execution_time = time.time() - start_time
            self._update_execution_stats(tool_name, False, execution_time, "execution_error")
            
            return self._create_error_response(
                e.message,
                tool_name,
                parameters,
                error_type="execution_error"
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_execution_stats(tool_name, False, execution_time, "unknown_error")
            
            self.logger.error(f"Unexpected error executing tool '{tool_name}': {str(e)}")
            
            return self._create_error_response(
                f"Tool execution failed: {str(e)}",
                tool_name,
                parameters,
                error_type="unknown_error"
            )
    
    async def _execute_handler(self, handler: Callable, parameters: Dict[str, Any]) -> Any:
        """Execute the tool handler function"""
        if handler is None:
            raise ToolExecutionError("Tool handler is not defined")
        
        try:
            # Check if handler is async
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**parameters)
            else:
                # Run sync handler in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: handler(**parameters))
            
            return result
            
        except TypeError as e:
            if "unexpected keyword argument" in str(e):
                raise ToolExecutionError(f"Invalid parameters for tool: {str(e)}")
            else:
                raise ToolExecutionError(f"Tool handler error: {str(e)}")
                
        except Exception as e:
            raise ToolExecutionError(f"Tool execution failed: {str(e)}")
    
    def _create_success_response(self, result: Any, tool_name: str, 
                               parameters: Dict[str, Any], execution_time: float) -> Dict[str, Any]:
        """Create a successful tool execution response"""
        response = {
            "success": True,
            "tool_name": tool_name,
            "execution_time": execution_time,
            "parameters_used": list(parameters.keys())
        }
        
        # Handle different result types
        if isinstance(result, dict):
            response.update(result)
        else:
            response["result"] = result
        
        return response
    
    def _create_error_response(self, error_message: str, tool_name: str = None, 
                             parameters: Dict[str, Any] = None, 
                             error_type: str = "unknown",
                             **kwargs) -> Dict[str, Any]:
        """Create an error response"""
        response = {
            "success": False,
            "error": error_message,
            "error_type": error_type
        }
        
        if tool_name:
            response["tool_name"] = tool_name
        
        if parameters:
            response["parameters_used"] = list(parameters.keys())
        
        # Add any additional error information
        response.update(kwargs)
        
        return response
    
    def _update_execution_stats(self, tool_name: str, success: bool, 
                              execution_time: float, error_type: str = None) -> None:
        """Update execution statistics for a tool"""
        if tool_name not in self.execution_stats:
            self.execution_stats[tool_name] = {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "total_execution_time": 0.0,
                "average_execution_time": 0.0,
                "last_execution": None,
                "error_types": {}
            }
        
        stats = self.execution_stats[tool_name]
        stats["total_executions"] += 1
        stats["total_execution_time"] += execution_time
        stats["average_execution_time"] = stats["total_execution_time"] / stats["total_executions"]
        stats["last_execution"] = time.time()
        
        if success:
            stats["successful_executions"] += 1
        else:
            stats["failed_executions"] += 1
            if error_type:
                if error_type not in stats["error_types"]:
                    stats["error_types"][error_type] = 0
                stats["error_types"][error_type] += 1
    
    def get_execution_stats(self, tool_name: str = None) -> Dict[str, Any]:
        """Get execution statistics for tools"""
        if tool_name:
            return self.execution_stats.get(tool_name, {})
        else:
            return self.execution_stats.copy()
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get a summary of all tool executions"""
        total_executions = sum(stats["total_executions"] for stats in self.execution_stats.values())
        total_successes = sum(stats["successful_executions"] for stats in self.execution_stats.values())
        total_failures = sum(stats["failed_executions"] for stats in self.execution_stats.values())
        
        # Calculate success rate
        success_rate = (total_successes / total_executions * 100) if total_executions > 0 else 0
        
        # Find most used tools
        most_used_tools = sorted(
            self.execution_stats.items(),
            key=lambda x: x[1]["total_executions"],
            reverse=True
        )[:5]
        
        # Find tools with highest error rates
        error_prone_tools = []
        for tool_name, stats in self.execution_stats.items():
            if stats["total_executions"] > 0:
                error_rate = stats["failed_executions"] / stats["total_executions"] * 100
                if error_rate > 10:  # More than 10% error rate
                    error_prone_tools.append((tool_name, error_rate))
        
        error_prone_tools.sort(key=lambda x: x[1], reverse=True)
        
        return {
            "total_executions": total_executions,
            "successful_executions": total_successes,
            "failed_executions": total_failures,
            "success_rate": round(success_rate, 2),
            "unique_tools_executed": len(self.execution_stats),
            "most_used_tools": [{"tool": name, "executions": stats["total_executions"]} 
                               for name, stats in most_used_tools],
            "error_prone_tools": [{"tool": name, "error_rate": round(rate, 2)} 
                                 for name, rate in error_prone_tools[:5]]
        }
    
    def reset_stats(self, tool_name: str = None) -> None:
        """Reset execution statistics"""
        if tool_name:
            if tool_name in self.execution_stats:
                del self.execution_stats[tool_name]
                self.logger.info(f"Reset stats for tool: {tool_name}")
        else:
            self.execution_stats.clear()
            self.logger.info("Reset all execution statistics")
    
    def validate_tool_definition(self, tool: MCPTool) -> Dict[str, Any]:
        """Validate a tool definition"""
        issues = []
        warnings = []
        
        # Check required fields
        if not tool.name:
            issues.append("Tool name is required")
        
        if not tool.description:
            warnings.append("Tool description is empty")
        
        if not tool.input_schema:
            issues.append("Tool input schema is required")
        elif not isinstance(tool.input_schema, dict):
            issues.append("Tool input schema must be a dictionary")
        
        if not tool.handler:
            issues.append("Tool handler function is required")
        elif not callable(tool.handler):
            issues.append("Tool handler must be callable")
        
        # Validate input schema structure
        if tool.input_schema and isinstance(tool.input_schema, dict):
            if "type" not in tool.input_schema:
                warnings.append("Input schema should specify a type")
            
            if "properties" in tool.input_schema:
                properties = tool.input_schema["properties"]
                if not isinstance(properties, dict):
                    issues.append("Schema properties must be a dictionary")
                else:
                    for prop_name, prop_schema in properties.items():
                        if not isinstance(prop_schema, dict):
                            issues.append(f"Property '{prop_name}' schema must be a dictionary")
                        elif "type" not in prop_schema:
                            warnings.append(f"Property '{prop_name}' should specify a type")
        
        # Check handler signature compatibility (basic check)
        if tool.handler and callable(tool.handler):
            import inspect
            try:
                sig = inspect.signature(tool.handler)
                handler_params = list(sig.parameters.keys())
                
                # Remove 'self' if it's a method
                if handler_params and handler_params[0] == 'self':
                    handler_params = handler_params[1:]
                
                # Check if schema properties match handler parameters
                if tool.input_schema and "properties" in tool.input_schema:
                    schema_params = set(tool.input_schema["properties"].keys())
                    handler_param_set = set(handler_params)
                    
                    # Check for mismatched parameters
                    extra_schema_params = schema_params - handler_param_set
                    extra_handler_params = handler_param_set - schema_params
                    
                    if extra_schema_params:
                        warnings.append(f"Schema defines parameters not in handler: {extra_schema_params}")
                    
                    if extra_handler_params:
                        # Filter out parameters with defaults
                        params_without_defaults = [
                            param for param in extra_handler_params
                            if sig.parameters[param].default == inspect.Parameter.empty
                        ]
                        if params_without_defaults:
                            warnings.append(f"Handler has required parameters not in schema: {params_without_defaults}")
                
            except Exception as e:
                warnings.append(f"Could not validate handler signature: {str(e)}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "tool_name": tool.name
        }

# Test code to verify the module works independently
if __name__ == "__main__":
    import asyncio
    
    async def test_tool_executor():
        """Test tool executor components"""
        print("Testing Tool Executor...")
        
        # Test ToolExecutor classes
        executor = ToolExecutor()
        executor.logger = logging.getLogger("test")
        executor.tool_stats = ToolStatistics()
        
        # Test tool registration
        def sample_handler(message: str, count: int = 1):
            """Sample tool handler"""
            return {"message": message, "repeated": message * count}
        
        executor.register_tool(
            name="sample_tool",
            description="A sample tool for testing",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "count": {"type": "integer", "default": 1}
                },
                "required": ["message"]
            },
            handler=sample_handler
        )
        
        assert "sample_tool" in executor.tools
        print("✅ Tool registered successfully")
        
        # Test tool execution
        result = await executor.execute_tool("sample_tool", {"message": "Hello", "count": 3})
        
        assert result["success"]
        assert result["result"]["message"] == "Hello"
        assert result["result"]["repeated"] == "HelloHelloHello"
        print("✅ Tool execution successful")
        
        # Test tool execution with missing parameter
        result = await executor.execute_tool("sample_tool", {})
        assert not result["success"]
        assert "Required parameter 'message' missing" in result["error"]
        print("✅ Tool execution correctly handles missing parameters")
        
        # Test async tool handler
        async def async_handler(data: str):
            """Async tool handler"""
            await asyncio.sleep(0.01)  # Simulate async work
            return {"processed": data.upper()}
        
        executor.register_tool(
            name="async_tool",
            description="An async tool",
            input_schema={
                "type": "object",
                "properties": {"data": {"type": "string"}},
                "required": ["data"]
            },
            handler=async_handler
        )
        
        result = await executor.execute_tool("async_tool", {"data": "test"})
        assert result["success"]
        assert result["result"]["processed"] == "TEST"
        print("✅ Async tool execution successful")
        
        # Test tool decorator
        @executor.mcp_tool(
            name="decorated_tool",
            description="A decorated tool",
            input_schema={
                "type": "object",
                "properties": {"value": {"type": "integer"}},
                "required": ["value"]
            }
        )
        def decorated_handler(value: int):
            return {"doubled": value * 2}
        
        assert "decorated_tool" in executor.tools
        result = await executor.execute_tool("decorated_tool", {"value": 21})
        assert result["success"]
        assert result["result"]["doubled"] == 42
        print("✅ Tool decorator works correctly")
        
        # Test schema generation from function
        def auto_schema_handler(name: str, age: int, active: bool = True):
            return {"name": name, "age": age, "active": active}
        
        schema = executor._generate_schema_from_function(auto_schema_handler)
        
        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert "age" in schema["properties"]
        assert "active" in schema["properties"]
        assert "name" in schema["required"]
        assert "age" in schema["required"]
        assert "active" not in schema["required"]  # Has default value
        print("✅ Schema generation from function works")
        
        # Test tool statistics
        stats = executor.tool_stats.get_stats()
        assert stats["total_executions"] > 0
        assert stats["successful_executions"] > 0
        print(f"✅ Tool statistics: {stats}")
        
        # Test tool discovery configuration
        executor.configure_tool_discovery(
            auto_discover=True,
            tool_modules=["test_module"]
        )
        assert executor.auto_discover_tools
        assert "test_module" in executor.tool_modules
        print("✅ Tool discovery configuration updated")
        
        # Test tool listing
        tools = list(executor.tools.keys())
        assert len(tools) >= 3  # sample_tool, async_tool, decorated_tool
        print(f"✅ Tool listing: {tools}")
        
        print("🎉 All tool executor tests passed!")
    
    # Run test
    asyncio.run(test_tool_executor())
    print("Run with: python -m src.mcp.core.server.tool_executor") 