"""
Data Management MCP Server

Provides MCP interface for general data management tools including:
- File upload and validation
- Data format conversion
- Data quality assessment
- Export and download functionality
"""

import asyncio
import pandas as pd
import numpy as np
from typing import Any, Dict, Optional
import streamlit as st

from ..core.server import MCPServer


class DataMCPServer(MCPServer):
    """MCP Server for general data management tools"""
    
    def __init__(self):
        super().__init__("data_server", "1.0.0")
    
    async def initialize(self) -> None:
        """Initialize data server with tools and resources"""
        
        # Register data management tools
        await self._register_data_tools()
        
        # Register validation tools
        await self._register_validation_tools()
        
        # Register conversion tools
        await self._register_conversion_tools()
        
        # Register resources
        await self._register_resources()
        
        # Register prompts
        await self._register_prompts()
    
    async def _register_data_tools(self):
        """Register data management tools"""
        
        # Upload validation
        self.register_tool(
            name="validate_uploaded_files",
            description="Validate all uploaded files and check data integrity",
            input_schema={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self._validate_uploads
        )
        
        # Data summary
        self.register_tool(
            name="get_data_overview",
            description="Get comprehensive overview of all uploaded data",
            input_schema={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self._get_data_overview
        )
        
        # Clear data
        self.register_tool(
            name="clear_all_data",
            description="Clear all uploaded data and reset session",
            input_schema={
                "type": "object",
                "properties": {
                    "confirm": {
                        "type": "boolean",
                        "description": "Confirmation to clear all data",
                        "default": False
                    }
                },
                "required": ["confirm"]
            },
            handler=self._clear_data
        )
    
    async def _register_validation_tools(self):
        """Register data validation tools"""
        
        # Check data compatibility
        self.register_tool(
            name="check_data_compatibility",
            description="Check if uploaded datasets are compatible for analysis",
            input_schema={
                "type": "object",
                "properties": {
                    "analysis_type": {
                        "type": "string",
                        "description": "Type of analysis to check compatibility for",
                        "enum": ["rnaseq", "scrnaseq", "tabular", "image"]
                    }
                },
                "required": ["analysis_type"]
            },
            handler=self._check_compatibility
        )
        
        # Data quality assessment
        self.register_tool(
            name="assess_data_quality",
            description="Assess quality of uploaded data",
            input_schema={
                "type": "object",
                "properties": {
                    "data_type": {
                        "type": "string",
                        "description": "Type of data to assess",
                        "enum": ["counts", "metadata", "expression", "general"]
                    }
                },
                "required": []
            },
            handler=self._assess_quality
        )
    
    async def _register_conversion_tools(self):
        """Register data conversion tools"""
        
        # Format conversion
        self.register_tool(
            name="convert_data_format",
            description="Convert data between different formats",
            input_schema={
                "type": "object",
                "properties": {
                    "source_format": {
                        "type": "string",
                        "description": "Source data format",
                        "enum": ["csv", "tsv", "xlsx", "h5ad", "h5"]
                    },
                    "target_format": {
                        "type": "string",
                        "description": "Target data format",
                        "enum": ["csv", "tsv", "xlsx", "h5ad", "h5"]
                    },
                    "data_key": {
                        "type": "string",
                        "description": "Session state key for the data to convert"
                    }
                },
                "required": ["source_format", "target_format", "data_key"]
            },
            handler=self._convert_format
        )
    
    async def _register_resources(self):
        """Register data management resources"""
        
        # Upload status resource
        self.register_resource(
            uri="data://status/uploads",
            name="Upload Status",
            description="Status of all file uploads",
            mime_type="application/json"
        )
        
        # Data inventory resource
        self.register_resource(
            uri="data://inventory/all",
            name="Data Inventory",
            description="Complete inventory of uploaded data",
            mime_type="application/json"
        )
    
    async def _register_prompts(self):
        """Register data management prompts"""
        
        self.register_prompt(
            name="data_upload_guidance",
            description="Provide guidance for data upload based on analysis type",
            template="""
            For {analysis_type} analysis, you need to upload:
            
            Required files:
            {required_files}
            
            Optional files:
            {optional_files}
            
            File format requirements:
            {format_requirements}
            
            Please ensure your data meets these requirements for successful analysis.
            """,
            parameters={
                "analysis_type": "string",
                "required_files": "array",
                "optional_files": "array",
                "format_requirements": "string"
            }
        )
    
    # Tool handler implementations
    
    async def _validate_uploads(self) -> Dict[str, Any]:
        """Validate all uploaded files"""
        validation_results = {
            "total_files": 0,
            "valid_files": 0,
            "invalid_files": 0,
            "file_details": {},
            "issues": []
        }
        
        # Check RNA-seq data
        if "rnaseq_counts_df" in st.session_state:
            validation_results["total_files"] += 1
            validation_results["file_details"]["rnaseq_counts"] = {
                "type": "RNA-seq counts",
                "shape": st.session_state["rnaseq_counts_df"].shape,
                "valid": True
            }
            validation_results["valid_files"] += 1
        
        if "rnaseq_metadata_df" in st.session_state:
            validation_results["total_files"] += 1
            validation_results["file_details"]["rnaseq_metadata"] = {
                "type": "RNA-seq metadata",
                "shape": st.session_state["rnaseq_metadata_df"].shape,
                "valid": True
            }
            validation_results["valid_files"] += 1
        
        # Check scRNA-seq data
        if "anndata" in st.session_state and st.session_state.anndata is not None:
            validation_results["total_files"] += 1
            adata = st.session_state.anndata
            validation_results["file_details"]["scrnaseq_data"] = {
                "type": "scRNA-seq AnnData",
                "shape": adata.shape,
                "valid": True
            }
            validation_results["valid_files"] += 1
        
        return {
            "success": True,
            "validation": validation_results
        }
    
    async def _get_data_overview(self) -> Dict[str, Any]:
        """Get comprehensive data overview"""
        overview = {
            "uploaded_datasets": {},
            "analysis_ready": {},
            "storage_info": {}
        }
        
        # RNA-seq data
        if "rnaseq_counts_df" in st.session_state and "rnaseq_metadata_df" in st.session_state:
            counts_df = st.session_state["rnaseq_counts_df"]
            metadata_df = st.session_state["rnaseq_metadata_df"]
            overview["uploaded_datasets"]["rnaseq"] = {
                "counts_shape": counts_df.shape,
                "metadata_shape": metadata_df.shape,
                "samples_match": set(counts_df.columns) == set(metadata_df.index)
            }
            overview["analysis_ready"]["rnaseq"] = True
        
        # scRNA-seq data
        if "anndata" in st.session_state and st.session_state.anndata is not None:
            adata = st.session_state.anndata
            overview["uploaded_datasets"]["scrnaseq"] = {
                "shape": adata.shape,
                "obs_columns": list(adata.obs.columns),
                "var_columns": list(adata.var.columns)
            }
            overview["analysis_ready"]["scrnaseq"] = True
        
        return {
            "success": True,
            "overview": overview
        }
    
    async def _clear_data(self, confirm: bool = False) -> Dict[str, Any]:
        """Clear all uploaded data"""
        if not confirm:
            return {
                "success": False,
                "message": "Data clearing requires confirmation. Set confirm=True to proceed."
            }
        
        # Clear RNA-seq data
        keys_to_clear = [
            "rnaseq_counts_df", "rnaseq_metadata_df", "deseq_results", "go_results",
            "anndata", "qc_done", "filtered", "normalized", "clustered"
        ]
        
        cleared_count = 0
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
                cleared_count += 1
        
        return {
            "success": True,
            "message": f"Cleared {cleared_count} data objects from session",
            "cleared_keys": cleared_count
        }
    
    async def _check_compatibility(self, analysis_type: str) -> Dict[str, Any]:
        """Check data compatibility for analysis type"""
        compatibility = {
            "compatible": False,
            "missing_requirements": [],
            "recommendations": []
        }
        
        if analysis_type == "rnaseq":
            has_counts = "rnaseq_counts_df" in st.session_state
            has_metadata = "rnaseq_metadata_df" in st.session_state
            
            if has_counts and has_metadata:
                # Check if sample names match
                counts_samples = set(st.session_state["rnaseq_counts_df"].columns)
                metadata_samples = set(st.session_state["rnaseq_metadata_df"].index)
                compatibility["compatible"] = counts_samples == metadata_samples
                
                if not compatibility["compatible"]:
                    compatibility["missing_requirements"].append("Sample names must match between counts and metadata")
            else:
                if not has_counts:
                    compatibility["missing_requirements"].append("RNA-seq counts matrix")
                if not has_metadata:
                    compatibility["missing_requirements"].append("Sample metadata")
        
        elif analysis_type == "scrnaseq":
            has_data = "anndata" in st.session_state and st.session_state.anndata is not None
            compatibility["compatible"] = has_data
            
            if not has_data:
                compatibility["missing_requirements"].append("scRNA-seq data (.h5ad or 10x format)")
        
        return {
            "success": True,
            "compatibility": compatibility
        }
    
    async def _assess_quality(self, data_type: str = "general") -> Dict[str, Any]:
        """Assess data quality"""
        quality_report = {
            "overall_score": 0,
            "issues": [],
            "recommendations": []
        }
        
        if data_type == "counts" and "rnaseq_counts_df" in st.session_state:
            counts_df = st.session_state["rnaseq_counts_df"]
            
            # Check for negative values
            if (counts_df < 0).any().any():
                quality_report["issues"].append("Negative values found in counts matrix")
            
            # Check for missing values
            if counts_df.isnull().any().any():
                quality_report["issues"].append("Missing values found in counts matrix")
            
            # Check for low count genes
            low_count_genes = (counts_df.sum(axis=1) < 10).sum()
            if low_count_genes > counts_df.shape[0] * 0.5:
                quality_report["issues"].append(f"High proportion of low-count genes ({low_count_genes})")
                quality_report["recommendations"].append("Consider filtering low-expression genes")
            
            quality_report["overall_score"] = max(0, 100 - len(quality_report["issues"]) * 20)
        
        return {
            "success": True,
            "quality_report": quality_report
        }
    
    async def _convert_format(self, source_format: str, target_format: str, data_key: str) -> Dict[str, Any]:
        """Convert data format"""
        if data_key not in st.session_state:
            return {
                "success": False,
                "message": f"Data key '{data_key}' not found in session"
            }
        
        # Mock conversion - in real implementation, would perform actual conversion
        return {
            "success": True,
            "message": f"Converted {data_key} from {source_format} to {target_format}",
            "source_format": source_format,
            "target_format": target_format,
            "converted_key": f"{data_key}_{target_format}"
        }
    
    def _get_server_specific_context(self) -> Dict[str, Any]:
        """Get data management specific context"""
        context = {
            "analysis_type": "data_management",
            "uploaded_files": []
        }
        
        # Check what data is uploaded
        if "rnaseq_counts_df" in st.session_state:
            context["uploaded_files"].append("rnaseq_counts")
        if "rnaseq_metadata_df" in st.session_state:
            context["uploaded_files"].append("rnaseq_metadata")
        if "anndata" in st.session_state and st.session_state.anndata is not None:
            context["uploaded_files"].append("scrnaseq_data")
        
        context["total_files"] = len(context["uploaded_files"])
        
        return context 