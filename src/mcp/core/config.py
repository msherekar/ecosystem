"""
Extended Configuration for MCP Servers

Enhanced configuration with security, scalability, and Electron integration settings.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ServerConfig:
    """Comprehensive configuration for MCP server system"""
    
    # Core server settings
    max_concurrent_servers: int = 10
    allow_multiple_instances: bool = False
    prewarm_servers: bool = True
    prewarm_server_types: List[str] = field(default_factory=lambda: ["rnaseq", "scrnaseq"])
    
    # Security settings
    secret_key: str = field(default_factory=lambda: os.environ.get("MCP_SECRET_KEY", "default_secret_change_me"))
    encryption_enabled: bool = False
    encryption_key: Optional[str] = None
    allow_anonymous_access: bool = True
    allow_anonymous_tool_execution: bool = False
    max_failed_attempts: int = 5
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window_minutes: int = 1
    
    # Monitoring and health
    health_check_interval: int = 30
    max_security_events: int = 10000
    
    # Logging
    log_level: int = logging.INFO
    log_file: Optional[str] = None
    
    # Electron integration
    electron_mode: bool = False
    electron_bridge_enabled: bool = True
    
    # File system
    data_directory: Path = field(default_factory=lambda: Path.home() / ".mcp_servers")
    cache_directory: Optional[Path] = None
    temp_directory: Optional[Path] = None
    
    def __post_init__(self):
        """Post-initialization setup"""
        # Ensure data directory exists
        self.data_directory.mkdir(parents=True, exist_ok=True)
        
        # Set default cache and temp directories
        if self.cache_directory is None:
            self.cache_directory = self.data_directory / "cache"
        if self.temp_directory is None:
            self.temp_directory = self.data_directory / "temp"
        
        # Create directories
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        self.temp_directory.mkdir(parents=True, exist_ok=True)
        
        # Validate encryption settings
        if self.encryption_enabled and not self.encryption_key:
            self.encryption_key = os.environ.get("MCP_ENCRYPTION_KEY")
            if not self.encryption_key:
                raise ValueError("Encryption enabled but no encryption key provided")
        
        # Auto-detect Electron mode
        if not self.electron_mode:
            self.electron_mode = self._detect_electron_mode()
    
    def _detect_electron_mode(self) -> bool:
        """Auto-detect if running in Electron environment"""
        electron_indicators = [
            "ELECTRON_MODE",  # Our custom indicator
            "ELECTRON_RUN_AS_NODE",
            "ELECTRON_NO_ATTACH_CONSOLE",
            "__ELECTRON_ENABLE_LOGGING__"
        ]
        
        return any(os.environ.get(indicator) for indicator in electron_indicators)
    
    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Create configuration from environment variables"""
        return cls(
            max_concurrent_servers=int(os.environ.get("MCP_MAX_SERVERS", "10")),
            allow_multiple_instances=os.environ.get("MCP_ALLOW_MULTIPLE", "false").lower() == "true",
            prewarm_servers=os.environ.get("MCP_PREWARM", "true").lower() == "true",
            secret_key=os.environ.get("MCP_SECRET_KEY", "default_secret_change_me"),
            encryption_enabled=os.environ.get("MCP_ENCRYPTION", "false").lower() == "true",
            encryption_key=os.environ.get("MCP_ENCRYPTION_KEY"),
            allow_anonymous_access=os.environ.get("MCP_ALLOW_ANONYMOUS", "true").lower() == "true",
            rate_limit_requests=int(os.environ.get("MCP_RATE_LIMIT", "100")),
            log_level=getattr(logging, os.environ.get("MCP_LOG_LEVEL", "INFO").upper()),
            data_directory=Path(os.environ.get("MCP_DATA_DIR", str(Path.home() / ".mcp_servers")))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "max_concurrent_servers": self.max_concurrent_servers,
            "allow_multiple_instances": self.allow_multiple_instances,
            "prewarm_servers": self.prewarm_servers,
            "prewarm_server_types": self.prewarm_server_types,
            "encryption_enabled": self.encryption_enabled,
            "allow_anonymous_access": self.allow_anonymous_access,
            "rate_limit_requests": self.rate_limit_requests,
            "rate_limit_window_minutes": self.rate_limit_window_minutes,
            "health_check_interval": self.health_check_interval,
            "log_level": self.log_level,
            "electron_mode": self.electron_mode,
            "electron_bridge_enabled": self.electron_bridge_enabled,
            "data_directory": str(self.data_directory),
            "cache_directory": str(self.cache_directory),
            "temp_directory": str(self.temp_directory)
        }


def main():
    """Main function for testing ServerConfig"""
    print("=== Server Config Test ===")
    
    # Static tests
    print("\n1. Testing default configuration...")
    config = ServerConfig()
    assert config.max_concurrent_servers == 10
    assert config.allow_anonymous_access is True
    assert config.data_directory.exists()
    print("✅ Default configuration created")
    
    print("\n2. Testing environment detection...")
    electron_mode = config._detect_electron_mode()
    assert isinstance(electron_mode, bool)
    print("✅ Electron mode detection working")
    
    print("\n3. Testing configuration serialization...")
    config_dict = config.to_dict()
    assert "max_concurrent_servers" in config_dict
    assert "electron_mode" in config_dict
    print("✅ Configuration serialization working")
    
    print("\n4. Testing directory creation...")
    assert config.cache_directory.exists()
    assert config.temp_directory.exists()
    print("✅ Directory creation working")


def test_dynamic():
    """Dynamic tests for ServerConfig"""
    print("\n=== Dynamic Tests ===")
    
    print("1. Testing environment-based configuration...")
    # Temporarily set environment variables
    original_max_servers = os.environ.get("MCP_MAX_SERVERS")
    os.environ["MCP_MAX_SERVERS"] = "5"
    
    try:
        env_config = ServerConfig.from_env()
        assert env_config.max_concurrent_servers == 5
        print("✅ Environment-based configuration working")
    finally:
        # Restore original value
        if original_max_servers:
            os.environ["MCP_MAX_SERVERS"] = original_max_servers
        else:
            os.environ.pop("MCP_MAX_SERVERS", None)
    
    print("\n2. Testing custom data directory...")
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        custom_config = ServerConfig(data_directory=Path(temp_dir) / "custom_mcp")
        assert custom_config.data_directory.exists()
        assert custom_config.cache_directory.exists()
        print("✅ Custom data directory working")
    
    print("\n3. Testing security configuration...")
    secure_config = ServerConfig(
        encryption_enabled=False,  # Keep disabled for test
        allow_anonymous_access=False,
        max_failed_attempts=3
    )
    assert secure_config.allow_anonymous_access is False
    assert secure_config.max_failed_attempts == 3
    print("✅ Security configuration working")
    
    print("\n🎉 All dynamic tests passed!")


if __name__ == "__main__":
    main()
    test_dynamic()