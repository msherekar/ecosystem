"""
ATAC-seq MCP Server Implementation

Provides MCP server functionality for ATAC-seq (chromatin accessibility) analysis.
Demonstrates how the improved session tracking automatically handles new analysis types.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
import streamlit as st
import pandas as pd
import numpy as np

from src.mcp.core.server import MCPServer


class ATACSeqMCPServer(MCPServer):
    """MCP Server for ATAC-seq analysis tools"""
    
    def __init__(self):
        super().__init__("atacseq", "1.0.0")
        self.logger = logging.getLogger("mcp.atacseq")
        
        # Configure session tracking for ATAC-seq specific variables
        self.configure_session_tracking(
            tracked_variables=[
                # Core ATAC-seq data
                'atacseq_peaks_df', 'atacseq_metadata_df', 'peak_counts_matrix',
                'fragment_counts', 'tss_enrichment_scores', 'nucleosome_signal',
                
                # Analysis results
                'differential_peaks', 'motif_enrichment_results', 'footprinting_results',
                'chromvar_results', 'cicero_connections', 'archR_project',
                
                # Quality control flags
                'qc_metrics_calculated', 'peaks_called', 'fragments_processed'
            ],
            variable_patterns=[
                r'.*_peaks$',           # Any variable ending with _peaks
                r'.*_accessibility$',   # Accessibility scores
                r'.*_motifs$',         # Motif analysis results
                r'tss_.*',             # TSS-related metrics
                r'nucleosome_.*',      # Nucleosome positioning
                r'.*_footprints$',     # Footprinting results
                r'chromvar_.*',        # ChromVAR results
                r'cicero_.*',          # Cicero co-accessibility
                r'.*_fragments$'       # Fragment-related data
            ],
            auto_discover=True  # Also auto-discover important variables
        )
    
    async def initialize(self) -> None:
        """Initialize the ATAC-seq server"""
        await self._register_analysis_tools()
        await self._register_resources()
        await self._register_prompts()
        self.logger.info("ATAC-seq MCP Server initialized")
    
    async def _register_analysis_tools(self):
        """Register ATAC-seq analysis tools"""
        
        # Main pipeline tool
        self.register_tool(
            name="run_atacseq_pipeline",
            description="Execute the complete ATAC-seq analysis pipeline including peak calling, accessibility analysis, and motif discovery",
            input_schema={
                "type": "object",
                "properties": {
                    "force_rerun": {
                        "type": "boolean",
                        "description": "Force rerun of analysis even if results exist",
                        "default": False
                    },
                    "genome_build": {
                        "type": "string",
                        "description": "Genome build to use (hg38, hg19, mm10, etc.)",
                        "default": "hg38"
                    }
                },
                "required": []
            },
            handler=self._run_pipeline
        )
        
        # Peak calling
        self.register_tool(
            name="call_peaks",
            description="Call accessible chromatin peaks from ATAC-seq data using MACS2",
            input_schema={
                "type": "object",
                "properties": {
                    "q_value": {
                        "type": "number",
                        "description": "Q-value cutoff for peak calling",
                        "default": 0.05
                    },
                    "min_length": {
                        "type": "integer",
                        "description": "Minimum peak length",
                        "default": 150
                    },
                    "max_length": {
                        "type": "integer",
                        "description": "Maximum peak length",
                        "default": 1000
                    }
                },
                "required": []
            },
            handler=self._call_peaks
        )
        
        # Quality control
        self.register_tool(
            name="calculate_qc_metrics",
            description="Calculate ATAC-seq specific QC metrics including TSS enrichment and nucleosome signal",
            input_schema={
                "type": "object",
                "properties": {
                    "tss_window": {
                        "type": "integer",
                        "description": "Window size around TSS for enrichment calculation",
                        "default": 2000
                    }
                },
                "required": []
            },
            handler=self._calculate_qc_metrics
        )
        
        # Differential accessibility
        self.register_tool(
            name="find_differential_peaks",
            description="Find differentially accessible peaks between conditions",
            input_schema={
                "type": "object",
                "properties": {
                    "condition_column": {
                        "type": "string",
                        "description": "Column name for condition comparison",
                        "default": "condition"
                    },
                    "log2fc_cutoff": {
                        "type": "number",
                        "description": "Log2 fold change cutoff",
                        "default": 1.0
                    },
                    "padj_cutoff": {
                        "type": "number",
                        "description": "Adjusted p-value cutoff",
                        "default": 0.05
                    }
                },
                "required": []
            },
            handler=self._find_differential_peaks
        )
        
        # Motif analysis
        self.register_tool(
            name="analyze_motifs",
            description="Perform transcription factor motif enrichment analysis in accessible regions",
            input_schema={
                "type": "object",
                "properties": {
                    "motif_database": {
                        "type": "string",
                        "description": "Motif database to use (JASPAR, HOCOMOCO, etc.)",
                        "default": "JASPAR2022"
                    },
                    "background_regions": {
                        "type": "string",
                        "description": "Background regions for motif analysis",
                        "default": "genome"
                    }
                },
                "required": []
            },
            handler=self._analyze_motifs
        )
        
        # ChromVAR analysis
        self.register_tool(
            name="run_chromvar",
            description="Run ChromVAR analysis to identify transcription factor activity differences",
            input_schema={
                "type": "object",
                "properties": {
                    "motif_set": {
                        "type": "string",
                        "description": "Motif set for ChromVAR analysis",
                        "default": "JASPAR2022"
                    }
                },
                "required": []
            },
            handler=self._run_chromvar
        )
        
        # Footprinting
        self.register_tool(
            name="perform_footprinting",
            description="Perform transcription factor footprinting analysis",
            input_schema={
                "type": "object",
                "properties": {
                    "motif_list": {
                        "type": "array",
                        "description": "List of specific motifs to analyze",
                        "items": {"type": "string"}
                    }
                },
                "required": []
            },
            handler=self._perform_footprinting
        )
    
    async def _register_resources(self):
        """Register ATAC-seq specific resources"""
        
        # Peak annotations
        self.register_resource(
            uri="atacseq://peaks/annotations",
            name="Peak Annotations",
            description="Genomic annotations for called peaks",
            mime_type="application/json"
        )
        
        # QC metrics
        self.register_resource(
            uri="atacseq://qc/metrics",
            name="QC Metrics",
            description="ATAC-seq quality control metrics",
            mime_type="application/json"
        )
        
        # Motif results
        self.register_resource(
            uri="atacseq://motifs/enrichment",
            name="Motif Enrichment Results",
            description="Transcription factor motif enrichment analysis results",
            mime_type="application/json"
        )
    
    async def _register_prompts(self):
        """Register ATAC-seq specific prompts"""
        
        self.register_prompt(
            name="interpret_accessibility",
            description="Interpret chromatin accessibility patterns",
            template="""
            Based on the ATAC-seq analysis results:
            - {num_peaks} peaks were identified
            - TSS enrichment score: {tss_enrichment}
            - {num_differential} differentially accessible regions found
            
            Please interpret these chromatin accessibility patterns and suggest:
            1. What these patterns might indicate about gene regulation
            2. Which transcription factors might be involved
            3. Recommended follow-up analyses
            """,
            parameters={
                "num_peaks": "Number of peaks called",
                "tss_enrichment": "TSS enrichment score",
                "num_differential": "Number of differential peaks"
            }
        )
        
        self.register_prompt(
            name="motif_analysis_summary",
            description="Summarize motif enrichment results",
            template="""
            Motif enrichment analysis identified {num_enriched} significantly enriched motifs.
            
            Top enriched transcription factor families:
            {top_tf_families}
            
            Please provide:
            1. Biological interpretation of these enriched motifs
            2. Potential regulatory networks involved
            3. Connections to the experimental conditions: {conditions}
            """,
            parameters={
                "num_enriched": "Number of enriched motifs",
                "top_tf_families": "List of top TF families",
                "conditions": "Experimental conditions"
            }
        )
    
    def _check_data_availability(self) -> bool:
        """Check if ATAC-seq data is available"""
        required_data = ['atacseq_peaks_df', 'peak_counts_matrix', 'atacseq_metadata_df']
        return any(data in st.session_state for data in required_data)
    
    async def _run_pipeline(self, force_rerun: bool = False, genome_build: str = "hg38") -> Dict[str, Any]:
        """Run the complete ATAC-seq analysis pipeline"""
        try:
            if not self._check_data_availability() and not force_rerun:
                return {
                    "success": False,
                    "message": "ATAC-seq data not available. Please upload peak data first."
                }
            
            # Simulate pipeline execution
            steps_completed = []
            
            # Step 1: QC metrics
            if force_rerun or not st.session_state.get("qc_metrics_calculated", False):
                await self._calculate_qc_metrics()
                steps_completed.append("QC metrics calculation")
                st.session_state["qc_metrics_calculated"] = True
            
            # Step 2: Peak calling (if not done)
            if force_rerun or not st.session_state.get("peaks_called", False):
                await self._call_peaks()
                steps_completed.append("Peak calling")
                st.session_state["peaks_called"] = True
            
            # Step 3: Differential accessibility
            if force_rerun or "differential_peaks" not in st.session_state:
                await self._find_differential_peaks()
                steps_completed.append("Differential accessibility analysis")
            
            # Step 4: Motif analysis
            if force_rerun or "motif_enrichment_results" not in st.session_state:
                await self._analyze_motifs()
                steps_completed.append("Motif enrichment analysis")
            
            return {
                "success": True,
                "message": f"ATAC-seq pipeline completed successfully. Steps: {', '.join(steps_completed)}",
                "genome_build": genome_build,
                "steps_completed": steps_completed
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Pipeline execution failed: {str(e)}"
            }
    
    async def _call_peaks(self, q_value: float = 0.05, min_length: int = 150, max_length: int = 1000) -> Dict[str, Any]:
        """Call accessible chromatin peaks"""
        try:
            # Simulate peak calling
            num_peaks = np.random.randint(20000, 80000)
            
            # Create mock peak data
            peaks_data = {
                'chr': [f'chr{i%22 + 1}' for i in range(num_peaks)],
                'start': np.random.randint(1000, 1000000, num_peaks),
                'end': np.random.randint(1000, 1000000, num_peaks),
                'peak_score': np.random.exponential(10, num_peaks),
                'q_value': np.random.beta(0.1, 10, num_peaks)
            }
            
            peaks_df = pd.DataFrame(peaks_data)
            peaks_df = peaks_df[peaks_df['q_value'] < q_value]
            
            # Store in session state
            st.session_state["atacseq_peaks_df"] = peaks_df
            st.session_state["peaks_called"] = True
            
            return {
                "success": True,
                "message": f"Peak calling completed. {len(peaks_df)} peaks identified.",
                "num_peaks": len(peaks_df),
                "parameters": {
                    "q_value": q_value,
                    "min_length": min_length,
                    "max_length": max_length
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Peak calling failed: {str(e)}"
            }
    
    async def _calculate_qc_metrics(self, tss_window: int = 2000) -> Dict[str, Any]:
        """Calculate ATAC-seq QC metrics"""
        try:
            # Simulate QC calculations
            tss_enrichment = np.random.uniform(5, 15)  # Good ATAC-seq should be >7
            nucleosome_signal = np.random.uniform(0.1, 0.3)  # Lower is better
            fragment_length_dist = np.random.normal(200, 50, 1000)
            
            qc_metrics = {
                'tss_enrichment_score': tss_enrichment,
                'nucleosome_signal': nucleosome_signal,
                'fragment_length_distribution': fragment_length_dist.tolist(),
                'total_fragments': np.random.randint(1000000, 10000000),
                'unique_fragments': np.random.randint(800000, 8000000)
            }
            
            # Store in session state
            st.session_state["tss_enrichment_scores"] = tss_enrichment
            st.session_state["nucleosome_signal"] = nucleosome_signal
            st.session_state["qc_metrics_calculated"] = True
            
            return {
                "success": True,
                "message": "QC metrics calculated successfully",
                "metrics": qc_metrics
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"QC calculation failed: {str(e)}"
            }
    
    async def _find_differential_peaks(self, condition_column: str = "condition", 
                                     log2fc_cutoff: float = 1.0, padj_cutoff: float = 0.05) -> Dict[str, Any]:
        """Find differentially accessible peaks"""
        try:
            # Simulate differential analysis
            num_differential = np.random.randint(1000, 5000)
            
            differential_data = {
                'peak_id': [f'peak_{i}' for i in range(num_differential)],
                'log2FoldChange': np.random.normal(0, 2, num_differential),
                'padj': np.random.beta(0.1, 10, num_differential),
                'accessibility_change': np.random.choice(['increased', 'decreased'], num_differential)
            }
            
            diff_df = pd.DataFrame(differential_data)
            diff_df = diff_df[
                (abs(diff_df['log2FoldChange']) > log2fc_cutoff) & 
                (diff_df['padj'] < padj_cutoff)
            ]
            
            # Store in session state
            st.session_state["differential_peaks"] = diff_df
            
            return {
                "success": True,
                "message": f"Differential accessibility analysis completed. {len(diff_df)} significant peaks found.",
                "num_differential": len(diff_df),
                "increased_accessibility": len(diff_df[diff_df['accessibility_change'] == 'increased']),
                "decreased_accessibility": len(diff_df[diff_df['accessibility_change'] == 'decreased'])
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Differential analysis failed: {str(e)}"
            }
    
    async def _analyze_motifs(self, motif_database: str = "JASPAR2022", 
                            background_regions: str = "genome") -> Dict[str, Any]:
        """Perform motif enrichment analysis"""
        try:
            # Simulate motif analysis
            tf_families = ['AP-1', 'NF-κB', 'STAT', 'ETS', 'bHLH', 'Homeodomain', 'GATA']
            num_enriched = np.random.randint(20, 100)
            
            motif_results = {
                'motif_id': [f'motif_{i}' for i in range(num_enriched)],
                'tf_family': np.random.choice(tf_families, num_enriched),
                'enrichment_score': np.random.exponential(2, num_enriched),
                'p_value': np.random.beta(0.05, 10, num_enriched),
                'target_genes': [np.random.randint(10, 200) for _ in range(num_enriched)]
            }
            
            motif_df = pd.DataFrame(motif_results)
            
            # Store in session state
            st.session_state["motif_enrichment_results"] = motif_df
            
            return {
                "success": True,
                "message": f"Motif enrichment analysis completed. {num_enriched} enriched motifs found.",
                "num_enriched": num_enriched,
                "top_tf_families": motif_df.groupby('tf_family').size().sort_values(ascending=False).head().to_dict(),
                "database_used": motif_database
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Motif analysis failed: {str(e)}"
            }
    
    async def _run_chromvar(self, motif_set: str = "JASPAR2022") -> Dict[str, Any]:
        """Run ChromVAR analysis"""
        try:
            # Simulate ChromVAR results
            num_samples = np.random.randint(10, 50)
            num_motifs = np.random.randint(100, 500)
            
            chromvar_scores = np.random.normal(0, 1, (num_samples, num_motifs))
            
            # Store in session state
            st.session_state["chromvar_results"] = {
                'deviation_scores': chromvar_scores,
                'motif_set': motif_set,
                'num_samples': num_samples,
                'num_motifs': num_motifs
            }
            
            return {
                "success": True,
                "message": f"ChromVAR analysis completed for {num_samples} samples and {num_motifs} motifs",
                "num_samples": num_samples,
                "num_motifs": num_motifs
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"ChromVAR analysis failed: {str(e)}"
            }
    
    async def _perform_footprinting(self, motif_list: Optional[List[str]] = None) -> Dict[str, Any]:
        """Perform transcription factor footprinting"""
        try:
            if motif_list is None:
                motif_list = ['CTCF', 'AP1', 'NFKB1', 'STAT1']
            
            # Simulate footprinting results
            footprint_results = {}
            for motif in motif_list:
                footprint_results[motif] = {
                    'footprint_score': np.random.uniform(0.5, 2.0),
                    'protection_score': np.random.uniform(0.1, 0.8),
                    'num_sites': np.random.randint(100, 1000)
                }
            
            # Store in session state
            st.session_state["footprinting_results"] = footprint_results
            
            return {
                "success": True,
                "message": f"Footprinting analysis completed for {len(motif_list)} motifs",
                "analyzed_motifs": motif_list,
                "results_summary": footprint_results
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Footprinting analysis failed: {str(e)}"
            }
    
    def _get_server_specific_context(self) -> Dict[str, Any]:
        """Get ATAC-seq specific context"""
        context = {
            "analysis_type": "atacseq",
            "data_uploaded": self._check_data_availability(),
            "pipeline_status": {}
        }
        
        # Check analysis progress
        if "atacseq_peaks_df" in st.session_state:
            peaks_df = st.session_state["atacseq_peaks_df"]
            context["data_summary"] = {
                "total_peaks": len(peaks_df),
                "genome_coverage": f"{len(peaks_df) * 500 / 1e6:.1f} Mb"  # Rough estimate
            }
        
        if "differential_peaks" in st.session_state:
            diff_df = st.session_state["differential_peaks"]
            context["pipeline_status"]["differential_completed"] = True
            context["pipeline_status"]["significant_peaks"] = len(diff_df)
        
        if "motif_enrichment_results" in st.session_state:
            context["pipeline_status"]["motif_analysis_completed"] = True
        
        if "tss_enrichment_scores" in st.session_state:
            tss_score = st.session_state["tss_enrichment_scores"]
            context["qc_status"] = {
                "tss_enrichment": tss_score,
                "quality_assessment": "Good" if tss_score > 7 else "Poor"
            }
        
        return context
    
    def get_pipeline_context(self) -> Dict[str, Any]:
        """Get ATAC-seq pipeline context"""
        steps = [
            "Data Upload", "QC Metrics", "Peak Calling", 
            "Differential Accessibility", "Motif Analysis", 
            "ChromVAR", "Footprinting"
        ]
        
        completed_steps = []
        if st.session_state.get("qc_metrics_calculated", False):
            completed_steps.append("QC Metrics")
        if st.session_state.get("peaks_called", False):
            completed_steps.append("Peak Calling")
        if "differential_peaks" in st.session_state:
            completed_steps.append("Differential Accessibility")
        if "motif_enrichment_results" in st.session_state:
            completed_steps.append("Motif Analysis")
        if "chromvar_results" in st.session_state:
            completed_steps.append("ChromVAR")
        if "footprinting_results" in st.session_state:
            completed_steps.append("Footprinting")
        
        current_step = None
        next_step = None
        
        if not completed_steps:
            current_step = "Data Upload"
            next_step = "QC Metrics"
        elif len(completed_steps) < len(steps):
            current_step = completed_steps[-1]
            remaining_steps = [s for s in steps if s not in completed_steps]
            next_step = remaining_steps[0] if remaining_steps else None
        
        return {
            "current_step": current_step,
            "next_step": next_step,
            "completed_steps": completed_steps,
            "available_steps": steps,
            "pipeline_description": "ATAC-seq chromatin accessibility analysis pipeline"
        }
    
    def get_analysis_insights(self) -> str:
        """Get current ATAC-seq analysis insights"""
        insights = []
        
        if "tss_enrichment_scores" in st.session_state:
            tss_score = st.session_state["tss_enrichment_scores"]
            if tss_score > 7:
                insights.append(f"Good data quality with TSS enrichment of {tss_score:.1f}")
            else:
                insights.append(f"Poor data quality - TSS enrichment only {tss_score:.1f} (should be >7)")
        
        if "atacseq_peaks_df" in st.session_state:
            num_peaks = len(st.session_state["atacseq_peaks_df"])
            insights.append(f"Identified {num_peaks:,} accessible chromatin regions")
        
        if "differential_peaks" in st.session_state:
            num_diff = len(st.session_state["differential_peaks"])
            insights.append(f"Found {num_diff:,} differentially accessible regions between conditions")
        
        if "motif_enrichment_results" in st.session_state:
            motif_df = st.session_state["motif_enrichment_results"]
            top_family = motif_df.groupby('tf_family').size().idxmax()
            insights.append(f"Most enriched TF family: {top_family}")
        
        return "; ".join(insights) if insights else "No analysis insights available yet"
    
    def get_suggested_actions(self) -> List[str]:
        """Get suggested next actions for ATAC-seq analysis"""
        suggestions = []
        
        if not self._check_data_availability():
            suggestions.append("Upload ATAC-seq peak data or fragment files")
        
        if not st.session_state.get("qc_metrics_calculated", False):
            suggestions.append("Calculate QC metrics (TSS enrichment, nucleosome signal)")
        
        if not st.session_state.get("peaks_called", False):
            suggestions.append("Call accessible chromatin peaks")
        
        if "differential_peaks" not in st.session_state:
            suggestions.append("Perform differential accessibility analysis")
        
        if "motif_enrichment_results" not in st.session_state:
            suggestions.append("Run motif enrichment analysis")
        
        if "chromvar_results" not in st.session_state:
            suggestions.append("Perform ChromVAR analysis for TF activity")
        
        if "footprinting_results" not in st.session_state:
            suggestions.append("Run transcription factor footprinting")
        
        return suggestions[:3]  # Return top 3 suggestions 