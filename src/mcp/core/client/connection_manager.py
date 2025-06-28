"""
MCP Client Connection Manager - Scalable & Secure

Handles server connections, health monitoring, connection lifecycle, and security.
Designed for scalability, security, and Electron UI/UX compatibility.
"""

import asyncio
import logging
import json
import time
import threading
import ssl
from typing import Any, Dict, List, Optional, Callable, Union, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import uuid
import hashlib
import weakref


class ConnectionStatus(Enum):
    """Connection status enumeration with detailed states"""
    INITIALIZING = "initializing"
    CONNECTING = "connecting" 
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    TIMEOUT = "timeout"
    AUTHENTICATION_FAILED = "authentication_failed"
    RATE_LIMITED = "rate_limited"
    MAINTENANCE = "maintenance"


class ConnectionPriority(Enum):
    """Connection priority levels for resource allocation"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ConnectionMetrics:
    """Comprehensive connection metrics for monitoring"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    average_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    connection_established_at: Optional[datetime] = None
    total_disconnections: int = 0
    total_reconnections: int = 0
    last_error: Optional[str] = None
    error_count: int = 0
    uptime_seconds: float = 0.0
    
    def update_request_metrics(self, success: bool, response_time: float, bytes_sent: int = 0, bytes_received: int = 0):
        """Update request metrics"""
        self.total_requests += 1
        self.bytes_sent += bytes_sent
        self.bytes_received += bytes_received
        self.last_request_time = datetime.now()
        
        if success:
            self.successful_requests += 1
            # Update rolling average response time
            if self.average_response_time == 0:
                self.average_response_time = response_time
            else:
                self.average_response_time = (self.average_response_time * 0.9) + (response_time * 0.1)
        else:
            self.failed_requests += 1
            self.error_count += 1
    
    def get_success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    def get_uptime(self) -> float:
        """Calculate uptime in seconds"""
        if self.connection_established_at:
            return (datetime.now() - self.connection_established_at).total_seconds()
        return 0.0


@dataclass
class SecurityPolicy:
    """Security policy for connections"""
    require_encryption: bool = True
    allowed_protocols: Set[str] = field(default_factory=lambda: {"https", "wss", "mqtts"})
    max_connection_attempts: int = 3
    connection_timeout: int = 30
    idle_timeout: int = 300
    rate_limit_requests_per_minute: int = 60
    require_authentication: bool = True
    allowed_origins: Set[str] = field(default_factory=set)
    blocked_ips: Set[str] = field(default_factory=set)
    enable_certificate_validation: bool = True
    
    def validate_connection_request(self, server_info: Dict[str, Any]) -> tuple[bool, str]:
        """Validate if connection is allowed by security policy"""
        # Check protocol
        protocol = server_info.get("protocol", "").lower()
        if protocol and protocol not in self.allowed_protocols:
            return False, f"Protocol '{protocol}' not allowed"
        
        # Check origin if specified
        origin = server_info.get("origin", "")
        if self.allowed_origins and origin not in self.allowed_origins:
            return False, f"Origin '{origin}' not in allowed list"
        
        # Check blocked IPs
        ip = server_info.get("ip", "")
        if ip in self.blocked_ips:
            return False, f"IP '{ip}' is blocked"
        
        return True, "Connection allowed"


@dataclass
class ConnectionConfiguration:
    """Configuration for individual connections"""
    name: str
    priority: ConnectionPriority = ConnectionPriority.NORMAL
    max_reconnect_attempts: int = 3
    reconnect_delay: float = 1.0
    reconnect_backoff_multiplier: float = 2.0
    max_reconnect_delay: float = 60.0
    health_check_interval: float = 30.0
    request_timeout: float = 30.0
    enable_auto_reconnect: bool = True
    connection_metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        """Validate configuration"""
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Connection name must be a non-empty string")
        if self.max_reconnect_attempts < 0:
            raise ValueError("max_reconnect_attempts must be non-negative")
        if self.reconnect_delay < 0:
            raise ValueError("reconnect_delay must be non-negative")


class ServerConnection:
    """Enhanced server connection with comprehensive monitoring and security"""
    
    def __init__(self, 
                 server: Any,
                 config: ConnectionConfiguration,
                 security_policy: SecurityPolicy,
                 logger: logging.Logger):
        """
        Initialize server connection.
        
        Args:
            server: MCP server instance
            config: Connection configuration
            security_policy: Security policy to enforce
            logger: Logger instance
        """
        self.server = server
        self.config = config
        self.security_policy = security_policy
        self.logger = logger
        
        # Connection state
        self.connection_id = str(uuid.uuid4())
        self.status = ConnectionStatus.INITIALIZING
        self.status_lock = threading.Lock()
        
        # Timestamps
        self.created_at = datetime.now()
        self.connected_at: Optional[datetime] = None
        self.last_ping: Optional[datetime] = None
        self.last_activity: Optional[datetime] = None
        
        # Reconnection state
        self.reconnect_attempts = 0
        self.next_reconnect_delay = config.reconnect_delay
        
        # Capabilities and metadata
        self.capabilities: Dict[str, Any] = {}
        self.server_info: Dict[str, Any] = {}
        
        # Metrics and monitoring
        self.metrics = ConnectionMetrics()
        
        # Rate limiting
        self.request_timestamps: List[float] = []
        
        # Event callbacks
        self.event_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        # Health check task
        self.health_check_task: Optional[asyncio.Task] = None
        
        self.logger.info(f"Created connection: {self.config.name} [{self.connection_id}]")
    
    def _set_status(self, new_status: ConnectionStatus, error_message: str = None):
        """Thread-safe status setting with event emission"""
        with self.status_lock:
            old_status = self.status
            self.status = new_status
            
            # Update metrics
            if new_status == ConnectionStatus.CONNECTED:
                self.connected_at = datetime.now()
                self.metrics.connection_established_at = self.connected_at
                self.reconnect_attempts = 0
                self.next_reconnect_delay = self.config.reconnect_delay
            elif new_status == ConnectionStatus.DISCONNECTED:
                self.metrics.total_disconnections += 1
            elif new_status in [ConnectionStatus.ERROR, ConnectionStatus.TIMEOUT]:
                if error_message:
                    self.metrics.last_error = error_message
                self.metrics.error_count += 1
            
            self.logger.debug(f"Connection {self.config.name} status: {old_status.value} -> {new_status.value}")
            
            # Emit status change event
            self._emit_event("status_changed", {
                "connection_id": self.connection_id,
                "connection_name": self.config.name,
                "old_status": old_status.value,
                "new_status": new_status.value,
                "error_message": error_message,
                "timestamp": datetime.now().isoformat()
            })
    
    def _emit_event(self, event_name: str, data: Any):
        """Emit event to registered callbacks"""
        if event_name in self.event_callbacks:
            for callback in self.event_callbacks[event_name]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(data))
                    else:
                        callback(data)
                except Exception as e:
                    self.logger.error(f"Error in event callback {event_name}: {e}")
    
    def on(self, event_name: str, callback: Callable):
        """Register event callback"""
        self.event_callbacks[event_name].append(callback)
    
    def _check_rate_limit(self) -> bool:
        """Check if request is within rate limits"""
        current_time = time.time()
        
        # Clean old timestamps (older than 1 minute)
        self.request_timestamps = [
            ts for ts in self.request_timestamps
            if current_time - ts < 60
        ]
        
        # Check limit
        if len(self.request_timestamps) >= self.security_policy.rate_limit_requests_per_minute:
            return False
        
        # Record request
        self.request_timestamps.append(current_time)
        return True
    
    async def connect(self) -> bool:
        """Connect to the server with security validation"""
        try:
            self._set_status(ConnectionStatus.CONNECTING)
            
            # Validate security policy
            server_info = getattr(self.server, 'get_server_info', lambda: {})()
            allowed, reason = self.security_policy.validate_connection_request(server_info)
            if not allowed:
                self._set_status(ConnectionStatus.ERROR, f"Security policy violation: {reason}")
                return False
            
            # Attempt connection with timeout
            try:
                await asyncio.wait_for(
                    self.server.initialize(),
                    timeout=self.security_policy.connection_timeout
                )
            except asyncio.TimeoutError:
                self._set_status(ConnectionStatus.TIMEOUT, "Connection timeout")
                return False
            
            # Get capabilities
            self.capabilities = self.server.get_capabilities()
            self.server_info = server_info
            
            # Validate capabilities if required
            if self.security_policy.require_authentication:
                if not self.capabilities.get("authentication_supported", False):
                    self._set_status(ConnectionStatus.AUTHENTICATION_FAILED, "Authentication required but not supported")
                    return False
            
            self._set_status(ConnectionStatus.CONNECTED)
            self.last_activity = datetime.now()
            
            # Start health checking
            if self.config.health_check_interval > 0:
                self.health_check_task = asyncio.create_task(self._health_check_loop())
            
            self.logger.info(f"Successfully connected to {self.config.name}")
            return True
            
        except Exception as e:
            self._set_status(ConnectionStatus.ERROR, str(e))
            self.logger.error(f"Failed to connect to {self.config.name}: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from the server"""
        try:
            self._set_status(ConnectionStatus.DISCONNECTING)
            
            # Cancel health check
            if self.health_check_task and not self.health_check_task.done():
                self.health_check_task.cancel()
                try:
                    await self.health_check_task
                except asyncio.CancelledError:
                    pass
            
            # Call server cleanup
            if hasattr(self.server, 'cleanup'):
                await self.server.cleanup()
            
            self._set_status(ConnectionStatus.DISCONNECTED)
            self.logger.info(f"Disconnected from {self.config.name}")
            return True
            
        except Exception as e:
            self._set_status(ConnectionStatus.ERROR, str(e))
            self.logger.error(f"Error disconnecting from {self.config.name}: {e}")
            return False
    
    async def execute_request(self, request_type: str, *args, **kwargs) -> Any:
        """Execute a request with monitoring and rate limiting"""
        # Check rate limiting
        if not self._check_rate_limit():
            self._set_status(ConnectionStatus.RATE_LIMITED, "Rate limit exceeded")
            raise ConnectionError("Rate limit exceeded")
        
        # Check connection status
        if self.status != ConnectionStatus.CONNECTED:
            raise ConnectionError(f"Connection not available: {self.status.value}")
        
        start_time = time.time()
        try:
            # Execute request with timeout
            result = await asyncio.wait_for(
                getattr(self.server, request_type)(*args, **kwargs),
                timeout=self.config.request_timeout
            )
            
            # Update metrics
            response_time = time.time() - start_time
            self.metrics.update_request_metrics(True, response_time)
            self.last_activity = datetime.now()
            
            return result
            
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            self.metrics.update_request_metrics(False, response_time)
            self._set_status(ConnectionStatus.TIMEOUT, f"Request timeout: {request_type}")
            raise
        except Exception as e:
            response_time = time.time() - start_time
            self.metrics.update_request_metrics(False, response_time)
            self.logger.error(f"Request failed on {self.config.name}: {e}")
            raise
    
    async def _health_check_loop(self):
        """Background health check loop"""
        while self.status == ConnectionStatus.CONNECTED:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                if self.status != ConnectionStatus.CONNECTED:
                    break
                
                # Perform health check
                try:
                    await asyncio.wait_for(
                        self.server.get_capabilities(),
                        timeout=10.0
                    )
                    self.last_ping = datetime.now()
                    
                except Exception as e:
                    self.logger.warning(f"Health check failed for {self.config.name}: {e}")
                    self._set_status(ConnectionStatus.ERROR, f"Health check failed: {e}")
                    break
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check loop for {self.config.name}: {e}")
                break
    
    async def attempt_reconnect(self) -> bool:
        """Attempt to reconnect with exponential backoff"""
        if not self.config.enable_auto_reconnect:
            return False
        
        if self.reconnect_attempts >= self.config.max_reconnect_attempts:
            self.logger.error(f"Max reconnection attempts reached for {self.config.name}")
            return False
        
        self.reconnect_attempts += 1
        self._set_status(ConnectionStatus.RECONNECTING)
        
        # Wait with exponential backoff
        await asyncio.sleep(self.next_reconnect_delay)
        self.next_reconnect_delay = min(
            self.next_reconnect_delay * self.config.reconnect_backoff_multiplier,
            self.config.max_reconnect_delay
        )
        
        self.logger.info(f"Attempting reconnection {self.reconnect_attempts}/{self.config.max_reconnect_attempts} for {self.config.name}")
        
        success = await self.connect()
        if success:
            self.metrics.total_reconnections += 1
        
        return success
    
    @property
    def is_healthy(self) -> bool:
        """Check if connection is healthy"""
        if self.status != ConnectionStatus.CONNECTED:
            return False
        
        # Check if connection is too old without activity
        if self.last_activity:
            idle_time = (datetime.now() - self.last_activity).total_seconds()
            if idle_time > self.security_policy.idle_timeout:
                return False
        
        # Check error rate
        success_rate = self.metrics.get_success_rate()
        if self.metrics.total_requests > 10 and success_rate < 50:
            return False
        
        return True
    
    @property
    def needs_reconnect(self) -> bool:
        """Check if connection needs reconnection"""
        return (
            self.status in [ConnectionStatus.ERROR, ConnectionStatus.TIMEOUT] and
            self.config.enable_auto_reconnect and
            self.reconnect_attempts < self.config.max_reconnect_attempts
        )
    
    def get_status_info(self) -> Dict[str, Any]:
        """Get comprehensive status information for UI"""
        return {
            "connection_id": self.connection_id,
            "name": self.config.name,
            "status": self.status.value,
            "priority": self.config.priority.value,
            "created_at": self.created_at.isoformat(),
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "last_ping": self.last_ping.isoformat() if self.last_ping else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "is_healthy": self.is_healthy,
            "needs_reconnect": self.needs_reconnect,
            "reconnect_attempts": self.reconnect_attempts,
            "max_reconnect_attempts": self.config.max_reconnect_attempts,
            "capabilities": list(self.capabilities.keys()) if self.capabilities else [],
            "server_info": self.server_info,
            "tags": list(self.config.tags),
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "successful_requests": self.metrics.successful_requests,
                "failed_requests": self.metrics.failed_requests,
                "success_rate": self.metrics.get_success_rate(),
                "average_response_time": self.metrics.average_response_time,
                "uptime_seconds": self.metrics.get_uptime(),
                "bytes_sent": self.metrics.bytes_sent,
                "bytes_received": self.metrics.bytes_received,
                "error_count": self.metrics.error_count,
                "last_error": self.metrics.last_error
            }
        }


class ConnectionManager:
    """
    Scalable and secure connection manager for MCP servers.
    
    Features:
    - Connection pooling and lifecycle management
    - Security policies and validation
    - Health monitoring and auto-reconnection
    - Performance metrics and monitoring
    - Event-driven architecture for UI integration
    - Thread-safe operations
    - Priority-based connection management
    """
    
    def __init__(self, 
                 logger: logging.Logger,
                 security_policy: Optional[SecurityPolicy] = None,
                 max_connections: int = 50,
                 default_health_check_interval: float = 30.0):
        """
        Initialize connection manager.
        
        Args:
            logger: Logger instance
            security_policy: Security policy for connections
            max_connections: Maximum number of concurrent connections
            default_health_check_interval: Default health check interval
        """
        self.logger = logger
        self.security_policy = security_policy or SecurityPolicy()
        self.max_connections = max_connections
        self.default_health_check_interval = default_health_check_interval
        
        # Connection storage
        self.connections: Dict[str, ServerConnection] = {}
        self.connections_lock = threading.RLock()
        
        # Connection pools by priority
        self.connection_pools: Dict[ConnectionPriority, Set[str]] = {
            priority: set() for priority in ConnectionPriority
        }
        
        # Background tasks
        self.background_tasks: Set[asyncio.Task] = set()
        self.is_running = False
        
        # Event system
        self.event_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        # Metrics
        self.manager_metrics = {
            "total_connections_created": 0,
            "total_connections_destroyed": 0,
            "total_reconnection_attempts": 0,
            "successful_reconnections": 0,
            "failed_reconnections": 0
        }
        
        self.logger.info(f"Connection manager initialized - max_connections: {max_connections}")
    
    def on(self, event_name: str, callback: Callable):
        """Register event callback"""
        self.event_callbacks[event_name].append(callback)
    
    def _emit_event(self, event_name: str, data: Any):
        """Emit event to registered callbacks"""
        if event_name in self.event_callbacks:
            for callback in self.event_callbacks[event_name]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(data))
                    else:
                        callback(data)
                except Exception as e:
                    self.logger.error(f"Error in event callback {event_name}: {e}")
    
    async def start(self):
        """Start the connection manager"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start background monitoring task
        monitor_task = asyncio.create_task(self._background_monitor())
        self.background_tasks.add(monitor_task)
        monitor_task.add_done_callback(self.background_tasks.discard)
        
        self.logger.info("Connection manager started")
        self._emit_event("manager_started", {"timestamp": datetime.now().isoformat()})
    
    async def stop(self):
        """Stop the connection manager and cleanup all connections"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.logger.info("Stopping connection manager...")
        
        # Cancel background tasks
        for task in self.background_tasks.copy():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Disconnect all connections
        with self.connections_lock:
            disconnect_tasks = []
            for connection in self.connections.values():
                disconnect_tasks.append(connection.disconnect())
            
            if disconnect_tasks:
                await asyncio.gather(*disconnect_tasks, return_exceptions=True)
            
            self.connections.clear()
            for pool in self.connection_pools.values():
                pool.clear()
        
        self.logger.info("Connection manager stopped")
        self._emit_event("manager_stopped", {"timestamp": datetime.now().isoformat()})
    
    async def connect_server(self, 
                           server: Any, 
                           name: str,
                           priority: ConnectionPriority = ConnectionPriority.NORMAL,
                           **config_kwargs) -> bool:
        """
        Connect to an MCP server with enhanced configuration.
        
        Args:
            server: MCP server instance
            name: Unique connection name
            priority: Connection priority level
            **config_kwargs: Additional configuration options
            
        Returns:
            True if connection successful, False otherwise
        """
        # Check connection limits
        with self.connections_lock:
            if len(self.connections) >= self.max_connections:
                self.logger.error(f"Cannot connect to {name}: Connection limit reached ({self.max_connections})")
                return False
            
            if name in self.connections:
                self.logger.warning(f"Connection {name} already exists")
                return False
        
        try:
            # Create connection configuration
            config = ConnectionConfiguration(
                name=name,
                priority=priority,
                health_check_interval=self.default_health_check_interval,
                **config_kwargs
            )
            
            # Create connection
            connection = ServerConnection(
                server=server,
                config=config,
                security_policy=self.security_policy,
                logger=self.logger
            )
            
            # Register for connection events
            connection.on("status_changed", self._on_connection_status_changed)
            
            # Attempt connection
            success = await connection.connect()
            
            if success:
                with self.connections_lock:
                    self.connections[name] = connection
                    self.connection_pools[priority].add(name)
                
                self.manager_metrics["total_connections_created"] += 1
                
                self.logger.info(f"Successfully connected to server: {name}")
                self._emit_event("server_connected", {
                    "connection_name": name,
                    "priority": priority.value,
                    "connection_id": connection.connection_id
                })
            else:
                self.logger.error(f"Failed to connect to server: {name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error connecting to server {name}: {e}")
            return False
    
    async def disconnect_server(self, name: str) -> bool:
        """
        Disconnect from an MCP server.
        
        Args:
            name: Connection name
            
        Returns:
            True if disconnection successful, False otherwise
        """
        with self.connections_lock:
            connection = self.connections.get(name)
            if not connection:
                self.logger.warning(f"Cannot disconnect from unknown connection: {name}")
                return False
        
        try:
            success = await connection.disconnect()
            
            if success:
                with self.connections_lock:
                    del self.connections[name]
                    # Remove from all pools
                    for pool in self.connection_pools.values():
                        pool.discard(name)
                
                self.manager_metrics["total_connections_destroyed"] += 1
                
                self.logger.info(f"Successfully disconnected from server: {name}")
                self._emit_event("server_disconnected", {
                    "connection_name": name,
                    "connection_id": connection.connection_id
                })
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from server {name}: {e}")
            return False
    
    def get_connection(self, name: str) -> Optional[ServerConnection]:
        """Get connection by name (thread-safe)"""
        with self.connections_lock:
            return self.connections.get(name)
    
    def get_connections_by_priority(self, priority: ConnectionPriority) -> List[ServerConnection]:
        """Get all connections of a specific priority"""
        with self.connections_lock:
            connection_names = self.connection_pools[priority].copy()
            return [self.connections[name] for name in connection_names if name in self.connections]
    
    def get_connected_servers(self) -> List[str]:
        """Get list of connected server names"""
        with self.connections_lock:
            return [
                name for name, conn in self.connections.items()
                if conn.status == ConnectionStatus.CONNECTED
            ]
    
    def get_healthy_servers(self) -> List[str]:
        """Get list of healthy server names"""
        with self.connections_lock:
            return [
                name for name, conn in self.connections.items()
                if conn.is_healthy
            ]
    
    def get_all_servers(self) -> List[str]:
        """Get list of all server names"""
        with self.connections_lock:
            return list(self.connections.keys())
    
    async def health_check(self, server_name: Optional[str] = None) -> Dict[str, bool]:
        """
        Perform health check on servers.
        
        Args:
            server_name: Specific server to check, or None for all servers
            
        Returns:
            Dict mapping server names to health status
        """
        results = {}
        
        with self.connections_lock:
            if server_name:
                connections_to_check = [server_name] if server_name in self.connections else []
            else:
                connections_to_check = list(self.connections.keys())
        
        for name in connections_to_check:
            connection = self.get_connection(name)
            if connection:
                results[name] = connection.is_healthy
            else:
                results[name] = False
        
        return results
    
    async def _background_monitor(self):
        """Background monitoring and maintenance task"""
        while self.is_running:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                if not self.is_running:
                    break
                
                # Check for connections needing reconnection
                reconnect_tasks = []
                
                with self.connections_lock:
                    for connection in self.connections.values():
                        if connection.needs_reconnect:
                            reconnect_tasks.append(self._attempt_reconnection(connection))
                
                # Attempt reconnections
                if reconnect_tasks:
                    await asyncio.gather(*reconnect_tasks, return_exceptions=True)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in background monitor: {e}")
    
    async def _attempt_reconnection(self, connection: ServerConnection):
        """Attempt to reconnect a connection"""
        try:
            self.manager_metrics["total_reconnection_attempts"] += 1
            
            success = await connection.attempt_reconnect()
            
            if success:
                self.manager_metrics["successful_reconnections"] += 1
                self.logger.info(f"Successfully reconnected to {connection.config.name}")
            else:
                self.manager_metrics["failed_reconnections"] += 1
                self.logger.warning(f"Failed to reconnect to {connection.config.name}")
            
        except Exception as e:
            self.manager_metrics["failed_reconnections"] += 1
            self.logger.error(f"Error attempting reconnection for {connection.config.name}: {e}")
    
    def _on_connection_status_changed(self, event_data: Dict[str, Any]):
        """Handle connection status change events"""
        self._emit_event("connection_status_changed", event_data)
        
        # Log important status changes
        connection_name = event_data.get("connection_name")
        new_status = event_data.get("new_status")
        
        if new_status in ["error", "timeout", "authentication_failed"]:
            self.logger.warning(f"Connection {connection_name} status changed to {new_status}")
        elif new_status == "connected":
            self.logger.info(f"Connection {connection_name} established successfully")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get comprehensive connection statistics"""
        with self.connections_lock:
            total_connections = len(self.connections)
            connected_count = len(self.get_connected_servers())
            healthy_count = len(self.get_healthy_servers())
            
            # Count by priority
            priority_counts = {}
            for priority in ConnectionPriority:
                priority_counts[priority.name.lower()] = len(self.connection_pools[priority])
            
            # Count by status
            status_counts = defaultdict(int)
            for connection in self.connections.values():
                status_counts[connection.status.value] += 1
            
            return {
                "total_connections": total_connections,
                "connected": connected_count,
                "healthy": healthy_count,
                "unhealthy": total_connections - healthy_count,
                "by_priority": priority_counts,
                "by_status": dict(status_counts),
                "manager_running": self.is_running,
                "max_connections": self.max_connections,
                "connection_utilization": (total_connections / self.max_connections) * 100,
                "manager_metrics": self.manager_metrics.copy()
            }
    
    def get_connection_details(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed information about all connections"""
        with self.connections_lock:
            return {
                name: connection.get_status_info()
                for name, connection in self.connections.items()
            }
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get security-related status information"""
        return {
            "security_policy": {
                "require_encryption": self.security_policy.require_encryption,
                "allowed_protocols": list(self.security_policy.allowed_protocols),
                "max_connection_attempts": self.security_policy.max_connection_attempts,
                "connection_timeout": self.security_policy.connection_timeout,
                "rate_limit_per_minute": self.security_policy.rate_limit_requests_per_minute,
                "require_authentication": self.security_policy.require_authentication,
                "certificate_validation": self.security_policy.enable_certificate_validation,
                "allowed_origins_count": len(self.security_policy.allowed_origins),
                "blocked_ips_count": len(self.security_policy.blocked_ips)
            },
            "active_security_violations": self._get_security_violations()
        }
    
    def _get_security_violations(self) -> List[Dict[str, Any]]:
        """Get current security violations"""
        violations = []
        
        with self.connections_lock:
            for connection in self.connections.values():
                if connection.status == ConnectionStatus.RATE_LIMITED:
                    violations.append({
                        "type": "rate_limit_exceeded",
                        "connection_name": connection.config.name,
                        "timestamp": datetime.now().isoformat()
                    })
                elif connection.status == ConnectionStatus.AUTHENTICATION_FAILED:
                    violations.append({
                        "type": "authentication_failed",
                        "connection_name": connection.config.name,
                        "timestamp": datetime.now().isoformat()
                    })
        
        return violations
    
    def update_security_policy(self, policy_updates: Dict[str, Any]):
        """Update security policy settings"""
        for key, value in policy_updates.items():
            if hasattr(self.security_policy, key):
                setattr(self.security_policy, key, value)
                self.logger.info(f"Updated security policy: {key} = {value}")
        
        self._emit_event("security_policy_updated", {
            "updates": policy_updates,
            "timestamp": datetime.now().isoformat()
        })
    
    def block_ip(self, ip_address: str):
        """Block an IP address"""
        self.security_policy.blocked_ips.add(ip_address)
        self.logger.warning(f"Blocked IP address: {ip_address}")
        self._emit_event("ip_blocked", {"ip": ip_address})
    
    def unblock_ip(self, ip_address: str):
        """Unblock an IP address"""
        self.security_policy.blocked_ips.discard(ip_address)
        self.logger.info(f"Unblocked IP address: {ip_address}")
        self._emit_event("ip_unblocked", {"ip": ip_address})
    
    def add_allowed_origin(self, origin: str):
        """Add an allowed origin"""
        self.security_policy.allowed_origins.add(origin)
        self.logger.info(f"Added allowed origin: {origin}")
        self._emit_event("origin_allowed", {"origin": origin})
    
    def remove_allowed_origin(self, origin: str):
        """Remove an allowed origin"""
        self.security_policy.allowed_origins.discard(origin)
        self.logger.info(f"Removed allowed origin: {origin}")
        self._emit_event("origin_removed", {"origin": origin})
    
    async def execute_on_connection(self, 
                                  connection_name: str, 
                                  request_type: str, 
                                  *args, 
                                  **kwargs) -> Any:
        """Execute a request on a specific connection with monitoring"""
        connection = self.get_connection(connection_name)
        if not connection:
            raise ConnectionError(f"Connection '{connection_name}' not found")
        
        return await connection.execute_request(request_type, *args, **kwargs)
    
    async def execute_on_priority_group(self, 
                                      priority: ConnectionPriority,
                                      request_type: str,
                                      *args,
                                      **kwargs) -> Dict[str, Any]:
        """Execute a request on all connections of a specific priority"""
        connections = self.get_connections_by_priority(priority)
        
        if not connections:
            return {}
        
        # Execute on all connections concurrently
        tasks = []
        connection_names = []
        
        for connection in connections:
            if connection.is_healthy:
                tasks.append(connection.execute_request(request_type, *args, **kwargs))
                connection_names.append(connection.config.name)
        
        if not tasks:
            return {}
        
        # Wait for all results
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        combined_results = {}
        for name, result in zip(connection_names, results):
            if isinstance(result, Exception):
                combined_results[name] = {"error": str(result)}
            else:
                combined_results[name] = {"result": result}
        
        return combined_results
    
    def get_ui_status(self) -> Dict[str, Any]:
        """Get status information optimized for UI consumption"""
        stats = self.get_connection_stats()
        details = self.get_connection_details()
        security = self.get_security_status()
        
        # Simplify for UI
        ui_connections = []
        for name, detail in details.items():
            ui_connections.append({
                "name": name,
                "status": detail["status"],
                "priority": detail["priority"],
                "is_healthy": detail["is_healthy"],
                "success_rate": detail["metrics"]["success_rate"],
                "uptime": detail["metrics"]["uptime_seconds"],
                "last_activity": detail["last_activity"],
                "error_count": detail["metrics"]["error_count"]
            })
        
        return {
            "summary": {
                "total": stats["total_connections"],
                "connected": stats["connected"],
                "healthy": stats["healthy"],
                "utilization": stats["connection_utilization"]
            },
            "connections": ui_connections,
            "security_status": {
                "violations_count": len(security["active_security_violations"]),
                "policy_active": True,
                "blocked_ips": security["security_policy"]["blocked_ips_count"]
            },
            "last_updated": datetime.now().isoformat()
        }


def main():
    """
    Main function demonstrating Connection Manager usage with security and scalability.
    """
    print("🚀 Connection Manager - Scalable & Secure")
    print("=" * 50)
    
    async def demo_connection_manager():
        """Demonstrate connection manager capabilities"""
        
        # Create security policy
        security_policy = SecurityPolicy(
            require_encryption=True,
            allowed_protocols={"https", "wss"},
            max_connection_attempts=3,
            rate_limit_requests_per_minute=100,
            require_authentication=False  # For demo
        )
        
        # Create connection manager
        logger = logging.getLogger("demo_connection_manager")
        manager = ConnectionManager(
            logger=logger,
            security_policy=security_policy,
            max_connections=20
        )
        
        print(f"✅ Connection Manager created")
        print(f"   Max connections: {manager.max_connections}")
        print(f"   Security enabled: {security_policy.require_encryption}")
        
        # Start manager
        await manager.start()
        print(f"   Status: {'🟢 RUNNING' if manager.is_running else '🔴 STOPPED'}")
        
        # Mock server for demonstration
        class MockServer:
            def __init__(self, name: str):
                self.name = name
                self.initialized = False
            
            async def initialize(self):
                await asyncio.sleep(0.1)  # Simulate connection time
                self.initialized = True
            
            def get_capabilities(self):
                return {
                    "tools": [f"tool_{self.name}_1", f"tool_{self.name}_2"],
                    "resources": [f"resource_{self.name}"],
                    "authentication_supported": False
                }
            
            def get_server_info(self):
                return {
                    "protocol": "https",
                    "origin": "localhost",
                    "version": "1.0.0"
                }
            
            async def cleanup(self):
                self.initialized = False
        
        # Test connections with different priorities
        servers_to_connect = [
            ("critical_server", ConnectionPriority.CRITICAL),
            ("high_priority_server", ConnectionPriority.HIGH),
            ("normal_server", ConnectionPriority.NORMAL),
            ("low_priority_server", ConnectionPriority.LOW)
        ]
        
        # Connect servers
        for server_name, priority in servers_to_connect:
            mock_server = MockServer(server_name)
            success = await manager.connect_server(
                mock_server, 
                server_name,
                priority=priority,
                enable_auto_reconnect=True,
                health_check_interval=5.0
            )
            status = "✅ CONNECTED" if success else "❌ FAILED"
            print(f"   {server_name}: {status} (Priority: {priority.name})")
        
        # Display status
        print(f"\n📊 Connection Status:")
        stats = manager.get_connection_stats()
        print(f"   Total: {stats['total_connections']}")
        print(f"   Connected: {stats['connected']}")
        print(f"   Healthy: {stats['healthy']}")
        print(f"   Utilization: {stats['connection_utilization']:.1f}%")
        
        # Display priority distribution
        print(f"\n🏷️ Priority Distribution:")
        for priority, count in stats['by_priority'].items():
            print(f"   {priority.upper()}: {count}")
        
        # Display security status
        print(f"\n🔒 Security Status:")
        security_status = manager.get_security_status()
        policy = security_status['security_policy']
        print(f"   Encryption Required: {policy['require_encryption']}")
        print(f"   Rate Limit: {policy['rate_limit_per_minute']}/min")
        print(f"   Blocked IPs: {policy['blocked_ips_count']}")
        print(f"   Security Violations: {len(security_status['active_security_violations'])}")
        
        # Test health check
        print(f"\n🏥 Health Check:")
        health_results = await manager.health_check()
        for server_name, is_healthy in health_results.items():
            status = "🟢 HEALTHY" if is_healthy else "🔴 UNHEALTHY"
            print(f"   {server_name}: {status}")
        
        # Test priority-based operations
        print(f"\n⚡ Priority-based Operations:")
        try:
            # Execute on critical priority connections
            critical_results = await manager.execute_on_priority_group(
                ConnectionPriority.CRITICAL,
                "get_capabilities"
            )
            print(f"   Critical servers responded: {len(critical_results)}")
        except Exception as e:
            print(f"   Critical operation failed: {e}")
        
        # Test UI status
        print(f"\n🎨 UI Status Summary:")
        ui_status = manager.get_ui_status()
        summary = ui_status['summary']
        print(f"   {summary['connected']}/{summary['total']} connected ({summary['utilization']:.1f}% capacity)")
        print(f"   Security violations: {ui_status['security_status']['violations_count']}")
        
        # Demonstrate security features
        print(f"\n🛡️ Security Features:")
        
        # Block an IP (demonstration)
        manager.block_ip("192.168.1.100")
        print(f"   Blocked IP: 192.168.1.100")
        
        # Add allowed origin
        manager.add_allowed_origin("trusted-domain.com")
        print(f"   Added allowed origin: trusted-domain.com")
        
        # Show updated security status
        updated_security = manager.get_security_status()
        policy = updated_security['security_policy']
        print(f"   Updated blocked IPs: {policy['blocked_ips_count']}")
        print(f"   Updated allowed origins: {policy['allowed_origins_count']}")
        
        # Cleanup
        print(f"\n🧹 Cleanup:")
        await manager.stop()
        print(f"   Manager stopped: {'✅ SUCCESS' if not manager.is_running else '❌ FAILED'}")
        
        return manager
    
    # Run demonstration
    try:
        manager = asyncio.run(demo_connection_manager())
        print("\n🎉 Demo completed successfully!")
        return manager
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        return None


if __name__ == "__main__":
    """
    Main execution block for testing the ConnectionManager locally.
    """
    def run_static_tests():
        """Run static tests for ConnectionManager"""
        print("🧪 Running Static Tests...")
        
        tests = []
        
        # Test 1: Security Policy creation and validation
        try:
            policy = SecurityPolicy(
                require_encryption=True,
                allowed_protocols={"https", "wss"},
                rate_limit_requests_per_minute=60
            )
            
            # Test validation
            allowed, reason = policy.validate_connection_request({
                "protocol": "https",
                "origin": "localhost"
            })
            
            tests.append(("Security Policy", allowed, "Security policy validation works"))
        except Exception as e:
            tests.append(("Security Policy", False, f"Security error: {e}"))
        
        # Test 2: Connection Configuration validation
        try:
            # Valid config
            config = ConnectionConfiguration(
                name="test_connection",
                priority=ConnectionPriority.HIGH,
                max_reconnect_attempts=5
            )
            
            # Invalid config (should raise exception)
            try:
                ConnectionConfiguration(name="", max_reconnect_attempts=-1)
                tests.append(("Config Validation", False, "Should have rejected invalid config"))
            except ValueError:
                tests.append(("Config Validation", True, "Properly rejected invalid config"))
        except Exception as e:
            tests.append(("Config Validation", False, f"Config error: {e}"))
        
        # Test 3: ConnectionMetrics
        try:
            metrics = ConnectionMetrics()
            metrics.update_request_metrics(True, 0.5, 100, 200)
            
            success_rate = metrics.get_success_rate()
            is_valid = (
                metrics.total_requests == 1 and
                metrics.successful_requests == 1 and
                success_rate == 100.0
            )
            
            tests.append(("Connection Metrics", is_valid, "Metrics tracking works"))
        except Exception as e:
            tests.append(("Connection Metrics", False, f"Metrics error: {e}"))
        
        # Test 4: ConnectionStatus enum
        try:
            status = ConnectionStatus.CONNECTED
            is_valid = status.value == "connected"
            
            # Test all status values
            all_statuses = [s.value for s in ConnectionStatus]
            has_expected = "connected" in all_statuses and "error" in all_statuses
            
            tests.append(("Connection Status", is_valid and has_expected, "Status enum works"))
        except Exception as e:
            tests.append(("Connection Status", False, f"Status error: {e}"))
        
        # Test 5: ConnectionPriority enum
        try:
            priority = ConnectionPriority.HIGH
            is_valid = priority.value == 3
            
            # Test priority ordering
            priorities = sorted([p.value for p in ConnectionPriority])
            correct_order = priorities == [1, 2, 3, 4]
            
            tests.append(("Connection Priority", is_valid and correct_order, "Priority enum works"))
        except Exception as e:
            tests.append(("Connection Priority", False, f"Priority error: {e}"))
        
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
        """Run dynamic tests for ConnectionManager"""
        print("\n⚡ Running Dynamic Tests...")
        
        async def async_test_suite():
            tests = []
            
            # Test 1: Connection Manager lifecycle
            try:
                logger = logging.getLogger("test_connection_manager")
                manager = ConnectionManager(logger, max_connections=5)
                
                # Start manager
                await manager.start()
                is_running = manager.is_running
                
                # Stop manager
                await manager.stop()
                is_stopped = not manager.is_running
                
                tests.append(("Manager Lifecycle", is_running and is_stopped, "Start/stop works"))
            except Exception as e:
                tests.append(("Manager Lifecycle", False, f"Lifecycle error: {e}"))
            
            # Test 2: Connection limits
            try:
                logger = logging.getLogger("test_limits")
                manager = ConnectionManager(logger, max_connections=2)
                await manager.start()
                
                # Mock server
                class MockServer:
                    async def initialize(self): pass
                    def get_capabilities(self): return {}
                    def get_server_info(self): return {"protocol": "https"}
                
                # Try to connect 3 servers (should allow only 2)
                servers = [MockServer() for _ in range(3)]
                results = []
                
                for i, server in enumerate(servers):
                    result = await manager.connect_server(server, f"server_{i}")
                    results.append(result)
                
                # Should have 2 successes and 1 failure
                successes = sum(results)
                connection_limit_works = successes == 2
                
                tests.append(("Connection Limits", connection_limit_works, f"Limited to 2/3 connections"))
                
                await manager.stop()
            except Exception as e:
                tests.append(("Connection Limits", False, f"Limits error: {e}"))
            
            # Test 3: Security policy enforcement
            try:
                security_policy = SecurityPolicy(
                    allowed_protocols={"https"},
                    blocked_ips={"192.168.1.100"}
                )
                
                logger = logging.getLogger("test_security")
                manager = ConnectionManager(logger, security_policy=security_policy)
                await manager.start()
                
                # Mock server with blocked protocol
                class BlockedServer:
                    async def initialize(self): pass
                    def get_capabilities(self): return {}
                    def get_server_info(self): return {"protocol": "http", "ip": "192.168.1.100"}
                
                blocked_server = BlockedServer()
                result = await manager.connect_server(blocked_server, "blocked_server")
                
                # Should be blocked by security policy
                security_works = not result
                
                tests.append(("Security Enforcement", security_works, "Blocked insecure connection"))
                
                await manager.stop()
            except Exception as e:
                tests.append(("Security Enforcement", False, f"Security error: {e}"))
            
            # Test 4: Priority-based connection management
            try:
                logger = logging.getLogger("test_priority")
                manager = ConnectionManager(logger)
                await manager.start()
                
                # Mock server
                class PriorityServer:
                    def __init__(self, name): self.name = name
                    async def initialize(self): pass
                    def get_capabilities(self): return {"server": self.name}
                    def get_server_info(self): return {"protocol": "https"}
                
                # Connect servers with different priorities
                await manager.connect_server(
                    PriorityServer("critical"), "critical",
                    priority=ConnectionPriority.CRITICAL
                )
                await manager.connect_server(
                    PriorityServer("normal"), "normal",
                    priority=ConnectionPriority.NORMAL
                )
                
                # Check priority distribution
                stats = manager.get_connection_stats()
                priority_works = (
                    stats['by_priority']['critical'] == 1 and
                    stats['by_priority']['normal'] == 1
                )
                
                tests.append(("Priority Management", priority_works, "Priority assignment works"))
                
                await manager.stop()
            except Exception as e:
                tests.append(("Priority Management", False, f"Priority error: {e}"))
            
            # Test 5: Health monitoring
            try:
                logger = logging.getLogger("test_health")
                manager = ConnectionManager(logger)
                await manager.start()
                
                # Mock healthy server
                class HealthyServer:
                    async def initialize(self): pass
                    def get_capabilities(self): return {"status": "healthy"}
                    def get_server_info(self): return {"protocol": "https"}
                
                server = HealthyServer()
                await manager.connect_server(server, "healthy_server")
                
                # Perform health check
                health_results = await manager.health_check()
                
                health_works = (
                    "healthy_server" in health_results and
                    isinstance(health_results["healthy_server"], bool)
                )
                
                tests.append(("Health Monitoring", health_works, "Health check works"))
                
                await manager.stop()
            except Exception as e:
                tests.append(("Health Monitoring", False, f"Health error: {e}"))
            
            # Test 6: Event system
            try:
                logger = logging.getLogger("test_events")
                manager = ConnectionManager(logger)
                
                # Event capture
                events_captured = []
                def event_handler(data):
                    events_captured.append(data)
                
                manager.on("manager_started", event_handler)
                manager.on("manager_stopped", event_handler)
                
                await manager.start()
                await manager.stop()
                
                # Should have captured start and stop events
                event_system_works = len(events_captured) >= 2
                
                tests.append(("Event System", event_system_works, f"Captured {len(events_captured)} events"))
            except Exception as e:
                tests.append(("Event System", False, f"Event error: {e}"))
            
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
    print("🏃 Running ConnectionManager Tests")
    print("=" * 60)
    
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
        print("Please check the test results above and fix any issues.")
    
    # Final summary
    print("\n" + "=" * 60)
    print("🏁 ConnectionManager Test Summary")
    print("=" * 60)
    print(f"Static Tests: {'✅ PASSED' if static_passed else '❌ FAILED'}")
    print(f"Dynamic Tests: {'✅ PASSED' if dynamic_passed else '❌ FAILED'}")
    print(f"Overall Status: {'✅ SUCCESS' if static_passed and dynamic_passed else '❌ FAILURE'}")
    
    # Additional information for Electron integration
    if static_passed and dynamic_passed:
        print("\n🎨 Electron Integration Notes:")
        print("  • Real-time connection status via manager.get_ui_status()")
        print("  • Event-driven updates via manager.on('event', handler)")
        print("  • Security monitoring via manager.get_security_status()")
        print("  • Priority-based connection management")
        print("  • Comprehensive metrics and health monitoring")
        print("  • Thread-safe operations for UI polling")
    
    exit_code = 0 if (static_passed and dynamic_passed) else 1
    print(f"\nExit Code: {exit_code}")
    print("Run with: python -m src.mcp.core.client.connection_manager")