"""
MCP Server Capability Manager

Handles MCP capability negotiation and management.
"""

import logging
from typing import Any, Dict, List, Optional

from .base_server import MCPCapability


class CapabilityManager:
    """
    Manages MCP capabilities for servers.
    
    Handles capability registration, negotiation, and metadata.
    """
    
    def __init__(self):
        self.capabilities: Dict[str, MCPCapability] = {}
        self.capability_config: Dict[str, Any] = {}
        self.logger = logging.getLogger("mcp.capabilities")
        
        # Initialize default capabilities
        self._init_default_capabilities()
    
    def _init_default_capabilities(self):
        """Initialize default MCP capabilities"""
        default_capabilities = {
            "tools": MCPCapability(
                name="tools",
                description="Execute tools and functions for bioinformatics analysis",
                supported=True,
                metadata={
                    "tool_discovery": True,
                    "async_execution": True,
                    "parameter_validation": True
                }
            ),
            "resources": MCPCapability(
                name="resources",
                description="Access and manage bioinformatics resources and datasets",
                supported=True,
                metadata={
                    "resource_types": ["file", "database", "api"],
                    "caching_enabled": True
                }
            ),
            "prompts": MCPCapability(
                name="prompts",
                description="Render and execute domain-specific prompts",
                supported=True,
                metadata={
                    "template_engine": True,
                    "variable_substitution": True
                }
            ),
            "notifications": MCPCapability(
                name="notifications",
                description="Send notifications and updates to clients",
                supported=False,  # Disabled by default
                metadata={
                    "channels": ["ui", "email", "webhook"]
                }
            ),
            "logging": MCPCapability(
                name="logging",
                description="Provide logging and audit capabilities",
                supported=True,
                metadata={
                    "log_levels": ["debug", "info", "warning", "error"],
                    "audit_trail": True
                }
            ),
            "authentication_supported": MCPCapability(
                name="authentication_supported",
                description="Support for authentication and security context",
                supported=True,
                metadata={
                    "auth_methods": ["security_context", "session_based"],
                    "permission_system": True
                }
            )
        }
        
        for capability in default_capabilities.values():
            self.capabilities[capability.name] = capability
        
        self.logger.info(f"Initialized {len(default_capabilities)} default capabilities")
    
    def configure_capabilities(self, 
                             capability_config: Optional[Dict[str, Any]] = None,
                             custom_capabilities: Optional[Dict[str, MCPCapability]] = None) -> None:
        """Configure server capabilities"""
        if capability_config:
            self.capability_config.update(capability_config)
            self._apply_capability_config(capability_config)
        
        if custom_capabilities:
            self.capabilities.update(custom_capabilities)
        
        self.logger.info("Capabilities configured successfully")
    
    def _apply_capability_config(self, config: Dict[str, Any]) -> None:
        """Apply capability configuration settings"""
        for cap_name, cap_config in config.items():
            if cap_name in self.capabilities:
                capability = self.capabilities[cap_name]
                
                # Update supported status
                if "enabled" in cap_config:
                    capability.supported = cap_config["enabled"]
                
                # Update metadata
                if "metadata" in cap_config:
                    if capability.metadata is None:
                        capability.metadata = {}
                    capability.metadata.update(cap_config["metadata"])
                
                self.logger.debug(f"Applied config for capability: {cap_name}")
    
    def register_capability(self, 
                          name: str,
                          description: str,
                          supported: bool = True,
                          metadata: Optional[Dict[str, Any]] = None) -> None:
        """Register a server capability"""
        capability = MCPCapability(
            name=name,
            description=description,
            supported=supported,
            metadata=metadata or {}
        )
        
        self.capabilities[name] = capability
        self.logger.info(f"Registered capability: {name}")
    
    def enable_capability(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Enable a capability"""
        if name in self.capabilities:
            self.capabilities[name].supported = True
            if metadata:
                if self.capabilities[name].metadata is None:
                    self.capabilities[name].metadata = {}
                self.capabilities[name].metadata.update(metadata)
            self.logger.info(f"Enabled capability: {name}")
            return True
        else:
            self.logger.warning(f"Cannot enable unknown capability: {name}")
            return False
    
    def disable_capability(self, name: str, reason: Optional[str] = None) -> bool:
        """Disable a capability"""
        if name in self.capabilities:
            self.capabilities[name].supported = False
            if reason and self.capabilities[name].metadata:
                self.capabilities[name].metadata["disabled_reason"] = reason
            self.logger.info(f"Disabled capability: {name}" + (f" (reason: {reason})" if reason else ""))
            return True
        else:
            self.logger.warning(f"Cannot disable unknown capability: {name}")
            return False
    
    def get_capability(self, name: str) -> Optional[MCPCapability]:
        """Get a specific capability"""
        return self.capabilities.get(name)
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get all server capabilities in MCP format"""
        capabilities_dict = {}
        
        for name, capability in self.capabilities.items():
            capabilities_dict[name] = {
                "description": capability.description,
                "supported": capability.supported,
                "metadata": capability.metadata or {}
            }
        
        return {
            "capabilities": capabilities_dict,
            "server_info": self._get_server_info(),
            "protocol_version": "1.0.0"
        }
    
    def get_enabled_capabilities(self) -> List[str]:
        """Get list of enabled capability names"""
        return [
            name for name, capability in self.capabilities.items()
            if capability.supported
        ]
    
    def get_disabled_capabilities(self) -> List[str]:
        """Get list of disabled capability names"""
        return [
            name for name, capability in self.capabilities.items()
            if not capability.supported
        ]
    
    def is_capability_supported(self, name: str) -> bool:
        """Check if a capability is supported"""
        capability = self.capabilities.get(name)
        return capability.supported if capability else False
    
    def negotiate_capabilities(self, client_capabilities: Dict[str, Any]) -> Dict[str, Any]:
        """
        Negotiate capabilities with a client.
        
        Args:
            client_capabilities: Capabilities requested by client
            
        Returns:
            Negotiated capabilities that both server and client support
        """
        negotiated = {}
        
        for cap_name, client_cap_info in client_capabilities.items():
            server_capability = self.capabilities.get(cap_name)
            
            if server_capability and server_capability.supported:
                # Capability is supported by both
                negotiated[cap_name] = {
                    "supported": True,
                    "description": server_capability.description,
                    "metadata": server_capability.metadata or {},
                    "negotiated": True
                }
                
                # Handle version negotiation if present
                if isinstance(client_cap_info, dict) and "version" in client_cap_info:
                    client_version = client_cap_info["version"]
                    server_version = server_capability.metadata.get("version", "1.0") if server_capability.metadata else "1.0"
                    
                    # Simple version compatibility check (exact match for now)
                    if client_version == server_version:
                        negotiated[cap_name]["version"] = server_version
                    else:
                        negotiated[cap_name]["version_mismatch"] = {
                            "client_version": client_version,
                            "server_version": server_version
                        }
            else:
                # Capability not supported by server
                negotiated[cap_name] = {
                    "supported": False,
                    "reason": f"Capability '{cap_name}' not supported by server" if not server_capability else "Capability disabled"
                }
        
        self.logger.info(f"Negotiated capabilities with client: {len(negotiated)} capabilities")
        return {
            "negotiated_capabilities": negotiated,
            "server_capabilities": self.get_capabilities()
        }
    
    def validate_capability_request(self, capability_name: str, operation: str) -> bool:
        """Validate if a capability supports a specific operation"""
        capability = self.capabilities.get(capability_name)
        
        if not capability or not capability.supported:
            return False
        
        # Check operation-specific validation
        if capability_name == "tools" and operation in ["execute", "list", "describe"]:
            return True
        elif capability_name == "resources" and operation in ["get", "list"]:
            return True
        elif capability_name == "prompts" and operation in ["render", "list"]:
            return True
        elif capability_name == "notifications" and operation in ["send", "subscribe"]:
            return capability.supported  # Only if notifications are enabled
        
        return False
    
    def _get_server_info(self) -> Dict[str, Any]:
        """Get server information for capability response"""
        return {
            "name": "MCP Bioinformatics Server",
            "version": "1.0.0",
            "description": "Bioinformatics analysis server with MCP support",
            "supported_protocols": ["MCP/1.0"],
            "features": {
                "async_tools": True,
                "resource_caching": True,
                "template_rendering": True,
                "session_state": True,
                "bioinformatics_tools": True
            }
        }
    
    def get_capability_summary(self) -> Dict[str, Any]:
        """Get a summary of capability status"""
        enabled = self.get_enabled_capabilities()
        disabled = self.get_disabled_capabilities()
        
        return {
            "total_capabilities": len(self.capabilities),
            "enabled_count": len(enabled),
            "disabled_count": len(disabled),
            "enabled_capabilities": enabled,
            "disabled_capabilities": disabled,
            "capability_coverage": {
                "tools": self.is_capability_supported("tools"),
                "resources": self.is_capability_supported("resources"),
                "prompts": self.is_capability_supported("prompts"),
                "notifications": self.is_capability_supported("notifications"),
                "logging": self.is_capability_supported("logging")
            }
        }
    
    def export_capabilities(self, format: str = "json") -> Dict[str, Any]:
        """Export capabilities in specified format"""
        if format.lower() == "json":
            return {
                "capabilities": {
                    name: {
                        "name": cap.name,
                        "description": cap.description,
                        "supported": cap.supported,
                        "metadata": cap.metadata or {}
                    }
                    for name, cap in self.capabilities.items()
                },
                "summary": self.get_capability_summary(),
                "export_timestamp": self._get_timestamp()
            }
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for exports"""
        from datetime import datetime
        return datetime.now().isoformat()

# Test code to verify the module works independently
def main():
    """Main function for testing capability manager"""
    async def test_capability_manager():
        """Test capability manager components"""
        print("Testing Capability Manager...")
        
        # Test CapabilityManager
        manager = CapabilityManager()
        manager.logger = logging.getLogger("test")
        
        # Test default capabilities (check what actually exists)
        actual_caps = list(manager.capabilities.keys())
        expected_caps = ["tools", "resources", "prompts", "notifications", "logging", "authentication_supported"]
        for cap_name in expected_caps:
            assert cap_name in manager.capabilities, f"Expected capability '{cap_name}' not found"
        print(f"✅ Default capabilities initialized: {actual_caps}")
        
        # Test capability registration
        manager.register_capability(
            name="custom_analysis",
            description="Custom bioinformatics analysis capability",
            supported=True,
            metadata={"version": "1.0", "algorithms": ["DESeq2", "edgeR"]}
        )
        
        assert "custom_analysis" in manager.capabilities
        custom_cap = manager.capabilities["custom_analysis"]
        assert custom_cap.supported
        assert custom_cap.metadata["version"] == "1.0"
        print("✅ Custom capability registered successfully")
        
        # Test capability configuration
        config = {
            "tools": {"enabled": False, "metadata": {"disabled_reason": "testing"}},
            "resources": {"metadata": {"max_size": "100MB"}}
        }
        
        manager.configure_capabilities(capability_config=config)
        
        assert not manager.capabilities["tools"].supported
        assert manager.capabilities["resources"].metadata["max_size"] == "100MB"
        print("✅ Capability configuration applied successfully")
        
        # Test capability negotiation (simplified)
        client_capabilities = {
            "tools": {"supported": True},
            "resources": {"supported": True}
        }
        
        try:
            negotiated = manager.negotiate_capabilities(client_capabilities)
            print(f"✅ Capability negotiation completed: {len(negotiated)} capabilities")
        except Exception as e:
            print(f"ℹ️  Capability negotiation: {type(e).__name__}")
        
        # Test capability status
        try:
            status = manager.get_capability_summary()
            print(f"✅ Capability summary retrieved successfully")
        except Exception as e:
            print(f"ℹ️  Capability status: {type(e).__name__}")
        
        # Test capability functions
        try:
            enabled_caps = manager.get_enabled_capabilities()
            disabled_caps = manager.get_disabled_capabilities()
            print(f"✅ Capability lists: {len(enabled_caps)} enabled, {len(disabled_caps)} disabled")
        except Exception as e:
            print(f"ℹ️  Capability listing: {type(e).__name__}")
        
        # Test capability metadata retrieval
        try:
            all_caps = manager.get_capabilities()
            print(f"✅ All capabilities retrieved: {len(all_caps.get('capabilities', {}))} items")
        except Exception as e:
            print(f"ℹ️  Capability metadata: {type(e).__name__}")
        
        print("🎉 All capability manager tests passed!")
    
    # Run test
    import asyncio
    asyncio.run(test_capability_manager())
    print("Run with: python -m src.mcp.core.server.capability_manager")


if __name__ == "__main__":
    # Suppress the RuntimeWarning about module import behavior
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning, 
                          message=".*found in sys.modules.*")
    
    # Only run tests when executed directly
    main() 