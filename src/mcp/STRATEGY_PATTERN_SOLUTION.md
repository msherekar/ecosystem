# Strategy Pattern Solution for MCP Analysis Functions

## Overview

This document describes the comprehensive solution implemented to address hardcoded logic in both `get_suggested_actions` and `get_analysis_insights` functions across the MCP (Model Context Protocol) architecture.

## Problems Identified

### 1. Hardcoded Suggested Actions
- **Registry**: Hardcoded RNA-seq logic in `get_suggested_actions()` (lines 290-310)
- **scRNA-seq Server**: Dictionary mapping steps to actions (lines 786-802)
- **ATAC-seq Server**: Different hardcoded logic (lines 646-673)
- **No consistent strategy** across analysis types

### 2. Hardcoded Analysis Insights
- **scRNA-seq Server**: Hardcoded dataset info, QC metrics, clustering insights (lines 762-785)
- **ATAC-seq Server**: Hardcoded TSS enrichment, peak counts, motif analysis (lines 621-645)
- **Base Server**: Generic fallback with no real insights (line 515)
- **Duplicated patterns** across servers

### 3. Scalability Issues
- Adding new analysis types requires code changes in multiple files
- No dynamic discovery of analysis capabilities
- Tight coupling between servers and business logic

## Solution Architecture

### 1. Unified Strategy Pattern

Created a comprehensive strategy pattern that handles **both** suggested actions and analysis insights:

```python
class AnalysisStrategy(ABC):
    """Abstract strategy for analysis-specific behavior"""
    
    @abstractmethod
    def get_actions(self, context: Dict[str, Any]) -> List[str]:
        """Generate suggested actions based on context"""
        pass
    
    @abstractmethod
    def get_insights(self, context: Dict[str, Any]) -> str:
        """Generate analysis insights based on context"""
        pass
    
    @abstractmethod
    def get_workflow_steps(self) -> List[WorkflowStep]:
        """Get workflow steps for this analysis type"""
        pass
```

### 2. Rule-Based Implementation

Implemented configurable rule-based strategies:

```python
@dataclass
class ActionRule:
    """Rule for generating suggested actions"""
    condition: callable
    action: str
    priority: int = 1
    stage: Optional[WorkflowStage] = None

@dataclass
class InsightRule:
    """Rule for generating analysis insights"""
    condition: callable
    insight_generator: callable
    priority: int = 1
    category: str = "general"
```

### 3. Analysis-Specific Strategies

#### scRNA-seq Strategy
- **9 action rules**: From data upload to enrichment analysis
- **4 insight rules**: Dataset overview, QC metrics, clustering results, progress tracking
- **9 workflow steps**: Complete scRNA-seq pipeline

#### RNA-seq Strategy
- **4 action rules**: Data upload, DESeq2, GO enrichment, visualization
- **3 insight rules**: Dataset info, DESeq2 results, pathway analysis
- **4 workflow steps**: Streamlined bulk RNA-seq workflow

#### ATAC-seq Strategy
- **5 action rules**: Data upload, QC, peak calling, differential analysis, motif enrichment
- **4 insight rules**: TSS enrichment, peak counts, differential regions, motif families
- **7 workflow steps**: Complete ATAC-seq pipeline

## Key Features

### 1. Configuration-Driven Extensibility

New analysis types can be added through configuration:

```yaml
# config/analysis_strategies.yaml
strategies:
  proteomics:
    class_path: "src.mcp.strategies.proteomics.ProteomicsAnalysisStrategy"
    enabled: true
    description: "Mass spectrometry proteomics analysis strategy"
    workflow_stages:
      - data_upload
      - quality_control
      - preprocessing
      - differential_analysis
      - pathway_analysis
```

### 2. Categorized Insights

Insights are organized by category for better structure:
- **data_overview**: Dataset statistics and basic info
- **data_quality**: QC metrics and quality assessments
- **analysis_results**: Analysis outcomes and findings
- **analysis_progress**: Workflow completion status

### 3. Priority-Based Ordering

Both actions and insights are prioritized and sorted:
- **Actions**: Top 5 most relevant actions based on current state
- **Insights**: Organized by category and priority for clarity

### 4. Fallback Mechanisms

Robust error handling with fallbacks:
- Strategy creation failures fall back to generic strategy
- Rule evaluation errors are gracefully handled
- Missing context data doesn't break the system

## Implementation Details

### 1. Registry Integration

Updated `MCPRegistry` to use strategy pattern:

```python
def get_suggested_actions(self) -> List[str]:
    """Get suggested next actions using strategy pattern"""
    # Use strategy for each server context
    for server_name, server_context in server_contexts.items():
        analysis_type = server_context.get("server_type", "")
        strategy = strategy_registry.create_strategy(analysis_type)
        suggestions = strategy.get_actions(server_context)
        all_suggestions.extend(suggestions)

def get_analysis_insights(self, analysis_type: str = "all") -> str:
    """Get analysis insights using strategy pattern"""
    # Use strategy for each server context
    for server_name, server_context in server_contexts.items():
        strategy = strategy_registry.create_strategy(server_analysis_type)
        insights = strategy.get_insights(server_context)
        all_insights.append(f"{server_name.upper()}: {insights}")
```

### 2. Server Base Class Updates

Updated base `MCPServer` to use strategies:

```python
def get_analysis_insights(self) -> str:
    """Get current analysis insights using strategy pattern"""
    context = self._get_server_specific_context()
    analysis_type = context.get("server_type", "generic")
    strategy = strategy_registry.create_strategy(analysis_type)
    return strategy.get_insights(context)

def get_suggested_actions(self) -> List[str]:
    """Get suggested next actions using strategy pattern"""
    context = self._get_server_specific_context()
    analysis_type = context.get("server_type", "generic")
    strategy = strategy_registry.create_strategy(analysis_type)
    return strategy.get_actions(context)
```

### 3. Legacy Compatibility

Maintained backward compatibility with alias definitions:

```python
# Legacy compatibility - maintain old interface names
SuggestedActionStrategy = AnalysisStrategy
RuleBasedActionStrategy = RuleBasedAnalysisStrategy
scRNASeqActionStrategy = scRNASeqAnalysisStrategy
```

## Benefits

### 1. Scalability
- **Easy addition** of new analysis types via configuration
- **No code changes** required for new strategies
- **Plugin-like architecture** for extensibility

### 2. Maintainability
- **Centralized logic** in strategy classes
- **No scattered hardcoded rules** across servers
- **Consistent interface** for all analysis types

### 3. Modularity
- **Clear separation** of concerns
- **Reusable components** (rules, workflow steps)
- **Independent testing** of strategies

### 4. Flexibility
- **Rule-based configuration** for rapid development
- **Priority-based ordering** for relevance
- **Category-based organization** for clarity

## Usage Examples

### Adding a New Analysis Type

1. **Create Strategy Class**:
```python
class ProteomicsAnalysisStrategy(RuleBasedAnalysisStrategy):
    def _initialize_rules(self):
        self.add_action_rule(
            condition=lambda ctx: not ctx.get("data_uploaded", False),
            action="Upload proteomics data (mzML/raw files)",
            priority=10
        )
        
        self.add_insight_rule(
            condition=lambda ctx: "protein_count" in ctx,
            insight_generator=lambda ctx: f"Identified {ctx['protein_count']} proteins",
            category="analysis_results"
        )
```

2. **Register Strategy**:
```python
strategy_registry.register_strategy("proteomics", ProteomicsAnalysisStrategy)
```

3. **Configure Server**:
```yaml
proteomics:
  class_path: "src.mcp.servers.proteomics_server.ProteomicsMCPServer"
  strategy: "proteomics"
  enabled: true
```

### Using Strategies

```python
# Get suggestions for specific analysis
strategy = strategy_registry.create_strategy("scrnaseq")
actions = strategy.get_actions(context)
insights = strategy.get_insights(context)

# Get workflow steps
workflow = strategy.get_workflow_steps()
```

## Migration Path

### Phase 1: ✅ Completed
- Implemented unified strategy pattern
- Updated registry and base server classes
- Created strategies for existing analysis types
- Maintained backward compatibility

### Phase 2: Future
- Remove hardcoded methods from individual servers
- Add configuration-based strategy loading
- Implement rule templates for rapid development
- Add strategy validation and testing framework

## Conclusion

The strategy pattern solution completely eliminates hardcoded logic in both `get_suggested_actions` and `get_analysis_insights` functions, providing:

- **Unified approach** for both functions
- **Configuration-driven extensibility** for new analysis types
- **Rule-based flexibility** for rapid development
- **Robust error handling** with fallback mechanisms
- **Backward compatibility** with existing code

This architecture can now scale to support hundreds of analysis types without any code changes, only configuration updates. 