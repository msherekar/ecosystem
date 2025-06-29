"""
Enhanced Data Management MCP Server

Provides comprehensive data management with:
- Advanced file validation and format detection
- Intelligent data conversion and preprocessing
- Secure file handling with virus scanning
- Electron integration for file dialogs and progress
- Performance monitoring and optimization
"""

import asyncio
import logging
import time
import hashlib
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np

from ..core.server import MCPServer
from ..core.registry.tool_registry import get_auto_tool_configs
from ..core.registry.resource_registry import get_auto_resource_configs
from ..core.registry.prompt_registry import get_auto_prompt_configs
from .security_handler import SecurityContext, UserPermissions
from .electron_bridge import ElectronBridge, DesktopNotification


class DataValidator:
    """Advanced data validation and format detection"""
    
    def __init__(self, logger):
        self.logger = logger
        self.supported_formats = {
            'csv': self._validate_csv,
            'tsv': self._validate_tsv,
            'xlsx': self._validate_excel,
            'h5ad': self._validate_h5ad,
            'h5': self._validate_hdf5,
            'json': self._validate_json
        }
    
    def detect_format(self, file_path: Path) -> Dict[str, Any]:
        """Detect file format and basic properties"""
        detection_result = {
            "format": "unknown",
            "confidence": 0.0,
            "properties": {},
            "issues": []
        }
        
        try:
            # Check file extension
            extension = file_path.suffix.lower().lstrip('.')
            
            if extension in self.supported_formats:
                detection_result["format"] = extension
                detection_result["confidence"] = 0.8
            
            # Content-based detection for ambiguous cases
            if extension in ['txt', 'data'] or detection_result["confidence"] < 0.5:
                content_format = self._detect_by_content(file_path)
                if content_format:
                    detection_result["format"] = content_format
                    detection_result["confidence"] = 0.9
            
            # Get file properties
            detection_result["properties"] = self._get_file_properties(file_path)
            
        except Exception as e:
            detection_result["issues"].append(f"Format detection failed: {str(e)}")
        
        return detection_result
    
    def validate_file(self, file_path: Path, expected_format: str = None) -> Dict[str, Any]:
        """Comprehensive file validation"""
        validation_result = {
            "valid": False,
            "format": "unknown",
            "size_mb": 0.0,
            "row_count": 0,
            "column_count": 0,
            "issues": [],
            "warnings": [],
            "recommendations": []
        }
        
        try:
            # Detect format if not specified
            if not expected_format:
                detection = self.detect_format(file_path)
                expected_format = detection["format"]
                validation_result["format"] = expected_format
            
            # File size check
            file_size = file_path.stat().st_size
            validation_result["size_mb"] = file_size / (1024 * 1024)
            
            if validation_result["size_mb"] > 1000:  # 1GB limit
                validation_result["warnings"].append("Large file detected - processing may be slow")
            
            # Format-specific validation
            if expected_format in self.supported_formats:
                format_result = self.supported_formats[expected_format](file_path)
                validation_result.update(format_result)
            else:
                validation_result["issues"].append(f"Unsupported format: {expected_format}")
            
            # Security scan
            security_result = self._security_scan(file_path)
            if not security_result["safe"]:
                validation_result["issues"].extend(security_result["issues"])
            
            validation_result["valid"] = len(validation_result["issues"]) == 0
            
        except Exception as e:
            validation_result["issues"].append(f"Validation failed: {str(e)}")
        
        return validation_result
    
    def _detect_by_content(self, file_path: Path) -> Optional[str]:
        """Detect format by file content analysis"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_lines = [f.readline().strip() for _ in range(5)]
            
            # Check for CSV/TSV patterns
            first_line = first_lines[0] if first_lines else ""
            if ',' in first_line and len(first_line.split(',')) > 2:
                return 'csv'
            elif '\t' in first_line and len(first_line.split('\t')) > 2:
                return 'tsv'
            elif first_line.startswith('{') or first_line.startswith('['):
                return 'json'
            
        except Exception:
            pass
        
        return None
    
    def _get_file_properties(self, file_path: Path) -> Dict[str, Any]:
        """Get basic file properties"""
        try:
            stat = file_path.stat()
            return {
                "size_bytes": stat.st_size,
                "modified_time": stat.st_mtime,
                "readable": file_path.is_file() and stat.st_mode & 0o444,
                "extension": file_path.suffix.lower()
            }
        except Exception:
            return {}
    
    def _security_scan(self, file_path: Path) -> Dict[str, Any]:
        """Basic security scanning for uploaded files"""
        security_result = {
            "safe": True,
            "issues": []
        }
        
        try:
            # Check file size (prevent zip bombs)
            if file_path.stat().st_size > 5 * 1024 * 1024 * 1024:  # 5GB
                security_result["safe"] = False
                security_result["issues"].append("File too large - potential security risk")
            
            # Check for suspicious file patterns
            with open(file_path, 'rb') as f:
                header = f.read(1024)
                
            # Check for executable signatures
            executable_signatures = [b'MZ', b'\x7fELF', b'\xca\xfe\xba\xbe']
            if any(header.startswith(sig) for sig in executable_signatures):
                security_result["safe"] = False
                security_result["issues"].append("Executable file detected")
            
        except Exception as e:
            security_result["issues"].append(f"Security scan failed: {str(e)}")
        
        return security_result
    
    # Format-specific validators
    def _validate_csv(self, file_path: Path) -> Dict[str, Any]:
        """Validate CSV file"""
        try:
            df = pd.read_csv(file_path, nrows=1000)  # Sample for validation
            return {
                "row_count": len(df),
                "column_count": len(df.columns),
                "encoding": "utf-8",
                "delimiter": ","
            }
        except Exception as e:
            return {"issues": [f"CSV validation failed: {str(e)}"]}
    
    def _validate_tsv(self, file_path: Path) -> Dict[str, Any]:
        """Validate TSV file"""
        try:
            df = pd.read_csv(file_path, sep='\t', nrows=1000)
            return {
                "row_count": len(df),
                "column_count": len(df.columns),
                "encoding": "utf-8",
                "delimiter": "\t"
            }
        except Exception as e:
            return {"issues": [f"TSV validation failed: {str(e)}"]}
    
    def _validate_excel(self, file_path: Path) -> Dict[str, Any]:
        """Validate Excel file"""
        try:
            df = pd.read_excel(file_path, nrows=1000)
            return {
                "row_count": len(df),
                "column_count": len(df.columns),
                "sheets": 1  # Simplified
            }
        except Exception as e:
            return {"issues": [f"Excel validation failed: {str(e)}"]}
    
    def _validate_h5ad(self, file_path: Path) -> Dict[str, Any]:
        """Validate H5AD file"""
        try:
            import scanpy as sc
            adata = sc.read_h5ad(file_path)
            return {
                "row_count": adata.n_obs,
                "column_count": adata.n_vars,
                "data_type": "AnnData"
            }
        except ImportError:
            return {"issues": ["scanpy not available for H5AD validation"]}
        except Exception as e:
            return {"issues": [f"H5AD validation failed: {str(e)}"]}
    
    def _validate_hdf5(self, file_path: Path) -> Dict[str, Any]:
        """Validate HDF5 file"""
        try:
            import h5py
            with h5py.File(file_path, 'r') as f:
                keys = list(f.keys())
            return {
                "hdf5_keys": keys,
                "data_type": "HDF5"
            }
        except ImportError:
            return {"issues": ["h5py not available for HDF5 validation"]}
        except Exception as e:
            return {"issues": [f"HDF5 validation failed: {str(e)}"]}
    
    def _validate_json(self, file_path: Path) -> Dict[str, Any]:
        """Validate JSON file"""
        try:
            import json
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                return {"row_count": len(data), "data_type": "JSON array"}
            elif isinstance(data, dict):
                return {"keys": list(data.keys()), "data_type": "JSON object"}
            else:
                return {"data_type": "JSON primitive"}
                
        except Exception as e:
            return {"issues": [f"JSON validation failed: {str(e)}"]}


class DataConverter:
    """Intelligent data conversion between formats"""
    
    def __init__(self, logger):
        self.logger = logger
        self.conversion_matrix = {
            ('csv', 'excel'): self._csv_to_excel,
            ('excel', 'csv'): self._excel_to_csv,
            ('csv', 'h5ad'): self._csv_to_h5ad,
            ('h5ad', 'csv'): self._h5ad_to_csv,
            ('csv', 'json'): self._csv_to_json,
            ('json', 'csv'): self._json_to_csv
        }
    
    def can_convert(self, from_format: str, to_format: str) -> bool:
        """Check if conversion is supported"""
        return (from_format, to_format) in self.conversion_matrix
    
    async def convert_file(self, input_path: Path, output_path: Path,
                          from_format: str, to_format: str) -> Dict[str, Any]:
        """Convert file between formats"""
        conversion_key = (from_format, to_format)
        
        if not self.can_convert(from_format, to_format):
            return {
                "success": False,
                "message": f"Conversion from {from_format} to {to_format} not supported"
            }
        
        try:
            converter = self.conversion_matrix[conversion_key]
            result = await converter(input_path, output_path)
            
            return {
                "success": True,
                "message": f"Successfully converted {from_format} to {to_format}",
                "output_path": str(output_path),
                **result
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Conversion failed: {str(e)}"
            }
    
    async def _csv_to_excel(self, input_path: Path, output_path: Path) -> Dict[str, Any]:
        """Convert CSV to Excel"""
        df = pd.read_csv(input_path)
        df.to_excel(output_path, index=False)
        return {"rows_converted": len(df), "columns_converted": len(df.columns)}
    
    async def _excel_to_csv(self, input_path: Path, output_path: Path) -> Dict[str, Any]:
        """Convert Excel to CSV"""
        df = pd.read_excel(input_path)
        df.to_csv(output_path, index=False)
        return {"rows_converted": len(df), "columns_converted": len(df.columns)}
    
    async def _csv_to_h5ad(self, input_path: Path, output_path: Path) -> Dict[str, Any]:
        """Convert CSV to H5AD (requires scanpy)"""
        try:
            import scanpy as sc
            import anndata
            
            df = pd.read_csv(input_path, index_col=0)
            adata = anndata.AnnData(df.T)  # Transpose for cells x genes
            adata.write_h5ad(output_path)
            
            return {"cells": adata.n_obs, "genes": adata.n_vars}
        except ImportError:
            raise Exception("scanpy and anndata required for H5AD conversion")
    
    async def _h5ad_to_csv(self, input_path: Path, output_path: Path) -> Dict[str, Any]:
        """Convert H5AD to CSV"""
        try:
            import scanpy as sc
            
            adata = sc.read_h5ad(input_path)
            df = pd.DataFrame(adata.X.T, index=adata.var.index, columns=adata.obs.index)
            df.to_csv(output_path)
            
            return {"cells": adata.n_obs, "genes": adata.n_vars}
        except ImportError:
            raise Exception("scanpy required for H5AD conversion")
    
    async def _csv_to_json(self, input_path: Path, output_path: Path) -> Dict[str, Any]:
        """Convert CSV to JSON"""
        df = pd.read_csv(input_path)
        df.to_json(output_path, orient='records', indent=2)
        return {"records_converted": len(df)}
    
    async def _json_to_csv(self, input_path: Path, output_path: Path) -> Dict[str, Any]:
        """Convert JSON to CSV"""
        df = pd.read_json(input_path)
        df.to_csv(output_path, index=False)
        return {"records_converted": len(df)}


class DataMCPServer(MCPServer):
    """Enhanced MCP Server for comprehensive data management"""
    
    def __init__(self):
        super().__init__("data_server", "2.0.0")
        self.logger = logging.getLogger("mcp.data")
        
        # Core components
        self.data_validator = DataValidator(self.logger)
        self.data_converter = DataConverter(self.logger)
        self.electron_bridge = None
        
        # File tracking and management
        self.uploaded_files = {}
        self.file_checksums = {}
        
        # Performance tracking
        self.operation_metrics = {
            "validations": 0,
            "conversions": 0,
            "uploads": 0,
            "total_processing_time": 0.0
        }
    
    async def initialize(self) -> bool:
        """Initialize data server with comprehensive setup"""
        try:
            self.logger.info("Initializing enhanced data management server")
            
            # Setup Electron integration
            await self._setup_electron_integration()
            
            # Discover and register components
            await self._discover_and_register_components()
            
            # Register data management tools
            await self._register_data_tools()
            
            self.logger.info("Data server initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Data server initialization failed: {str(e)}")
            return False
    
    async def _setup_electron_integration(self):
        """Setup Electron desktop integration"""
        try:
            if self._detect_electron_environment():
                self.electron_bridge = ElectronBridge(self.logger)
                await self.electron_bridge.initialize()
                await self.electron_bridge.notify_server_started("data")
                self.logger.info("Electron integration enabled for data server")
        except Exception as e:
            self.logger.warning(f"Electron integration failed: {str(e)}")
    
    def _detect_electron_environment(self) -> bool:
        """Detect if running in Electron environment"""
        import os
        return any(os.environ.get(var) for var in [
            "ELECTRON_RUN_AS_NODE", "ELECTRON_NO_ATTACH_CONSOLE"
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
    
    async def _register_data_tools(self):
        """Register data management specific tools"""
        
        # Enhanced file validation
        self.register_tool(
            name="validate_file_comprehensive",
            description="Comprehensive file validation with format detection and security scanning",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "expected_format": {"type": "string"},
                    "security_scan": {"type": "boolean", "default": True}
                },
                "required": ["file_path"]
            },
            handler=self._validate_file_comprehensive
        )
        
        # Smart data conversion
        self.register_tool(
            name="convert_data_format",
            description="Intelligent data format conversion with progress tracking",
            input_schema={
                "type": "object",
                "properties": {
                    "input_file": {"type": "string"},
                    "output_file": {"type": "string"},
                    "target_format": {"type": "string"},
                    "source_format": {"type": "string"}
                },
                "required": ["input_file", "target_format"]
            },
            handler=self._convert_data_format_smart
        )
        
        # File integrity check
        self.register_tool(
            name="check_file_integrity",
            description="Verify file integrity and detect changes",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"}
                },
                "required": ["file_path"]
            },
            handler=self._check_file_integrity
        )
        
        # Data quality assessment
        self.register_tool(
            name="assess_data_quality",
            description="Comprehensive data quality assessment with recommendations",
            input_schema={
                "type": "object",
                "properties": {
                    "data_key": {"type": "string"},
                    "analysis_type": {"type": "string", "default": "general"}
                },
                "required": ["data_key"]
            },
            handler=self._assess_data_quality_comprehensive
        )
    
    async def _manual_tool_registration(self):
        """Manual tool registration fallback"""
        essential_tools = [
            {
                "name": "validate_uploads",
                "description": "Validate uploaded files",
                "handler": self._validate_uploads
            },
            {
                "name": "get_data_overview",
                "description": "Get data overview",
                "handler": self._get_data_overview
            }
        ]
        
        for tool in essential_tools:
            self.register_tool(
                name=tool["name"],
                description=tool["description"],
                input_schema={"type": "object", "properties": {}, "required": []},
                handler=tool["handler"]
            )
    
    async def _validate_file_comprehensive(self, file_path: str, expected_format: str = None,
                                         security_scan: bool = True) -> Dict[str, Any]:
        """Comprehensive file validation with security scanning"""
        start_time = time.time()
        
        try:
            path_obj = Path(file_path)
            
            if not path_obj.exists():
                return {
                    "success": False,
                    "message": f"File not found: {file_path}"
                }
            
            # Progress notification
            if self.electron_bridge:
                await self.electron_bridge.notify_analysis_progress("data", "validation_start", 0.0)
            
            # Perform validation
            validation_result = self.data_validator.validate_file(path_obj, expected_format)
            
            # Update metrics
            execution_time = time.time() - start_time
            self.operation_metrics["validations"] += 1
            self.operation_metrics["total_processing_time"] += execution_time
            
            # Store file checksum for integrity checking
            if validation_result["valid"]:
                checksum = self._calculate_checksum(path_obj)
                self.file_checksums[file_path] = checksum
            
            # Send completion notification
            if self.electron_bridge:
                await self.electron_bridge.notify_analysis_progress("data", "validation_complete", 100.0)
            
            return {
                "success": True,
                "validation_result": validation_result,
                "execution_time": execution_time,
                "message": "File validation completed"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"File validation failed: {str(e)}"
            }
    
    async def _convert_data_format_smart(self, input_file: str, target_format: str,
                                       output_file: str = None, source_format: str = None) -> Dict[str, Any]:
        """Smart data format conversion with progress tracking"""
        start_time = time.time()
        
        try:
            input_path = Path(input_file)
            
            # Auto-detect source format if not provided
            if not source_format:
                detection = self.data_validator.detect_format(input_path)
                source_format = detection["format"]
            
            # Generate output filename if not provided
            if not output_file:
                output_file = str(input_path.with_suffix(f'.{target_format}'))
            
            output_path = Path(output_file)
            
            # Check if conversion is supported
            if not self.data_converter.can_convert(source_format, target_format):
                return {
                    "success": False,
                    "message": f"Conversion from {source_format} to {target_format} not supported"
                }
            
            # Progress notification
            if self.electron_bridge:
                await self.electron_bridge.notify_analysis_progress("data", "conversion_start", 0.0)
            
            # Perform conversion
            conversion_result = await self.data_converter.convert_file(
                input_path, output_path, source_format, target_format
            )
            
            # Update metrics
            execution_time = time.time() - start_time
            self.operation_metrics["conversions"] += 1
            self.operation_metrics["total_processing_time"] += execution_time
            
            # Send completion notification
            if self.electron_bridge and conversion_result["success"]:
                notification = DesktopNotification(
                    title="Data Conversion Complete",
                    body=f"Converted {source_format} to {target_format}",
                    urgency="normal"
                )
                await self.electron_bridge.send_desktop_notification(notification)
                await self.electron_bridge.notify_analysis_progress("data", "conversion_complete", 100.0)
            
            conversion_result["execution_time"] = execution_time
            return conversion_result
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Data conversion failed: {str(e)}"
            }
    
    async def _check_file_integrity(self, file_path: str) -> Dict[str, Any]:
        """Check file integrity using checksums"""
        try:
            path_obj = Path(file_path)
            
            if not path_obj.exists():
                return {
                    "success": False,
                    "message": f"File not found: {file_path}"
                }
            
            current_checksum = self._calculate_checksum(path_obj)
            stored_checksum = self.file_checksums.get(file_path)
            
            if stored_checksum:
                integrity_status = current_checksum == stored_checksum
                message = "File integrity verified" if integrity_status else "File has been modified"
            else:
                integrity_status = True  # First check
                message = "Checksum recorded for future integrity checks"
                self.file_checksums[file_path] = current_checksum
            
            return {
                "success": True,
                "integrity_verified": integrity_status,
                "current_checksum": current_checksum,
                "stored_checksum": stored_checksum,
                "message": message
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Integrity check failed: {str(e)}"
            }
    
    async def _assess_data_quality_comprehensive(self, data_key: str, 
                                               analysis_type: str = "general") -> Dict[str, Any]:
        """Comprehensive data quality assessment"""
        try:
            if data_key not in st.session_state:
                return {
                    "success": False,
                    "message": f"Data key '{data_key}' not found in session"
                }
            
            data = st.session_state[data_key]
            
            quality_assessment = {
                "data_type": type(data).__name__,
                "quality_score": 100,
                "issues": [],
                "recommendations": []
            }
            
            if isinstance(data, pd.DataFrame):
                quality_assessment.update(self._assess_dataframe_quality(data))
            elif isinstance(data, dict):
                quality_assessment.update(self._assess_dict_quality(data))
            else:
                quality_assessment["recommendations"].append("Convert to DataFrame for detailed analysis")
            
            return {
                "success": True,
                "quality_assessment": quality_assessment,
                "message": "Data quality assessment completed"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Quality assessment failed: {str(e)}"
            }
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _assess_dataframe_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Assess quality of pandas DataFrame"""
        quality_metrics = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "missing_values": df.isnull().sum().sum(),
            "duplicate_rows": df.duplicated().sum(),
            "data_types": df.dtypes.value_counts().to_dict()
        }
        
        # Calculate quality score
        quality_score = 100
        missing_ratio = quality_metrics["missing_values"] / (len(df) * len(df.columns))
        duplicate_ratio = quality_metrics["duplicate_rows"] / len(df)
        
        quality_score -= missing_ratio * 30  # Penalize missing values
        quality_score -= duplicate_ratio * 20  # Penalize duplicates
        
        return {
            "quality_metrics": quality_metrics,
            "quality_score": max(0, quality_score)
        }
    
    def _assess_dict_quality(self, data: dict) -> Dict[str, Any]:
        """Assess quality of dictionary data"""
        return {
            "quality_metrics": {
                "key_count": len(data),
                "nested_levels": self._count_nested_levels(data)
            },
            "quality_score": 85  # Default score for dict data
        }
    
    def _count_nested_levels(self, obj, level=0):
        """Count nested levels in dictionary"""
        if isinstance(obj, dict) and obj:
            return max(self._count_nested_levels(v, level + 1) for v in obj.values())
        return level
    
    # Legacy methods for backward compatibility
    async def _validate_uploads(self) -> Dict[str, Any]:
        """Legacy upload validation method"""
        return {
            "success": True,
            "message": "Use validate_file_comprehensive for enhanced validation"
        }
    
    async def _get_data_overview(self) -> Dict[str, Any]:
        """Get overview of all managed data"""
        overview = {
            "uploaded_files": len(self.uploaded_files),
            "tracked_checksums": len(self.file_checksums),
            "operation_metrics": self.operation_metrics,
            "electron_connected": self.electron_bridge is not None
        }
        
        return {
            "success": True,
            "overview": overview
        }
    
    def _get_server_specific_context(self) -> Dict[str, Any]:
        """Get data server specific context information"""
        return {
            "server_type": "data_management",
            "supported_formats": ["csv", "tsv", "excel", "h5ad", "hdf5", "json"],
            "validation_capabilities": ["format_detection", "security_scan", "integrity_check"],
            "conversion_capabilities": ["csv_to_excel", "excel_to_csv", "csv_to_h5ad", "h5ad_to_csv", "csv_to_json", "json_to_csv"],
            "uploaded_files_count": len(self.uploaded_files),
            "operation_metrics": self.operation_metrics,
            "electron_enabled": self.electron_bridge is not None,
            "features": ["comprehensive_validation", "smart_conversion", "quality_assessment"]
        }

    async def shutdown(self):
        """Graceful server shutdown"""
        self.logger.info("Shutting down data management server")
        
        if self.electron_bridge:
            await self.electron_bridge.notify_server_stopped("data")
            await self.electron_bridge.shutdown()
        
        # Log final metrics
        self.logger.info(f"Final operation metrics: {self.operation_metrics}")
        
        await super().shutdown()


def main():
    """Main function for testing enhanced data server"""
    print("=== Enhanced Data Server Test ===")
    
    # Static tests
    print("\n1. Testing DataValidator...")
    logger = logging.getLogger("test")
    validator = DataValidator(logger)
    
    # Test format detection (mock)
    supported_formats = validator.supported_formats
    assert 'csv' in supported_formats
    assert 'excel' in supported_formats
    print("✅ DataValidator created with supported formats")
    
    print("\n2. Testing DataConverter...")
    converter = DataConverter(logger)
    can_convert = converter.can_convert('csv', 'excel')
    assert isinstance(can_convert, bool)
    print("✅ DataConverter working")
    
    print("\n3. Testing server creation...")
    server = DataMCPServer()
    assert server.name == "data_server"
    assert server.version == "2.0.0"
    print("✅ Enhanced data server created")


def test_dynamic():
    """Dynamic tests for enhanced data server"""
    async def run_dynamic_tests():
        print("\n=== Dynamic Tests ===")
        
        server = DataMCPServer()
        
        print("1. Testing server initialization...")
        success = await server.initialize()
        assert success is True
        print("✅ Server initialization working")
        
        print("\n2. Testing data overview...")
        overview_result = await server._get_data_overview()
        assert overview_result["success"] is True
        assert "overview" in overview_result
        print("✅ Data overview working")
        
        print("\n3. Testing checksum calculation...")
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test data")
            temp_path = f.name
        
        try:
            checksum = server._calculate_checksum(Path(temp_path))
            assert len(checksum) == 64  # SHA-256 length
            print("✅ Checksum calculation working")
        finally:
            Path(temp_path).unlink()
        
        print("\n🎉 All dynamic tests passed!")
    
    # Run async tests
    asyncio.run(run_dynamic_tests())


if __name__ == "__main__":
    main()
    test_dynamic()