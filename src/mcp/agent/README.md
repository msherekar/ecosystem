# Gliaent MCP Agent System

A comprehensive bioinformatics agent system with intelligent routing, coordination, decision-making, and provider management capabilities.

## Overview

The Gliaent MCP Agent provides a sophisticated AI-powered interface for bioinformatics workflows, featuring:

- **Intelligent Tool Routing**: Context-aware tool selection based on biological analysis needs
- **Hybrid Coordination**: Load balancing between local and external LLM providers
- **Decision Engine**: Smart provider selection based on performance, cost, and capabilities
- **Biological Context Analysis**: Domain-specific understanding of bioinformatics workflows
- **Modular Architecture**: Extensible design with pluggable components

## Architecture

The agent system consists of several key components:

### Core Components

- **Agent**: Main conversational AI interface (`core.py`)
- **Brain**: High-level agent orchestration (`brain.py`) 
- **IntelligentToolRouter**: Context-aware tool selection (`intelligent_router.py`)

### Subsystems

- **Coordination**: Hybrid coordination and load balancing (`coordination/`)
- **Decision**: Provider selection and strategy management (`decision/`)
- **Providers**: LLM provider management (`providers/`)
- **Routing**: Biological context analysis and workflow prediction (`routing/`)

## Quick Start

### Installation

```bash
# Set up environment
export OPENROUTER_API_KEY="your-api-key-here"
# or
export OPENAI_API_KEY="your-api-key-here"
```

### Basic Usage

```python
from src.mcp.agent import get_agent, ask_agent

# Get agent instance
agent = get_agent()

# Ask a bioinformatics question
response = await ask_agent("How do I analyze single-cell RNA-seq data?")
print(response['response'])
```

### Interactive CLI

```bash
# Start interactive chat
python -m src.mcp.agent

# Check system status
python -m src.mcp.agent --status

# Run demonstrations
python -m src.mcp.agent --demo

# Run system tests
python -m src.mcp.agent --test
```

## Advanced Usage

### Complete Agent Setup

```python
from src.mcp.agent import create_complete_agent

# Create fully configured agent
config = {
    'coordination': {
        'enable_load_balancing': True,
        'enable_caching': True,
        'cache_size': 1000
    },
    'routing': {
        'enable_biological_context': True,
        'enable_workflow_prediction': True,
        'enable_learning': True
    }
}

agent = await create_complete_agent(config=config)
```

### Bioinformatics Quick Start

```python
from src.mcp.agent import quick_start_bioinformatics_agent

# Pre-configured for bioinformatics workflows
agent = await quick_start_bioinformatics_agent()

# Process bioinformatics queries
response = await agent.process_command("Create a volcano plot for differential expression")
```

### Intelligent Tool Routing

```python
from src.mcp.agent import IntelligentToolRouter

router = IntelligentToolRouter()

# Analyze biological context
context = await router.analyze_biological_context(
    "Analyze scRNA-seq clustering results", 
    session_state={}
)

# Select optimal tools
tool_set = await router.dynamic_tool_selection(context)
print(f"Selected {len(tool_set.tools)} tools with {tool_set.confidence:.2f} confidence")
```

## Bioinformatics Examples

### Single-Cell RNA-seq Analysis

```python
# Interactive workflow guidance
response = await ask_agent("""
I have single-cell RNA-seq data from mouse brain samples. 
I want to identify cell types and find marker genes.
What's the recommended workflow?
""")
```

### Differential Expression Analysis

```python
# RNA-seq analysis pipeline
response = await ask_agent("""
I have RNA-seq data comparing treated vs control samples.
Help me set up a differential expression analysis using DESeq2.
""")
```

### Data Visualization

```python
# Plotting assistance
response = await ask_agent("""
Create a volcano plot showing differential expression results
with genes labeled and significance thresholds marked.
""")
```

## Configuration

### Environment Variables

- `OPENROUTER_API_KEY`: API key for OpenRouter service
- `OPENAI_API_KEY`: Alternative OpenAI API key
- `GLIAENT_LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

### Component Configuration

```python
# Coordination settings
coordination_config = {
    'enable_load_balancing': True,
    'enable_caching': True,
    'cache_size': 1000,
    'fallback_enabled': True
}

# Routing settings
routing_config = {
    'enable_biological_context': True,
    'enable_workflow_prediction': True,
    'enable_learning': True,
    'max_tools': 5
}
```

## API Reference

### Core Functions

- `get_agent()`: Get global agent instance
- `ask_agent(prompt)`: Process a query with enhanced routing
- `enhanced_ask_agent(prompt, history)`: Full-featured query processing
- `get_agent_status()`: Get system status information

### Agent Methods

- `agent.process_command(command)`: Process a single command
- `agent.set_available_tools(tools)`: Set available tools
- `agent.add_to_memory(item)`: Add item to memory
- `agent.get_memory()`: Retrieve memory contents

### Router Methods

- `router.analyze_biological_context(query, session)`: Analyze biological context
- `router.dynamic_tool_selection(context)`: Select optimal tools
- `router.learn_from_usage(tool, context, success, time)`: Learn from tool usage

## Testing

### Run Integration Tests

```bash
# Run basic integration tests
python -m src.mcp.agent.test_agent_integration

# Run with pytest
pytest src/mcp/agent/test_agent_integration.py -v
```

### System Tests

```bash
# Run comprehensive system tests
python -m src.mcp.agent --test

# Run performance benchmarks
python -m src.mcp.agent --benchmark
```

## Troubleshooting

### Common Issues

1. **API Key Not Found**
   - Set `OPENROUTER_API_KEY` or `OPENAI_API_KEY` environment variable
   - Check API key validity and permissions

2. **Tool Selection Issues**
   - Verify MCP registry is initialized
   - Check tool availability in the system

3. **Memory Issues**
   - Reduce cache size in configuration
   - Clear agent memory periodically

4. **Performance Issues**
   - Enable caching in coordination config
   - Use local LLM provider for frequent queries

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable detailed logging
from src.mcp.agent import get_agent
agent = get_agent()
```

## Development

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Run the test suite
5. Submit a pull request

### Architecture Extensions

- **New Providers**: Implement `BaseLLMProvider` interface
- **Custom Routers**: Extend `IntelligentToolRouter` class
- **Analysis Modules**: Add to `routing/` directory
- **Coordination Strategies**: Implement in `coordination/` directory

### Testing New Components

```python
# Test new provider
from src.mcp.agent.providers import BaseLLMProvider

class MyProvider(BaseLLMProvider):
    # Implementation here
    pass

# Test integration
provider = MyProvider()
await provider.initialize()
```

## License

This project is part of the Gliaent bioinformatics platform.

## Support

For issues and questions:
- Check the troubleshooting section
- Run system diagnostics: `python -m src.mcp.agent --status`
- Review logs in the `logs/` directory
- Submit issues through the project repository

## Changelog

### v1.0.0
- Initial release with core agent functionality
- Intelligent tool routing system
- Hybrid coordination architecture
- Bioinformatics context analysis
- CLI interface and testing suite 