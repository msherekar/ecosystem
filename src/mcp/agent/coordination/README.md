# Scalable Hybrid Coordinator

A production-ready, highly scalable LLM coordination system with advanced features including load balancing, circuit breakers, intelligent caching, security, and Electron UI integration.

## 🚀 Features

### Core Features
- **Dynamic Provider Management**: Hot-reloadable provider configuration
- **Advanced Load Balancing**: Multiple strategies with circuit breaker protection
- **Intelligent Caching**: Multi-level cache with semantic similarity
- **Security**: Authentication, rate limiting, and access control
- **Electron Integration**: WebSocket bridge for desktop applications
- **Production Ready**: Graceful shutdown, metrics, health monitoring

### Load Balancing Strategies
- `weighted_round_robin` - Performance-based weighted selection
- `round_robin` - Simple round-robin distribution
- `least_connections` - Route to provider with fewest active connections
- `response_time` - Route to fastest responding provider
- `priority` - Context-aware priority-based routing
- `random` - Random provider selection

### Security Features
- API key authentication
- Rate limiting per client
- Connection security for Electron bridge
- Request validation and sanitization

## 📁 Architecture

```
coordination/
├── scalable_coordinator.py     # Main production coordinator
├── provider_registry.py        # Dynamic provider management
├── load_balancer.py            # Advanced load balancing
├── intelligent_cache.py        # Multi-level caching
├── electron_bridge.py          # Electron WebSocket bridge
├── hybrid_coordinator.py       # Backward compatibility wrapper
└── README.md                   # This file
```

## 🛠️ Quick Start

### Basic Usage

```python
import asyncio
from src.mcp.agent.coordination import (
    ScalableHybridCoordinator, 
    CoordinatorConfig,
    ProviderConfig
)

async def main():
    # Create coordinator with configuration
    config = CoordinatorConfig(
        max_concurrent_requests=50,
        caching_enabled=True,
        load_balancing_strategy="weighted_round_robin",
        rate_limiting_enabled=True
    )
    
    coordinator = ScalableHybridCoordinator(config)
    
    # Initialize
    await coordinator.initialize()
    
    # Chat with automatic provider selection and load balancing
    response, flags, metadata = await coordinator.chat(
        "What is machine learning?",
        context={"domain": "technical"}
    )
    
    print(f"Response: {response}")
    print(f"Provider used: {metadata['provider_used']}")
    print(f"Cache hit: {metadata['cache_hit']}")
    
    # Get comprehensive status
    status = coordinator.get_status()
    print(f"Active requests: {status['coordinator']['active_requests']}")
    print(f"Cache hit rate: {status['cache']['hit_rate']:.2f}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Configuration-Based Setup

```python
import asyncio
from src.mcp.agent.coordination import ScalableHybridCoordinator

async def main():
    coordinator = ScalableHybridCoordinator()
    
    # Initialize with configuration file
    await coordinator.initialize("config/scalable_coordinator.yaml")
    
    # Chat requests are automatically load balanced and cached
    response, flags, metadata = await coordinator.chat(
        "Explain quantum computing",
        api_key="your-api-key",  # Optional for authentication
        client_id="user_123"     # For rate limiting
    )

if __name__ == "__main__":
    asyncio.run(main())
```

## ⚙️ Configuration

### YAML Configuration File

Create `config/scalable_coordinator.yaml`:

```yaml
coordinator:
  max_concurrent_requests: 100
  request_timeout: 30.0
  fallback_enabled: true
  circuit_breaker_enabled: true
  caching_enabled: true
  load_balancing_strategy: "weighted_round_robin"
  
  security:
    enable_authentication: true
    rate_limiting_enabled: true
    max_requests_per_minute: 60

providers:
  external_openai:
    type: "external"
    class: "external"
    priority: 1
    enabled: true
    params:
      api_key: "${OPENAI_API_KEY}"
      model: "gpt-4"
  
  local_ollama:
    type: "local"
    class: "local"
    priority: 0
    enabled: true
    params:
      model: "llama3.1:8b"
      base_url: "http://localhost:11434"

cache:
  local_cache_size: 1000
  similarity_threshold: 0.8
  default_ttl: 3600
  enable_semantic_cache: true
```

### Programmatic Provider Registration

```python
from src.mcp.agent.coordination import ProviderRegistry, ProviderConfig

async def setup_providers():
    registry = ProviderRegistry()
    
    # Register external provider
    external_config = ProviderConfig(
        provider_type="external",
        provider_class="external",
        initialization_params={
            "api_key": "your-api-key",
            "model": "gpt-4"
        },
        priority=1,
        enabled=True,
        max_concurrent_requests=20
    )
    
    await registry.register_provider("openai", external_config)
    
    # Register local provider
    local_config = ProviderConfig(
        provider_type="local",
        provider_class="local",
        initialization_params={
            "model": "llama3.1:8b"
        },
        priority=0,
        enabled=True
    )
    
    await registry.register_provider("ollama", local_config)
```

## 🔄 Load Balancing

### Strategy Selection

```python
# Different strategies for different use cases
strategies = {
    "performance": "weighted_round_robin",  # Best overall performance
    "simple": "round_robin",               # Simple distribution
    "efficiency": "least_connections",     # Resource efficiency
    "speed": "response_time",              # Fastest response
    "priority": "priority",                # Context-aware routing
    "testing": "random"                    # Random for testing
}

# Set strategy dynamically
coordinator.config.load_balancing_strategy = strategies["performance"]
```

### Circuit Breaker Configuration

```python
from src.mcp.agent.coordination import LoadBalancerConfig

lb_config = LoadBalancerConfig(
    circuit_breaker_failure_threshold=5,  # Open after 5 failures
    circuit_breaker_timeout=60.0,         # Try reset after 60s
    metrics_window_size=100               # Track last 100 requests
)

coordinator = ScalableHybridCoordinator(
    load_balancer=AdvancedLoadBalancer(lb_config)
)
```

## 💾 Intelligent Caching

### Cache Configuration

```python
from src.mcp.agent.coordination import CacheConfig, IntelligentCache

cache_config = CacheConfig(
    local_cache_size=2000,
    similarity_threshold=0.8,    # 80% similarity for semantic cache hits
    default_ttl=3600,           # 1 hour default
    enable_semantic_cache=True,
    memory_limit_mb=200         # 200MB memory limit
)

cache = IntelligentCache(cache_config)
```

### Cache Usage

```python
# Manual cache operations
await cache.set("key", "value", ttl=1800)  # 30 minutes
cached_value = await cache.get("key")

# Semantic similarity example
await cache.set("machine learning basics", "ML is...")
similar_result = await cache.get("what is machine learning")  # May hit cache!

# Cache statistics
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']:.2f}")
print(f"Semantic hits: {stats['semantic_hits']}")
```

## 🔒 Security

### Authentication Setup

```python
# Add API keys
coordinator.security_manager.add_api_key(
    "api_key_123", 
    permissions=["chat", "status"],
    rate_limit=100  # requests per minute
)

# Chat with authentication
response, flags, metadata = await coordinator.chat(
    "Hello",
    api_key="api_key_123",
    client_id="user_456"
)
```

### Rate Limiting

```python
# Configure rate limiting
config = CoordinatorConfig(
    rate_limiting_enabled=True,
    max_requests_per_minute=60
)

# Rate limiting is automatically applied per client_id or api_key
```

## 🖥️ Electron Integration

### WebSocket Bridge Setup

```python
from src.mcp.agent.coordination import ElectronBridge, ElectronConfig

# Configure Electron bridge
electron_config = ElectronConfig(
    host="localhost",
    port=8080,
    max_connections=20,
    heartbeat_interval=30.0
)

bridge = ElectronBridge(electron_config, coordinator)
await bridge.start()
```

### Frontend Integration (JavaScript)

```javascript
// Connect to coordinator
const ws = new WebSocket('ws://localhost:8080');

// Authenticate
ws.send(JSON.stringify({
    type: 'authenticate',
    token: 'electron_demo_token'
}));

// Send chat message
ws.send(JSON.stringify({
    type: 'chat',
    message: 'Hello from Electron!',
    context: { source: 'electron_app' }
}));

// Handle responses
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'chat_response') {
        console.log('Response:', data.data.response);
        console.log('Provider:', data.data.metadata.provider_used);
    }
};
```

### Custom Message Handlers

```python
# Register custom Electron message handler
async def custom_handler(connection_id, message):
    # Process custom message type
    result = await process_custom_request(message)
    
    # Send response back to Electron
    await bridge._send_message_to_connection(connection_id, {
        'type': 'custom_response',
        'data': result
    })

bridge.register_handler('custom_request', custom_handler)
```

## 📊 Monitoring & Metrics

### Status Monitoring

```python
# Get comprehensive status
status = coordinator.get_status()

print("Coordinator Status:")
print(f"  Uptime: {status['coordinator']['uptime_seconds']:.0f}s")
print(f"  Active requests: {status['coordinator']['active_requests']}")

print("Provider Health:")
for name, health in status['providers'].items():
    print(f"  {name}: {health['status']} ({health['request_count']} requests)")

print("Load Balancer:")
for name, metrics in status['load_balancer'].items():
    if isinstance(metrics, dict):
        print(f"  {name}: {metrics['success_rate']:.2f} success rate")

print("Cache:")
if status['cache']:
    print(f"  Hit rate: {status['cache']['hit_rate']:.2f}")
    print(f"  Memory usage: {status['cache']['local_cache']['memory_usage_mb']:.1f}MB")
```

### Performance Metrics

```python
# Reset metrics for testing
coordinator.reset_statistics()

# Run some operations...
for i in range(10):
    await coordinator.chat(f"Test message {i}")

# Check performance
final_status = coordinator.get_status()
avg_response_time = final_status['metrics']['avg_response_time']
print(f"Average response time: {avg_response_time:.3f}s")
```

## 🧪 Testing

### Individual Component Testing

```python
# Test each component individually
if __name__ == "__main__":
    # Test provider registry
    from src.mcp.agent.coordination.provider_registry import main as test_registry
    test_registry()
    
    # Test load balancer
    from src.mcp.agent.coordination.load_balancer import main as test_lb
    test_lb()
    
    # Test cache
    from src.mcp.agent.coordination.intelligent_cache import main as test_cache
    test_cache()
    
    # Test full coordinator
    from src.mcp.agent.coordination.scalable_coordinator import main as test_coordinator
    test_coordinator()
```

### Integration Testing

```python
async def integration_test():
    coordinator = ScalableHybridCoordinator()
    await coordinator.initialize("config/scalable_coordinator.yaml")
    
    # Test multiple concurrent requests
    tasks = []
    for i in range(20):
        task = coordinator.chat(f"Test message {i}")
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    
    # Verify results
    assert len(results) == 20
    assert all(len(result) == 3 for result in results)  # (response, flags, metadata)
    
    print("✅ Integration test passed!")

asyncio.run(integration_test())
```

## 🔧 Advanced Usage

### Custom Provider Implementation

```python
from src.mcp.agent.providers.base_provider import BaseProvider

class CustomProvider(BaseProvider):
    async def initialize(self) -> bool:
        # Custom initialization logic
        return True
    
    async def chat(self, message: str, context: Dict = None):
        # Custom chat implementation
        response = f"Custom response to: {message}"
        flags = ["custom"]
        return response, flags
    
    def is_available(self) -> bool:
        return True

# Register custom provider
coordinator.provider_registry.register_provider_class("custom", CustomProvider)
```

### Dynamic Configuration Updates

```python
# Hot reload configuration
await coordinator.reload_configuration("config/updated_config.yaml")

# Add provider at runtime
new_config = ProviderConfig(
    provider_type="external",
    provider_class="external",
    initialization_params={"api_key": "new_key"},
    enabled=True
)

await coordinator.provider_registry.register_provider("new_provider", new_config)
```

### Graceful Shutdown

```python
import signal

async def shutdown_handler():
    print("Initiating graceful shutdown...")
    await coordinator.shutdown()
    print("Shutdown complete")

# Register signal handler
signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(shutdown_handler()))
signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(shutdown_handler()))
```

## 🏗️ Production Deployment

### Docker Configuration

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ src/
COPY config/ config/

# Expose Electron bridge port
EXPOSE 8080

CMD ["python", "-m", "src.mcp.agent.coordination.scalable_coordinator"]
```

### Environment Variables

```bash
# Set API keys
export OPENAI_API_KEY="your-openai-key"
export OPENROUTER_API_KEY="your-openrouter-key"

# Set configuration
export COORDINATOR_CONFIG="config/production.yaml"
export LOG_LEVEL="INFO"
```

### Health Check Endpoint

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health_check():
    status = coordinator.get_status()
    
    # Check if any providers are healthy
    healthy_providers = [
        name for name, health in status['providers'].items()
        if health['status'] == 'healthy'
    ]
    
    if not healthy_providers:
        return {"status": "unhealthy", "providers": 0}
    
    return {
        "status": "healthy",
        "providers": len(healthy_providers),
        "uptime": status['coordinator']['uptime_seconds']
    }
```

## 📈 Performance Optimization

### Best Practices

1. **Provider Configuration**:
   - Set appropriate `max_concurrent_requests` per provider
   - Configure circuit breaker thresholds based on provider reliability
   - Use priority settings to prefer cost-effective providers

2. **Caching Strategy**:
   - Enable semantic caching for similar queries
   - Set appropriate TTL values based on content freshness requirements
   - Monitor memory usage and adjust limits

3. **Load Balancing**:
   - Use `weighted_round_robin` for production workloads
   - Monitor provider performance metrics
   - Adjust circuit breaker settings based on observed failure patterns

4. **Security**:
   - Enable rate limiting in production
   - Use API key authentication for external access
   - Monitor for suspicious activity patterns

## 🐛 Troubleshooting

### Common Issues

1. **Provider Connection Failures**:
   ```python
   # Check provider health
   health = coordinator.provider_registry.get_provider_health()
   for name, status in health.items():
       if status['status'] == 'unhealthy':
           print(f"Provider {name} is unhealthy: {status}")
   ```

2. **Circuit Breaker Issues**:
   ```python
   # Check circuit breaker states
   lb_metrics = coordinator.load_balancer.get_metrics()
   for name, metrics in lb_metrics.items():
       if isinstance(metrics, dict) and 'circuit_breaker' in metrics:
           cb_status = metrics['circuit_breaker']
           if cb_status and cb_status['state'] == 'OPEN':
               print(f"Circuit breaker OPEN for {name}")
   ```

3. **Cache Performance**:
   ```python
   # Monitor cache performance
   cache_stats = coordinator.cache.get_stats()
   if cache_stats['hit_rate'] < 0.3:
       print("Low cache hit rate - consider adjusting similarity threshold")
   ```

### Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable verbose coordinator logging
coordinator.configure(debug_mode=True)
```

This scalable coordinator system provides enterprise-grade reliability, performance, and security for LLM coordination needs. The modular architecture allows for easy extension and customization while maintaining backward compatibility with existing code. 