"""
Enhanced WebSocket Server for MCP Core Server System

Provides real-time bidirectional communication between MCP Core servers and Electron frontend,
enabling server management, capability monitoring, and resource access through WebSocket connections.
"""

import asyncio
import json
import logging
import websockets
from typing import Dict, List, Optional, Any, Set, Callable, Union
from datetime import datetime
import traceback
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path

# Import base server components
from .base_server import BaseMCPServer
from .capability_manager import CapabilityManager
from .resource_manager import ResourceManager
from .tool_executor import ToolExecutor
from ..exceptions import MCPBaseException, ServerError

logger = logging.getLogger(__name__)

@dataclass
class ServerEvent:
    """Represents a server event to be sent to Electron"""
    event_type: str
    server_id: str
    data: Dict[str, Any]
    timestamp: str = None
    correlation_id: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.correlation_id is None:
            self.correlation_id = str(uuid.uuid4())

class MCPServerWebSocketHandler:
    """
    WebSocket handler for MCP Server system
    
    Features:
    - Real-time server status updates
    - Capability monitoring and management
    - Resource access and management
    - Tool execution monitoring
    - Server lifecycle management
    - Performance metrics streaming
    """
    
    def __init__(self, 
                 servers: Dict[str, BaseMCPServer],
                 websocket_port: int = 8766,
                 max_connections: int = 10):
        self.servers = servers
        self.websocket_port = websocket_port
        self.max_connections = max_connections
        
        # WebSocket management
        self.websocket_server = None
        self.connected_clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        
        # Event management
        self.event_queue = asyncio.Queue()
        self.client_subscriptions: Dict[str, Set[str]] = {}
        self.server_subscriptions: Dict[str, Set[str]] = {}  # client_id -> server_ids
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        self.running = False
        
        # Performance monitoring
        self.metrics_interval = 5.0  # seconds
        self.last_metrics_update = None
        
        # Request/response tracking
        self.pending_requests: Dict[str, asyncio.Future] = {}
    
    async def start(self):
        """Start the WebSocket server"""
        if self.running:
            return
        
        logger.info(f"Starting MCP Server WebSocket handler on port {self.websocket_port}")
        
        try:
            # Start WebSocket server
            self.websocket_server = await websockets.serve(
                self._handle_connection,
                "localhost",
                self.websocket_port,
                ping_interval=30,
                ping_timeout=10,
                max_size=10**6,  # 1MB max message size
                max_queue=100
            )
            
            # Start background tasks
            self.background_tasks = [
                asyncio.create_task(self._event_processor()),
                asyncio.create_task(self._metrics_streamer()),
                asyncio.create_task(self._health_monitor()),
                asyncio.create_task(self._connection_cleanup())
            ]
            
            self.running = True
            logger.info("MCP Server WebSocket handler started successfully")
            
            # Register event handlers with servers
            await self._register_server_handlers()
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            raise
    
    async def stop(self):
        """Stop the WebSocket server"""
        if not self.running:
            return
        
        logger.info("Stopping MCP Server WebSocket handler...")
        self.running = False
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Close client connections
        if self.connected_clients:
            await asyncio.gather(
                *[client.close() for client in self.connected_clients.values()],
                return_exceptions=True
            )
        
        # Close WebSocket server
        if self.websocket_server:
            self.websocket_server.close()
            await self.websocket_server.wait_closed()
        
        logger.info("MCP Server WebSocket handler stopped")
    
    async def _handle_connection(self, websocket, path):
        """Handle new WebSocket connection"""
        if len(self.connected_clients) >= self.max_connections:
            await websocket.close(code=1013, reason="Server full")
            return
        
        client_id = str(uuid.uuid4())
        self.connected_clients[client_id] = websocket
        logger.info(f"New client connected: {client_id}")
        
        try:
            # Send welcome message with server info
            await self._send_to_client(client_id, {
                "type": "welcome",
                "client_id": client_id,
                "available_servers": list(self.servers.keys()),
                "server_info": {
                    "version": "2.0.0",
                    "capabilities": ["server_management", "real_time_monitoring", "tool_execution"]
                }
            })
            
            # Handle messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_client_message(client_id, data)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from client {client_id}: {e}")
                    await self._send_error(client_id, "Invalid JSON format")
                except Exception as e:
                    logger.error(f"Message handling error: {e}")
                    await self._send_error(client_id, str(e))
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Connection error for client {client_id}: {e}")
        finally:
            # Cleanup
            self.connected_clients.pop(client_id, None)
            self.client_subscriptions.pop(client_id, None)
            self.server_subscriptions.pop(client_id, None)
    
    async def _handle_client_message(self, client_id: str, data: Dict[str, Any]):
        """Handle incoming message from client"""
        message_type = data.get("type")
        
        if message_type == "subscribe_servers":
            # Subscribe to specific servers
            server_ids = data.get("server_ids", [])
            if client_id not in self.server_subscriptions:
                self.server_subscriptions[client_id] = set()
            self.server_subscriptions[client_id].update(server_ids)
            
            await self._send_to_client(client_id, {
                "type": "subscription_confirmed",
                "subscribed_servers": list(self.server_subscriptions[client_id])
            })
        
        elif message_type == "subscribe_events":
            # Subscribe to specific event types
            events = data.get("events", [])
            if client_id not in self.client_subscriptions:
                self.client_subscriptions[client_id] = set()
            self.client_subscriptions[client_id].update(events)
        
        elif message_type == "get_server_status":
            # Get status of specific server
            server_id = data.get("server_id")
            await self._handle_server_status_request(client_id, server_id, data.get("request_id"))
        
        elif message_type == "get_server_capabilities":
            # Get server capabilities
            server_id = data.get("server_id")
            await self._handle_capabilities_request(client_id, server_id, data.get("request_id"))
        
        elif message_type == "execute_tool":
            # Execute tool on server
            await self._handle_tool_execution(client_id, data)
        
        elif message_type == "get_resources":
            # Get available resources
            server_id = data.get("server_id")
            await self._handle_resources_request(client_id, server_id, data.get("request_id"))
        
        elif message_type == "server_command":
            # Execute server management command
            await self._handle_server_command(client_id, data)
        
        else:
            logger.warning(f"Unknown message type from {client_id}: {message_type}")
    
    async def _handle_server_status_request(self, client_id: str, server_id: str, request_id: str):
        """Handle server status request"""
        try:
            if server_id not in self.servers:
                raise ValueError(f"Server {server_id} not found")
            
            server = self.servers[server_id]
            status = await server.get_status()
            
            await self._send_to_client(client_id, {
                "type": "server_status_response",
                "server_id": server_id,
                "status": status,
                "request_id": request_id
            })
            
        except Exception as e:
            await self._send_error(client_id, str(e), request_id)
    
    async def _handle_capabilities_request(self, client_id: str, server_id: str, request_id: str):
        """Handle server capabilities request"""
        try:
            if server_id not in self.servers:
                raise ValueError(f"Server {server_id} not found")
            
            server = self.servers[server_id]
            capabilities = await server.get_capabilities()
            
            await self._send_to_client(client_id, {
                "type": "capabilities_response",
                "server_id": server_id,
                "capabilities": capabilities,
                "request_id": request_id
            })
            
        except Exception as e:
            await self._send_error(client_id, str(e), request_id)
    
    async def _handle_tool_execution(self, client_id: str, data: Dict[str, Any]):
        """Handle tool execution request"""
        try:
            server_id = data.get("server_id")
            tool_name = data.get("tool_name")
            parameters = data.get("parameters", {})
            request_id = data.get("request_id")
            
            if server_id not in self.servers:
                raise ValueError(f"Server {server_id} not found")
            
            server = self.servers[server_id]
            
            # Execute tool
            result = await server.execute_tool(tool_name, parameters)
            
            await self._send_to_client(client_id, {
                "type": "tool_execution_response",
                "server_id": server_id,
                "tool_name": tool_name,
                "success": result.success,
                "data": result.data if result.success else None,
                "error": result.error if not result.success else None,
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            await self._send_error(client_id, str(e), data.get("request_id"))
    
    async def _handle_resources_request(self, client_id: str, server_id: str, request_id: str):
        """Handle resources request"""
        try:
            if server_id not in self.servers:
                raise ValueError(f"Server {server_id} not found")
            
            server = self.servers[server_id]
            resources = await server.list_resources()
            
            await self._send_to_client(client_id, {
                "type": "resources_response",
                "server_id": server_id,
                "resources": resources,
                "request_id": request_id
            })
            
        except Exception as e:
            await self._send_error(client_id, str(e), request_id)
    
    async def _handle_server_command(self, client_id: str, data: Dict[str, Any]):
        """Handle server management commands"""
        try:
            server_id = data.get("server_id")
            command = data.get("command")
            request_id = data.get("request_id")
            
            if server_id not in self.servers:
                raise ValueError(f"Server {server_id} not found")
            
            server = self.servers[server_id]
            result = None
            
            if command == "start":
                result = await server.start()
            elif command == "stop":
                result = await server.stop()
            elif command == "restart":
                await server.stop()
                result = await server.start()
            elif command == "health_check":
                result = await server.health_check()
            else:
                raise ValueError(f"Unknown command: {command}")
            
            await self._send_to_client(client_id, {
                "type": "server_command_response",
                "server_id": server_id,
                "command": command,
                "success": True,
                "result": result,
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Server command error: {e}")
            await self._send_error(client_id, str(e), data.get("request_id"))
    
    async def emit_server_event(self, server_id: str, event_type: str, data: Dict[str, Any]):
        """Emit server event to subscribed clients"""
        event = ServerEvent(
            event_type=event_type,
            server_id=server_id,
            data=data
        )
        await self.event_queue.put(event)
    
    async def _event_processor(self):
        """Process and distribute events to clients"""
        while self.running:
            try:
                try:
                    event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                # Send to subscribed clients
                for client_id, websocket in list(self.connected_clients.items()):
                    # Check if client is subscribed to this server
                    if (client_id in self.server_subscriptions and 
                        event.server_id in self.server_subscriptions[client_id]):
                        
                        # Check if client is subscribed to this event type
                        if (client_id not in self.client_subscriptions or
                            event.event_type in self.client_subscriptions[client_id]):
                            
                            try:
                                await self._send_to_client(client_id, {
                                    "type": "server_event",
                                    "event_type": event.event_type,
                                    "server_id": event.server_id,
                                    "data": event.data,
                                    "timestamp": event.timestamp,
                                    "correlation_id": event.correlation_id
                                })
                            except Exception as e:
                                logger.error(f"Failed to send event to client {client_id}: {e}")
                                await self._cleanup_client(client_id)
                
            except Exception as e:
                logger.error(f"Event processor error: {e}")
                await asyncio.sleep(1)
    
    async def _metrics_streamer(self):
        """Stream performance metrics to clients"""
        while self.running:
            try:
                await asyncio.sleep(self.metrics_interval)
                
                # Collect metrics from all servers
                metrics = {}
                for server_id, server in self.servers.items():
                    try:
                        server_metrics = await server.get_metrics()
                        metrics[server_id] = server_metrics
                    except Exception as e:
                        logger.error(f"Failed to get metrics for server {server_id}: {e}")
                        metrics[server_id] = {"error": str(e)}
                
                # Send to all connected clients
                if metrics:
                    for client_id in list(self.connected_clients.keys()):
                        try:
                            await self._send_to_client(client_id, {
                                "type": "metrics_update",
                                "metrics": metrics,
                                "timestamp": datetime.now().isoformat()
                            })
                        except Exception as e:
                            logger.error(f"Failed to send metrics to client {client_id}: {e}")
                            await self._cleanup_client(client_id)
                
                self.last_metrics_update = datetime.now()
                
            except Exception as e:
                logger.error(f"Metrics streamer error: {e}")
                await asyncio.sleep(10)
    
    async def _health_monitor(self):
        """Monitor server health and emit events"""
        while self.running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                for server_id, server in self.servers.items():
                    try:
                        health = await server.health_check()
                        await self.emit_server_event(server_id, "health_update", health)
                    except Exception as e:
                        logger.error(f"Health check failed for server {server_id}: {e}")
                        await self.emit_server_event(server_id, "health_error", {"error": str(e)})
                
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(60)
    
    async def _connection_cleanup(self):
        """Clean up dead connections"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                dead_clients = []
                for client_id, websocket in self.connected_clients.items():
                    if websocket.closed:
                        dead_clients.append(client_id)
                
                for client_id in dead_clients:
                    await self._cleanup_client(client_id)
                
            except Exception as e:
                logger.error(f"Connection cleanup error: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_client(self, client_id: str):
        """Clean up client connection and subscriptions"""
        self.connected_clients.pop(client_id, None)
        self.client_subscriptions.pop(client_id, None)
        self.server_subscriptions.pop(client_id, None)
        logger.debug(f"Cleaned up client {client_id}")
    
    async def _send_to_client(self, client_id: str, data: Dict[str, Any]):
        """Send data to specific client"""
        if client_id not in self.connected_clients:
            return
        
        websocket = self.connected_clients[client_id]
        try:
            message = json.dumps(data, default=str)
            await websocket.send(message)
        except Exception as e:
            logger.error(f"Failed to send message to client {client_id}: {e}")
            await self._cleanup_client(client_id)
    
    async def _send_error(self, client_id: str, error_message: str, request_id: str = None):
        """Send error message to client"""
        await self._send_to_client(client_id, {
            "type": "error",
            "message": error_message,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        })
    
    async def _register_server_handlers(self):
        """Register event handlers with all servers"""
        for server_id, server in self.servers.items():
            # Register handlers for server events
            server.on_status_change = lambda status, sid=server_id: asyncio.create_task(
                self.emit_server_event(sid, "status_change", {"status": status})
            )
            
            server.on_tool_execution = lambda result, tool_name, sid=server_id: asyncio.create_task(
                self.emit_server_event(sid, "tool_executed", {
                    "tool_name": tool_name,
                    "success": result.success,
                    "data": result.data if result.success else None,
                    "error": result.error if not result.success else None
                })
            )
            
            server.on_error = lambda error, context, sid=server_id: asyncio.create_task(
                self.emit_server_event(sid, "server_error", {
                    "error": str(error),
                    "context": context,
                    "traceback": traceback.format_exc()
                })
            )

# Factory function
def create_websocket_handler(servers: Dict[str, BaseMCPServer], **kwargs) -> MCPServerWebSocketHandler:
    """Create and configure a WebSocket handler for MCP servers"""
    return MCPServerWebSocketHandler(servers, **kwargs) 