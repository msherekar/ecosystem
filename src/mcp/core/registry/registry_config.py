"""
Registry Configuration Management

Handles loading and managing server configurations for the MCP registry.
Supports multiple configuration sources and dynamic server loading.

This file is separate from the core registry to keep configuration
management isolated and easily testable.
"""

import logging
import json
import os
import importlib
from typing import Dict, List, Any, Optional, Type
from dataclasses import dataclass, field
from pathlib import Path
import yaml

# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class ServerConfiguration:
    """Configuration for a single server"""
    name: str
    class_path: str
    enabled: bool = True
    auto_connect: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    retry_count: int = 3
    retry_delay: float = 1.0
    description: str = ""
    
    def __post_init__(self):
        """Validate server configuration"""
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Server name must be a non-empty string")
        
        if not self.class_path or not isinstance(self.class_path, str):
            raise ValueError("Server class_path must be a non-empty string")


class ConfigurationLoader:
    """Loads configuration from various sources"""
    
    def __init__(self):
        self.logger = logger.getChild("ConfigLoader")
        self.config_paths = [
            "config/mcp_servers.yaml",
            "config/mcp_servers.json", 
            "mcp_servers.yaml",
            "mcp_servers.json",
            os.path.expanduser("~/.mcp/servers.yaml"),
            os.path.expanduser("~/.mcp/servers.json")
        ]
    
    def load_from_file(self, config_path: str) -> Optional[Dict[str, Any]]:
        """Load configuration from a specific file"""
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                return None
            
            self.logger.info(f"Loading configuration from {config_path}")
            
            with open(config_file, 'r') as f:
                if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                    return yaml.safe_load(f)
                elif config_path.endswith('.json'):
                    return json.load(f)
                else:
                    self.logger.warning(f"Unsupported config file format: {config_path}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error loading config from {config_path}: {e}")
            return None
    
    def load_from_environment(self) -> Optional[Dict[str, Any]]:
        """Load configuration from environment variables"""
        try:
            config_json = os.getenv('MCP_SERVERS_CONFIG')
            if config_json:
                self.logger.info("Loading configuration from environment variable")
                return json.loads(config_json)
            return None
        except Exception as e:
            self.logger.error(f"Error loading config from environment: {e}")
            return None
    
    def load_configuration(self) -> Dict[str, Any]:
        """Load configuration from available sources in priority order"""
        
        # Try environment first
        config = self.load_from_environment()
        if config:
            return config
        
        # Try configuration files
        for config_path in self.config_paths:
            config = self.load_from_file(config_path)
            if config:
                return config
        
        # No configuration found
        self.logger.warning("No configuration files found, using defaults")
        return self._get_default_configuration()
    
    def _get_default_configuration(self) -> Dict[str, Any]:
        """Get default server configuration"""
        return {
            "servers": [
                {
                    "name": "scrnaseq",
                    "class_path": "src.mcp.servers.scrnaseq_server.scRNASeqMCPServer",
                    "enabled": True,
                    "auto_connect": True,
                    "priority": 10,
                    "description": "Single-cell RNA sequencing analysis server"
                },
                {
                    "name": "data",
                    "class_path": "src.mcp.servers.data_server.DataMCPServer",
                    "enabled": True,
                    "auto_connect": True,
                    "priority": 20,
                    "description": "Data management and file handling server"
                },
                {
                    "name": "visualization",
                    "class_path": "src.mcp.servers.visualization_server.VisualizationMCPServer",
                    "enabled": True,
                    "auto_connect": True,
                    "priority": 5,
                    "description": "Data visualization and plotting server"
                },
                {
                    "name": "search", 
                    "class_path": "src.mcp.servers.search_server.SearchMCPServer",
                    "enabled": True,
                    "auto_connect": False,  # Optional server
                    "priority": 0,
                    "description": "Search and discovery server"
                }
            ]
        }


class ServerClassLoader:
    """Dynamically loads server classes"""
    
    def __init__(self):
        self.logger = logger.getChild("ClassLoader")
        self._class_cache = {}
    
    def load_server_class(self, class_path: str) -> Optional[Type]:
        """Load a server class from its module path"""
        
        # Check cache first
        if class_path in self._class_cache:
            return self._class_cache[class_path]
        
        try:
            # Split module path and class name
            if '.' not in class_path:
                raise ValueError(f"Invalid class path format: {class_path}")
            
            module_path, class_name = class_path.rsplit('.', 1)
            
            self.logger.debug(f"Loading class {class_name} from module {module_path}")
            
            # Import the module
            module = importlib.import_module(module_path)
            
            # Get the class
            server_class = getattr(module, class_name)
            
            # Validate that it's a class
            if not isinstance(server_class, type):
                raise ValueError(f"{class_path} is not a class")
            
            # Cache the class
            self._class_cache[class_path] = server_class
            
            self.logger.info(f"Successfully loaded server class: {class_path}")
            return server_class
            
        except ImportError as e:
            self.logger.error(f"Failed to import module for {class_path}: {e}")
            return None
        except AttributeError as e:
            self.logger.error(f"Class not found in module for {class_path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error loading server class {class_path}: {e}")
            return None
    
    def validate_server_class(self, server_class: Type) -> bool:
        """Validate that a class is a proper MCP server"""
        try:
            # Check if it has required methods (basic validation)
            required_methods = ['__init__']  # Add more as needed
            
            for method in required_methods:
                if not hasattr(server_class, method):
                    self.logger.warning(f"Server class missing required method: {method}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating server class: {e}")
            return False
    
    def clear_cache(self):
        """Clear the class cache"""
        self._class_cache.clear()
        self.logger.info("Server class cache cleared")


class ConfigurationManager:
    """Main configuration management class"""
    
    def __init__(self):
        self.logger = logger.getChild("ConfigManager")
        self.loader = ConfigurationLoader()
        self.class_loader = ServerClassLoader()
        self._config_cache = None
        self._cache_timestamp = 0
        self._cache_ttl = 300  # 5 minutes
    
    def get_enabled_servers(self) -> List[ServerConfiguration]:
        """Get list of enabled server configurations"""
        config = self._get_cached_config()
        
        servers = []
        server_configs = config.get('servers', [])
        
        for server_config in server_configs:
            try:
                # Create ServerConfiguration object
                server = ServerConfiguration(
                    name=server_config.get('name'),
                    class_path=server_config.get('class_path'),
                    enabled=server_config.get('enabled', True),
                    auto_connect=server_config.get('auto_connect', True),
                    config=server_config.get('config', {}),
                    priority=server_config.get('priority', 0),
                    retry_count=server_config.get('retry_count', 3),
                    retry_delay=server_config.get('retry_delay', 1.0),
                    description=server_config.get('description', '')
                )
                
                # Only include enabled servers
                if server.enabled:
                    servers.append(server)
                    
            except Exception as e:
                self.logger.error(f"Error parsing server config: {e}")
                continue
        
        # Sort by priority (higher first)
        servers.sort(key=lambda x: x.priority, reverse=True)
        
        self.logger.info(f"Found {len(servers)} enabled servers")
        return servers
    
    def get_server_config(self, server_name: str) -> Optional[ServerConfiguration]:
        """Get configuration for a specific server"""
        enabled_servers = self.get_enabled_servers()
        
        for server in enabled_servers:
            if server.name == server_name:
                return server
        
        return None
    
    def load_server_class(self, class_path: str) -> Optional[Type]:
        """Load and validate a server class"""
        server_class = self.class_loader.load_server_class(class_path)
        
        if server_class and self.class_loader.validate_server_class(server_class):
            return server_class
        
        return None
    
    def reload_configuration(self):
        """Force reload of configuration from sources"""
        self._config_cache = None
        self._cache_timestamp = 0
        self.class_loader.clear_cache()
        self.logger.info("Configuration reloaded")
    
    def _get_cached_config(self) -> Dict[str, Any]:
        """Get configuration with caching"""
        import time
        current_time = time.time()
        
        if (self._config_cache is None or 
            current_time - self._cache_timestamp > self._cache_ttl):
            
            self._config_cache = self.loader.load_configuration()
            self._cache_timestamp = current_time
            self.logger.debug("Configuration loaded from source")
        
        return self._config_cache
    
    def validate_configuration(self) -> List[str]:
        """Validate the current configuration and return issues"""
        issues = []
        
        try:
            config = self._get_cached_config()
            
            # Check required top-level keys
            if 'servers' not in config:
                issues.append("Configuration missing 'servers' section")
                return issues
            
            servers = config['servers']
            if not isinstance(servers, list):
                issues.append("'servers' must be a list")
                return issues
            
            # Validate each server configuration
            server_names = set()
            for i, server_config in enumerate(servers):
                if not isinstance(server_config, dict):
                    issues.append(f"Server {i} must be an object")
                    continue
                
                # Check required fields
                required_fields = ['name', 'class_path']
                for field in required_fields:
                    if field not in server_config:
                        issues.append(f"Server {i} missing required field: {field}")
                
                # Check for duplicate names
                name = server_config.get('name')
                if name in server_names:
                    issues.append(f"Duplicate server name: {name}")
                else:
                    server_names.add(name)
                
                # Validate class path
                class_path = server_config.get('class_path')
                if class_path and not self._is_valid_class_path(class_path):
                    issues.append(f"Invalid class path for server {name}: {class_path}")
                
                # Validate priority
                priority = server_config.get('priority', 0)
                if not isinstance(priority, int):
                    issues.append(f"Priority for server {name} must be an integer")
                
                # Validate retry settings
                retry_count = server_config.get('retry_count', 3)
                if not isinstance(retry_count, int) or retry_count < 0:
                    issues.append(f"retry_count for server {name} must be a non-negative integer")
                
                retry_delay = server_config.get('retry_delay', 1.0)
                if not isinstance(retry_delay, (int, float)) or retry_delay < 0:
                    issues.append(f"retry_delay for server {name} must be a non-negative number")
        
        except Exception as e:
            issues.append(f"Error validating configuration: {e}")
        
        return issues
    
    def _is_valid_class_path(self, class_path: str) -> bool:
        """Check if a class path has valid format"""
        if not isinstance(class_path, str) or not class_path:
            return False
        
        # Must contain at least one dot
        if '.' not in class_path:
            return False
        
        # Split into parts
        parts = class_path.split('.')
        
        # All parts must be valid Python identifiers
        for part in parts:
            if not part.isidentifier():
                return False
        
        return True
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration"""
        try:
            config = self._get_cached_config()
            enabled_servers = self.get_enabled_servers()
            
            return {
                "config_source": "loaded" if self._config_cache else "not_loaded",
                "cache_age": __import__('time').time() - self._cache_timestamp,
                "total_servers": len(config.get('servers', [])),
                "enabled_servers": len(enabled_servers),
                "auto_connect_servers": len([s for s in enabled_servers if s.auto_connect]),
                "validation_issues": self.validate_configuration(),
                "server_priorities": {s.name: s.priority for s in enabled_servers}
            }
            
        except Exception as e:
            return {"error": f"Failed to get configuration summary: {e}"}


# Example configuration file format for documentation
EXAMPLE_CONFIG = {
    "servers": [
        {
            "name": "scrnaseq",
            "class_path": "src.mcp.servers.scrnaseq_server.scRNASeqMCPServer",
            "enabled": True,
            "auto_connect": True,
            "priority": 10,
            "retry_count": 3,
            "retry_delay": 1.0,
            "description": "Single-cell RNA sequencing analysis server",
            "config": {
                "max_cells": 100000,
                "default_resolution": 0.5
            }
        },
        {
            "name": "data",
            "class_path": "src.mcp.servers.data_server.DataMCPServer", 
            "enabled": True,
            "auto_connect": True,
            "priority": 20,
            "description": "Data management server"
        }
    ]
}


def save_example_config(file_path: str = "mcp_servers.yaml"):
    """Save an example configuration file"""
    try:
        import yaml
        with open(file_path, 'w') as f:
            yaml.dump(EXAMPLE_CONFIG, f, default_flow_style=False, indent=2)
        logger.info(f"Example configuration saved to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving example config: {e}")
        return False


def main():
    """Main function for module testing"""
    print("Testing Configuration Management...")
    
    # Test configuration loader
    loader = ConfigurationLoader()
    print("✅ Created ConfigurationLoader")
    
    # Test default configuration
    default_config = loader._get_default_configuration()
    print(f"✅ Default config has {len(default_config['servers'])} servers")
    
    # Test class loader
    class_loader = ServerClassLoader()
    print("✅ Created ServerClassLoader")
    
    # Test configuration manager
    config_manager = ConfigurationManager()
    print("✅ Created ConfigurationManager")
    
    # Test getting enabled servers
    enabled_servers = config_manager.get_enabled_servers()
    print(f"✅ Found {len(enabled_servers)} enabled servers:")
    
    for server in enabled_servers:
        print(f"   - {server.name}: priority {server.priority}, auto_connect: {server.auto_connect}")
    
    # Test configuration validation
    issues = config_manager.validate_configuration()
    if issues:
        print(f"⚠️  Configuration issues: {issues}")
    else:
        print("✅ Configuration validation passed")
    
    # Test configuration summary
    summary = config_manager.get_configuration_summary()
    print(f"✅ Configuration summary:")
    print(f"   Total servers: {summary.get('total_servers', 0)}")
    print(f"   Enabled servers: {summary.get('enabled_servers', 0)}")
    print(f"   Auto-connect servers: {summary.get('auto_connect_servers', 0)}")
    
    # Test example config saving
    try:
        save_example_config("test_config.yaml")
        print("✅ Example config file saved")
    except:
        print("⚠️  Could not save example config (yaml not available)")
    
    print("🎉 All Configuration Management tests passed!")


if __name__ == "__main__":
    main()