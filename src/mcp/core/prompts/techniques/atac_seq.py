"""
ATAC-seq Domain Expert

This module provides domain expertise for ATAC-seq (Assay for Transposase-Accessible
Chromatin using sequencing) analysis, including peak interpretation and chromatin
accessibility analysis.
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


class ATACSeqDomainExpert(DomainExpert):
    """Domain expert for ATAC-seq analysis"""
    
    def get_metadata(self) -> TechniqueMetadata:
        return TechniqueMetadata(
            name="atacseq",
            display_name="ATAC-seq",
            description="Assay for Transposase-Accessible Chromatin using sequencing",
            category="Epigenomics",
            subcategory="Chromatin Accessibility",
            aliases=["atac_seq", "atac", "chromatin_accessibility"],
            related_techniques=["chipseq", "dnase_seq", "faire_seq", "scatac_seq"],
            typical_applications=[
                "Chromatin accessibility profiling",
                "Transcription factor footprinting",
                "Regulatory element identification",
                "Epigenomic disease studies",
                "Development and differentiation studies"
            ],
            required_expertise=ExpertiseLevel.EXPERT,
            version="2.0",
            author="Gliaent Bioinformatics Team"
        )
    
    def get_prompts(self) -> Dict[str, DomainPrompt]:
        """Get all ATAC-seq domain prompts"""
        prompts = {}
        prompts.update(self._get_interpretation_prompts())
        prompts.update(self._get_quality_control_prompts())
        prompts.update(self._get_comparison_prompts())
        prompts.update(self._get_troubleshooting_prompts())
        return prompts
    
    def _get_interpretation_prompts(self) -> Dict[str, DomainPrompt]:
        """Peak and accessibility interpretation prompts"""
        return {
            "interpret_peaks": DomainPrompt(
                name="interpret_peaks",
                description="Interpret chromatin accessibility peaks",
                template="""
ATAC-seq peak analysis results:

- Total peaks identified: {total_peaks}
- Peaks in promoters: {promoter_peaks} ({promoter_percentage}%)
- Peaks in enhancers: {enhancer_peaks} ({enhancer_percentage}%)
- Peaks in gene bodies: {genebody_peaks} ({genebody_percentage}%)
- Peaks in intergenic regions: {intergenic_peaks} ({intergenic_percentage}%)
- Top accessible regions: {top_regions}
- Peak width distribution: {peak_width_stats}
- Signal-to-noise ratio: {signal_noise_ratio}

Please interpret these accessibility patterns, including:
1. Overall chromatin landscape overview
2. Regulatory element activity and distribution
3. Potential transcription factor binding sites
4. Biological implications of accessibility changes
5. Comparison to expected accessibility patterns for this cell type/condition
6. Suggested follow-up analyses (motif analysis, footprinting, etc.)
""",
                parameters=["total_peaks", "promoter_peaks", "promoter_percentage", 
                          "enhancer_peaks", "enhancer_percentage", "genebody_peaks", 
                          "genebody_percentage", "intergenic_peaks", "intergenic_percentage",
                          "top_regions", "peak_width_stats", "signal_noise_ratio"],
                expertise_level=ExpertiseLevel.EXPERT,
                biological_context=BiologicalContext.CHROMATIN_ACCESSIBILITY,
                tags={"peaks", "chromatin", "accessibility", "regulatory-elements"},
                references=["doi:10.1038/nmeth.2688", "doi:10.1038/s41586-020-2493-4"]
            ),
            
            "interpret_motif_analysis": DomainPrompt(
                name="interpret_motif_analysis",
                description="Interpret transcription factor motif enrichment results",
                template="""
ATAC-seq motif enrichment analysis results:

- Total motifs tested: {total_motifs}
- Significantly enriched motifs: {enriched_motifs}
- Top enriched transcription factor: {top_tf}
- Enrichment p-value: {top_pvalue}
- Fold enrichment: {fold_enrichment}
- Motif occurrence frequency: {motif_frequency}
- Known TF families represented: {tf_families}
- Condition-specific motifs: {condition_specific}

Please interpret these motif results, including:
1. Key transcription factors likely active in your samples
2. Regulatory networks and pathways implicated
3. Biological significance of the enriched TF families
4. How these results relate to the experimental condition
5. Potential upstream regulators and signaling pathways
6. Validation experiments to confirm TF activity
""",
                parameters=["total_motifs", "enriched_motifs", "top_tf", "top_pvalue",
                          "fold_enrichment", "motif_frequency", "tf_families", "condition_specific"],
                expertise_level=ExpertiseLevel.EXPERT,
                biological_context=BiologicalContext.CHROMATIN_ACCESSIBILITY,
                tags={"motifs", "transcription-factors", "regulatory-networks"},
                references=["doi:10.1016/j.cell.2018.06.052"]
            ),
            
            "interpret_footprinting": DomainPrompt(
                name="interpret_footprinting",
                description="Interpret transcription factor footprinting results",
                template="""
ATAC-seq footprinting analysis results:

- Footprints identified: {total_footprints}
- High-confidence footprints: {confident_footprints}
- Top footprinted transcription factor: {top_footprinted_tf}
- Footprint score: {footprint_score}
- Protection score: {protection_score}
- Footprint width: {footprint_width}
- Flanking accessibility: {flanking_signal}

Please interpret these footprinting results, including:
1. Evidence for transcription factor binding in vivo
2. Confidence level in the footprinting results
3. Biological significance of the footprinted regions
4. Comparison with expected TF binding patterns
5. Integration with motif enrichment results
6. Suggested validation approaches (ChIP-seq, EMSA, etc.)
""",
                parameters=["total_footprints", "confident_footprints", "top_footprinted_tf",
                          "footprint_score", "protection_score", "footprint_width", "flanking_signal"],
                expertise_level=ExpertiseLevel.SPECIALIST,
                biological_context=BiologicalContext.CHROMATIN_ACCESSIBILITY,
                tags={"footprinting", "tf-binding", "in-vivo-binding"},
                references=["doi:10.1038/nature14590"]
            )
        }
    
    def _get_quality_control_prompts(self) -> Dict[str, DomainPrompt]:
        """Quality control prompts"""
        return {
            "qc_assessment": DomainPrompt(
                name="qc_assessment",
                description="Assess ATAC-seq data quality metrics",
                template="""
ATAC-seq quality control metrics:

- Total reads: {total_reads}
- Mapping rate: {mapping_rate}%
- Mitochondrial reads: {mito_reads}%
- Duplicate rate: {duplicate_rate}%
- Fragment size distribution: {fragment_size_dist}
- TSS enrichment score: {tss_enrichment}
- Fraction of reads in peaks (FRiP): {frip_score}
- Peak calling summary: {peak_summary}
- Library complexity: {library_complexity}

Please assess the data quality, including:
1. Overall data quality assessment (excellent/good/moderate/poor)
2. Which metrics are concerning and why
3. Potential sources of technical problems
4. Recommendations for data processing parameters
5. Whether the data is suitable for downstream analysis
6. Suggestions for improving future ATAC-seq experiments
""",
                parameters=["total_reads", "mapping_rate", "mito_reads", "duplicate_rate",
                          "fragment_size_dist", "tss_enrichment", "frip_score", 
                          "peak_summary", "library_complexity"],
                expertise_level=ExpertiseLevel.INTERMEDIATE,
                biological_context=BiologicalContext.QUALITY_CONTROL,
                tags={"qc", "quality-metrics", "tss-enrichment", "frip"},
                references=["doi:10.1038/s41467-020-14288-y"]
            )
        }
    
    def _get_comparison_prompts(self) -> Dict[str, DomainPrompt]:
        """Comparison analysis prompts"""
        return {
            "compare_accessibility": DomainPrompt(
                name="compare_accessibility",
                description="Compare chromatin accessibility between conditions",
                template="""
Differential accessibility analysis results:

- Condition 1: {condition1_name} ({condition1_samples} samples)
- Condition 2: {condition2_name} ({condition2_samples} samples)
- Differentially accessible regions: {dar_count}
- More accessible in condition 1: {more_accessible_cond1}
- More accessible in condition 2: {more_accessible_cond2}
- Top gained accessibility regions: {top_gained_regions}
- Top lost accessibility regions: {top_lost_regions}
- Affected regulatory elements: {affected_elements}
- Associated genes: {associated_genes}

Please interpret this accessibility comparison, including:
1. Key regulatory changes between conditions
2. Potential biological drivers of accessibility differences
3. Transcription factors that may be responsible for changes
4. Implications for gene expression regulation
5. Therapeutic or diagnostic relevance if applicable
6. Suggested validation experiments
""",
                parameters=["condition1_name", "condition1_samples", "condition2_name", 
                          "condition2_samples", "dar_count", "more_accessible_cond1",
                          "more_accessible_cond2", "top_gained_regions", "top_lost_regions",
                          "affected_elements", "associated_genes"],
                expertise_level=ExpertiseLevel.EXPERT,
                biological_context=BiologicalContext.COMPARATIVE_ANALYSIS,
                tags={"differential-accessibility", "comparison", "regulatory-changes"},
                references=["doi:10.1016/j.cell.2016.10.024"]
            )
        }
    
    def _get_troubleshooting_prompts(self) -> Dict[str, DomainPrompt]:
        """Troubleshooting prompts"""
        return {
            "troubleshoot_atacseq": DomainPrompt(
                name="troubleshoot_atacseq",
                description="Help troubleshoot ATAC-seq analysis issues",
                template="""
ATAC-seq analysis issue:

- Problem description: {problem_description}
- Analysis step: {analysis_step}
- Error message: {error_message}
- Sample information: {sample_info}
- Library preparation: {library_prep}
- Analysis parameters: {parameters}
- Software used: {software_info}

Please provide troubleshooting guidance, including:
1. Most likely causes of this issue
2. Step-by-step troubleshooting approach
3. Parameter adjustments to try
4. Alternative analysis strategies
5. How to prevent this issue in future experiments
6. When to consider re-doing the library preparation
""",
                parameters=["problem_description", "analysis_step", "error_message",
                          "sample_info", "library_prep", "parameters", "software_info"],
                expertise_level=ExpertiseLevel.EXPERT,
                biological_context=BiologicalContext.TROUBLESHOOTING,
                tags={"troubleshooting", "errors", "library-prep", "analysis-issues"}
            )
        }


# Auto-register this expert when module is imported
register_expert(ATACSeqDomainExpert)


if __name__ == "__main__":
    # Test the ATAC-seq expert
    print("Testing ATAC-seq Domain Expert")
    
    expert = ATACSeqDomainExpert()
    metadata = expert.get_metadata()
    
    print(f"Expert: {metadata.display_name}")
    print(f"Category: {metadata.category}")
    print(f"Subcategory: {metadata.subcategory}")
    print(f"Applications: {metadata.typical_applications}")
    
    prompts = expert.get_prompts()
    print(f"Total prompts: {len(prompts)}")
    
    # Test peak interpretation prompt
    peak_prompt = expert.get_prompt_by_name("interpret_peaks")
    if peak_prompt:
        print(f"Peak prompt parameters: {len(peak_prompt.parameters)}")
        print(f"References: {peak_prompt.references}")
    
    # Test footprinting prompt
    footprint_prompt = expert.get_prompt_by_name("interpret_footprinting")
    if footprint_prompt:
        print(f"Footprinting prompt expertise: {footprint_prompt.expertise_level}")
        print(f"Tags: {footprint_prompt.tags}")
    
    # Validation
    errors = expert.validate_prompts()
    print(f"Validation errors: {len(errors)}")
    if errors:
        for error in errors:
            print(f"  - {error}") 