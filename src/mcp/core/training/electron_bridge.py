"""
Enhanced Electron Bridge for MCP Core Training System

Provides seamless integration between the Python MCP Core training system and Electron frontend,
enabling real-time training data collection updates, session management, and analytics visualization.
"""

import asyncio
import json
import logging
import websockets
from typing import Dict, List, Optional, Any, Callable, Set
from datetime import datetime
import uuid
import traceback
from dataclasses import dataclass, asdict
from pathlib import Path

# Import training components
from . import TrainingCollector, SessionManager, TrainingConfig, ExportFormat
from .collectors import DataCollector
from .session_manager import TrainingSession
from .exporters import TrainingExporter
from ..exceptions import MCPBaseException

logger = logging.getLogger(__name__)

@dataclass 
class TrainingEvent:
    """Represents a training event to be sent to Electron"""
    event_type: str
    session_id: str
    data: Dict[str, Any]
    timestamp: str = None
    correlation_id: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.correlation_id is None:
            self.correlation_id = str(uuid.uuid4())

class MCPTrainingElectronBridge:
    """
    Bridge between MCP Training system and Electron frontend
    
    Features:
    - Real-time training data collection updates
    - Session management and monitoring
    - Training analytics and visualization data
    - Export progress tracking
    - Performance metrics streaming
    - Collection configuration management
    """
    
    def __init__(self,
                 training_collector=None,
                 session_manager=None,
                 websocket_port: int = 8767,
                 update_interval: float = 0.5):
        self.training_collector = training_collector
        self.session_manager = session_manager
        self.websocket_port = websocket_port
        self.update_interval = update_interval
        
        # WebSocket management
        self.websocket_server = None
        self.connected_clients: Set[websockets.WebSocketServerProtocol] = set()
        
        # Event management
        self.event_queue = asyncio.Queue()
        self.client_subscriptions: Dict[str, Set[str]] = {}  # client_id -> subscribed events
        self.session_subscriptions: Dict[str, Set[str]] = {}  # client_id -> session_ids
        
        # State management
        self.last_analytics_update = None
        self.analytics_interval = 2.0  # seconds
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        self.running = False
        
        # Performance tracking
        self.metrics = {
            "data_points_collected": 0,
            "sessions_active": 0,
            "exports_completed": 0,
            "last_collection_time": None
        }
        
        # Setup event handlers
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Setup event handlers for training system events"""
        if self.training_collector:
            # Training collector events
            if hasattr(self.training_collector, 'on_data_collected'):
                self.training_collector.on_data_collected = self._handle_data_collected
            if hasattr(self.training_collector, 'on_collection_started'):
                self.training_collector.on_collection_started = self._handle_collection_started
            if hasattr(self.training_collector, 'on_collection_stopped'):
                self.training_collector.on_collection_stopped = self._handle_collection_stopped
            if hasattr(self.training_collector, 'on_collection_error'):
                self.training_collector.on_collection_error = self._handle_collection_error
        
        if self.session_manager:
            # Session manager events  
            if hasattr(self.session_manager, 'on_session_created'):
                self.session_manager.on_session_created = self._handle_session_created
            if hasattr(self.session_manager, 'on_session_updated'):
                self.session_manager.on_session_updated = self._handle_session_updated
            if hasattr(self.session_manager, 'on_session_ended'):
                self.session_manager.on_session_ended = self._handle_session_ended
            if hasattr(self.session_manager, 'on_export_started'):
                self.session_manager.on_export_started = self._handle_export_started
            if hasattr(self.session_manager, 'on_export_completed'):
                self.session_manager.on_export_completed = self._handle_export_completed
    
    async def start(self):
        """Start the training Electron bridge"""
        if self.running:
            return
        
        logger.info(f"Starting Training Electron bridge on port {self.websocket_port}")
        
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
                asyncio.create_task(self._analytics_streamer()),
                asyncio.create_task(self._session_monitor()),
                asyncio.create_task(self._connection_monitor())
            ]
            
            self.running = True
            logger.info("Training Electron bridge started successfully")
            
            # Send initial status
            await self.emit_event("system_ready", "global", {
                "training_status": await self._get_training_status(),
                "active_sessions": await self._get_active_sessions(),
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Failed to start Training Electron bridge: {e}")
            raise
    
    async def stop(self):
        """Stop the training Electron bridge"""
        if not self.running:
            return
        
        logger.info("Stopping Training Electron bridge...")
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
        
        logger.info("Training Electron bridge stopped")
    
    async def _handle_websocket_connection(self, websocket, path):
        """Handle new WebSocket connection from Electron"""
        client_id = str(uuid.uuid4())
        self.connected_clients.add(websocket)
        logger.info(f"New training client connected: {client_id}")
        
        try:
            # Send welcome message
            await self._send_to_client(websocket, {
                "type": "welcome",
                "client_id": client_id,
                "server_info": {
                    "version": "2.0.0",
                    "capabilities": ["training_monitoring", "session_management", "real_time_analytics"]  
                }
            })
            
            # Handle incoming messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_client_message(websocket, client_id, data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from training client {client_id}: {message}")
                except Exception as e:
                    logger.error(f"Error handling training message from {client_id}: {e}")
                    await self._send_error_to_client(websocket, str(e))
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Training client {client_id} disconnected")
        except Exception as e:
            logger.error(f"WebSocket error for training client {client_id}: {e}")
        finally:
            self.connected_clients.discard(websocket)
            # Clean up subscriptions
            self.client_subscriptions.pop(client_id, None)
            self.session_subscriptions.pop(client_id, None)
    
    async def _handle_client_message(self, websocket, client_id: str, data: Dict[str, Any]):
        """Handle incoming message from Electron client"""
        message_type = data.get("type")
        
        if message_type == "subscribe":
            # Handle event subscription
            events = data.get("events", [])
            if client_id not in self.client_subscriptions:
                self.client_subscriptions[client_id] = set()
            self.client_subscriptions[client_id].update(events)
            
            await self._send_to_client(websocket, {
                "type": "subscription_confirmed",
                "events": list(self.client_subscriptions[client_id])
            })
        
        elif message_type == "subscribe_sessions":
            # Handle session subscription
            session_ids = data.get("session_ids", [])
            if client_id not in self.session_subscriptions:
                self.session_subscriptions[client_id] = set()
            self.session_subscriptions[client_id].update(session_ids)
        
        elif message_type == "start_collection":
            # Handle collection start request
            await self._handle_start_collection_request(websocket, client_id, data)
        
        elif message_type == "stop_collection":
            # Handle collection stop request
            await self._handle_stop_collection_request(websocket, client_id, data)
        
        elif message_type == "create_session":
            # Handle session creation request
            await self._handle_create_session_request(websocket, client_id, data)
        
        elif message_type == "get_session_data":
            # Handle session data request
            await self._handle_get_session_data_request(websocket, client_id, data)
        
        elif message_type == "export_session":
            # Handle session export request
            await self._handle_export_session_request(websocket, client_id, data)
        
        elif message_type == "get_analytics":
            # Handle analytics request
            await self._handle_get_analytics_request(websocket, client_id, data)
        
        elif message_type == "get_status":
            # Handle status request
            status = await self._get_training_status()
            await self._send_to_client(websocket, {
                "type": "status_response",
                "data": status,
                "request_id": data.get("request_id")
            })
        
        else:
            logger.warning(f"Unknown message type from training client {client_id}: {message_type}")
    
    async def _handle_start_collection_request(self, websocket, client_id: str, data: Dict[str, Any]):
        """Handle collection start request"""
        try:
            session_id = data.get("session_id")
            config = data.get("config", {})
            request_id = data.get("request_id")
            
            # Start collection
            success = True
            if self.training_collector and hasattr(self.training_collector, 'start_collection'):
                success = await self.training_collector.start_collection(session_id, **config)
            
            await self._send_to_client(websocket, {
                "type": "collection_start_response", 
                "success": success,
                "session_id": session_id,
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Collection start error for client {client_id}: {e}")
            await self._send_to_client(websocket, {
                "type": "collection_start_response",
                "success": False,
                "error": str(e),
                "request_id": data.get("request_id")
            })
    
    async def _handle_stop_collection_request(self, websocket, client_id: str, data: Dict[str, Any]):
        """Handle collection stop request"""
        try:
            session_id = data.get("session_id")
            request_id = data.get("request_id")
            
            # Stop collection
            success = True
            if self.training_collector and hasattr(self.training_collector, 'stop_collection'):
                success = await self.training_collector.stop_collection(session_id)
            
            await self._send_to_client(websocket, {
                "type": "collection_stop_response",
                "success": success,
                "session_id": session_id,
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Collection stop error for client {client_id}: {e}")
            await self._send_to_client(websocket, {
                "type": "collection_stop_response",
                "success": False,
                "error": str(e),
                "request_id": data.get("request_id")
            })
    
    async def _handle_create_session_request(self, websocket, client_id: str, data: Dict[str, Any]):
        """Handle session creation request"""
        try:
            session_name = data.get("session_name")
            metadata = data.get("metadata", {})
            request_id = data.get("request_id")
            
            # Create session
            session = None
            if self.session_manager and hasattr(self.session_manager, 'create_session'):
                session = await self.session_manager.create_session(session_name, metadata)
            
            if session:
                await self._send_to_client(websocket, {
                    "type": "session_create_response",
                    "success": True,
                    "session": {
                        "id": getattr(session, 'id', str(uuid.uuid4())),
                        "name": getattr(session, 'name', session_name),
                        "created_at": getattr(session, 'created_at', datetime.now()).isoformat(),
                        "metadata": getattr(session, 'metadata', metadata)
                    },
                    "request_id": request_id
                })
            else:
                await self._send_to_client(websocket, {
                    "type": "session_create_response",
                    "success": False,
                    "error": "Session manager not available",
                    "request_id": request_id
                })
            
        except Exception as e:
            logger.error(f"Session creation error for client {client_id}: {e}")
            await self._send_to_client(websocket, {
                "type": "session_create_response",
                "success": False,
                "error": str(e),
                "request_id": data.get("request_id")
            })
    
    async def _handle_get_session_data_request(self, websocket, client_id: str, data: Dict[str, Any]):
        """Handle session data request"""
        try:
            session_id = data.get("session_id")
            request_id = data.get("request_id")
            
            # Get session data
            session_data = {}
            if self.session_manager and hasattr(self.session_manager, 'get_session_data'):
                session_data = await self.session_manager.get_session_data(session_id)
            
            await self._send_to_client(websocket, {
                "type": "session_data_response",
                "success": True,
                "session_id": session_id,
                "data": session_data,
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Session data error for client {client_id}: {e}")
            await self._send_to_client(websocket, {
                "type": "session_data_response",
                "success": False,
                "error": str(e),
                "request_id": data.get("request_id")
            })
    
    async def _handle_export_session_request(self, websocket, client_id: str, data: Dict[str, Any]):
        """Handle session export request"""
        try:
            session_id = data.get("session_id")
            format_type = data.get("format", "json")
            output_path = data.get("output_path")
            request_id = data.get("request_id")
            
            # Start export (async operation)
            result = {"export_path": output_path or f"session_{session_id}.{format_type}"}
            if self.session_manager and hasattr(self.session_manager, 'export_session'):
                export_task = asyncio.create_task(
                    self.session_manager.export_session(session_id, format_type, output_path)
                )
                result = await export_task
            
            await self._send_to_client(websocket, {
                "type": "session_export_response",
                "success": True,
                "session_id": session_id,
                "export_path": result.get("export_path"),
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Session export error for client {client_id}: {e}")
            await self._send_to_client(websocket, {
                "type": "session_export_response",
                "success": False,
                "error": str(e),
                "request_id": data.get("request_id")
            })
    
    async def _handle_get_analytics_request(self, websocket, client_id: str, data: Dict[str, Any]):
        """Handle analytics request"""
        try:
            analytics_type = data.get("analytics_type", "summary")
            session_id = data.get("session_id")  # Optional
            request_id = data.get("request_id")
            
            # Get analytics data
            analytics = await self._get_analytics_data(analytics_type, session_id)
            
            await self._send_to_client(websocket, {
                "type": "analytics_response",
                "success": True,
                "analytics_type": analytics_type,
                "data": analytics,
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Analytics error for client {client_id}: {e}")
            await self._send_to_client(websocket, {
                "type": "analytics_response",
                "success": False,
                "error": str(e),
                "request_id": data.get("request_id")
            })
    
    async def emit_event(self, event_type: str, session_id: str, data: Dict[str, Any]):
        """Emit training event to subscribed clients"""
        event = TrainingEvent(
            event_type=event_type,
            session_id=session_id,
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
                for websocket in list(self.connected_clients):
                    client_id = getattr(websocket, 'client_id', None)
                    
                    # Check if client is subscribed to this event type
                    if (client_id in self.client_subscriptions and
                        event.event_type in self.client_subscriptions[client_id]):
                        
                        # Check if client is subscribed to this session
                        if (client_id not in self.session_subscriptions or
                            event.session_id in self.session_subscriptions[client_id] or
                            event.session_id == "global"):
                            
                            try:
                                await self._send_to_client(websocket, {
                                    "type": "training_event",
                                    "event_type": event.event_type,
                                    "session_id": event.session_id,
                                    "data": event.data,
                                    "timestamp": event.timestamp,
                                    "correlation_id": event.correlation_id
                                })
                            except Exception as e:
                                logger.error(f"Failed to send training event to client: {e}")
                                self.connected_clients.discard(websocket)
                
            except Exception as e:
                logger.error(f"Training event processor error: {e}")
                await asyncio.sleep(1)
    
    async def _analytics_streamer(self):
        """Stream analytics data to clients"""
        while self.running:
            try:
                await asyncio.sleep(self.analytics_interval)
                
                # Get current analytics
                analytics = await self._get_analytics_data("real_time")
                
                # Send to all connected clients
                for websocket in list(self.connected_clients):
                    try:
                        await self._send_to_client(websocket, {
                            "type": "analytics_update",
                            "data": analytics,
                            "timestamp": datetime.now().isoformat()
                        })
                    except Exception as e:
                        logger.error(f"Analytics stream error: {e}")
                        self.connected_clients.discard(websocket)
                
                self.last_analytics_update = datetime.now()
                
            except Exception as e:
                logger.error(f"Analytics streamer error: {e}")
                await asyncio.sleep(5)
    
    async def _session_monitor(self):
        """Monitor session status and emit events"""
        while self.running:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                # Get active sessions
                active_sessions = await self._get_active_sessions()
                
                for session_data in active_sessions:
                    # Emit session heartbeat
                    await self.emit_event("session_heartbeat", session_data.get("id", "unknown"), {
                        "session_name": session_data.get("name", "Unknown"),
                        "data_points": session_data.get("data_points", 0),
                        "last_activity": session_data.get("last_activity")
                    })
                
                # Update metrics
                self.metrics["sessions_active"] = len(active_sessions)
                
            except Exception as e:
                logger.error(f"Session monitor error: {e}")
                await asyncio.sleep(30)
    
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
                    logger.debug("Removed dead training WebSocket connection")
                
            except Exception as e:
                logger.error(f"Training connection monitor error: {e}")
                await asyncio.sleep(10)
    
    async def _get_training_status(self) -> Dict[str, Any]:
        """Get current training system status"""
        try:
            return {
                "collector_running": (self.training_collector and 
                                    hasattr(self.training_collector, 'is_running') and 
                                    self.training_collector.is_running()),
                "active_sessions": len(await self._get_active_sessions()),
                "total_data_points": self.metrics["data_points_collected"],
                "last_collection": self.metrics["last_collection_time"],
                "exports_completed": self.metrics["exports_completed"]
            }
        except Exception as e:
            logger.error(f"Error getting training status: {e}")
            return {"error": str(e)}
    
    async def _get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get active training sessions"""
        try:
            if self.session_manager and hasattr(self.session_manager, 'get_active_sessions'):
                sessions = await self.session_manager.get_active_sessions()
                return [
                    {
                        "id": getattr(session, 'id', str(uuid.uuid4())),
                        "name": getattr(session, 'name', 'Unknown'),
                        "created_at": getattr(session, 'created_at', datetime.now()).isoformat(),
                        "data_points": len(getattr(session, 'data_points', [])),
                        "last_activity": getattr(session, 'last_activity', datetime.now()).isoformat()
                    }
                    for session in sessions
                ]
            else:
                return []
        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")
            return []
    
    async def _get_analytics_data(self, analytics_type: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get analytics data for visualization"""
        try:
            if analytics_type == "summary":
                return {
                    "total_sessions": (await self._get_session_count()),
                    "total_data_points": self.metrics["data_points_collected"],
                    "active_sessions": len(await self._get_active_sessions()),
                    "collection_rate": await self._calculate_collection_rate()
                }
            
            elif analytics_type == "real_time":
                return {
                    "current_rate": await self._calculate_current_collection_rate(), 
                    "active_collectors": await self._get_active_collectors_count(),
                    "memory_usage": await self._get_memory_usage(),
                    "processing_latency": await self._get_processing_latency()
                }
            
            elif analytics_type == "session_details" and session_id:
                return await self._get_session_analytics(session_id)
            
            else:
                return {"error": f"Unknown analytics type: {analytics_type}"}
                
        except Exception as e:
            logger.error(f"Error getting analytics data: {e}")
            return {"error": str(e)}
    
    async def _get_session_count(self) -> int:
        """Get total session count"""
        if self.session_manager and hasattr(self.session_manager, 'get_session_count'):
            return await self.session_manager.get_session_count()
        return 0
    
    async def _calculate_collection_rate(self) -> float:
        """Calculate data collection rate"""
        # Simplified rate calculation
        return 0.0  # Implement based on actual metrics
    
    async def _calculate_current_collection_rate(self) -> float:
        """Calculate current collection rate"""
        # Simplified current rate calculation  
        return 0.0  # Implement based on actual metrics
    
    async def _get_active_collectors_count(self) -> int:
        """Get number of active collectors"""
        return 1 if (self.training_collector and 
                    hasattr(self.training_collector, 'is_running') and 
                    self.training_collector.is_running()) else 0
    
    async def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage metrics"""
        # Simplified memory usage
        return {"used": 0, "available": 0}
    
    async def _get_processing_latency(self) -> float:
        """Get processing latency metrics"""
        # Simplified latency calculation
        return 0.0
    
    async def _get_session_analytics(self, session_id: str) -> Dict[str, Any]:
        """Get detailed analytics for a specific session"""
        try:
            if self.session_manager and hasattr(self.session_manager, 'get_session'):
                session = await self.session_manager.get_session(session_id)
                if not session:
                    return {"error": "Session not found"}
                
                return {
                    "session_id": session_id,
                    "data_points_count": len(getattr(session, 'data_points', [])),
                    "collection_duration": (datetime.now() - getattr(session, 'created_at', datetime.now())).total_seconds(),
                    "data_types": await self._analyze_data_types(session),
                    "quality_metrics": await self._calculate_quality_metrics(session)
                }
            else:
                return {"error": "Session manager not available"}
            
        except Exception as e:
            logger.error(f"Error getting session analytics: {e}")
            return {"error": str(e)}
    
    async def _analyze_data_types(self, session) -> Dict[str, int]:
        """Analyze data types in session"""
        # Simplified data type analysis
        return {"text": 0, "numeric": 0, "binary": 0}
    
    async def _calculate_quality_metrics(self, session) -> Dict[str, float]:
        """Calculate data quality metrics"""
        # Simplified quality metrics
        return {"completeness": 1.0, "accuracy": 1.0, "consistency": 1.0}
    
    async def _send_to_client(self, websocket, data: Dict[str, Any]):
        """Send data to specific client"""
        try:
            message = json.dumps(data, default=str)
            await websocket.send(message)
        except Exception as e:
            logger.error(f"Failed to send message to training client: {e}")
            raise
    
    async def _send_error_to_client(self, websocket, error_message: str):
        """Send error message to client"""
        await self._send_to_client(websocket, {
            "type": "error",
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        })
    
    # Event handlers for training system events
    async def _handle_data_collected(self, session_id: str, data_point: Dict[str, Any]):
        """Handle data collection event"""
        self.metrics["data_points_collected"] += 1
        self.metrics["last_collection_time"] = datetime.now().isoformat()
        
        await self.emit_event("data_collected", session_id, {
            "data_point": data_point,
            "total_collected": self.metrics["data_points_collected"]
        })
    
    async def _handle_collection_started(self, session_id: str):
        """Handle collection start event"""
        await self.emit_event("collection_started", session_id, {
            "timestamp": datetime.now().isoformat()
        })
    
    async def _handle_collection_stopped(self, session_id: str):
        """Handle collection stop event"""
        await self.emit_event("collection_stopped", session_id, {
            "timestamp": datetime.now().isoformat()
        })
    
    async def _handle_collection_error(self, session_id: str, error: Exception):
        """Handle collection error event"""
        await self.emit_event("collection_error", session_id, {
            "error": str(error),
            "error_type": type(error).__name__,
            "traceback": traceback.format_exc()
        })
    
    async def _handle_session_created(self, session):
        """Handle session creation event"""
        await self.emit_event("session_created", getattr(session, 'id', 'unknown'), {
            "session_name": getattr(session, 'name', 'Unknown'),
            "created_at": getattr(session, 'created_at', datetime.now()).isoformat(),
            "metadata": getattr(session, 'metadata', {})
        })
    
    async def _handle_session_updated(self, session):
        """Handle session update event"""
        await self.emit_event("session_updated", getattr(session, 'id', 'unknown'), {
            "session_name": getattr(session, 'name', 'Unknown'),
            "data_points": len(getattr(session, 'data_points', [])),
            "last_activity": getattr(session, 'last_activity', datetime.now()).isoformat()
        })
    
    async def _handle_session_ended(self, session):
        """Handle session end event"""
        await self.emit_event("session_ended", getattr(session, 'id', 'unknown'), {
            "session_name": getattr(session, 'name', 'Unknown'),
            "total_data_points": len(getattr(session, 'data_points', [])),
            "duration": (datetime.now() - getattr(session, 'created_at', datetime.now())).total_seconds()
        })
    
    async def _handle_export_started(self, session_id: str, export_format: str):
        """Handle export start event"""
        await self.emit_event("export_started", session_id, {
            "format": export_format,
            "timestamp": datetime.now().isoformat()
        })
    
    async def _handle_export_completed(self, session_id: str, export_path: str):
        """Handle export completion event"""
        self.metrics["exports_completed"] += 1
        
        await self.emit_event("export_completed", session_id, {
            "export_path": export_path,
            "total_exports": self.metrics["exports_completed"]
        })

# Factory function
def create_training_bridge(training_collector=None, 
                          session_manager=None, 
                          **kwargs) -> MCPTrainingElectronBridge:
    """Create and configure an Electron bridge for the training system"""
    return MCPTrainingElectronBridge(training_collector, session_manager, **kwargs) 