"""
Biological Context Data Structures and Ontology Graph

This module contains the core data structures and knowledge graph
for biological context analysis.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Tuple
import networkx as nx


@dataclass
class BiologicalContext:
    """Rich biological context representation."""
    primary_domain: str
    secondary_domains: List[str]
    data_types: List[str]
    experimental_design: str
    analysis_objectives: List[str]
    workflow_stage: str
    complexity_score: float
    tool_recommendations: Dict[str, float]  # tool_name -> confidence
    integration_requirements: Dict[str, Any]
    confidence_metrics: Dict[str, float]
    
    # Temporal context
    session_progression: List[str] = field(default_factory=list)
    estimated_time_remaining: float = 0.0
    
    # User context
    expertise_level: str = "intermediate"
    preferred_tools: List[str] = field(default_factory=list)
    
    # Quality metrics
    data_quality_indicators: Dict[str, float] = field(default_factory=dict)
    statistical_power: float = 0.0


class BiologicalOntologyGraph:
    """Biological knowledge graph for enhanced context understanding."""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.concept_embeddings = {}
        self.relationship_types = {
            'is_a', 'part_of', 'requires', 'produces', 'analyzes',
            'precedes', 'enables', 'quantifies', 'visualizes'
        }
        self._build_ontology()
    
    def _build_ontology(self):
        """Build comprehensive biological analysis ontology."""
        
        # Data types hierarchy
        data_hierarchy = {
            'omics_data': {
                'genomics': ['wgs', 'wes', 'variants', 'structural_variants'],
                'transcriptomics': ['bulk_rnaseq', 'scrna_seq', 'spatial_rnaseq'],
                'proteomics': ['mass_spec', 'western_blot', 'immunoassay'],
                'metabolomics': ['lcms', 'gcms', 'nmr'],
                'epigenomics': ['chip_seq', 'atac_seq', 'bisulfite_seq']
            }
        }
        
        # Analysis types hierarchy
        analysis_hierarchy = {
            'analysis_types': {
                'differential_analysis': ['deseq2', 'edger', 'limma'],
                'clustering': ['hierarchical', 'kmeans', 'leiden', 'louvain'],
                'dimensionality_reduction': ['pca', 'umap', 'tsne', 'diffusion_maps'],
                'pathway_analysis': ['gsea', 'over_representation', 'network_analysis'],
                'machine_learning': ['classification', 'regression', 'deep_learning']
            }
        }
        
        # Tool relationships
        tool_relationships = {
            'seurat': ['scrna_seq', 'clustering', 'dimensionality_reduction'],
            'scanpy': ['scrna_seq', 'trajectory_analysis', 'preprocessing'],
            'deseq2': ['bulk_rnaseq', 'differential_analysis'],
            'gsea': ['pathway_analysis', 'enrichment'],
            'cytoscape': ['network_analysis', 'visualization']
        }
        
        # Build graph
        self._add_hierarchy_to_graph(data_hierarchy)
        self._add_hierarchy_to_graph(analysis_hierarchy)
        self._add_tool_relationships(tool_relationships)
    
    def _add_hierarchy_to_graph(self, hierarchy: Dict, parent: str = None):
        """Add hierarchical relationships to graph."""
        for key, value in hierarchy.items():
            if parent:
                self.graph.add_edge(parent, key, relation='is_a')
            
            if isinstance(value, dict):
                self._add_hierarchy_to_graph(value, key)
            elif isinstance(value, list):
                for item in value:
                    self.graph.add_edge(key, item, relation='has_subtype')
    
    def _add_tool_relationships(self, tool_relationships: Dict[str, List[str]]):
        """Add tool-to-analysis relationships to graph."""
        for tool, analyses in tool_relationships.items():
            for analysis in analyses:
                self.graph.add_edge(tool, analysis, relation='performs')
    
    def get_related_concepts(self, concept: str, max_distance: int = 2) -> List[Tuple[str, float]]:
        """Get concepts related to given concept with similarity scores."""
        related = []
        
        if concept not in self.graph:
            return related
        
        # Use shortest path to find related concepts
        for node in self.graph.nodes():
            if node != concept:
                try:
                    distance = nx.shortest_path_length(self.graph, concept, node)
                    if distance <= max_distance:
                        similarity = 1.0 / (distance + 1)
                        related.append((node, similarity))
                except nx.NetworkXNoPath:
                    continue
        
        return sorted(related, key=lambda x: x[1], reverse=True)
    
    def get_node_neighbors(self, concept: str) -> List[str]:
        """Get direct neighbors of a concept."""
        if concept not in self.graph:
            return []
        return list(self.graph.neighbors(concept))
    
    def get_concept_path(self, source: str, target: str) -> List[str]:
        """Get shortest path between two concepts."""
        try:
            return nx.shortest_path(self.graph, source, target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []


def main():
    """Test function for the biological context module."""
    print("Testing BiologicalContext...")
    
    # Test BiologicalContext creation
    context = BiologicalContext(
        primary_domain="transcriptomics",
        secondary_domains=["genomics"],
        data_types=["scrna_seq"],
        experimental_design="case_control",
        analysis_objectives=["differential_expression"],
        workflow_stage="preprocessing",
        complexity_score=0.7,
        tool_recommendations={"seurat": 0.9, "scanpy": 0.8},
        integration_requirements={},
        confidence_metrics={"domain": 0.95}
    )
    
    print(f"Created context with primary domain: {context.primary_domain}")
    print(f"Tool recommendations: {context.tool_recommendations}")
    
    # Test BiologicalOntologyGraph
    print("\nTesting BiologicalOntologyGraph...")
    ontology = BiologicalOntologyGraph()
    
    print(f"Graph has {ontology.graph.number_of_nodes()} nodes")
    print(f"Graph has {ontology.graph.number_of_edges()} edges")
    
    # Test related concepts
    related = ontology.get_related_concepts("scrna_seq", max_distance=2)
    print(f"Related concepts to 'scrna_seq': {related[:5]}")  # Show first 5
    
    # Test neighbors
    neighbors = ontology.get_node_neighbors("transcriptomics")
    print(f"Neighbors of 'transcriptomics': {neighbors}")


if __name__ == "__main__":
    main() 