"""
Single-cell RNA-seq Domain Expert

This module provides domain expertise for single-cell RNA sequencing analysis,
including interpretation, troubleshooting, and visualization guidance.
"""

from typing import Dict
try:
    from ..core import (
        DomainExpert, DomainPrompt, TechniqueMetadata, 
        ExpertiseLevel, BiologicalContext
    )
    from ..registry import register_expert
except ImportError:
    # Fallback for absolute imports
    from src.mcp.core.prompts.core import (
        DomainExpert, DomainPrompt, TechniqueMetadata, 
        ExpertiseLevel, BiologicalContext
    )
    from src.mcp.core.prompts.registry import register_expert


class scRNASeqDomainExpert(DomainExpert):
    """Domain expert for single-cell RNA-seq analysis"""
    
    def get_metadata(self) -> TechniqueMetadata:
        return TechniqueMetadata(
            name="scrnaseq",
            display_name="Single-cell RNA-seq",
            description="Single-cell RNA sequencing for studying gene expression at cellular resolution",
            category="Transcriptomics",
            subcategory="Single-cell",
            aliases=["scrna", "sc-rna-seq", "single-cell", "10x"],
            related_techniques=["rnaseq", "atacseq", "cite-seq", "spatial-transcriptomics"],
            typical_applications=[
                "Cell type identification",
                "Developmental trajectory analysis", 
                "Disease mechanisms",
                "Drug response",
                "Tissue heterogeneity"
            ],
            required_expertise=ExpertiseLevel.EXPERT,
            version="2.0",
            author="Gliaent Bioinformatics Team"
        )
    
    def get_prompts(self) -> Dict[str, DomainPrompt]:
        """Get all scRNA-seq domain prompts"""
        prompts = {}
        prompts.update(self._get_interpretation_prompts())
        prompts.update(self._get_troubleshooting_prompts())
        prompts.update(self._get_visualization_prompts())
        prompts.update(self._get_comparison_prompts())
        prompts.update(self._get_quality_control_prompts())
        prompts.update(self._get_advanced_analysis_prompts())
        return prompts
    
    def _get_interpretation_prompts(self) -> Dict[str, DomainPrompt]:
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
- Statistical significance threshold: {pvalue_threshold}

Please provide a biological interpretation of these marker genes, including:
1. Potential cell types represented by each cluster based on marker expression
2. Key biological functions or pathways associated with these markers
3. Confidence level in cell type assignments (high/medium/low)
4. Suggested validation experiments or additional markers to check
5. Potential doublets or low-quality clusters to investigate
""",
                parameters=["n_clusters", "avg_markers_per_cluster", "top_marker_genes", 
                          "cluster_with_most_markers", "cluster_with_fewest_markers", "pvalue_threshold"],
                expertise_level=ExpertiseLevel.EXPERT,
                biological_context=BiologicalContext.CELL_TYPE_IDENTIFICATION,
                tags={"markers", "clustering", "cell-types"},
                references=["doi:10.1038/nmeth.4402", "doi:10.1186/s13059-019-1663-x"]
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
- Statistical significance: {pvalue}
- Fold change vs background: {fold_change}

Please explain this gene's expression pattern, including:
1. Biological significance of this expression level and pattern
2. What this tells us about the cells expressing this gene
3. Potential cell types or states associated with this expression
4. Clinical or research relevance of this gene
5. Suggested follow-up genes to examine
6. Potential technical artifacts to consider
""",
                parameters=["gene_name", "expression_level", "pct_expressing", 
                          "top_cluster", "expression_pattern", "pvalue", "fold_change"],
                expertise_level=ExpertiseLevel.EXPERT,
                biological_context=BiologicalContext.GENE_EXPRESSION,
                tags={"gene-expression", "patterns", "significance"},
                references=["doi:10.1038/s41576-018-0073-y"]
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
- Method used: {trajectory_method}

Please interpret this trajectory analysis, including:
1. Biological significance of the identified developmental paths
2. Validation of the starting and ending cell populations
3. Key transition points and their biological meaning
4. Dynamic genes driving the trajectory progression
5. Potential regulatory mechanisms controlling the transitions
6. Suggested experimental validations for the trajectory
7. Alternative trajectory interpretations to consider
""",
                parameters=["n_trajectories", "root_cells", "terminal_cells", 
                          "pseudotime_range", "branch_points", "trajectory_confidence", 
                          "dynamic_genes", "trajectory_method"],
                expertise_level=ExpertiseLevel.EXPERT,
                biological_context=BiologicalContext.TRAJECTORY_ANALYSIS,
                tags={"trajectory", "pseudotime", "development", "dynamics"},
                references=["doi:10.1038/s41587-019-0071-9", "doi:10.1038/nmeth.4150"]
            )
        }
    
    def _get_quality_control_prompts(self) -> Dict[str, DomainPrompt]:
        """Quality control prompts"""
        return {
            "qc_interpretation": DomainPrompt(
                name="qc_interpretation", 
                description="Interpret quality control metrics and filtering decisions",
                template="""
Based on the scRNA-seq quality control analysis:

- Total cells before filtering: {cells_before}
- Total cells after filtering: {cells_after}
- Cells removed: {cells_removed} ({removal_percentage}%)
- Average genes per cell: {avg_genes_per_cell}
- Average UMI per cell: {avg_umi_per_cell}
- Average mitochondrial percentage: {avg_mito_pct}
- Cells with high mitochondrial content: {high_mito_cells}
- Doublet detection rate: {doublet_rate}%

Please provide an interpretation of these QC metrics, including:
1. Assessment of data quality (excellent/good/moderate/poor)
2. Whether the filtering parameters were appropriate
3. Potential biological or technical factors affecting quality
4. Recommendations for downstream analysis parameters
5. Warning signs that might indicate batch effects or technical issues
6. Suggestions for improving data quality in future experiments
""",
                parameters=["cells_before", "cells_after", "cells_removed", "removal_percentage",
                          "avg_genes_per_cell", "avg_umi_per_cell", "avg_mito_pct", 
                          "high_mito_cells", "doublet_rate"],
                expertise_level=ExpertiseLevel.INTERMEDIATE,
                biological_context=BiologicalContext.QUALITY_CONTROL,
                tags={"qc", "filtering", "quality", "metrics"},
                references=["doi:10.1186/s13059-016-0947-7"]
            )
        }
    
    def _get_troubleshooting_prompts(self) -> Dict[str, DomainPrompt]:
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
- Software/version: {software_version}

Please provide troubleshooting guidance, including:
1. Most likely causes of this issue
2. Step-by-step solutions to try (in order of likelihood)
3. Parameter adjustments that might help
4. How to prevent this issue in future analyses
5. Alternative approaches if the standard solution doesn't work
6. When to consider seeking additional expert help
""",
                parameters=["problem_description", "current_step", "error_message",
                          "data_info", "parameters_used", "software_version"],
                expertise_level=ExpertiseLevel.EXPERT,
                biological_context=BiologicalContext.TROUBLESHOOTING,
                tags={"troubleshooting", "errors", "debugging"}
            )
        }
    
    def _get_visualization_prompts(self) -> Dict[str, DomainPrompt]:
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
- UMAP parameters: {umap_params}

Please explain this UMAP plot, including:
1. What UMAP shows and how to interpret the spatial arrangement
2. Quality of clustering based on visual separation
3. Biological significance of the observed patterns
4. What the coloring reveals about cell relationships
5. Any concerning patterns that might indicate technical issues
6. Suggestions for alternative visualizations or parameter adjustments
""",
                parameters=["n_cells", "n_clusters", "separation_quality", 
                          "color_variable", "observed_patterns", "umap_params"],
                expertise_level=ExpertiseLevel.INTERMEDIATE,
                biological_context=BiologicalContext.VISUALIZATION,
                tags={"umap", "visualization", "clustering", "patterns"}
            )
        }
    
    def _get_comparison_prompts(self) -> Dict[str, DomainPrompt]:
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
- Statistical method used: {statistical_method}
- FDR threshold: {fdr_threshold}

Please interpret this comparison, including:
1. Key biological differences between conditions
2. Potential mechanisms driving these differences
3. Clinical or therapeutic implications
4. Suggested validation experiments
5. Additional comparisons that would be informative
6. Confounding factors to consider
""",
                parameters=["condition1_name", "condition1_cells", "condition2_name", "condition2_cells",
                          "de_genes_count", "top_up_condition1", "top_up_condition2", 
                          "pathways_condition1", "pathways_condition2", "statistical_method", "fdr_threshold"],
                expertise_level=ExpertiseLevel.EXPERT,
                biological_context=BiologicalContext.COMPARATIVE_ANALYSIS,
                tags={"comparison", "differential-expression", "conditions"}
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
- Database used: {pathway_database}

Please interpret these pathway results, including:
1. Biological significance of the enriched pathways
2. How these pathways relate to your experimental conditions
3. Potential therapeutic targets identified
4. Connections between different enriched pathways
5. Suggested follow-up analyses or experiments
6. Limitations of the pathway analysis approach used
""",
                parameters=["total_pathways", "enriched_pathways_count", "top_pathway", 
                          "top_pvalue", "pathway_categories", "pathway_genes", "pathway_database"],
                expertise_level=ExpertiseLevel.EXPERT,
                biological_context=BiologicalContext.PATHWAY_ANALYSIS,
                tags={"pathways", "enrichment", "functional-analysis"}
            )
        }
    
    def _get_advanced_analysis_prompts(self) -> Dict[str, DomainPrompt]:
        """Advanced analysis prompts"""
        return {
            "interpret_cell_communication": DomainPrompt(
                name="interpret_cell_communication",
                description="Interpret cell-cell communication analysis results",
                template="""
Cell-cell communication analysis results:

- Total interactions identified: {total_interactions}
- Most active sender cell type: {top_sender}
- Most active receiver cell type: {top_receiver}
- Top signaling pathways: {top_pathways}
- Interaction strength: {interaction_strength}
- Statistical significance: {pvalue}

Please interpret these cell communication results, including:
1. Biological significance of the identified interactions
2. Key signaling pathways driving communication
3. Therapeutic implications of disrupting these interactions
4. Validation experiments to confirm findings
5. How communication patterns relate to tissue function
""",
                parameters=["total_interactions", "top_sender", "top_receiver", 
                          "top_pathways", "interaction_strength", "pvalue"],
                expertise_level=ExpertiseLevel.SPECIALIST,
                biological_context=BiologicalContext.COMPARATIVE_ANALYSIS,
                tags={"cell-communication", "signaling", "interactions"},
                version="2.0"
            )
        }


# Auto-register this expert when module is imported
register_expert(scRNASeqDomainExpert)


if __name__ == "__main__":
    # Test the scRNA-seq expert
    print("Testing scRNA-seq Domain Expert")
    
    expert = scRNASeqDomainExpert()
    metadata = expert.get_metadata()
    
    print(f"Expert: {metadata.display_name}")
    print(f"Category: {metadata.category}")
    print(f"Aliases: {metadata.aliases}")
    
    prompts = expert.get_prompts()
    print(f"Total prompts: {len(prompts)}")
    
    # Test a specific prompt
    marker_prompt = expert.get_prompt_by_name("interpret_markers")
    if marker_prompt:
        print(f"Marker prompt parameters: {marker_prompt.parameters}")
        print(f"Expertise level: {marker_prompt.expertise_level}")
    
    # Validation
    errors = expert.validate_prompts()
    print(f"Validation errors: {len(errors)}")
    if errors:
        for error in errors:
            print(f"  - {error}") 