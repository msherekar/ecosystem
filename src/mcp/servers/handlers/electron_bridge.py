"""
Electron Bridge

Provides integration between Python backend and Electron frontend.
Handles IPC communication, progress updates, and UI state synchronization.
"""

import json
import asyncio
import websockets
from typing import Any, Dict, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
import logging
from pathlib import Path


@dataclass
class ElectronMessage:
    """Message structure for Electron communication"""
    type: str
    payload: Dict[str, Any]
    timestamp: str
    message_id: str


class ElectronBridge:
    """Bridge for communicating with Electron frontend"""
    
    def __init__(self, websocket_port: int = 8765, log_file: str = "logs/electron_bridge.log"):
        self.websocket_port = websocket_port
        self.websocket_server = None
        self.connected_clients = set()
        
        # Setup logging
        self.logger = logging.getLogger("electron_bridge")
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        
        # Message handlers
        self.message_handlers: Dict[str, Callable] = {}
        self._setup_default_handlers()
    
    async def start_server(self):
        """Start WebSocket server for Electron communication"""
        try:
            self.websocket_server = await websockets.serve(
                self._handle_client,
                "localhost",
                self.websocket_port
            )
            self.logger.info(f"WebSocket server started on port {self.websocket_port}")
        except Exception as e:
            self.logger.error(f"Failed to start WebSocket server: {e}")
    
    async def stop_server(self):
        """Stop WebSocket server"""
        if self.websocket_server:
            self.websocket_server.close()
            await self.websocket_server.wait_closed()
            self.logger.info("WebSocket server stopped")
    
    async def _handle_client(self, websocket, path):
        """Handle new WebSocket client connection"""
        self.connected_clients.add(websocket)
        self.logger.info("New Electron client connected")
        
        try:
            async for message in websocket:
                await self._process_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            self.logger.info("Electron client disconnected")
        except Exception as e:
            self.logger.error(f"Error handling client: {e}")
        finally:
            self.connected_clients.discard(websocket)
    
    async def _process_message(self, websocket, raw_message: str):
        """Process incoming message from Electron"""
        try:
            message_data = json.loads(raw_message)
            message_type = message_data.get("type")
            
            if message_type in self.message_handlers:
                response = await self.message_handlers[message_type](message_data)
                if response:
                    await self._send_to_client(websocket, response)
            else:
                self.logger.warning(f"Unknown message type: {message_type}")
        
        except json.JSONDecodeError:
            self.logger.error("Invalid JSON received from Electron")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
    
    async def _send_to_client(self, websocket, message: Dict[str, Any]):
        """Send message to specific client"""
        try:
            await websocket.send(json.dumps(message))
        except Exception as e:
            self.logger.error(f"Error sending message to client: {e}")
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.connected_clients:
            return
        
        message_json = json.dumps(message)
        disconnected_clients = []
        
        for client in self.connected_clients:
            try:
                await client.send(message_json)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.append(client)
            except Exception as e:
                self.logger.error(f"Error broadcasting to client: {e}")
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.connected_clients.discard(client)
    
    def notify_operation_complete(self, operation_result):
        """Notify Electron of completed operation"""
        if not self.connected_clients:
            return
        
        message = {
            "type": "operation_complete",
            "payload": {
                "success": operation_result.success,
                "message": operation_result.message,
                "operation_id": operation_result.operation_id,
                "timestamp": operation_result.timestamp.isoformat() if operation_result.timestamp else None,
                "data": operation_result.data
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Use asyncio to broadcast (non-blocking)
        asyncio.create_task(self.broadcast_to_all(message))
    
    def notify_operation_error(self, operation_result):
        """Notify Electron of operation error"""
        if not self.connected_clients:
            return
        
        message = {
            "type": "operation_error",
            "payload": {
                "message": operation_result.message,
                "error_type": operation_result.error_type,
                "operation_id": operation_result.operation_id,
                "timestamp": operation_result.timestamp.isoformat() if operation_result.timestamp else None
            },
            "timestamp": datetime.now().isoformat()
        }
        
        asyncio.create_task(self.broadcast_to_all(message))
    
    def notify_progress_update(self, technique: str, step: str, completed: bool):
        """Notify Electron of progress update"""
        if not self.connected_clients:
            return
        
        message = {
            "type": "progress_update",
            "payload": {
                "technique": technique,
                "step": step,
                "completed": completed
            },
            "timestamp": datetime.now().isoformat()
        }
        
        asyncio.create_task(self.broadcast_to_all(message))
    
    def notify_data_upload(self, filename: str, file_size: int, technique: str):
        """Notify Electron of data upload"""
        if not self.connected_clients:
            return
        
        message = {
            "type": "data_upload",
            "payload": {
                "filename": filename,
                "file_size": file_size,
                "technique": technique
            },
            "timestamp": datetime.now().isoformat()
        }
        
        asyncio.create_task(self.broadcast_to_all(message))
    
    def _setup_default_handlers(self):
        """Setup default message handlers"""
        
        async def handle_ping(message_data):
            return {
                "type": "pong",
                "payload": {"timestamp": datetime.now().isoformat()}
            }
        
        async def handle_get_status(message_data):
            return {
                "type": "status_response",
                "payload": {
                    "connected_clients": len(self.connected_clients),
                    "server_running": self.websocket_server is not None
                }
            }
        
        async def handle_ui_state_change(message_data):
            """Handle UI state changes from Electron"""
            self.logger.info(f"UI state change: {message_data.get('payload', {})}")
            # Broadcast to other clients for state synchronization
            await self.broadcast_to_all(message_data)
        
        self.message_handlers = {
            "ping": handle_ping,
            "get_status": handle_get_status,
            "ui_state_change": handle_ui_state_change
        }
    
    def register_handler(self, message_type: str, handler: Callable):
        """Register custom message handler"""
        self.message_handlers[message_type] = handler
    
    def is_connected(self) -> bool:
        """Check if any Electron clients are connected"""
        return len(self.connected_clients) > 0
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information"""
        return {
            "connected_clients": len(self.connected_clients),
            "websocket_port": self.websocket_port,
            "server_running": self.websocket_server is not None
        }


def main():
    """Test Electron bridge functionality"""
    import asyncio
    
    async def test_bridge():
        bridge = ElectronBridge(websocket_port=8766)  # Use different port for testing
        
        # Test server start/stop
        await bridge.start_server()
        assert bridge.websocket_server is not None
        
        # Test connection info
        info = bridge.get_connection_info()
        assert info["websocket_port"] == 8766
        assert info["server_running"] is True
        
        await bridge.stop_server()
        print("✅ Electron bridge tests passed")
    
    # Run async test
    asyncio.run(test_bridge())


if __name__ == "__main__":
    main()