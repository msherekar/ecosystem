"""
Enhanced Electron Bridge for MCP Core Client System

Provides seamless integration between the Python MCP Core client and Electron frontend,
enabling real-time communication, state synchronization, and event-driven updates.
"""

import asyncio
import json
import logging
import websockets
from typing import Dict, List, Optional, Any, Callable, Set
from datetime import datetime
import traceback
from dataclasses import dataclass, asdict
from pathlib import Path
import uuid

# Import base classes
from .mcp_client import MCPClient, OperationResult
from .cache_manager import CacheManager
from .connection_manager import ConnectionManager
from .execution_engine import ExecutionEngine
from ..exceptions import MCPBaseException

logger = logging.getLogger(__name__)

@dataclass
class ElectronEvent:
    """Represents an event to be sent to Electron frontend"""
    event_type: str
    data: Dict[str, Any]
    timestamp: str = None
    source: str = "mcp_client"
    correlation_id: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.correlation_id is None:
            self.correlation_id = str(uuid.uuid4())

class MCPClientElectronBridge:
    """
    Bridge between MCP Client system and Electron frontend
    
    Features:
    - Real-time WebSocket communication
    - Event serialization and forwarding
    - State synchronization
    - Request/response handling
    - Subscription management
    """
    
    def __init__(self, 
                 client: MCPClient,
                 websocket_port: int = 8765,
                 ui_update_interval: float = 0.1):
        self.client = client
        self.websocket_port = websocket_port
        self.ui_update_interval = ui_update_interval
        
        # WebSocket management
        self.websocket_server = None
        self.connected_clients: Set[websockets.WebSocketServerProtocol] = set()
        
        # Event management
        self.event_queue = asyncio.Queue()
        self.event_subscriptions: Dict[str, Set[str]] = {}  # client_id -> subscribed events
        
        # State management
        self.last_state_sync = None
        self.state_sync_interval = 1.0  # seconds
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        self.running = False
        
        # Event handlers
        self._setup_client_event_handlers()
    
    def _setup_client_event_handlers(self):
        """Setup event handlers for client system events"""
        
        # Register handlers for different client events
        self.client.on_connection_change = self._handle_connection_change
        self.client.on_execution_start = self._handle_execution_start
        self.client.on_execution_complete = self._handle_execution_complete
        self.client.on_cache_update = self._handle_cache_update
        self.client.on_error = self._handle_error
    
    async def start(self):
        """Start the Electron bridge"""
        if self.running:
            return
        
        logger.info(f"Starting Electron bridge on port {self.websocket_port}")
        
        try:
            # Start WebSocket server
            self.websocket_server = await websockets.serve(
                self._handle_websocket_connection,
                "localhost",
                self.websocket_port,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10
            )
            
            # Start background tasks
            self.background_tasks = [
                asyncio.create_task(self._event_processor()),
                asyncio.create_task(self._state_synchronizer()),
                asyncio.create_task(self._connection_monitor())
            ]
            
            self.running = True
            logger.info("Electron bridge started successfully")
            
            # Send initial system status
            await self.emit_event("system_ready", {
                "client_status": await self.client.get_status(),
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Failed to start Electron bridge: {e}")
            raise
    
    async def stop(self):
        """Stop the Electron bridge"""
        if not self.running:
            return
        
        logger.info("Stopping Electron bridge...")
        self.running = False
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Close WebSocket connections
        if self.connected_clients:
            await asyncio.gather(
                *[client.close() for client in self.connected_clients],
                return_exceptions=True
            )
        
        # Close WebSocket server
        if self.websocket_server:
            self.websocket_server.close()
            await self.websocket_server.wait_closed()
        
        logger.info("Electron bridge stopped")
    
    async def _handle_websocket_connection(self, websocket, path):
        """Handle new WebSocket connection from Electron"""
        client_id = str(uuid.uuid4())
        self.connected_clients.add(websocket)
        logger.info(f"New Electron client connected: {client_id}")
        
        try:
            # Send welcome message
            await self._send_to_client(websocket, {
                "type": "welcome",
                "client_id": client_id,
                "server_info": {
                    "version": "2.0.0",
                    "capabilities": ["real_time_updates", "state_sync", "subscriptions"]
                }
            })
            
            # Handle incoming messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_client_message(websocket, client_id, data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from client {client_id}: {message}")
                except Exception as e:
                    logger.error(f"Error handling message from {client_id}: {e}")
                    await self._send_error_to_client(websocket, str(e))
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"WebSocket error for client {client_id}: {e}")
        finally:
            self.connected_clients.discard(websocket)
            # Clean up subscriptions
            self.event_subscriptions.pop(client_id, None)
    
    async def _handle_client_message(self, websocket, client_id: str, data: Dict[str, Any]):
        """Handle incoming message from Electron client"""
        message_type = data.get("type")
        
        if message_type == "subscribe":
            # Handle event subscription
            events = data.get("events", [])
            if client_id not in self.event_subscriptions:
                self.event_subscriptions[client_id] = set()
            self.event_subscriptions[client_id].update(events)
            
            await self._send_to_client(websocket, {
                "type": "subscription_confirmed",
                "events": list(self.event_subscriptions[client_id])
            })
        
        elif message_type == "unsubscribe":
            # Handle event unsubscription
            events = data.get("events", [])
            if client_id in self.event_subscriptions:
                self.event_subscriptions[client_id].difference_update(events)
        
        elif message_type == "execute_operation":
            # Handle operation execution request
            await self._handle_execution_request(websocket, client_id, data)
        
        elif message_type == "get_status":
            # Handle status request
            status = await self.client.get_status()
            await self._send_to_client(websocket, {
                "type": "status_response",
                "data": status,
                "request_id": data.get("request_id")
            })
        
        elif message_type == "sync_state":
            # Handle state synchronization request
            await self._send_full_state(websocket)
        
        else:
            logger.warning(f"Unknown message type from {client_id}: {message_type}")
    
    async def _handle_execution_request(self, websocket, client_id: str, data: Dict[str, Any]):
        """Handle execution request from Electron"""
        try:
            operation_type = data.get("operation")
            params = data.get("params", {})
            request_id = data.get("request_id")
            
            if operation_type == "connect_server":
                result = await self.client.connect_server(**params)
            elif operation_type == "disconnect_server":
                result = await self.client.disconnect_server(params.get("server_name"))
            elif operation_type == "execute_tool":
                result = await self.client.execute_tool(**params)
            elif operation_type == "list_servers":
                result = await self.client.list_servers()
            else:
                raise ValueError(f"Unknown operation: {operation_type}")
            
            # Send response
            await self._send_to_client(websocket, {
                "type": "execution_response",
                "success": True,
                "data": result,
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Execution error for client {client_id}: {e}")
            await self._send_to_client(websocket, {
                "type": "execution_response",
                "success": False,
                "error": str(e),
                "request_id": data.get("request_id")
            })
    
    async def emit_event(self, event_type: str, data: Dict[str, Any], target_clients: Optional[List[str]] = None):
        """Emit event to Electron clients"""
        event = ElectronEvent(event_type=event_type, data=data)
        await self.event_queue.put(event)
    
    async def _event_processor(self):
        """Process events and send to connected clients"""
        while self.running:
            try:
                # Get event from queue with timeout
                try:
                    event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                # Send to all subscribed clients
                for websocket in list(self.connected_clients):
                    client_id = getattr(websocket, 'client_id', None)
                    
                    # Check if client is subscribed to this event
                    if (client_id in self.event_subscriptions and 
                        event.event_type in self.event_subscriptions[client_id]):
                        
                        try:
                            await self._send_to_client(websocket, {
                                "type": "event",
                                "event_type": event.event_type,
                                "data": event.data,
                                "timestamp": event.timestamp,
                                "correlation_id": event.correlation_id
                            })
                        except Exception as e:
                            logger.error(f"Failed to send event to client: {e}")
                            self.connected_clients.discard(websocket)
                
            except Exception as e:
                logger.error(f"Event processor error: {e}")
                await asyncio.sleep(1)
    
    async def _state_synchronizer(self):
        """Periodically synchronize state with Electron clients"""
        while self.running:
            try:
                await asyncio.sleep(self.state_sync_interval)
                
                # Get current state
                current_state = await self._get_current_state()
                
                # Send to all connected clients
                for websocket in list(self.connected_clients):
                    try:
                        await self._send_to_client(websocket, {
                            "type": "state_sync",
                            "data": current_state,
                            "timestamp": datetime.now().isoformat()
                        })
                    except Exception as e:
                        logger.error(f"State sync error: {e}")
                        self.connected_clients.discard(websocket)
                
                self.last_state_sync = datetime.now()
                
            except Exception as e:
                logger.error(f"State synchronizer error: {e}")
                await asyncio.sleep(5)
    
    async def _connection_monitor(self):
        """Monitor WebSocket connections and clean up dead ones"""
        while self.running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                dead_connections = []
                for websocket in list(self.connected_clients):
                    if websocket.closed:
                        dead_connections.append(websocket)
                
                for websocket in dead_connections:
                    self.connected_clients.discard(websocket)
                    logger.debug("Removed dead WebSocket connection")
                
            except Exception as e:
                logger.error(f"Connection monitor error: {e}")
                await asyncio.sleep(10)
    
    async def _get_current_state(self) -> Dict[str, Any]:
        """Get current system state for synchronization"""
        try:
            return {
                "client_status": await self.client.get_status(),
                "connected_servers": await self.client.list_servers(),
                "cache_stats": self.client.cache_manager.get_stats() if self.client.cache_manager else {},
                "execution_stats": self.client.execution_engine.get_stats() if self.client.execution_engine else {},
                "connection_stats": self.client.connection_manager.get_stats() if self.client.connection_manager else {}
            }
        except Exception as e:
            logger.error(f"Error getting current state: {e}")
            return {"error": str(e)}
    
    async def _send_to_client(self, websocket, data: Dict[str, Any]):
        """Send data to specific client"""
        try:
            message = json.dumps(data, default=str)
            await websocket.send(message)
        except Exception as e:
            logger.error(f"Failed to send message to client: {e}")
            raise
    
    async def _send_error_to_client(self, websocket, error_message: str):
        """Send error message to client"""
        await self._send_to_client(websocket, {
            "type": "error",
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        })
    
    async def _send_full_state(self, websocket):
        """Send full system state to client"""
        state = await self._get_current_state()
        await self._send_to_client(websocket, {
            "type": "full_state",
            "data": state,
            "timestamp": datetime.now().isoformat()
        })
    
    # Event handlers for client system events
    async def _handle_connection_change(self, server_name: str, connected: bool):
        """Handle server connection changes"""
        await self.emit_event("connection_change", {
            "server_name": server_name,
            "connected": connected
        })
    
    async def _handle_execution_start(self, operation_id: str, operation_type: str, params: Dict[str, Any]):
        """Handle execution start"""
        await self.emit_event("execution_start", {
            "operation_id": operation_id,
            "operation_type": operation_type,
            "params": params
        })
    
    async def _handle_execution_complete(self, operation_id: str, result: OperationResult):
        """Handle execution completion"""
        await self.emit_event("execution_complete", {
            "operation_id": operation_id,
            "success": result.success,
            "data": result.data if result.success else None,
            "error": result.error if not result.success else None
        })
    
    async def _handle_cache_update(self, cache_key: str, action: str):
        """Handle cache updates"""
        await self.emit_event("cache_update", {
            "cache_key": cache_key,
            "action": action
        })
    
    async def _handle_error(self, error: Exception, context: Dict[str, Any]):
        """Handle system errors"""
        await self.emit_event("system_error", {
            "error": str(error),
            "error_type": type(error).__name__,
            "context": context,
            "traceback": traceback.format_exc()
        })

# Factory function
def create_electron_bridge(client: MCPClient, **kwargs) -> MCPClientElectronBridge:
    """Create and configure an Electron bridge for the MCP client"""
    return MCPClientElectronBridge(client, **kwargs) 