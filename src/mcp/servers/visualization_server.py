"""
Visualization MCP Server

Provides MCP interface for visualization tools including:
- Statistical plots (histograms, boxplots, scatter plots)
- Heatmaps and clustering visualizations
- Dimensionality reduction plots (PCA, UMAP, t-SNE)
- Publication-ready figure generation
- Interactive plotting capabilities
"""

import asyncio
import pandas as pd
import numpy as np
from typing import Any, Dict, Optional, List
import streamlit as st

from ..core.server import MCPServer


class VisualizationMCPServer(MCPServer):
    """MCP Server for visualization tools"""
    
    def __init__(self):
        super().__init__("visualization_server", "1.0.0")
    
    async def initialize(self) -> None:
        """Initialize visualization server with tools and resources"""
        
        # Register statistical plot tools
        await self._register_statistical_plots()
        
        # Register specialized plot tools
        await self._register_specialized_plots()
        
        # Register interactive plot tools
        await self._register_interactive_plots()
        
        # Register export tools
        await self._register_export_tools()
        
        # Register resources
        await self._register_resources()
        
        # Register prompts
        await self._register_prompts()
    
    async def _register_statistical_plots(self):
        """Register statistical plotting tools"""
        
        # Histogram
        self.register_tool(
            name="create_histogram",
            description="Create histogram plot for data distribution",
            input_schema={
                "type": "object",
                "properties": {
                    "data_key": {
                        "type": "string",
                        "description": "Session state key for the data"
                    },
                    "column": {
                        "type": "string",
                        "description": "Column name to plot"
                    },
                    "bins": {
                        "type": "integer",
                        "description": "Number of bins",
                        "default": 30
                    },
                    "title": {
                        "type": "string",
                        "description": "Plot title"
                    }
                },
                "required": ["data_key", "column"]
            },
            handler=self._create_histogram
        )
        
        # Box plot
        self.register_tool(
            name="create_boxplot",
            description="Create box plot for comparing distributions",
            input_schema={
                "type": "object",
                "properties": {
                    "data_key": {
                        "type": "string",
                        "description": "Session state key for the data"
                    },
                    "x_column": {
                        "type": "string",
                        "description": "X-axis column (categorical)"
                    },
                    "y_column": {
                        "type": "string",
                        "description": "Y-axis column (numerical)"
                    },
                    "title": {
                        "type": "string",
                        "description": "Plot title"
                    }
                },
                "required": ["data_key", "x_column", "y_column"]
            },
            handler=self._create_boxplot
        )
        
        # Scatter plot
        self.register_tool(
            name="create_scatter_plot",
            description="Create scatter plot for correlation analysis",
            input_schema={
                "type": "object",
                "properties": {
                    "data_key": {
                        "type": "string",
                        "description": "Session state key for the data"
                    },
                    "x_column": {
                        "type": "string",
                        "description": "X-axis column"
                    },
                    "y_column": {
                        "type": "string",
                        "description": "Y-axis column"
                    },
                    "color_column": {
                        "type": "string",
                        "description": "Column to color points by"
                    },
                    "title": {
                        "type": "string",
                        "description": "Plot title"
                    }
                },
                "required": ["data_key", "x_column", "y_column"]
            },
            handler=self._create_scatter_plot
        )
        
        # Correlation heatmap
        self.register_tool(
            name="create_correlation_heatmap",
            description="Create correlation heatmap for numerical data",
            input_schema={
                "type": "object",
                "properties": {
                    "data_key": {
                        "type": "string",
                        "description": "Session state key for the data"
                    },
                    "method": {
                        "type": "string",
                        "description": "Correlation method",
                        "enum": ["pearson", "spearman", "kendall"],
                        "default": "pearson"
                    },
                    "title": {
                        "type": "string",
                        "description": "Plot title"
                    }
                },
                "required": ["data_key"]
            },
            handler=self._create_correlation_heatmap
        )
    
    async def _register_specialized_plots(self):
        """Register specialized plotting tools"""
        
        # PCA plot
        self.register_tool(
            name="create_pca_plot",
            description="Create PCA plot for dimensionality reduction visualization",
            input_schema={
                "type": "object",
                "properties": {
                    "data_key": {
                        "type": "string",
                        "description": "Session state key for the data"
                    },
                    "color_by": {
                        "type": "string",
                        "description": "Variable to color points by"
                    },
                    "components": {
                        "type": "array",
                        "description": "PCA components to plot",
                        "items": {"type": "integer"},
                        "default": [1, 2]
                    },
                    "title": {
                        "type": "string",
                        "description": "Plot title"
                    }
                },
                "required": ["data_key"]
            },
            handler=self._create_pca_plot
        )
        
        # Volcano plot
        self.register_tool(
            name="create_volcano_plot",
            description="Create volcano plot for differential expression results",
            input_schema={
                "type": "object",
                "properties": {
                    "results_key": {
                        "type": "string",
                        "description": "Session state key for DE results",
                        "default": "deseq_results"
                    },
                    "logfc_threshold": {
                        "type": "number",
                        "description": "Log fold change threshold",
                        "default": 1.0
                    },
                    "pvalue_threshold": {
                        "type": "number",
                        "description": "P-value threshold",
                        "default": 0.05
                    },
                    "title": {
                        "type": "string",
                        "description": "Plot title"
                    }
                },
                "required": ["results_key"]
            },
            handler=self._create_volcano_plot
        )
        
        # MA plot
        self.register_tool(
            name="create_ma_plot",
            description="Create MA plot for expression analysis",
            input_schema={
                "type": "object",
                "properties": {
                    "results_key": {
                        "type": "string",
                        "description": "Session state key for results",
                        "default": "deseq_results"
                    },
                    "title": {
                        "type": "string",
                        "description": "Plot title"
                    }
                },
                "required": ["results_key"]
            },
            handler=self._create_ma_plot
        )
    
    async def _register_interactive_plots(self):
        """Register interactive plotting tools"""
        
        # Interactive scatter
        self.register_tool(
            name="create_interactive_scatter",
            description="Create interactive scatter plot with hover information",
            input_schema={
                "type": "object",
                "properties": {
                    "data_key": {
                        "type": "string",
                        "description": "Session state key for the data"
                    },
                    "x_column": {
                        "type": "string",
                        "description": "X-axis column"
                    },
                    "y_column": {
                        "type": "string",
                        "description": "Y-axis column"
                    },
                    "hover_columns": {
                        "type": "array",
                        "description": "Columns to show on hover",
                        "items": {"type": "string"}
                    },
                    "title": {
                        "type": "string",
                        "description": "Plot title"
                    }
                },
                "required": ["data_key", "x_column", "y_column"]
            },
            handler=self._create_interactive_scatter
        )
        
        # Interactive heatmap
        self.register_tool(
            name="create_interactive_heatmap",
            description="Create interactive heatmap with zoom and selection",
            input_schema={
                "type": "object",
                "properties": {
                    "data_key": {
                        "type": "string",
                        "description": "Session state key for the data"
                    },
                    "cluster_rows": {
                        "type": "boolean",
                        "description": "Cluster rows",
                        "default": True
                    },
                    "cluster_cols": {
                        "type": "boolean",
                        "description": "Cluster columns",
                        "default": True
                    },
                    "title": {
                        "type": "string",
                        "description": "Plot title"
                    }
                },
                "required": ["data_key"]
            },
            handler=self._create_interactive_heatmap
        )
    
    async def _register_export_tools(self):
        """Register plot export tools"""
        
        # Export plot
        self.register_tool(
            name="export_plot",
            description="Export plot to file",
            input_schema={
                "type": "object",
                "properties": {
                    "plot_id": {
                        "type": "string",
                        "description": "ID of the plot to export"
                    },
                    "format": {
                        "type": "string",
                        "description": "Export format",
                        "enum": ["png", "pdf", "svg", "html"],
                        "default": "png"
                    },
                    "width": {
                        "type": "integer",
                        "description": "Plot width in pixels",
                        "default": 800
                    },
                    "height": {
                        "type": "integer",
                        "description": "Plot height in pixels",
                        "default": 600
                    },
                    "dpi": {
                        "type": "integer",
                        "description": "Resolution in DPI",
                        "default": 300
                    }
                },
                "required": ["plot_id"]
            },
            handler=self._export_plot
        )
        
        # Create figure panel
        self.register_tool(
            name="create_figure_panel",
            description="Combine multiple plots into a figure panel",
            input_schema={
                "type": "object",
                "properties": {
                    "plot_ids": {
                        "type": "array",
                        "description": "List of plot IDs to combine",
                        "items": {"type": "string"}
                    },
                    "layout": {
                        "type": "string",
                        "description": "Panel layout",
                        "enum": ["grid", "horizontal", "vertical"],
                        "default": "grid"
                    },
                    "title": {
                        "type": "string",
                        "description": "Figure title"
                    }
                },
                "required": ["plot_ids"]
            },
            handler=self._create_figure_panel
        )
    
    async def _register_resources(self):
        """Register visualization resources"""
        
        # Plot gallery resource
        self.register_resource(
            uri="viz://gallery/all",
            name="Plot Gallery",
            description="Gallery of all generated plots",
            mime_type="application/json"
        )
        
        # Plot templates resource
        self.register_resource(
            uri="viz://templates/standard",
            name="Plot Templates",
            description="Standard plot templates and styles",
            mime_type="application/json"
        )
    
    async def _register_prompts(self):
        """Register visualization prompts"""
        
        self.register_prompt(
            name="suggest_visualization",
            description="Suggest appropriate visualizations based on data type",
            template="""
            Based on your data characteristics:
            
            - Data type: {data_type}
            - Number of variables: {n_variables}
            - Variable types: {variable_types}
            - Sample size: {sample_size}
            - Analysis goal: {analysis_goal}
            
            I recommend the following visualizations:
            {recommended_plots}
            
            These plots will help you:
            {plot_purposes}
            """,
            parameters={
                "data_type": "string",
                "n_variables": "integer",
                "variable_types": "array",
                "sample_size": "integer",
                "analysis_goal": "string",
                "recommended_plots": "array",
                "plot_purposes": "array"
            }
        )
    
    # Tool handler implementations
    
    async def _create_histogram(self, data_key: str, column: str, bins: int = 30, title: str = None) -> Dict[str, Any]:
        """Create histogram plot"""
        if data_key not in st.session_state:
            return {
                "success": False,
                "message": f"Data key '{data_key}' not found in session"
            }
        
        data = st.session_state[data_key]
        if column not in data.columns:
            return {
                "success": False,
                "message": f"Column '{column}' not found in data"
            }
        
        # Mock implementation - would create actual plot
        return {
            "success": True,
            "message": f"Histogram created for {column} with {bins} bins",
            "plot_type": "histogram",
            "plot_id": f"hist_{column}_{bins}",
            "parameters": {
                "column": column,
                "bins": bins,
                "title": title or f"Distribution of {column}"
            }
        }
    
    async def _create_boxplot(self, data_key: str, x_column: str, y_column: str, title: str = None) -> Dict[str, Any]:
        """Create box plot"""
        if data_key not in st.session_state:
            return {
                "success": False,
                "message": f"Data key '{data_key}' not found in session"
            }
        
        data = st.session_state[data_key]
        missing_cols = [col for col in [x_column, y_column] if col not in data.columns]
        if missing_cols:
            return {
                "success": False,
                "message": f"Columns not found: {missing_cols}"
            }
        
        return {
            "success": True,
            "message": f"Box plot created: {y_column} by {x_column}",
            "plot_type": "boxplot",
            "plot_id": f"box_{x_column}_{y_column}",
            "parameters": {
                "x_column": x_column,
                "y_column": y_column,
                "title": title or f"{y_column} by {x_column}"
            }
        }
    
    async def _create_scatter_plot(self, data_key: str, x_column: str, y_column: str, color_column: str = None, title: str = None) -> Dict[str, Any]:
        """Create scatter plot"""
        if data_key not in st.session_state:
            return {
                "success": False,
                "message": f"Data key '{data_key}' not found in session"
            }
        
        data = st.session_state[data_key]
        required_cols = [x_column, y_column]
        if color_column:
            required_cols.append(color_column)
        
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            return {
                "success": False,
                "message": f"Columns not found: {missing_cols}"
            }
        
        return {
            "success": True,
            "message": f"Scatter plot created: {x_column} vs {y_column}",
            "plot_type": "scatter",
            "plot_id": f"scatter_{x_column}_{y_column}",
            "parameters": {
                "x_column": x_column,
                "y_column": y_column,
                "color_column": color_column,
                "title": title or f"{x_column} vs {y_column}"
            }
        }
    
    async def _create_correlation_heatmap(self, data_key: str, method: str = "pearson", title: str = None) -> Dict[str, Any]:
        """Create correlation heatmap"""
        if data_key not in st.session_state:
            return {
                "success": False,
                "message": f"Data key '{data_key}' not found in session"
            }
        
        data = st.session_state[data_key]
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        
        if len(numeric_cols) < 2:
            return {
                "success": False,
                "message": "Need at least 2 numeric columns for correlation analysis"
            }
        
        return {
            "success": True,
            "message": f"Correlation heatmap created using {method} method",
            "plot_type": "correlation_heatmap",
            "plot_id": f"corr_{method}",
            "parameters": {
                "method": method,
                "n_variables": len(numeric_cols),
                "title": title or f"Correlation Matrix ({method})"
            }
        }
    
    async def _create_pca_plot(self, data_key: str, color_by: str = None, components: List[int] = [1, 2], title: str = None) -> Dict[str, Any]:
        """Create PCA plot"""
        if data_key not in st.session_state:
            return {
                "success": False,
                "message": f"Data key '{data_key}' not found in session"
            }
        
        return {
            "success": True,
            "message": f"PCA plot created for components {components}",
            "plot_type": "pca",
            "plot_id": f"pca_{'_'.join(map(str, components))}",
            "parameters": {
                "components": components,
                "color_by": color_by,
                "title": title or f"PCA Plot (PC{components[0]} vs PC{components[1]})"
            }
        }
    
    async def _create_volcano_plot(self, results_key: str = "deseq_results", logfc_threshold: float = 1.0, pvalue_threshold: float = 0.05, title: str = None) -> Dict[str, Any]:
        """Create volcano plot"""
        if results_key not in st.session_state:
            return {
                "success": False,
                "message": f"Results key '{results_key}' not found in session"
            }
        
        return {
            "success": True,
            "message": f"Volcano plot created with thresholds: logFC={logfc_threshold}, p={pvalue_threshold}",
            "plot_type": "volcano",
            "plot_id": f"volcano_{logfc_threshold}_{pvalue_threshold}",
            "parameters": {
                "logfc_threshold": logfc_threshold,
                "pvalue_threshold": pvalue_threshold,
                "title": title or "Volcano Plot"
            }
        }
    
    async def _create_ma_plot(self, results_key: str = "deseq_results", title: str = None) -> Dict[str, Any]:
        """Create MA plot"""
        if results_key not in st.session_state:
            return {
                "success": False,
                "message": f"Results key '{results_key}' not found in session"
            }
        
        return {
            "success": True,
            "message": "MA plot created",
            "plot_type": "ma_plot",
            "plot_id": "ma_plot",
            "parameters": {
                "title": title or "MA Plot"
            }
        }
    
    async def _create_interactive_scatter(self, data_key: str, x_column: str, y_column: str, hover_columns: List[str] = None, title: str = None) -> Dict[str, Any]:
        """Create interactive scatter plot"""
        if data_key not in st.session_state:
            return {
                "success": False,
                "message": f"Data key '{data_key}' not found in session"
            }
        
        return {
            "success": True,
            "message": f"Interactive scatter plot created: {x_column} vs {y_column}",
            "plot_type": "interactive_scatter",
            "plot_id": f"interactive_scatter_{x_column}_{y_column}",
            "parameters": {
                "x_column": x_column,
                "y_column": y_column,
                "hover_columns": hover_columns or [],
                "title": title or f"Interactive: {x_column} vs {y_column}"
            }
        }
    
    async def _create_interactive_heatmap(self, data_key: str, cluster_rows: bool = True, cluster_cols: bool = True, title: str = None) -> Dict[str, Any]:
        """Create interactive heatmap"""
        if data_key not in st.session_state:
            return {
                "success": False,
                "message": f"Data key '{data_key}' not found in session"
            }
        
        return {
            "success": True,
            "message": f"Interactive heatmap created with clustering: rows={cluster_rows}, cols={cluster_cols}",
            "plot_type": "interactive_heatmap",
            "plot_id": f"interactive_heatmap_{cluster_rows}_{cluster_cols}",
            "parameters": {
                "cluster_rows": cluster_rows,
                "cluster_cols": cluster_cols,
                "title": title or "Interactive Heatmap"
            }
        }
    
    async def _export_plot(self, plot_id: str, format: str = "png", width: int = 800, height: int = 600, dpi: int = 300) -> Dict[str, Any]:
        """Export plot to file"""
        return {
            "success": True,
            "message": f"Plot {plot_id} exported as {format}",
            "export_info": {
                "plot_id": plot_id,
                "format": format,
                "dimensions": f"{width}x{height}",
                "dpi": dpi,
                "filename": f"{plot_id}.{format}"
            }
        }
    
    async def _create_figure_panel(self, plot_ids: List[str], layout: str = "grid", title: str = None) -> Dict[str, Any]:
        """Create figure panel from multiple plots"""
        return {
            "success": True,
            "message": f"Figure panel created with {len(plot_ids)} plots in {layout} layout",
            "plot_type": "figure_panel",
            "plot_id": f"panel_{len(plot_ids)}_{layout}",
            "parameters": {
                "plot_ids": plot_ids,
                "layout": layout,
                "title": title or f"Figure Panel ({len(plot_ids)} plots)"
            }
        }
    
    def _get_server_specific_context(self) -> Dict[str, Any]:
        """Get visualization specific context"""
        context = {
            "analysis_type": "visualization",
            "available_data": [],
            "plot_suggestions": []
        }
        
        # Check available data for plotting
        if "rnaseq_counts_df" in st.session_state:
            context["available_data"].append("rnaseq_counts")
            context["plot_suggestions"].extend(["pca", "correlation_heatmap", "sample_clustering"])
        
        if "rnaseq_metadata_df" in st.session_state:
            context["available_data"].append("rnaseq_metadata")
            context["plot_suggestions"].extend(["metadata_distribution", "sample_overview"])
        
        if "deseq_results" in st.session_state:
            context["available_data"].append("deseq_results")
            context["plot_suggestions"].extend(["volcano_plot", "ma_plot"])
        
        if "anndata" in st.session_state and st.session_state.anndata is not None:
            context["available_data"].append("scrnaseq_data")
            context["plot_suggestions"].extend(["umap", "violin_plot", "marker_heatmap"])
        
        return context 