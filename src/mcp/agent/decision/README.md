# Scalable Provider Selection System

A comprehensive, enterprise-grade provider selection engine with plugin architecture, advanced analytics, and intelligent decision-making capabilities.

## 🚀 Features

### Core Capabilities
- **Plugin-Based Architecture**: Modular selection strategies with easy extensibility
- **AI-Powered Message Analysis**: NLP-based query complexity and category classification
- **Load Balancing**: Circuit breakers, health monitoring, and intelligent traffic distribution
- **Configuration-Driven Rules**: YAML-based rule engine for dynamic provider selection
- **Comprehensive Metrics**: Real-time analytics, Prometheus integration, and performance monitoring
- **Security Controls**: Multi-level security validation and rate limiting
- **Electron UI Integration**: Seamless integration with desktop applications
- **A/B Testing**: Built-in experimentation framework for optimization

### Scalability Features
- **Async Processing**: Non-blocking operations for high throughput
- **Caching**: Intelligent caching with TTL for improved performance
- **Circuit Breakers**: Automatic failover and fault tolerance
- **Resource Management**: Memory-efficient data structures and cleanup
- **Multi-tenant Support**: User and session isolation
- **Horizontal Scaling**: Stateless design for distributed deployment

## 📁 File Structure

```
src/mcp/agent/decision/
├── provider_selector.py      # Main scalable provider selector
├── selection_strategies.py   # Plugin-based selection strategies
├── message_analyzer.py      # AI-powered message analysis
├── load_balancer.py         # Load balancing with circuit breakers
├── rule_engine.py           # Configuration-driven rule engine
├── metrics_collector.py     # Comprehensive metrics collection
├── selection_rules.yaml     # Example rule configuration
└── README.md               # This documentation
```

## 🛠 Quick Start

### Basic Usage

```python
from src.mcp.agent.decision.provider_selector import (
    ScalableProviderSelector, 
    SelectionContext, 
    SelectionCriteria,
    SelectionStrategy
)

# Initialize the selector
selector = ScalableProviderSelector(config_path="selection_rules.yaml")

# Configure selection criteria
criteria = SelectionCriteria(
    cost_weight=0.4,
    quality_weight=0.3,
    latency_weight=0.2,
    availability_weight=0.1,
    security_level="high"
)

# Set strategy
selector.configure_strategy(SelectionStrategy.HYBRID_INTELLIGENT, criteria)

# Create selection context
context = SelectionContext(
    user_message="Analyze my RNA-seq differential expression results",
    user_id="researcher_001",
    session_id="analysis_session_123",
    usage_stats={"external_calls": 5, "local_calls": 12},
    cost_budget=0.50,
    security_context={"level": "high", "user_role": "researcher"},
    electron_context={"window_id": "main", "tab_id": "analysis"}
)

# Mock providers (replace with actual provider instances)
providers = {
    "external": ExternalProvider(),
    "local": LocalProvider()
}

# Select provider
selected_provider = await selector.select_provider(context, providers, criteria)
print(f"Selected provider: {selected_provider}")

# Get selection statistics
stats = selector.get_selection_stats()
print(f"Total selections: {stats['total_selections']}")
```

### Configuration-Based Selection

```yaml
# selection_rules.yaml
selection_rules:
  - name: "cost_optimization"
    condition: "cost_budget < 0.10"
    action: "'local'"
    priority: 85
    enabled: true
    
  - name: "complex_bioinformatics"
    condition: "contains(message, 'differential expression')"
    action: "'external'"
    priority: 65
    enabled: true
```

## 🧩 Components

### 1. ScalableProviderSelector

The main orchestrator that coordinates all components:

```python
selector = ScalableProviderSelector(config_path="rules.yaml")

# Key methods
await selector.select_provider(context, providers, criteria)
selector.configure_strategy(strategy, criteria)
selector.get_selection_stats()
```

**Features:**
- Plugin architecture for strategies
- Security validation
- Fallback handling
- Electron UI integration
- Comprehensive error handling

### 2. Selection Strategies

Modular strategy implementations:

```python
from src.mcp.agent.decision.selection_strategies import (
    SelectionStrategyFactory,
    CostOptimizedStrategy,
    PerformanceOptimizedStrategy
)

factory = SelectionStrategyFactory()
strategy = factory.get_strategy("cost_optimized")
```

**Available Strategies:**
- `local_first`: Always prefer local providers
- `external_first`: Always prefer external providers  
- `cost_optimized`: Optimize for cost efficiency
- `performance_optimized`: Optimize for quality and performance
- `hybrid_intelligent`: Multi-factor intelligent selection

### 3. Message Analyzer

AI-powered message analysis:

```python
from src.mcp.agent.decision.message_analyzer import MessageAnalyzer

analyzer = MessageAnalyzer()
analysis = await analyzer.analyze_message(
    "Interpret my pathway analysis results",
    context={"session_type": "production"}
)

print(f"Complexity: {analysis.complexity.name}")
print(f"Category: {analysis.category.value}")
print(f"Domain specificity: {analysis.domain_specificity}")
```

**Analysis Features:**
- Query complexity assessment (SIMPLE, MODERATE, COMPLEX, EXPERT)
- Category classification (INFORMATIONAL, ANALYTICAL, etc.)
- Domain specificity scoring
- Sentiment analysis
- Urgency detection
- Cost estimation

### 4. Load Balancer

Advanced load balancing with health monitoring:

```python
from src.mcp.agent.decision.load_balancer import LoadBalancer

lb = LoadBalancer(LoadBalancingStrategy.INTELLIGENT)

# Filter healthy providers
healthy = await lb.filter_healthy_providers(providers)

# Select with load balancing
selected = await lb.select_provider_with_load_balancing(healthy)

# Record request results
await lb.record_request_result(provider, request_id, success, response_time)
```

**Load Balancing Strategies:**
- Round Robin
- Least Connections
- Weighted Round Robin
- Response Time-based
- Intelligent (multi-factor)

### 5. Rule Engine

Configuration-driven rule evaluation:

```python
from src.mcp.agent.decision.rule_engine import RuleEngine

engine = RuleEngine("selection_rules.yaml")
result = engine.evaluate_rules(context, providers)
```

**Rule Features:**
- Priority-based evaluation
- Safe expression evaluation
- Dynamic rule management
- Category-based organization
- Runtime rule modification

### 6. Metrics Collector

Comprehensive analytics and monitoring:

```python
from src.mcp.agent.decision.metrics_collector import MetricsCollector

collector = MetricsCollector(enable_prometheus=True)

# Record selections
await collector.record_selection(context, provider, strategy, duration)

# Get aggregated metrics
metrics = collector.get_aggregated_metrics()

# Export for monitoring
prometheus_data = collector.export_metrics('prometheus')
```

**Metrics Features:**
- Real-time collection
- Prometheus integration
- Historical analysis
- User behavior tracking
- Cost analytics
- Performance monitoring

## ⚙️ Configuration

### Selection Rules

Rules are defined in YAML format with the following structure:

```yaml
selection_rules:
  - name: "rule_name"
    description: "Human-readable description"
    category: "rule_category"
    priority: 100  # Higher = evaluated first
    enabled: true
    condition: "python_expression"
    action: "provider_name_or_expression"
```

### Available Context Variables

Rules can access these context variables:

- `message`: User's input message
- `message_length`: Character count
- `word_count`: Word count
- `external_calls`: Number of external calls in session
- `local_calls`: Number of local calls in session
- `cost_budget`: Available budget for request
- `session_type`: Type of session (interactive, production, etc.)
- `security_level`: Security level (low, standard, high, critical)
- `user_role`: User's role (user, researcher, admin)
- `available_providers`: List of available provider names
- `has_external`: Boolean if external provider available
- `has_local`: Boolean if local provider available

### Custom Functions

Built-in functions for rule expressions:

- `contains(text, substring)`: Case-insensitive substring check
- `starts_with(text, prefix)`: Case-insensitive prefix check
- `ends_with(text, suffix)`: Case-insensitive suffix check
- `word_count(text)`: Count words in text
- `get_nested(obj, key, default)`: Safe nested dictionary access

## 🔒 Security Features

### Multi-Level Security

1. **Input Validation**: Sanitization of user inputs
2. **Rate Limiting**: Per-user and per-session limits
3. **Content Filtering**: Detection of potentially dangerous content
4. **Access Controls**: Role-based provider access
5. **Audit Logging**: Comprehensive security event logging

### Security Levels

- **Low**: Basic validation, minimal restrictions
- **Standard**: Standard rate limiting and content filtering
- **High**: Strict limits, enhanced monitoring
- **Critical**: Maximum security, local-only providers

## 📊 Monitoring & Analytics

### Key Metrics

- **Selection Metrics**: Count, success rate, duration
- **Cost Metrics**: Total cost, cost per selection, efficiency
- **Performance Metrics**: Response times, error rates
- **Usage Patterns**: Provider distribution, user behavior
- **Health Metrics**: Circuit breaker states, load levels

### Prometheus Integration

```python
# Enable Prometheus metrics
collector = MetricsCollector(enable_prometheus=True)

# Metrics available:
# - provider_selections_total
# - provider_selection_duration_seconds  
# - provider_selection_success_rate
# - provider_selection_cost_dollars
# - active_users_count
# - provider_health_score
```

### Dashboard Queries

Example Prometheus queries:

```promql
# Selection rate per minute
rate(provider_selections_total[1m])

# Average response time by provider
avg(provider_selection_duration_seconds) by (provider)

# Success rate by strategy
avg(provider_selection_success_rate) by (strategy)

# Cost efficiency
sum(provider_selections_total{success="true"}) / sum(provider_selection_cost_dollars)
```

## 🧪 Testing

### Unit Tests

Each component includes comprehensive unit tests:

```bash
# Test individual components
python -m src.mcp.agent.decision.provider_selector
python -m src.mcp.agent.decision.selection_strategies
python -m src.mcp.agent.decision.message_analyzer
python -m src.mcp.agent.decision.load_balancer
python -m src.mcp.agent.decision.rule_engine
python -m src.mcp.agent.decision.metrics_collector
```

### Integration Testing

```python
# Full system test
from src.mcp.agent.decision.test_integration import run_integration_tests

await run_integration_tests()
```

## 🔧 Customization

### Adding Custom Strategies

```python
from src.mcp.agent.decision.selection_strategies import BaseSelectionStrategy

class CustomStrategy(BaseSelectionStrategy):
    async def select_provider(self, context, providers, criteria, analysis):
        # Custom selection logic
        return "preferred_provider"
    
    def get_strategy_name(self):
        return "custom_strategy"

# Register the strategy
factory.register_strategy("custom", CustomStrategy)
```

### Custom Rule Functions

```python
# Add custom functions to rule engine
engine.custom_functions['my_function'] = lambda x: custom_logic(x)
```

### Custom Metrics

```python
# Add custom metrics collection
collector.record_custom_metric("my_metric", value, labels)
```

## 🚀 Deployment

### Production Configuration

```python
selector = ScalableProviderSelector(
    config_path="/etc/gliaent/selection_rules.yaml"
)

# Configure for production
criteria = SelectionCriteria(
    security_level="high",
    max_cost_per_request=0.50,
    min_quality_score=0.9
)

# Enable monitoring
await collector.start_background_tasks()
```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ /app/src/
COPY config/ /app/config/

WORKDIR /app
CMD ["python", "-m", "src.mcp.agent.decision.provider_selector"]
```

### Kubernetes Configuration

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: provider-selector
spec:
  replicas: 3
  selector:
    matchLabels:
      app: provider-selector
  template:
    spec:
      containers:
      - name: provider-selector
        image: gliaent/provider-selector:latest
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

## 📈 Performance Optimization

### Best Practices

1. **Caching**: Enable aggressive caching for stable workloads
2. **Connection Pooling**: Reuse provider connections
3. **Batch Processing**: Group similar requests
4. **Resource Limits**: Set appropriate memory and CPU limits
5. **Monitoring**: Use comprehensive monitoring for optimization

### Scaling Guidelines

- **Memory**: ~50MB base + 1KB per selection record
- **CPU**: Minimal for rule evaluation, more for NLP analysis
- **Network**: Low bandwidth requirements
- **Storage**: Metrics retention configurable

## 🔗 Integration

### Electron Integration

```javascript
// In Electron main process
const { ipcMain } = require('electron');

ipcMain.handle('select-provider', async (event, context) => {
  const result = await pythonBackend.selectProvider(context);
  return result;
});

// Send notifications to UI
providerSelector.onSelectionMade((selection) => {
  mainWindow.webContents.send('provider-selected', selection);
});
```

### API Integration

```python
from fastapi import FastAPI
from src.mcp.agent.decision.provider_selector import ScalableProviderSelector

app = FastAPI()
selector = ScalableProviderSelector()

@app.post("/select-provider")
async def select_provider(context: SelectionContext):
    result = await selector.select_provider(context, providers)
    return {"provider": result}
```

## 🔧 Troubleshooting

### Common Issues

1. **No Provider Selected**: Check rule conditions and provider availability
2. **High Response Times**: Review load balancing configuration
3. **Circuit Breaker Open**: Check provider health and error rates
4. **Rule Evaluation Errors**: Validate rule expressions syntax
5. **Memory Usage**: Adjust retention settings and cache TTL

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

selector = ScalableProviderSelector()
# Detailed logging will be enabled
```

### Health Checks

```python
# Check system health
health = {
    'provider_health': lb.get_provider_health(),
    'rule_stats': engine.get_rule_stats(),
    'selection_stats': selector.get_selection_stats(),
    'metrics_summary': collector.get_aggregated_metrics()
}
```

## 📚 API Reference

### Core Classes

- `ScalableProviderSelector`: Main orchestrator
- `SelectionContext`: Request context data
- `SelectionCriteria`: Selection configuration
- `MessageAnalysis`: Analysis result data
- `ProviderMetrics`: Provider performance data

### Key Methods

- `select_provider()`: Main selection method
- `configure_strategy()`: Set selection strategy
- `record_selection()`: Record selection event
- `get_aggregated_metrics()`: Get analytics data
- `evaluate_rules()`: Evaluate selection rules

## 🤝 Contributing

1. Follow the modular architecture
2. Add comprehensive tests
3. Update documentation
4. Ensure security compliance
5. Maintain performance standards

## 📄 License

This system is part of the Gliaent project. See the main project license for details.

## 🙋‍♂️ Support

For questions or support:
- Open an issue in the main Gliaent repository
- Check the troubleshooting section above
- Review the comprehensive test examples

---

This scalable provider selection system provides enterprise-grade capabilities while maintaining simplicity and extensibility. The modular design allows for easy customization and scaling to meet diverse requirements. 