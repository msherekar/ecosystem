"""
Electron WebSocket Communication Testing

Comprehensive testing for real-time communication between Python handlers
and Electron frontend via WebSocket bridge.
"""

import asyncio
import pytest
import logging
import json
import time
import threading
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch
import websockets
from datetime import datetime

# Import Electron and handler components
from ..electron_bridge import ElectronBridge, ElectronMessage
from ..base_handler import OperationResult
from .. import create_handler


class MockElectronClient:
    """Mock Electron client for testing WebSocket communication"""
    
    def __init__(self, uri: str):
        self.uri = uri
        self.websocket = None
        self.received_messages = []
        self.is_connected = False
        self.connection_event = asyncio.Event()
    
    async def connect(self):
        """Connect to WebSocket server"""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.is_connected = True
            self.connection_event.set()
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    async def send_message(self, message: Dict[str, Any]):
        """Send message to server"""
        if self.websocket and self.is_connected:
            await self.websocket.send(json.dumps(message))
    
    async def receive_messages(self, timeout: float = 5.0):
        """Receive messages for specified duration"""
        if not self.websocket or not self.is_connected:
            return
        
        end_time = time.time() + timeout
        
        try:
            while time.time() < end_time:
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(), 
                        timeout=0.1
                    )
                    self.received_messages.append(json.loads(message))
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    break
        except Exception as e:
            print(f"Error receiving messages: {e}")
    
    async def disconnect(self):
        """Disconnect from server"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False


class ElectronWebSocketTester:
    """Comprehensive Electron WebSocket communication testing"""
    
    def __init__(self):
        self.logger = logging.getLogger("electron.websocket.test")
        self.setup_logging()
        self.bridge = None
        self.mock_clients = []
    
    def setup_logging(self):
        """Setup test logging"""
        logging.basicConfig(level=logging.INFO)
    
    async def cleanup(self):
        """Cleanup test resources"""
        # Disconnect mock clients
        for client in self.mock_clients:
            if client.is_connected:
                await client.disconnect()
        
        # Stop WebSocket server
        if self.bridge:
            await self.bridge.stop_server()

    # =============================================================================
    # 1. WEBSOCKET SERVER TESTING
    # =============================================================================
    
    async def test_websocket_server_startup(self):
        """Test WebSocket server starts and accepts connections"""
        print("🌐 Testing WebSocket Server Startup...")
        
        # Start WebSocket server
        self.bridge = ElectronBridge(websocket_port=8770)  # Test port
        await self.bridge.start_server()
        
        # Wait for server to be ready
        await asyncio.sleep(0.5)
        
        # Test connection
        client = MockElectronClient("ws://localhost:8770")
        connection_success = await client.connect()
        
        assert connection_success, "Should be able to connect to WebSocket server"
        assert client.is_connected, "Client should be connected"
        
        self.mock_clients.append(client)
        print("   ✅ WebSocket server startup tests passed")
    
    async def test_multiple_client_connections(self):
        """Test multiple Electron clients can connect simultaneously"""
        print("👥 Testing Multiple Client Connections...")
        
        if not self.bridge:
            self.bridge = ElectronBridge(websocket_port=8771)
            await self.bridge.start_server()
            await asyncio.sleep(0.5)
        
        # Connect multiple clients
        clients = []
        for i in range(3):
            client = MockElectronClient(f"ws://localhost:{self.bridge.websocket_port}")
            success = await client.connect()
            assert success, f"Client {i} should connect successfully"
            clients.append(client)
        
        self.mock_clients.extend(clients)
        
        # Verify all are connected
        assert len(self.bridge.connected_clients) == len(clients), "All clients should be tracked"
        
        print(f"   ✅ {len(clients)} clients connected successfully")

    # =============================================================================
    # 2. MESSAGE HANDLING TESTING
    # =============================================================================
    
    async def test_ping_pong_communication(self):
        """Test basic ping-pong communication"""
        print("🏓 Testing Ping-Pong Communication...")
        
        if not self.bridge:
            self.bridge = ElectronBridge(websocket_port=8772)
            await self.bridge.start_server()
            await asyncio.sleep(0.5)
        
        # Connect client
        client = MockElectronClient(f"ws://localhost:{self.bridge.websocket_port}")
        await client.connect()
        self.mock_clients.append(client)
        
        # Send ping message
        ping_message = {
            "type": "ping",
            "payload": {"timestamp": datetime.now().isoformat()}
        }
        
        await client.send_message(ping_message)
        
        # Receive response
        await client.receive_messages(timeout=2.0)
        
        # Verify pong response
        assert len(client.received_messages) > 0, "Should receive pong response"
        
        pong_message = client.received_messages[0]
        assert pong_message["type"] == "pong", "Should receive pong message"
        assert "timestamp" in pong_message["payload"], "Pong should include timestamp"
        
        print("   ✅ Ping-pong communication tests passed")
    
    async def test_status_request_handling(self):
        """Test status request handling"""
        print("📊 Testing Status Request Handling...")
        
        if not self.bridge:
            self.bridge = ElectronBridge(websocket_port=8773)
            await self.bridge.start_server()
            await asyncio.sleep(0.5)
        
        # Connect client
        client = MockElectronClient(f"ws://localhost:{self.bridge.websocket_port}")
        await client.connect()
        self.mock_clients.append(client)
        
        # Send status request
        status_message = {
            "type": "get_status",
            "payload": {}
        }
        
        await client.send_message(status_message)
        await client.receive_messages(timeout=2.0)
        
        # Verify status response
        assert len(client.received_messages) > 0, "Should receive status response"
        
        status_response = client.received_messages[0]
        assert status_response["type"] == "status_response", "Should receive status response"
        assert "connected_clients" in status_response["payload"], "Should include client count"
        assert "server_running" in status_response["payload"], "Should include server status"
        
        print("   ✅ Status request handling tests passed")

    # =============================================================================
    # 3. PROGRESS UPDATE TESTING
    # =============================================================================
    
    async def test_progress_updates(self):
        """Test progress updates broadcast to Electron clients"""
        print("📈 Testing Progress Updates...")
        
        if not self.bridge:
            self.bridge = ElectronBridge(websocket_port=8774)
            await self.bridge.start_server()
            await asyncio.sleep(0.5)
        
        # Connect client
        client = MockElectronClient(f"ws://localhost:{self.bridge.websocket_port}")
        await client.connect()
        self.mock_clients.append(client)
        
        # Start receiving messages
        receive_task = asyncio.create_task(client.receive_messages(timeout=3.0))
        
        # Send progress updates
        await asyncio.sleep(0.5)  # Let client start receiving
        
        self.bridge.notify_progress_update("scRNA-seq", "qc", False)
        await asyncio.sleep(0.2)
        
        self.bridge.notify_progress_update("scRNA-seq", "qc", True)
        await asyncio.sleep(0.2)
        
        self.bridge.notify_progress_update("scRNA-seq", "clustering", False)
        await asyncio.sleep(0.2)
        
        # Wait for messages to be received
        await receive_task
        
        # Verify progress messages
        progress_messages = [
            msg for msg in client.received_messages 
            if msg.get("type") == "progress_update"
        ]
        
        assert len(progress_messages) >= 3, f"Should receive 3 progress updates, got {len(progress_messages)}"
        
        # Verify message structure
        for msg in progress_messages:
            assert "payload" in msg, "Progress message should have payload"
            assert "technique" in msg["payload"], "Should include technique"
            assert "step" in msg["payload"], "Should include step"
            assert "completed" in msg["payload"], "Should include completion status"
        
        print(f"   ✅ {len(progress_messages)} progress updates received")
    
    async def test_operation_completion_notifications(self):
        """Test operation completion notifications"""
        print("✅ Testing Operation Completion Notifications...")
        
        if not self.bridge:
            self.bridge = ElectronBridge(websocket_port=8775)
            await self.bridge.start_server()
            await asyncio.sleep(0.5)
        
        # Connect client
        client = MockElectronClient(f"ws://localhost:{self.bridge.websocket_port}")
        await client.connect()
        self.mock_clients.append(client)
        
        # Start receiving messages
        receive_task = asyncio.create_task(client.receive_messages(timeout=2.0))
        
        # Send operation completion
        await asyncio.sleep(0.5)
        
        operation_result = OperationResult(
            success=True,
            message="QC completed successfully",
            operation_id="qc_12345",
            timestamp=datetime.now(),
            data={"cells_filtered": 100, "genes_filtered": 200}
        )
        
        self.bridge.notify_operation_complete(operation_result)
        await asyncio.sleep(0.5)
        
        # Wait for messages
        await receive_task
        
        # Verify completion message
        completion_messages = [
            msg for msg in client.received_messages 
            if msg.get("type") == "operation_complete"
        ]
        
        assert len(completion_messages) >= 1, "Should receive operation completion"
        
        completion_msg = completion_messages[0]
        assert completion_msg["payload"]["success"] is True, "Should indicate success"
        assert completion_msg["payload"]["operation_id"] == "qc_12345", "Should include operation ID"
        assert "data" in completion_msg["payload"], "Should include operation data"
        
        print("   ✅ Operation completion notifications working")

    # =============================================================================
    # 4. ERROR HANDLING TESTING
    # =============================================================================
    
    async def test_error_notifications(self):
        """Test error notifications to Electron clients"""
        print("🚨 Testing Error Notifications...")
        
        if not self.bridge:
            self.bridge = ElectronBridge(websocket_port=8776)
            await self.bridge.start_server()
            await asyncio.sleep(0.5)
        
        # Connect client
        client = MockElectronClient(f"ws://localhost:{self.bridge.websocket_port}")
        await client.connect()
        self.mock_clients.append(client)
        
        # Start receiving messages
        receive_task = asyncio.create_task(client.receive_messages(timeout=2.0))
        
        # Send error notification
        await asyncio.sleep(0.5)
        
        error_result = OperationResult(
            success=False,
            message="Analysis failed due to invalid data",
            error_type="data_validation_error",
            operation_id="analysis_67890",
            timestamp=datetime.now()
        )
        
        self.bridge.notify_operation_error(error_result)
        await asyncio.sleep(0.5)
        
        # Wait for messages
        await receive_task
        
        # Verify error message
        error_messages = [
            msg for msg in client.received_messages 
            if msg.get("type") == "operation_error"
        ]
        
        assert len(error_messages) >= 1, "Should receive error notification"
        
        error_msg = error_messages[0]
        assert error_msg["payload"]["message"], "Should include error message"
        assert error_msg["payload"]["error_type"] == "data_validation_error", "Should include error type"
        assert error_msg["payload"]["operation_id"] == "analysis_67890", "Should include operation ID"
        
        print("   ✅ Error notifications working")
    
    async def test_connection_resilience(self):
        """Test connection resilience and reconnection"""
        print("🔄 Testing Connection Resilience...")
        
        if not self.bridge:
            self.bridge = ElectronBridge(websocket_port=8777)
            await self.bridge.start_server()
            await asyncio.sleep(0.5)
        
        # Connect client
        client = MockElectronClient(f"ws://localhost:{self.bridge.websocket_port}")
        await client.connect()
        
        initial_client_count = len(self.bridge.connected_clients)
        
        # Disconnect client
        await client.disconnect()
        await asyncio.sleep(0.5)
        
        # Verify client was removed from server
        final_client_count = len(self.bridge.connected_clients)
        assert final_client_count < initial_client_count, "Disconnected client should be removed"
        
        # Test reconnection
        reconnect_success = await client.connect()
        assert reconnect_success, "Should be able to reconnect"
        
        self.mock_clients.append(client)
        print("   ✅ Connection resilience tests passed")

    # =============================================================================
    # 5. HANDLER INTEGRATION TESTING
    # =============================================================================
    
    async def test_handler_integration(self):
        """Test handlers can communicate with Electron via bridge"""
        print("🔗 Testing Handler Integration...")
        
        if not self.bridge:
            self.bridge = ElectronBridge(websocket_port=8778)
            await self.bridge.start_server()
            await asyncio.sleep(0.5)
        
        # Connect client
        client = MockElectronClient(f"ws://localhost:{self.bridge.websocket_port