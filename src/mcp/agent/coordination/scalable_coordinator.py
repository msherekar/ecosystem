"""
Scalable Hybrid Coordinator
Production-ready coordinator with security and Electron integration.
"""

import asyncio
import logging
import signal
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
import weakref
import json
import os
from pathlib import Path

from .provider_registry import ProviderRegistry, ProviderConfig
from .load_balancer import AdvancedLoadBalancer, LoadBalancerConfig
from .intelligent_cache import IntelligentCache, CacheConfig


@dataclass
class CoordinatorConfig:
    """Configuration for scalable coordinator."""
    max_concurrent_requests: int = 100
    request_timeout: float = 30.0
    fallback_enabled: bool = True
    circuit_breaker_enabled: bool = True
    caching_enabled: bool = True
    metrics_collection: bool = True
    health_check_interval: int = 60
    auto_scaling_enabled: bool = False
    load_balancing_strategy: str = "weighted_round_robin"
    
    # Security settings
    enable_authentication: bool = True
    api_key_required: bool = False
    rate_limiting_enabled: bool = True
    max_requests_per_minute: int = 60
    
    # Electron integration
    electron_bridge_enabled: bool = False
    electron_port: int = 8080
    electron_host: str = "localhost"


@dataclass
class SecurityManager:
    """Security manager for coordinator."""
    
    def __init__(self, config: CoordinatorConfig):
        self.config = config
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self.rate_limits: Dict[str, List[float]] = {}
        self.logger = logging.getLogger("security_manager")
    
    def add_api_key(self, key: str, permissions: List[str] = None, rate_limit: int = None):
        """Add API key with permissions."""
        self.api_keys[key] = {
            'permissions': permissions or ['chat'],
            'rate_limit': rate_limit or self.config.max_requests_per_minute,
            'created_at': time.time()
        }
    
    def validate_api_key(self, key: str) -> bool:
        """Validate API key."""
        return key in self.api_keys
    
    def check_rate_limit(self, identifier: str) -> bool:
        """Check rate limiting for identifier."""
        if not self.config.rate_limiting_enabled:
            return True
        
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        if identifier in self.rate_limits:
            self.rate_limits[identifier] = [
                req_time for req_time in self.rate_limits[identifier] 
                if req_time > minute_ago
            ]
        else:
            self.rate_limits[identifier] = []
        
        # Check limit
        current_requests = len(self.rate_limits[identifier])
        if current_requests >= self.config.max_requests_per_minute:
            return False
        
        # Record request
        self.rate_limits[identifier].append(now)
        return True


class ScalableHybridCoordinator:
    """Production-ready scalable hybrid coordinator."""
    
    def __init__(
        self,
        config: CoordinatorConfig = None,
        provider_registry: ProviderRegistry = None,
        load_balancer: AdvancedLoadBalancer = None,
        cache: IntelligentCache = None
    ):
        self.config = config or CoordinatorConfig()
        self.logger = logging.getLogger("scalable_coordinator")
        
        # Core components
        self.provider_registry = provider_registry or ProviderRegistry()
        
        lb_config = LoadBalancerConfig(
            default_strategy=self.config.load_balancing_strategy,
            circuit_breaker_failure_threshold=5 if self.config.circuit_breaker_enabled else 999
        )
        self.load_balancer = load_balancer or AdvancedLoadBalancer(lb_config)
        
        cache_config = CacheConfig(
            local_cache_size=1000,
            similarity_threshold=0.8,
            cleanup_interval=300 if self.config.caching_enabled else 0
        )
        self.cache = cache or IntelligentCache(cache_config)
        
        # Security
        self.security_manager = SecurityManager(self.config)
        
        # Request management
        self.request_semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        self.active_requests: weakref.WeakSet = weakref.WeakSet()
        
        # Lifecycle management
        self.shutdown_event = asyncio.Event()
        self.background_tasks: List[asyncio.Task] = []
        
        # Metrics
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'rate_limited_requests': 0,
            'fallback_requests': 0,
            'avg_response_time': 0.0,
            'uptime_start': time.time()
        }
        
        # Electron integration
        self.electron_connected = False
        self.electron_websocket = None
        
        # Register built-in provider classes
        self._register_builtin_providers()
    
    def _register_builtin_providers(self):
        """Register built-in provider classes."""
        try:
            from src.mcp.agent.providers.external_provider import ExternalLLMProvider
            from src.mcp.agent.providers.local_provider import LocalLLMProvider
            
            self.provider_registry.register_provider_class("external", ExternalLLMProvider)
            self.provider_registry.register_provider_class("local", LocalLLMProvider)
        except ImportError as e:
            self.logger.warning(f"Could not import provider classes: {e}")
    
    async def initialize(self, config_path: str = None) -> bool:
        """Initialize coordinator and all components."""
        try:
            self.logger.info("Initializing scalable hybrid coordinator...")
            
            # Load configuration if provided
            if config_path:
                await self._load_configuration(config_path)
            
            # Start background tasks
            if self.config.health_check_interval > 0:
                health_task = asyncio.create_task(self._health_monitoring_loop())
                self.background_tasks.append(health_task)
            
            # Setup Electron bridge if enabled
            if self.config.electron_bridge_enabled:
                electron_task = asyncio.create_task(self._setup_electron_bridge())
                self.background_tasks.append(electron_task)
            
            # Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            self.logger.info("Scalable hybrid coordinator initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize coordinator: {e}")
            return False
    
    async def _load_configuration(self, config_path: str):
        """Load configuration from file."""
        config_path = Path(config_path)
        
        if config_path.exists():
            await self.provider_registry.reload_from_config(config_path)
            self.logger.info(f"Configuration loaded from {config_path}")
    
    @asynccontextmanager
    async def request_context(self, request_id: str = None):
        """Context manager for request lifecycle with security."""
        request_id = request_id or str(uuid.uuid4())
        
        # Acquire semaphore
        await self.request_semaphore.acquire()
        
        try:
            # Track active request
            current_task = asyncio.current_task()
            self.active_requests.add(current_task)
            
            self.metrics['total_requests'] += 1
            
            yield request_id
            
        finally:
            # Release semaphore
            self.request_semaphore.release()
    
    async def chat(
        self, 
        user_message: str, 
        context: Dict[str, Any] = None,
        api_key: str = None,
        client_id: str = None,
        **kwargs
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        """
        Enhanced chat method with security and scalability.
        
        Returns:
            Tuple of (response, flags, metadata)
        """
        
        start_time = time.time()
        metadata = {
            'request_id': str(uuid.uuid4()),
            'start_time': start_time,
            'provider_used': None,
            'cache_hit': False,
            'fallback_used': False,
            'security_checks': {}
        }
        
        # Security checks
        if self.config.enable_authentication:
            if self.config.api_key_required and not self.security_manager.validate_api_key(api_key):
                return "Authentication failed: Invalid API key", [], metadata
            
            identifier = client_id or api_key or "anonymous"
            if not self.security_manager.check_rate_limit(identifier):
                self.metrics['rate_limited_requests'] += 1
                return "Rate limit exceeded. Please try again later.", [], metadata
            
            metadata['security_checks']['rate_limit_passed'] = True
        
        async with self.request_context(metadata['request_id']) as request_id:
            try:
                # Check cache if enabled
                if self.config.caching_enabled:
                    cache_key = self.cache._generate_cache_key(
                        "chat", user_message, context
                    )
                    cached_result = await self.cache.get(cache_key)
                    
                    if cached_result:
                        metadata['cache_hit'] = True
                        response, flags = cached_result
                        self.metrics['successful_requests'] += 1
                        return response, flags, metadata
                
                # Get available providers
                available_providers = self.provider_registry.get_available_providers()
                
                if not available_providers:
                    raise Exception("No providers available")
                
                # Execute with load balancing
                try:
                    result, selected_provider = await asyncio.wait_for(
                        self.load_balancer.execute_with_load_balancing(
                            available_providers,
                            'chat',
                            user_message,
                            context or {},
                            strategy=self.config.load_balancing_strategy
                        ),
                        timeout=self.config.request_timeout
                    )
                    
                    response, flags = result
                    metadata['provider_used'] = selected_provider
                    
                    # Cache result if enabled
                    if self.config.caching_enabled:
                        await self.cache.set(cache_key, (response, flags))
                    
                    # Update metrics
                    execution_time = time.time() - start_time
                    self._update_metrics(execution_time, success=True)
                    
                    # Send to Electron if connected
                    if self.electron_connected:
                        await self._send_to_electron({
                            'type': 'chat_response',
                            'data': {'response': response, 'metadata': metadata}
                        })
                    
                    return response, flags, metadata
                    
                except asyncio.TimeoutError:
                    raise Exception(f"Request timed out after {self.config.request_timeout}s")
                    
                except Exception as e:
                    # Try fallback if enabled
                    if self.config.fallback_enabled:
                        return await self._try_fallback(
                            user_message, context, metadata, start_time
                        )
                    else:
                        raise e
                        
            except Exception as e:
                self.metrics['failed_requests'] += 1
                self.logger.error(f"Chat request failed: {e}")
                return f"I encountered an error: {str(e)}", [], metadata
    
    async def _try_fallback(
        self,
        user_message: str,
        context: Dict[str, Any],
        metadata: Dict[str, Any],
        start_time: float
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        """Try fallback providers when primary fails."""
        
        available_providers = self.provider_registry.get_available_providers()
        
        for provider_name, provider in available_providers.items():
            try:
                response, flags = await provider.chat(user_message, context)
                
                metadata['provider_used'] = provider_name
                metadata['fallback_used'] = True
                self.metrics['fallback_requests'] += 1
                
                execution_time = time.time() - start_time
                self._update_metrics(execution_time, success=True)
                
                return response, flags, metadata
                
            except Exception as e:
                self.logger.warning(f"Fallback provider {provider_name} failed: {e}")
                continue
        
        return "All providers failed. Please try again later.", [], metadata
    
    def _update_metrics(self, execution_time: float, success: bool):
        """Update coordinator metrics."""
        if success:
            self.metrics['successful_requests'] += 1
        
        # Update average response time
        total_successful = self.metrics['successful_requests']
        if total_successful > 0:
            current_avg = self.metrics['avg_response_time']
            self.metrics['avg_response_time'] = (
                (current_avg * (total_successful - 1) + execution_time) / total_successful
            )
    
    async def _health_monitoring_loop(self):
        """Background health monitoring loop."""
        while not self.shutdown_event.is_set():
            try:
                health_report = self.provider_registry.get_provider_health()
                
                # Log unhealthy providers
                for provider_name, health in health_report.items():
                    if health['status'] == 'unhealthy':
                        self.logger.warning(f"Provider {provider_name} is unhealthy")
                
                await asyncio.sleep(self.config.health_check_interval)
                
            except Exception as e:
                self.logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(self.config.health_check_interval)
    
    async def _setup_electron_bridge(self):
        """Setup Electron WebSocket bridge."""
        try:
            import websockets
            
            async def handle_electron_client(websocket, path):
                self.electron_websocket = websocket
                self.electron_connected = True
                self.logger.info("Electron client connected")
                
                try:
                    async for message in websocket:
                        data = json.loads(message)
                        await self._handle_electron_message(data)
                except websockets.exceptions.ConnectionClosed:
                    self.logger.info("Electron client disconnected")
                finally:
                    self.electron_connected = False
                    self.electron_websocket = None
            
            server = websockets.serve(
                handle_electron_client,
                self.config.electron_host,
                self.config.electron_port
            )
            
            self.logger.info(f"Electron bridge listening on {self.config.electron_host}:{self.config.electron_port}")
            await server
            
        except ImportError:
            self.logger.warning("websockets library not available for Electron bridge")
        except Exception as e:
            self.logger.error(f"Failed to setup Electron bridge: {e}")
    
    async def _handle_electron_message(self, data: Dict[str, Any]):
        """Handle message from Electron frontend."""
        try:
            message_type = data.get('type')
            
            if message_type == 'chat':
                user_message = data.get('message', '')
                context = data.get('context', {})
                
                response, flags, metadata = await self.chat(
                    user_message, context, client_id='electron'
                )
                
                await self._send_to_electron({
                    'type': 'chat_response',
                    'data': {'response': response, 'flags': flags, 'metadata': metadata}
                })
            
            elif message_type == 'status':
                status = self.get_status()
                await self._send_to_electron({
                    'type': 'status_response',
                    'data': status
                })
                
        except Exception as e:
            self.logger.error(f"Error handling Electron message: {e}")
    
    async def _send_to_electron(self, data: Dict[str, Any]):
        """Send data to Electron frontend."""
        if self.electron_connected and self.electron_websocket:
            try:
                await self.electron_websocket.send(json.dumps(data))
            except Exception as e:
                self.logger.error(f"Failed to send to Electron: {e}")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def shutdown(self):
        """Graceful shutdown of coordinator."""
        self.logger.info("Starting graceful shutdown...")
        
        # Set shutdown event
        self.shutdown_event.set()
        
        # Wait for active requests to complete (with timeout)
        try:
            active_tasks = list(self.active_requests)
            if active_tasks:
                self.logger.info(f"Waiting for {len(active_tasks)} active requests to complete")
                await asyncio.wait_for(
                    asyncio.gather(*active_tasks, return_exceptions=True),
                    timeout=30.0
                )
        except asyncio.TimeoutError:
            self.logger.warning("Some requests did not complete within timeout")
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Shutdown components
        await self.provider_registry.shutdown()
        await self.cache.shutdown()
        
        self.logger.info("Graceful shutdown completed")
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive coordinator status."""
        uptime = time.time() - self.metrics['uptime_start']
        
        return {
            'coordinator': {
                'uptime_seconds': uptime,
                'active_requests': len(self.active_requests),
                'max_concurrent_requests': self.config.max_concurrent_requests,
                'shutdown_initiated': self.shutdown_event.is_set(),
                'electron_connected': self.electron_connected
            },
            'metrics': self.metrics,
            'providers': self.provider_registry.get_provider_health(),
            'load_balancer': self.load_balancer.get_metrics(),
            'cache': self.cache.get_stats() if self.config.caching_enabled else None,
            'security': {
                'authentication_enabled': self.config.enable_authentication,
                'rate_limiting_enabled': self.config.rate_limiting_enabled,
                'api_keys_count': len(self.security_manager.api_keys)
            }
        }
    
    async def reload_configuration(self, config_path: str):
        """Reload configuration from file."""
        await self.provider_registry.reload_from_config(config_path)
        self.logger.info("Configuration reloaded successfully")


def main():
    """Test the scalable coordinator individually."""
    import asyncio
    import os
    
    async def test_scalable_coordinator():
        print("🧪 Testing ScalableHybridCoordinator...")
        
        # Create coordinator with test configuration
        config = CoordinatorConfig(
            max_concurrent_requests=10,
            request_timeout=5.0,
            caching_enabled=True,
            rate_limiting_enabled=True,
            max_requests_per_minute=10
        )
        
        coordinator = ScalableHybridCoordinator(config)
        print("✅ Coordinator initialized")
        
        # Initialize
        success = await coordinator.initialize()
        print(f"✅ Coordinator initialization: {success}")
        
        # Test security manager
        coordinator.security_manager.add_api_key("test_key", ["chat"], 5)
        print("✅ API key added")
        
        # Test rate limiting
        for i in range(3):
            valid = coordinator.security_manager.check_rate_limit("test_client")
            print(f"✅ Rate limit check {i+1}: {valid}")
        
        # Test chat (without providers, will fail gracefully)
        try:
            response, flags, metadata = await coordinator.chat(
                "Hello test", 
                api_key="test_key", 
                client_id="test_client"
            )
            print(f"✅ Chat response: {response[:50]}...")
        except Exception as e:
            print(f"⚠️  Chat failed (expected without providers): {e}")
        
        # Test status
        status = coordinator.get_status()
        print(f"✅ Status check: uptime={status['coordinator']['uptime_seconds']:.1f}s")
        
        # Test metrics
        metrics = status['metrics']
        print(f"✅ Metrics: total_requests={metrics['total_requests']}")
        
        # Test shutdown
        await coordinator.shutdown()
        print("✅ Coordinator shutdown complete")
        
        print("🎉 Scalable coordinator tests completed!")
    
    # Run tests
    asyncio.run(test_scalable_coordinator())


if __name__ == "__main__":
    main() 