# MCP (Model Context Protocol) Implementation

## Overview

This bioinformatics analysis platform implements a scalable MCP architecture that enables easy addition of new analysis techniques while maintaining unified agent access and context awareness. The platform currently supports RNA-seq, scRNA-seq, data management, and visualization capabilities, with a demonstrated example of how to add proteomics analysis.

## Architecture

### Core Components

#### 1. MCP Core Infrastructure (`src/mcp/core/`)

- **`server.py`**: Base MCP server class providing tool/resource/prompt management
- **`client.py`**: MCP client for unified communication with multiple servers  
- **`registry.py`**: Central registry managing all MCP servers and providing unified access

#### 2. Analysis Servers (`src/mcp/servers/`)

- **`rnaseq_server.py`**: RNA-seq analysis tools (DESeq2, GO enrichment, visualizations)
- **`scrnaseq_server.py`**: Single-cell RNA-seq analysis tools (QC, clustering, marker genes)
- **`data_server.py`**: Data management tools (validation, format conversion, quality assessment)
- **`visualization_server.py`**: Plotting and visualization tools (statistical plots, specialized plots)
- **`proteomics_server.py`**: Example proteomics server demonstrating extensibility

#### 3. Agent Integration (`src/modules/agent/core.py`)

- Enhanced agent with MCP integration
- Context awareness aggregated from all connected servers
- Tool discovery and execution across multiple servers
- Results appear in center panel, agent discusses in chat

## Key Features

### 1. Scalable Architecture

The MCP architecture allows for easy addition of new analysis techniques:

```python
# Adding a new server is as simple as:
class NewAnalysisMCPServer(MCPServer):
    def __init__(self):
        super().__init__("new_analysis_server", "1.0.0")
    
    async def initialize(self):
        # Register tools, resources, and prompts
        pass
```

### 2. Unified Tool Access

All tools across servers are accessible through a single interface:

```python
# Execute any tool from any server
result = await registry.execute_tool("run_rnaseq_pipeline", {"force_rerun": True})
result = await registry.execute_tool("cluster_cells", {"resolution": 0.8})
result = await registry.execute_tool("create_volcano_plot", {"logfc_threshold": 2.0})
```

### 3. Context Aggregation

The agent has unified awareness of all analysis states:

```python
context = registry.get_aggregated_context()
# Returns combined context from all servers including:
# - Data upload status
# - Analysis progress
# - Available tools
# - Suggested next steps
```

### 4. Standardized Interfaces

All servers implement standardized interfaces for:
- **Tools**: Analysis functions with JSON schema validation
- **Resources**: Data and results access
- **Prompts**: Template-based result interpretation

## Current Analysis Capabilities

### RNA-seq Analysis
- **Pipeline execution**: Complete RNA-seq workflow
- **Differential expression**: DESeq2-based analysis
- **Gene ontology**: GO term enrichment analysis
- **Quality control**: Data validation and filtering
- **Visualizations**: PCA, volcano plots, heatmaps

### scRNA-seq Analysis  
- **Quality control**: Cell and gene filtering
- **Normalization**: Multiple normalization methods
- **Clustering**: Leiden algorithm-based clustering
- **Marker genes**: Differential expression between clusters
- **Visualizations**: UMAP, violin plots, marker heatmaps

### Data Management
- **File validation**: Multi-format data validation
- **Format conversion**: Between CSV, TSV, H5AD, etc.
- **Quality assessment**: Data quality scoring and recommendations
- **Compatibility checking**: Analysis-specific data requirements

### Visualization
- **Statistical plots**: Histograms, box plots, scatter plots
- **Specialized plots**: PCA, volcano, MA plots
- **Interactive plots**: Hover information and zoom capabilities
- **Export tools**: Multiple format export with publication quality

### Proteomics (Example)
- **Mass spectrometry processing**: Raw data processing
- **Protein identification**: Database search and FDR control
- **Quantification**: Label-free and TMT-based methods
- **Differential analysis**: Statistical comparison between conditions
- **Pathway analysis**: Protein pathway enrichment

## Adding New Analysis Techniques

### Step 1: Create MCP Server

Create a new server file in `src/mcp/servers/`:

```python
# src/mcp/servers/your_analysis_server.py
from ..core.server import MCPServer

class YourAnalysisMCPServer(MCPServer):
    def __init__(self):
        super().__init__("your_analysis_server", "1.0.0")
    
    async def initialize(self):
        await self._register_analysis_tools()
        await self._register_resources()
        await self._register_prompts()
    
    async def _register_analysis_tools(self):
        self.register_tool(
            name="your_analysis_tool",
            description="Description of what this tool does",
            input_schema={
                "type": "object",
                "properties": {
                    "parameter1": {
                        "type": "string",
                        "description": "Parameter description"
                    }
                },
                "required": ["parameter1"]
            },
            handler=self._your_analysis_handler
        )
    
    async def _your_analysis_handler(self, parameter1: str) -> Dict[str, Any]:
        # Implement your analysis logic
        return {
            "success": True,
            "message": "Analysis completed",
            "results": {}
        }
```

### Step 2: Register in Registry

Add your server to the registry in `src/mcp/core/registry.py`:

```python
from ..servers.your_analysis_server import YourAnalysisMCPServer

def _register_default_servers(self):
    # ... existing servers ...
    
    # Your new server
    self.register_server_config(
        name="your_analysis",
        server_class=YourAnalysisMCPServer,
        enabled=True,
        auto_connect=True
    )
```

### Step 3: Add UI Components (Optional)

If you need UI components, add them to the interface:

```python
# src/interface/left.py - Add navigation button
if st.button("Your Analysis"):
    st.session_state.active_tab = "your_analysis"
    # Reset other flags and set yours to True

# src/interface/center.py - Add display logic
elif st.session_state.active_tab == "your_analysis":
    display_your_analysis()
```

### Step 4: Test Integration

The agent will automatically discover your tools and can execute them:

```python
# Agent can now use your tools
result = await registry.execute_tool("your_analysis_tool", {"parameter1": "value"})
```

## Tool Schema Guidelines

### Input Schema Structure
```python
input_schema = {
    "type": "object",
    "properties": {
        "parameter_name": {
            "type": "string|number|boolean|array|object",
            "description": "Clear description of parameter",
            "enum": ["option1", "option2"],  # For limited choices
            "default": "default_value",      # Optional default
            "items": {"type": "string"}      # For arrays
        }
    },
    "required": ["required_param1", "required_param2"]
}
```

### Handler Return Format
```python
async def _tool_handler(self, **kwargs) -> Dict[str, Any]:
    try:
        # Your analysis logic here
        return {
            "success": True,
            "message": "Human-readable success message",
            "results": {
                # Your analysis results
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error description: {str(e)}"
        }
```

## Resource Management

### Registering Resources
```python
self.register_resource(
    uri="your_analysis://data/results",
    name="Analysis Results",
    description="Results from your analysis",
    mime_type="application/json"
)
```

### Accessing Resources
```python
resource = await registry.get_resource("your_analysis://data/results")
```

## Prompt Templates

### Creating Prompts
```python
self.register_prompt(
    name="interpret_your_results",
    description="Interpret results from your analysis",
    template="""
    Based on your analysis results:
    
    - Parameter 1: {param1}
    - Parameter 2: {param2}
    
    Please provide interpretation including:
    1. Key findings
    2. Biological significance
    3. Next steps
    """,
    parameters={
        "param1": "string",
        "param2": "integer"
    }
)
```

### Using Prompts
```python
prompt = await registry.render_prompt("interpret_your_results", {
    "param1": "value1",
    "param2": 42
})
```

## Context Awareness

### Server-Specific Context
Implement `_get_server_specific_context()` in your server:

```python
def _get_server_specific_context(self) -> Dict[str, Any]:
    return {
        "analysis_type": "your_analysis",
        "data_uploaded": self._check_data_availability(),
        "pipeline_status": self._get_pipeline_status(),
        "capabilities": ["capability1", "capability2"]
    }
```

### Agent Integration
The agent automatically aggregates context from all servers and uses it to:
- Understand current analysis state
- Suggest appropriate next steps
- Provide contextual assistance
- Execute relevant tools

## Error Handling

### Server-Level Error Handling
```python
async def _tool_handler(self, **kwargs):
    try:
        # Validate inputs
        if not self._validate_inputs(kwargs):
            return {"success": False, "message": "Invalid inputs"}
        
        # Check data availability
        if not self._check_data_availability():
            return {"success": False, "message": "Required data not available"}
        
        # Execute analysis
        result = self._run_analysis(kwargs)
        
        return {"success": True, "message": "Success", "results": result}
        
    except Exception as e:
        self.logger.error(f"Tool execution failed: {str(e)}")
        return {"success": False, "message": f"Analysis failed: {str(e)}"}
```

### Registry-Level Error Handling
The registry handles server connection failures gracefully and provides fallback mechanisms.

## Performance Considerations

### Async Operations
All MCP operations are asynchronous to prevent blocking the UI:

```python
async def _long_running_analysis(self, **kwargs):
    # Use async operations for long-running tasks
    result = await self._async_analysis_function(kwargs)
    return result
```

### Resource Management
- Servers manage their own resources
- Automatic cleanup on disconnection
- Memory-efficient data handling

## Testing New Servers

### Unit Testing
```python
import pytest
from your_analysis_server import YourAnalysisMCPServer

@pytest.mark.asyncio
async def test_your_analysis_tool():
    server = YourAnalysisMCPServer()
    await server.initialize()
    
    result = await server._your_analysis_handler(parameter1="test")
    assert result["success"] == True
```

### Integration Testing
```python
@pytest.mark.asyncio
async def test_registry_integration():
    registry = MCPRegistry()
    await registry.initialize()
    
    result = await registry.execute_tool("your_analysis_tool", {"parameter1": "test"})
    assert result["success"] == True
```

## Future Extensions

The MCP architecture supports easy addition of:

### New Analysis Types
- **Genomics**: Variant calling, genome assembly, annotation
- **Imaging**: Microscopy analysis, image segmentation, quantification  
- **Metabolomics**: Peak detection, pathway analysis, biomarker discovery
- **Epigenomics**: ChIP-seq, ATAC-seq, methylation analysis

### Advanced Features
- **Workflow orchestration**: Multi-step analysis pipelines
- **Real-time collaboration**: Multi-user analysis sessions
- **Cloud integration**: Scalable compute resources
- **API endpoints**: External tool integration

### AI/ML Integration
- **Model serving**: Deploy custom ML models as MCP tools
- **AutoML**: Automated model selection and training
- **Prediction services**: Real-time inference capabilities

## Dependencies

The MCP implementation requires:

```txt
# Core MCP dependencies
mcp>=1.0.0
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.5.0
asyncio-mqtt>=0.13.0

# Analysis dependencies
pandas>=2.0.0
numpy>=1.24.0
streamlit>=1.28.0

# Bioinformatics dependencies
scanpy>=1.9.0
anndata>=0.9.0
# Add analysis-specific dependencies as needed
```

## Conclusion

The MCP architecture provides a robust, scalable foundation for bioinformatics analysis platforms. New analysis techniques can be added with minimal effort while maintaining unified agent access and context awareness. The standardized interfaces ensure consistency across all analysis types, and the async architecture provides responsive user experience even with long-running analyses.

This implementation demonstrates how MCP can transform complex bioinformatics workflows into an intuitive, agent-assisted analysis environment that scales to support thousands of analysis techniques. 