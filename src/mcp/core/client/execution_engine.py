"""
MCP Client Execution Engine - Enterprise Edition

Handles tool execution, resource access, and routing across connected servers.
Designed for scalability, security, high availability, and Electron UI/UX integration.
"""

import asyncio
import hashlib
import json
import logging
import time
import threading
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union, Callable, Tuple


class ExecutionStrategy(Enum):
    """Execution strategies for tool/resource operations"""
    ROUND_ROBIN = "round_robin"
    FASTEST_FIRST = "fastest_first"
    PRIORITY_BASED = "priority_based"
    LOAD_BALANCED = "load_balanced"
    FAILOVER = "failover"
    PARALLEL = "parallel"


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ExecutionConfiguration:
    """Configuration for execution engine with validation"""
    max_concurrent_executions: int = 50
    execution_timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    enable_circuit_breaker: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60
    enable_security_validation: bool = True
    enable_parallel_execution: bool = True
    max_parallel_requests: int = 10
    cache_ttl_seconds: int = 300
    enable_load_balancing: bool = True
    health_check_interval: float = 30.0
    
    def __post_init__(self):
        """Validate configuration"""
        if self.max_concurrent_executions < 1:
            raise ValueError("max_concurrent_executions must be at least 1")
        if self.execution_timeout < 1:
            raise ValueError("execution_timeout must be at least 1")
        if self.retry_attempts < 0:
            raise ValueError("retry_attempts must be non-negative")


@dataclass
class ExecutionRequest:
    """Standardized execution request with metadata"""
    request_id: str
    operation_type: str
    target: str
    parameters: Dict[str, Any]
    strategy: ExecutionStrategy
    priority: int = 5
    timeout: Optional[float] = None
    retry_attempts: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_cache_key(self) -> str:
        """Generate cache key for this request"""
        params_hash = hashlib.md5(
            json.dumps(self.parameters, sort_keys=True).encode()
        ).hexdigest()
        return f"{self.operation_type}:{self.target}:{params_hash}"


@dataclass
class ExecutionResult:
    """Comprehensive execution result with metrics"""
    request_id: str
    success: bool
    data: Any = None
    error_message: str = None
    server_name: str = None
    execution_time: float = 0.0
    cached: bool = False
    attempts: int = 1
    strategy_used: str = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "request_id": self.request_id,
            "success": self.success,
            "data": self.data,
            "error_message": self.error_message,
            "server_name": self.server_name,
            "execution_time": self.execution_time,
            "cached": self.cached,
            "attempts": self.attempts,
            "strategy_used": self.strategy_used,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class CircuitBreaker:
    """Circuit breaker for server protection"""
    
    def __init__(self, threshold: int = 5, timeout: int = 60, name: str = "default"):
        self.threshold = threshold
        self.timeout = timeout
        self.name = name
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
        self._lock = threading.Lock()
    
    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            elif self.state == CircuitState.OPEN:
                if (self.last_failure_time and 
                    datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout)):
                    self.state = CircuitState.HALF_OPEN
                    return True
                return False
            else:  # HALF_OPEN
                return True
    
    def record_success(self):
        """Record successful execution"""
        with self._lock:
            self.failure_count = 0
            self.state = CircuitState.CLOSED
    
    def record_failure(self):
        """Record failed execution"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.failure_count >= self.threshold:
                self.state = CircuitState.OPEN
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "threshold": self.threshold,
                "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None
            }


class SecurityValidator:
    """Security validation for execution requests"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.blocked_tools: Set[str] = set()
        self.blocked_patterns: Set[str] = set()
        self.max_parameter_size = 1024 * 1024  # 1MB
        self.max_parameter_depth = 10
    
    def validate_tool_execution(self, tool_name: str, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate tool execution request"""
        if not self.enabled:
            return True, "Security validation disabled"
        
        # Check blocked tools
        if tool_name in self.blocked_tools:
            return False, f"Tool '{tool_name}' is blocked"
        
        # Check blocked patterns
        for pattern in self.blocked_patterns:
            if pattern in tool_name:
                return False, f"Tool matches blocked pattern: {pattern}"
        
        return True, "Tool is valid"
    
    def validate_resource_access(self, uri: str) -> Tuple[bool, str]:
        """Validate resource access request"""
        if not self.enabled:
            return True, "Security validation disabled"
        
        # Check for dangerous protocols
        dangerous_protocols = ["file://", "ftp://", "sftp://"]
        if any(uri.startswith(proto) for proto in dangerous_protocols):
            return False, f"Dangerous protocol in URI: {uri}"
        
        # Check for path traversal
        if ".." in uri:
            return False, f"Path traversal detected in URI: {uri}"
        
        return True, "URI is valid"
    
    def block_tool(self, tool_name: str):
        """Block a tool from execution"""
        self.blocked_tools.add(tool_name)
    
    def unblock_tool(self, tool_name: str):
        """Unblock a tool"""
        self.blocked_tools.discard(tool_name)


class LoadBalancer:
    """Load balancer for server selection"""
    
    def __init__(self, strategy: ExecutionStrategy = ExecutionStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self.server_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "request_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "average_response_time": 0.0,
            "current_load": 0
        })
        self.round_robin_index = 0
        self._lock = threading.Lock()
    
    def select_server(self, available_servers: List[str]) -> Optional[str]:
        """Select best server based on strategy"""
        if not available_servers:
            return None
        
        with self._lock:
            if self.strategy == ExecutionStrategy.ROUND_ROBIN:
                server = available_servers[self.round_robin_index % len(available_servers)]
                self.round_robin_index += 1
                return server
            elif self.strategy == ExecutionStrategy.FASTEST_FIRST:
                fastest_server = min(
                    available_servers,
                    key=lambda s: self.server_metrics[s]["average_response_time"]
                )
                return fastest_server
            elif self.strategy == ExecutionStrategy.LOAD_BALANCED:
                least_loaded = min(
                    available_servers,
                    key=lambda s: self.server_metrics[s]["current_load"]
                )
                return least_loaded
            else:
                return available_servers[0]
    
    def record_request_start(self, server_name: str):
        """Record request start for load tracking"""
        with self._lock:
            self.server_metrics[server_name]["request_count"] += 1
            self.server_metrics[server_name]["current_load"] += 1
    
    def record_request_end(self, server_name: str, success: bool, response_time: float):
        """Record request completion"""
        with self._lock:
            metrics = self.server_metrics[server_name]
            metrics["current_load"] = max(0, metrics["current_load"] - 1)
            
            if success:
                metrics["success_count"] += 1
            else:
                metrics["failure_count"] += 1
            
            # Update average response time
            if metrics["average_response_time"] == 0:
                metrics["average_response_time"] = response_time
            else:
                metrics["average_response_time"] = (
                    metrics["average_response_time"] * 0.8 + response_time * 0.2
                )
    
    def get_server_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get server performance metrics"""
        with self._lock:
            return dict(self.server_metrics)


class ExecutionEngine:
    """
    Enterprise-grade execution engine for MCP operations.
    
    Features:
    - High-availability with circuit breakers and failover
    - Advanced load balancing and server selection
    - Security validation and request sanitization
    - Parallel execution and performance optimization
    - Comprehensive monitoring and metrics
    - Real-time UI/UX integration
    """
    
    def __init__(self, 
                 connection_manager,
                 cache_manager,
                 response_formatter,
                 logger: logging.Logger,
                 config: Optional[ExecutionConfiguration] = None):
        """Initialize enterprise execution engine"""
        self.connection_manager = connection_manager
        self.cache_manager = cache_manager
        self.response_formatter = response_formatter
        self.logger = logger
        self.config = config or ExecutionConfiguration()
        
        # Core components
        self.security_validator = SecurityValidator(self.config.enable_security_validation)
        self.load_balancer = LoadBalancer()
        
        # Indexes for fast lookup (thread-safe)
        self._indexes_lock = threading.RLock()
        self.tool_index: Dict[str, List[str]] = {}
        self.resource_index: Dict[str, List[str]] = {}
        self.prompt_index: Dict[str, List[str]] = {}
        
        # Circuit breakers per server
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Execution tracking
        self.active_executions: Dict[str, asyncio.Task] = {}
        self.execution_semaphore = asyncio.Semaphore(self.config.max_concurrent_executions)
        
        # Metrics and monitoring
        self.execution_metrics = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'security_violations': 0,
            'circuit_breaker_trips': 0,
            'average_execution_time': 0.0,
            'parallel_executions': 0
        }
        
        # Event system for UI integration
        self.event_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self.event_queue: deque = deque(maxlen=1000)
        
        # Background tasks
        self.background_tasks: Set[asyncio.Task] = set()
        self.is_running = False
        
        self.logger.info(f"Execution engine initialized - concurrent: {self.config.max_concurrent_executions}")
    
    def _emit_event(self, event_name: str, data: Any):
        """Emit event for UI/monitoring systems"""
        event = {
            "event": event_name,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "engine_id": id(self)
        }
        
        self.event_queue.append(event)
        
        # Call registered callbacks
        for callback in self.event_callbacks[event_name]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(data))
                else:
                    callback(data)
            except Exception as e:
                self.logger.error(f"Error in event callback {event_name}: {e}")
    
    def on(self, event_name: str, callback: Callable):
        """Register event callback for UI integration"""
        self.event_callbacks[event_name].append(callback)
    
    def get_events(self, since: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get events for UI consumption"""
        events = list(self.event_queue)
        
        if since:
            try:
                since_dt = datetime.fromisoformat(since)
                events = [
                    event for event in events
                    if datetime.fromisoformat(event["timestamp"]) > since_dt
                ]
            except ValueError:
                pass
        
        if limit:
            events = events[-limit:]
        
        return events
    
    async def start_background_tasks(self):
        """Start background maintenance tasks"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Health monitoring task
        health_task = asyncio.create_task(self._background_health_monitor())
        self.background_tasks.add(health_task)
        health_task.add_done_callback(self.background_tasks.discard)
        
        self.logger.info("Execution engine background tasks started")
    
    async def stop_background_tasks(self):
        """Stop background tasks"""
        self.is_running = False
        
        for task in self.background_tasks.copy():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Execution engine stopped")
    
    async def _background_health_monitor(self):
        """Background task for health monitoring"""
        while self.is_running:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                if not self.is_running:
                    break
                
                # Update server health metrics
                connected_servers = self.connection_manager.get_connected_servers()
                healthy_servers = self.connection_manager.get_healthy_servers()
                
                self._emit_event("health_update", {
                    "connected_servers": len(connected_servers),
                    "healthy_servers": len(healthy_servers)
                })
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health monitor: {e}")
    
    def _get_circuit_breaker(self, server_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for server"""
        if server_name not in self.circuit_breakers:
            self.circuit_breakers[server_name] = CircuitBreaker(
                threshold=self.config.circuit_breaker_threshold,
                timeout=self.config.circuit_breaker_timeout,
                name=server_name
            )
        return self.circuit_breakers[server_name]
    
    def _validate_server_connection(self, server_name: str) -> Optional[Any]:
        """Validate server connection with circuit breaker"""
        connection = self.connection_manager.get_connection(server_name)
        if not connection:
            return None
        
        if not connection.is_healthy:
            return None
        
        # Check circuit breaker
        if self.config.enable_circuit_breaker:
            circuit_breaker = self._get_circuit_breaker(server_name)
            if not circuit_breaker.can_execute():
                return None
        
        return connection
    
    async def execute_tool(self, 
                          tool_name: str, 
                          parameters: Dict[str, Any],
                          strategy: Optional[ExecutionStrategy] = None,
                          timeout: Optional[float] = None,
                          priority: int = 5) -> ExecutionResult:
        """Execute a tool with enterprise features"""
        request = ExecutionRequest(
            request_id=str(uuid.uuid4()),
            operation_type="tool",
            target=tool_name,
            parameters=parameters,
            strategy=strategy or ExecutionStrategy.ROUND_ROBIN,
            timeout=timeout or self.config.execution_timeout,
            priority=priority
        )
        
        return await self._execute_request(request)
    
    async def get_resource(self,
                          uri: str,
                          strategy: Optional[ExecutionStrategy] = None,
                          timeout: Optional[float] = None,
                          priority: int = 5) -> ExecutionResult:
        """Get a resource with enterprise features"""
        request = ExecutionRequest(
            request_id=str(uuid.uuid4()),
            operation_type="resource",
            target=uri,
            parameters={},
            strategy=strategy or ExecutionStrategy.ROUND_ROBIN,
            timeout=timeout or self.config.execution_timeout,
            priority=priority
        )
        
        return await self._execute_request(request)
    
    async def _execute_request(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute a request with full enterprise capabilities"""
        start_time = time.time()
        
        try:
            async with self.execution_semaphore:
                # Security validation
                if request.operation_type == "tool":
                    valid, reason = self.security_validator.validate_tool_execution(
                        request.target, request.parameters
                    )
                    if not valid:
                        self.execution_metrics['security_violations'] += 1
                        return ExecutionResult(
                            request_id=request.request_id,
                            success=False,
                            error_message=f"Security validation failed: {reason}",
                            execution_time=time.time() - start_time
                        )
                
                elif request.operation_type == "resource":
                    valid, reason = self.security_validator.validate_resource_access(request.target)
                    if not valid:
                        self.execution_metrics['security_violations'] += 1
                        return ExecutionResult(
                            request_id=request.request_id,
                            success=False,
                            error_message=f"Security validation failed: {reason}",
                            execution_time=time.time() - start_time
                        )
                
                # Check cache first
                cache_key = request.to_cache_key()
                cached_result = self.cache_manager.get(cache_key)
                
                if cached_result is not None:
                    self.execution_metrics['cache_hits'] += 1
                    return ExecutionResult(
                        request_id=request.request_id,
                        success=True,
                        data=cached_result,
                        cached=True,
                        execution_time=time.time() - start_time,
                        strategy_used=request.strategy.value
                    )
                
                self.execution_metrics['cache_misses'] += 1
                
                # Execute based on strategy
                if request.strategy == ExecutionStrategy.PARALLEL:
                    result = await self._execute_parallel(request)
                else:
                    result = await self._execute_sequential(request)
                
                # Cache successful results
                if result.success and result.data is not None:
                    self.cache_manager.set(
                        cache_key,
                        result.data,
                        ttl=self.config.cache_ttl_seconds,
                        tags={f"{request.operation_type}:{request.target}"}
                    )
                
                # Update metrics
                if result.success:
                    self.execution_metrics['successful_executions'] += 1
                else:
                    self.execution_metrics['failed_executions'] += 1
                
                self.execution_metrics['total_executions'] += 1
                
                # Update average execution time
                if self.execution_metrics['average_execution_time'] == 0:
                    self.execution_metrics['average_execution_time'] = result.execution_time
                else:
                    self.execution_metrics['average_execution_time'] = (
                        self.execution_metrics['average_execution_time'] * 0.9 + 
                        result.execution_time * 0.1
                    )
                
                return result
                
        except Exception as e:
            self.logger.error(f"Execution error for {request.target}: {e}")
            return ExecutionResult(
                request_id=request.request_id,
                success=False,
                error_message=str(e),
                execution_time=time.time() - start_time
            )
    
    async def _execute_sequential(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute request sequentially with retry logic"""
        # Get available servers
        if request.operation_type == "tool":
            available_servers = self._get_servers_for_tool(request.target)
        elif request.operation_type == "resource":
            available_servers = self._get_servers_for_resource(request.target)
        else:
            available_servers = []
        
        if not available_servers:
            return ExecutionResult(
                request_id=request.request_id,
                success=False,
                error_message=f"{request.operation_type.title()} '{request.target}' not found",
                attempts=0
            )
        
        # Filter healthy servers
        healthy_servers = [
            server for server in available_servers
            if self._validate_server_connection(server) is not None
        ]
        
        if not healthy_servers:
            return ExecutionResult(
                request_id=request.request_id,
                success=False,
                error_message="No healthy servers available",
                attempts=0
            )
        
        # Try executing on servers
        last_error = None
        
        for attempt in range(1, request.retry_attempts + 1):
            server_name = self.load_balancer.select_server(healthy_servers)
            if not server_name:
                break
            
            connection = self._validate_server_connection(server_name)
            if not connection:
                continue
            
            circuit_breaker = self._get_circuit_breaker(server_name)
            
            try:
                self.load_balancer.record_request_start(server_name)
                start_time = time.time()
                
                if request.operation_type == "tool":
                    result_data = await asyncio.wait_for(
                        connection.server.execute_tool(request.target, request.parameters),
                        timeout=request.timeout
                    )
                elif request.operation_type == "resource":
                    result_data = await asyncio.wait_for(
                        connection.server.get_resource(request.target),
                        timeout=request.timeout
                    )
                else:
                    raise ValueError(f"Unsupported operation type: {request.operation_type}")
                
                execution_time = time.time() - start_time
                
                # Record success
                circuit_breaker.record_success()
                self.load_balancer.record_request_end(server_name, True, execution_time)
                
                return ExecutionResult(
                    request_id=request.request_id,
                    success=True,
                    data=result_data,
                    server_name=server_name,
                    execution_time=execution_time,
                    attempts=attempt,
                    strategy_used=request.strategy.value
                )
                
            except Exception as e:
                execution_time = time.time() - start_time
                last_error = str(e)
                
                # Record failure
                circuit_breaker.record_failure()
                self.load_balancer.record_request_end(server_name, False, execution_time)
                
                if circuit_breaker.state == CircuitState.OPEN:
                    self.execution_metrics['circuit_breaker_trips'] += 1
        
        return ExecutionResult(
            request_id=request.request_id,
            success=False,
            error_message=f"All retry attempts failed. Last error: {last_error}",
            attempts=request.retry_attempts
        )
    
    async def _execute_parallel(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute request in parallel across multiple servers"""
        # Get available servers
        if request.operation_type == "tool":
            available_servers = self._get_servers_for_tool(request.target)
        elif request.operation_type == "resource":
            available_servers = self._get_servers_for_resource(request.target)
        else:
            available_servers = []
        
        if not available_servers:
            return ExecutionResult(
                request_id=request.request_id,
                success=False,
                error_message=f"{request.operation_type.title()} '{request.target}' not found"
            )
        
        # Filter healthy servers
        healthy_servers = [
            server for server in available_servers
            if self._validate_server_connection(server) is not None
        ][:self.config.max_parallel_requests]
        
        if not healthy_servers:
            return ExecutionResult(
                request_id=request.request_id,
                success=False,
                error_message="No healthy servers available"
            )
        
        # Create parallel tasks
        tasks = []
        start_time = time.time()
        
        for server_name in healthy_servers:
            task = asyncio.create_task(
                self._execute_on_server(request, server_name)
            )
            tasks.append(task)
        
        self.execution_metrics['parallel_executions'] += 1
        
        try:
            # Wait for first successful result
            done, pending = await asyncio.wait(
                tasks,
                timeout=request.timeout,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
            
            # Check results
            for task in done:
                try:
                    result = await task
                    if result.success:
                        result.execution_time = time.time() - start_time
                        result.strategy_used = "parallel"
                        return result
                except Exception:
                    continue
            
            return ExecutionResult(
                request_id=request.request_id,
                success=False,
                error_message="Parallel execution failed",
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return ExecutionResult(
                request_id=request.request_id,
                success=False,
                error_message=f"Parallel execution error: {e}",
                execution_time=time.time() - start_time
            )
    
    async def _execute_on_server(self, request: ExecutionRequest, server_name: str) -> ExecutionResult:
        """Execute request on a specific server"""
        connection = self._validate_server_connection(server_name)
        if not connection:
            return ExecutionResult(
                request_id=request.request_id,
                success=False,
                error_message=f"Server {server_name} not available",
                server_name=server_name
            )
        
        circuit_breaker = self._get_circuit_breaker(server_name)
        start_time = time.time()
        
        try:
            self.load_balancer.record_request_start(server_name)
            
            if request.operation_type == "tool":
                result_data = await connection.server.execute_tool(
                    request.target, request.parameters
                )
            elif request.operation_type == "resource":
                result_data = await connection.server.get_resource(request.target)
            else:
                raise ValueError(f"Unsupported operation: {request.operation_type}")
            
            execution_time = time.time() - start_time
            
            # Record success
            circuit_breaker.record_success()
            self.load_balancer.record_request_end(server_name, True, execution_time)
            
            return ExecutionResult(
                request_id=request.request_id,
                success=True,
                data=result_data,
                server_name=server_name,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Record failure
            circuit_breaker.record_failure()
            self.load_balancer.record_request_end(server_name, False, execution_time)
            
            return ExecutionResult(
                request_id=request.request_id,
                success=False,
                error_message=str(e),
                server_name=server_name,
                execution_time=execution_time
            )
    
    def _get_servers_for_tool(self, tool_name: str) -> List[str]:
        """Get servers that have a specific tool"""
        with self._indexes_lock:
            servers = self.tool_index.get(tool_name, [])
            if not servers:
                servers = self._discover_servers_with_tool(tool_name)
            return servers.copy()
    
    def _get_servers_for_resource(self, uri: str) -> List[str]:
        """Get servers that have a specific resource"""
        with self._indexes_lock:
            servers = self.resource_index.get(uri, [])
            if not servers:
                servers = self._discover_servers_with_resource(uri)
            return servers.copy()
    
    def _discover_servers_with_tool(self, tool_name: str) -> List[str]:
        """Dynamically discover servers that have a tool"""
        servers_with_tool = []
        
        for server_name in self.connection_manager.get_connected_servers():
            connection = self._validate_server_connection(server_name)
            if not connection:
                continue
            
            try:
                tools = connection.server.get_tools()
                if tool_name in tools:
                    servers_with_tool.append(server_name)
                    # Update index
                    with self._indexes_lock:
                        if tool_name not in self.tool_index:
                            self.tool_index[tool_name] = []
                        if server_name not in self.tool_index[tool_name]:
                            self.tool_index[tool_name].append(server_name)
            except Exception as e:
                self.logger.warning(f"Error discovering tools on {server_name}: {e}")
        
        return servers_with_tool
    
    def _discover_servers_with_resource(self, uri: str) -> List[str]:
        """Dynamically discover servers that have a resource"""
        servers_with_resource = []
        
        for server_name in self.connection_manager.get_connected_servers():
            connection = self._validate_server_connection(server_name)
            if not connection:
                continue
            
            try:
                resources = connection.server.get_resources()
                if uri in resources:
                    servers_with_resource.append(server_name)
                    # Update index
                    with self._indexes_lock:
                        if uri not in self.resource_index:
                            self.resource_index[uri] = []
                        if server_name not in self.resource_index[uri]:
                            self.resource_index[uri].append(server_name)
            except Exception as e:
                self.logger.warning(f"Error discovering resources on {server_name}: {e}")
        
        return servers_with_resource
    
    def update_indexes(self, server_name: str, server) -> None:
        """Update indexes with tools/resources/prompts from a server"""
        try:
            with self._indexes_lock:
                # Update tool index
                tools = server.get_tools()
                for tool_name in tools:
                    if tool_name not in self.tool_index:
                        self.tool_index[tool_name] = []
                    if server_name not in self.tool_index[tool_name]:
                        self.tool_index[tool_name].append(server_name)
                
                # Update resource index
                resources = server.get_resources()
                for resource_uri in resources:
                    if resource_uri not in self.resource_index:
                        self.resource_index[resource_uri] = []
                    if server_name not in self.resource_index[resource_uri]:
                        self.resource_index[resource_uri].append(server_name)
                
                # Update prompt index
                prompts = server.get_prompts()
                for prompt_name in prompts:
                    if prompt_name not in self.prompt_index:
                        self.prompt_index[prompt_name] = []
                    if server_name not in self.prompt_index[prompt_name]:
                        self.prompt_index[prompt_name].append(server_name)
            
            self._emit_event("indexes_updated", {
                "server_name": server_name,
                "tools_count": len(tools),
                "resources_count": len(resources),
                "prompts_count": len(prompts)
            })
            
            self.logger.debug(f"Updated indexes for server: {server_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to update indexes for server {server_name}: {e}")
    
    def remove_from_indexes(self, server_name: str) -> None:
        """Remove server from all indexes"""
        try:
            with self._indexes_lock:
                # Remove from tool index
                for tool_name, servers in list(self.tool_index.items()):
                    if server_name in servers:
                        servers.remove(server_name)
                    if not servers:
                        del self.tool_index[tool_name]
                
                # Remove from resource index
                for resource_uri, servers in list(self.resource_index.items()):
                    if server_name in servers:
                        servers.remove(server_name)
                    if not servers:
                        del self.resource_index[resource_uri]
                
                # Remove from prompt index
                for prompt_name, servers in list(self.prompt_index.items()):
                    if server_name in servers:
                        servers.remove(server_name)
                    if not servers:
                        del self.prompt_index[prompt_name]
            
            # Clear cache entries from this server
            self.cache_manager.clear(tags={f"server:{server_name}"})
            
            # Remove circuit breaker
            if server_name in self.circuit_breakers:
                del self.circuit_breakers[server_name]
            
            self._emit_event("server_removed", {"server_name": server_name})
            self.logger.debug(f"Removed server from indexes: {server_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to remove server {server_name} from indexes: {e}")
    
    def get_execution_metrics(self) -> Dict[str, Any]:
        """Get comprehensive execution metrics"""
        load_balancer_metrics = self.load_balancer.get_server_metrics()
        circuit_breaker_status = {
            name: cb.get_status()
            for name, cb in self.circuit_breakers.items()
        }
        
        return {
            "execution_stats": self.execution_metrics.copy(),
            "server_metrics": load_balancer_metrics,
            "circuit_breakers": circuit_breaker_status,
            "indexes": {
                "tools_count": len(self.tool_index),
                "resources_count": len(self.resource_index),
                "prompts_count": len(self.prompt_index),
                "total_tool_instances": sum(len(servers) for servers in self.tool_index.values()),
                "total_resource_instances": sum(len(servers) for servers in self.resource_index.values())
            },
            "active_executions": len(self.active_executions),
            "configuration": {
                "max_concurrent": self.config.max_concurrent_executions,
                "circuit_breaker_enabled": self.config.enable_circuit_breaker,
                "security_enabled": self.config.enable_security_validation,
                "parallel_enabled": self.config.enable_parallel_execution
            }
        }
    
    def get_ui_metrics(self) -> Dict[str, Any]:
        """Get metrics optimized for UI dashboard"""
        metrics = self.get_execution_metrics()
        
        # Calculate derived metrics
        total_requests = (metrics["execution_stats"]["successful_executions"] + 
                         metrics["execution_stats"]["failed_executions"])
        success_rate = 0.0
        if total_requests > 0:
            success_rate = (metrics["execution_stats"]["successful_executions"] / total_requests) * 100
        
        cache_total = metrics["execution_stats"]["cache_hits"] + metrics["execution_stats"]["cache_misses"]
        cache_hit_rate = 0.0
        if cache_total > 0:
            cache_hit_rate = (metrics["execution_stats"]["cache_hits"] / cache_total) * 100
        
        return {
            "performance": {
                "success_rate": round(success_rate, 2),
                "cache_hit_rate": round(cache_hit_rate, 2),
                "average_execution_time": round(metrics["execution_stats"]["average_execution_time"] * 1000, 2),
                "total_executions": total_requests,
                "active_executions": metrics["active_executions"]
            },
            "availability": {
                "circuit_breakers_open": len([
                    cb for cb in metrics["circuit_breakers"].values() 
                    if cb["state"] == "open"
                ]),
                "healthy_servers": len([
                    server for server, server_metrics in metrics["server_metrics"].items()
                    if server_metrics["success_count"] > server_metrics["failure_count"]
                ]),
                "total_servers": len(metrics["server_metrics"])
            },
            "capacity": {
                "tools_available": metrics["indexes"]["tools_count"],
                "resources_available": metrics["indexes"]["resources_count"],
                "concurrent_limit": metrics["configuration"]["max_concurrent"],
                "utilization": (metrics["active_executions"] / metrics["configuration"]["max_concurrent"]) * 100
            },
            "security": {
                "violations": metrics["execution_stats"]["security_violations"],
                "validation_enabled": metrics["configuration"]["security_enabled"]
            },
            "last_updated": datetime.now().isoformat()
        }
    
    def get_server_performance(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed server performance metrics"""
        server_metrics = self.load_balancer.get_server_metrics()
        circuit_status = {name: cb.get_status() for name, cb in self.circuit_breakers.items()}
        
        combined_metrics = {}
        for server_name, metrics in server_metrics.items():
            combined_metrics[server_name] = {
                **metrics,
                "circuit_breaker": circuit_status.get(server_name, {"state": "unknown"}),
                "tools_count": len([
                    tool for tool, servers in self.tool_index.items()
                    if server_name in servers
                ]),
                "resources_count": len([
                    resource for resource, servers in self.resource_index.items()
                    if server_name in servers
                ])
            }
        
        return combined_metrics
    
    def get_available_operations(self) -> Dict[str, Dict[str, Any]]:
        """Get all available operations across servers"""
        with self._indexes_lock:
            return {
                "tools": {
                    tool_name: {
                        "servers": servers.copy(),
                        "server_count": len(servers)
                    }
                    for tool_name, servers in self.tool_index.items()
                },
                "resources": {
                    resource_uri: {
                        "servers": servers.copy(),
                        "server_count": len(servers)
                    }
                    for resource_uri, servers in self.resource_index.items()
                },
                "prompts": {
                    prompt_name: {
                        "servers": servers.copy(),
                        "server_count": len(servers)
                    }
                    for prompt_name, servers in self.prompt_index.items()
                }
            }
    
    def block_tool(self, tool_name: str):
        """Block a tool from execution"""
        self.security_validator.block_tool(tool_name)
        self._emit_event("tool_blocked", {"tool_name": tool_name})
        self.logger.warning(f"Blocked tool: {tool_name}")
    
    def unblock_tool(self, tool_name: str):
        """Unblock a tool"""
        self.security_validator.unblock_tool(tool_name)
        self._emit_event("tool_unblocked", {"tool_name": tool_name})
        self.logger.info(f"Unblocked tool: {tool_name}")
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get security configuration and status"""
        return {
            "validation_enabled": self.security_validator.enabled,
            "blocked_tools": list(self.security_validator.blocked_tools),
            "blocked_patterns": list(self.security_validator.blocked_patterns),
            "violations_count": self.execution_metrics["security_violations"]
        }


def main():
    """Main function demonstrating Enterprise Execution Engine usage"""
    print("🚀 Enterprise Execution Engine - High Performance & Security")
    print("=" * 70)
    
    async def demo_execution_engine():
        """Demonstrate execution engine capabilities"""
        
        # Mock dependencies for demonstration
        class MockConnectionManager:
            def __init__(self):
                self.servers = {
                    "fast_server": {"healthy": True, "response_time": 0.1},
                    "slow_server": {"healthy": True, "response_time": 0.5}
                }
            
            def get_connected_servers(self):
                return list(self.servers.keys())
            
            def get_healthy_servers(self):
                return [name for name, info in self.servers.items() if info["healthy"]]
            
            def get_connection(self, name):
                if name in self.servers:
                    class MockConnection:
                        def __init__(self, server_info):
                            self.is_healthy = server_info["healthy"]
                            self.server = MockServer(server_info["response_time"])
                    return MockConnection(self.servers[name])
                return None
        
        class MockServer:
            def __init__(self, response_time=0.1):
                self.response_time = response_time
            
            def get_tools(self):
                return {
                    "data_analyzer": {"description": "Analyze data"},
                    "file_processor": {"description": "Process files"}
                }
            
            def get_resources(self):
                return {
                    "data://dataset1": {"type": "dataset"}
                }
            
            def get_prompts(self):
                return {"summary_prompt": {"description": "Summarize content"}}
            
            async def execute_tool(self, tool_name, parameters):
                await asyncio.sleep(self.response_time)
                return {
                    "tool": tool_name,
                    "parameters": parameters,
                    "result": f"Executed {tool_name} successfully"
                }
            
            async def get_resource(self, uri):
                await asyncio.sleep(self.response_time)
                return {
                    "uri": uri,
                    "content": f"Resource content for {uri}"
                }
        
        class MockCacheManager:
            def __init__(self):
                self.cache = {}
            
            def get(self, key):
                return self.cache.get(key)
            
            def set(self, key, value, ttl=None, tags=None):
                self.cache[key] = value
            
            def clear(self, tags=None):
                if tags:
                    keys_to_remove = []
                    for key in self.cache:
                        for tag in tags:
                            if tag in key:
                                keys_to_remove.append(key)
                                break
                    for key in keys_to_remove:
                        del self.cache[key]
                else:
                    self.cache.clear()
        
        class MockResponseFormatter:
            def format_success(self, data, **metadata):
                return {"success": True, "data": data, **metadata}
            
            def format_error(self, error, **metadata):
                return {"success": False, "error": error, **metadata}
        
        # Create execution engine
        config = ExecutionConfiguration(
            max_concurrent_executions=20,
            enable_circuit_breaker=True,
            enable_security_validation=True,
            enable_parallel_execution=True
        )
        
        connection_manager = MockConnectionManager()
        cache_manager = MockCacheManager()
        response_formatter = MockResponseFormatter()
        logger = logging.getLogger("demo_execution_engine")
        
        engine = ExecutionEngine(
            connection_manager, cache_manager, response_formatter, logger, config
        )
        
        print(f"✅ Execution Engine created")
        print(f"   Max concurrent: {config.max_concurrent_executions}")
        print(f"   Security enabled: {config.enable_security_validation}")
        print(f"   Circuit breakers: {config.enable_circuit_breaker}")
        
        # Start background tasks
        await engine.start_background_tasks()
        print(f"   Background tasks: 🟢 RUNNING")
        
        # Update indexes
        print(f"\n📚 Index Management:")
        for server_name in connection_manager.get_connected_servers():
            connection = connection_manager.get_connection(server_name)
            if connection and connection.is_healthy:
                engine.update_indexes(server_name, connection.server)
        
        operations = engine.get_available_operations()
        print(f"   Tools indexed: {len(operations['tools'])}")
        print(f"   Resources indexed: {len(operations['resources'])}")
        
        # Demonstrate tool execution
        print(f"\n🔧 Tool Execution:")
        
        result = await engine.execute_tool(
            "data_analyzer",
            {"data": "sample_data", "format": "json"}
        )
        print(f"   Tool execution: {'✅ SUCCESS' if result.success else '❌ FAILED'} "
              f"({result.execution_time:.3f}s)")
        
        # Demonstrate caching
        print(f"\n🗄️ Caching Performance:")
        
        # First execution (cache miss)
        start_time = time.time()
        result1 = await engine.execute_tool("data_analyzer", {"test": "cache"})
        first_time = time.time() - start_time
        
        # Second execution (cache hit)
        start_time = time.time()
        result2 = await engine.execute_tool("data_analyzer", {"test": "cache"})
        second_time = time.time() - start_time
        
        print(f"   First execution: {first_time:.3f}s (cache miss)")
        print(f"   Second execution: {second_time:.3f}s (cache hit: {result2.cached})")
        
        # Demonstrate security features
        print(f"\n🔒 Security Features:")
        
        # Valid tool execution
        valid_result = await engine.execute_tool("data_analyzer", {"valid": "parameters"})
        print(f"   Valid execution: {'✅ ALLOWED' if valid_result.success else '❌ BLOCKED'}")
        
        # Block a tool
        engine.block_tool("dangerous_tool")
        blocked_result = await engine.execute_tool("dangerous_tool", {})
        print(f"   Blocked tool: {'✅ BLOCKED' if not blocked_result.success else '❌ ALLOWED'}")
        
        # Demonstrate performance metrics
        print(f"\n📊 Performance Metrics:")
        ui_metrics = engine.get_ui_metrics()
        
        performance = ui_metrics['performance']
        availability = ui_metrics['availability']
        capacity = ui_metrics['capacity']
        
        print(f"   Success rate: {performance['success_rate']:.1f}%")
        print(f"   Cache hit rate: {performance['cache_hit_rate']:.1f}%")
        print(f"   Avg execution time: {performance['average_execution_time']:.1f}ms")
        print(f"   Tools available: {capacity['tools_available']}")
        
        # Cleanup
        await engine.stop_background_tasks()
        print(f"\n🧹 Cleanup completed")
        
        return engine
    
    # Run demonstration
    try:
        engine = asyncio.run(demo_execution_engine())
        print("\n🎉 Demo completed successfully!")
        return engine
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        return None


if __name__ == "__main__":
    """Main execution block for testing the Enterprise Execution Engine locally"""
    
    def run_static_tests():
        """Run static tests for Execution Engine"""
        print("🧪 Running Static Tests...")
        
        tests = []
        
        # Test 1: Configuration validation
        try:
            config = ExecutionConfiguration(
                max_concurrent_executions=10,
                enable_security_validation=True,
                enable_circuit_breaker=True
            )
            tests.append(("Configuration Creation", True, "Valid config created"))
        except Exception as e:
            tests.append(("Configuration Creation", False, f"Config error: {e}"))
        
        # Test 2: Invalid configuration
        try:
            ExecutionConfiguration(max_concurrent_executions=0, execution_timeout=0)
            tests.append(("Invalid Config Validation", False, "Should have failed"))
        except ValueError:
            tests.append(("Invalid Config Validation", True, "Properly rejected invalid config"))
        
        # Test 3: Security validator
        try:
            validator = SecurityValidator(enabled=True)
            
            valid, reason = validator.validate_tool_execution("safe_tool", {"param": "value"})
            invalid, reason = validator.validate_resource_access("file:///etc/passwd")
            
            security_works = valid and not invalid
            tests.append(("Security Validator", security_works, "Security validation works"))
        except Exception as e:
            tests.append(("Security Validator", False, f"Security error: {e}"))
        
        # Test 4: Circuit breaker
        try:
            breaker = CircuitBreaker(threshold=3, timeout=60)
            
            # Should be closed initially
            initial_state = breaker.can_execute()
            
            # Record failures to trip it
            for _ in range(3):
                breaker.record_failure()
            
            # Should be open now
            tripped_state = not breaker.can_execute()
            
            circuit_works = initial_state and tripped_state
            tests.append(("Circuit Breaker", circuit_works, "Circuit breaker logic works"))
        except Exception as e:
            tests.append(("Circuit Breaker", False, f"Circuit breaker error: {e}"))
        
        # Test 5: Load balancer
        try:
            balancer = LoadBalancer(ExecutionStrategy.ROUND_ROBIN)
            
            servers = ["server1", "server2", "server3"]
            selected1 = balancer.select_server(servers)
            selected2 = balancer.select_server(servers)
            
            # Should round robin
            round_robin_works = (selected1 != selected2)
            tests.append(("Load Balancer", round_robin_works, "Load balancer selection works"))
        except Exception as e:
            tests.append(("Load Balancer", False, f"Load balancer error: {e}"))
        
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
        """Run dynamic tests for Execution Engine"""
        print("\n⚡ Running Dynamic Tests...")
        
        async def async_test_suite():
            tests = []
            
            # Mock classes for testing
            class MockConnectionManager:
                def get_connected_servers(self):
                    return ["test_server"]
                
                def get_healthy_servers(self):
                    return ["test_server"]
                
                def get_connection(self, name):
                    class MockConnection:
                        def __init__(self):
                            self.is_healthy = True
                            self.server = MockServer()
                    return MockConnection() if name == "test_server" else None
            
            class MockServer:
                def get_tools(self):
                    return {"test_tool": {}}
                
                def get_resources(self):
                    return {"test://resource": {}}
                
                def get_prompts(self):
                    return {"test_prompt": {}}
                
                async def execute_tool(self, tool, params):
                    return {"result": f"executed {tool}"}
                
                async def get_resource(self, uri):
                    return {"content": f"resource {uri}"}
            
            class MockCacheManager:
                def __init__(self):
                    self.cache = {}
                
                def get(self, key):
                    return self.cache.get(key)
                
                def set(self, key, value, **kwargs):
                    self.cache[key] = value
                
                def clear(self, **kwargs):
                    self.cache.clear()
            
            class MockResponseFormatter:
                def format_success(self, data, **metadata):
                    return {"success": True, "data": data, **metadata}
                
                def format_error(self, error, **metadata):
                    return {"success": False, "error": error, **metadata}
            
            # Test 1: Engine creation and configuration
            try:
                config = ExecutionConfiguration(max_concurrent_executions=5)
                engine = ExecutionEngine(
                    MockConnectionManager(),
                    MockCacheManager(),
                    MockResponseFormatter(),
                    logging.getLogger("test"),
                    config
                )
                
                creation_works = engine.config.max_concurrent_executions == 5
                tests.append(("Engine Creation", creation_works, "Engine created with config"))
            except Exception as e:
                tests.append(("Engine Creation", False, f"Creation error: {e}"))
            
            # Test 2: Index management
            try:
                engine = ExecutionEngine(
                    MockConnectionManager(),
                    MockCacheManager(),
                    MockResponseFormatter(),
                    logging.getLogger("test")
                )
                
                mock_server = MockServer()
                engine.update_indexes("test_server", mock_server)
                
                index_works = (
                    "test_tool" in engine.tool_index and
                    "test://resource" in engine.resource_index
                )
                tests.append(("Index Management", index_works, "Indexes updated correctly"))
            except Exception as e:
                tests.append(("Index Management", False, f"Index error: {e}"))
            
            # Test 3: Tool execution
            try:
                engine = ExecutionEngine(
                    MockConnectionManager(),
                    MockCacheManager(),
                    MockResponseFormatter(),
                    logging.getLogger("test")
                )
                
                mock_server = MockServer()
                engine.update_indexes("test_server", mock_server)
                
                result = await engine.execute_tool("test_tool", {"param": "value"})
                
                execution_works = result.success
                tests.append(("Tool Execution", execution_works, "Tool executed successfully"))
            except Exception as e:
                tests.append(("Tool Execution", False, f"Execution error: {e}"))
            
            # Test 4: Background tasks
            try:
                engine = ExecutionEngine(
                    MockConnectionManager(),
                    MockCacheManager(),
                    MockResponseFormatter(),
                    logging.getLogger("test")
                )
                
                await engine.start_background_tasks()
                background_started = engine.is_running
                
                await engine.stop_background_tasks()
                background_stopped = not engine.is_running
                
                background_works = background_started and background_stopped
                tests.append(("Background Tasks", background_works, "Background tasks lifecycle works"))
            except Exception as e:
                tests.append(("Background Tasks", False, f"Background error: {e}"))
            
            # Test 5: Metrics collection
            try:
                engine = ExecutionEngine(
                    MockConnectionManager(),
                    MockCacheManager(),
                    MockResponseFormatter(),
                    logging.getLogger("test")
                )
                
                metrics = engine.get_execution_metrics()
                ui_metrics = engine.get_ui_metrics()
                
                metrics_works = (
                    "execution_stats" in metrics and
                    "performance" in ui_metrics
                )
                tests.append(("Metrics Collection", metrics_works, "Metrics collection works"))
            except Exception as e:
                tests.append(("Metrics Collection", False, f"Metrics error: {e}"))
            
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
    print("🏃 Running Enterprise Execution Engine Tests")
    print("=" * 80)
    
    # Configure logging for tests
    logging.basicConfig(
        level=logging.WARNING,
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
    
    # Final summary
    print("\n" + "=" * 80)
    print("🏁 Enterprise Execution Engine Test Summary")
    print("=" * 80)
    print(f"Static Tests: {'✅ PASSED' if static_passed else '❌ FAILED'}")
    print(f"Dynamic Tests: {'✅ PASSED' if dynamic_passed else '❌ FAILED'}")
    print(f"Overall Status: {'✅ SUCCESS' if static_passed and dynamic_passed else '❌ FAILURE'}")
    
    if static_passed and dynamic_passed:
        print("\n🎨 Electron Integration Features:")
        print("  • Real-time execution metrics via engine.get_ui_metrics()")
        print("  • Event-driven updates via engine.on('event', handler)")
        print("  • Server performance monitoring")
        print("  • Security status tracking")
        print("  • Circuit breaker status monitoring")
    
    exit_code = 0 if (static_passed and dynamic_passed) else 1
    print(f"\nExit Code: {exit_code}")
    print("Run with: python -m src.mcp.core.client.execution_engine")