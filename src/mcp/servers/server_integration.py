"""
MCP Server Integration Layer

Provides integration between modular handlers and the MCP server.
Handles handler registration, tool routing, and server orchestration.
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional, Type
from datetime import datetime

from .handlers.config_manager import ConfigManager
from .handlers.error_handlers import ErrorHandler
from .handlers import create_handler, get_available_techniques


class MCPServerIntegration:
    """Integration layer for MCP server and modular handlers"""
    
    def __init__(self, config_path: str = "config/server_config.yaml"):
        self.config_manager = ConfigManager(config_path)
        self.error_handler = ErrorHandler()
        self.handlers: Dict[str, Any] = {}
        self.logger = logging.getLogger("mcp_server_integration")
        
        # Server state
        self.server_started = False
        self.electron_bridge = None
        
        # Initialize logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup centralized logging"""
        log_config = self.config_manager.get_config("logging", {})
        
        # Configure logging level
        log_level = getattr(logging, log_config.get("level", "INFO").upper())
        self.logger.setLevel(log_level)
        
        # Add file handler if specified
        if "file" in log_config:
            handler = logging.FileHandler(log_config["file"])
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    async def initialize_server(self) -> Dict[str, Any]:
        """Initialize MCP server with modular handlers"""
        try:
            self.logger.info("Initializing MCP server with modular handlers")
            
            # Get server configuration
            server_config = self.config_manager.get_config("server", {})
            
            # Initialize available techniques
            available_techniques = get_available_techniques()
            
            # Create handlers for each technique
            for technique_info in available_techniques:
                technique_name = technique_info["name"]
                
                try:
                    # Get technique-specific config
                    technique_config = self.config_manager.get_config(
                        f"techniques.{technique_name.lower()}", {}
                    )
                    
                    # Create handler
                    handler = create_handler(
                        technique_name, 
                        self.logger, 
                        technique_config
                    )
                    
                    self.handlers[technique_name] = handler
                    self.logger.info(f"Initialized {technique_name} handler")
                    
                except Exception as e:
                    self.logger.error(f"Failed to initialize {technique_name} handler: {e}")
                    self.error_handler.log_error("handler_initialization", str(e), {
                        "technique": technique_name
                    })
            
            # Start Electron bridge if configured
            electron_config = self.config_manager.get_config("electron", {})
            if electron_config.get("auto_start_server", True):
                await self._start_electron_bridge(electron_config)
            
            self.server_started = True
            
            return {
                "success": True,
                "message": "MCP server initialized successfully",
                "handlers_loaded": list(self.handlers.keys()),
                "electron_bridge_active": self.electron_bridge is not None
            }
            
        except Exception as e:
            self.logger.error(f"Server initialization failed: {e}")
            return self.error_handler.handle_error("server_initialization", e)
    
    async def _start_electron_bridge(self, electron_config: Dict[str, Any]):
        """Start Electron bridge for desktop integration"""
        try:
            # Import here to avoid circular imports
            from .handlers.electron_bridge import ElectronBridge
            
            port = electron_config.get("websocket_port", 8765)
            self.electron_bridge = ElectronBridge(websocket_port=port)
            
            # Start WebSocket server
            await self.electron_bridge.start_server()
            
            # Register custom message handlers
            self._register_electron_handlers()
            
            self.logger.info(f"Electron bridge started on port {port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start Electron bridge: {e}")
            self.error_handler.log_error("electron_bridge_start", str(e))
    
    def _register_electron_handlers(self):
        """Register custom Electron message handlers"""
        if not self.electron_bridge:
            return
        
        async def handle_get_techniques(message_data):
            """Handle request for available techniques"""
            return {
                "type": "techniques_response",
                "payload": {
                    "techniques": get_available_techniques(),
                    "active_handlers": list(self.handlers.keys())
                }
            }
        
        async def handle_handler_status(message_data):
            """Handle request for handler status"""
            technique = message_data.get("payload", {}).get("technique")
            if technique in self.handlers:
                handler = self.handlers[technique]
                status = await handler.health_check()
                return {
                    "type": "handler_status_response",
                    "payload": status
                }
            return {
                "type": "error",
                "payload": {"message": f"Handler not found: {technique}"}
            }
        
        # Register handlers
        self.electron_bridge.register_handler("get_techniques", handle_get_techniques)
        self.electron_bridge.register_handler("handler_status", handle_handler_status)
    
    async def route_tool_call(self, technique: str, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Route tool call to appropriate handler"""
        try:
            # Validate technique
            if technique not in self.handlers:
                return self.error_handler.handle_error(
                    "invalid_technique",
                    f"Technique '{technique}' not available",
                    {"available_techniques": list(self.handlers.keys())}
                )
            
            handler = self.handlers[technique]
            
            # Check if handler has the requested tool
            if not hasattr(handler, tool_name):
                return self.error_handler.handle_error(
                    "invalid_tool",
                    f"Tool '{tool_name}' not available for {technique}",
                    {"technique": technique}
                )
            
            # Execute tool with error handling
            tool_method = getattr(handler, tool_name)
            
            # Log tool execution
            self.logger.info(f"Executing {technique}.{tool_name} with args: {kwargs}")
            
            # Execute with timeout
            timeout = self.config_manager.get_config("server.tool_timeout", 300)
            result = await asyncio.wait_for(tool_method(**kwargs), timeout=timeout)
            
            # Log successful execution
            self.logger.info(f"Successfully executed {technique}.{tool_name}")
            
            return result
            
        except asyncio.TimeoutError:
            error_msg = f"Tool execution timeout: {technique}.{tool_name}"
            self.logger.error(error_msg)
            return self.error_handler.handle_error("timeout", error_msg)
            
        except Exception as e:
            error_msg = f"Tool execution failed: {technique}.{tool_name} - {str(e)}"
            self.logger.error(error_msg)
            return self.error_handler.handle_error("tool_execution", error_msg, {
                "technique": technique,
                "tool": tool_name,
                "args": kwargs
            })
    
    async def get_server_status(self) -> Dict[str, Any]:
        """Get comprehensive server status"""
        try:
            status = {
                "server_started": self.server_started,
                "timestamp": datetime.now().isoformat(),
                "handlers": {},
                "electron_bridge": None,
                "configuration": {
                    "config_loaded": self.config_manager.config_loaded,
                    "config_file": self.config_manager.config_path
                }
            }
            
            # Get handler status
            for technique, handler in self.handlers.items():
                try:
                    handler_status = await handler.health_check()
                    status["handlers"][technique] = handler_status
                except Exception as e:
                    status["handlers"][technique] = {
                        "healthy": False,
                        "error": str(e)
                    }
            
            # Get Electron bridge status
            if self.electron_bridge:
                status["electron_bridge"] = self.electron_bridge.get_connection_info()
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get server status: {e}")
            return self.error_handler.handle_error("status_check", str(e))
    
    async def shutdown_server(self) -> Dict[str, Any]:
        """Gracefully shutdown server"""
        try:
            self.logger.info("Shutting down MCP server")
            
            # Stop Electron bridge
            if self.electron_bridge:
                await self.electron_bridge.stop_server()
                self.electron_bridge = None
            
            # Clear handlers
            self.handlers.clear()
            
            self.server_started = False
            
            return {
                "success": True,
                "message": "Server shutdown completed"
            }
            
        except Exception as e:
            self.logger.error(f"Server shutdown failed: {e}")
            return self.error_handler.handle_error("shutdown", str(e))
    
    def get_available_tools(self, technique: str = None) -> Dict[str, Any]:
        """Get available tools for technique(s)"""
        try:
            if technique:
                if technique not in self.handlers:
                    return {"error": f"Technique '{technique}' not available"}
                
                handler = self.handlers[technique]
                # Get tools from handler (would need to implement tool discovery)
                return {"technique": technique, "tools": []}
            
            # Return all available tools
            all_tools = {}
            for tech, handler in self.handlers.items():
                all_tools[tech] = []  # Would implement tool discovery
            
            return {"techniques": all_tools}
            
        except Exception as e:
            return self.error_handler.handle_error("tool_discovery", str(e))


def main():
    """Test server integration functionality"""
    import asyncio
    import tempfile
    import yaml
    
    async def test_integration():
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config = {
                "server": {"tool_timeout": 300},
                "electron": {"auto_start_server": False},  # Don't start for test
                "logging": {"level": "INFO"}
            }
            yaml.dump(config, f)
            config_path = f.name
        
        # Test integration
        integration = MCPServerIntegration(config_path)
        
        # Test initialization
        result = await integration.initialize_server()
        assert result["success"] is True
        assert len(result["handlers_loaded"]) >= 4  # scRNA-seq, ATAC-seq, Spatial, Proteomics
        
        # Test status
        status = await integration.get_server_status()
        assert status["server_started"] is True
        assert "handlers" in status
        
        # Test shutdown
        shutdown_result = await integration.shutdown_server()
        assert shutdown_result["success"] is True
        
        print("✅ Server integration tests passed")
    
    # Run async test
    asyncio.run(test_integration())


if __name__ == "__main__":
    main()