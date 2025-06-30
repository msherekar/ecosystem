"""
Electron Bridge - Desktop application integration for MCP servers

Provides seamless integration between MCP servers and Electron desktop app:
- IPC communication with Electron main process
- File system access and local data management
- Native OS integration (notifications, system tray)
- Offline capability and local caching
- Enhanced UI/UX for desktop environment
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from pathlib import Path
import tempfile


# Define custom exceptions locally since import path might not exist
class ElectronError(Exception):
    """Exception raised for Electron-related errors"""
    pass


class CommunicationError(Exception):
    """Exception raised for communication errors"""
    pass


class ElectronBridge:
    """Bridge for communication with Electron desktop application"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.is_electron_env = self._detect_electron_environment()
        self.message_handlers: Dict[str, Callable] = {}
        self.file_manager = FileSystemManager(logger)
        
        # IPC communication
        self.stdin_reader = None
        self.stdout_writer = None
        self.message_queue = asyncio.Queue()
        self.running = False
    
    def _detect_electron_environment(self) -> bool:
        """Detect if running in Electron environment"""
        # Check for Electron-specific environment variables
        electron_indicators = [
            "ELECTRON_MODE",  # Our custom indicator
            "ELECTRON_RUN_AS_NODE",
            "ELECTRON_NO_ATTACH_CONSOLE",
            "__ELECTRON_ENABLE_LOGGING__"
        ]
        
        for indicator in electron_indicators:
            if os.environ.get(indicator):
                return True
        
        # Check if started with electron-specific arguments
        if any("electron" in arg.lower() for arg in sys.argv):
            return True
        
        return False
    
    async def initialize(self):
        """Initialize Electron bridge communication"""
        if not self.is_electron_env:
            self.logger.info("Not running in Electron environment - bridge disabled")
            return
        
        try:
            # Setup IPC communication via stdin/stdout
            self.stdin_reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(self.stdin_reader)
            await asyncio.get_event_loop().connect_read_pipe(
                lambda: protocol, sys.stdin
            )
            
            # Setup message processing
            self._setup_message_handlers()
            
            # Start message processing loop
            self.running = True
            asyncio.create_task(self._process_messages())
            
            # Notify Electron that bridge is ready
            await self._send_message("bridge_ready", {
                "version": "1.0.0",
                "capabilities": self._get_bridge_capabilities()
            })
            
            self.logger.info("Electron bridge initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Electron bridge: {str(e)}")
            raise ElectronError(f"Bridge initialization failed: {str(e)}")
    
    def _setup_message_handlers(self):
        """Setup handlers for different message types from Electron"""
        self.message_handlers = {
            "server_start_request": self._handle_server_start_request,
            "server_stop_request": self._handle_server_stop_request,
            "tool_execution_request": self._handle_tool_execution_request,
            "file_save_request": self._handle_file_save_request,
            "file_load_request": self._handle_file_load_request,
            "cache_request": self._handle_cache_request,
            "notification_request": self._handle_notification_request,
            "system_info_request": self._handle_system_info_request
        }
    
    async def _process_messages(self):
        """Process incoming messages from Electron"""
        while self.running:
            try:
                # Read message from stdin
                line = await self.stdin_reader.readline()
                if not line:
                    break
                
                # Parse message
                message_data = json.loads(line.decode('utf-8').strip())
                message = ElectronMessage(**message_data)
                
                # Handle message
                if message.type in self.message_handlers:
                    handler = self.message_handlers[message.type]
                    response = await handler(message)
                    
                    # Send response if needed
                    if response and message.request_id:
                        await self._send_response(message.request_id, response)
                
            except Exception as e:
                self.logger.error(f"Error processing Electron message: {str(e)}")
    
    async def _send_message(self, message_type: str, payload: Dict[str, Any], 
                           request_id: str = None):
        """Send message to Electron main process"""
        if not self.is_electron_env:
            return
        
        try:
            message = ElectronMessage(
                type=message_type,
                payload=payload,
                request_id=request_id,
                timestamp=asyncio.get_event_loop().time()
            )
            
            message_json = json.dumps(message.__dict__)
            sys.stdout.write(message_json + "\n")
            sys.stdout.flush()
            
        except Exception as e:
            self.logger.error(f"Failed to send message to Electron: {str(e)}")
    
    async def _send_response(self, request_id: str, response_data: Dict[str, Any]):
        """Send response to a specific request"""
        await self._send_message("response", response_data, request_id)
    
    def _get_bridge_capabilities(self) -> List[str]:
        """Get list of bridge capabilities"""
        return [
            "server_management",
            "file_operations",
            "local_caching",
            "notifications",
            "system_integration"
        ]
    
    # Message handlers
    async def _handle_server_start_request(self, message: "ElectronMessage") -> Dict[str, Any]:
        """Handle server start request from Electron"""
        server_type = message.payload.get("server_type")
        if not server_type:
            return {"success": False, "error": "Missing server_type"}
        
        # This would integrate with the main orchestrator
        # For now, return mock response
        return {
            "success": True,
            "message": f"Server {server_type} start requested",
            "server_id": f"electron_{server_type}_123"
        }
    
    async def _handle_server_stop_request(self, message: "ElectronMessage") -> Dict[str, Any]:
        """Handle server stop request from Electron"""
        server_id = message.payload.get("server_id")
        return {
            "success": True,
            "message": f"Server {server_id} stop requested"
        }
    
    async def _handle_tool_execution_request(self, message: "ElectronMessage") -> Dict[str, Any]:
        """Handle tool execution request from Electron"""
        tool_name = message.payload.get("tool_name")
        server_type = message.payload.get("server_type")
        parameters = message.payload.get("parameters", {})
        
        return {
            "success": True,
            "message": f"Tool {tool_name} execution requested",
            "result": {"executed": True, "tool": tool_name}
        }
    
    async def _handle_file_save_request(self, message: "ElectronMessage") -> Dict[str, Any]:
        """Handle file save request from Electron"""
        file_data = message.payload.get("data")
        filename = message.payload.get("filename")
        
        if not file_data or not filename:
            return {"success": False, "error": "Missing file data or filename"}
        
        try:
            file_path = self.file_manager.app_data_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                if isinstance(file_data, (dict, list)):
                    json.dump(file_data, f, indent=2)
                else:
                    f.write(str(file_data))
            
            return {
                "success": True,
                "message": "File saved successfully",
                "file_path": str(file_path)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_file_load_request(self, message: "ElectronMessage") -> Dict[str, Any]:
        """Handle file load request from Electron"""
        filename = message.payload.get("filename")
        
        if not filename:
            return {"success": False, "error": "Missing filename"}
        
        try:
            file_path = self.file_manager.app_data_dir / filename
            if not file_path.exists():
                return {"success": False, "error": "File not found"}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                if filename.endswith('.json'):
                    data = json.load(f)
                else:
                    data = f.read()
            
            return {
                "success": True,
                "message": "File loaded successfully",
                "data": data
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_cache_request(self, message: "ElectronMessage") -> Dict[str, Any]:
        """Handle cache operations from Electron"""
        operation = message.payload.get("operation")
        cache_key = message.payload.get("cache_key")
        
        if operation == "save":
            data = message.payload.get("data")
            success = self.file_manager.save_cache(cache_key, data)
            return {
                "success": success,
                "message": "Cache save completed" if success else "Cache save failed"
            }
        
        elif operation == "load":
            data = self.file_manager.load_cache(cache_key)
            return {
                "success": data is not None,
                "data": data,
                "message": "Cache loaded" if data else "Cache not found"
            }
        
        elif operation == "clear":
            success = self.file_manager.clear_cache(cache_key)
            return {
                "success": success,
                "message": "Cache cleared" if success else "Cache clear failed"
            }
        
        return {"success": False, "error": "Invalid cache operation"}
    
    async def _handle_notification_request(self, message: "ElectronMessage") -> Dict[str, Any]:
        """Handle notification request from Electron"""
        notification_data = message.payload
        
        # Send notification to Electron for display
        await self._send_message("show_notification", notification_data)
        
        return {
            "success": True,
            "message": "Notification sent to Electron"
        }
    
    async def _handle_system_info_request(self, message: "ElectronMessage") -> Dict[str, Any]:
        """Handle system information request"""
        import platform
        
        try:
            # Try to import psutil, but provide fallback if not available
            try:
                import psutil
                system_info = {
                    "platform": platform.system(),
                    "platform_version": platform.version(),
                    "architecture": platform.machine(),
                    "python_version": platform.python_version(),
                    "cpu_count": psutil.cpu_count(),
                    "memory_total": psutil.virtual_memory().total,
                    "disk_usage": psutil.disk_usage('/').total if platform.system() != "Windows" else psutil.disk_usage('C:').total
                }
            except ImportError:
                system_info = {
                    "platform": platform.system(),
                    "platform_version": platform.version(),
                    "architecture": platform.machine(),
                    "python_version": platform.python_version(),
                    "cpu_count": os.cpu_count() or 1,
                    "memory_total": "Unknown (psutil not available)",
                    "disk_usage": "Unknown (psutil not available)"
                }
            
            return {
                "success": True,
                "system_info": system_info
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Public methods for server integration
    async def notify_server_started(self, server_type: str):
        """Notify Electron that a server has started"""
        await self._send_message("server_started", {
            "server_type": server_type,
            "timestamp": asyncio.get_event_loop().time()
        })
    
    async def notify_server_stopped(self, server_type: str):
        """Notify Electron that a server has stopped"""
        await self._send_message("server_stopped", {
            "server_type": server_type,
            "timestamp": asyncio.get_event_loop().time()
        })
    
    async def notify_analysis_progress(self, server_type: str, step: str, progress: float):
        """Notify Electron of analysis progress"""
        await self._send_message("analysis_progress", {
            "server_type": server_type,
            "step": step,
            "progress": progress,
            "timestamp": asyncio.get_event_loop().time()
        })
    
    async def send_desktop_notification(self, notification: "DesktopNotification"):
        """Send desktop notification via Electron"""
        await self._send_message("desktop_notification", {
            "title": notification.title,
            "body": notification.body,
            "icon": notification.icon,
            "urgency": notification.urgency,
            "timeout": notification.timeout,
            "actions": notification.actions or []
        })
    
    async def update_system_tray(self, status: str, tooltip: str = None):
        """Update system tray icon and tooltip"""
        await self._send_message("update_system_tray", {
            "status": status,
            "tooltip": tooltip or f"MCP Servers - {status}"
        })
    
    async def show_file_dialog(self, dialog_type: str = "open", 
                              filters: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Show file dialog and return selected files"""
        request_id = f"file_dialog_{asyncio.get_event_loop().time()}"
        
        await self._send_message("show_file_dialog", {
            "dialog_type": dialog_type,
            "filters": filters or []
        }, request_id)
        
        # Wait for response (simplified - in real implementation would use proper async waiting)
        return {"success": True, "files": []}
    
    def get_app_data_path(self) -> str:
        """Get application data directory path"""
        return str(self.file_manager.app_data_dir)
    
    def get_cache_path(self) -> str:
        """Get cache directory path"""
        return str(self.file_manager.cache_dir)
    
    async def shutdown(self):
        """Shutdown Electron bridge"""
        self.running = False
        
        if self.is_electron_env:
            await self._send_message("bridge_shutdown", {
                "timestamp": asyncio.get_event_loop().time()
            })
        
        self.logger.info("Electron bridge shutdown complete")


@dataclass
class ElectronMessage:
    """Message structure for Electron IPC communication"""
    type: str
    payload: Dict[str, Any]
    request_id: Optional[str] = None
    timestamp: Optional[float] = None


@dataclass
class DesktopNotification:
    """Desktop notification configuration"""
    title: str
    body: str
    icon: Optional[str] = None
    urgency: str = "normal"  # low, normal, critical
    timeout: int = 5000  # milliseconds
    actions: List[Dict[str, str]] = None


class FileSystemManager:
    """Manages local file system operations for desktop app"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.app_data_dir = self._get_app_data_directory()
        self.cache_dir = self.app_data_dir / "cache"
        self.temp_dir = self.app_data_dir / "temp"
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _get_app_data_directory(self) -> Path:
        """Get platform-specific application data directory"""
        if sys.platform == "win32":
            base_dir = Path(os.environ.get("APPDATA", ""))
        elif sys.platform == "darwin":
            base_dir = Path.home() / "Library" / "Application Support"
        else:  # Linux and others
            base_dir = Path.home() / ".config"
        
        return base_dir / "MCPBioinformatics"
    
    def _ensure_directories(self):
        """Ensure required directories exist"""
        for directory in [self.app_data_dir, self.cache_dir, self.temp_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_cache_path(self, cache_key: str) -> Path:
        """Get path for cached data"""
        safe_key = "".join(c for c in cache_key if c.isalnum() or c in "._-")
        return self.cache_dir / f"{safe_key}.json"
    
    def save_cache(self, cache_key: str, data: Any) -> bool:
        """Save data to local cache"""
        try:
            cache_path = self.get_cache_path(cache_key)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save cache {cache_key}: {str(e)}")
            return False
    
    def load_cache(self, cache_key: str) -> Optional[Any]:
        """Load data from local cache"""
        try:
            cache_path = self.get_cache_path(cache_key)
            if not cache_path.exists():
                return None
            
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load cache {cache_key}: {str(e)}")
            return None
    
    def clear_cache(self, cache_key: str = None) -> bool:
        """Clear specific cache entry or all cache"""
        try:
            if cache_key:
                cache_path = self.get_cache_path(cache_key)
                if cache_path.exists():
                    cache_path.unlink()
            else:
                # Clear all cache files
                for cache_file in self.cache_dir.glob("*.json"):
                    cache_file.unlink()
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear cache {cache_key}: {str(e)}")
            return False
    
    def create_temp_file(self, suffix: str = ".tmp") -> Path:
        """Create a temporary file and return its path"""
        temp_fd, temp_path = tempfile.mkstemp(suffix=suffix, dir=self.temp_dir)
        os.close(temp_fd)  # Close the file descriptor
        return Path(temp_path)


# Desktop integration utilities
class DesktopIntegration:
    """Utilities for desktop environment integration"""
    
    @staticmethod
    def create_analysis_notification(analysis_type: str, status: str) -> DesktopNotification:
        """Create notification for analysis completion"""
        status_messages = {
            "completed": f"{analysis_type} analysis completed successfully",
            "failed": f"{analysis_type} analysis failed",
            "started": f"{analysis_type} analysis started"
        }
        
        urgency_map = {
            "completed": "normal",
            "failed": "critical", 
            "started": "low"
        }
        
        return DesktopNotification(
            title="MCP Bioinformatics",
            body=status_messages.get(status, f"{analysis_type} - {status}"),
            urgency=urgency_map.get(status, "normal"),
            timeout=5000 if status != "failed" else 10000
        )
    
    @staticmethod
    def create_server_notification(server_type: str, action: str) -> DesktopNotification:
        """Create notification for server events"""
        return DesktopNotification(
            title="MCP Server Manager",
            body=f"{server_type.upper()} server {action}",
            urgency="low",
            timeout=3000
        )


def main():
    """Main function for testing ElectronBridge"""
    print("=== Electron Bridge Test ===")
    
    # Static tests
    print("\n1. Testing ElectronMessage...")
    message = ElectronMessage(
        type="test_message",
        payload={"data": "test"},
        request_id="req_123"
    )
    assert message.type == "test_message"
    assert message.payload["data"] == "test"
    print("✅ ElectronMessage created")
    
    print("\n2. Testing DesktopNotification...")
    notification = DesktopNotification(
        title="Test",
        body="Test notification",
        urgency="normal"
    )
    assert notification.title == "Test"
    assert notification.urgency == "normal"
    print("✅ DesktopNotification created")
    
    print("\n3. Testing FileSystemManager...")
    logger = logging.getLogger("test")
    fs_manager = FileSystemManager(logger)
    
    assert fs_manager.app_data_dir.exists()
    assert fs_manager.cache_dir.exists()
    print("✅ FileSystemManager initialized")
    
    print("\n4. Testing cache operations...")
    test_data = {"test": "data", "number": 42}
    cache_key = "test_cache"
    
    # Save cache
    saved = fs_manager.save_cache(cache_key, test_data)
    assert saved is True
    
    # Load cache
    loaded_data = fs_manager.load_cache(cache_key)
    assert loaded_data == test_data
    
    # Clear cache
    cleared = fs_manager.clear_cache(cache_key)
    assert cleared is True
    print("✅ Cache operations working")
    
    print("\n5. Testing ElectronBridge creation...")
    bridge = ElectronBridge(logger)
    assert bridge.logger == logger
    assert hasattr(bridge, 'message_handlers')
    print("✅ ElectronBridge created")


def test_dynamic():
    """Dynamic tests for ElectronBridge"""
    async def run_dynamic_tests():
        print("\n=== Dynamic Tests ===")
        
        logger = logging.getLogger("test")
        bridge = ElectronBridge(logger)
        
        print("1. Testing environment detection...")
        # Test Electron environment detection
        is_electron = bridge._detect_electron_environment()
        # Will be False in test environment
        assert isinstance(is_electron, bool)
        print("✅ Environment detection working")
        
        print("\n2. Testing message handlers setup...")
        bridge._setup_message_handlers()
        expected_handlers = [
            "server_start_request",
            "tool_execution_request", 
            "cache_request",
            "notification_request"
        ]
        for handler in expected_handlers:
            assert handler in bridge.message_handlers
        print("✅ Message handlers setup")
        
        print("\n3. Testing capabilities...")
        capabilities = bridge._get_bridge_capabilities()
        assert "server_management" in capabilities
        assert "file_operations" in capabilities
        print("✅ Bridge capabilities defined")
        
        print("\n4. Testing file operations...")
        fs_manager = bridge.file_manager
        
        # Test temp file creation
        temp_file = fs_manager.create_temp_file(".test")
        assert temp_file.exists()
        temp_file.unlink()  # Cleanup
        print("✅ File operations working")
        
        print("\n5. Testing desktop integration utilities...")
        notification = DesktopIntegration.create_analysis_notification("RNA-seq", "completed")
        assert notification.title == "MCP Bioinformatics"
        assert "RNA-seq" in notification.body
        
        server_notification = DesktopIntegration.create_server_notification("scrnaseq", "started")
        assert "SCRNASEQ" in server_notification.body
        print("✅ Desktop integration utilities working")
        
        print("\n6. Testing message handling...")
        # Test cache request handling
        test_message = ElectronMessage(
            type="cache_request",
            payload={
                "operation": "save",
                "cache_key": "test_key",
                "data": {"test": True}
            }
        )
        
        response = await bridge._handle_cache_request(test_message)
        assert response["success"] is True
        print("✅ Message handling working")
        
        print("\n🎉 All dynamic tests passed!")
    
    # Run async tests
    asyncio.run(run_dynamic_tests())


if __name__ == "__main__":
    main()
    test_dynamic() 



