"""
MCP Core - Unified Model Context Protocol Core System

This module provides a comprehensive, integrated system that combines:
- MCP Client/Server infrastructure
- Domain Expert & Prompt Management
- Registry & Resource Management  
- Analysis Strategy System
- Training Data Collection
- Electron UI/UX Integration

All subsystems are designed to work in tandem with seamless Electron integration.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json

# Core configuration and exceptions
from .config import ServerConfig
from .exceptions import (
    MCPBaseException, SecurityError, ValidationError, 
    ConfigurationError, AnalysisError, ServerError
)

# Analysis interface
from .analysis_interface import (
    AnalysisProvider, BaseAnalysisProvider, 
    scRNASeqAnalysisProvider, ATACSeqAnalysisProvider,
    get_analysis_provider, register_analysis_provider
)

# Local LLM support
from .local_llm import LocalLLMManager, LocalLLMConfig, get_local_llm_manager

# Training collector
from .training_collector import SimpleTrainingCollector as TrainingCollector

# Client subsystem
from .client import (
    MCPClient, ClientConfiguration, OperationResult,
    CacheManager, CacheConfiguration, ConnectionManager, 
    ExecutionEngine, ExecutionConfiguration,
    ResponseFormatter, ElectronResponseFormatter, 
    StandardResponseFormatter, ResponseFormatterFactory
)

# Prompts subsystem  
from .prompts import (
    DomainExpert, DomainPrompt, TechniqueMetadata,
    ExpertiseLevel, BiologicalContext, SecurityLevel,
    get_registry as get_prompt_registry,
    initialize_system as initialize_prompt_system,
    get_system_info as get_prompt_system_info
)

# Registry subsystem
from .registry import (
    MCPRegistry, MCPServerConfig, 
    AutoToolRegistry, AutoResourceRegistry, AutoPromptRegistry,
    get_mcp_registry, ToolConfig, ResourceConfig, PromptConfig
)

# Server subsystem
from .server import (
    MCPServer, BaseMCPServer, MCPTool, MCPResource, MCPPrompt,
    CapabilityManager, ResourceManager, TemplateEngine,
    ValidationSystem, ToolExecutor
)

# Strategy subsystem
from .strategy import (
    AnalysisStrategy, StrategyFactory, WorkflowStep,
    get_system_info as get_strategy_system_info,
    validate_system as validate_strategy_system
)

# Training subsystem
from .training import (
    ConversationCollector as AdvancedTrainingCollector,
    TrainingConfig
)

# Version info
__version__ = "2.0.0"
__author__ = "MCP Core Team"

# Logger setup
logger = logging.getLogger(__name__)

@dataclass
class MCPCoreConfiguration:
    """Comprehensive configuration for the entire MCP Core system"""
    
    # System-wide settings
    name: str = "mcp_core_system"
    version: str = __version__
    debug: bool = False
    electron_mode: bool = True
    
    # Client configuration
    client_config: Optional[ClientConfiguration] = None
    cache_config: Optional[CacheConfiguration] = None
    execution_config: Optional[ExecutionConfiguration] = None
    
    # Server configuration  
    server_config: Optional[ServerConfig] = None
    enable_validation: bool = True
    enable_templates: bool = True
    
    # Registry configuration
    max_servers: int = 10
    auto_discover_servers: bool = True
    enable_server_health_monitoring: bool = True
    
    # Strategy configuration
    default_analysis_types: List[str] = field(default_factory=lambda: ["scrnaseq", "rnaseq", "atacseq"])
    enable_workflow_tracking: bool = True
    
    # Training configuration
    enable_training_collection: bool = True
    training_data_path: Optional[Path] = None
    
    # Electron integration
    electron_bridge_enabled: bool = True
    ui_update_interval: float = 0.1
    websocket_port: int = 8765
    
    # Security settings
    security_level: SecurityLevel = SecurityLevel.PUBLIC
    enable_audit_logging: bool = True
    
    def __post_init__(self):
        """Initialize default configurations if not provided"""
        if self.client_config is None:
            self.client_config = ClientConfiguration(
                name=f"{self.name}_client",
                electron_mode=self.electron_mode,
                ui_update_interval=self.ui_update_interval
            )
        
        if self.server_config is None:
            self.server_config = ServerConfig(
                max_concurrent_servers=self.max_servers,
                electron_mode=self.electron_mode,
                electron_bridge_enabled=self.electron_bridge_enabled
            )
        
        if self.training_data_path is None:
            self.training_data_path = Path.home() / ".mcp_core" / "training"
            self.training_data_path.mkdir(parents=True, exist_ok=True)

class MCPCoreSystem:
    """
    Unified MCP Core System that orchestrates all subsystems
    
    This is the main entry point that coordinates:
    - Client/Server communication
    - Domain expert and prompt management
    - Registry and resource management
    - Analysis strategy execution
    - Training data collection
    - Electron UI/UX integration
    """
    
    def __init__(self, config: Union[MCPCoreConfiguration, Dict[str, Any], None] = None):
        # Configuration setup
        if isinstance(config, dict):
            self.config = MCPCoreConfiguration(**config)
        elif config is None:
            self.config = MCPCoreConfiguration()
        else:
            self.config = config
        
        # System state
        self.initialized = False
        self.running = False
        self._shutdown_event = asyncio.Event()
        
        # Core components (initialized in initialize())
        self.client: Optional[MCPClient] = None
        self.registry: Optional[MCPRegistry] = None
        self.server_instances: Dict[str, MCPServer] = {}
        self.strategy_orchestrator = None
        self.training_collector: Optional[AdvancedTrainingCollector] = None
        self.local_llm_manager: Optional[LocalLLMManager] = None
        
        # Electron integration
        self.electron_bridge = None
        self.websocket_server = None
        
        # Event handlers for UI updates
        self._ui_event_handlers: List[Callable] = []
        
        # Performance metrics
        self.start_time: Optional[datetime] = None
        self.metrics: Dict[str, Any] = {}
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging for the entire system"""
        log_level = logging.DEBUG if self.config.debug else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(self.config.training_data_path / "mcp_core.log")
            ]
        )
        logger.info(f"MCP Core System v{__version__} initialized")
    
    async def initialize(self) -> bool:
        """Initialize all subsystems in proper order"""
        if self.initialized:
            logger.warning("System already initialized")
            return True
        
        try:
            self.start_time = datetime.now()
            logger.info("Initializing MCP Core System...")
            
            # 1. Initialize prompt system (foundation)
            await self._initialize_prompt_system()
            
            # 2. Initialize client system
            await self._initialize_client_system()
            
            # 3. Initialize registry system
            await self._initialize_registry_system()
            
            # 4. Initialize strategy system
            await self._initialize_strategy_system()
            
            # 5. Initialize training system
            await self._initialize_training_system()
            
            # 6. Initialize local LLM if available
            await self._initialize_local_llm()
            
            # 7. Setup Electron integration
            if self.config.electron_mode:
                await self._initialize_electron_integration()
            
            # 8. Start background tasks
            await self._start_background_tasks()
            
            self.initialized = True
            self.running = True
            
            logger.info("MCP Core System initialization complete")
            await self._emit_system_event("system_initialized", {
                "version": __version__,
                "config": self.config.__dict__,
                "initialization_time": (datetime.now() - self.start_time).total_seconds()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP Core System: {e}")
            await self.shutdown()
            raise MCPBaseException(f"System initialization failed: {e}")
    
    async def _initialize_prompt_system(self):
        """Initialize the domain expert and prompt management system"""
        logger.info("Initializing prompt system...")
        
        # Initialize the prompt system with our configuration
        # Disable auto_discover to avoid asyncio.run() conflicts when in async context
        prompt_config = {
            "auto_discover": False,  # Disable to avoid event loop conflicts
            "log_level": "DEBUG" if self.config.debug else "INFO",
            "security_level": self.config.security_level,
            "enable_events": True,
            "enable_performance_monitoring": True
        }
        
        # This initializes the global prompt registry
        initialize_prompt_system(**prompt_config)
        
        # Manually register the core techniques without using asyncio.run()
        try:
            from .prompts.techniques import rnaseq, scrnaseq, atac_seq
            from .prompts import register_expert
            
            # Register experts manually to avoid event loop conflicts
            register_expert(rnaseq.RNASeqDomainExpert, "rnaseq")
            register_expert(scrnaseq.scRNASeqDomainExpert, "scrnaseq") 
            register_expert(atac_seq.ATACSeqDomainExpert, "atacseq")
            
            logger.info("Manually registered core technique experts")
        except ImportError as e:
            logger.warning(f"Could not manually register techniques: {e}")
        
        logger.info("Prompt system initialized")
    
    async def _initialize_client_system(self):
        """Initialize the MCP client system"""
        logger.info("Initializing client system...")
        
        # Create response formatter optimized for Electron
        formatter = ElectronResponseFormatter() if self.config.electron_mode else StandardResponseFormatter()
        
        # Initialize client
        self.client = MCPClient(
            config=self.config.client_config,
            response_formatter=formatter
        )
        
        # Setup event handlers for UI updates
        self.client.ui_event_emitter.on("*", self._handle_client_event)
        
        logger.info("Client system initialized")
    
    async def _initialize_registry_system(self):
        """Initialize the MCP registry system"""
        logger.info("Initializing registry system...")
        
        # Get the global registry instance and pass our client to it
        self.registry = await get_mcp_registry(client=self.client)
        
        # Initialize with our configuration - but skip initialization since we already passed the client
        # The registry was already initialized in get_mcp_registry()
        
        logger.info("Registry system initialized with unified client")
    
    async def _initialize_strategy_system(self):
        """Initialize the analysis strategy system"""
        logger.info("Initializing strategy system...")
        
        # Import and initialize strategy orchestrator
        from .strategy import StrategySystemOrchestrator
        
        self.strategy_orchestrator = StrategySystemOrchestrator(
            debug=self.config.debug
        )
        
        # Validate system
        validation_result = validate_strategy_system()
        if not validation_result.get("valid", False):
            logger.warning(f"Strategy system validation warnings: {validation_result}")
        
        logger.info("Strategy system initialized")
    
    async def _initialize_training_system(self):
        """Initialize the training data collection system"""
        logger.info("Initializing training system...")
        
        # Initialize advanced training collector
        training_config = TrainingConfig(
            data_dir=str(self.config.training_data_path),
            collect_enabled=self.config.enable_training_collection,
            log_level="DEBUG" if self.config.debug else "INFO"
        )
        
        # Use the factory function to create a complete training system
        from .training import create_training_system
        self.training_collector = create_training_system(training_config)
        
        logger.info("Training system initialized")
    
    async def _initialize_local_llm(self):
        """Initialize local LLM support if available"""
        logger.info("Checking for local LLM availability...")
        
        try:
            llm_config = LocalLLMConfig()
            self.local_llm_manager = await get_local_llm_manager(llm_config)
            
            if self.local_llm_manager:
                logger.info("Local LLM system initialized")
            else:
                logger.info("Local LLM not available, using external LLM services")
                
        except Exception as e:
            logger.warning(f"Local LLM initialization failed: {e}")
            self.local_llm_manager = None
    
    async def _initialize_electron_integration(self):
        """Initialize Electron UI/UX integration"""
        logger.info("Initializing Electron integration...")
        
        try:
            # Import electron bridge components
            from .client.electron_bridge import ElectronBridge
            from .server.electron_websocket import WebSocketServer
            
            # Initialize Electron bridge
            self.electron_bridge = ElectronBridge(
                port=self.config.websocket_port,
                update_interval=self.config.ui_update_interval
            )
            
            # Initialize WebSocket server for real-time communication
            self.websocket_server = WebSocketServer(
                port=self.config.websocket_port + 1,
                core_system=self
            )
            
            # Setup event forwarding to Electron
            await self._setup_electron_event_forwarding()
            
            logger.info("Electron integration initialized")
            
        except ImportError:
            logger.warning("Electron bridge components not available, running in standard mode")
            self.config.electron_mode = False
        except Exception as e:
            logger.error(f"Electron integration failed: {e}")
            self.config.electron_mode = False
    
    async def _setup_electron_event_forwarding(self):
        """Setup event forwarding from all subsystems to Electron UI"""
        
        def forward_to_electron(event_data):
            if self.electron_bridge:
                asyncio.create_task(self.electron_bridge.emit_event(event_data))
        
        # Add to our UI event handlers
        self._ui_event_handlers.append(forward_to_electron)
        
        # Setup forwarding from client events
        if self.client:
            self.client.ui_event_emitter.on("*", forward_to_electron)
        
        # Setup forwarding from registry events  
        if self.registry:
            # Registry events are handled through our system events
            pass
        
        logger.info("Electron event forwarding configured")
    
    async def _start_background_tasks(self):
        """Start background monitoring and maintenance tasks"""
        logger.info("Starting background tasks...")
        
        # Start client background tasks
        if self.client:
            await self.client.connection_manager.start()
            await self.client.execution_engine.start_background_tasks()
            await self.client.cache_manager.start_background_tasks()
        
        # Start registry health monitoring
        if self.registry and self.config.enable_server_health_monitoring:
            # Health monitoring is handled internally by registry
            pass
        
        # Start training collection
        # (ConversationCollector is ready to collect data as conversations happen)
        
        # Start Electron communication
        if self.electron_bridge:
            await self.electron_bridge.start()
        
        if self.websocket_server:
            await self.websocket_server.start()
        
        logger.info("Background tasks started")
    
    # Public API methods
    
    async def connect_server(self, server_name: str, server_class: type, **config) -> bool:
        """Connect to an MCP server"""
        if not self.initialized:
            raise MCPBaseException("System not initialized")
        
        try:
            # Create server instance
            server_instance = server_class()
            await server_instance.initialize()
            
            # Connect through client
            result = await self.client.connect_server(
                server_instance, 
                server_name, 
                **config
            )
            
            if result.success:
                self.server_instances[server_name] = server_instance
                await self._emit_system_event("server_connected", {
                    "server_name": server_name,
                    "server_class": server_class.__name__
                })
            
            return result.success
            
        except Exception as e:
            logger.error(f"Failed to connect server {server_name}: {e}")
            return False
    
    async def execute_analysis(self, analysis_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a complete analysis workflow"""
        if not self.initialized:
            raise MCPBaseException("System not initialized")
        
        try:
            # Create analysis strategy
            strategy = self.strategy_orchestrator.create_strategy(analysis_type)
            
            # Get workflow steps
            workflow_steps = self.strategy_orchestrator.get_workflow_steps(analysis_type)
            
            # Execute workflow through client
            results = []
            for step in workflow_steps:
                if step.get("type") == "tool_execution":
                    result = await self.client.execute_tool(
                        step["tool_name"],
                        step.get("parameters", {}),
                        timeout=step.get("timeout")
                    )
                    results.append(result)
                elif step.get("type") == "resource_access":
                    result = await self.client.get_resource(
                        step["uri"],
                        timeout=step.get("timeout")
                    )
                    results.append(result)
            
            # Collect training data
            if self.training_collector and self.config.enable_training_collection:
                await self.training_collector.collect_conversation_turn(
                    user_message=context.get("user_query", ""),
                    assistant_response=str(results),
                    session_id=context.get("session_id"),
                    additional_context={"analysis_type": analysis_type, "workflow_results": results},
                    success=all(r.success for r in results if hasattr(r, 'success'))
                )
            
            # Generate insights and actions
            insights = self.strategy_orchestrator.get_insights(analysis_type, context)
            actions = self.strategy_orchestrator.get_actions(analysis_type, context)
            
            analysis_result = {
                "analysis_type": analysis_type,
                "workflow_results": results,
                "insights": insights,
                "suggested_actions": actions,
                "timestamp": datetime.now().isoformat(),
                "success": all(r.success for r in results if hasattr(r, 'success'))
            }
            
            await self._emit_system_event("analysis_completed", analysis_result)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Analysis execution failed: {e}")
            raise AnalysisError(f"Analysis failed: {e}", technique=analysis_type)
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            "initialized": self.initialized,
            "running": self.running,
            "version": __version__,
            "uptime": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "electron_mode": self.config.electron_mode,
            "subsystems": {}
        }
        
        if self.client:
            status["subsystems"]["client"] = self.client.get_client_status()
        
        if self.registry:
            status["subsystems"]["registry"] = self.registry.get_registry_stats()
        
        if self.strategy_orchestrator:
            status["subsystems"]["strategy"] = self.strategy_orchestrator.get_system_status()
        
        if self.training_collector:
            status["subsystems"]["training"] = {
                "enabled": self.config.enable_training_collection,
                "collecting": self.training_collector.is_collecting(),
                "current_session_turns": len(self.training_collector.get_current_session_turns()),
                "config": self.training_collector.config.to_dict()
            }
        
        # Add server status
        status["servers"] = {
            name: {
                "connected": True,
                "type": type(server).__name__
            }
            for name, server in self.server_instances.items()
        }
        
        return status
    
    def get_available_tools(self) -> Dict[str, Any]:
        """Get all available tools from the client system"""
        if not self.client:
            return {}
        
        # First try client system (for properly connected servers)
        client_tools = self.client.get_available_tools()
        
        # If client has no tools but registry has connected servers, query registry directly
        if len(client_tools) == 0 and self.registry:
            try:
                # Use registry's built-in methods instead of accessing internals
                registry_tools = self.registry.get_available_tools()
                if registry_tools:
                    logger.info(f"Retrieved {len(registry_tools)} tools from registry")
                    return registry_tools
            except Exception as e:
                logger.error(f"Failed to query registry for tools: {e}")
        
        return client_tools
    
    def get_available_resources(self) -> Dict[str, Any]:
        """Get all available resources from the client system"""
        if not self.client:
            return {}
        return self.client.get_available_resources()
    
    def get_available_prompts(self) -> Dict[str, Any]:
        """Get all available prompts from the client system"""
        if not self.client:
            return {}
        return self.client.get_available_prompts()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        health_status = {
            "overall_health": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        
        # Client health
        if self.client:
            try:
                client_health = await self.client.health_check()
                health_status["checks"]["client"] = {
                    "status": "healthy" if all(client_health.values()) else "degraded",
                    "details": client_health
                }
            except Exception as e:
                health_status["checks"]["client"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        # Registry health
        if self.registry:
            try:
                registry_health = await self.registry.health_check()
                health_status["checks"]["registry"] = {
                    "status": "healthy" if all(registry_health.values()) else "degraded",
                    "details": registry_health
                }
            except Exception as e:
                health_status["checks"]["registry"] = {
                    "status": "unhealthy", 
                    "error": str(e)
                }
        
        # Strategy system health
        if self.strategy_orchestrator:
            try:
                strategy_health = await self.strategy_orchestrator.health_check()
                health_status["checks"]["strategy"] = strategy_health
            except Exception as e:
                health_status["checks"]["strategy"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        # Determine overall health
        unhealthy_systems = [
            name for name, check in health_status["checks"].items()
            if check.get("status") == "unhealthy"
        ]
        
        if unhealthy_systems:
            health_status["overall_health"] = "unhealthy"
        elif any(check.get("status") == "degraded" for check in health_status["checks"].values()):
            health_status["overall_health"] = "degraded"
        
        return health_status
    
    def register_ui_event_handler(self, handler: Callable):
        """Register a custom UI event handler"""
        self._ui_event_handlers.append(handler)
    
    async def _handle_client_event(self, event_data):
        """Handle events from the client system"""
        # Forward to all UI event handlers
        for handler in self._ui_event_handlers:
            try:
                handler(event_data)
            except Exception as e:
                logger.error(f"UI event handler error: {e}")
    
    async def _emit_system_event(self, event_type: str, data: Any):
        """Emit system-wide events"""
        event_data = {
            "event": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "source": "mcp_core_system"
        }
        
        # Forward to UI handlers
        for handler in self._ui_event_handlers:
            try:
                handler(event_data)
            except Exception as e:
                logger.error(f"System event handler error: {e}")
        
        logger.debug(f"System event emitted: {event_type}")
    
    async def shutdown(self):
        """Gracefully shutdown the entire system"""
        if not self.running:
            return
        
        logger.info("Shutting down MCP Core System...")
        self.running = False
        
        try:
            # Stop background tasks
            if self.client:
                await self.client.connection_manager.stop()
                await self.client.execution_engine.stop_background_tasks()
                await self.client.cache_manager.stop_background_tasks()
            
            if self.training_collector:
                await self.training_collector.finalize_session()
            
            if self.electron_bridge:
                await self.electron_bridge.stop()
            
            if self.websocket_server:
                await self.websocket_server.stop()
            
            # Disconnect servers
            for server_name in list(self.server_instances.keys()):
                try:
                    await self.client.disconnect_server(server_name)
                except Exception as e:
                    logger.error(f"Error disconnecting server {server_name}: {e}")
            
            # Shutdown client
            if self.client:
                await self.client.shutdown()
            
            # Cleanup strategy system
            if self.strategy_orchestrator:
                self.strategy_orchestrator.shutdown()
            
            # Cleanup LLM manager
            if self.local_llm_manager:
                await self.local_llm_manager.cleanup()
            
            await self._emit_system_event("system_shutdown", {
                "uptime": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            })
            
            logger.info("MCP Core System shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Global system instance
_global_system: Optional[MCPCoreSystem] = None

async def initialize_mcp_core(config: Union[MCPCoreConfiguration, Dict[str, Any], None] = None) -> MCPCoreSystem:
    """Initialize the global MCP Core system"""
    global _global_system
    
    if _global_system is not None and _global_system.initialized:
        logger.warning("MCP Core system already initialized")
        return _global_system
    
    _global_system = MCPCoreSystem(config)
    await _global_system.initialize()
    return _global_system

def get_mcp_core() -> Optional[MCPCoreSystem]:
    """Get the global MCP Core system instance"""
    return _global_system

async def shutdown_mcp_core():
    """Shutdown the global MCP Core system"""
    global _global_system
    if _global_system:
        await _global_system.shutdown()
        _global_system = None

# Convenience functions for common operations
async def execute_analysis(analysis_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute analysis using the global system"""
    system = get_mcp_core()
    if not system:
        raise MCPBaseException("MCP Core system not initialized. Call initialize_mcp_core() first.")
    return await system.execute_analysis(analysis_type, context)

async def connect_server(server_name: str, server_class: type, **config) -> bool:
    """Connect server using the global system"""
    system = get_mcp_core()
    if not system:
        raise MCPBaseException("MCP Core system not initialized. Call initialize_mcp_core() first.")
    return await system.connect_server(server_name, server_class, **config)

async def get_system_status() -> Dict[str, Any]:
    """Get system status using the global system"""
    system = get_mcp_core()
    if not system:
        return {"error": "MCP Core system not initialized"}
    return await system.get_system_status()

# Export main classes and functions
__all__ = [
    # Core system
    "MCPCoreSystem", "MCPCoreConfiguration",
    "initialize_mcp_core", "get_mcp_core", "shutdown_mcp_core",
    
    # Convenience functions
    "execute_analysis", "connect_server", "get_system_status",
    
    # Configuration
    "ServerConfig", 
    
    # Exceptions
    "MCPBaseException", "SecurityError", "ValidationError", 
    "ConfigurationError", "AnalysisError", "ServerError",
    
    # Analysis interface
    "AnalysisProvider", "BaseAnalysisProvider", 
    "scRNASeqAnalysisProvider", "ATACSeqAnalysisProvider",
    "get_analysis_provider", "register_analysis_provider",
    
    # Local LLM
    "LocalLLMManager", "LocalLLMConfig", "get_local_llm_manager",
    
    # Training
    "TrainingCollector",
    
    # Client components
    "MCPClient", "ClientConfiguration", "OperationResult",
    "CacheManager", "CacheConfiguration", "ConnectionManager", 
    "ExecutionEngine", "ExecutionConfiguration",
    "ResponseFormatter", "ElectronResponseFormatter", 
    "StandardResponseFormatter", "ResponseFormatterFactory",
    
    # Prompt components
    "DomainExpert", "DomainPrompt", "TechniqueMetadata",
    "ExpertiseLevel", "BiologicalContext", "SecurityLevel",
    "get_prompt_registry", "initialize_prompt_system",
    "get_prompt_system_info",
    
    # Registry components
    "MCPRegistry", "MCPServerConfig", 
    "AutoToolRegistry", "AutoResourceRegistry", "AutoPromptRegistry",
    "get_mcp_registry", "ToolConfig", "ResourceConfig", "PromptConfig",
    
    # Server components
    "MCPServer", "BaseMCPServer", "MCPTool", "MCPResource", "MCPPrompt",
    "CapabilityManager", "ResourceManager", "TemplateEngine",
    "ValidationSystem", "ToolExecutor",
    
    # Strategy components
    "AnalysisStrategy", "StrategyFactory", "WorkflowStep",
    "get_strategy_system_info", "validate_strategy_system",
    
    # Training components (advanced)
    "AdvancedTrainingCollector", "TrainingConfig",
    
    # Version info
    "__version__", "__author__"
] 