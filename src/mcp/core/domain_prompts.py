"""
Domain-Specific Prompt Templates

Centralized repository for biological domain knowledge prompts.
This separates domain expertise from code structure, making it scalable.

Each technique gets its own domain expert class with specialized prompts.
"""

from abc import ABC, abstractmethod
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class DomainPrompt:
    """Domain-specific prompt template"""
    name: str
    description: str
    template: str
    parameters: List[str]
    expertise_level: str  # "basic", "intermediate", "expert"
    biological_context: str


class DomainExpert(ABC):
    """Abstract base class for domain experts"""
    
    @abstractmethod
    def get_technique_name(self) -> str:
        """Get the technique this expert covers"""
        pass
    
    @abstractmethod
    def get_prompts(self) -> Dict[str, DomainPrompt]:
        """Get all domain prompts for this technique"""
        pass
    
    @abstractmethod
    def get_interpretation_prompts(self) -> Dict[str, DomainPrompt]:
        """Get result interpretation prompts"""
        pass
    
    @abstractmethod
    def get_troubleshooting_prompts(self) -> Dict[str, DomainPrompt]:
        """Get troubleshooting prompts"""
        pass


class scRNASeqDomainExpert(DomainExpert):
    """Domain expert for single-cell RNA-seq analysis"""
    
    def get_technique_name(self) -> str:
        return "scRNA-seq"
    
    def get_prompts(self) -> Dict[str, DomainPrompt]:
        """Get all scRNA-seq domain prompts"""
        prompts = {}
        prompts.update(self.get_interpretation_prompts())
        prompts.update(self.get_troubleshooting_prompts())
        prompts.update(self.get_visualization_prompts())
        prompts.update(self.get_comparison_prompts())
        return prompts
    
    def get_interpretation_prompts(self) -> Dict[str, DomainPrompt]:
        """Result interpretation prompts"""
        return {
            "interpret_markers": DomainPrompt(
                name="interpret_markers",
                description="Interpret marker gene results with cell type identification",
                template="""
Based on the scRNA-seq marker gene analysis results:

- Total clusters analyzed: {n_clusters}
- Average markers per cluster: {avg_markers_per_cluster}
- Top marker genes: {top_marker_genes}
- Cluster with most markers: {cluster_with_most_markers}
- Cluster with fewest markers: {cluster_with_fewest_markers}

Please provide a biological interpretation of these marker genes, including:
1. Potential cell types represented by each cluster based on marker expression
2. Key biological functions or pathways associated with these markers
3. Confidence level in cell type assignments
4. Suggested validation experiments or additional markers to check
""",
                parameters=["n_clusters", "avg_markers_per_cluster", "top_marker_genes", 
                          "cluster_with_most_markers", "cluster_with_fewest_markers"],
                expertise_level="expert",
                biological_context="cell_type_identification"
            ),
            
            "qc_interpretation": DomainPrompt(
                name="qc_interpretation", 
                description="Interpret quality control metrics and filtering decisions",
                template="""
Based on the scRNA-seq quality control analysis:

- Total cells before filtering: {cells_before}
- Total cells after filtering: {cells_after}
- Cells removed: {cells_removed} ({removal_percentage}%)
- Average genes per cell: {avg_genes_per_cell}
- Average mitochondrial percentage: {avg_mito_pct}
- Cells with high mitochondrial content: {high_mito_cells}

Please provide an interpretation of these QC metrics, including:
1. Assessment of data quality (good/moderate/poor)
2. Whether the filtering parameters were appropriate
3. Potential biological or technical factors affecting quality
4. Recommendations for downstream analysis parameters
""",
                parameters=["cells_before", "cells_after", "cells_removed", "removal_percentage",
                          "avg_genes_per_cell", "avg_mito_pct", "high_mito_cells"],
                expertise_level="intermediate",
                biological_context="quality_control"
            ),
            
            "interpret_pca_results": DomainPrompt(
                name="interpret_pca_results",
                description="Interpret PCA dimensionality reduction with biological context",
                template="""
Based on the PCA analysis results:

- Variance explained by PC1: {pc1_variance}%
- Variance explained by PC2: {pc2_variance}%
- Total variance in first 10 PCs: {total_variance_10pc}%
- Number of PCs for downstream analysis: {n_pcs_used}
- Main drivers of PC1: {pc1_drivers}
- Main drivers of PC2: {pc2_drivers}

Please interpret these PCA results, including:
1. Whether the variance capture is adequate for downstream analysis
2. Biological interpretation of the main principal components
3. Assessment of batch effects or technical artifacts
4. Recommendations for number of PCs to use in clustering
""",
                parameters=["pc1_variance", "pc2_variance", "total_variance_10pc", 
                          "n_pcs_used", "pc1_drivers", "pc2_drivers"],
                expertise_level="intermediate",
                biological_context="dimensionality_reduction"
            ),
            
            "explain_gene_expression": DomainPrompt(
                name="explain_gene_expression",
                description="Explain gene expression patterns and biological significance",
                template="""
Gene expression analysis for {gene_name}:

- Expression level: {expression_level}
- Percentage of cells expressing: {pct_expressing}%
- Highest expression in cluster: {top_cluster}
- Expression pattern: {expression_pattern}
- Known function: {gene_function}

Please explain this gene's expression pattern, including:
1. Biological significance of this expression level and pattern
2. What this tells us about the cells expressing this gene
3. Potential cell types or states associated with this expression
4. Clinical or research relevance of this gene
5. Suggested follow-up genes to examine
""",
                parameters=["gene_name", "expression_level", "pct_expressing", 
                          "top_cluster", "expression_pattern", "gene_function"],
                expertise_level="expert",
                biological_context="gene_expression"
            ),
            
            "interpret_trajectory_analysis": DomainPrompt(
                name="interpret_trajectory_analysis",
                description="Interpret pseudotime trajectory analysis and developmental paths",
                template="""
Trajectory analysis results for scRNA-seq data:

- Number of trajectories identified: {n_trajectories}
- Starting cell population: {root_cells}
- End cell populations: {terminal_cells}
- Pseudotime range: {pseudotime_range}
- Key branch points: {branch_points}
- Trajectory confidence: {trajectory_confidence}
- Top dynamic genes: {dynamic_genes}

Please interpret this trajectory analysis, including:
1. Biological significance of the identified developmental paths
2. Validation of the starting and ending cell populations
3. Key transition points and their biological meaning
4. Dynamic genes driving the trajectory progression
5. Potential regulatory mechanisms controlling the transitions
6. Suggested experimental validations for the trajectory
""",
                parameters=["n_trajectories", "root_cells", "terminal_cells", 
                          "pseudotime_range", "branch_points", "trajectory_confidence", "dynamic_genes"],
                expertise_level="expert",
                biological_context="trajectory_analysis"
            )
        }
    
    def get_troubleshooting_prompts(self) -> Dict[str, DomainPrompt]:
        """Troubleshooting prompts"""
        return {
            "troubleshoot_analysis": DomainPrompt(
                name="troubleshoot_analysis",
                description="Help troubleshoot common scRNA-seq analysis issues",
                template="""
Analysis issue encountered:

- Problem description: {problem_description}
- Analysis step: {current_step}
- Error message: {error_message}
- Data characteristics: {data_info}
- Parameters used: {parameters_used}

Please provide troubleshooting guidance, including:
1. Likely causes of this issue
2. Step-by-step solutions to try
3. Parameter adjustments that might help
4. How to prevent this issue in future analyses
5. Alternative approaches if the standard solution doesn't work
""",
                parameters=["problem_description", "current_step", "error_message",
                          "data_info", "parameters_used"],
                expertise_level="expert",
                biological_context="troubleshooting"
            )
        }
    
    def get_visualization_prompts(self) -> Dict[str, DomainPrompt]:
        """Visualization interpretation prompts"""
        return {
            "explain_umap_plot": DomainPrompt(
                name="explain_umap_plot",
                description="Explain UMAP visualization patterns and biological significance",
                template="""
Based on the UMAP visualization showing:

- Number of cells plotted: {n_cells}
- Number of clusters visible: {n_clusters}
- Cluster separation quality: {separation_quality}
- Colored by: {color_variable}
- Main patterns observed: {observed_patterns}

Please explain this UMAP plot, including:
1. What UMAP shows and how to interpret the spatial arrangement
2. Quality of clustering based on visual separation
3. Biological significance of the observed patterns
4. What the coloring reveals about cell relationships
5. Any concerning patterns that might indicate technical issues
""",
                parameters=["n_cells", "n_clusters", "separation_quality", 
                          "color_variable", "observed_patterns"],
                expertise_level="intermediate",
                biological_context="visualization"
            )
        }
    
    def get_comparison_prompts(self) -> Dict[str, DomainPrompt]:
        """Comparison and pathway analysis prompts"""
        return {
            "compare_conditions": DomainPrompt(
                name="compare_conditions",
                description="Compare different experimental conditions or cell types",
                template="""
Comparison between conditions:

- Condition 1: {condition1_name} ({condition1_cells} cells)
- Condition 2: {condition2_name} ({condition2_cells} cells)
- Differentially expressed genes: {de_genes_count}
- Top upregulated in condition 1: {top_up_condition1}
- Top upregulated in condition 2: {top_up_condition2}
- Enriched pathways condition 1: {pathways_condition1}
- Enriched pathways condition 2: {pathways_condition2}

Please interpret this comparison, including:
1. Key biological differences between conditions
2. Potential mechanisms driving these differences
3. Clinical or therapeutic implications
4. Suggested validation experiments
5. Additional comparisons that would be informative
""",
                parameters=["condition1_name", "condition1_cells", "condition2_name", "condition2_cells",
                          "de_genes_count", "top_up_condition1", "top_up_condition2", 
                          "pathways_condition1", "pathways_condition2"],
                expertise_level="expert",
                biological_context="comparative_analysis"
            ),
            
            "pathway_analysis_interpretation": DomainPrompt(
                name="pathway_analysis_interpretation",
                description="Interpret pathway enrichment analysis results",
                template="""
Pathway enrichment analysis results:

- Total pathways tested: {total_pathways}
- Significantly enriched pathways: {enriched_pathways_count}
- Top enriched pathway: {top_pathway} (p-value: {top_pvalue})
- Pathway categories represented: {pathway_categories}
- Genes involved: {pathway_genes}

Please interpret these pathway results, including:
1. Biological significance of the enriched pathways
2. How these pathways relate to your experimental conditions
3. Potential therapeutic targets identified
4. Connections between different enriched pathways
5. Suggested follow-up analyses or experiments
""",
                parameters=["total_pathways", "enriched_pathways_count", "top_pathway", 
                          "top_pvalue", "pathway_categories", "pathway_genes"],
                expertise_level="expert",
                biological_context="pathway_analysis"
            )
        }


class RNASeqDomainExpert(DomainExpert):
    """Domain expert for bulk RNA-seq analysis"""
    
    def get_technique_name(self) -> str:
        return "RNA-seq"
    
    def get_prompts(self) -> Dict[str, DomainPrompt]:
        """Get all RNA-seq domain prompts"""
        return {
            "interpret_de_genes": DomainPrompt(
                name="interpret_de_genes",
                description="Interpret differential expression results",
                template="""
Differential expression analysis results:

- Total genes tested: {total_genes}
- Significantly DE genes: {de_genes_count}
- Upregulated genes: {upregulated_count}
- Downregulated genes: {downregulated_count}
- Top upregulated: {top_upregulated}
- Top downregulated: {top_downregulated}

Please interpret these results, including:
1. Biological significance of the expression changes
2. Potential pathways and processes affected
3. Clinical or therapeutic implications
4. Suggested validation experiments
""",
                parameters=["total_genes", "de_genes_count", "upregulated_count", 
                          "downregulated_count", "top_upregulated", "top_downregulated"],
                expertise_level="expert",
                biological_context="differential_expression"
            )
        }
    
    def get_interpretation_prompts(self) -> Dict[str, DomainPrompt]:
        return self.get_prompts()
    
    def get_troubleshooting_prompts(self) -> Dict[str, DomainPrompt]:
        return {}


class ATACSeqDomainExpert(DomainExpert):
    """Domain expert for ATAC-seq analysis"""
    
    def get_technique_name(self) -> str:
        return "ATAC-seq"
    
    def get_prompts(self) -> Dict[str, DomainPrompt]:
        """Get all ATAC-seq domain prompts"""
        return {
            "interpret_peaks": DomainPrompt(
                name="interpret_peaks",
                description="Interpret chromatin accessibility peaks",
                template="""
ATAC-seq peak analysis results:

- Total peaks identified: {total_peaks}
- Peaks in promoters: {promoter_peaks}
- Peaks in enhancers: {enhancer_peaks}
- Peaks in gene bodies: {genebody_peaks}
- Top accessible regions: {top_regions}

Please interpret these accessibility patterns, including:
1. Chromatin landscape overview
2. Regulatory element activity
3. Potential transcription factor binding
4. Biological implications of accessibility changes
""",
                parameters=["total_peaks", "promoter_peaks", "enhancer_peaks", 
                          "genebody_peaks", "top_regions"],
                expertise_level="expert",
                biological_context="chromatin_accessibility"
            )
        }
    
    def get_interpretation_prompts(self) -> Dict[str, DomainPrompt]:
        return self.get_prompts()
    
    def get_troubleshooting_prompts(self) -> Dict[str, DomainPrompt]:
        return {}


# Domain Expert Registry
DOMAIN_EXPERTS = {
    "scrnaseq": scRNASeqDomainExpert(),
    "rnaseq": RNASeqDomainExpert(),
    "atacseq": ATACSeqDomainExpert()
}


def get_domain_expert(technique: str) -> DomainExpert:
    """Get domain expert for a specific technique"""
    if technique not in DOMAIN_EXPERTS:
        raise ValueError(f"No domain expert available for technique: {technique}")
    return DOMAIN_EXPERTS[technique]


def get_domain_prompts(technique: str) -> Dict[str, DomainPrompt]:
    """Get all domain prompts for a technique"""
    expert = get_domain_expert(technique)
    return expert.get_prompts() 