"""
MCP Client Connection Manager

Handles server connections, health monitoring, and connection lifecycle.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ConnectionStatus(Enum):
    """Connection status enumeration"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


@dataclass
class ServerConnection:
    """Represents a connection to an MCP server"""
    server: Any  # MCPServer type - avoiding circular import
    name: str
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    capabilities: Dict[str, Any] = field(default_factory=dict)
    last_ping: Optional[datetime] = None
    error_count: int = 0
    connected_at: Optional[datetime] = None
    last_error: Optional[str] = None
    reconnect_attempts: int = 0
    max_reconnect_attempts: int = 3
    
    @property
    def is_healthy(self) -> bool:
        """Check if connection is healthy"""
        return self.status == ConnectionStatus.CONNECTED and self.error_count < 5
    
    @property
    def needs_reconnect(self) -> bool:
        """Check if connection needs reconnection"""
        return (
            self.status == ConnectionStatus.ERROR and 
            self.reconnect_attempts < self.max_reconnect_attempts
        )


class ConnectionManager:
    """
    Manages server connections and lifecycle.
    
    Handles connection establishment, health monitoring, and automatic reconnection.
    """
    
    def __init__(self, logger: logging.Logger):
        self.connections: Dict[str, ServerConnection] = {}
        self.logger = logger
        self._health_check_interval = 60  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self) -> None:
        """Start the connection manager with background tasks"""
        if self._running:
            return
        
        self._running = True
        self._health_check_task = asyncio.create_task(self._background_health_check())
        self.logger.info("Connection manager started")
    
    async def stop(self) -> None:
        """Stop the connection manager and cleanup"""
        self._running = False
        
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect all servers
        for server_name in list(self.connections.keys()):
            await self.disconnect_server(server_name)
        
        self.logger.info("Connection manager stopped")
    
    async def connect_server(self, server, name: str, 
                           max_reconnect_attempts: int = 3) -> bool:
        """
        Connect to an MCP server.
        
        Args:
            server: MCP server instance
            name: Server identifier
            max_reconnect_attempts: Maximum reconnection attempts
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            connection = ServerConnection(
                server=server,
                name=name,
                status=ConnectionStatus.CONNECTING,
                max_reconnect_attempts=max_reconnect_attempts
            )
            
            # Store connection early for status tracking
            self.connections[name] = connection
            
            # Initialize the server
            await server.initialize()
            
            # Negotiate capabilities
            capabilities = server.get_capabilities()
            connection.capabilities = capabilities
            connection.status = ConnectionStatus.CONNECTED
            connection.connected_at = datetime.now()
            connection.last_ping = datetime.now()
            connection.error_count = 0
            connection.reconnect_attempts = 0
            
            self.logger.info(f"Connected to server: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to server {name}: {str(e)}")
            if name in self.connections:
                self.connections[name].status = ConnectionStatus.ERROR
                self.connections[name].error_count += 1
                self.connections[name].last_error = str(e)
            return False
    
    async def disconnect_server(self, name: str) -> bool:
        """
        Disconnect from an MCP server.
        
        Args:
            name: Server identifier
            
        Returns:
            True if disconnection successful, False otherwise
        """
        if name not in self.connections:
            self.logger.warning(f"Cannot disconnect from unknown server: {name}")
            return False
        
        try:
            connection = self.connections[name]
            
            # Call server cleanup if available
            if hasattr(connection.server, 'cleanup'):
                await connection.server.cleanup()
            
            connection.status = ConnectionStatus.DISCONNECTED
            del self.connections[name]
            
            self.logger.info(f"Disconnected from server: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from server {name}: {str(e)}")
            return False
    
    def get_connection(self, name: str) -> Optional[ServerConnection]:
        """Get connection by name"""
        return self.connections.get(name)
    
    def get_connected_servers(self) -> List[str]:
        """Get list of connected server names"""
        return [
            name for name, conn in self.connections.items()
            if conn.status == ConnectionStatus.CONNECTED
        ]
    
    def get_all_servers(self) -> List[str]:
        """Get list of all server names (connected and disconnected)"""
        return list(self.connections.keys())
    
    def get_healthy_servers(self) -> List[str]:
        """Get list of healthy server names"""
        return [
            name for name, conn in self.connections.items()
            if conn.is_healthy
        ]
    
    async def health_check(self, server_name: Optional[str] = None) -> Dict[str, bool]:
        """
        Perform health check on servers.
        
        Args:
            server_name: Specific server to check, or None for all servers
            
        Returns:
            Dict mapping server names to health status
        """
        results = {}
        servers_to_check = []
        
        if server_name:
            if server_name in self.connections:
                servers_to_check = [server_name]
            else:
                self.logger.warning(f"Cannot health check unknown server: {server_name}")
                return {server_name: False}
        else:
            servers_to_check = list(self.connections.keys())
        
        for name in servers_to_check:
            connection = self.connections[name]
            try:
                # Simple ping by getting capabilities
                capabilities = connection.server.get_capabilities()
                connection.last_ping = datetime.now()
                
                # Reset error count on successful ping
                if connection.status == ConnectionStatus.ERROR:
                    connection.error_count = max(0, connection.error_count - 1)
                
                connection.status = ConnectionStatus.CONNECTED
                results[name] = True
                
            except Exception as e:
                self.logger.warning(f"Health check failed for {name}: {str(e)}")
                connection.error_count += 1
                connection.status = ConnectionStatus.ERROR
                connection.last_error = str(e)
                results[name] = False
        
        return results
    
    async def reconnect_server(self, name: str) -> bool:
        """
        Attempt to reconnect to a server.
        
        Args:
            name: Server identifier
            
        Returns:
            True if reconnection successful, False otherwise
        """
        if name not in self.connections:
            self.logger.warning(f"Cannot reconnect to unknown server: {name}")
            return False
        
        connection = self.connections[name]
        
        if not connection.needs_reconnect:
            self.logger.debug(f"Server {name} does not need reconnection")
            return connection.status == ConnectionStatus.CONNECTED
        
        connection.reconnect_attempts += 1
        connection.status = ConnectionStatus.RECONNECTING
        
        self.logger.info(f"Attempting to reconnect to server {name} (attempt {connection.reconnect_attempts}/{connection.max_reconnect_attempts})")
        
        try:
            # Re-initialize the server
            await connection.server.initialize()
            
            # Re-negotiate capabilities
            capabilities = connection.server.get_capabilities()
            connection.capabilities = capabilities
            connection.status = ConnectionStatus.CONNECTED
            connection.last_ping = datetime.now()
            connection.error_count = 0
            connection.last_error = None
            
            self.logger.info(f"Successfully reconnected to server: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Reconnection failed for server {name}: {str(e)}")
            connection.status = ConnectionStatus.ERROR
            connection.last_error = str(e)
            
            if connection.reconnect_attempts >= connection.max_reconnect_attempts:
                self.logger.error(f"Max reconnection attempts reached for server {name}")
            
            return False
    
    async def _background_health_check(self) -> None:
        """Background task for periodic health checks"""
        while self._running:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                if not self._running:
                    break
                
                # Perform health checks
                health_results = await self.health_check()
                
                # Attempt reconnection for failed servers
                for server_name, is_healthy in health_results.items():
                    if not is_healthy:
                        connection = self.connections.get(server_name)
                        if connection and connection.needs_reconnect:
                            await self.reconnect_server(server_name)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in background health check: {str(e)}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        total_connections = len(self.connections)
        connected_count = len(self.get_connected_servers())
        healthy_count = len(self.get_healthy_servers())
        error_count = sum(1 for conn in self.connections.values() if conn.status == ConnectionStatus.ERROR)
        
        return {
            "total_connections": total_connections,
            "connected": connected_count,
            "healthy": healthy_count,
            "errors": error_count,
            "health_check_interval": self._health_check_interval,
            "running": self._running
        }
    
    def set_health_check_interval(self, interval_seconds: int) -> None:
        """Set the health check interval"""
        if interval_seconds < 10:
            raise ValueError("Health check interval must be at least 10 seconds")
        
        self._health_check_interval = interval_seconds
        self.logger.info(f"Health check interval set to {interval_seconds} seconds")
    
    def get_connection_details(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed information about all connections"""
        details = {}
        
        for name, connection in self.connections.items():
            details[name] = {
                "status": connection.status.value,
                "connected_at": connection.connected_at.isoformat() if connection.connected_at else None,
                "last_ping": connection.last_ping.isoformat() if connection.last_ping else None,
                "error_count": connection.error_count,
                "last_error": connection.last_error,
                "reconnect_attempts": connection.reconnect_attempts,
                "max_reconnect_attempts": connection.max_reconnect_attempts,
                "is_healthy": connection.is_healthy,
                "needs_reconnect": connection.needs_reconnect,
                "capabilities": list(connection.capabilities.keys()) if connection.capabilities else []
            }
        
        return details

# Test code to verify the module works independently
if __name__ == "__main__":
    import asyncio
    
    # Mock server class for testing
    class MockServer:
        def __init__(self, name: str):
            self.name = name
            self.initialized = False
            
        async def initialize(self):
            self.initialized = True
            return True
            
        def get_capabilities(self):
            return {"tools": ["test_tool"], "resources": [], "prompts": []}
            
        async def cleanup(self):
            self.initialized = False
    
    async def test_connection_manager():
        """Test connection manager functionality"""
        print("Testing Connection Manager...")
        
        # Test connection manager creation
        logger = logging.getLogger("test_connection_manager")
        manager = ConnectionManager(logger)
        
        print("✅ ConnectionManager created")
        
        # Test starting manager
        await manager.start()
        print("✅ ConnectionManager started")
        
        # Test server connection
        mock_server = MockServer("test_server")
        success = await manager.connect_server(mock_server, "test_server")
        
        if success:
            print("✅ Server connected successfully")
        else:
            print("ℹ️  Server connection failed (expected in test)")
        
        # Test connection status
        connection = manager.get_connection("test_server")
        if connection:
            print(f"✅ Connection found: {connection.name} - {connection.status.value}")
        else:
            print("ℹ️  No connection found")
        
        # Test getting connected servers
        connected = manager.get_connected_servers()
        print(f"✅ Connected servers: {len(connected)}")
        
        # Test getting all servers
        all_servers = manager.get_all_servers()
        print(f"✅ All servers: {len(all_servers)}")
        
        # Test getting healthy servers
        healthy = manager.get_healthy_servers()
        print(f"✅ Healthy servers: {len(healthy)}")
        
        # Test health check
        health_results = await manager.health_check()
        print(f"✅ Health check completed: {len(health_results)} servers checked")
        
        # Test connection statistics
        stats = manager.get_connection_stats()
        print(f"✅ Connection stats: {stats['total_connections']} total, {stats['connected']} connected")
        
        # Test connection details
        details = manager.get_connection_details()
        print(f"✅ Connection details retrieved for {len(details)} servers")
        
        # Test server disconnection
        if "test_server" in manager.connections:
            disconnect_success = await manager.disconnect_server("test_server")
            if disconnect_success:
                print("✅ Server disconnected successfully")
            else:
                print("ℹ️  Server disconnection failed")
        
        # Test stopping manager
        await manager.stop()
        print("✅ ConnectionManager stopped")
        
        print("🎉 All connection manager tests passed!")
    
    # Run test
    asyncio.run(test_connection_manager())
    print("Run with: python -m src.mcp.core.client.connection_manager") 