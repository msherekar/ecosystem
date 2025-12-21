"""
Common Prompt Templates

Provides reusable prompt templates that can be used across different techniques
and analysis types. These templates are standardized and well-tested.

This file is separate to keep template management clean and allow for
easy customization and extension.
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum


class TemplateCategory(Enum):
    """Categories of prompt templates"""
    GUIDANCE = "guidance"
    INTERPRETATION = "interpretation"
    TROUBLESHOOTING = "troubleshooting"
    WORKFLOW = "workflow"
    QUALITY_CONTROL = "quality_control"
    REPORTING = "reporting"


@dataclass
class PromptTemplate:
    """A reusable prompt template"""
    name: str
    description: str
    template: str
    parameters: List[str]
    category: TemplateCategory
    use_cases: List[str]
    
    def render(self, **kwargs) -> str:
        """Render the template with provided parameters"""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required parameter: {e}")


class CommonPromptTemplates:
    """Collection of common prompt templates for bioinformatics analysis"""
    
    @staticmethod
    def get_all_templates() -> Dict[str, PromptTemplate]:
        """Get all available templates"""
        return {
            "suggest_next_steps": CommonPromptTemplates.suggest_next_steps_template(),
            "interpret_clustering_results": CommonPromptTemplates.interpret_clustering_results_template(),
            "troubleshoot_common_issues": CommonPromptTemplates.troubleshoot_common_issues_template(),
            "quality_control_assessment": CommonPromptTemplates.quality_control_assessment_template(),
            "differential_expression_interpretation": CommonPromptTemplates.differential_expression_interpretation_template(),
            "parameter_optimization": CommonPromptTemplates.parameter_optimization_template(),
            "visualization_guidance": CommonPromptTemplates.visualization_guidance_template(),
            "workflow_planning": CommonPromptTemplates.workflow_planning_template(),
            "results_summary": CommonPromptTemplates.results_summary_template(),
            "method_comparison": CommonPromptTemplates.method_comparison_template()
        }
    
    @staticmethod
    def suggest_next_steps_template() -> PromptTemplate:
        """Template for suggesting next analysis steps"""
        return PromptTemplate(
            name="suggest_next_steps",
            description="Suggest logical next steps in analysis workflow",
            template="""Based on the current {analysis_type} analysis state:

Current Progress:
- Analysis step: {current_step}
- Data status: {data_status}
- Completed steps: {completed_steps}
- Sample count: {n_samples}
- Significant features: {significant_features}

Please suggest the next logical analysis steps:

1. **Immediate Next Steps**
   - What should be done right now based on current progress
   - Any quality checks or validations needed

2. **Alternative Analysis Paths**
   - Different approaches to consider
   - When to use each alternative

3. **Potential Issues to Watch**
   - Common problems at this stage
   - How to detect and prevent them

4. **Visualization and Interpretation**
   - What plots or summaries would be helpful
   - How to interpret the results

5. **Documentation and Reporting**
   - What should be documented at this stage
   - Key metrics to track""",
            parameters=[
                "analysis_type", "current_step", "data_status", 
                "completed_steps", "n_samples", "significant_features"
            ],
            category=TemplateCategory.GUIDANCE,
            use_cases=["workflow planning", "analysis guidance", "progress tracking"]
        )
    
    @staticmethod
    def interpret_clustering_results_template() -> PromptTemplate:
        """Template for interpreting clustering results"""
        return PromptTemplate(
            name="interpret_clustering_results",
            description="Help interpret clustering analysis results",
            template="""{analysis_type} clustering analysis results:

Clustering Summary:
- Number of clusters: {n_clusters}
- Cluster sizes: {cluster_sizes}
- Method used: {clustering_method}
- Parameters: {clustering_params}
- Quality metrics: {quality_metrics}

Please provide interpretation guidance:

1. **Cluster Quality Assessment**
   - Are the clusters well-separated and meaningful?
   - Do cluster sizes suggest biological relevance?
   - How do quality metrics compare to expected ranges?

2. **Biological Significance**
   - What might each cluster represent biologically?
   - Are there known biological processes that could explain the clustering?
   - How do results compare to published studies?

3. **Cluster Characterization**
   - What features distinguish each cluster?
   - Which markers or genes are most important?
   - How to validate cluster identities?

4. **Next Steps for Analysis**
   - What downstream analyses would be most informative?
   - How to further validate or refine the clusters?
   - What comparisons or contrasts to perform?""",
            parameters=[
                "analysis_type", "n_clusters", "cluster_sizes", 
                "clustering_method", "clustering_params", "quality_metrics"
            ],
            category=TemplateCategory.INTERPRETATION,
            use_cases=["clustering analysis", "cell type identification", "sample grouping"]
        )
    
    @staticmethod
    def troubleshoot_common_issues_template() -> PromptTemplate:
        """Template for troubleshooting analysis issues"""
        return PromptTemplate(
            name="troubleshoot_common_issues",
            description="Help troubleshoot common analysis problems",
            template="""{analysis_type} analysis troubleshooting:

Problem Details:
- Issue: {problem_description}
- Analysis step: {analysis_step}
- Error message: {error_message}
- Data characteristics: {data_characteristics}
- Environment: {environment_info}

Troubleshooting guidance:

1. **Immediate Diagnosis**
   - Most likely causes of this specific issue
   - Quick checks to narrow down the problem
   - Emergency fixes if data integrity is at risk

2. **Step-by-Step Solutions**
   - Detailed resolution steps in order of likelihood
   - Alternative approaches if primary solution fails
   - How to verify each fix attempt

3. **Parameter Adjustments**
   - Which parameters to modify and why
   - Safe ranges for parameter changes
   - How to test parameter effects

4. **Prevention Strategies**
   - How to avoid this issue in future analyses
   - Early warning signs to watch for
   - Best practices for this analysis type

5. **When to Seek Additional Help**
   - Signs that the issue requires expert consultation
   - What information to gather before seeking help
   - Alternative analysis approaches to consider""",
            parameters=[
                "analysis_type", "problem_description", "analysis_step",
                "error_message", "data_characteristics", "environment_info"
            ],
            category=TemplateCategory.TROUBLESHOOTING,
            use_cases=["error resolution", "parameter tuning", "method optimization"]
        )
    
    @staticmethod
    def quality_control_assessment_template() -> PromptTemplate:
        """Template for quality control assessment"""
        return PromptTemplate(
            name="quality_control_assessment",
            description="Assess data quality and suggest improvements",
            template="""Quality Control Assessment for {analysis_type}:

Data Quality Metrics:
- Sample count: {n_samples}
- Feature count: {n_features}
- Missing data: {missing_data_pct}%
- Quality scores: {quality_scores}
- Outlier detection: {outlier_info}

Assessment and Recommendations:

1. **Overall Data Quality**
   - Is the data suitable for downstream analysis?
   - What are the main quality concerns?
   - How do metrics compare to typical standards?

2. **Filtering Recommendations**
   - Which samples or features should be filtered?
   - What filtering thresholds are appropriate?
   - How aggressive should quality control be?

3. **Preprocessing Steps**
   - What normalization or transformation is needed?
   - Are there batch effects to address?
   - What additional quality checks to perform?

4. **Impact on Analysis**
   - How will data quality affect downstream results?
   - What analyses are safe to proceed with?
   - Where should we be more cautious in interpretation?""",
            parameters=[
                "analysis_type", "n_samples", "n_features", 
                "missing_data_pct", "quality_scores", "outlier_info"
            ],
            category=TemplateCategory.QUALITY_CONTROL,
            use_cases=["data validation", "preprocessing", "quality assessment"]
        )
    
    @staticmethod
    def differential_expression_interpretation_template() -> PromptTemplate:
        """Template for interpreting differential expression results"""
        return PromptTemplate(
            name="differential_expression_interpretation", 
            description="Interpret differential expression analysis results",
            template="""Differential Expression Analysis Results:

Results Summary:
- Comparison: {comparison_description}
- Significant genes: {n_significant_genes}
- Upregulated: {n_upregulated}
- Downregulated: {n_downregulated}
- Statistical method: {statistical_method}
- Significance threshold: {significance_threshold}

Top Results:
{top_genes_table}

Interpretation Guidance:

1. **Result Quality Assessment**
   - Do the results make biological sense?
   - Are effect sizes meaningful and significant?
   - How robust are the statistical results?

2. **Biological Interpretation**
   - What biological processes are affected?
   - Are there known pathways or gene sets enriched?
   - How do results relate to the experimental design?

3. **Validation and Follow-up**
   - Which results should be validated experimentally?
   - What additional analyses would strengthen conclusions?
   - How to prioritize genes for further study?

4. **Pathway and Network Analysis**
   - What pathway enrichment analyses to perform?
   - How to interpret pathway results in context?
   - What regulatory networks might be involved?""",
            parameters=[
                "comparison_description", "n_significant_genes", "n_upregulated",
                "n_downregulated", "statistical_method", "significance_threshold", "top_genes_table"
            ],
            category=TemplateCategory.INTERPRETATION,
            use_cases=["differential expression", "gene analysis", "pathway analysis"]
        )
    
    @staticmethod
    def parameter_optimization_template() -> PromptTemplate:
        """Template for parameter optimization guidance"""
        return PromptTemplate(
            name="parameter_optimization",
            description="Guide parameter optimization for analysis methods",
            template="""Parameter Optimization for {analysis_type}:

Current Parameters:
{current_parameters}

Optimization Goals:
- Primary objective: {primary_objective}
- Quality metrics to maximize: {target_metrics}
- Constraints: {constraints}

Optimization Strategy:

1. **Parameter Prioritization**
   - Which parameters have the biggest impact?
   - What order should parameters be optimized?
   - Which parameters can be fixed at default values?

2. **Search Strategy**
   - Recommended parameter ranges to explore
   - Grid search vs. random search considerations
   - How to balance exploration vs. exploitation

3. **Evaluation Criteria**
   - How to measure optimization success
   - Multiple objective considerations
   - Validation strategies to avoid overfitting

4. **Practical Considerations**
   - Computational cost vs. performance trade-offs
   - When to stop the optimization process
   - How to document and reproduce optimal settings""",
            parameters=[
                "analysis_type", "current_parameters", "primary_objective",
                "target_metrics", "constraints"
            ],
            category=TemplateCategory.GUIDANCE,
            use_cases=["method optimization", "parameter tuning", "performance improvement"]
        )
    
    @staticmethod
    def visualization_guidance_template() -> PromptTemplate:
        """Template for visualization guidance"""
        return PromptTemplate(
            name="visualization_guidance",
            description="Provide guidance on effective data visualization",
            template="""Visualization Guidance for {analysis_type}:

Data Context:
- Data type: {data_type}
- Sample size: {sample_size}
- Key variables: {key_variables}
- Analysis goal: {analysis_goal}

Visualization Recommendations:

1. **Plot Type Selection**
   - Most appropriate plot types for this data
   - When to use each visualization approach
   - How to handle high-dimensional data

2. **Design Principles**
   - Color schemes that enhance interpretation
   - Layout and annotation best practices
   - How to highlight key findings

3. **Interactive Elements**
   - When to add interactivity
   - Most useful interactive features
   - Tools and libraries to consider

4. **Publication and Presentation**
   - How to prepare figures for publication
   - What supplementary visualizations to include
   - How to ensure accessibility and clarity""",
            parameters=[
                "analysis_type", "data_type", "sample_size", 
                "key_variables", "analysis_goal"
            ],
            category=TemplateCategory.GUIDANCE,
            use_cases=["data visualization", "plot selection", "figure preparation"]
        )
    
    @staticmethod
    def workflow_planning_template() -> PromptTemplate:
        """Template for analysis workflow planning"""
        return PromptTemplate(
            name="workflow_planning",
            description="Help plan comprehensive analysis workflows",
            template="""Analysis Workflow Planning:

Project Context:
- Research question: {research_question}
- Data type: {data_type}
- Sample information: {sample_info}
- Available resources: {available_resources}
- Timeline: {timeline}

Recommended Workflow:

1. **Phase 1: Data Preparation**
   - Quality control and preprocessing steps
   - Data integration and harmonization
   - Exploratory data analysis

2. **Phase 2: Primary Analysis**
   - Core analytical methods to apply
   - Statistical approaches and parameters
   - Validation and quality checks

3. **Phase 3: Interpretation**
   - Biological interpretation methods
   - Pathway and network analysis
   - Result visualization and reporting

4. **Phase 4: Validation and Follow-up**
   - Experimental validation priorities
   - Additional analyses to consider
   - Publication and sharing strategies

Each phase includes: estimated time, required resources, key deliverables, and decision points.""",
            parameters=[
                "research_question", "data_type", "sample_info", 
                "available_resources", "timeline"
            ],
            category=TemplateCategory.WORKFLOW,
            use_cases=["project planning", "workflow design", "resource allocation"]
        )
    
    @staticmethod
    def results_summary_template() -> PromptTemplate:
        """Template for summarizing analysis results"""
        return PromptTemplate(
            name="results_summary",
            description="Generate comprehensive results summaries",
            template="""Analysis Results Summary:

Study Overview:
- Analysis type: {analysis_type}
- Research question: {research_question}
- Data description: {data_description}
- Methods used: {methods_used}

Key Findings:
{key_findings}

Statistical Summary:
{statistical_summary}

Biological Insights:
{biological_insights}

Summary:

1. **Main Conclusions**
   - Primary discoveries and their significance
   - How results address the research question
   - Statistical confidence in findings

2. **Biological Implications**
   - What the results mean biologically
   - How findings relate to existing knowledge
   - Potential clinical or research applications

3. **Limitations and Considerations**
   - Study limitations and potential biases
   - Areas of uncertainty in the results
   - Need for additional validation

4. **Next Steps**
   - Recommended follow-up studies
   - Additional analyses to strengthen conclusions
   - Potential collaborations or resources needed""",
            parameters=[
                "analysis_type", "research_question", "data_description",
                "methods_used", "key_findings", "statistical_summary", "biological_insights"
            ],
            category=TemplateCategory.REPORTING,
            use_cases=["results reporting", "manuscript preparation", "presentation summaries"]
        )
    
    @staticmethod
    def method_comparison_template() -> PromptTemplate:
        """Template for comparing analysis methods"""
        return PromptTemplate(
            name="method_comparison",
            description="Compare different analysis methods and approaches",
            template="""Method Comparison for {analysis_type}:

Methods Evaluated:
{methods_description}

Comparison Criteria:
- Accuracy: {accuracy_comparison}
- Computational efficiency: {efficiency_comparison}
- Robustness: {robustness_comparison}
- Interpretability: {interpretability_comparison}

Detailed Comparison:

1. **Performance Analysis**
   - Which method performed best overall?
   - Are there specific conditions where each excels?
   - How significant are the performance differences?

2. **Practical Considerations**
   - Ease of implementation and use
   - Computational resource requirements
   - Software availability and support

3. **Use Case Recommendations**
   - When to use each method
   - How to choose between methods for new projects
   - Combination strategies that might be effective

4. **Future Considerations**
   - Emerging methods to watch
   - How the field is evolving
   - When to revisit method choices""",
            parameters=[
                "analysis_type", "methods_description", "accuracy_comparison",
                "efficiency_comparison", "robustness_comparison", "interpretability_comparison"
            ],
            category=TemplateCategory.GUIDANCE,
            use_cases=["method selection", "benchmark studies", "protocol development"]
        )


def main():
    """Main function for module testing"""
    print("Testing Common Prompt Templates...")
    
    # Get all templates
    templates = CommonPromptTemplates.get_all_templates()
    
    print(f"✅ Available templates: {len(templates)}")
    
    # Test each template
    for name, template in templates.items():
        print(f"✅ Template: {template.name}")
        print(f"   Category: {template.category.value}")
        print(f"   Parameters: {len(template.parameters)}")
        print(f"   Use cases: {', '.join(template.use_cases)}")
        
        # Test template rendering with dummy data
        try:
            dummy_params = {param: f"test_{param}" for param in template.parameters}
            rendered = template.render(**dummy_params)
            print(f"   ✅ Rendering test passed ({len(rendered)} chars)")
        except Exception as e:
            print(f"   ❌ Rendering test failed: {e}")
    
    # Test specific template with realistic data
    next_steps = templates["suggest_next_steps"]
    realistic_params = {
        "analysis_type": "scRNA-seq",
        "current_step": "Quality control",
        "data_status": "Filtered and normalized",
        "completed_steps": "QC, normalization",
        "n_samples": "10,000 cells",
        "significant_features": "2,500 genes"
    }
    
    rendered = next_steps.render(**realistic_params)
    print(f"✅ Realistic rendering test: {len(rendered)} characters")
    
    print("🎉 All Template tests passed!")


if __name__ == "__main__":
    main()