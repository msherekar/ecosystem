"""
MCP Client - Main Client Class Implementation

This module contains the primary MCPClient class that orchestrates all MCP operations.
Designed for scalability, security, and Electron UI/UX compatibility.
"""

import asyncio
import logging
import json
import hashlib
import time
from typing import Any, Dict, List, Optional, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor
import uuid

from .connection_manager import ConnectionManager, ServerConnection, ConnectionStatus, SecurityPolicy
from .cache_manager import CacheManager
from .execution_engine import ExecutionEngine
from .response_formatter import ResponseFormatter, StandardResponseFormatter


class MCPClientState(Enum):
    """Client state enumeration for better state management"""
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"
    OFFLINE = "offline"


@dataclass
class ClientConfiguration:
    """Configuration class for MCP Client with validation"""
    name: str
    cache_max_size: int = 1000
    cache_default_ttl: int = 300
    max_concurrent_operations: int = 10
    operation_timeout: int = 30
    enable_security_features: bool = True
    enable_audit_logging: bool = True
    electron_mode: bool = False
    ui_update_interval: float = 0.1
    max_log_entries: int = 1000
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.cache_max_size < 1:
            raise ValueError("cache_max_size must be at least 1")
        if self.cache_default_ttl < 1:
            raise ValueError("cache_default_ttl must be at least 1 second")
        if self.max_concurrent_operations < 1:
            raise ValueError("max_concurrent_operations must be at least 1")
        if self.operation_timeout < 1:
            raise ValueError("operation_timeout must be at least 1 second")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string")


@dataclass
class OperationResult:
    """Standardized operation result for UI consumption"""
    operation_id: str
    operation_type: str
    success: bool
    data: Any = None
    error_message: str = None
    timestamp: datetime = None
    duration_ms: float = 0
    server_name: str = None
    cached: bool = False
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type,
            "success": self.success,
            "data": self.data,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "server_name": self.server_name,
            "cached": self.cached,
            "metadata": self.metadata
        }


class SecurityManager:
    """Security manager for MCP Client operations"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.operation_history: List[Dict[str, Any]] = []
        self.blocked_operations: set = set()
        self.rate_limits: Dict[str, List[float]] = {}
        self.max_operations_per_minute = 100
        
    def validate_operation(self, operation_type: str, parameters: Dict[str, Any]) -> bool:
        """Validate if operation is allowed"""
        if not self.enabled:
            return True
        
        # Check if operation is blocked
        operation_hash = self._hash_operation(operation_type, parameters)
        if operation_hash in self.blocked_operations:
            return False
        
        # Check rate limiting
        current_time = time.time()
        if operation_type not in self.rate_limits:
            self.rate_limits[operation_type] = []
        
        # Clean old entries (older than 1 minute)
        self.rate_limits[operation_type] = [
            timestamp for timestamp in self.rate_limits[operation_type]
            if current_time - timestamp < 60
        ]
        
        # Check if under rate limit
        if len(self.rate_limits[operation_type]) >= self.max_operations_per_minute:
            return False
        
        # Record operation
        self.rate_limits[operation_type].append(current_time)
        return True
    
    def _hash_operation(self, operation_type: str, parameters: Dict[str, Any]) -> str:
        """Create hash of operation for tracking"""
        operation_str = f"{operation_type}:{json.dumps(parameters, sort_keys=True)}"
        return hashlib.sha256(operation_str.encode()).hexdigest()
    
    def block_operation(self, operation_type: str, parameters: Dict[str, Any]):
        """Block a specific operation"""
        operation_hash = self._hash_operation(operation_type, parameters)
        self.blocked_operations.add(operation_hash)
    
    def unblock_operation(self, operation_type: str, parameters: Dict[str, Any]):
        """Unblock a specific operation"""
        operation_hash = self._hash_operation(operation_type, parameters)
        self.blocked_operations.discard(operation_hash)


class UIEventEmitter:
    """Event emitter for Electron UI integration"""
    
    def __init__(self, electron_mode: bool = False):
        self.electron_mode = electron_mode
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.event_queue: List[Dict[str, Any]] = []
        self.max_queue_size = 1000
        
    def on(self, event_name: str, handler: Callable):
        """Register event handler"""
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(handler)
    
    def emit(self, event_name: str, data: Any = None):
        """Emit event to handlers and queue for UI"""
        event = {
            "event": event_name,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "id": str(uuid.uuid4())
        }
        
        # Add to queue for UI polling
        self.event_queue.append(event)
        if len(self.event_queue) > self.max_queue_size:
            self.event_queue.pop(0)
        
        # Call registered handlers
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(data))
                    else:
                        handler(data)
                except Exception as e:
                    logging.error(f"Error in event handler for {event_name}: {e}")
    
    def get_events(self, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get events for UI consumption"""
        if since is None:
            return self.event_queue.copy()
        
        # Filter events after timestamp
        try:
            since_dt = datetime.fromisoformat(since)
            return [
                event for event in self.event_queue
                if datetime.fromisoformat(event["timestamp"]) > since_dt
            ]
        except (ValueError, KeyError):
            return self.event_queue.copy()
    
    def clear_events(self):
        """Clear event queue"""
        self.event_queue.clear()


class MCPClient:
    """
    Main MCP Client for connecting to and interacting with MCP servers.
    
    Features:
    - Scalable architecture with async operations
    - Security features and operation validation
    - Electron UI/UX integration
    - Comprehensive monitoring and logging
    - Thread-safe operations
    - Rate limiting and resource management
    """
    
    def __init__(self, 
                 config: Union[ClientConfiguration, Dict[str, Any], str],
                 response_formatter: Optional[ResponseFormatter] = None):
        """
        Initialize MCP Client with configuration.
        
        Args:
            config: Client configuration (ClientConfiguration, dict, or name string)
            response_formatter: Custom response formatter
        """
        # Parse configuration
        if isinstance(config, str):
            self.config = ClientConfiguration(name=config)
        elif isinstance(config, dict):
            self.config = ClientConfiguration(**config)
        elif isinstance(config, ClientConfiguration):
            self.config = config
        else:
            raise ValueError("config must be ClientConfiguration, dict, or string")
        
        # Initialize state
        self._state = MCPClientState.INITIALIZING
        self._state_lock = threading.Lock()
        self._operation_semaphore = asyncio.Semaphore(self.config.max_concurrent_operations)
        self._active_operations: Dict[str, asyncio.Task] = {}
        
        # Initialize logger
        self.logger = logging.getLogger(f"mcp.client.{self.config.name}")
        self.logger.setLevel(logging.INFO)
        
        # Initialize components
        self.cache_manager = CacheManager({
            "max_memory_size": self.config.cache_max_size,
            "default_ttl": self.config.cache_default_ttl
        })
        
        # Create development-friendly security policy for local use
        dev_security_policy = SecurityPolicy(
            require_authentication=False,  # Disable authentication requirement for local development
            require_encryption=False,      # Allow unencrypted connections locally
            allowed_protocols={"http", "https", "ws", "wss", "file", "memory"},  # Allow more protocols
            max_connection_attempts=5,
            connection_timeout=60,
            idle_timeout=600,  # Longer idle timeout
            rate_limit_requests_per_minute=1000,  # Higher rate limit for development
            enable_certificate_validation=False  # Skip cert validation for local dev
        )
        
        self.connection_manager = ConnectionManager(self.logger, security_policy=dev_security_policy)
        
        self.response_formatter = response_formatter or StandardResponseFormatter()
        
        self.execution_engine = ExecutionEngine(
            self.connection_manager,
            self.cache_manager,
            self.response_formatter,
            self.logger
        )
        
        # Initialize security and UI components
        self.security_manager = SecurityManager(self.config.enable_security_features)
        self.ui_event_emitter = UIEventEmitter(self.config.electron_mode)
        
        # Audit logging
        self.audit_log: List[Dict[str, Any]] = []
        
        # Thread pool for CPU-intensive operations
        self._thread_pool = ThreadPoolExecutor(max_workers=4)
        
        # Performance metrics
        self.metrics = {
            "operations_completed": 0,
            "operations_failed": 0,
            "total_execution_time": 0.0,
            "cache_hit_rate": 0.0,
            "active_connections": 0
        }
        
        # Set state to ready
        self._set_state(MCPClientState.READY)
        
        self.logger.info(f"Initialized MCP Client: {self.config.name}")
        self.ui_event_emitter.emit("client_initialized", {"client_name": self.config.name})
    
    def _set_state(self, new_state: MCPClientState):
        """Thread-safe state setting"""
        with self._state_lock:
            old_state = self._state
            self._state = new_state
            self.logger.info(f"Client state changed: {old_state.value} -> {new_state.value}")
            self.ui_event_emitter.emit("state_changed", {
                "old_state": old_state.value,
                "new_state": new_state.value
            })
    
    @property
    def state(self) -> MCPClientState:
        """Get current client state"""
        with self._state_lock:
            return self._state
    
    def _generate_operation_id(self) -> str:
        """Generate unique operation ID"""
        return f"{self.config.name}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
    
    def _log_audit_event(self, event_type: str, details: Dict[str, Any]):
        """Log audit event"""
        if not self.config.enable_audit_logging:
            return
        
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "client_name": self.config.name,
            "details": details
        }
        
        self.audit_log.append(audit_entry)
        
        # Keep only recent entries
        if len(self.audit_log) > self.config.max_log_entries:
            self.audit_log = self.audit_log[-self.config.max_log_entries:]
        
        self.ui_event_emitter.emit("audit_event", audit_entry)
    
    async def _execute_with_timeout(self, coro, timeout: Optional[int] = None) -> Any:
        """Execute coroutine with timeout"""
        timeout = timeout or self.config.operation_timeout
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Operation timed out after {timeout} seconds")
    
    async def connect_server(self, server, name: str, **kwargs) -> OperationResult:
        """Connect to an MCP server with full monitoring"""
        operation_id = self._generate_operation_id()
        start_time = time.time()
        
        self._log_audit_event("server_connect_attempt", {"server_name": name})
        self.ui_event_emitter.emit("operation_started", {
            "operation_id": operation_id,
            "operation_type": "connect_server",
            "server_name": name
        })
        
        try:
            # Validate operation
            if not self.security_manager.validate_operation("connect_server", {"name": name}):
                raise SecurityError("Operation blocked by security manager")
            
            async with self._operation_semaphore:
                success = await self._execute_with_timeout(
                    self.connection_manager.connect_server(server, name, **kwargs)
                )
                
                if success:
                    # Update execution engine indexes
                    self.execution_engine.update_indexes(name, server)
                    self.metrics["active_connections"] += 1
                    
                    result = OperationResult(
                        operation_id=operation_id,
                        operation_type="connect_server",
                        success=True,
                        data={"server_name": name, "connected": True},
                        duration_ms=(time.time() - start_time) * 1000,
                        server_name=name
                    )
                    
                    self._log_audit_event("server_connected", {"server_name": name})
                    self.ui_event_emitter.emit("server_connected", {"server_name": name})
                else:
                    result = OperationResult(
                        operation_id=operation_id,
                        operation_type="connect_server",
                        success=False,
                        error_message=f"Failed to connect to server: {name}",
                        duration_ms=(time.time() - start_time) * 1000,
                        server_name=name
                    )
                    
                    self._log_audit_event("server_connect_failed", {"server_name": name})
                    self.ui_event_emitter.emit("server_connect_failed", {"server_name": name})
                
                self.metrics["operations_completed"] += 1
                return result
                
        except Exception as e:
            self.metrics["operations_failed"] += 1
            result = OperationResult(
                operation_id=operation_id,
                operation_type="connect_server",
                success=False,
                error_message=str(e),
                duration_ms=(time.time() - start_time) * 1000,
                server_name=name
            )
            
            self._log_audit_event("server_connect_error", {"server_name": name, "error": str(e)})
            self.ui_event_emitter.emit("operation_error", result.to_dict())
            return result
    
    async def disconnect_server(self, name: str) -> OperationResult:
        """Disconnect from an MCP server with full monitoring"""
        operation_id = self._generate_operation_id()
        start_time = time.time()
        
        self._log_audit_event("server_disconnect_attempt", {"server_name": name})
        
        try:
            async with self._operation_semaphore:
                success = await self._execute_with_timeout(
                    self.connection_manager.disconnect_server(name)
                )
                
                if success:
                    self.execution_engine.remove_from_indexes(name)
                    self.metrics["active_connections"] = max(0, self.metrics["active_connections"] - 1)
                    
                    result = OperationResult(
                        operation_id=operation_id,
                        operation_type="disconnect_server",
                        success=True,
                        data={"server_name": name, "disconnected": True},
                        duration_ms=(time.time() - start_time) * 1000,
                        server_name=name
                    )
                    
                    self._log_audit_event("server_disconnected", {"server_name": name})
                    self.ui_event_emitter.emit("server_disconnected", {"server_name": name})
                else:
                    result = OperationResult(
                        operation_id=operation_id,
                        operation_type="disconnect_server",
                        success=False,
                        error_message=f"Failed to disconnect from server: {name}",
                        duration_ms=(time.time() - start_time) * 1000,
                        server_name=name
                    )
                
                self.metrics["operations_completed"] += 1
                return result
                
        except Exception as e:
            self.metrics["operations_failed"] += 1
            result = OperationResult(
                operation_id=operation_id,
                operation_type="disconnect_server",
                success=False,
                error_message=str(e),
                duration_ms=(time.time() - start_time) * 1000,
                server_name=name
            )
            
            self._log_audit_event("server_disconnect_error", {"server_name": name, "error": str(e)})
            return result
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any], 
                          timeout: Optional[int] = None) -> OperationResult:
        """Execute a tool on connected servers with full monitoring"""
        operation_id = self._generate_operation_id()
        start_time = time.time()
        
        self._log_audit_event("tool_execute_attempt", {
            "tool_name": tool_name,
            "parameters": parameters
        })
        
        try:
            # Validate operation
            if not self.security_manager.validate_operation("execute_tool", {
                "tool_name": tool_name,
                "parameters": parameters
            }):
                raise SecurityError("Tool execution blocked by security manager")
            
            async with self._operation_semaphore:
                execution_result = await self._execute_with_timeout(
                    self.execution_engine.execute_tool(tool_name, parameters),
                    timeout
                )
                
                success = execution_result.get("success", False)
                cached = execution_result.get("cached", False)
                
                result = OperationResult(
                    operation_id=operation_id,
                    operation_type="execute_tool",
                    success=success,
                    data=execution_result.get("data") if success else None,
                    error_message=execution_result.get("error") if not success else None,
                    duration_ms=(time.time() - start_time) * 1000,
                    server_name=execution_result.get("metadata", {}).get("server_name"),
                    cached=cached,
                    metadata={
                        "tool_name": tool_name,
                        "parameters_hash": hashlib.md5(
                            json.dumps(parameters, sort_keys=True).encode()
                        ).hexdigest()
                    }
                )
                
                if success:
                    self._log_audit_event("tool_executed", {
                        "tool_name": tool_name,
                        "server_name": result.server_name,
                        "cached": cached
                    })
                    self.ui_event_emitter.emit("tool_executed", {
                        "tool_name": tool_name,
                        "success": True,
                        "cached": cached
                    })
                else:
                    self._log_audit_event("tool_execution_failed", {
                        "tool_name": tool_name,
                        "error": result.error_message
                    })
                    self.ui_event_emitter.emit("tool_execution_failed", {
                        "tool_name": tool_name,
                        "error": result.error_message
                    })
                
                self.metrics["operations_completed"] += 1
                return result
                
        except Exception as e:
            self.metrics["operations_failed"] += 1
            result = OperationResult(
                operation_id=operation_id,
                operation_type="execute_tool",
                success=False,
                error_message=str(e),
                duration_ms=(time.time() - start_time) * 1000,
                metadata={"tool_name": tool_name}
            )
            
            self._log_audit_event("tool_execution_error", {
                "tool_name": tool_name,
                "error": str(e)
            })
            return result
    
    async def get_resource(self, uri: str, timeout: Optional[int] = None) -> OperationResult:
        """Get a resource from connected servers with full monitoring"""
        operation_id = self._generate_operation_id()
        start_time = time.time()
        
        self._log_audit_event("resource_access_attempt", {"uri": uri})
        
        try:
            # Validate operation
            if not self.security_manager.validate_operation("get_resource", {"uri": uri}):
                raise SecurityError("Resource access blocked by security manager")
            
            async with self._operation_semaphore:
                resource_result = await self._execute_with_timeout(
                    self.execution_engine.get_resource(uri),
                    timeout
                )
                
                success = resource_result.get("success", False)
                cached = resource_result.get("cached", False)
                
                result = OperationResult(
                    operation_id=operation_id,
                    operation_type="get_resource",
                    success=success,
                    data=resource_result.get("data") if success else None,
                    error_message=resource_result.get("error") if not success else None,
                    duration_ms=(time.time() - start_time) * 1000,
                    server_name=resource_result.get("metadata", {}).get("server_name"),
                    cached=cached,
                    metadata={"uri": uri}
                )
                
                if success:
                    self._log_audit_event("resource_accessed", {
                        "uri": uri,
                        "server_name": result.server_name,
                        "cached": cached
                    })
                    self.ui_event_emitter.emit("resource_accessed", {
                        "uri": uri,
                        "success": True,
                        "cached": cached
                    })
                else:
                    self._log_audit_event("resource_access_failed", {
                        "uri": uri,
                        "error": result.error_message
                    })
                
                self.metrics["operations_completed"] += 1
                return result
                
        except Exception as e:
            self.metrics["operations_failed"] += 1
            result = OperationResult(
                operation_id=operation_id,
                operation_type="get_resource",
                success=False,
                error_message=str(e),
                duration_ms=(time.time() - start_time) * 1000,
                metadata={"uri": uri}
            )
            
            self._log_audit_event("resource_access_error", {"uri": uri, "error": str(e)})
            return result
    
    # Additional methods for UI/UX integration
    def get_client_status(self) -> Dict[str, Any]:
        """Get comprehensive client status for UI"""
        cache_stats = self.cache_manager.get_stats()
        connection_stats = self.connection_manager.get_connection_stats()
        
        return {
            "client_name": self.config.name,
            "state": self._state.value,
            "uptime_seconds": time.time() - getattr(self, '_start_time', time.time()),
            "configuration": {
                "cache_max_size": self.config.cache_max_size,
                "cache_default_ttl": self.config.cache_default_ttl,
                "max_concurrent_operations": self.config.max_concurrent_operations,
                "electron_mode": self.config.electron_mode,
                "security_enabled": self.config.enable_security_features
            },
            "metrics": self.metrics,
            "cache_stats": cache_stats,
            "connection_stats": connection_stats,
            "active_operations": len(self._active_operations),
            "audit_log_size": len(self.audit_log)
        }
    
    def get_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get all available tools from connected servers (thread-safe)"""
        all_tools = {}
        
        # Collect tools directly from connected servers
        for server_name in self.connection_manager.get_connected_servers():
            connection = self.connection_manager.get_connection(server_name)
            if connection and hasattr(connection.server, 'get_tools'):
                try:
                    server_tools = connection.server.get_tools()
                    if server_tools:
                        for tool_name, tool_info in server_tools.items():
                            # Create unique tool key with server prefix using underscores (OpenAI/OpenRouter compatible)
                            tool_key = f"{server_name}_{tool_name}"
                            
                            # Convert MCPTool to dict if needed
                            if hasattr(tool_info, '__dict__'):
                                tool_dict = {
                                    "name": tool_info.name,
                                    "description": tool_info.description,
                                    "inputSchema": tool_info.input_schema,
                                    "outputSchema": getattr(tool_info, 'output_schema', None),
                                    "server": server_name
                                }
                            else:
                                tool_dict = {
                                    **tool_info,
                                    "server": server_name
                                }
                            all_tools[tool_key] = tool_dict
                except Exception as e:
                    self.logger.warning(f"Failed to get tools from {server_name}: {e}")
        
        # Also check if we can get tools from the execution engine's discovery
        # Use tool_index to find which servers have which tools
        for tool_name, server_list in self.execution_engine.tool_index.items():
            for server_name in server_list:
                tool_key = f"{server_name}_{tool_name}"
                if tool_key not in all_tools:
                    # Try to get tool definition from server
                    connection = self.connection_manager.get_connection(server_name)
                    if connection and hasattr(connection.server, 'get_tools'):
                        try:
                            server_tools = connection.server.get_tools()
                            if server_tools and tool_name in server_tools:
                                tool_info = server_tools[tool_name]
                                if hasattr(tool_info, '__dict__'):
                                    tool_dict = {
                                        "name": tool_info.name,
                                        "description": tool_info.description,
                                        "inputSchema": tool_info.input_schema,
                                        "outputSchema": getattr(tool_info, 'output_schema', None),
                                        "server": server_name
                                    }
                                else:
                                    tool_dict = {
                                        **tool_info,
                                        "server": server_name
                                    }
                                all_tools[tool_key] = tool_dict
                        except Exception as e:
                            self.logger.debug(f"Failed to get tool {tool_name} from {server_name}: {e}")
        
        return all_tools
    
    def get_available_resources(self) -> Dict[str, Dict[str, Any]]:
        """Get all available resources from connected servers (thread-safe)"""
        # First try the resource index (from auto-discovery)
        indexed_resources = self.execution_engine.resource_index.copy()
        
        # Also collect resources directly from connected servers (for resources registered after discovery)
        all_resources = indexed_resources.copy()
        
        for server_name in self.connection_manager.get_connected_servers():
            connection = self.connection_manager.get_connection(server_name)
            if connection and hasattr(connection.server, 'get_resources'):
                try:
                    server_resources = connection.server.get_resources()
                    if server_resources:
                        for resource_uri, resource_info in server_resources.items():
                            # Add server info to resource
                            resource_key = f"{server_name}:{resource_uri}"
                            # Convert MCPResource to dict if needed
                            if hasattr(resource_info, '__dict__'):
                                resource_dict = {
                                    "uri": resource_info.uri,
                                    "name": resource_info.name,
                                    "description": resource_info.description,
                                    "mime_type": resource_info.mime_type,
                                    "metadata": getattr(resource_info, 'metadata', None),
                                    "server": server_name
                                }
                            else:
                                resource_dict = {
                                    **resource_info,
                                    "server": server_name
                                }
                            all_resources[resource_key] = resource_dict
                except Exception as e:
                    self.logger.warning(f"Failed to get resources from {server_name}: {e}")
        
        return all_resources
    
    def get_available_prompts(self) -> Dict[str, Dict[str, Any]]:
        """Get all available prompts from connected servers (thread-safe)"""
        # For now, return prompts from the execution engine if it has a prompt_index
        if hasattr(self.execution_engine, 'prompt_index'):
            return self.execution_engine.prompt_index.copy()
        
        # Otherwise, collect prompts from connected servers
        all_prompts = {}
        for server_name in self.connection_manager.get_connected_servers():
            connection = self.connection_manager.get_connection(server_name)
            if connection and hasattr(connection.server, 'get_prompts'):
                try:
                    server_prompts = connection.server.get_prompts()
                    if server_prompts:
                        for prompt_name, prompt_info in server_prompts.items():
                            # Add server info to prompt
                            prompt_key = f"{server_name}:{prompt_name}"
                            all_prompts[prompt_key] = {
                                **prompt_info,
                                "server": server_name
                            }
                except Exception as e:
                    self.logger.warning(f"Failed to get prompts from {server_name}: {e}")
        
        return all_prompts
    
    def get_tool_definitions_for_agent(self) -> List[Dict[str, Any]]:
        """Get tool definitions formatted for agent/LLM consumption"""
        try:
            tools = self.get_available_tools()
            tool_definitions = []
            
            for tool_name, tool_info in tools.items():
                # Convert tool info to agent-friendly format compatible with OpenAI API
                # Ensure function name only contains allowed characters (letters, numbers, underscores, hyphens)
                clean_function_name = tool_name.replace(":", "_")  # Replace any remaining colons
                
                definition = {
                    "type": "function",  # Required by OpenAI API
                    "function": {
                        "name": clean_function_name,
                        "description": tool_info.get("description", f"Execute {tool_name} tool"),
                        "parameters": tool_info.get("inputSchema", {
                            "type": "object",
                            "properties": {},
                            "required": []
                        })
                    },
                    # Add metadata for internal use (not sent to OpenAI)
                    "server": tool_info.get("server", "unknown"),
                    "category": tool_info.get("category", "general")
                }
                
                # Ensure parameters have proper schema structure
                parameters = definition["function"]["parameters"]
                if "properties" not in parameters:
                    parameters["properties"] = {}
                if "required" not in parameters:
                    parameters["required"] = []
                if "type" not in parameters:
                    parameters["type"] = "object"
                
                tool_definitions.append(definition)
            
            return tool_definitions
            
        except Exception as e:
            self.logger.error(f"Error getting tool definitions for agent: {e}")
            return []
    
    def get_aggregated_context(self) -> Dict[str, Any]:
        """Get aggregated context from all connected servers"""
        try:
            context = {
                "connected_servers": len(self.connection_manager.get_connected_servers()),
                "healthy_servers": len(self.connection_manager.get_healthy_servers()),
                "available_tools": len(self.get_available_tools()),
                "available_resources": len(self.get_available_resources()),
                "available_prompts": len(self.get_available_prompts()),
                "client_state": self.state.value,
                "cache_stats": {
                    "entries": self.cache_manager.get_stats().get("memory_entries", 0),
                    "hit_rate": self.cache_manager.get_stats().get("hit_rate", 0.0)
                },
                "servers": {}
            }
            
            # Add server-specific context
            for server_name in self.connection_manager.get_connected_servers():
                connection = self.connection_manager.get_connection(server_name)
                if connection:
                    server_context = {
                        "status": connection.get_status_info().get("status", "unknown"),
                        "capabilities": {}
                    }
                    
                    # Try to get server capabilities
                    if hasattr(connection.server, 'get_capabilities'):
                        try:
                            server_context["capabilities"] = connection.server.get_capabilities()
                        except Exception as e:
                            self.logger.debug(f"Could not get capabilities for {server_name}: {e}")
                    
                    context["servers"][server_name] = server_context
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error getting aggregated context: {e}")
            return {
                "error": "Failed to get aggregated context",
                "connected_servers": 0,
                "healthy_servers": 0,
                "available_tools": 0,
                "available_resources": 0,
                "available_prompts": 0,
                "client_state": self.state.value if hasattr(self, 'state') else "unknown"
            }
    
    def get_server_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all server connections (thread-safe)"""
        return self.connection_manager.get_connection_details()
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all connected servers"""
        return await self.connection_manager.health_check()
    
    def clear_cache(self, tags: Optional[set] = None) -> None:
        """Clear the client cache"""
        self.cache_manager.clear(tags)
        self.ui_event_emitter.emit("cache_cleared", {"tags": list(tags) if tags else None})
        self._log_audit_event("cache_cleared", {"tags": list(tags) if tags else None})
    
    def get_audit_log(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get audit log entries"""
        if limit is None:
            return self.audit_log.copy()
        return self.audit_log[-limit:].copy()
    
    def get_ui_events(self, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get UI events for Electron frontend"""
        return self.ui_event_emitter.get_events(since)
    
    def clear_ui_events(self):
        """Clear UI event queue"""
        self.ui_event_emitter.clear_events()
    
    async def shutdown(self):
        """Gracefully shutdown the client"""
        self._set_state(MCPClientState.SHUTTING_DOWN)
        self.logger.info("Shutting down MCP Client...")
        
        try:
            # Cancel active operations
            for operation_id, task in self._active_operations.items():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Stop connection manager
            await self.connection_manager.stop()
            
            # Shutdown thread pool
            self._thread_pool.shutdown(wait=True)
            
            self._set_state(MCPClientState.OFFLINE)
            self.logger.info("MCP Client shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            self._set_state(MCPClientState.ERROR)


class SecurityError(Exception):
    """Custom exception for security-related errors"""
    pass


def main():
    """
    Main function demonstrating MCP Client usage with Electron compatibility.
    """
    print("🚀 MCP Client - Scalable & Electron-Ready")
    print("=" * 50)
    
    async def demo_client():
        """Demonstrate client capabilities"""
        # Create configuration
        config = ClientConfiguration(
            name="demo_client",
            cache_max_size=500,
            cache_default_ttl=600,
            max_concurrent_operations=20,
            electron_mode=True,
            enable_security_features=True,
            enable_audit_logging=True
        )
        
        # Create client
        client = MCPClient(config)
        
        print(f"✅ Client created: {client.config.name}")
        print(f"   State: {client.state.value}")
        print(f"   Electron Mode: {client.config.electron_mode}")
        print(f"   Security: {client.config.enable_security_features}")
        
        # Demonstrate status retrieval
        status = client.get_client_status()
        print(f"\n📊 Client Status:")
        print(f"   Cache Size: {status['cache_stats']['memory_entries']}/{status['configuration']['cache_max_size']}")
        print(f"   Active Operations: {status['active_operations']}")
        print(f"   Metrics: {status['metrics']['operations_completed']} ops completed")
        
        # Demonstrate UI event system
        print(f"\n🎨 UI Events:")
        events = client.get_ui_events()
        print(f"   Events in queue: {len(events)}")
        for event in events[:3]:  # Show first 3 events
            print(f"   - {event['event']}: {event['timestamp']}")
        
        # Demonstrate security features
        print(f"\n🔒 Security Features:")
        security_test = client.security_manager.validate_operation("test_op", {"param": "value"})
        print(f"   Operation validation: {'✅ PASS' if security_test else '❌ BLOCKED'}")
        
        # Demonstrate audit logging
        audit_entries = client.get_audit_log(limit=5)
        print(f"   Audit log entries: {len(audit_entries)}")
        
        # Shutdown demonstration
        await client.shutdown()
        print(f"   Final state: {client.state.value}")
        
        return client
    
    # Run demonstration
    try:
        client = asyncio.run(demo_client())
        print("\n🎉 Demo completed successfully!")
        return client
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        return None


if __name__ == "__main__":
    """
    Main execution block for testing the MCPClient locally.
    """
    def run_static_tests():
        """Run static tests for MCPClient"""
        print("🧪 Running Static Tests...")
        
        tests = []
        
        # Test 1: Configuration validation
        try:
            config = ClientConfiguration(name="test", cache_max_size=100)
            tests.append(("Configuration Creation", True, "Valid config created"))
        except Exception as e:
            tests.append(("Configuration Creation", False, f"Config error: {e}"))
        
        # Test 2: Invalid configuration
        try:
            ClientConfiguration(name="", cache_max_size=0)
            tests.append(("Invalid Configuration", False, "Should have failed validation"))
        except ValueError:
            tests.append(("Invalid Configuration", True, "Properly rejected invalid config"))
        except Exception as e:
            tests.append(("Invalid Configuration", False, f"Unexpected error: {e}"))
        
        # Test 3: Security manager
        try:
            security = SecurityManager(enabled=True)
            valid = security.validate_operation("test_op", {"test": "param"})
            tests.append(("Security Manager", valid, "Security validation works"))
        except Exception as e:
            tests.append(("Security Manager", False, f"Security error: {e}"))
        
        # Test 4: UI Event Emitter
        try:
            emitter = UIEventEmitter(electron_mode=True)
            emitter.emit("test_event", {"data": "test"})
            events = emitter.get_events()
            has_event = len(events) > 0 and events[0]["event"] == "test_event"
            tests.append(("UI Event Emitter", has_event, "Event emission and retrieval works"))
        except Exception as e:
            tests.append(("UI Event Emitter", False, f"Event error: {e}"))
        
        # Test 5: Operation Result
        try:
            result = OperationResult(
                operation_id="test_001",
                operation_type="test",
                success=True,
                data={"result": "success"}
            )
            result_dict = result.to_dict()
            is_valid = (
                result_dict["operation_id"] == "test_001" and
                result_dict["success"] is True and
                "timestamp" in result_dict
            )
            tests.append(("Operation Result", is_valid, "Result serialization works"))
        except Exception as e:
            tests.append(("Operation Result", False, f"Result error: {e}"))
        
        # Print results
        passed = 0
        for test_name, success, message in tests:
            status = "✅" if success else "❌"
            print(f"  {status} {test_name}: {message}")
            if success:
                passed += 1
        
        success_rate = (passed / len(tests)) * 100
        print(f"\n📊 Static Tests: {passed}/{len(tests)} passed ({success_rate:.1f}%)")
        return passed == len(tests)
    
    def run_dynamic_tests():
        """Run dynamic tests for MCPClient"""
        print("\n⚡ Running Dynamic Tests...")
        
        async def async_test_suite():
            tests = []
            
            # Test 1: Client creation with different config types
            try:
                # Test with string
                client1 = MCPClient("string_config_client")
                
                # Test with dict
                client2 = MCPClient({
                    "name": "dict_config_client",
                    "cache_max_size": 50,
                    "electron_mode": True
                })
                
                # Test with ClientConfiguration
                config = ClientConfiguration(
                    name="object_config_client",
                    max_concurrent_operations=5
                )
                client3 = MCPClient(config)
                
                all_created = all([
                    client1.config.name == "string_config_client",
                    client2.config.name == "dict_config_client",
                    client2.config.electron_mode is True,
                    client3.config.name == "object_config_client",
                    client3.config.max_concurrent_operations == 5
                ])
                
                tests.append(("Client Creation Variants", all_created, "All config types work"))
                
                # Cleanup
                await client1.shutdown()
                await client2.shutdown()
                await client3.shutdown()
                
            except Exception as e:
                tests.append(("Client Creation Variants", False, f"Creation error: {e}"))
            
            # Test 2: State management
            try:
                client = MCPClient("state_test_client")
                initial_state = client.state
                
                client._set_state(MCPClientState.BUSY)
                busy_state = client.state
                
                client._set_state(MCPClientState.READY)
                final_state = client.state
                
                state_management_works = (
                    initial_state == MCPClientState.READY and
                    busy_state == MCPClientState.BUSY and
                    final_state == MCPClientState.READY
                )
                
                tests.append(("State Management", state_management_works, "State transitions work"))
                await client.shutdown()
                
            except Exception as e:
                tests.append(("State Management", False, f"State error: {e}"))
            
            # Test 3: Security validation and rate limiting
            try:
                client = MCPClient({
                    "name": "security_test_client",
                    "enable_security_features": True
                })
                
                # Test normal operation
                valid1 = client.security_manager.validate_operation("test_op", {"param": 1})
                
                # Test rate limiting by making many requests
                rate_limit_hit = False
                for i in range(105):  # Exceed the 100/minute limit
                    if not client.security_manager.validate_operation("rapid_op", {"iteration": i}):
                        rate_limit_hit = True
                        break
                
                security_works = valid1 and rate_limit_hit
                tests.append(("Security & Rate Limiting", security_works, "Security validation and rate limiting work"))
                
                await client.shutdown()
                
            except Exception as e:
                tests.append(("Security & Rate Limiting", False, f"Security error: {e}"))
            
            # Test 4: UI Event system
            try:
                client = MCPClient({
                    "name": "ui_test_client",
                    "electron_mode": True
                })
                
                # Emit some events
                client.ui_event_emitter.emit("test_event_1", {"data": "first"})
                client.ui_event_emitter.emit("test_event_2", {"data": "second"})
                
                # Get events
                events = client.get_ui_events()
                
                # Test event filtering
                if len(events) >= 2:
                    first_timestamp = events[0]["timestamp"]
                    filtered_events = client.get_ui_events(since=first_timestamp)
                    
                ui_works = (
                    len(events) >= 3 and  # Including client_initialized event
                    any(event["event"] == "test_event_1" for event in events) and
                    any(event["event"] == "test_event_2" for event in events)
                )
                
                tests.append(("UI Event System", ui_works, "Event emission and retrieval work"))
                
                await client.shutdown()
                
            except Exception as e:
                tests.append(("UI Event System", False, f"UI error: {e}"))
            
            # Test 5: Error handling in operations
            try:
                client = MCPClient("error_test_client")
                
                # Test tool execution with no servers (should fail gracefully)
                result = await client.execute_tool("nonexistent_tool", {})
                
                # Test resource access with no servers (should fail gracefully)
                resource_result = await client.get_resource("nonexistent://resource")
                
                error_handling_works = (
                    isinstance(result, OperationResult) and
                    not result.success and
                    result.error_message is not None and
                    isinstance(resource_result, OperationResult) and
                    not resource_result.success and
                    resource_result.error_message is not None
                )
                
                tests.append(("Error Handling", error_handling_works, "Operations fail gracefully"))
                
                await client.shutdown()
                
            except Exception as e:
                tests.append(("Error Handling", False, f"Error handling failed: {e}"))
            
            # Test 6: Concurrent operations
            try:
                client = MCPClient({
                    "name": "concurrent_test_client",
                    "max_concurrent_operations": 3
                })
                
                # Start multiple operations concurrently
                tasks = []
                for i in range(5):
                    task = client.execute_tool(f"tool_{i}", {"param": i})
                    tasks.append(task)
                
                # Wait for all to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # All should be OperationResult objects (even if they fail)
                all_are_results = all(
                    isinstance(result, OperationResult) or isinstance(result, Exception)
                    for result in results
                )
                
                tests.append(("Concurrent Operations", all_are_results, f"Handled {len(results)} concurrent operations"))
                
                await client.shutdown()
                
            except Exception as e:
                tests.append(("Concurrent Operations", False, f"Concurrency error: {e}"))
            
            # Test 7: Configuration validation edge cases
            try:
                invalid_configs = [
                    {"name": "", "cache_max_size": 100},  # Empty name
                    {"name": "test", "cache_max_size": 0},  # Invalid cache size
                    {"name": "test", "cache_default_ttl": 0},  # Invalid TTL
                    {"name": "test", "max_concurrent_operations": 0},  # Invalid concurrency
                ]
                
                validation_works = True
                for invalid_config in invalid_configs:
                    try:
                        MCPClient(invalid_config)
                        validation_works = False  # Should have failed
                        break
                    except ValueError:
                        continue  # Expected failure
                    except Exception:
                        validation_works = False  # Unexpected error
                        break
                
                tests.append(("Config Validation", validation_works, "Invalid configs properly rejected"))
                
            except Exception as e:
                tests.append(("Config Validation", False, f"Validation error: {e}"))
            
            return tests
        
        # Run async tests
        try:
            test_results = asyncio.run(async_test_suite())
            
            # Print results
            passed = 0
            for test_name, success, message in test_results:
                status = "✅" if success else "❌"
                print(f"  {status} {test_name}: {message}")
                if success:
                    passed += 1
            
            success_rate = (passed / len(test_results)) * 100
            print(f"\n📊 Dynamic Tests: {passed}/{len(test_results)} passed ({success_rate:.1f}%)")
            
            return passed == len(test_results)
            
        except Exception as e:
            print(f"❌ Dynamic test suite failed: {e}")
            return False
    
    # Main test execution
    print("🏃 Running MCPClient Tests")
    print("=" * 60)
    
    # Configure logging for tests
    logging.basicConfig(
        level=logging.WARNING,  # Reduce noise during tests
        format='%(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    static_passed = run_static_tests()
    dynamic_passed = run_dynamic_tests()
    
    # Run main demo if tests pass
    if static_passed and dynamic_passed:
        print("\n✅ All tests passed! Running main demo...")
        main()
    else:
        print("\n❌ Some tests failed. Skipping main demo.")
        print("Please check the test results above and fix any issues.")
    
    # Final summary
    print("\n" + "=" * 60)
    print("🏁 MCPClient Test Summary")
    print("=" * 60)
    print(f"Static Tests: {'✅ PASSED' if static_passed else '❌ FAILED'}")
    print(f"Dynamic Tests: {'✅ PASSED' if dynamic_passed else '❌ FAILED'}")
    print(f"Overall Status: {'✅ SUCCESS' if static_passed and dynamic_passed else '❌ FAILURE'}")
    
    # Additional information for Electron integration
    if static_passed and dynamic_passed:
        print("\n🎨 Electron Integration Notes:")
        print("  • Client state management via client.state property")
        print("  • UI events available via client.get_ui_events()")
        print("  • Real-time status via client.get_client_status()")
        print("  • Audit logging via client.get_audit_log()")
        print("  • Security features via client.security_manager")
        print("  • Graceful shutdown via client.shutdown()")
    
    exit_code = 0 if (static_passed and dynamic_passed) else 1
    print(f"\nExit Code: {exit_code}")
    print("Run with: python -m src.mcp.core.client.mcp_client")