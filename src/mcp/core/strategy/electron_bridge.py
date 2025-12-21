"""
Electron Bridge Module

Provides seamless integration between Python backend and
Electron frontend for bioinformatics analysis UI.
"""

import json
import asyncio
import websockets
import threading
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ElectronBridge:
    """Bridge for Electron frontend communication"""
    
    def __init__(self):
        """Initialize ElectronBridge"""
        self.host = "localhost"
        self.port = 8765
        self.is_running = False
        self.server = None
        self.clients = {}
        self.stats = {
            "connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0
        }
        self.message_handlers = {
            "ping": self._handle_ping,
            "get_strategies": self._handle_get_strategies,
            "get_actions": self._handle_get_actions,
            "get_insights": self._handle_get_insights,
            "get_workflow": self._handle_get_workflow,
            "system_status": self._handle_system_status,
            "file_upload": self._handle_file_upload
        }
    
    def initialize(self, host: str = "localhost", port: int = 8765):
        """Initialize Electron bridge configuration"""
        self.host = host
        self.port = port
        logger.info(f"Electron bridge initialized on {host}:{port}")
    
    def register_handler(self, message_type: str, handler: Callable):
        """Register custom message handler"""
        self.message_handlers[message_type] = handler
        logger.info(f"Registered handler for message type: {message_type}")
    
    async def handle_client(self, websocket, path):
        """Handle individual client connections"""
        client_id = f"client_{len(self.clients)}"
        self.clients[client_id] = websocket
        self.stats["connections"] += 1
        
        logger.info(f"Client {client_id} connected from {websocket.remote_address}")
        
        try:
            await websocket.send(json.dumps({
                "type": "connection_established",
                "client_id": client_id,
                "timestamp": datetime.now().isoformat()
            }))
            
            async for message in websocket:
                await self._process_message(client_id, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
            self.stats["errors"] += 1
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
    
    async def _process_message(self, client_id: str, message: str):
        """Process incoming message from client"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            message_id = data.get("id", "unknown")
            
            self.stats["messages_received"] += 1
            
            if message_type in self.message_handlers:
                response = await self.message_handlers[message_type](data)
                response["id"] = message_id
                response["timestamp"] = datetime.now().isoformat()
                
                await self.send_to_client(client_id, response)
            else:
                await self.send_error(client_id, f"Unknown message type: {message_type}", message_id)
                
        except json.JSONDecodeError:
            await self.send_error(client_id, "Invalid JSON format")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.send_error(client_id, str(e))
    
    async def send_to_client(self, client_id: str, data: Dict[str, Any]):
        """Send data to specific client"""
        if client_id in self.clients:
            try:
                await self.clients[client_id].send(json.dumps(data))
                self.stats["messages_sent"] += 1
            except Exception as e:
                logger.error(f"Error sending to client {client_id}: {e}")
                self.stats["errors"] += 1
    
    async def broadcast(self, data: Dict[str, Any]):
        """Broadcast data to all connected clients"""
        if self.clients:
            message = json.dumps(data)
            await asyncio.gather(
                *[client.send(message) for client in self.clients.values()],
                return_exceptions=True
            )
            self.stats["messages_sent"] += len(self.clients)
    
    async def send_error(self, client_id: str, error: str, message_id: str = "unknown"):
        """Send error response to client"""
        error_response = {
            "type": "error",
            "error": error,
            "id": message_id,
            "timestamp": datetime.now().isoformat()
        }
        await self.send_to_client(client_id, error_response)
    
    # Default message handlers
    async def _handle_ping(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ping message"""
        return {
            "type": "pong",
            "timestamp": datetime.now().isoformat(),
            "server_time": datetime.now().isoformat()
        }
    
    async def _handle_get_strategies(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get strategies request"""
        from .factory import strategy_registry
        
        return {
            "type": "strategies_response",
            "strategies": strategy_registry.get_available_strategies()
        }
    
    async def _handle_get_actions(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get actions request"""
        from .__main__ import get_orchestrator
        
        try:
            orchestrator = get_orchestrator()
            analysis_type = data.get("analysis_type", "")
            context = data.get("context", {})
            session_id = data.get("session_id")
            
            actions = orchestrator.get_actions(analysis_type, context, session_id)
            
            return {
                "type": "actions_response",
                "actions": actions,
                "analysis_type": analysis_type
            }
        except Exception as e:
            return {
                "type": "error",
                "error": str(e)
            }
    
    async def _handle_get_insights(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get insights request"""
        from .__main__ import get_orchestrator
        
        try:
            orchestrator = get_orchestrator()
            analysis_type = data.get("analysis_type", "")
            context = data.get("context", {})
            session_id = data.get("session_id")
            
            insights = orchestrator.get_insights(analysis_type, context, session_id)
            
            return {
                "type": "insights_response",
                "insights": insights,
                "analysis_type": analysis_type
            }
        except Exception as e:
            return {
                "type": "error",
                "error": str(e)
            }
    
    async def _handle_get_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get workflow request"""
        from .__main__ import get_orchestrator
        
        try:
            orchestrator = get_orchestrator()
            analysis_type = data.get("analysis_type", "")
            
            workflow_steps = orchestrator.get_workflow_steps(analysis_type)
            
            return {
                "type": "workflow_response",
                "workflow_steps": workflow_steps,
                "analysis_type": analysis_type
            }
        except Exception as e:
            return {
                "type": "error",
                "error": str(e)
            }
    
    async def _handle_system_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system status request"""
        from .__main__ import get_orchestrator
        
        try:
            orchestrator = get_orchestrator()
            status = orchestrator.get_system_status()
            status.update({"bridge_stats": self.stats})
            
            return {
                "type": "system_status_response",
                "status": status
            }
        except Exception as e:
            return {
                "type": "error",
                "error": str(e)
            }
    
    async def _handle_file_upload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file upload notification"""
        try:
            file_path = data.get("file_path", "")
            file_type = data.get("file_type", "")
            session_id = data.get("session_id", "")
            
            # Validate file path
            from .security import SecurityManager
            security = SecurityManager()
            
            if not security.validate_file_path(file_path):
                return {
                    "type": "error",
                    "error": "Invalid file path or type"
                }
            
            return {
                "type": "file_upload_response",
                "status": "success",
                "file_path": file_path,
                "session_id": session_id
            }
            
        except Exception as e:
            return {
                "type": "error",
                "error": str(e)
            }
    
    def start_server(self, host: Optional[str] = None, port: Optional[int] = None):
        """Start WebSocket server in background thread"""
        if host:
            self.host = host
        if port:
            self.port = port
        
        def run_server():
            """Run server in thread"""
            asyncio.set_event_loop(asyncio.new_event_loop())
            loop = asyncio.get_event_loop()
            
            start_server = websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                ping_interval=30,
                ping_timeout=10
            )
            
            self.server = loop.run_until_complete(start_server)
            self.is_running = True
            
            logger.info(f"Electron bridge server started on {self.host}:{self.port}")
            
            try:
                loop.run_forever()
            except KeyboardInterrupt:
                logger.info("Server stopped by user")
            finally:
                self.is_running = False
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        return server_thread
    
    def stop_server(self):
        """Stop WebSocket server"""
        if self.server:
            self.server.close()
            self.is_running = False
            logger.info("Electron bridge server stopped")
    
    def get_status(self) -> str:
        """Get bridge status"""
        return "running" if self.is_running else "stopped"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bridge statistics"""
        return {
            **self.stats,
            "active_clients": len(self.clients),
            "is_running": self.is_running,
            "host": self.host,
            "port": self.port
        }
    
    def cleanup(self):
        """Clean up resources"""
        self.stop_server()
        self.clients.clear()
        logger.info("Electron bridge cleaned up")


class ElectronAPI:
    """High-level API for Electron integration"""
    
    def __init__(self, bridge: ElectronBridge):
        self.bridge = bridge
    
    async def notify_progress(self, session_id: str, step: str, progress: float, message: str = ""):
        """Notify frontend of analysis progress"""
        notification = {
            "type": "progress_update",
            "session_id": session_id,
            "step": step,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        await self.bridge.broadcast(notification)
    
    async def notify_completion(self, session_id: str, analysis_type: str, results: Dict[str, Any]):
        """Notify frontend of analysis completion"""
        notification = {
            "type": "analysis_complete",
            "session_id": session_id,
            "analysis_type": analysis_type,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        await self.bridge.broadcast(notification)
    
    async def notify_error(self, session_id: str, error: str, details: str = ""):
        """Notify frontend of errors"""
        notification = {
            "type": "analysis_error",
            "session_id": session_id,
            "error": error,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        await self.bridge.broadcast(notification)


def main():
    """Test Electron bridge functionality"""
    print("Testing Electron Bridge...")
    
    bridge = ElectronBridge()
    
    # Test initialization
    bridge.initialize("localhost", 8765)
    assert bridge.host == "localhost", "Host should be set"
    assert bridge.port == 8765, "Port should be set"
    print("✅ Bridge initialization passed")
    
    # Test handler registration
    def test_handler(data):
        return {"type": "test_response", "data": data}
    
    bridge.register_handler("test", test_handler)
    assert "test" in bridge.message_handlers, "Handler should be registered"
    print("✅ Handler registration passed")
    
    # Test message processing (without actual WebSocket)
    import asyncio
    
    async def test_message_handlers():
        # Test ping handler
        ping_response = await bridge._handle_ping({})
        assert ping_response["type"] == "pong", "Ping should return pong"
        
        # Test strategies handler
        strategies_response = await bridge._handle_get_strategies({})
        assert strategies_response["type"] == "strategies_response", "Should return strategies"
        
        print("✅ Message handlers passed")
    
    asyncio.run(test_message_handlers())
    
    # Test stats
    stats = bridge.get_stats()
    assert "active_clients" in stats, "Stats should include client count"
    assert "is_running" in stats, "Stats should include running status"
    print("✅ Stats functionality passed")
    
    print("🎉 All Electron bridge tests passed!")


if __name__ == "__main__":
    def test_static_electron():
        """Static Electron bridge tests"""
        print("Running static Electron tests...")
        
        bridge = ElectronBridge()
        
        # Test initial state
        assert not bridge.is_running, "Should not be running initially"
        assert len(bridge.clients) == 0, "Should have no clients initially"
        assert len(bridge.message_handlers) > 0, "Should have default handlers"
        
        print("✅ Static Electron tests passed!")
    
    def test_dynamic_electron():
        """Dynamic Electron bridge tests"""
        print("Running dynamic Electron tests...")
        
        # Run main tests
        main()
        
        print("✅ Dynamic Electron tests passed!")
    
    # Run tests
    test_static_electron()
    test_dynamic_electron() 
    
    