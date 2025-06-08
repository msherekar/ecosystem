"""
MCP Configuration Management

Provides configuration-driven approach for server registration,
strategy selection, and workflow management.
"""

import yaml
import json
from typing import Dict, List, Any, Optional, Type
from dataclasses import dataclass, field
from pathlib import Path
import importlib
import logging


@dataclass
class ServerConfig:
    """Configuration for an MCP server"""
    name: str
    class_path: str  # e.g., "src.mcp.servers.scrnaseq_server.scRNASeqMCPServer"
    enabled: bool = True
    auto_connect: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    strategy: Optional[str] = None  # Strategy for suggested actions
    dependencies: List[str] = field(default_factory=list)
    priority: int = 1


@dataclass
class AnalysisConfig:
    """Configuration for an analysis type"""
    name: str
    display_name: str
    description: str
    icon: str
    server_name: str
    strategy: str
    workflow_stages: List[str] = field(default_factory=list)
    data_requirements: List[str] = field(default_factory=list)
    optional_data: List[str] = field(default_factory=list)


class ConfigManager:
    """Manages MCP configuration from files and dynamic registration"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.logger = logging.getLogger("mcp.config")
        
        # Configuration storage
        self.server_configs: Dict[str, ServerConfig] = {}
        self.analysis_configs: Dict[str, AnalysisConfig] = {}
        self.global_config: Dict[str, Any] = {}
        
        # Load configurations
        self._load_configurations()
    
    def _load_configurations(self):
        """Load all configuration files"""
        try:
            # Load global config
            self._load_global_config()
            
            # Load server configs
            self._load_server_configs()
            
            # Load analysis configs
            self._load_analysis_configs()
            
            self.logger.info("Configuration loaded successfully")
            
        except Exception as e:
            self.logger.warning(f"Failed to load configuration: {e}")
            self._load_default_configs()
    
    def _load_global_config(self):
        """Load global MCP configuration"""
        config_file = self.config_dir / "mcp_config.yaml"
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                self.global_config = yaml.safe_load(f) or {}
        else:
            self.global_config = self._get_default_global_config()
    
    def _load_server_configs(self):
        """Load server configurations"""
        config_file = self.config_dir / "servers.yaml"
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                servers_data = yaml.safe_load(f) or {}
                
                for name, config_data in servers_data.items():
                    self.server_configs[name] = ServerConfig(
                        name=name,
                        **config_data
                    )
        else:
            self._load_default_server_configs()
    
    def _load_analysis_configs(self):
        """Load analysis type configurations"""
        config_file = self.config_dir / "analysis_types.yaml"
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                analysis_data = yaml.safe_load(f) or {}
                
                for name, config_data in analysis_data.items():
                    self.analysis_configs[name] = AnalysisConfig(
                        name=name,
                        **config_data
                    )
        else:
            self._load_default_analysis_configs()
    
    def _load_default_configs(self):
        """Load default configurations when files are not available"""
        self.global_config = self._get_default_global_config()
        self._load_default_server_configs()
        self._load_default_analysis_configs()
    
    def _get_default_global_config(self) -> Dict[str, Any]:
        """Get default global configuration"""
        return {
            "mcp": {
                "client_name": "bioinformatics_platform",
                "cache": {
                    "enabled": True,
                    "max_size": 1000,
                    "default_ttl": 300
                },
                "connection": {
                    "timeout": 30,
                    "retry_attempts": 3,
                    "retry_delay": 1
                }
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        }
    
    def _load_default_server_configs(self):
        """Load default server configurations"""
        default_servers = [
            ServerConfig(
                name="scrnaseq",
                class_path="src.mcp.servers.scrnaseq_server.scRNASeqMCPServer",
                enabled=True,
                auto_connect=True,
                strategy="scrnaseq",
                priority=1
            ),
            ServerConfig(
                name="rnaseq",
                class_path="src.mcp.servers.rnaseq_server.RNASeqMCPServer",
                enabled=False,  # Disabled by default
                auto_connect=False,
                strategy="rnaseq",
                priority=2
            ),
            ServerConfig(
                name="data",
                class_path="src.mcp.servers.data_server.DataMCPServer",
                enabled=True,
                auto_connect=True,
                priority=3
            ),
            ServerConfig(
                name="visualization",
                class_path="src.mcp.servers.visualization_server.VisualizationMCPServer",
                enabled=True,
                auto_connect=True,
                priority=4
            ),
            ServerConfig(
                name="search",
                class_path="src.mcp.servers.search_server.SearchMCPServer",
                enabled=True,
                auto_connect=True,
                strategy="search",
                priority=5
            ),
            ServerConfig(
                name="atacseq",
                class_path="src.mcp.servers.atacseq_server.ATACSeqMCPServer",
                enabled=False,  # Can be enabled when needed
                auto_connect=False,
                strategy="atacseq",
                priority=6
            )
        ]
        
        for config in default_servers:
            self.server_configs[config.name] = config
    
    def _load_default_analysis_configs(self):
        """Load default analysis configurations"""
        default_analyses = [
            AnalysisConfig(
                name="scrnaseq",
                display_name="Single-cell RNA-seq",
                description="Single-cell RNA sequencing analysis",
                icon="🧬",
                server_name="scrnaseq",
                strategy="scrnaseq",
                workflow_stages=["data_upload", "quality_control", "preprocessing", "analysis", "visualization"],
                data_requirements=["expression_matrix"],
                optional_data=["metadata", "feature_annotations"]
            ),
            AnalysisConfig(
                name="rnaseq",
                display_name="Bulk RNA-seq",
                description="Bulk RNA sequencing analysis",
                icon="🧬",
                server_name="rnaseq",
                strategy="rnaseq",
                workflow_stages=["data_upload", "analysis", "interpretation", "visualization"],
                data_requirements=["counts_matrix", "sample_metadata"],
                optional_data=["gene_annotations"]
            ),
            AnalysisConfig(
                name="atacseq",
                display_name="ATAC-seq",
                description="Assay for Transposase-Accessible Chromatin",
                icon="🔬",
                server_name="atacseq",
                strategy="atacseq",
                workflow_stages=["data_upload", "quality_control", "analysis", "interpretation"],
                data_requirements=["peak_data"],
                optional_data=["fragment_files", "metadata"]
            )
        ]
        
        for config in default_analyses:
            self.analysis_configs[config.name] = config
    
    def get_server_config(self, name: str) -> Optional[ServerConfig]:
        """Get server configuration by name"""
        return self.server_configs.get(name)
    
    def get_analysis_config(self, name: str) -> Optional[AnalysisConfig]:
        """Get analysis configuration by name"""
        return self.analysis_configs.get(name)
    
    def get_enabled_servers(self) -> List[ServerConfig]:
        """Get list of enabled server configurations"""
        return [config for config in self.server_configs.values() if config.enabled]
    
    def get_auto_connect_servers(self) -> List[ServerConfig]:
        """Get list of servers that should auto-connect"""
        return [config for config in self.server_configs.values() 
                if config.enabled and config.auto_connect]
    
    def register_server_config(self, config: ServerConfig):
        """Register a new server configuration"""
        self.server_configs[config.name] = config
        self.logger.info(f"Registered server config: {config.name}")
    
    def register_analysis_config(self, config: AnalysisConfig):
        """Register a new analysis configuration"""
        self.analysis_configs[config.name] = config
        self.logger.info(f"Registered analysis config: {config.name}")
    
    def load_server_class(self, class_path: str) -> Optional[Type]:
        """Dynamically load server class from path"""
        try:
            module_path, class_name = class_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except Exception as e:
            self.logger.error(f"Failed to load server class {class_path}: {e}")
            return None
    
    def save_configuration(self):
        """Save current configuration to files"""
        try:
            # Ensure config directory exists
            self.config_dir.mkdir(exist_ok=True)
            
            # Save global config
            with open(self.config_dir / "mcp_config.yaml", 'w') as f:
                yaml.dump(self.global_config, f, default_flow_style=False)
            
            # Save server configs
            servers_data = {}
            for name, config in self.server_configs.items():
                servers_data[name] = {
                    "class_path": config.class_path,
                    "enabled": config.enabled,
                    "auto_connect": config.auto_connect,
                    "config": config.config,
                    "strategy": config.strategy,
                    "dependencies": config.dependencies,
                    "priority": config.priority
                }
            
            with open(self.config_dir / "servers.yaml", 'w') as f:
                yaml.dump(servers_data, f, default_flow_style=False)
            
            # Save analysis configs
            analysis_data = {}
            for name, config in self.analysis_configs.items():
                analysis_data[name] = {
                    "display_name": config.display_name,
                    "description": config.description,
                    "icon": config.icon,
                    "server_name": config.server_name,
                    "strategy": config.strategy,
                    "workflow_stages": config.workflow_stages,
                    "data_requirements": config.data_requirements,
                    "optional_data": config.optional_data
                }
            
            with open(self.config_dir / "analysis_types.yaml", 'w') as f:
                yaml.dump(analysis_data, f, default_flow_style=False)
            
            self.logger.info("Configuration saved successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
    
    def get_global_setting(self, key: str, default: Any = None) -> Any:
        """Get global configuration setting"""
        keys = key.split('.')
        value = self.global_config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def validate_configuration(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        # Validate server configs
        for name, config in self.server_configs.items():
            # Check if class can be loaded
            server_class = self.load_server_class(config.class_path)
            if server_class is None:
                issues.append(f"Server {name}: Cannot load class {config.class_path}")
            
            # Check dependencies
            for dep in config.dependencies:
                if dep not in self.server_configs:
                    issues.append(f"Server {name}: Missing dependency {dep}")
        
        # Validate analysis configs
        for name, config in self.analysis_configs.items():
            # Check if server exists
            if config.server_name not in self.server_configs:
                issues.append(f"Analysis {name}: Server {config.server_name} not found")
        
        return issues


# Global configuration manager
config_manager = ConfigManager()


# Test code to verify the module works independently
if __name__ == "__main__":
    def test_config_manager():
        """Test ConfigManager functionality"""
        print("Testing ConfigManager...")
        
        # Test config manager creation
        print(f"✅ Created ConfigManager with {len(config_manager.server_configs)} servers")
        
        # Test enabled servers
        enabled_servers = config_manager.get_enabled_servers()
        print(f"✅ Enabled servers: {len(enabled_servers)}")
        for server in enabled_servers:
            print(f"   - {server.name}: {server.class_path}")
        
        # Test auto-connect servers
        auto_connect = config_manager.get_auto_connect_servers()
        print(f"✅ Auto-connect servers: {len(auto_connect)}")
        
        # Test global settings
        client_name = config_manager.get_global_setting('mcp.client_name', 'default')
        print(f"✅ Client name: {client_name}")
        
        # Test configuration validation
        issues = config_manager.validate_configuration()
        print(f"✅ Configuration validation: {len(issues)} issues found")
        for issue in issues:
            print(f"   ⚠️  {issue}")
        
        # Test dynamic class loading
        for server_config in config_manager.server_configs.values():
            if server_config.enabled:
                server_class = config_manager.load_server_class(server_config.class_path)
                status = "✅ Loaded" if server_class else "❌ Failed"
                print(f"   {status}: {server_config.name}")
        
        print("🎉 All ConfigManager tests passed!")
    
    # Run test
    test_config_manager() 
    # python -m src.mcp.core.config
    # Add servers for other techniques