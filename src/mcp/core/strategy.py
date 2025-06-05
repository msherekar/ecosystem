"""
MCP Strategy Patterns

Implements strategy patterns for scalable and configurable behavior
across different analysis types and workflow stages.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import streamlit as st


class WorkflowStage(Enum):
    """Standard workflow stages across analysis types"""
    DATA_UPLOAD = "data_upload"
    QUALITY_CONTROL = "quality_control"
    PREPROCESSING = "preprocessing"
    ANALYSIS = "analysis"
    VISUALIZATION = "visualization"
    INTERPRETATION = "interpretation"
    EXPORT = "export"


@dataclass
class ActionRule:
    """Rule for generating suggested actions"""
    condition: callable  # Function that returns bool
    action: str
    priority: int = 1
    stage: Optional[WorkflowStage] = None


@dataclass
class InsightRule:
    """Rule for generating analysis insights"""
    condition: callable  # Function that returns bool
    insight_generator: callable  # Function that returns insight string
    priority: int = 1
    category: str = "general"  # e.g., "data_quality", "analysis_progress", "results"


@dataclass
class WorkflowStep:
    """Configuration for a workflow step"""
    key: str
    title: str
    description: str
    stage: WorkflowStage
    dependencies: List[str] = None
    optional: bool = False


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


class RuleBasedAnalysisStrategy(AnalysisStrategy):
    """Rule-based strategy for suggested actions and insights"""
    
    def __init__(self, analysis_type: str):
        self.analysis_type = analysis_type
        self.action_rules: List[ActionRule] = []
        self.insight_rules: List[InsightRule] = []
        self.workflow_steps: List[WorkflowStep] = []
        self._initialize_rules()
    
    def add_action_rule(self, condition: callable, action: str, priority: int = 1, 
                       stage: Optional[WorkflowStage] = None):
        """Add a rule for action generation"""
        self.action_rules.append(ActionRule(condition, action, priority, stage))
    
    def add_insight_rule(self, condition: callable, insight_generator: callable, 
                        priority: int = 1, category: str = "general"):
        """Add a rule for insight generation"""
        self.insight_rules.append(InsightRule(condition, insight_generator, priority, category))
    
    def add_workflow_step(self, step: WorkflowStep):
        """Add a workflow step"""
        self.workflow_steps.append(step)
    
    def get_actions(self, context: Dict[str, Any]) -> List[str]:
        """Generate actions based on rules"""
        applicable_rules = []
        
        for rule in self.action_rules:
            try:
                if rule.condition(context):
                    applicable_rules.append(rule)
            except Exception:
                # Skip rules that fail evaluation
                continue
        
        # Sort by priority and return actions
        applicable_rules.sort(key=lambda r: r.priority, reverse=True)
        return [rule.action for rule in applicable_rules[:5]]  # Top 5 actions
    
    def get_insights(self, context: Dict[str, Any]) -> str:
        """Generate insights based on rules"""
        applicable_insights = []
        
        for rule in self.insight_rules:
            try:
                if rule.condition(context):
                    insight = rule.insight_generator(context)
                    if insight:  # Only add non-empty insights
                        applicable_insights.append((insight, rule.priority, rule.category))
            except Exception:
                # Skip rules that fail evaluation
                continue
        
        if not applicable_insights:
            return f"No {self.analysis_type} analysis insights available"
        
        # Sort by priority and category
        applicable_insights.sort(key=lambda x: (x[2], -x[1]))  # Category first, then priority desc
        
        # Group by category and format
        insights_by_category = {}
        for insight, priority, category in applicable_insights:
            if category not in insights_by_category:
                insights_by_category[category] = []
            insights_by_category[category].append(insight)
        
        # Format insights
        formatted_insights = []
        for category, insights in insights_by_category.items():
            if category != "general":
                formatted_insights.extend(insights)
            else:
                formatted_insights.extend(insights)
        
        return "; ".join(formatted_insights)
    
    def get_workflow_steps(self) -> List[WorkflowStep]:
        """Get workflow steps"""
        return self.workflow_steps
    
    @abstractmethod
    def _initialize_rules(self):
        """Initialize rules for this analysis type"""
        pass


class scRNASeqAnalysisStrategy(RuleBasedAnalysisStrategy):
    """Strategy for scRNA-seq suggested actions and insights"""
    
    def __init__(self):
        super().__init__("scrnaseq")
    
    def _initialize_rules(self):
        """Initialize scRNA-seq specific rules"""
        
        # === ACTION RULES ===
        
        # Data upload rules
        self.add_action_rule(
            condition=lambda ctx: not ctx.get("data_uploaded", False),
            action="Upload scRNA-seq data (.h5ad or 10x format)",
            priority=10,
            stage=WorkflowStage.DATA_UPLOAD
        )
        
        # QC rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("data_uploaded", False) and 
                                 not ctx.get("pipeline_status", {}).get("qc", False)),
            action="Perform quality control analysis",
            priority=9,
            stage=WorkflowStage.QUALITY_CONTROL
        )
        
        # Filtering rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("pipeline_status", {}).get("qc", False) and
                                 not ctx.get("pipeline_status", {}).get("filtering", False)),
            action="Filter low-quality cells and genes",
            priority=8,
            stage=WorkflowStage.PREPROCESSING
        )
        
        # Normalization rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("pipeline_status", {}).get("filtering", False) and
                                 not ctx.get("pipeline_status", {}).get("normalization", False)),
            action="Normalize and scale expression data",
            priority=7,
            stage=WorkflowStage.PREPROCESSING
        )
        
        # Dimensionality reduction rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("pipeline_status", {}).get("normalization", False) and
                                 not ctx.get("pipeline_status", {}).get("dimred", False)),
            action="Perform dimensionality reduction (PCA/UMAP)",
            priority=6,
            stage=WorkflowStage.ANALYSIS
        )
        
        # Clustering rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("pipeline_status", {}).get("dimred", False) and
                                 not ctx.get("pipeline_status", {}).get("clustering", False)),
            action="Cluster cells to identify populations",
            priority=5,
            stage=WorkflowStage.ANALYSIS
        )
        
        # Differential expression rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("pipeline_status", {}).get("clustering", False) and
                                 not ctx.get("pipeline_status", {}).get("dea", False)),
            action="Find marker genes for each cluster",
            priority=4,
            stage=WorkflowStage.ANALYSIS
        )
        
        # Visualization rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("pipeline_status", {}).get("clustering", False) and
                                 not ctx.get("pipeline_status", {}).get("viz", False)),
            action="Create visualizations (UMAP, heatmaps)",
            priority=4,
            stage=WorkflowStage.VISUALIZATION
        )
        
        # Enrichment rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("pipeline_status", {}).get("dea", False) and
                                 not ctx.get("pipeline_status", {}).get("enrichment", False)),
            action="Perform pathway enrichment analysis",
            priority=3,
            stage=WorkflowStage.INTERPRETATION
        )
        
        # === INSIGHT RULES ===
        
        # Dataset overview insights
        self.add_insight_rule(
            condition=lambda ctx: ctx.get("data_uploaded", False) and "data_summary" in ctx,
            insight_generator=lambda ctx: f"Dataset: {ctx['data_summary'].get('n_cells', 0):,} cells × {ctx['data_summary'].get('n_genes', 0):,} genes",
            priority=10,
            category="data_overview"
        )
        
        # QC insights
        self.add_insight_rule(
            condition=lambda ctx: "anndata" in st.session_state and hasattr(st.session_state.anndata, 'obs') and "pct_counts_mt" in st.session_state.anndata.obs,
            insight_generator=lambda ctx: f"Median mitochondrial content: {st.session_state.anndata.obs['pct_counts_mt'].median():.1f}%",
            priority=9,
            category="data_quality"
        )
        
        # Clustering insights
        self.add_insight_rule(
            condition=lambda ctx: "anndata" in st.session_state and hasattr(st.session_state.anndata, 'obs') and "leiden" in st.session_state.anndata.obs,
            insight_generator=lambda ctx: f"Identified {len(st.session_state.anndata.obs['leiden'].unique())} cell clusters",
            priority=8,
            category="analysis_results"
        )
        
        # Progress insights
        self.add_insight_rule(
            condition=lambda ctx: ctx.get("pipeline_status", {}),
            insight_generator=lambda ctx: self._generate_progress_insight(ctx),
            priority=7,
            category="analysis_progress"
        )
        
        # Define workflow steps
        self.workflow_steps = [
            WorkflowStep("data_upload", "Data Upload", "Upload scRNA-seq data", WorkflowStage.DATA_UPLOAD),
            WorkflowStep("qc", "Quality Control", "Assess data quality", WorkflowStage.QUALITY_CONTROL, ["data_upload"]),
            WorkflowStep("filtering", "Filtering", "Filter cells and genes", WorkflowStage.PREPROCESSING, ["qc"]),
            WorkflowStep("normalization", "Normalization", "Normalize expression", WorkflowStage.PREPROCESSING, ["filtering"]),
            WorkflowStep("dimred", "Dimensionality Reduction", "PCA and UMAP", WorkflowStage.ANALYSIS, ["normalization"]),
            WorkflowStep("clustering", "Clustering", "Identify cell populations", WorkflowStage.ANALYSIS, ["dimred"]),
            WorkflowStep("dea", "Differential Expression", "Find marker genes", WorkflowStage.ANALYSIS, ["clustering"]),
            WorkflowStep("viz", "Visualization", "Create plots", WorkflowStage.VISUALIZATION, ["clustering"]),
            WorkflowStep("enrichment", "Enrichment", "Pathway analysis", WorkflowStage.INTERPRETATION, ["dea"])
        ]
    
    def _generate_progress_insight(self, context: Dict[str, Any]) -> str:
        """Generate progress insight based on completed steps"""
        pipeline_status = context.get("pipeline_status", {})
        completed_steps = [step for step, done in pipeline_status.items() if done]
        
        if not completed_steps:
            return "Analysis not started"
        elif len(completed_steps) < 3:
            return f"Early stage: {len(completed_steps)} steps completed"
        elif len(completed_steps) < 6:
            return f"Mid-stage analysis: {len(completed_steps)} steps completed"
        else:
            return f"Advanced analysis: {len(completed_steps)} steps completed"


class RNASeqAnalysisStrategy(RuleBasedAnalysisStrategy):
    """Strategy for RNA-seq suggested actions and insights"""
    
    def __init__(self):
        super().__init__("rnaseq")
    
    def _initialize_rules(self):
        """Initialize RNA-seq specific rules"""
        
        # === ACTION RULES ===
        
        # Data upload rules
        self.add_action_rule(
            condition=lambda ctx: not ctx.get("data_uploaded", False),
            action="Upload RNA-seq counts and metadata files",
            priority=10,
            stage=WorkflowStage.DATA_UPLOAD
        )
        
        # DESeq2 rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("data_uploaded", False) and
                                 not ctx.get("pipeline_status", {}).get("deseq2_completed", False)),
            action="Run differential expression analysis (DESeq2)",
            priority=9,
            stage=WorkflowStage.ANALYSIS
        )
        
        # GO enrichment rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("pipeline_status", {}).get("deseq2_completed", False) and
                                 not ctx.get("pipeline_status", {}).get("go_enrichment_completed", False)),
            action="Perform Gene Ontology enrichment analysis",
            priority=8,
            stage=WorkflowStage.INTERPRETATION
        )
        
        # Visualization rules
        self.add_action_rule(
            condition=lambda ctx: ctx.get("pipeline_status", {}).get("deseq2_completed", False),
            action="Create visualizations (PCA, volcano plot, heatmap)",
            priority=7,
            stage=WorkflowStage.VISUALIZATION
        )
        
        # === INSIGHT RULES ===
        
        # Dataset insights
        self.add_insight_rule(
            condition=lambda ctx: "rnaseq_counts_df" in st.session_state and st.session_state.rnaseq_counts_df is not None,
            insight_generator=lambda ctx: f"RNA-seq dataset: {st.session_state.rnaseq_counts_df.shape[1]} samples × {st.session_state.rnaseq_counts_df.shape[0]} genes",
            priority=10,
            category="data_overview"
        )
        
        # DESeq2 results insights
        self.add_insight_rule(
            condition=lambda ctx: "deseq_results" in st.session_state and st.session_state.deseq_results is not None,
            insight_generator=lambda ctx: self._generate_deseq_insight(),
            priority=9,
            category="analysis_results"
        )
        
        # GO enrichment insights
        self.add_insight_rule(
            condition=lambda ctx: "go_results" in st.session_state and st.session_state.go_results is not None,
            insight_generator=lambda ctx: f"GO enrichment: {len(st.session_state.go_results)} significant pathways",
            priority=8,
            category="analysis_results"
        )
        
        # Define workflow steps
        self.workflow_steps = [
            WorkflowStep("data_upload", "Data Upload", "Upload counts and metadata", WorkflowStage.DATA_UPLOAD),
            WorkflowStep("deseq2", "Differential Expression", "DESeq2 analysis", WorkflowStage.ANALYSIS, ["data_upload"]),
            WorkflowStep("go_enrichment", "GO Enrichment", "Pathway analysis", WorkflowStage.INTERPRETATION, ["deseq2"]),
            WorkflowStep("visualization", "Visualization", "Create plots", WorkflowStage.VISUALIZATION, ["deseq2"])
        ]
    
    def _generate_deseq_insight(self) -> str:
        """Generate DESeq2 results insight"""
        deseq_results = st.session_state.deseq_results
        if hasattr(deseq_results, 'shape'):
            significant = deseq_results[deseq_results['padj'] < 0.05] if 'padj' in deseq_results.columns else deseq_results
            return f"DESeq2: {len(significant)} significant genes (padj < 0.05)"
        return "DESeq2 analysis completed"


class ATACSeqAnalysisStrategy(RuleBasedAnalysisStrategy):
    """Strategy for ATAC-seq suggested actions and insights"""
    
    def __init__(self):
        super().__init__("atacseq")
    
    def _initialize_rules(self):
        """Initialize ATAC-seq specific rules"""
        
        # === ACTION RULES ===
        
        # Data upload rules
        self.add_action_rule(
            condition=lambda ctx: not ctx.get("data_uploaded", False),
            action="Upload ATAC-seq peak data or fragment files",
            priority=10,
            stage=WorkflowStage.DATA_UPLOAD
        )
        
        # QC rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("data_uploaded", False) and
                                 not st.session_state.get("qc_metrics_calculated", False)),
            action="Calculate QC metrics (TSS enrichment, nucleosome signal)",
            priority=9,
            stage=WorkflowStage.QUALITY_CONTROL
        )
        
        # Peak calling rules
        self.add_action_rule(
            condition=lambda ctx: (ctx.get("data_uploaded", False) and
                                 not st.session_state.get("peaks_called", False)),
            action="Call accessible chromatin peaks",
            priority=8,
            stage=WorkflowStage.ANALYSIS
        )
        
        # Differential accessibility rules
        self.add_action_rule(
            condition=lambda ctx: (st.session_state.get("peaks_called", False) and
                                 "differential_peaks" not in st.session_state),
            action="Perform differential accessibility analysis",
            priority=7,
            stage=WorkflowStage.ANALYSIS
        )
        
        # Motif enrichment rules
        self.add_action_rule(
            condition=lambda ctx: ("differential_peaks" in st.session_state and
                                 "motif_enrichment_results" not in st.session_state),
            action="Run motif enrichment analysis",
            priority=6,
            stage=WorkflowStage.INTERPRETATION
        )
        
        # === INSIGHT RULES ===
        
        # TSS enrichment insights
        self.add_insight_rule(
            condition=lambda ctx: "tss_enrichment_scores" in st.session_state,
            insight_generator=lambda ctx: self._generate_tss_insight(),
            priority=10,
            category="data_quality"
        )
        
        # Peak insights
        self.add_insight_rule(
            condition=lambda ctx: "atacseq_peaks_df" in st.session_state,
            insight_generator=lambda ctx: f"Identified {len(st.session_state.atacseq_peaks_df):,} accessible chromatin regions",
            priority=9,
            category="analysis_results"
        )
        
        # Differential accessibility insights
        self.add_insight_rule(
            condition=lambda ctx: "differential_peaks" in st.session_state,
            insight_generator=lambda ctx: f"Found {len(st.session_state.differential_peaks):,} differentially accessible regions",
            priority=8,
            category="analysis_results"
        )
        
        # Motif enrichment insights
        self.add_insight_rule(
            condition=lambda ctx: "motif_enrichment_results" in st.session_state,
            insight_generator=lambda ctx: self._generate_motif_insight(),
            priority=7,
            category="analysis_results"
        )
    
    def _generate_tss_insight(self) -> str:
        """Generate TSS enrichment insight"""
        tss_score = st.session_state.tss_enrichment_scores
        if tss_score > 7:
            return f"Good data quality with TSS enrichment of {tss_score:.1f}"
        else:
            return f"Poor data quality - TSS enrichment only {tss_score:.1f} (should be >7)"
    
    def _generate_motif_insight(self) -> str:
        """Generate motif enrichment insight"""
        motif_df = st.session_state.motif_enrichment_results
        if hasattr(motif_df, 'groupby') and 'tf_family' in motif_df.columns:
            top_family = motif_df.groupby('tf_family').size().idxmax()
            return f"Most enriched TF family: {top_family}"
        return "Motif enrichment analysis completed"


class StrategyFactory:
    """Factory for creating analysis strategies"""
    
    _strategies = {
        "scrnaseq": scRNASeqAnalysisStrategy,
        "rnaseq": RNASeqAnalysisStrategy,
        "atacseq": ATACSeqAnalysisStrategy
    }
    
    @classmethod
    def create_strategy(cls, analysis_type: str) -> AnalysisStrategy:
        """Create strategy for analysis type"""
        strategy_class = cls._strategies.get(analysis_type)
        if strategy_class:
            return strategy_class()
        
        # Return generic strategy for unknown types
        return GenericAnalysisStrategy(analysis_type)
    
    @classmethod
    def register_strategy(cls, analysis_type: str, strategy_class: type):
        """Register new strategy"""
        cls._strategies[analysis_type] = strategy_class
    
    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """Get list of available strategies"""
        return list(cls._strategies.keys())


class GenericAnalysisStrategy(RuleBasedAnalysisStrategy):
    """Generic strategy for unknown analysis types"""
    
    def _initialize_rules(self):
        """Initialize generic rules"""
        # Action rules
        self.add_action_rule(
            condition=lambda ctx: not ctx.get("data_uploaded", False),
            action="Upload data files for analysis",
            priority=10
        )
        
        self.add_action_rule(
            condition=lambda ctx: ctx.get("data_uploaded", False),
            action="Begin analysis workflow",
            priority=5
        )
        
        # Insight rules
        self.add_insight_rule(
            condition=lambda ctx: ctx.get("data_uploaded", False),
            insight_generator=lambda ctx: "Data uploaded and ready for analysis",
            priority=5,
            category="general"
        )


# Global strategy registry
strategy_registry = StrategyFactory()


# Legacy compatibility - maintain old interface names
SuggestedActionStrategy = AnalysisStrategy
RuleBasedActionStrategy = RuleBasedAnalysisStrategy
scRNASeqActionStrategy = scRNASeqAnalysisStrategy
RNASeqActionStrategy = RNASeqAnalysisStrategy
ATACSeqActionStrategy = ATACSeqAnalysisStrategy
GenericActionStrategy = GenericAnalysisStrategy


# Test code to verify the module works independently
if __name__ == "__main__":
    def test_strategy_registry():
        """Test StrategyFactory functionality"""
        print("Testing StrategyFactory...")
        
        # Test available strategies
        available = strategy_registry.get_available_strategies()
        print(f"✅ Available strategies: {available}")
        
        # Test strategy creation for each type
        for strategy_type in available:
            strategy = strategy_registry.create_strategy(strategy_type)
            print(f"✅ Created {strategy_type} strategy: {strategy.__class__.__name__}")
            
            # Test empty context
            empty_context = {}
            actions = strategy.get_actions(empty_context)
            insights = strategy.get_insights(empty_context)
            workflow_steps = strategy.get_workflow_steps()
            
            print(f"   - Actions: {len(actions)}")
            print(f"   - Insights: {len(insights)} chars")
            print(f"   - Workflow steps: {len(workflow_steps)}")
        
        # Test generic strategy for unknown type
        generic = strategy_registry.create_strategy("unknown_type")
        print(f"✅ Generic strategy: {generic.__class__.__name__}")
        
        # Test workflow stages enum
        stages = list(WorkflowStage)
        print(f"✅ Workflow stages: {len(stages)}")
        
        print("🎉 All Strategy tests passed!")
    
    # Run test
    test_strategy_registry() 
    # python -m src.mcp.core.strategy