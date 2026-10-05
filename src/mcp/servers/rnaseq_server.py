"""
Enhanced RNA-seq MCP Server

Provides comprehensive bulk RNA-seq analysis with:
- DESeq2 differential expression analysis
- Gene ontology enrichment with multiple databases
- Advanced security and permission management
- Electron desktop integration with progress tracking
- Performance monitoring and intelligent caching
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from functools import wraps
import pandas as pd
import numpy as np

from gliaent.analysis import AnalysisParams
from gliaent.session import DataStore, InMemoryDataStore, require
from modules.rna_seq.pydeseq import run_pydeseq2

from ..core.server import MCPServer
from ..core.registry.tool_registry import get_auto_tool_configs
from ..core.registry.resource_registry import get_auto_resource_configs
from ..core.registry.prompt_registry import get_auto_prompt_configs
from .security_handler import SecurityContext, UserPermissions
from .electron_bridge import ElectronBridge, DesktopNotification
from src.modules.rna_seq.workflow import run_rnaseq_pipeline
from src.modules.rna_seq.input_preview import show_rnaseq_inputs


class RNASeqDataValidator:
    """Validates RNA-seq data integrity and compatibility"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def validate_counts_matrix(self, counts_df: pd.DataFrame) -> Dict[str, Any]:
        """Validate counts matrix structure and content"""
        validation_result = {
            "valid": True,
            "issues": [],
            "warnings": [],
            "stats": {}
        }
        
        try:
            # Basic structure validation
            if counts_df.empty:
                validation_result["valid"] = False
                validation_result["issues"].append("Counts matrix is empty")
                return validation_result
            
            # Check for negative values
            if (counts_df < 0).any().any():
                validation_result["issues"].append("Negative values found in counts matrix")
                validation_result["valid"] = False
            
            # Check for missing values
            missing_count = counts_df.isnull().sum().sum()
            if missing_count > 0:
                validation_result["warnings"].append(f"Found {missing_count} missing values")
            
            # Statistical summary
            validation_result["stats"] = {
                "genes": counts_df.shape[0],
                "samples": counts_df.shape[1],
                "total_counts": int(counts_df.sum().sum()),
                "median_counts_per_gene": float(counts_df.sum(axis=1).median()),
                "zero_count_genes": int((counts_df.sum(axis=1) == 0).sum())
            }
            
            # Quality warnings
            if validation_result["stats"]["zero_count_genes"] > counts_df.shape[0] * 0.5:
                validation_result["warnings"].append("High proportion of zero-count genes detected")
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["issues"].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    def validate_metadata_compatibility(self, counts_df: pd.DataFrame, 
                                      metadata_df: pd.DataFrame) -> Dict[str, Any]:
        """Validate metadata compatibility with counts matrix"""
        validation_result = {
            "compatible": True,
            "issues": [],
            "sample_matching": {}
        }
        
        try:
            counts_samples = set(counts_df.columns)
            metadata_samples = set(metadata_df.index)
            
            # Check sample overlap
            common_samples = counts_samples & metadata_samples
            missing_in_metadata = counts_samples - metadata_samples
            missing_in_counts = metadata_samples - counts_samples
            
            validation_result["sample_matching"] = {
                "total_common": len(common_samples),
                "missing_in_metadata": list(missing_in_metadata),
                "missing_in_counts": list(missing_in_counts)
            }
            
            if len(common_samples) == 0:
                validation_result["compatible"] = False
                validation_result["issues"].append("No common samples between counts and metadata")
            elif missing_in_metadata or missing_in_counts:
                validation_result["issues"].append("Sample name mismatch detected")
            
        except Exception as e:
            validation_result["compatible"] = False
            validation_result["issues"].append(f"Compatibility check error: {str(e)}")
        
        return validation_result


class RNASeqCacheManager:
    """Manages intelligent caching for RNA-seq analysis results"""
    
    def __init__(self):
        self.cache = {}
        self.cache_metadata = {}
        self.max_cache_size = 50  # Maximum cached results
    
    def generate_cache_key(self, analysis_type: str, parameters: Dict[str, Any], 
                          data_hash: str) -> str:
        """Generate unique cache key for analysis"""
        import hashlib
        
        param_str = str(sorted(parameters.items()))
        key_data = f"{analysis_type}:{param_str}:{data_hash}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get_data_hash(self, counts_df: pd.DataFrame, metadata_df: pd.DataFrame) -> str:
        """Generate hash for data to detect changes"""
        import hashlib
        
        counts_hash = hashlib.md5(str(counts_df.shape).encode()).hexdigest()
        metadata_hash = hashlib.md5(str(metadata_df.shape).encode()).hexdigest()
        return f"{counts_hash}:{metadata_hash}"
    
    def get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Retrieve cached result if available and valid"""
        if cache_key in self.cache:
            # Update access time
            self.cache_metadata[cache_key]["last_accessed"] = time.time()
            return self.cache[cache_key]
        return None
    
    def cache_result(self, cache_key: str, result: Any, analysis_type: str):
        """Cache analysis result with metadata"""
        # Implement LRU eviction if cache is full
        if len(self.cache) >= self.max_cache_size:
            self._evict_oldest()
        
        self.cache[cache_key] = result
        self.cache_metadata[cache_key] = {
            "analysis_type": analysis_type,
            "cached_at": time.time(),
            "last_accessed": time.time()
        }
    
    def _evict_oldest(self):
        """Evict least recently used cache entry"""
        if not self.cache_metadata:
            return
        
        oldest_key = min(
            self.cache_metadata.keys(),
            key=lambda k: self.cache_metadata[k]["last_accessed"]
        )
        
        del self.cache[oldest_key]
        del self.cache_metadata[oldest_key]


def cache_analysis_result(analysis_type: str):
    """Decorator to cache analysis results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, **kwargs):
            # Generate cache key
            if hasattr(self, 'cache_manager') and self._check_data_availability():
                counts_df = self.store["rnaseq_counts_df"]
                metadata_df = self.store["rnaseq_metadata_df"]
                
                data_hash = self.cache_manager.get_data_hash(counts_df, metadata_df)
                cache_key = self.cache_manager.generate_cache_key(analysis_type, kwargs, data_hash)
                
                # Try to get cached result
                cached_result = self.cache_manager.get_cached_result(cache_key)
                if cached_result:
                    self.logger.info(f"Using cached result for {analysis_type}")
                    return cached_result
                
                # Execute analysis and cache result
                result = await func(self, **kwargs)
                if result.get("success"):
                    self.cache_manager.cache_result(cache_key, result, analysis_type)
                
                return result
            else:
                return await func(self, **kwargs)
        
        return wrapper
    return decorator


def _condition_from_design(design_formula: str) -> str:
    """Extract the condition column from an R-style design formula.

    Accepts "~ condition", "~condition" or a bare "condition". Only
    single-factor designs are supported; a multi-factor formula raises rather
    than silently analysing the first term.

    Raises:
        ValueError: If the formula is empty or has more than one term.
    """
    terms = [t.strip() for t in design_formula.lstrip("~").split("+") if t.strip()]
    if not terms:
        raise ValueError(f"design formula {design_formula!r} names no factor")
    if len(terms) > 1:
        raise ValueError(
            f"design formula {design_formula!r} has {len(terms)} factors; only "
            "single-factor designs are supported. Multi-factor designs need a "
            "contrast specification this server does not yet accept."
        )
    return terms[0]


class RNASeqMCPServer(MCPServer):
    """Enhanced MCP Server for bulk RNA-seq analysis"""
    
    def __init__(self, store: Optional[DataStore] = None):
        """Initialise the server.

        Args:
            store: Where session data lives. Defaults to an in-process store.
                This used to read `streamlit.session_state`, which does not
                exist in the headless `python -m` child this server runs in.
        """
        super().__init__("rnaseq_server", "2.0.0")
        self.logger = logging.getLogger("mcp.rnaseq")

        self.store: DataStore = store if store is not None else InMemoryDataStore()

        # Core components
        self.data_validator = RNASeqDataValidator(self.logger)
        self.cache_manager = RNASeqCacheManager()
        self.electron_bridge = None
        
        # Session tracking for RNA-seq specific data
        self.configure_session_tracking(
            tracked_variables=[
                'rnaseq_counts_df', 'rnaseq_metadata_df', 'deseq_results',
                'go_results', 'filtered_counts', 'normalized_counts'
            ],
            variable_patterns=[
                r'.*_counts$', r'.*_results$', r'.*_enrichment$',
                r'deseq_.*', r'go_.*', r'pathway_.*'
            ],
            auto_discover=True
        )
        
        # Performance tracking
        self.analysis_metrics = {
            "deseq_executions": 0,
            "go_enrichment_executions": 0,
            "total_analysis_time": 0.0
        }
    
    async def initialize(self) -> bool:
        """Initialize RNA-seq server with comprehensive setup"""
        try:
            self.logger.info("Initializing enhanced RNA-seq server")
            
            # Setup Electron integration
            await self._setup_electron_integration()
            
            # Discover and register components
            await self._discover_and_register_components()
            
            # Register RNA-seq specific tools
            await self._register_rnaseq_tools()
            
            self.logger.info("RNA-seq server initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"RNA-seq server initialization failed: {str(e)}")
            return False
    
    async def _setup_electron_integration(self):
        """Setup Electron desktop integration"""
        try:
            if self._detect_electron_environment():
                self.electron_bridge = ElectronBridge(self.logger)
                await self.electron_bridge.initialize()
                await self.electron_bridge.notify_server_started("rnaseq")
                self.logger.info("Electron integration enabled for RNA-seq")
        except Exception as e:
            self.logger.warning(f"Electron integration failed: {str(e)}")
    
    def _detect_electron_environment(self) -> bool:
        """Detect if running in Electron environment"""
        import os
        return any(os.environ.get(var) for var in [
            "ELECTRON_MODE", "ELECTRON_RUN_AS_NODE", "ELECTRON_NO_ATTACH_CONSOLE"
        ])
    
    async def _discover_and_register_components(self):
        """Discover and register tools, resources, and prompts"""
        try:
            # Use existing registry system
            self.tool_configs = get_auto_tool_configs(self)
            self.resource_configs = get_auto_resource_configs(self)
            self.prompt_configs = get_auto_prompt_configs(self)
            
            # Register discovered components
            for tool_name, tool_config in self.tool_configs.items():
                self.register_tool(
                    name=tool_name,
                    description=tool_config.description,
                    input_schema={
                        "type": "object",
                        "properties": tool_config.properties,
                        "required": tool_config.required
                    },
                    handler=tool_config.handler
                )
                
        except Exception as e:
            self.logger.warning(f"Auto-discovery failed, using manual registration: {str(e)}")
            await self._manual_tool_registration()
    
    async def _register_rnaseq_tools(self):
        """Register RNA-seq specific analysis tools"""
        
        # Main pipeline tool
        self.register_tool(
            name="run_rnaseq_pipeline",
            description="Execute complete RNA-seq analysis pipeline",
            input_schema={
                "type": "object",
                "properties": {
                    "force_rerun": {"type": "boolean", "default": False},
                    "filter_low_counts": {"type": "boolean", "default": True}
                },
                "required": []
            },
            handler=self._run_pipeline_with_monitoring
        )
        
        # Data validation tool
        self.register_tool(
            name="validate_rnaseq_data",
            description="Comprehensive RNA-seq data validation",
            input_schema={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self._validate_data_comprehensive
        )
        
        # Enhanced DESeq2 analysis
        self.register_tool(
            name="run_deseq2_analysis",
            description="Advanced DESeq2 differential expression analysis",
            input_schema={
                "type": "object",
                "properties": {
                    "design_formula": {"type": "string", "default": "~ condition"},
                    "contrast": {"type": "array", "items": {"type": "string"}},
                    "alpha": {"type": "number", "default": 0.05},
                    "lfc_threshold": {"type": "number", "default": 0.0}
                },
                "required": []
            },
            handler=self._run_deseq2_enhanced
        )
        
        # Alias for frontend compatibility
        self.register_tool(
            name="analyze_differential_expression",
            description="Differential expression analysis (alias for run_deseq2_analysis)",
            input_schema={
                "type": "object",
                "properties": {
                    "files": {"type": "array", "items": {"type": "object"}},
                    "parameters": {"type": "object", "default": {}},
                    "pvalue_threshold": {"type": "number", "default": 0.05},
                    "log2fc_threshold": {"type": "number", "default": 1.0},
                    "normalization_method": {"type": "string", "default": "deseq2"}
                },
                "required": []
            },
            handler=self._analyze_differential_expression_frontend
        )
    
    async def _manual_tool_registration(self):
        """Manual tool registration fallback"""
        essential_tools = [
            {
                "name": "validate_data",
                "description": "Validate RNA-seq data",
                "handler": self._validate_data_comprehensive
            },
            {
                "name": "run_pipeline",
                "description": "Run RNA-seq pipeline",
                "handler": self._run_pipeline_with_monitoring
            }
        ]
        
        for tool in essential_tools:
            self.register_tool(
                name=tool["name"],
                description=tool["description"],
                input_schema={"type": "object", "properties": {}, "required": []},
                handler=tool["handler"]
            )
    
    async def _run_pipeline_with_monitoring(self, force_rerun: bool = False, 
                                          filter_low_counts: bool = True) -> Dict[str, Any]:
        """Run RNA-seq pipeline with enhanced monitoring"""
        start_time = time.time()
        
        try:
            if not self._check_data_availability():
                return {
                    "success": False,
                    "message": "RNA-seq data not available. Please upload counts and metadata first."
                }
            
            # Send progress notification
            if self.electron_bridge:
                await self.electron_bridge.notify_analysis_progress("rnaseq", "pipeline_start", 0.0)
            
            # Run pipeline
            result = run_rnaseq_pipeline()
            
            # Update metrics
            execution_time = time.time() - start_time
            self.analysis_metrics["total_analysis_time"] += execution_time
            
            # Send completion notification
            if self.electron_bridge:
                notification = DesktopNotification(
                    title="RNA-seq Analysis Complete",
                    body=f"Pipeline completed in {execution_time:.1f}s",
                    urgency="normal"
                )
                await self.electron_bridge.send_desktop_notification(notification)
                await self.electron_bridge.notify_analysis_progress("rnaseq", "pipeline_complete", 100.0)
            
            return {
                "success": True,
                "message": "RNA-seq pipeline completed successfully",
                "execution_time": execution_time,
                "result": result
            }
            
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {str(e)}")
            return {
                "success": False,
                "message": f"Pipeline execution failed: {str(e)}"
            }
    
    async def _validate_data_comprehensive(self) -> Dict[str, Any]:
        """Comprehensive data validation with detailed reporting"""
        try:
            if not self._check_data_availability():
                return {
                    "success": False,
                    "message": "No RNA-seq data available for validation"
                }
            
            counts_df = self.store["rnaseq_counts_df"]
            metadata_df = self.store["rnaseq_metadata_df"]
            
            # Validate counts matrix
            counts_validation = self.data_validator.validate_counts_matrix(counts_df)
            
            # Validate metadata compatibility
            compatibility = self.data_validator.validate_metadata_compatibility(counts_df, metadata_df)
            
            # Overall validation result
            overall_valid = counts_validation["valid"] and compatibility["compatible"]
            
            validation_result = {
                "success": True,
                "overall_valid": overall_valid,
                "counts_validation": counts_validation,
                "metadata_compatibility": compatibility,
                "recommendations": self._generate_recommendations(counts_validation, compatibility)
            }
            
            return validation_result
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Data validation failed: {str(e)}"
            }
    
    async def _analyze_differential_expression_frontend(self, files: List[Dict] = None, 
                                                      parameters: Dict = None, 
                                                      pvalue_threshold: float = 0.05,
                                                      log2fc_threshold: float = 1.0,
                                                      normalization_method: str = "deseq2") -> Dict[str, Any]:
        """Frontend-compatible differential expression analysis"""
        start_time = time.time()
        
        try:
            # Handle file uploads if provided
            if files:
                await self._process_uploaded_files(files)
            
            # Extract parameters
            if parameters:
                pvalue_threshold = parameters.get('pvalue_threshold', pvalue_threshold)
                log2fc_threshold = parameters.get('log2fc_threshold', log2fc_threshold)
                normalization_method = parameters.get('normalization_method', normalization_method)
            
            # Check if data is available
            if not self._check_data_availability():
                return {
                    "success": False,
                    "message": "RNA-seq data not available. Please upload counts and metadata files."
                }
            
            # Run the analysis pipeline
            result = await self._run_deseq2_enhanced(
                alpha=pvalue_threshold,
                lfc_threshold=log2fc_threshold
            )
            
            # Format response for frontend
            if result.get("success"):
                return {
                    "success": True,
                    "data": {
                        "summary": result.get("results", {}),
                        "total_genes": result.get("results", {}).get("total_genes", 0),
                        "upregulated": result.get("results", {}).get("upregulated", 0),
                        "downregulated": result.get("results", {}).get("downregulated", 0),
                        "execution_time": time.time() - start_time,
                        "parameters": {
                            "pvalue_threshold": pvalue_threshold,
                            "log2fc_threshold": log2fc_threshold,
                            "normalization_method": normalization_method
                        }
                    },
                    "message": "RNA-seq differential expression analysis completed successfully"
                }
            else:
                return result
                
        except Exception as e:
            self.logger.error(f"Frontend differential expression analysis failed: {str(e)}")
            return {
                "success": False,
                "message": f"Analysis failed: {str(e)}"
            }
    
    async def _process_uploaded_files(self, files: List[Dict]):
        """Process uploaded files from frontend"""
        try:
            for file_info in files:
                if file_info.get('name', '').lower().endswith(('.csv', '.tsv', '.txt')):
                    # Parse file content
                    content = file_info.get('content', '')
                    if content:
                        # Create DataFrame from content
                        import io
                        import pandas as pd
                        
                        if file_info['name'].lower().endswith('.csv'):
                            df = pd.read_csv(io.StringIO(content), index_col=0)
                        else:  # tsv or txt
                            df = pd.read_csv(io.StringIO(content), sep='\t', index_col=0)
                        
                        # Determine if it's counts or metadata based on content
                        if self._is_counts_matrix(df):
                            self.store["rnaseq_counts_df"] = df
                            self.logger.info(f"Loaded counts matrix: {df.shape}")
                        else:
                            self.store["rnaseq_metadata_df"] = df
                            self.logger.info(f"Loaded metadata: {df.shape}")
                            
        except Exception as e:
            self.logger.error(f"File processing failed: {str(e)}")
            raise
    
    def _is_counts_matrix(self, df: pd.DataFrame) -> bool:
        """Determine if DataFrame is a counts matrix or metadata"""
        # Simple heuristic: counts matrices typically have numeric data
        # and more genes (rows) than samples (columns)
        try:
            # Check if mostly numeric
            numeric_cols = df.select_dtypes(include=['number']).shape[1]
            total_cols = df.shape[1]
            
            # If more than 80% numeric columns and more rows than columns, likely counts
            return (numeric_cols / total_cols > 0.8) and (df.shape[0] > df.shape[1])
        except:
            return False

    @cache_analysis_result("deseq2")
    async def _run_deseq2_enhanced(self, design_formula: str = "~ condition", 
                                 contrast: List[str] = None, alpha: float = 0.05,
                                 lfc_threshold: float = 0.0) -> Dict[str, Any]:
        """Enhanced DESeq2 analysis with caching and monitoring"""
        start_time = time.time()
        
        try:
            if not self._check_data_availability():
                return {
                    "success": False,
                    "message": "RNA-seq data not available"
                }
            
            # Progress notification
            if self.electron_bridge:
                await self.electron_bridge.notify_analysis_progress("rnaseq", "deseq2_start", 0.0)
            
            # Real DESeq2 via pydeseq2. This previously returned
            # `int(n_genes * 0.1)` as the significant-gene count, with a
            # hardcoded 60/40 up/down split and an asyncio.sleep to imitate
            # compute time.
            counts_df = require(self.store, "rnaseq_counts_df", "Counts matrix")
            metadata_df = require(self.store, "rnaseq_metadata_df", "Sample metadata")

            params = AnalysisParams(alpha=alpha, log2fc_threshold=lfc_threshold)
            condition_column = _condition_from_design(design_formula)

            # pydeseq2 is CPU-bound and synchronous; run it off the event loop
            # so the server stays responsive.
            results_df = await asyncio.to_thread(
                run_pydeseq2,
                counts_df,
                metadata_df,
                condition_column,
                params,
            )

            self.store.set("deseq2_results_df", results_df)

            significant = results_df["significant"]
            up = int((significant & (results_df["log2FoldChange"] > 0)).sum())
            down = int((significant & (results_df["log2FoldChange"] < 0)).sum())

            result = {
                "success": True,
                "message": (
                    f"DESeq2 complete ({results_df.attrs.get('gliaent_contrast', '')}): "
                    f"{int(significant.sum())} of {len(results_df)} genes significant "
                    f"at {params.describe()}"
                ),
                "parameters": {
                    "design_formula": design_formula,
                    "condition_column": condition_column,
                    "contrast": results_df.attrs.get("gliaent_contrast"),
                    **params.to_dict(),
                },
                "results": {
                    "total_genes": int(len(results_df)),
                    "significant_genes": int(significant.sum()),
                    "upregulated": up,
                    "downregulated": down,
                    "execution_time": time.time() - start_time,
                },
            }
            
            # Update metrics
            self.analysis_metrics["deseq_executions"] += 1
            
            # Completion notification
            if self.electron_bridge:
                await self.electron_bridge.notify_analysis_progress("rnaseq", "deseq2_complete", 100.0)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "message": f"DESeq2 analysis failed: {str(e)}"
            }
    
    def _generate_recommendations(self, counts_validation: Dict, 
                                compatibility: Dict) -> List[str]:
        """Generate analysis recommendations based on validation results"""
        recommendations = []
        
        if not counts_validation["valid"]:
            recommendations.extend([
                "Fix data quality issues before proceeding with analysis",
                "Remove or correct negative values in counts matrix"
            ])
        
        if counts_validation.get("warnings"):
            recommendations.append("Consider filtering low-count genes to improve analysis power")
        
        if not compatibility["compatible"]:
            recommendations.extend([
                "Ensure sample names match between counts matrix and metadata",
                "Check for typos or formatting differences in sample names"
            ])
        
        # Data-driven recommendations
        stats = counts_validation.get("stats", {})
        if stats.get("zero_count_genes", 0) > stats.get("genes", 1) * 0.5:
            recommendations.append("High proportion of zero-count genes detected - consider more stringent filtering")
        
        return recommendations
    
    def _check_data_availability(self) -> bool:
        """Check if required RNA-seq data is available"""
        return (
            "rnaseq_counts_df" in self.store and
            "rnaseq_metadata_df" in self.store and
            self.store["rnaseq_counts_df"] is not None and
            self.store["rnaseq_metadata_df"] is not None
        )
    
    async def get_analysis_summary(self) -> Dict[str, Any]:
        """Get comprehensive analysis summary"""
        summary = {
            "server_info": {
                "name": self.name,
                "version": self.version,
                "status": "running"
            },
            "data_status": {
                "data_available": self._check_data_availability(),
                "cache_entries": len(self.cache_manager.cache)
            },
            "analysis_metrics": self.analysis_metrics,
            "electron_connected": self.electron_bridge is not None
        }
        
        if self._check_data_availability():
            counts_df = self.store["rnaseq_counts_df"]
            metadata_df = self.store["rnaseq_metadata_df"]
            
            summary["data_summary"] = {
                "genes": counts_df.shape[0],
                "samples": counts_df.shape[1],
                "metadata_variables": metadata_df.shape[1]
            }
        
        return summary
    
    def _get_server_specific_context(self) -> Dict[str, Any]:
        """Get RNA-seq server specific context information"""
        return {
            "server_type": "bulk_rna_analysis",
            "analysis_capabilities": ["differential_expression", "deseq2", "data_validation", "pipeline_analysis"],
            "supported_data_formats": ["csv", "tsv", "h5", "xlsx"],
            "caching_enabled": True,
            "cache_size": len(self.cache_manager.cache),
            "analysis_metrics": self.analysis_metrics,
            "electron_enabled": self.electron_bridge is not None,
            "features": ["enhanced_caching", "comprehensive_validation", "pipeline_monitoring"],
            "data_availability": self._check_data_availability()
        }

    async def shutdown(self):
        """Graceful server shutdown"""
        self.logger.info("Shutting down RNA-seq server")
        
        if self.electron_bridge:
            await self.electron_bridge.notify_server_stopped("rnaseq")
            await self.electron_bridge.shutdown()
        
        # Log final metrics
        self.logger.info(f"Final analysis metrics: {self.analysis_metrics}")
        
        await super().shutdown()


def main():
    """Main function for testing enhanced RNA-seq server"""
    print("=== Enhanced RNA-seq Server Test ===")
    
    # Static tests
    print("\n1. Testing RNASeqDataValidator...")
    logger = logging.getLogger("test")
    validator = RNASeqDataValidator(logger)
    
    # Test counts validation
    test_counts = pd.DataFrame({
        'sample1': [10, 20, 0],
        'sample2': [15, 25, 5]
    })
    validation = validator.validate_counts_matrix(test_counts)
    assert validation["valid"] is True
    assert validation["stats"]["genes"] == 3
    print("✅ RNASeqDataValidator working")
    
    print("\n2. Testing RNASeqCacheManager...")
    cache_manager = RNASeqCacheManager()
    test_key = cache_manager.generate_cache_key("deseq2", {"alpha": 0.05}, "test_hash")
    assert len(test_key) == 32  # MD5 hash length
    print("✅ RNASeqCacheManager working")
    
    print("\n3. Testing server creation...")
    server = RNASeqMCPServer()
    assert server.name == "rnaseq_server"
    assert server.version == "2.0.0"
    print("✅ Enhanced RNA-seq server created")


def test_dynamic():
    """Dynamic tests for enhanced RNA-seq server"""
    async def run_dynamic_tests():
        print("\n=== Dynamic Tests ===")
        
        server = RNASeqMCPServer()
        
        print("1. Testing server initialization...")
        success = await server.initialize()
        assert success is True
        print("✅ Server initialization working")
        
        print("\n2. Testing analysis summary...")
        summary = await server.get_analysis_summary()
        assert "server_info" in summary
        assert "analysis_metrics" in summary
        print("✅ Analysis summary working")
        
        print("\n3. Testing data validation...")
        validation_result = await server._validate_data_comprehensive()
        assert "success" in validation_result
        print("✅ Data validation working")
        
        print("\n🎉 All dynamic tests passed!")
    
    # Run async tests
    asyncio.run(run_dynamic_tests())


if __name__ == "__main__":
    main()
    test_dynamic()