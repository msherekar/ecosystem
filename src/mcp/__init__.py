"""
MCP (Model Context Protocol) - Unified Bioinformatics Analysis Platform

A comprehensive platform integrating AI agents, analysis servers, and intelligent routing
for bioinformatics research. Provides seamless communication between components with
advanced Electron UI/UX integration.

Main Components:
- Agent System: Intelligent routing, coordination, and decision-making
- Core System: Client, registry, server management, and training
- Server System: Specialized analysis servers (RNA-seq, scRNA-seq, ATAC-seq, etc.)

Usage:
    # Initialize complete MCP system
    from src.mcp import MCPSystem
    
    system = MCPSystem()
    await system.initialize()
    
    # Start with Electron UI
    await system.start_electron_ui()
    
    # Or use individual components
    from src.mcp.agent import quick_start_bioinformatics_agent
    from src.mcp.core import initialize_mcp_core
    from src.mcp.servers import get_orchestrator
"""

# Required: dataclass annotations below reference names resolved lazily by
# __getattr__, so they must stay strings rather than being evaluated at
# class-creation time.
from __future__ import annotations

import asyncio
import logging
import sys
import tracemalloc
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json
import uuid

# tracemalloc is NOT started here. Starting it as an import side effect slows
# every allocation in the process for the lifetime of the program, to silence
# a warning that only appears when an unawaited coroutine is garbage
# collected. Set PYTHONTRACEMALLOC=1 when you actually need that traceback.

# Version information
__version__ = "1.0.0"
__author__ = "Gliaent Bioinformatics Platform"
__description__ = "Unified MCP platform for bioinformatics analysis"

# Import core components
# --- Lazy subpackage re-exports ------------------------------------------
#
# These were eager `from .core import ...` / `.agent` / `.servers` blocks, so
# importing ANY name from this package loaded the entire system: the agent, the
# routing layer, every analysis server, and transitively `streamlit` (via
# core.analysis_interface). That made it impossible to import a single
# validator in a headless process or a test without a Streamlit install, and
# it meant `import mcp` paid for several seconds of work no matter what the
# caller actually wanted.
#
# PEP 562 module __getattr__ resolves each name on first access instead. The
# public API is unchanged: `from mcp import Agent` still works.

_LAZY_EXPORTS = {
    # name -> submodule it lives in
    "MCPCoreSystem": ".core",
    "MCPCoreConfiguration": ".core",
    "initialize_mcp_core": ".core",
    "get_mcp_core": ".core",
    "shutdown_mcp_core": ".core",
    "quick_start_bioinformatics_agent": ".agent",
    "get_hybrid_coordinator": ".agent",
    "IntelligentToolRouter": ".agent",
    "Agent": ".agent",
    "get_agent_status": ".agent",
    "create_complete_agent": ".agent",
    "get_orchestrator": ".servers",
    "MCPServerOrchestrator": ".servers",
    "ServerConfig": ".servers",
    "ServerContext": ".servers",
}


def __getattr__(name: str):
    """Resolve a re-exported name on first access.

    Raises:
        AttributeError: If `name` is not exported by this package.
    """
    module_name = _LAZY_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    import importlib

    module = importlib.import_module(module_name, __name__)
    try:
        value = getattr(module, name)
    except AttributeError as exc:
        raise AttributeError(
            f"{__name__}.{name} is declared in _LAZY_EXPORTS but "
            f"{module_name} does not define it"
        ) from exc
    globals()[name] = value  # cache, so this runs once per name
    return value


def __dir__():
    return sorted(set(globals()) | set(_LAZY_EXPORTS))

# Setup logging
logger = logging.getLogger(__name__)


@dataclass
class MCPSystemConfiguration:
    """Unified configuration for the entire MCP system"""
    
    # System-wide settings
    name: str = "gliaent_mcp_system"
    version: str = __version__
    debug: bool = False
    electron_mode: bool = True
    
    # Agent configuration
    agent_api_key: Optional[str] = None
    enable_intelligent_routing: bool = True
    enable_coordination: bool = True
    
    # Core system configuration
    core_config: Optional[MCPCoreConfiguration] = None
    
    # Server configuration
    server_config: Optional[ServerConfig] = None
    
    # Electron integration
    websocket_port: int = 8765
    ui_update_interval: float = 0.1
    enable_real_time_sync: bool = True
    
    # Security and performance
    max_concurrent_operations: int = 50
    operation_timeout: int = 30
    enable_audit_logging: bool = True
    
    # Data paths
    data_directory: Optional[Path] = None
    
    def __post_init__(self):
        """Initialize default configurations"""
        if self.core_config is None:
            self.core_config = MCPCoreConfiguration(
                name=f"{self.name}_core",
                electron_mode=self.electron_mode,
                websocket_port=self.websocket_port + 1,
                debug=self.debug
            )
        
        if self.server_config is None:
            self.server_config = ServerConfig(
                electron_mode=self.electron_mode,
                electron_bridge_enabled=True,
                log_level=logging.DEBUG if self.debug else logging.INFO
            )
        
        if self.data_directory is None:
            self.data_directory = Path.home() / ".gliaent_mcp"
            self.data_directory.mkdir(parents=True, exist_ok=True)


class MCPSystemBridge:
    """Bridge for communication between MCP subsystems"""
    
    def __init__(self):
        self.message_queue = asyncio.Queue()
        self.event_handlers: Dict[str, List[callable]] = {}
        self.system_state: Dict[str, Any] = {}
        
    def register_handler(self, event_type: str, handler: callable):
        """Register event handler for inter-system communication"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit event to all registered handlers"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {e}")
    
    def update_system_state(self, component: str, state: Dict[str, Any]):
        """Update system state from components"""
        self.system_state[component] = {
            **state,
            "last_updated": datetime.now().isoformat()
        }


class MCPSystem:
    """
    Unified MCP System - Main orchestrator for all components
    
    This class provides the main entry point for the entire MCP platform,
    coordinating between agent, core, and server subsystems while maintaining
    seamless Electron UI/UX integration.
    """
    
    def __init__(self, config: Union[MCPSystemConfiguration, Dict[str, Any], None] = None):
        # Configuration setup
        if isinstance(config, dict):
            self.config = MCPSystemConfiguration(**config)
        elif config is None:
            self.config = MCPSystemConfiguration()
        else:
            self.config = config
        
        # System state
        self.initialized = False
        self.running = False
        self.start_time: Optional[datetime] = None
        
        # Core components (initialized in initialize())
        self.agent = None
        self.router = None
        self.coordinator = None
        self.core_system = None
        self.server_orchestrator = None
        
        # Inter-system communication
        self.bridge = MCPSystemBridge()
        
        # Electron integration
        self.electron_bridges: Dict[str, Any] = {}
        self.websocket_servers: List[Any] = []
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        
        # Metrics and monitoring
        self.metrics: Dict[str, Any] = {
            "operations_completed": 0,
            "errors_encountered": 0,
            "last_operation_time": None,
            "system_events": []
        }
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup comprehensive logging for the entire system"""
        log_level = logging.DEBUG if self.config.debug else logging.INFO
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        
        # Setup file handler
        log_file = self.config.data_directory / "mcp_system.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        
        # Setup console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        if not root_logger.handlers:
            root_logger.addHandler(file_handler)
            root_logger.addHandler(console_handler)
        
        logger.info(f"MCP System v{__version__} logging initialized")
    
    async def initialize(self) -> bool:
        """Initialize all MCP subsystems in proper order"""
        if self.initialized:
            logger.warning("MCP System already initialized")
            return True
        
        try:
            self.start_time = datetime.now()
            logger.info("🚀 Initializing Complete MCP System...")
            
            # Setup inter-system communication bridges
            self._setup_system_bridges()
            
            # 1. Initialize Core System (provides foundation)
            await self._initialize_core_system()
            
            # 2. Initialize Server Orchestrator (provides analysis capabilities)
            await self._initialize_server_system()
            
            # 3. Initialize Agent System (provides intelligence and routing)
            await self._initialize_agent_system()
            
            # 4. Setup cross-system communication
            await self._setup_cross_system_communication()
            
            # 5. Initialize Electron integration
            if self.config.electron_mode:
                await self._initialize_electron_integration()
            
            # 6. Start background monitoring and sync tasks
            await self._start_background_tasks()
            
            self.initialized = True
            self.running = True
            
            # Emit system ready event
            await self.bridge.emit_event("system_initialized", {
                "timestamp": datetime.now().isoformat(),
                "components": ["agent", "core", "servers"],
                "electron_mode": self.config.electron_mode
            })
            
            logger.info("✅ Complete MCP System initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize MCP System: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def _setup_system_bridges(self):
        """Setup communication bridges between subsystems"""
        logger.info("Setting up inter-system communication bridges...")
        
        # Register cross-system event handlers
        self.bridge.register_handler("agent_request", self._handle_agent_request)
        self.bridge.register_handler("server_response", self._handle_server_response)
        self.bridge.register_handler("core_event", self._handle_core_event)
        self.bridge.register_handler("electron_message", self._handle_electron_message)
        
        logger.info("✅ System bridges configured")
    
    async def _initialize_core_system(self):
        """Initialize the MCP Core system"""
        logger.info("🔧 Initializing Core System...")
        
        try:
            self.core_system = await initialize_mcp_core(self.config.core_config)
            
            # Connect core events to our bridge
            self.core_system.register_ui_event_handler(
                lambda event: asyncio.create_task(
                    self.bridge.emit_event("core_event", event)
                )
            )
            
            logger.info("✅ Core System initialized")
            
        except Exception as e:
            logger.error(f"❌ Core System initialization failed: {e}")
            raise
    
    async def _initialize_server_system(self):
        """Initialize the MCP Server orchestrator"""
        logger.info("🔧 Initializing Server System...")
        
        try:
            # Import server orchestrator
            from .servers import get_orchestrator
            
            # Create server context
            server_context = ServerContext(
                electron_mode=self.config.electron_mode,
                debug_mode=self.config.debug
            )
            
            self.server_orchestrator = await get_orchestrator(self.config.server_config)
            await self.server_orchestrator.initialize(server_context)
            
            logger.info("✅ Server System initialized")
            
        except Exception as e:
            logger.error(f"❌ Server System initialization failed: {e}")
            raise
    
    async def _initialize_agent_system(self):
        """Initialize the Agent system with intelligent routing"""
        logger.info("🔧 Initializing Agent System...")
        
        try:
            # Initialize core agent
            self.agent = await create_complete_agent(
                api_key=self.config.agent_api_key,
                config={
                    "electron_mode": self.config.electron_mode,
                    "debug": self.config.debug
                }
            )
            
            # Initialize intelligent router
            if self.config.enable_intelligent_routing:
                self.router = IntelligentToolRouter()
            
            # Initialize coordination system
            if self.config.enable_coordination:
                self.coordinator = await get_hybrid_coordinator(
                    api_key=self.config.agent_api_key
                )
            
            logger.info("✅ Agent System initialized")
            
        except Exception as e:
            logger.error(f"❌ Agent System initialization failed: {e}")
            raise
    
    async def _setup_cross_system_communication(self):
        """Setup communication pathways between all subsystems"""
        logger.info("🔗 Setting up cross-system communication...")
        
        try:
            # Connect agent to core system
            if self.agent and self.core_system:
                # Agent can access core tools through the registry
                available_tools = self.core_system.get_available_tools()
                self.agent.set_available_tools(available_tools)
            
            # Connect servers to core registry
            if self.server_orchestrator and self.core_system:
                # Register active servers with core registry
                for server_name, server_info in self.server_orchestrator.get_active_servers().items():
                    await self.core_system.connect_server(
                        server_name, 
                        server_info["class"], 
                        **server_info.get("config", {})
                    )
            
            # Setup agent-server communication through core
            if self.agent and self.router and self.core_system:
                # Router can access all registered tools
                tools = self.core_system.get_available_tools()
                # Additional agent-specific setup would go here
            
            logger.info("✅ Cross-system communication established")
            
        except Exception as e:
            logger.error(f"❌ Cross-system communication setup failed: {e}")
            raise
    
    async def _initialize_electron_integration(self):
        """Initialize comprehensive Electron UI/UX integration"""
        logger.info("⚡ Initializing Electron Integration...")
        
        try:
            bridges_initialized = 0
            
            # Initialize core electron bridge
            try:
                if hasattr(self.core_system, 'electron_bridge') and self.core_system.electron_bridge:
                    self.electron_bridges['core'] = self.core_system.electron_bridge
                    bridges_initialized += 1
                else:
                    logger.debug("Core system electron bridge not available")
            except Exception as e:
                logger.debug(f"Core electron bridge initialization failed: {e}")
            
            # Initialize agent coordination electron bridge
            try:
                if self.coordinator and hasattr(self.coordinator, 'electron_bridge'):
                    # Agent coordination has its own Electron bridge
                    agent_bridge = self.coordinator.electron_bridge
                    if agent_bridge:
                        self.electron_bridges['agent'] = agent_bridge
                        bridges_initialized += 1
                else:
                    logger.debug("Agent coordinator electron bridge not available")
            except Exception as e:
                logger.debug(f"Agent electron bridge initialization failed: {e}")
            
            # Initialize server orchestrator electron bridge  
            try:
                if hasattr(self.server_orchestrator, 'electron_bridge') and self.server_orchestrator.electron_bridge:
                    self.electron_bridges['servers'] = self.server_orchestrator.electron_bridge
                    bridges_initialized += 1
                else:
                    logger.debug("Server orchestrator electron bridge not available")
            except Exception as e:
                logger.debug(f"Server electron bridge initialization failed: {e}")
            
            # Create unified MCP system bridge for cross-component communication
            try:
                await self._create_unified_electron_bridge()
                # Check if unified bridge was created (either real or mock)
                if 'unified' in self.electron_bridges:
                    bridges_initialized += 1
            except Exception as e:
                logger.error(f"Failed to create unified electron bridge: {e}")
                # Create minimal fallback
                self._create_mock_electron_bridge()
                bridges_initialized += 1
            
            # Setup real-time synchronization if we have bridges
            if self.config.enable_real_time_sync and len(self.electron_bridges) > 0:
                try:
                    await self._setup_real_time_sync()
                    logger.debug("Real-time synchronization enabled")
                except Exception as e:
                    logger.warning(f"Real-time sync setup failed: {e}")
            
            logger.info(f"✅ Electron Integration initialized with {bridges_initialized} bridges")
            
            # Keep electron mode enabled even with mock bridges for testing
            if bridges_initialized == 0:
                logger.warning("No Electron bridges available - creating minimal bridge")
                self._create_mock_electron_bridge()
            
        except Exception as e:
            logger.error(f"❌ Electron Integration initialization failed: {e}")
            # Create minimal bridge even on failure
            try:
                self._create_mock_electron_bridge()
                logger.info("Created fallback Electron bridge")
            except Exception as fallback_error:
                logger.error(f"Even fallback bridge creation failed: {fallback_error}")
                # Only disable electron mode if we can't create anything
                self.config.electron_mode = False
    
    async def _create_unified_electron_bridge(self):
        """Create a unified Electron bridge for the entire MCP system"""
        try:
            # Try to import websockets - handle gracefully if not available
            try:
                import websockets
                websockets_available = True
            except ImportError:
                logger.warning("WebSockets library not available - Electron bridge will be limited")
                websockets_available = False
                # Create a mock bridge for testing purposes
                self._create_mock_electron_bridge()
                return
            
            # Create unified WebSocket server for MCP system coordination
            async def handle_mcp_client(websocket, path):
                """Handle Electron client connections for MCP system"""
                client_id = str(uuid.uuid4())
                logger.info(f"New Electron client connected: {client_id}")
                
                try:
                    # Send initial system status
                    status = await self.get_system_status()
                    await websocket.send(json.dumps({
                        "type": "system_status",
                        "data": status,
                        "client_id": client_id
                    }))
                    
                    # Handle incoming messages
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            await self._handle_electron_message(data, websocket, client_id)
                        except json.JSONDecodeError:
                            await websocket.send(json.dumps({
                                "type": "error",
                                "message": "Invalid JSON received"
                            }))
                            
                except websockets.exceptions.ConnectionClosed:
                    logger.info(f"Electron client disconnected: {client_id}")
                except Exception as e:
                    logger.error(f"Error handling Electron client {client_id}: {e}")
            
            # Start WebSocket server with error handling
            try:
                self.unified_websocket_server = await websockets.serve(
                    handle_mcp_client,
                    "localhost",
                    self.config.websocket_port,
                    ping_interval=30,
                    ping_timeout=10
                )
                
                logger.info(f"Unified MCP Electron bridge listening on port {self.config.websocket_port}")
                
            except OSError as e:
                if "Address already in use" in str(e):
                    logger.warning(f"Port {self.config.websocket_port} already in use - trying alternative port")
                    # Try alternative port
                    alternative_port = self.config.websocket_port + 1
                    self.unified_websocket_server = await websockets.serve(
                        handle_mcp_client,
                        "localhost",
                        alternative_port,
                        ping_interval=30,
                        ping_timeout=10
                    )
                    logger.info(f"Unified MCP Electron bridge listening on alternative port {alternative_port}")
                else:
                    raise
            
        except Exception as e:
            logger.error(f"Failed to create unified Electron bridge: {e}")
            # Create fallback bridge instead of failing completely
            self._create_mock_electron_bridge()
    
    def _create_mock_electron_bridge(self):
        """Create a mock electron bridge for testing when WebSockets are not available"""
        class MockElectronBridge:
            def __init__(self, name):
                self.name = name
                self.events = []
            
            async def emit_event(self, event_type: str, data: Dict[str, Any]):
                """Mock emit event method"""
                self.events.append({
                    "type": event_type,
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                })
                return True
            
            async def broadcast(self, message: Dict[str, Any]):
                """Mock broadcast method"""
                self.events.append({
                    "type": "broadcast",
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                })
                return True
        
        # Create mock bridges for each component
        self.electron_bridges['unified'] = MockElectronBridge('unified')
        logger.info("Created mock Electron bridge for testing")
    
    async def _setup_real_time_sync(self):
        """Setup real-time synchronization between components and Electron UI"""
        
        async def sync_loop():
            """Background task for real-time synchronization"""
            while self.running:
                try:
                    # Collect status from all components
                    status = await self.get_system_status()
                    
                    # Broadcast to all Electron bridges
                    await self._broadcast_to_electron({
                        "type": "status_update",
                        "data": status,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    await asyncio.sleep(self.config.ui_update_interval)
                    
                except Exception as e:
                    logger.error(f"Error in sync loop: {e}")
                    await asyncio.sleep(1.0)  # Fallback delay
        
        # Start sync task
        sync_task = asyncio.create_task(sync_loop())
        self.background_tasks.append(sync_task)
        
        logger.info("✅ Real-time synchronization enabled")
    
    async def _start_background_tasks(self):
        """Start background monitoring and maintenance tasks"""
        logger.info("🔄 Starting background tasks...")
        
        # Health monitoring task
        async def health_monitor():
            while self.running:
                try:
                    # Check all component health
                    health_status = await self.health_check()
                    
                    # Update metrics
                    self.bridge.update_system_state("health", health_status)
                    
                    # Log unhealthy components (use debug for routine checks)
                    for component, status in health_status.items():
                        if not status.get("healthy", True):
                            # Only warn if this is a critical error, otherwise use debug
                            error_msg = status.get("error", "")
                            if "not initialized" in error_msg:
                                logger.debug(f"Component {component} not yet initialized")
                            else:
                                logger.warning(f"Component {component} health check failed: {error_msg}")
                    
                    await asyncio.sleep(30)  # Check every 30 seconds
                    
                except Exception as e:
                    logger.error(f"Error in health monitor: {e}")
                    await asyncio.sleep(10)
        
        # System metrics collection task
        async def metrics_collector():
            while self.running:
                try:
                    # Collect metrics from all components
                    metrics = await self._collect_system_metrics()
                    
                    # Update bridge state
                    self.bridge.update_system_state("metrics", metrics)
                    
                    # Update our local metrics
                    self.metrics.update(metrics)
                    
                    await asyncio.sleep(60)  # Collect every minute
                    
                except Exception as e:
                    logger.error(f"Error in metrics collector: {e}")
                    await asyncio.sleep(30)
        
        # Start background tasks
        self.background_tasks.extend([
            asyncio.create_task(health_monitor()),
            asyncio.create_task(metrics_collector())
        ])
        
        logger.info(f"✅ Started {len(self.background_tasks)} background tasks")
    
    # Event handlers for inter-system communication
    
    async def _handle_agent_request(self, data: Dict[str, Any]):
        """Handle requests from the agent system"""
        request_type = data.get("type")
        
        if request_type == "execute_tool":
            # Agent wants to execute a tool through core system
            if self.core_system:
                result = await self.core_system.execute_analysis(
                    data.get("analysis_type"),
                    data.get("context", {})
                )
                # Send result back to agent
                await self.bridge.emit_event("server_response", {
                    "request_id": data.get("request_id"),
                    "result": result
                })
        
        elif request_type == "get_available_tools":
            # Agent wants to know available tools
            if self.core_system:
                tools = self.core_system.get_available_tools()
                await self.bridge.emit_event("server_response", {
                    "request_id": data.get("request_id"),
                    "result": {"tools": tools}
                })
    
    async def _handle_server_response(self, data: Dict[str, Any]):
        """Handle responses from server system"""
        # Forward server responses to agent if needed
        if self.agent and "request_id" in data:
            # Agent can process the response
            pass
    
    async def _handle_core_event(self, data: Dict[str, Any]):
        """Handle events from core system"""
        event_type = data.get("event", "unknown")
        
        # Update metrics
        if event_type == "analysis_completed":
            self.metrics["operations_completed"] += 1
            self.metrics["last_operation_time"] = datetime.now()
        
        # Broadcast to Electron if important
        if event_type in ["server_connected", "analysis_completed", "error"]:
            await self._broadcast_to_electron({
                "type": "core_event",
                "data": data
            })
    
    async def _handle_electron_message(self, data: Dict[str, Any], websocket=None, client_id=None):
        """Handle messages from Electron UI"""
        try:
            message_type = data.get("type")
            payload = data.get("payload", {})
            
            if message_type == "get_system_status":
                status = await self.get_system_status()
                if websocket:
                    await websocket.send(json.dumps({
                        "type": "system_status_response",
                        "data": status
                    }))
            
            elif message_type == "execute_analysis":
                # Execute analysis through appropriate component
                result = await self.execute_analysis(
                    payload.get("analysis_type"),
                    payload.get("context", {})
                )
                if websocket:
                    await websocket.send(json.dumps({
                        "type": "analysis_result",
                        "data": result
                    }))
            
            elif message_type == "agent_chat":
                # Forward to agent system
                if self.agent:
                    response = await self.agent.chat(payload.get("message", ""))
                    if websocket:
                        await websocket.send(json.dumps({
                            "type": "agent_response",
                            "data": {"response": response}
                        }))
            
        except Exception as e:
            logger.error(f"Error handling Electron message: {e}")
            if websocket:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": str(e)
                }))
    
    async def _broadcast_to_electron(self, message: Dict[str, Any]):
        """Broadcast message to all Electron bridges"""
        for bridge_name, bridge in self.electron_bridges.items():
            try:
                if hasattr(bridge, 'emit_event'):
                    await bridge.emit_event(message.get("type", "update"), message.get("data", {}))
                elif hasattr(bridge, 'broadcast'):
                    await bridge.broadcast(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {bridge_name} bridge: {e}")
    
    # Public API methods
    
    async def chat_with_agent(self, message: str) -> tuple[str, List[str]]:
        """Chat with the intelligent agent"""
        if not self.agent:
            raise RuntimeError("Agent system not initialized")
        
        return await self.agent.chat(message)
    
    async def execute_analysis(self, analysis_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute analysis through the core system"""
        if not self.core_system:
            raise RuntimeError("Core system not initialized")
        
        return await self.core_system.execute_analysis(analysis_type, context)
    
    async def get_available_tools(self) -> Dict[str, Any]:
        """Get all available tools from connected servers"""
        if not self.core_system:
            return {}
        
        return self.core_system.get_available_tools()
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            "version": __version__,
            "initialized": self.initialized,
            "running": self.running,
            "electron_mode": self.config.electron_mode,
            "uptime": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "components": {}
        }
        
        # Agent status
        if self.agent:
            status["components"]["agent"] = {
                "status": "running",
                "has_router": self.router is not None,
                "has_coordinator": self.coordinator is not None
            }
        
        # Core system status
        if self.core_system:
            core_status = await self.core_system.get_system_status()
            status["components"]["core"] = core_status
        
        # Server status
        if self.server_orchestrator:
            server_status = await self.server_orchestrator.get_system_status()
            status["components"]["servers"] = server_status
        
        # Electron bridges
        status["electron_bridges"] = list(self.electron_bridges.keys())
        status["background_tasks"] = len(self.background_tasks)
        
        return status
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all components"""
        health_status = {}
        
        # Check agent
        if self.agent:
            try:
                agent_status = get_agent_status()
                # More lenient health check - if agent exists and status is available, consider it healthy
                is_healthy = bool(agent_status and isinstance(agent_status, dict))
                health_status["agent"] = {
                    "healthy": is_healthy,
                    "details": agent_status
                }
            except Exception as e:
                logger.debug(f"Agent health check error: {e}")
                health_status["agent"] = {"healthy": False, "error": str(e)}
        else:
            # If agent component exists but isn't initialized, still consider system partially healthy
            health_status["agent"] = {"healthy": False, "error": "Agent not initialized"}
        
        # Check core system
        if self.core_system:
            try:
                core_health = await self.core_system.health_check()
                # More lenient - check if core system is responsive
                is_healthy = bool(core_health and isinstance(core_health, dict))
                health_status["core"] = {
                    "healthy": is_healthy,
                    "details": core_health
                }
            except Exception as e:
                logger.debug(f"Core system health check error: {e}")
                health_status["core"] = {"healthy": False, "error": str(e)}
        else:
            health_status["core"] = {"healthy": False, "error": "Core system not initialized"}
        
        # Check servers
        if self.server_orchestrator:
            try:
                server_health = await self.server_orchestrator.get_system_status()
                # More lenient - if orchestrator responds, consider it healthy
                is_healthy = bool(server_health and isinstance(server_health, dict))
                health_status["servers"] = {
                    "healthy": is_healthy,
                    "details": server_health
                }
            except Exception as e:
                logger.debug(f"Server orchestrator health check error: {e}")
                health_status["servers"] = {"healthy": False, "error": str(e)}
        else:
            health_status["servers"] = {"healthy": False, "error": "Server orchestrator not initialized"}
        
        return health_status
    
    async def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect metrics from all system components"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "uptime": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "operations_completed": self.metrics["operations_completed"],
            "errors_encountered": self.metrics["errors_encountered"]
        }
        
        # Collect from core system
        if self.core_system and hasattr(self.core_system, 'get_metrics'):
            metrics["core"] = await self.core_system.get_metrics()
        
        # Collect from server orchestrator
        if self.server_orchestrator and hasattr(self.server_orchestrator, 'get_metrics'):
            metrics["servers"] = self.server_orchestrator.get_metrics()
        
        return metrics
    
    async def start_electron_ui(self):
        """Start Electron UI if not already running"""
        if not self.config.electron_mode:
            logger.warning("Electron mode not enabled")
            return
        
        logger.info("🖥️  Starting Electron UI...")
        
        # Start all electron bridges
        for bridge_name, bridge in self.electron_bridges.items():
            try:
                if hasattr(bridge, 'start'):
                    await bridge.start()
                logger.info(f"✅ {bridge_name} Electron bridge started")
            except Exception as e:
                logger.error(f"❌ Failed to start {bridge_name} bridge: {e}")
        
        logger.info("🚀 Electron UI ready for connections")
    
    async def shutdown(self):
        """Gracefully shutdown the entire MCP system"""
        logger.info("🛑 Shutting down MCP System...")
        
        self.running = False
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Shutdown Electron bridges
        for bridge_name, bridge in self.electron_bridges.items():
            try:
                if hasattr(bridge, 'stop'):
                    await bridge.stop()
                logger.info(f"✅ {bridge_name} bridge stopped")
            except Exception as e:
                logger.error(f"Error stopping {bridge_name} bridge: {e}")
        
        # Shutdown unified WebSocket server
        if hasattr(self, 'unified_websocket_server'):
            self.unified_websocket_server.close()
            await self.unified_websocket_server.wait_closed()
        
        # Shutdown core system
        if self.core_system:
            await self.core_system.shutdown()
        
        # Shutdown server orchestrator
        if self.server_orchestrator:
            await self.server_orchestrator.shutdown()
        
        logger.info("✅ MCP System shutdown complete")


# Global system instance
_global_mcp_system: Optional[MCPSystem] = None


async def initialize_mcp_system(config: Union[MCPSystemConfiguration, Dict[str, Any], None] = None) -> MCPSystem:
    """Initialize the global MCP system"""
    global _global_mcp_system
    
    if _global_mcp_system is not None and _global_mcp_system.initialized:
        logger.warning("MCP System already initialized")
        return _global_mcp_system
    
    _global_mcp_system = MCPSystem(config)
    await _global_mcp_system.initialize()
    return _global_mcp_system


def get_mcp_system() -> Optional[MCPSystem]:
    """Get the global MCP system instance"""
    return _global_mcp_system


async def shutdown_mcp_system():
    """Shutdown the global MCP system"""
    global _global_mcp_system
    
    if _global_mcp_system:
        await _global_mcp_system.shutdown()
        _global_mcp_system = None


# Convenience functions for quick access
async def quick_start(
    electron_mode: bool = True,
    debug: bool = False,
    agent_api_key: Optional[str] = None
) -> MCPSystem:
    """Quick start the entire MCP system"""
    config = MCPSystemConfiguration(
        electron_mode=electron_mode,
        debug=debug,
        agent_api_key=agent_api_key
    )
    
    system = await initialize_mcp_system(config)
    
    if electron_mode:
        await system.start_electron_ui()
    
    return system


# Export main components
__all__ = [
    # Main system
    "MCPSystem",
    "MCPSystemConfiguration",
    "initialize_mcp_system",
    "get_mcp_system",
    "shutdown_mcp_system",
    "quick_start",
    
    # Core components
    "MCPCoreSystem",
    "MCPCoreConfiguration",
    
    # Agent components
    "Agent",
    "IntelligentToolRouter",
    "quick_start_bioinformatics_agent",
    
    # Server components
    "MCPServerOrchestrator",
    "ServerConfig",
    "ServerContext",
    
    # Utilities
    "MCPSystemBridge",
    
    # Version info
    "__version__",
    "__author__",
    "__description__"
] 