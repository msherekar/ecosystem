"""
Bulk RNA-seq Domain Expert

This module provides domain expertise for bulk RNA sequencing analysis,
including differential expression, pathway analysis, and result interpretation.
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


class RNASeqDomainExpert(DomainExpert):
    """Domain expert for bulk RNA-seq analysis"""
    
    def get_metadata(self) -> TechniqueMetadata:
        return TechniqueMetadata(
            name="rnaseq",
            display_name="Bulk RNA-seq",
            description="Bulk RNA sequencing for studying gene expression changes between conditions",
            category="Transcriptomics",
            subcategory="Bulk",
            aliases=["rna-seq", "bulk-rna", "transcriptome"],
            related_techniques=["scrnaseq", "microarray", "rt-pcr"],
            typical_applications=[
                "Differential gene expression",
                "Pathway analysis", 
                "Time course studies",
                "Treatment response",
                "Disease comparison"
            ],
            required_expertise=ExpertiseLevel.INTERMEDIATE,
            version="2.0",
            author="Gliaent Bioinformatics Team"
        )
    
    def get_prompts(self) -> Dict[str, DomainPrompt]:
        """Get all RNA-seq domain prompts"""
        prompts = {}
        prompts.update(self._get_interpretation_prompts())
        prompts.update(self._get_quality_control_prompts())
        prompts.update(self._get_pathway_analysis_prompts())
        prompts.update(self._get_troubleshooting_prompts())
        return prompts
    
    def _get_interpretation_prompts(self) -> Dict[str, DomainPrompt]:
        """Result interpretation prompts"""
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
- Statistical method: {statistical_method}
- FDR threshold: {fdr_threshold}
- Log2 fold change threshold: {fc_threshold}

Please interpret these results, including:
1. Biological significance of the expression changes
2. Potential pathways and processes affected
3. Clinical or therapeutic implications
4. Suggested validation experiments (qPCR, Western blot, etc.)
5. Follow-up analyses to consider
6. Potential confounding factors to investigate
""",
                parameters=["total_genes", "de_genes_count", "upregulated_count", 
                          "downregulated_count", "top_upregulated", "top_downregulated",
                          "statistical_method", "fdr_threshold", "fc_threshold"],
                expertise_level=ExpertiseLevel.EXPERT,
                biological_context=BiologicalContext.DIFFERENTIAL_EXPRESSION,
                tags={"differential-expression", "statistics", "validation"},
                references=["doi:10.1186/s13059-014-0550-8", "doi:10.1093/nar/gks042"]
            ),
            
            "interpret_expression_patterns": DomainPrompt(
                name="interpret_expression_patterns",
                description="Interpret gene expression patterns across samples",
                template="""
Gene expression pattern analysis:

- Gene of interest: {gene_name}
- Expression across samples: {expression_values}
- Sample groups: {sample_groups}
- Pattern type: {pattern_type}
- Statistical significance: {pvalue}
- Known function: {gene_function}
- Expression rank: {expression_rank}

Please interpret this expression pattern, including:
1. Biological significance of the observed pattern
2. Relationship to experimental conditions or sample types
3. Potential regulatory mechanisms
4. Clinical relevance if applicable
5. Suggested follow-up genes to examine
6. Experimental validations to perform
""",
                parameters=["gene_name", "expression_values", "sample_groups", 
                          "pattern_type", "pvalue", "gene_function", "expression_rank"],
                expertise_level=ExpertiseLevel.INTERMEDIATE,
                biological_context=BiologicalContext.GENE_EXPRESSION,
                tags={"patterns", "expression", "regulation"},
                references=["doi:10.1038/nrg.2017.88"]
            )
        }
    
    def _get_quality_control_prompts(self) -> Dict[str, DomainPrompt]:
        """Quality control prompts"""
        return {
            "qc_assessment": DomainPrompt(
                name="qc_assessment",
                description="Assess RNA-seq data quality metrics",
                template="""
RNA-seq quality control metrics:

- Total samples: {total_samples}
- Average read count per sample: {avg_reads}
- Mapping rate: {mapping_rate}%
- Duplicate rate: {duplicate_rate}%
- rRNA contamination: {rrna_rate}%
- Gene detection rate: {gene_detection_rate}%
- Sample correlation range: {correlation_range}
- Batch effects detected: {batch_effects}

Please assess the data quality, including:
1. Overall data quality assessment (excellent/good/moderate/poor)
2. Which metrics are concerning and why
3. Potential sources of technical variation
4. Recommendations for filtering or normalization
5. Whether the data is suitable for downstream analysis
6. Suggestions for improving future experiments
""",
                parameters=["total_samples", "avg_reads", "mapping_rate", "duplicate_rate",
                          "rrna_rate", "gene_detection_rate", "correlation_range", "batch_effects"],
                expertise_level=ExpertiseLevel.INTERMEDIATE,
                biological_context=BiologicalContext.QUALITY_CONTROL,
                tags={"qc", "quality", "technical-variation"},
                references=["doi:10.1186/s13059-016-0881-8"]
            )
        }
    
    def _get_pathway_analysis_prompts(self) -> Dict[str, DomainPrompt]:
        """Pathway analysis prompts"""
        return {
            "interpret_pathway_enrichment": DomainPrompt(
                name="interpret_pathway_enrichment",
                description="Interpret pathway enrichment analysis results",
                template="""
Pathway enrichment analysis results:

- Analysis method: {enrichment_method}
- Database used: {pathway_database}
- Total pathways tested: {total_pathways}
- Significantly enriched: {enriched_count}
- Top enriched pathway: {top_pathway}
- Enrichment p-value: {top_pvalue}
- Genes in pathway: {pathway_genes}
- Fold enrichment: {fold_enrichment}

Please interpret these pathway results, including:
1. Biological processes most affected by your experimental conditions
2. How these pathways relate to your research question
3. Therapeutic targets or drug mechanisms suggested
4. Connections between different enriched pathways
5. Limitations of the analysis approach
6. Suggested follow-up experiments or analyses
""",
                parameters=["enrichment_method", "pathway_database", "total_pathways", 
                          "enriched_count", "top_pathway", "top_pvalue", "pathway_genes", "fold_enrichment"],
                expertise_level=ExpertiseLevel.EXPERT,
                biological_context=BiologicalContext.PATHWAY_ANALYSIS,
                tags={"pathways", "enrichment", "functional-analysis"},
                references=["doi:10.1371/journal.pcbi.1002375"]
            ),
            
            "gene_set_analysis": DomainPrompt(
                name="gene_set_analysis",
                description="Interpret gene set enrichment analysis (GSEA) results",
                template="""
Gene Set Enrichment Analysis (GSEA) results:

- Gene sets tested: {total_gene_sets}
- Significantly enriched: {enriched_sets}
- Top enriched set: {top_gene_set}
- Normalized enrichment score: {nes}
- FDR q-value: {fdr_qvalue}
- Leading edge genes: {leading_edge}
- Enrichment plot pattern: {plot_pattern}

Please interpret these GSEA results, including:
1. Biological significance of the enriched gene sets
2. What the enrichment pattern tells us about the biology
3. Key genes driving the enrichment (leading edge)
4. How this relates to your experimental hypothesis
5. Validation strategies for the findings
6. Additional gene sets to investigate
""",
                parameters=["total_gene_sets", "enriched_sets", "top_gene_set", 
                          "nes", "fdr_qvalue", "leading_edge", "plot_pattern"],
                expertise_level=ExpertiseLevel.EXPERT,
                biological_context=BiologicalContext.PATHWAY_ANALYSIS,
                tags={"gsea", "gene-sets", "enrichment", "leading-edge"},
                references=["doi:10.1073/pnas.0506580102"]
            )
        }
    
    def _get_troubleshooting_prompts(self) -> Dict[str, DomainPrompt]:
        """Troubleshooting prompts"""
        return {
            "troubleshoot_rnaseq": DomainPrompt(
                name="troubleshoot_rnaseq",
                description="Help troubleshoot RNA-seq analysis issues",
                template="""
RNA-seq analysis issue:

- Problem description: {problem_description}
- Analysis step: {analysis_step}
- Error message: {error_message}
- Sample information: {sample_info}
- Analysis parameters: {parameters}
- Software/pipeline used: {software_info}

Please provide troubleshooting guidance, including:
1. Most likely causes of this issue
2. Step-by-step troubleshooting approach
3. Parameter adjustments to try
4. Alternative analysis strategies
5. How to prevent this issue in future analyses
6. When to seek additional bioinformatics support
""",
                parameters=["problem_description", "analysis_step", "error_message",
                          "sample_info", "parameters", "software_info"],
                expertise_level=ExpertiseLevel.EXPERT,
                biological_context=BiologicalContext.TROUBLESHOOTING,
                tags={"troubleshooting", "errors", "analysis-issues"}
            )
        }


# Auto-register this expert when module is imported
register_expert(RNASeqDomainExpert)


if __name__ == "__main__":
    # Test the RNA-seq expert
    print("Testing RNA-seq Domain Expert")
    
    expert = RNASeqDomainExpert()
    metadata = expert.get_metadata()
    
    print(f"Expert: {metadata.display_name}")
    print(f"Category: {metadata.category}")
    print(f"Applications: {metadata.typical_applications}")
    
    prompts = expert.get_prompts()
    print(f"Total prompts: {len(prompts)}")
    
    # Test pathway analysis prompt
    pathway_prompt = expert.get_prompt_by_name("interpret_pathway_enrichment")
    if pathway_prompt:
        print(f"Pathway prompt tags: {pathway_prompt.tags}")
        print(f"References: {pathway_prompt.references}")
    
    # Validation
    errors = expert.validate_prompts()
    print(f"Validation errors: {len(errors)}")
    if errors:
        for error in errors:
            print(f"  - {error}") 