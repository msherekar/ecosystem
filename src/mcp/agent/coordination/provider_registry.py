"""
Dynamic Provider Registry
Manages LLM providers with health monitoring and hot reloading.
"""

import asyncio
import logging
import json
import yaml
from typing import Dict, List, Any, Optional, Type, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager


@dataclass
class ProviderConfig:
    """Configuration for LLM providers."""
    provider_type: str
    provider_class: str
    initialization_params: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    enabled: bool = True
    health_check_interval: int = 60  # seconds
    max_concurrent_requests: int = 10
    timeout: float = 30.0
    retry_policy: Dict[str, Any] = field(default_factory=lambda: {
        'max_retries': 3,
        'backoff_factor': 1.0,
        'max_backoff': 60.0
    })


class ProviderRegistry:
    """Dynamic registry for LLM providers with hot reloading."""
    
    def __init__(self):
        self.providers: Dict[str, Any] = {}
        self.provider_configs: Dict[str, ProviderConfig] = {}
        self.provider_classes: Dict[str, Type] = {}
        self.initialization_lock = asyncio.Lock()
        self.logger = logging.getLogger("provider_registry")
        
        # Provider lifecycle management
        self.provider_lifecycles: Dict[str, Dict[str, Any]] = {}
        self.cleanup_tasks: Dict[str, asyncio.Task] = {}
        self.shutdown_event = asyncio.Event()
        
    def register_provider_class(self, provider_type: str, provider_class: Type):
        """Register a provider class for dynamic instantiation."""
        self.provider_classes[provider_type] = provider_class
        self.logger.info(f"Registered provider class: {provider_type}")
    
    async def register_provider(
        self, 
        name: str, 
        config: ProviderConfig,
        auto_initialize: bool = True
    ) -> bool:
        """Register and optionally initialize a provider."""
        
        async with self.initialization_lock:
            try:
                self.provider_configs[name] = config
                
                if auto_initialize and config.enabled:
                    success = await self._initialize_provider(name, config)
                    if success:
                        self.logger.info(f"Provider {name} registered and initialized")
                        return True
                    else:
                        self.logger.warning(f"Provider {name} registered but initialization failed")
                        return False
                else:
                    self.logger.info(f"Provider {name} registered (initialization deferred)")
                    return True
                    
            except Exception as e:
                self.logger.error(f"Failed to register provider {name}: {e}")
                return False
    
    async def _initialize_provider(self, name: str, config: ProviderConfig) -> bool:
        """Initialize a single provider."""
        try:
            # Get provider class
            provider_class = self.provider_classes.get(config.provider_class)
            if not provider_class:
                raise ValueError(f"Unknown provider class: {config.provider_class}")
            
            # Create provider instance - pass initialization_params as config dict
            provider = provider_class(config=config.initialization_params)
            
            # Initialize provider
            init_success = await provider.initialize()
            if init_success:
                self.providers[name] = provider
                self.provider_lifecycles[name] = {
                    'initialized_at': datetime.now(),
                    'last_health_check': None,
                    'health_status': 'unknown',
                    'request_count': 0,
                    'error_count': 0
                }
                
                # Start health monitoring
                await self._start_health_monitoring(name, config)
                return True
            else:
                self.logger.error(f"Provider {name} initialization failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error initializing provider {name}: {e}")
            return False
    
    async def _start_health_monitoring(self, name: str, config: ProviderConfig):
        """Start health monitoring for a provider."""
        async def health_monitor():
            while name in self.providers and not self.shutdown_event.is_set():
                try:
                    provider = self.providers[name]
                    health_status = 'healthy' if provider.is_available() else 'unhealthy'
                    
                    self.provider_lifecycles[name]['last_health_check'] = datetime.now()
                    self.provider_lifecycles[name]['health_status'] = health_status
                    
                    if health_status == 'unhealthy':
                        self.logger.warning(f"Provider {name} is unhealthy")
                    
                    await asyncio.sleep(config.health_check_interval)
                    
                except Exception as e:
                    self.logger.error(f"Health check failed for provider {name}: {e}")
                    await asyncio.sleep(config.health_check_interval)
        
        # Store cleanup task
        if name not in self.cleanup_tasks:
            task = asyncio.create_task(health_monitor())
            self.cleanup_tasks[name] = task
    
    async def unregister_provider(self, name: str) -> bool:
        """Unregister and cleanup a provider."""
        try:
            # Cancel health monitoring
            if name in self.cleanup_tasks:
                self.cleanup_tasks[name].cancel()
                del self.cleanup_tasks[name]
            
            # Cleanup provider
            if name in self.providers:
                provider = self.providers[name]
                if hasattr(provider, 'cleanup'):
                    await provider.cleanup()
                del self.providers[name]
            
            # Remove lifecycle tracking
            if name in self.provider_lifecycles:
                del self.provider_lifecycles[name]
            
            # Remove config
            if name in self.provider_configs:
                del self.provider_configs[name]
            
            self.logger.info(f"Provider {name} unregistered successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unregister provider {name}: {e}")
            return False
    
    def get_available_providers(self) -> Dict[str, Any]:
        """Get all available providers."""
        available = {}
        for name, provider in self.providers.items():
            if provider.is_available():
                available[name] = provider
        return available
    
    def get_provider_health(self) -> Dict[str, Any]:
        """Get health status of all providers."""
        health_report = {}
        for name, lifecycle in self.provider_lifecycles.items():
            config = self.provider_configs.get(name)
            health_report[name] = {
                'status': lifecycle['health_status'],
                'last_check': lifecycle['last_health_check'],
                'uptime': datetime.now() - lifecycle['initialized_at'],
                'request_count': lifecycle['request_count'],
                'error_count': lifecycle['error_count'],
                'error_rate': (
                    lifecycle['error_count'] / max(lifecycle['request_count'], 1)
                ),
                'enabled': config.enabled if config else False
            }
        return health_report
    
    async def reload_from_config(self, config_path: Union[str, Path]):
        """Reload provider configuration from file."""
        try:
            config_path = Path(config_path)
            
            if config_path.suffix.lower() == '.yaml':
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
            elif config_path.suffix.lower() == '.json':
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
            else:
                raise ValueError("Config file must be YAML or JSON")
            
            # Process provider configurations
            for provider_name, provider_data in config_data.get('providers', {}).items():
                config = ProviderConfig(
                    provider_type=provider_data['type'],
                    provider_class=provider_data['class'],
                    initialization_params=provider_data.get('params', {}),
                    priority=provider_data.get('priority', 0),
                    enabled=provider_data.get('enabled', True),
                    health_check_interval=provider_data.get('health_check_interval', 60),
                    max_concurrent_requests=provider_data.get('max_concurrent_requests', 10),
                    timeout=provider_data.get('timeout', 30.0),
                    retry_policy=provider_data.get('retry_policy', {
                        'max_retries': 3,
                        'backoff_factor': 1.0,
                        'max_backoff': 60.0
                    })
                )
                
                # Re-register provider
                await self.register_provider(provider_name, config)
            
            self.logger.info(f"Configuration reloaded from {config_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to reload configuration: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown registry and cleanup all providers."""
        self.shutdown_event.set()
        
        # Cleanup all providers
        for provider_name in list(self.providers.keys()):
            await self.unregister_provider(provider_name)
        
        self.logger.info("Provider registry shutdown complete")


def main():
    """Test the provider registry individually."""
    import asyncio
    import os
    
    async def test_provider_registry():
        print("🧪 Testing ProviderRegistry...")
        
        # Test registry initialization
        registry = ProviderRegistry()
        print("✅ Registry initialized")
        
        # Test provider class registration
        from src.mcp.agent.providers.external_provider import ExternalLLMProvider
        from src.mcp.agent.providers.local_provider import LocalLLMProvider
        
        registry.register_provider_class("external", ExternalLLMProvider)
        registry.register_provider_class("local", LocalLLMProvider)
        print("✅ Provider classes registered")
        
        # Test provider configuration
        local_config = ProviderConfig(
            provider_type="local",
            provider_class="local",
            initialization_params={},
            priority=1,
            enabled=True
        )
        
        success = await registry.register_provider("test_local", local_config)
        print(f"✅ Local provider registration: {success}")
        
        # Test health monitoring
        await asyncio.sleep(2)  # Let health check run
        health = registry.get_provider_health()
        print(f"✅ Health check: {len(health)} providers monitored")
        
        # Test available providers
        available = registry.get_available_providers()
        print(f"✅ Available providers: {list(available.keys())}")
        
        # Test unregistration
        await registry.unregister_provider("test_local")
        print("✅ Provider unregistered")
        
        # Test shutdown
        await registry.shutdown()
        print("✅ Registry shutdown complete")
        
        print("🎉 Provider registry tests completed!")
    
    # Run tests
    asyncio.run(test_provider_registry())


if __name__ == "__main__":
    main() 