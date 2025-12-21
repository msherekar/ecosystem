"""
Workflow Prediction Engine for Biological Analysis

This module predicts optimal next steps in biological analysis workflows
based on current context and analysis stage.
"""

import networkx as nx
from typing import Dict, List, Any
from .biological_context import BiologicalContext


class WorkflowPredictionEngine:
    """Predicts optimal next steps in biological analysis workflows."""
    
    def __init__(self):
        self.workflow_graphs = self._build_workflow_graphs()
        self.transition_probabilities = self._load_transition_probabilities()
    
    def _build_workflow_graphs(self) -> Dict[str, nx.DiGraph]:
        """Build directed graphs for different analysis workflows."""
        
        workflows = {
            'scrna_seq': self._build_scrna_workflow(),
            'bulk_rnaseq': self._build_bulk_rnaseq_workflow(),
            'proteomics': self._build_proteomics_workflow(),
            'multi_omics': self._build_multi_omics_workflow()
        }
        
        return workflows
    
    def _build_scrna_workflow(self) -> nx.DiGraph:
        """Build scRNA-seq analysis workflow graph."""
        G = nx.DiGraph()
        
        # Define workflow stages and transitions
        stages = [
            'data_loading', 'quality_control', 'filtering', 'normalization',
            'feature_selection', 'dimensionality_reduction', 'clustering',
            'cell_type_annotation', 'differential_expression', 'pathway_analysis',
            'trajectory_analysis', 'visualization', 'interpretation'
        ]
        
        # Add linear flow
        for i in range(len(stages) - 1):
            G.add_edge(stages[i], stages[i + 1], weight=1.0, type='sequential')
        
        # Add optional parallel paths
        G.add_edge('clustering', 'trajectory_analysis', weight=0.7, type='optional')
        G.add_edge('cell_type_annotation', 'visualization', weight=0.8, type='optional')
        
        # Add feedback loops
        G.add_edge('clustering', 'dimensionality_reduction', weight=0.3, type='iterative')
        G.add_edge('differential_expression', 'clustering', weight=0.2, type='refinement')
        
        return G
    
    def _build_bulk_rnaseq_workflow(self) -> nx.DiGraph:
        """Build bulk RNA-seq analysis workflow graph."""
        G = nx.DiGraph()
        
        stages = [
            'data_loading', 'quality_control', 'alignment', 'quantification',
            'normalization', 'differential_expression', 'pathway_analysis',
            'visualization', 'interpretation'
        ]
        
        # Add sequential flow
        for i in range(len(stages) - 1):
            G.add_edge(stages[i], stages[i + 1], weight=1.0, type='sequential')
        
        # Add optional paths
        G.add_edge('differential_expression', 'visualization', weight=0.9, type='optional')
        
        return G
    
    def _build_proteomics_workflow(self) -> nx.DiGraph:
        """Build proteomics analysis workflow graph."""
        G = nx.DiGraph()
        
        stages = [
            'data_loading', 'quality_control', 'normalization', 'imputation',
            'differential_analysis', 'pathway_analysis', 'protein_networks',
            'visualization', 'interpretation'
        ]
        
        for i in range(len(stages) - 1):
            G.add_edge(stages[i], stages[i + 1], weight=1.0, type='sequential')
        
        return G
    
    def _build_multi_omics_workflow(self) -> nx.DiGraph:
        """Build multi-omics integration workflow graph."""
        G = nx.DiGraph()
        
        stages = [
            'data_integration', 'cross_platform_normalization', 'feature_selection',
            'multi_omics_clustering', 'network_analysis', 'pathway_integration',
            'biomarker_discovery', 'visualization', 'interpretation'
        ]
        
        for i in range(len(stages) - 1):
            G.add_edge(stages[i], stages[i + 1], weight=1.0, type='sequential')
        
        return G
    
    def _load_transition_probabilities(self) -> Dict[str, Dict[str, float]]:
        """Load transition probabilities between workflow stages."""
        return {
            'scrna_seq': {
                'data_loading': {'quality_control': 0.95, 'filtering': 0.05},
                'quality_control': {'filtering': 0.8, 'data_loading': 0.2},
                'filtering': {'normalization': 0.9, 'quality_control': 0.1},
                'clustering': {'cell_type_annotation': 0.7, 'trajectory_analysis': 0.3}
            },
            'bulk_rnaseq': {
                'data_loading': {'quality_control': 0.9, 'alignment': 0.1},
                'differential_expression': {'pathway_analysis': 0.8, 'visualization': 0.2}
            }
        }
    
    async def predict_next_steps(
        self, 
        current_context: BiologicalContext,
        session_state: Dict,
        user_preferences: Dict = None
    ) -> List[Dict[str, Any]]:
        """Predict optimal next analysis steps."""
        
        workflow_type = self._determine_workflow_type(current_context)
        workflow_graph = self.workflow_graphs.get(workflow_type)
        
        if not workflow_graph:
            return []
        
        current_stage = current_context.workflow_stage
        
        # Get possible next steps from graph
        if current_stage in workflow_graph:
            next_steps = list(workflow_graph.successors(current_stage))
        else:
            # If current stage not in graph, start from beginning
            next_steps = [node for node in workflow_graph.nodes() 
                         if workflow_graph.in_degree(node) == 0]
        
        # Score and rank next steps
        scored_steps = []
        for step in next_steps:
            score = await self._score_next_step(
                step, current_context, session_state, workflow_graph
            )
            
            step_info = {
                'step': step,
                'confidence': score,
                'estimated_time': self._estimate_step_time(step, current_context),
                'required_tools': self._get_step_tools(step),
                'prerequisites': self._check_prerequisites(step, session_state),
                'difficulty': self._assess_step_difficulty(step, current_context)
            }
            scored_steps.append(step_info)
        
        # Sort by confidence score
        scored_steps.sort(key=lambda x: x['confidence'], reverse=True)
        
        return scored_steps[:5]  # Return top 5 recommendations
    
    def _determine_workflow_type(self, context: BiologicalContext) -> str:
        """Determine workflow type from biological context."""
        primary_domain = context.primary_domain
        data_types = context.data_types
        
        if 'scrna_seq' in data_types:
            return 'scrna_seq'
        elif 'bulk_rnaseq' in data_types:
            return 'bulk_rnaseq'
        elif 'proteomics' in primary_domain:
            return 'proteomics'
        elif len(context.secondary_domains) > 1:
            return 'multi_omics'
        else:
            return 'scrna_seq'  # Default
    
    async def _score_next_step(
        self, 
        step: str, 
        context: BiologicalContext, 
        session_state: Dict,
        workflow_graph: nx.DiGraph
    ) -> float:
        """Score a potential next step."""
        base_score = 0.5
        
        # Check if step follows natural workflow progression
        current_stage = context.workflow_stage
        if workflow_graph.has_edge(current_stage, step):
            edge_data = workflow_graph.get_edge_data(current_stage, step)
            base_score += edge_data.get('weight', 0.5) * 0.3
        
        # Consider user expertise level
        if context.expertise_level == 'beginner' and self._is_advanced_step(step):
            base_score -= 0.2
        elif context.expertise_level == 'expert' and self._is_basic_step(step):
            base_score -= 0.1
        
        # Check data requirements
        if self._has_required_data(step, session_state):
            base_score += 0.2
        else:
            base_score -= 0.3
        
        # Consider tool availability
        required_tools = self._get_step_tools(step)
        available_tools = context.tool_recommendations.keys()
        tool_overlap = len(set(required_tools) & set(available_tools))
        if required_tools:
            base_score += (tool_overlap / len(required_tools)) * 0.2
        
        return max(0.0, min(1.0, base_score))
    
    def _estimate_step_time(self, step: str, context: BiologicalContext) -> int:
        """Estimate time required for a workflow step (in minutes)."""
        time_estimates = {
            'data_loading': 10,
            'quality_control': 15,
            'filtering': 20,
            'normalization': 25,
            'clustering': 30,
            'differential_expression': 45,
            'pathway_analysis': 60,
            'visualization': 20,
            'interpretation': 30
        }
        
        base_time = time_estimates.get(step, 30)
        
        # Adjust for complexity
        complexity_multiplier = {
            'low': 0.7,
            'medium': 1.0,
            'high': 1.5
        }.get(context.complexity_score, 1.0)
        
        return int(base_time * complexity_multiplier)
    
    def _get_step_tools(self, step: str) -> List[str]:
        """Get required tools for a workflow step."""
        step_tools = {
            'quality_control': ['fastqc', 'multiqc'],
            'filtering': ['seurat', 'scanpy'],
            'normalization': ['seurat', 'scanpy', 'deseq2'],
            'clustering': ['seurat', 'scanpy'],
            'differential_expression': ['deseq2', 'limma', 'seurat'],
            'pathway_analysis': ['gsea', 'clusterprofiler'],
            'visualization': ['ggplot2', 'plotly', 'seurat']
        }
        
        return step_tools.get(step, [])
    
    def _check_prerequisites(self, step: str, session_state: Dict) -> List[str]:
        """Check prerequisites for a workflow step."""
        prerequisites = {
            'clustering': ['normalized_data'],
            'differential_expression': ['clustered_data'],
            'pathway_analysis': ['differential_genes'],
            'trajectory_analysis': ['clustered_data']
        }
        
        required = prerequisites.get(step, [])
        missing = []
        
        for req in required:
            if req not in session_state.get('completed_steps', []):
                missing.append(req)
        
        return missing
    
    def _assess_step_difficulty(self, step: str, context: BiologicalContext) -> str:
        """Assess difficulty level of a workflow step."""
        difficulty_levels = {
            'data_loading': 'easy',
            'quality_control': 'easy',
            'filtering': 'medium',
            'normalization': 'medium',
            'clustering': 'medium',
            'differential_expression': 'hard',
            'pathway_analysis': 'hard',
            'trajectory_analysis': 'hard',
            'visualization': 'medium'
        }
        
        return difficulty_levels.get(step, 'medium')
    
    def _is_advanced_step(self, step: str) -> bool:
        """Check if step is considered advanced."""
        advanced_steps = {
            'trajectory_analysis', 'pathway_analysis', 'network_analysis',
            'multi_omics_clustering', 'biomarker_discovery'
        }
        return step in advanced_steps
    
    def _is_basic_step(self, step: str) -> bool:
        """Check if step is considered basic."""
        basic_steps = {
            'data_loading', 'quality_control', 'visualization'
        }
        return step in basic_steps
    
    def _has_required_data(self, step: str, session_state: Dict) -> bool:
        """Check if required data is available for the step."""
        data_requirements = {
            'normalization': 'raw_counts',
            'clustering': 'normalized_data',
            'differential_expression': 'normalized_data',
            'pathway_analysis': 'differential_results'
        }
        
        required_data = data_requirements.get(step)
        if not required_data:
            return True
        
        return required_data in session_state.get('available_data', [])


def main():
    """Test function for the workflow predictor module."""
    print("Testing WorkflowPredictionEngine...")
    
    # Create predictor
    predictor = WorkflowPredictionEngine()
    
    # Test workflow graph creation
    print(f"Available workflows: {list(predictor.workflow_graphs.keys())}")
    
    scrna_workflow = predictor.workflow_graphs['scrna_seq']
    print(f"scRNA-seq workflow nodes: {scrna_workflow.number_of_nodes()}")
    print(f"scRNA-seq workflow edges: {scrna_workflow.number_of_edges()}")
    
    # Test workflow type determination
    from .biological_context import BiologicalContext
    
    test_context = BiologicalContext(
        primary_domain="transcriptomics",
        secondary_domains=[],
        data_types=["scrna_seq"],
        experimental_design="case_control",
        analysis_objectives=["clustering"],
        workflow_stage="quality_control",
        complexity_score=0.6,
        tool_recommendations={"seurat": 0.9},
        integration_requirements={},
        confidence_metrics={"domain": 0.8}
    )
    
    workflow_type = predictor._determine_workflow_type(test_context)
    print(f"Determined workflow type: {workflow_type}")
    
    # Test step tools
    tools = predictor._get_step_tools("clustering")
    print(f"Tools for clustering: {tools}")
    
    # Test difficulty assessment
    difficulty = predictor._assess_step_difficulty("pathway_analysis", test_context)
    print(f"Difficulty of pathway_analysis: {difficulty}")


if __name__ == "__main__":
    main() 