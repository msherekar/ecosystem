"""
Electron Bridge
WebSocket bridge for Electron UI integration with security.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
import time
import uuid
from pathlib import Path


@dataclass
class ElectronConfig:
    """Configuration for Electron bridge."""
    host: str = "localhost"
    port: int = 8080
    max_connections: int = 10
    message_timeout: float = 30.0
    heartbeat_interval: float = 30.0
    enable_cors: bool = True
    allowed_origins: List[str] = None
    
    def __post_init__(self):
        if self.allowed_origins is None:
            self.allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]


class ElectronBridge:
    """WebSocket bridge for Electron frontend communication."""
    
    def __init__(self, config: ElectronConfig = None, coordinator=None):
        self.config = config or ElectronConfig()
        self.coordinator = coordinator
        self.logger = logging.getLogger("electron_bridge")
        
        # Connection management
        self.active_connections: Dict[str, Any] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.server = None
        self.shutdown_event = asyncio.Event()
        
        # Security
        self.session_tokens: Dict[str, Dict[str, Any]] = {}
        
        # Metrics
        self.metrics = {
            'connections_total': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'errors': 0,
            'uptime_start': time.time()
        }
        
        # Register default handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default message handlers."""
        self.register_handler('chat', self._handle_chat)
        self.register_handler('status', self._handle_status)
        self.register_handler('ping', self._handle_ping)
        self.register_handler('authenticate', self._handle_authenticate)
    
    def register_handler(self, message_type: str, handler: Callable):
        """Register a message handler."""
        self.message_handlers[message_type] = handler
        self.logger.debug(f"Registered handler for {message_type}")
    
    async def start(self) -> bool:
        """Start the Electron WebSocket bridge."""
        try:
            import websockets
            from websockets.server import serve
            
            self.logger.info(f"Starting Electron bridge on {self.config.host}:{self.config.port}")
            
            self.server = await serve(
                self._handle_connection,
                self.config.host,
                self.config.port,
                max_size=1024*1024,  # 1MB max message size
                ping_interval=self.config.heartbeat_interval,
                ping_timeout=self.config.heartbeat_interval * 2
            )
            
            self.logger.info("Electron bridge started successfully")
            return True
            
        except ImportError:
            self.logger.error("websockets library not available")
            return False
        except Exception as e:
            self.logger.error(f"Failed to start Electron bridge: {e}")
            return False
    
    async def _handle_connection(self, websocket, path):
        """Handle new WebSocket connection."""
        connection_id = str(uuid.uuid4())
        client_info = {
            'id': connection_id,
            'websocket': websocket,
            'connected_at': time.time(),
            'authenticated': False,
            'last_activity': time.time()
        }
        
        self.active_connections[connection_id] = client_info
        self.metrics['connections_total'] += 1
        
        self.logger.info(f"New Electron connection: {connection_id}")
        
        try:
            # Send welcome message
            await self._send_message(websocket, {
                'type': 'welcome',
                'connection_id': connection_id,
                'timestamp': time.time()
            })
            
            # Handle messages
            async for message in websocket:
                await self._process_message(connection_id, message)
                
        except Exception as e:
            self.logger.error(f"Connection error for {connection_id}: {e}")
            self.metrics['errors'] += 1
        finally:
            # Cleanup connection
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
            self.logger.info(f"Electron connection closed: {connection_id}")
    
    async def _process_message(self, connection_id: str, raw_message: str):
        """Process incoming message from Electron."""
        try:
            message = json.loads(raw_message)
            message_type = message.get('type')
            
            if not message_type:
                await self._send_error(connection_id, "Missing message type")
                return
            
            # Update activity
            if connection_id in self.active_connections:
                self.active_connections[connection_id]['last_activity'] = time.time()
            
            # Check authentication for protected handlers
            if message_type not in ['authenticate', 'ping'] and not self._is_authenticated(connection_id):
                await self._send_error(connection_id, "Authentication required")
                return
            
            # Route to handler
            handler = self.message_handlers.get(message_type)
            if handler:
                await handler(connection_id, message)
                self.metrics['messages_received'] += 1
            else:
                await self._send_error(connection_id, f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await self._send_error(connection_id, "Invalid JSON message")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            await self._send_error(connection_id, "Internal server error")
    
    def _is_authenticated(self, connection_id: str) -> bool:
        """Check if connection is authenticated."""
        if connection_id not in self.active_connections:
            return False
        return self.active_connections[connection_id].get('authenticated', False)
    
    async def _handle_authenticate(self, connection_id: str, message: Dict[str, Any]):
        """Handle authentication request."""
        # For demo purposes, simple token-based auth
        token = message.get('token')
        
        if token and token.startswith('electron_'):
            # Generate session
            session_id = str(uuid.uuid4())
            self.session_tokens[session_id] = {
                'connection_id': connection_id,
                'created_at': time.time(),
                'token': token
            }
            
            # Mark connection as authenticated
            if connection_id in self.active_connections:
                self.active_connections[connection_id]['authenticated'] = True
                self.active_connections[connection_id]['session_id'] = session_id
            
            await self._send_message_to_connection(connection_id, {
                'type': 'auth_success',
                'session_id': session_id
            })
        else:
            await self._send_error(connection_id, "Invalid authentication token")
    
    async def _handle_chat(self, connection_id: str, message: Dict[str, Any]):
        """Handle chat request from Electron."""
        if not self.coordinator:
            await self._send_error(connection_id, "Coordinator not available")
            return
        
        try:
            user_message = message.get('message', '')
            context = message.get('context', {})
            
            # Add connection context
            context['electron_connection_id'] = connection_id
            context['source'] = 'electron'
            
            response, flags, metadata = await self.coordinator.chat(
                user_message, 
                context=context,
                client_id=f'electron_{connection_id}'
            )
            
            await self._send_message_to_connection(connection_id, {
                'type': 'chat_response',
                'data': {
                    'response': response,
                    'flags': flags,
                    'metadata': metadata
                }
            })
            
        except Exception as e:
            self.logger.error(f"Chat error: {e}")
            await self._send_error(connection_id, f"Chat failed: {str(e)}")
    
    async def _handle_status(self, connection_id: str, message: Dict[str, Any]):
        """Handle status request."""
        if not self.coordinator:
            status = {"error": "Coordinator not available"}
        else:
            status = self.coordinator.get_status()
            # Add bridge status
            status['electron_bridge'] = {
                'active_connections': len(self.active_connections),
                'metrics': self.metrics,
                'uptime': time.time() - self.metrics['uptime_start']
            }
        
        await self._send_message_to_connection(connection_id, {
            'type': 'status_response',
            'data': status
        })
    
    async def _handle_ping(self, connection_id: str, message: Dict[str, Any]):
        """Handle ping request."""
        await self._send_message_to_connection(connection_id, {
            'type': 'pong',
            'timestamp': time.time()
        })
    
    async def _send_message_to_connection(self, connection_id: str, message: Dict[str, Any]):
        """Send message to specific connection."""
        if connection_id not in self.active_connections:
            return
        
        websocket = self.active_connections[connection_id]['websocket']
        await self._send_message(websocket, message)
    
    async def _send_message(self, websocket, message: Dict[str, Any]):
        """Send message through WebSocket."""
        try:
            await websocket.send(json.dumps(message))
            self.metrics['messages_sent'] += 1
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            raise
    
    async def _send_error(self, connection_id: str, error_message: str):
        """Send error message to connection."""
        await self._send_message_to_connection(connection_id, {
            'type': 'error',
            'error': error_message,
            'timestamp': time.time()
        })
    
    async def broadcast(self, message: Dict[str, Any], authenticated_only: bool = True):
        """Broadcast message to all connected clients."""
        if not self.active_connections:
            return
        
        failed_connections = []
        
        for connection_id, client_info in self.active_connections.items():
            try:
                if authenticated_only and not client_info.get('authenticated', False):
                    continue
                
                await self._send_message(client_info['websocket'], message)
                
            except Exception as e:
                self.logger.error(f"Failed to broadcast to {connection_id}: {e}")
                failed_connections.append(connection_id)
        
        # Cleanup failed connections
        for connection_id in failed_connections:
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
    
    async def stop(self):
        """Stop the Electron bridge."""
        self.shutdown_event.set()
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # Close all connections
        for client_info in self.active_connections.values():
            try:
                await client_info['websocket'].close()
            except:
                pass
        
        self.active_connections.clear()
        self.logger.info("Electron bridge stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get bridge status."""
        return {
            'active_connections': len(self.active_connections),
            'metrics': self.metrics,
            'config': {
                'host': self.config.host,
                'port': self.config.port,
                'max_connections': self.config.max_connections
            },
            'uptime': time.time() - self.metrics['uptime_start']
        }


def main():
    """Test the Electron bridge individually."""
    import asyncio
    
    async def test_electron_bridge():
        print("🧪 Testing ElectronBridge...")
        
        # Create bridge
        config = ElectronConfig(port=8081)  # Use different port for testing
        bridge = ElectronBridge(config)
        print("✅ Bridge initialized")
        
        # Test handler registration
        async def custom_handler(connection_id, message):
            print(f"Custom handler called for {connection_id}")
        
        bridge.register_handler('test', custom_handler)
        print("✅ Custom handler registered")
        
        # Test status
        status = bridge.get_status()
        print(f"✅ Status check: {status['active_connections']} connections")
        
        # Start bridge (will fail without websockets in some environments)
        try:
            success = await bridge.start()
            print(f"✅ Bridge start: {success}")
            
            if success:
                # Wait a bit then stop
                await asyncio.sleep(1)
                await bridge.stop()
                print("✅ Bridge stopped")
        except Exception as e:
            print(f"⚠️  Bridge start failed (expected in some environments): {e}")
        
        print("🎉 Electron bridge tests completed!")
    
    # Run tests
    asyncio.run(test_electron_bridge())


if __name__ == "__main__":
    main() 