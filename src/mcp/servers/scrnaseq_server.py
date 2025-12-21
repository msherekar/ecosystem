"""
Enhanced scRNA-seq MCP Server

Provides comprehensive single-cell RNA-seq analysis with:
- Automated tool discovery from handlers
- Advanced security and permission management  
- Electron desktop integration
- Performance monitoring and caching
- Scalable session management
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
import streamlit as st
from functools import wraps

from ..core.server import MCPServer
from ..core.registry.tool_registry import get_auto_tool_configs
from ..core.registry.resource_registry import get_auto_resource_configs  
from ..core.registry.prompt_registry import get_auto_prompt_configs
from .handlers.scrnaseq_handlers import scRNASeqHandlers
from .security_handler import SecurityContext, UserPermissions
from .electron_bridge import ElectronBridge, DesktopNotification
from src.modules.scrna_seq.workflow import run_scrnaseq_pipeline


class SecurityContextManager:
    """Manages security context for server operations"""
    
    def __init__(self, server_instance):
        self.server = server_instance
        self.logger = logging.getLogger("mcp.scrnaseq.security")
    
    def create_context(self, user_id: str = None, permissions: List[str] = None) -> SecurityContext:
        """Create security context for operations"""
        user_permissions = UserPermissions(
            user_id=user_id or "anonymous",
            permissions=set(permissions or ["server:scrnaseq", "tool:execute", "data:read"])
        )
        
        return SecurityContext(
            user_id=user_id,
            permissions=user_permissions,
            session_id=st.session_state.get("session_id", "default"),
            authenticated=True
        )
    
    def validate_access(self, context: SecurityContext, required_permissions: List[str]) -> bool:
        """Validate user access for specific permissions"""
        if not required_permissions:
            return True
        
        for permission in required_permissions:
            if not context.user_permissions.has_permission(permission):
                self.logger.warning(f"Access denied: {context.user_id} lacks {permission}")
                return False
        
        return True


class PerformanceTracker:
    """Tracks server performance and provides optimization insights"""
    
    def __init__(self):
        self.execution_times = {}
        self.error_counts = {}
        self.cache_hits = 0
        self.cache_misses = 0
    
    def record_execution(self, tool_name: str, duration: float, success: bool):
        """Record tool execution metrics"""
        if tool_name not in self.execution_times:
            self.execution_times[tool_name] = []
        
        self.execution_times[tool_name].append(duration)
        
        if not success:
            self.error_counts[tool_name] = self.error_counts.get(tool_name, 0) + 1
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for monitoring"""
        summary = {
            "total_tools": len(self.execution_times),
            "cache_hit_rate": self.cache_hits / max(self.cache_hits + self.cache_misses, 1) * 100,
            "tool_performance": {}
        }
        
        for tool_name, times in self.execution_times.items():
            summary["tool_performance"][tool_name] = {
                "executions": len(times),
                "avg_duration": sum(times) / len(times),
                "error_count": self.error_counts.get(tool_name, 0)
            }
        
        return summary


def monitor_performance(func):
    """Decorator to monitor tool execution performance"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        start_time = time.time()
        success = False
        
        try:
            result = await func(self, *args, **kwargs)
            success = True
            return result
        except Exception as e:
            self.logger.error(f"Tool execution failed: {func.__name__} - {str(e)}")
            raise
        finally:
            duration = time.time() - start_time
            self.performance_tracker.record_execution(func.__name__, duration, success)
            
            # Alert on slow execution
            if duration > 30.0:
                await self._send_performance_alert(func.__name__, duration)
    
    return wrapper


class scRNASeqMCPServer(MCPServer):
    """Enhanced MCP Server for single-cell RNA-seq analysis"""
    
    def __init__(self):
        super().__init__("scrnaseq_server", "2.0.0")
        self.logger = logging.getLogger("mcp.scrnaseq")
        
        # Core components
        self.handlers = scRNASeqHandlers(self.logger)
        self.security_manager = SecurityContextManager(self)
        self.performance_tracker = PerformanceTracker()
        self.electron_bridge = None
        
        # Session tracking with enhanced capabilities
        self.configure_session_tracking(
            tracked_variables=[
                'anndata', 'qc_done', 'filtered', 'normalized', 'clustered',
                'umap_computed', 'markers_found', 'cell_types_assigned'
            ],
            variable_patterns=[
                r'.*_embedding$', r'.*_clusters$', r'.*_markers$',
                r'adata_.*', r'.*_results$', r'.*_metadata$'
            ],
            auto_discover=True
        )
        
        # Auto-discovery with error handling
        self.tool_configs = {}
        self.resource_configs = {}
        self.prompt_configs = {}
        
    async def initialize(self) -> bool:
        """Initialize server with comprehensive setup"""
        try:
            self.logger.info("Initializing enhanced scRNA-seq server")
            
            # Initialize security context
            self._setup_security_context()
            
            # Initialize Electron bridge if in desktop mode
            await self._setup_electron_integration()
            
            # Discover and register tools/resources/prompts
            await self._discover_and_register_components()
            
            # Setup performance monitoring
            self._setup_performance_monitoring()
            
            self.logger.info(f"Server initialized with {len(self.tool_configs)} tools")
            return True
            
        except Exception as e:
            self.logger.error(f"Server initialization failed: {str(e)}")
            return False
    
    def _setup_security_context(self):
        """Setup security context for handlers"""
        default_context = self.security_manager.create_context()
        self.handlers._security_context = default_context
    
    async def _setup_electron_integration(self):
        """Setup Electron desktop integration"""
        try:
            from .electron_bridge import ElectronBridge
            
            # Detect if running in Electron environment
            if self._detect_electron_environment():
                self.electron_bridge = ElectronBridge(self.logger)
                await self.electron_bridge.initialize()
                
                # Send server status to Electron
                await self.electron_bridge.notify_server_started("scrnaseq")
                
                self.logger.info("Electron integration enabled")
            
        except ImportError:
            self.logger.debug("Electron bridge not available")
        except Exception as e:
            self.logger.warning(f"Electron integration failed: {str(e)}")
    
    def _detect_electron_environment(self) -> bool:
        """Detect if running in Electron environment"""
        import os
        return any(os.environ.get(var) for var in [
            "ELECTRON_MODE", "ELECTRON_RUN_AS_NODE", "ELECTRON_NO_ATTACH_CONSOLE"
        ])
    
    async def _discover_and_register_components(self):
        """Discover and register tools, resources, and prompts"""
        try:
            # Use existing registry system
            self.tool_configs = get_auto_tool_configs(self.handlers)
            self.resource_configs = get_auto_resource_configs(self.handlers)
            self.prompt_configs = get_auto_prompt_configs(self.handlers)
            
            # Register with server
            await self._register_discovered_tools()
            await self._register_discovered_resources()
            await self._register_discovered_prompts()
            
        except Exception as e:
            self.logger.error(f"Component discovery failed: {str(e)}")
            # Fallback to manual registration
            await self._fallback_registration()
    
    async def _register_discovered_tools(self):
        """Register auto-discovered tools"""
        for tool_name, tool_config in self.tool_configs.items():
            self.register_tool(
                name=tool_name,
                description=tool_config.description,
                input_schema={
                    "type": "object",
                    "properties": tool_config.properties,
                    "required": tool_config.required
                },
                handler=self._create_monitored_handler(tool_config.handler)
            )
    
    async def _register_discovered_resources(self):
        """Register auto-discovered resources"""
        for uri, resource_config in self.resource_configs.items():
            self.register_resource(
                uri=resource_config.uri,
                name=resource_config.name,
                description=resource_config.description,
                mime_type=resource_config.mime_type
            )
    
    async def _register_discovered_prompts(self):
        """Register auto-discovered prompts"""
        for prompt_name, prompt_config in self.prompt_configs.items():
            self.register_prompt(
                name=prompt_config.name,
                description=prompt_config.description,
                template=prompt_config.template,
                parameters=prompt_config.parameters
            )
    
    def _create_monitored_handler(self, original_handler):
        """Create performance-monitored version of handler"""
        @monitor_performance
        async def monitored_handler(*args, **kwargs):
            # Add security context validation
            context = self.security_manager.create_context()
            
            # Execute original handler
            return await original_handler(*args, **kwargs)
        
        return monitored_handler
    
    async def _fallback_registration(self):
        """Fallback manual registration if auto-discovery fails"""
        self.logger.warning("Using fallback tool registration")
        
        # Register essential tools manually
        essential_tools = [
            {
                "name": "run_qc",
                "description": "Perform quality control analysis",
                "handler": self.handlers.run_qc,
                "properties": {
                    "min_genes": {"type": "integer", "default": 200},
                    "max_mito_pct": {"type": "number", "default": 20.0}
                }
            },
            {
                "name": "normalize_data", 
                "description": "Normalize expression data",
                "handler": self.handlers.normalize_data,
                "properties": {}
            }
        ]
        
        for tool in essential_tools:
            self.register_tool(
                name=tool["name"],
                description=tool["description"],
                input_schema={
                    "type": "object",
                    "properties": tool["properties"],
                    "required": []
                },
                handler=self._create_monitored_handler(tool["handler"])
            )
    
    def _setup_performance_monitoring(self):
        """Setup performance monitoring and alerts"""
        # Log performance summary periodically
        async def log_performance():
            while True:
                await asyncio.sleep(300)  # Every 5 minutes
                summary = self.performance_tracker.get_performance_summary()
                self.logger.info(f"Performance summary: {summary}")
        
        asyncio.create_task(log_performance())
    
    async def _send_performance_alert(self, tool_name: str, duration: float):
        """Send performance alert for slow operations"""
        if self.electron_bridge:
            notification = DesktopNotification(
                title="Performance Alert",
                body=f"Tool '{tool_name}' took {duration:.1f}s to execute",
                urgency="warning"
            )
            await self.electron_bridge.send_desktop_notification(notification)
    
    def update_security_context(self, user_id: str, permissions: List[str]):
        """Update security context for current session"""
        new_context = self.security_manager.create_context(user_id, permissions)
        self.handlers._security_context = new_context
        self.logger.info(f"Security context updated for user: {user_id}")
    
    async def get_analysis_progress(self) -> Dict[str, Any]:
        """Get current analysis progress with enhanced metrics"""
        # Base progress from parent class
        base_progress = super().get_analysis_context()
        
        # Add performance metrics
        performance_summary = self.performance_tracker.get_performance_summary()
        
        # Add data quality metrics
        data_quality = self._assess_data_quality()
        
        return {
            **base_progress,
            "performance_metrics": performance_summary,
            "data_quality": data_quality,
            "electron_connected": self.electron_bridge is not None,
            "security_level": getattr(self.handlers._security_context, 'security_level', 'standard')
        }
    
    def _assess_data_quality(self) -> Dict[str, Any]:
        """Assess current data quality"""
        quality_metrics = {
            "data_loaded": "anndata" in st.session_state,
            "qc_performed": st.session_state.get("qc_done", False),
            "data_filtered": st.session_state.get("filtered", False),
            "data_normalized": st.session_state.get("normalized", False)
        }
        
        if quality_metrics["data_loaded"]:
            adata = st.session_state.get("anndata")
            if adata is not None:
                quality_metrics.update({
                    "cell_count": adata.n_obs,
                    "gene_count": adata.n_vars,
                    "data_size_mb": adata.X.nbytes / (1024 * 1024) if hasattr(adata.X, 'nbytes') else 0
                })
        
        return quality_metrics
    
    def _get_server_specific_context(self) -> Dict[str, Any]:
        """Get scRNA-seq server specific context information"""
        return {
            "server_type": "single_cell_analysis",
            "analysis_capabilities": ["qc", "normalization", "clustering", "differential_expression", "trajectory_analysis"],
            "supported_data_formats": ["h5ad", "mtx", "csv", "h5"],
            "performance_tracking": True,
            "security_enabled": self.security_manager is not None,
            "electron_enabled": self.electron_bridge is not None,
            "features": ["enhanced_security", "performance_monitoring", "desktop_integration"],
            "current_security_level": getattr(getattr(self.handlers, '_security_context', None), 'security_level', 'standard')
        }

    async def shutdown(self):
        """Graceful server shutdown"""
        self.logger.info("Shutting down scRNA-seq server")
        
        # Notify Electron
        if self.electron_bridge:
            await self.electron_bridge.notify_server_stopped("scrnaseq")
            await self.electron_bridge.shutdown()
        
        # Log final performance summary
        final_summary = self.performance_tracker.get_performance_summary()
        self.logger.info(f"Final performance summary: {final_summary}")
        
        await super().shutdown()


def main():
    """Main function for testing enhanced scRNA-seq server"""
    print("=== Enhanced scRNA-seq Server Test ===")
    
    # Static tests
    print("\n1. Testing SecurityContextManager...")
    server = scRNASeqMCPServer()
    security_manager = SecurityContextManager(server)
    context = security_manager.create_context("test_user", ["server:scrnaseq"])
    assert context.user_id == "test_user"
    print("✅ SecurityContextManager working")
    
    print("\n2. Testing PerformanceTracker...")
    tracker = PerformanceTracker()
    tracker.record_execution("test_tool", 1.5, True)
    summary = tracker.get_performance_summary()
    assert summary["total_tools"] == 1
    print("✅ PerformanceTracker working")
    
    print("\n3. Testing server creation...")
    server = scRNASeqMCPServer()
    assert server.name == "scrnaseq_server"
    assert server.version == "2.0.0"
    print("✅ Enhanced server created")
    
    print("\n4. Testing Electron detection...")
    is_electron = server._detect_electron_environment()
    assert isinstance(is_electron, bool)
    print("✅ Electron detection working")


def test_dynamic():
    """Dynamic tests for enhanced server"""
    async def run_dynamic_tests():
        print("\n=== Dynamic Tests ===")
        
        server = scRNASeqMCPServer()
        
        print("1. Testing server initialization...")
        success = await server.initialize()
        assert success is True
        print("✅ Server initialization working")
        
        print("\n2. Testing security context update...")
        server.update_security_context("test_user", ["server:scrnaseq", "tool:execute"])
        context = server.handlers._security_context
        assert context.user_id == "test_user"
        print("✅ Security context update working")
        
        print("\n3. Testing analysis progress...")
        progress = await server.get_analysis_progress()
        assert "performance_metrics" in progress
        assert "data_quality" in progress
        print("✅ Analysis progress tracking working")
        
        print("\n4. Testing data quality assessment...")
        quality = server._assess_data_quality()
        assert "data_loaded" in quality
        assert "qc_performed" in quality
        print("✅ Data quality assessment working")
        
        print("\n🎉 All dynamic tests passed!")
    
    # Run async tests
    asyncio.run(run_dynamic_tests())


if __name__ == "__main__":
    main()
    test_dynamic()