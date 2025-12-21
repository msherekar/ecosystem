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
        client = MockElectronClient(f"ws://localhost:{self.bridge.websocket_port}")
        await client.connect()
        self.mock_clients.append(client)
        
        # Test tool registration
        tool_result = await client.register_tool("test_tool", "Test tool description")
        assert tool_result["success"], "Should register tool successfully"
        assert tool_result["tool_id"] == "test_tool", "Should return correct tool ID"
        
        print("   ✅ Handler integration tests passed")



        # =============================================================================
    # 6. BROADCAST TESTING
    # =============================================================================
    
    async def test_broadcast_to_multiple_clients(self):
        """Test broadcasting messages to multiple Electron clients"""
        print("📢 Testing Broadcast to Multiple Clients...")
        
        if not self.bridge:
            self.bridge = ElectronBridge(websocket_port=8779)
            await self.bridge.start_server()
            await asyncio.sleep(0.5)
        
        # Connect multiple clients
        clients = []
        for i in range(3):
            client = MockElectronClient(f"ws://localhost:{self.bridge.websocket_port}")
            await client.connect()
            clients.append(client)
        
        self.mock_clients.extend(clients)
        
        # Start receiving messages on all clients
        receive_tasks = [
            asyncio.create_task(client.receive_messages(timeout=2.0))
            for client in clients
        ]
        
        # Broadcast a message
        await asyncio.sleep(0.5)
        
        broadcast_message = {
            "type": "system_notification",
            "payload": {
                "message": "System maintenance scheduled",
                "priority": "low"
            }
        }
        
        await self.bridge.broadcast_to_all(broadcast_message)
        await asyncio.sleep(0.5)
        
        # Wait for all clients to receive messages
        await asyncio.gather(*receive_tasks)
        
        # Verify all clients received the broadcast
        for i, client in enumerate(clients):
            broadcast_messages = [
                msg for msg in client.received_messages 
                if msg.get("type") == "system_notification"
            ]
            assert len(broadcast_messages) >= 1, f"Client {i} should receive broadcast"
            assert broadcast_messages[0]["payload"]["message"] == "System maintenance scheduled"
        
        print(f"   ✅ Message broadcast to {len(clients)} clients successfully")

    # =============================================================================
    # 7. PERFORMANCE TESTING
    # =============================================================================
    
    async def test_websocket_performance(self):
        """Test WebSocket performance under load"""
        print("⚡ Testing WebSocket Performance...")
        
        if not self.bridge:
            self.bridge = ElectronBridge(websocket_port=8780)
            await self.bridge.start_server()
            await asyncio.sleep(0.5)
        
        # Connect client
        client = MockElectronClient(f"ws://localhost:{self.bridge.websocket_port}")
        await client.connect()
        self.mock_clients.append(client)
        
        # Test message throughput
        start_time = time.time()
        
        # Send multiple progress updates rapidly
        for i in range(50):
            self.bridge.notify_progress_update("scRNA-seq", f"step_{i}", i % 2 == 0)
            if i % 10 == 0:
                await asyncio.sleep(0.01)  # Small delay every 10 messages
        
        # Start receiving messages
        receive_task = asyncio.create_task(client.receive_messages(timeout=3.0))
        await receive_task
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Verify performance
        progress_messages = [
            msg for msg in client.received_messages 
            if msg.get("type") == "progress_update"
        ]
        
        messages_per_second = len(progress_messages) / duration
        
        assert messages_per_second > 10, f"Message throughput too low: {messages_per_second:.1f} msg/s"
        assert len(progress_messages) >= 45, f"Should receive most messages, got {len(progress_messages)}/50"
        
        print(f"   ✅ Performance test passed ({messages_per_second:.1f} msg/s)")

    # =============================================================================
    # MAIN TEST RUNNER
    # =============================================================================
    
    async def run_all_tests(self):
        """Run all Electron WebSocket communication tests"""
        print("🧪 Electron WebSocket Communication Testing Suite")
        print("="*55)
        
        start_time = time.time()
        tests_passed = 0
        tests_failed = 0
        
        test_methods = [
            self.test_websocket_server_startup,
            self.test_multiple_client_connections,
            self.test_ping_pong_communication,
            self.test_status_request_handling,
            self.test_progress_updates,
            self.test_operation_completion_notifications,
            self.test_error_notifications,
            self.test_connection_resilience,
            self.test_handler_integration,
            self.test_broadcast_to_multiple_clients,
            self.test_websocket_performance
        ]
        
        for test_method in test_methods:
            try:
                await test_method()
                tests_passed += 1
            except Exception as e:
                tests_failed += 1
                self.logger.error(f"Test {test_method.__name__} failed: {e}")
                import traceback
                traceback.print_exc()
            finally:
                # Clean up between tests
                for client in self.mock_clients:
                    if client.is_connected:
                        await client.disconnect()
                self.mock_clients.clear()
                
                if self.bridge:
                    await self.bridge.stop_server()
                    self.bridge = None
                
                await asyncio.sleep(0.2)  # Small delay between tests
        
        execution_time = time.time() - start_time
        
        print("\n" + "="*55)
        print("🎯 ELECTRON WEBSOCKET TEST SUMMARY")
        print("="*55)
        
        if tests_failed == 0:
            print("🎉 ALL WEBSOCKET TESTS PASSED!")
        else:
            print(f"⚠️  {tests_failed} TEST(S) FAILED")
        
        print(f"📊 Tests: {tests_passed}/{tests_passed + tests_failed} passed")
        print(f"⏱️  Execution time: {execution_time:.2f}s")
        print("="*55)
        
        await self.cleanup()
        return tests_failed == 0


# =============================================================================
# PYTEST INTEGRATION
# =============================================================================

@pytest.mark.asyncio
async def test_websocket_server_startup():
    """Pytest wrapper for WebSocket server startup testing"""
    tester = ElectronWebSocketTester()
    try:
        await tester.test_websocket_server_startup()
    finally:
        await tester.cleanup()

@pytest.mark.asyncio
async def test_progress_updates():
    """Pytest wrapper for progress update testing"""
    tester = ElectronWebSocketTester()
    try:
        await tester.test_progress_updates()
    finally:
        await tester.cleanup()

@pytest.mark.asyncio
async def test_error_notifications():
    """Pytest wrapper for error notification testing"""
    tester = ElectronWebSocketTester()
    try:
        await tester.test_error_notifications()
    finally:
        await tester.cleanup()

@pytest.mark.asyncio
async def test_handler_integration():
    """Pytest wrapper for handler integration testing"""
    tester = ElectronWebSocketTester()
    try:
        await tester.test_handler_integration()
    finally:
        await tester.cleanup()


def main():
    """Run Electron WebSocket communication tests"""
    async def run_tests():
        tester = ElectronWebSocketTester()
        try:
            return await tester.run_all_tests()
        except Exception as e:
            print(f"Test suite failed: {e}")
            return False
        finally:
            await tester.cleanup()
    
    success = asyncio.run(run_tests())
    return success


if __name__ == "__main__":
    main()
 
    

        

        

    




                                                      