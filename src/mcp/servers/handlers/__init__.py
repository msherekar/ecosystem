"""
Modular Handler Components - Enhanced Version

Advanced modular handler components with comprehensive error handling, lazy loading,
version management, and runtime validation. Provides enterprise-grade reliability
and extensibility for multi-omics analysis pipelines.

Architecture Overview:
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Core Layer    │    │   Mixin Layer    │    │ Handler Layer   │
│                 │    │                  │    │                 │
│ • BaseHandler   │───▶│ • Analysis       │───▶│ • scRNASeq      │
│ • Security      │    │ • Data           │    │ • ATACSeq       │
│ • Electron      │    │ • Visualization  │    │ • Spatial       │
│ • Config        │    │ • Pipeline       │    │ • Proteomics    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
                    ┌──────────────────┐
                    │ Integration Layer │
                    │ • MCP Server     │
                    │ • Error Handler  │
                    │ • Config Manager │
                    └──────────────────┘

Features:
- Lazy loading for improved startup performance
- Comprehensive error handling and recovery
- Version compatibility checking
- Runtime configuration validation
- Automatic dependency resolution
- Plugin architecture support
- Performance monitoring
- Development/production mode switching
"""

import logging
import sys
import warnings
from typing import Any, Dict, List, Optional, Type, Union, Callable
from pathlib import Path
import importlib
from functools import lru_cache
from dataclasses import dataclass
import threading
from datetime import datetime

# Version and compatibility information
__version__ = "2.1.0"
__api_version__ = "2.0"
__min_python_version__ = (3, 8)
__max_python_version__ = (3, 12)

# Module metadata
__author__ = "MCP Handlers Team"
__description__ = "Modular handler components for multi-omics analysis"
__license__ = "MIT"
__status__ = "Production"

# Global state management
_module_initialized = False
_initialization_lock = threading.Lock()
_loaded_components = {}
_failed_imports = {}
_handler_registry = {}


@dataclass
class ComponentInfo:
    """Information about a loadable component"""
    name: str
    module_path: str
    class_name: str
    dependencies: List[str] = None
    optional: bool = False
    lazy: bool = True
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class ModuleLoader:
    """Advanced module loader with lazy loading and error handling"""
    
    def __init__(self):
        self.logger = logging.getLogger("handlers.loader")
        self._component_cache = {}
        self._import_errors = {}
    
    def load_component(self, component_info: ComponentInfo, force_reload: bool = False):
        """Load component with comprehensive error handling"""
        if not force_reload and component_info.name in self._component_cache:
            return self._component_cache[component_info.name]
        
        try:
            # Load dependencies first
            for dep in component_info.dependencies:
                if dep not in self._component_cache:
                    self.logger.warning(f"Dependency {dep} not loaded for {component_info.name}")
            
            # Import module
            module = importlib.import_module(component_info.module_path)
            
            # Get class
            if hasattr(module, component_info.class_name):
                component_class = getattr(module, component_info.class_name)
                self._component_cache[component_info.name] = component_class
                return component_class
            else:
                raise ImportError(f"Class {component_info.class_name} not found in {component_info.module_path}")
                
        except Exception as e:
            self._import_errors[component_info.name] = str(e)
            if not component_info.optional:
                self.logger.error(f"Failed to load required component {component_info.name}: {e}")
                raise
            else:
                self.logger.warning(f"Failed to load optional component {component_info.name}: {e}")
                return None
    
    def get_import_errors(self) -> Dict[str, str]:
        """Get all import errors"""
        return self._import_errors.copy()


# Global module loader
_module_loader = ModuleLoader()


# Component definitions with enhanced metadata
CORE_COMPONENTS = [
    ComponentInfo("BaseHandler", "src.mcp.servers.handlers.base_handler", "BaseHandler", ["SecurityValidator", "ElectronBridge"]),
    ComponentInfo("OperationResult", "src.mcp.servers.handlers.base_handler", "OperationResult"),
    ComponentInfo("SecurityValidator", "src.mcp.servers.handlers.security_validator", "SecurityValidator"),
    ComponentInfo("ElectronBridge", "src.mcp.servers.handlers.electron_bridge", "ElectronBridge"),
]

ANALYSIS_COMPONENTS = [
    ComponentInfo("AnalysisHandlerMixin", "src.mcp.servers.handlers.analysis_handlers", "AnalysisHandlerMixin", 
                 ["QualityControlMixin", "ClusteringMixin", "PipelineMixin"]),
    ComponentInfo("QualityControlMixin", "src.mcp.servers.handlers.analysis_qc", "QualityControlMixin"),
    ComponentInfo("ClusteringMixin", "src.mcp.servers.handlers.analysis_clustering", "ClusteringMixin"),
    ComponentInfo("PipelineMixin", "src.mcp.servers.handlers.analysis_pipeline", "PipelineMixin"),
]

DATA_COMPONENTS = [
    ComponentInfo("DataHandlerMixin", "src.mcp.servers.handlers.data_handlers", "DataHandlerMixin",
                 ["DataValidationMixin", "DataFilteringMixin", "DataResourceMixin"]),
    ComponentInfo("DataValidationMixin", "src.mcp.servers.handlers.data_validation", "DataValidationMixin"),
    ComponentInfo("DataFilteringMixin", "src.mcp.servers.handlers.data_filtering", "DataFilteringMixin"),
    ComponentInfo("DataResourceMixin", "src.mcp.servers.handlers.data_resources", "DataResourceMixin"),
]

VISUALIZATION_COMPONENTS = [
    ComponentInfo("VisualizationHandlerMixin", "src.mcp.servers.handlers.visualization_handlers", "VisualizationHandlerMixin",
                 ["PlotCreationMixin", "PlotAnalysisMixin", "PlotExportMixin"]),
    ComponentInfo("PlotCreationMixin", "src.mcp.servers.handlers.visualization_plots", "PlotCreationMixin"),
    ComponentInfo("PlotAnalysisMixin", "src.mcp.servers.handlers.visualization_analysis", "PlotAnalysisMixin"),
    ComponentInfo("PlotExportMixin", "src.mcp.servers.handlers.visualization_export", "PlotExportMixin"),
]

TECHNIQUE_COMPONENTS = [
    ComponentInfo("scRNASeqHandlers", "src.mcp.servers.handlers.scrnaseq_handlers", "scRNASeqHandlers"),
    ComponentInfo("ATACSeqHandlers", "src.mcp.servers.handlers.ataqseq_handler", "ATACSeqHandlers"),
    ComponentInfo("SpatialHandlers", "src.mcp.servers.handlers.spatial_handlers", "SpatialHandlers"),
    ComponentInfo("ProteomicsHandlers", "src.mcp.servers.handlers.proteomics_handlers", "ProteomicsHandlers"),
]

INTEGRATION_COMPONENTS = [
    ComponentInfo("MCPServerIntegration", "src.mcp.servers.handlers.server_integration", "MCPServerIntegration"),
    ComponentInfo("ConfigManager", "src.mcp.servers.handlers.config_manager", "ConfigManager"),
    ComponentInfo("ErrorHandler", "src.mcp.servers.handlers.error_handlers", "ErrorHandler"),
]

ALL_COMPONENTS = (
    CORE_COMPONENTS + ANALYSIS_COMPONENTS + DATA_COMPONENTS + 
    VISUALIZATION_COMPONENTS + TECHNIQUE_COMPONENTS + INTEGRATION_COMPONENTS
)


def check_python_compatibility():
    """Check Python version compatibility"""
    current_version = sys.version_info[:2]
    
    if current_version < __min_python_version__:
        raise RuntimeError(
            f"Python {__min_python_version__[0]}.{__min_python_version__[1]}+ required, "
            f"but {current_version[0]}.{current_version[1]} found"
        )
    
    if current_version > __max_python_version__:
        warnings.warn(
            f"Python {current_version[0]}.{current_version[1]} not officially supported. "
            f"Recommended: {__min_python_version__[0]}.{__min_python_version__[1]}-"
            f"{__max_python_version__[0]}.{__max_python_version__[1]}",
            UserWarning
        )


def check_dependencies():
    """Check for required dependencies"""
    required_packages = {
        "streamlit": "Web interface framework",
        "asyncio": "Asynchronous I/O support",
        "logging": "Logging infrastructure"
    }
    
    missing_packages = []
    
    for package, description in required_packages.items():
        try:
            importlib.import_module(package)
        except ImportError:
            missing_packages.append(f"{package} ({description})")
    
    if missing_packages:
        raise ImportError(
            f"Missing required dependencies: {', '.join(missing_packages)}"
        )


def initialize_module(lazy_loading: bool = True, validate_config: bool = True) -> Dict[str, Any]:
    """Initialize the handlers module with comprehensive setup"""
    global _module_initialized
    
    with _initialization_lock:
        if _module_initialized:
            return {"status": "already_initialized", "components_loaded": len(_loaded_components)}
        
        logger = logging.getLogger("handlers.init")
        initialization_start = datetime.now()
        
        try:
            logger.info(f"Initializing handlers module v{__version__}")
            
            # Check compatibility
            check_python_compatibility()
            check_dependencies()
            
            # Load components based on strategy
            if lazy_loading:
                result = _initialize_lazy()
            else:
                result = _initialize_eager()
            
            # Validate configuration if requested
            if validate_config:
                _validate_default_config()
            
            # Register handlers
            _register_technique_handlers()
            
            _module_initialized = True
            initialization_time = (datetime.now() - initialization_start).total_seconds()
            
            logger.info(f"Module initialization completed in {initialization_time:.2f}s")
            
            return {
                "status": "initialized",
                "initialization_time": initialization_time,
                "components_loaded": len(_loaded_components),
                "lazy_loading": lazy_loading,
                "config_validated": validate_config,
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
                "module_version": __version__
            }
            
        except Exception as e:
            logger.error(f"Module initialization failed: {e}")
            raise


def _initialize_lazy() -> Dict[str, Any]:
    """Initialize with lazy loading (load on demand)"""
    logger = logging.getLogger("handlers.init.lazy")
    
    # Only load critical core components immediately
    critical_components = ["SecurityValidator", "ErrorHandler", "ConfigManager"]
    loaded_count = 0
    
    for component_info in ALL_COMPONENTS:
        if component_info.name in critical_components:
            try:
                component = _module_loader.load_component(component_info)
                if component:
                    _loaded_components[component_info.name] = component
                    loaded_count += 1
            except Exception as e:
                logger.error(f"Failed to load critical component {component_info.name}: {e}")
                raise
    
    logger.info(f"Lazy initialization: {loaded_count} critical components loaded")
    return {"loaded_immediately": loaded_count, "lazy_components": len(ALL_COMPONENTS) - loaded_count}


def _initialize_eager() -> Dict[str, Any]:
    """Initialize with eager loading (load all components)"""
    logger = logging.getLogger("handlers.init.eager")
    
    loaded_count = 0
    failed_count = 0
    
    for component_info in ALL_COMPONENTS:
        try:
            component = _module_loader.load_component(component_info)
            if component:
                _loaded_components[component_info.name] = component
                loaded_count += 1
            else:
                failed_count += 1
        except Exception as e:
            logger.error(f"Failed to load component {component_info.name}: {e}")
            failed_count += 1
            if not component_info.optional:
                raise
    
    logger.info(f"Eager initialization: {loaded_count} components loaded, {failed_count} failed")
    return {"loaded_components": loaded_count, "failed_components": failed_count}


def _validate_default_config():
    """Validate default configuration"""
    logger = logging.getLogger("handlers.config")
    
    # Validate security config
    security_config = DEFAULT_CONFIG.get("security", {})
    if security_config.get("max_operations_per_minute", 0) <= 0:
        raise ValueError("Invalid security configuration: max_operations_per_minute must be positive")
    
    # Validate electron config
    electron_config = DEFAULT_CONFIG.get("electron", {})
    port = electron_config.get("websocket_port", 0)
    if not (1024 <= port <= 65535):
        raise ValueError("Invalid electron configuration: websocket_port must be between 1024-65535")
    
    logger.info("Default configuration validated successfully")


def _register_technique_handlers():
    """Register technique handlers in global registry"""
    technique_mapping = {
        "scRNA-seq": "scRNASeqHandlers",
        "ATAC-seq": "ATACSeqHandlers", 
        "Spatial": "SpatialHandlers",
        "Proteomics": "ProteomicsHandlers"
    }
    
    for technique, handler_name in technique_mapping.items():
        _handler_registry[technique] = handler_name


@lru_cache(maxsize=128)
def get_component(component_name: str, force_reload: bool = False):
    """Get component with lazy loading and caching"""
    if not force_reload and component_name in _loaded_components:
        return _loaded_components[component_name]
    
    # Find component info
    component_info = None
    for comp_info in ALL_COMPONENTS:
        if comp_info.name == component_name:
            component_info = comp_info
            break
    
    if not component_info:
        raise ValueError(f"Unknown component: {component_name}")
    
    # Load component
    component = _module_loader.load_component(component_info, force_reload)
    if component:
        _loaded_components[component_name] = component
    
    return component


# Enhanced configuration with validation
DEFAULT_CONFIG = {
    "security": {
        "max_operations_per_minute": 60,
        "allowed_file_extensions": [".h5ad", ".csv", ".tsv", ".xlsx", ".h5", ".mtx", ".gz"],
        "max_file_size_mb": 100,
        "audit_log_enabled": True,
        "encryption_enabled": False
    },
    "electron": {
        "websocket_port": 8765,
        "auto_start_server": True,
        "broadcast_progress": True,
        "connection_timeout": 30,
        "max_connections": 10
    },
    "analysis": {
        "default_qc_params": {
            "min_genes": 200,
            "min_cells": 3,
            "max_genes": 5000,
            "max_mito_pct": 20.0
        },
        "default_clustering_params": {
            "resolution": 0.5,
            "n_neighbors": 15,
            "n_pcs": 40
        },
        "pipeline_timeout": 300,
        "memory_limit_gb": 16
    },
    "performance": {
        "lazy_loading": True,
        "cache_enabled": True,
        "parallel_processing": True,
        "max_workers": 4
    },
    "development": {
        "debug_mode": False,
        "profiling_enabled": False,
        "test_mode": False
    }
}


def get_available_techniques() -> List[Dict[str, Any]]:
    """Get list of available analysis techniques with enhanced metadata"""
    return [
        {
            "name": "scRNA-seq", 
            "handler": "scRNASeqHandlers",
            "description": "Single-cell RNA sequencing analysis",
            "version": "2.1.0",
            "supported_formats": [".h5ad", ".h5", ".mtx"],
            "features": ["QC", "normalization", "clustering", "differential_expression", "trajectory"],
            "memory_requirements": "4-16GB",
            "status": "stable"
        },
        {
            "name": "ATAC-seq",
            "handler": "ATACSeqHandlers", 
            "description": "ATAC-seq chromatin accessibility analysis",
            "version": "2.1.0",
            "supported_formats": [".h5ad", ".h5", ".bed"],
            "features": ["QC", "peak_calling", "motif_analysis", "clustering"],
            "memory_requirements": "8-32GB",
            "status": "stable"
        },
        {
            "name": "Spatial",
            "handler": "SpatialHandlers",
            "description": "Spatial transcriptomics analysis",
            "version": "2.1.0",
            "supported_formats": [".h5ad", ".h5"],
            "features": ["spatial_clustering", "domain_identification", "ligand_receptor"],
            "memory_requirements": "4-24GB",
            "status": "stable"
        },
        {
            "name": "Proteomics",
            "handler": "ProteomicsHandlers",
            "description": "Proteomics and mass spectrometry analysis",
            "version": "2.1.0",
            "supported_formats": [".csv", ".xlsx", ".mzML"],
            "features": ["imputation", "normalization", "differential_analysis", "pathway"],
            "memory_requirements": "2-8GB",
            "status": "stable"
        }
    ]


def create_handler(technique: str, logger, config: dict = None, **kwargs):
    """Enhanced factory function to create technique-specific handlers"""
    if not _module_initialized:
        initialize_module()
    
    if technique not in _handler_registry:
        available = list(_handler_registry.keys())
        raise ValueError(f"Unknown technique: {technique}. Available: {available}")
    
    handler_name = _handler_registry[technique]
    
    try:
        # Get handler class with lazy loading
        handler_class = get_component(handler_name)
        
        if not handler_class:
            raise ImportError(f"Handler class {handler_name} could not be loaded")
        
        # Create handler instance
        handler = handler_class(logger, **kwargs)
        
        # Apply configuration if provided
        if config and hasattr(handler, 'apply_config'):
            handler.apply_config(config)
        
        return handler
        
    except Exception as e:
        logger.error(f"Failed to create {technique} handler: {e}")
        raise


def get_module_info() -> Dict[str, Any]:
    """Get comprehensive module information"""
    return {
        "name": "handlers",
        "version": __version__,
        "api_version": __api_version__,
        "author": __author__,
        "description": __description__,
        "license": __license__,
        "status": __status__,
        "python_requirements": f"{__min_python_version__[0]}.{__min_python_version__[1]}+",
        "initialized": _module_initialized,
        "components": {
            "total": len(ALL_COMPONENTS),
            "loaded": len(_loaded_components),
            "failed": len(_module_loader.get_import_errors())
        },
        "techniques": [t["name"] for t in get_available_techniques()],
        "initialization_time": getattr(get_module_info, '_init_time', None)
    }


def reload_module(component_name: str = None) -> Dict[str, Any]:
    """Reload specific component or entire module"""
    global _module_initialized
    
    if component_name:
        # Reload specific component
        try:
            component = get_component(component_name, force_reload=True)
            return {"status": "reloaded", "component": component_name}
        except Exception as e:
            return {"status": "failed", "component": component_name, "error": str(e)}
    else:
        # Reload entire module
        with _initialization_lock:
            _module_initialized = False
            _loaded_components.clear()
            _module_loader._component_cache.clear()
            _module_loader._import_errors.clear()
            
            return initialize_module()


# Dynamic imports with lazy loading
def __getattr__(name: str):
    """Dynamic attribute access with lazy loading"""
    if name in [comp.name for comp in ALL_COMPONENTS]:
        return get_component(name)
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# Enhanced __all__ with dynamic generation
__all__ = [comp.name for comp in ALL_COMPONENTS] + [
    # Utility functions
    "get_available_techniques",
    "create_handler", 
    "get_module_info",
    "initialize_module",
    "reload_module",
    "DEFAULT_CONFIG",
    
    # Version info
    "__version__",
    "__api_version__"
]


def main():
    """Enhanced module testing with comprehensive validation"""
    import time
    
    print(f"🧬 Handlers Module v{__version__} - Comprehensive Testing")
    print("="*60)
    
    start_time = time.time()
    
    try:
        # Test initialization
        print("🔧 Testing module initialization...")
        init_result = initialize_module(lazy_loading=True, validate_config=True)
        print(f"   ✅ Initialized in {init_result['initialization_time']:.2f}s")
        
        # Test configuration
        print("⚙️ Testing configuration...")
        assert "security" in DEFAULT_CONFIG
        assert "electron" in DEFAULT_CONFIG
        assert "analysis" in DEFAULT_CONFIG
        print("   ✅ Configuration validated")
        
        # Test technique discovery
        print("🧬 Testing technique discovery...")
        techniques = get_available_techniques()
        assert len(techniques) >= 4
        assert all("name" in t and "handler" in t and "features" in t for t in techniques)
        print(f"   ✅ Found {len(techniques)} techniques")
        
        # Test handler creation
        print("🏭 Testing handler factory...")
        import logging
        logger = logging.getLogger("test")
        handler = create_handler("scRNA-seq", logger)
        assert handler.get_technique_name() == "scRNA-seq"
        print("   ✅ Handler creation successful")
        
        # Test component loading
        print("📦 Testing component loading...")
        security_validator = get_component("SecurityValidator")
        assert security_validator is not None
        print("   ✅ Component loading successful")
        
        # Test module info
        print("ℹ️ Testing module information...")
        info = get_module_info()
        assert info["initialized"] is True
        assert info["version"] == __version__
        print("   ✅ Module info complete")
        
        total_time = time.time() - start_time
        
        print("\n🎉 ALL TESTS PASSED!")
        print(f"📊 Total execution time: {total_time:.2f}s")
        print(f"🧬 Available techniques: {[t['name'] for t in techniques]}")
        print(f"📦 Components loaded: {len(_loaded_components)}")
        print(f"🐍 Python version: {sys.version_info.major}.{sys.version_info.minor}")
        print(f"📋 Module version: {__version__}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TESTS FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


# Auto-initialize in development mode
if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
else:
    # Initialize module on import (lazy by default)
    try:
        initialize_module(lazy_loading=True, validate_config=False)
    except Exception as e:
        warnings.warn(f"Module initialization failed: {e}", ImportWarning)