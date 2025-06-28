"""
Configuration Management System

Handles configuration loading, validation, and management for the MCP server.
Supports environment-specific configs and runtime configuration updates.
"""

import os
import yaml
import json
from typing import Any, Dict, Optional, Union
from pathlib import Path
import logging
from dataclasses import dataclass, asdict


@dataclass
class SecurityConfig:
    """Security configuration settings"""
    max_operations_per_minute: int = 60
    allowed_file_extensions: list = None
    max_file_size_mb: int = 100
    audit_log_enabled: bool = True
    
    def __post_init__(self):
        if self.allowed_file_extensions is None:
            self.allowed_file_extensions = [".h5ad", ".csv", ".tsv", ".xlsx", ".h5", ".mtx", ".gz"]


@dataclass
class ElectronConfig:
    """Electron integration configuration"""
    websocket_port: int = 8765
    auto_start_server: bool = True
    broadcast_progress: bool = True
    connection_timeout: int = 30


@dataclass
class AnalysisConfig:
    """Analysis configuration defaults"""
    default_qc_params: Dict[str, Any] = None
    default_clustering_params: Dict[str, Any] = None
    pipeline_timeout: int = 300
    
    def __post_init__(self):
        if self.default_qc_params is None:
            self.default_qc_params = {
                "min_genes": 200,
                "min_cells": 3,
                "max_genes": 5000,
                "max_mito_pct": 20.0
            }
        if self.default_clustering_params is None:
            self.default_clustering_params = {
                "resolution": 0.5,
                "n_neighbors": 15,
                "n_pcs": 40
            }


class ConfigManager:
    """Configuration management with validation and environment support"""
    
    def __init__(self, config_path: str = "config/server_config.yaml"):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.config_loaded = False
        self.logger = logging.getLogger("config_manager")
        
        # Default configurations
        self.defaults = {
            "security": SecurityConfig(),
            "electron": ElectronConfig(),
            "analysis": AnalysisConfig()
        }
        
        # Load configuration
        self._load_configuration()
    
    def _load_configuration(self):
        """Load configuration from file with fallbacks"""
        try:
            # Load from file if exists
            if self.config_path.exists():
                self._load_from_file()
            else:
                self.logger.warning(f"Config file not found: {self.config_path}, using defaults")
                self._use_defaults()
            
            # Override with environment variables
            self._apply_environment_overrides()
            
            # Validate configuration
            self._validate_configuration()
            
            self.config_loaded = True
            self.logger.info("Configuration loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            self._use_defaults()
            self.config_loaded = True
    
    def _load_from_file(self):
        """Load configuration from YAML or JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                if self.config_path.suffix.lower() in ['.yaml', '.yml']:
                    self.config = yaml.safe_load(f) or {}
                elif self.config_path.suffix.lower() == '.json':
                    self.config = json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {self.config_path.suffix}")
            
            self.logger.info(f"Loaded configuration from {self.config_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to load config file: {e}")
            self._use_defaults()
    
    def _use_defaults(self):
        """Use default configuration"""
        self.config = {
            "security": asdict(self.defaults["security"]),
            "electron": asdict(self.defaults["electron"]),
            "analysis": asdict(self.defaults["analysis"])
        }
    
    def _apply_environment_overrides(self):
        """Apply environment variable overrides"""
        env_mappings = {
            "MCP_WEBSOCKET_PORT": ("electron", "websocket_port", int),
            "MCP_MAX_FILE_SIZE": ("security", "max_file_size_mb", int),
            "MCP_AUDIT_ENABLED": ("security", "audit_log_enabled", bool),
            "MCP_AUTO_START_ELECTRON": ("electron", "auto_start_server", bool),
            "MCP_PIPELINE_TIMEOUT": ("analysis", "pipeline_timeout", int)
        }
        
        for env_var, (section, key, value_type) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    # Convert value to appropriate type
                    if value_type == bool:
                        converted_value = env_value.lower() in ('true', '1', 'yes', 'on')
                    else:
                        converted_value = value_type(env_value)
                    
                    # Set in config
                    if section not in self.config:
                        self.config[section] = {}
                    self.config[section][key] = converted_value
                    
                    self.logger.info(f"Applied environment override: {env_var} = {converted_value}")
                    
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Invalid environment variable {env_var}: {e}")
    
    def _validate_configuration(self):
        """Validate configuration values"""
        validation_errors = []
        
        # Validate security config
        security = self.config.get("security", {})
        if security.get("max_operations_per_minute", 0) <= 0:
            validation_errors.append("max_operations_per_minute must be positive")
        
        if security.get("max_file_size_mb", 0) <= 0:
            validation_errors.append("max_file_size_mb must be positive")
        
        # Validate electron config
        electron = self.config.get("electron", {})
        port = electron.get("websocket_port", 0)
        if not (1024 <= port <= 65535):
            validation_errors.append("websocket_port must be between 1024 and 65535")
        
        # Validate analysis config
        analysis = self.config.get("analysis", {})
        timeout = analysis.get("pipeline_timeout", 0)
        if timeout <= 0:
            validation_errors.append("pipeline_timeout must be positive")
        
        if validation_errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(validation_errors)}")
    
    def get_config(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'security.max_file_size_mb')"""
        try:
            value = self.config
            for key in key_path.split('.'):
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set_config(self, key_path: str, value: Any) -> bool:
        """Set configuration value using dot notation"""
        try:
            keys = key_path.split('.')
            config = self.config
            
            # Navigate to parent of target key
            for key in keys[:-1]:
                if key not in config:
                    config[key] = {}
                config = config[key]
            
            # Set value
            config[keys[-1]] = value
            
            self.logger.info(f"Updated configuration: {key_path} = {value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set config {key_path}: {e}")
            return False
    
    def save_config(self) -> bool:
        """Save current configuration to file"""
        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write configuration
            with open(self.config_path, 'w') as f:
                if self.config_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(self.config, f, default_flow_style=False)
                elif self.config_path.suffix.lower() == '.json':
                    json.dump(self.config, f, indent=2)
                else:
                    raise ValueError(f"Unsupported config file format: {self.config_path.suffix}")
            
            self.logger.info(f"Configuration saved to {self.config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get entire configuration"""
        return self.config.copy()
    
    def get_config_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section"""
        return self.config.get(section, {})
    
    def update_config_section(self, section: str, values: Dict[str, Any]) -> bool:
        """Update entire configuration section"""
        try:
            if section not in self.config:
                self.config[section] = {}
            
            self.config[section].update(values)
            self.logger.info(f"Updated configuration section: {section}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update config section {section}: {e}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """Reset configuration to defaults"""
        try:
            self._use_defaults()
            self.logger.info("Configuration reset to defaults")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reset configuration: {e}")
            return False
    
    def is_loaded(self) -> bool:
        """Check if configuration is loaded"""
        return self.config_loaded
    
    def get_config_path(self) -> str:
        """Get configuration file path"""
        return str(self.config_path)


def main():
    """Test configuration manager"""
    import tempfile
    
    # Test with temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        test_config = {
            "security": {
                "max_operations_per_minute": 120,
                "audit_log_enabled": True
            },
            "electron": {
                "websocket_port": 8765,
                "auto_start_server": False
            }
        }
        yaml.dump(test_config, f)
        config_path = f.name
    
    try:
        # Test config manager
        config_manager = ConfigManager(config_path)
        
        # Test getting values
        assert config_manager.get_config("security.max_operations_per_minute") == 120
        assert config_manager.get_config("electron.websocket_port") == 8765
        assert config_manager.get_config("nonexistent.key", "default") == "default"
        
        # Test setting values
        assert config_manager.set_config("test.new_value", "hello") is True
        assert config_manager.get_config("test.new_value") == "hello"
        
        # Test section operations
        security_section = config_manager.get_config_section("security")
        assert security_section["max_operations_per_minute"] == 120
        
        # Test updating section
        assert config_manager.update_config_section("test", {"key1": "value1", "key2": "value2"}) is True
        assert config_manager.get_config("test.key1") == "value1"
        
        print("✅ Configuration manager tests passed")
        
    finally:
        # Clean up
        Path(config_path).unlink()


if __name__ == "__main__":
    main()