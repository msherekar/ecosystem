"""
Simple tool registry for plot analysis functionality
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class SimpleToolRegistry:
    """Lightweight tool registry focused on plot analysis"""
    
    def __init__(self):
        self.tools = {}
        self._register_core_tools()
    
    def _register_core_tools(self):
        """Register essential plot analysis tools"""
        
        # Plot analysis tool
        self.tools["analyze_current_plots"] = {
            "type": "function",
            "function": {
                "name": "analyze_current_plots",
                "description": "Analyze plots and visualizations currently displayed in the analysis interface. Use this when users ask about plots, results, or what they can see on the page.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "analysis_type": {
                            "type": "string",
                            "description": "Type of analysis to focus on (qc, filtering, normalization, pca, clustering, etc.)",
                            "enum": ["qc", "filtering", "normalization", "pca", "clustering", "differential", "general"]
                        },
                        "specific_question": {
                            "type": "string",
                            "description": "Specific question about the plots or results"
                        }
                    },
                    "required": ["analysis_type"]
                }
            }
        }
        
        # File status tool
        self.tools["get_file_status"] = {
            "type": "function", 
            "function": {
                "name": "get_file_status",
                "description": "Get current status of analysis files and data",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    
    def get_tool_definitions_for_agent(self) -> List[Dict[str, Any]]:
        """Get tool definitions in OpenAI format"""
        return list(self.tools.values())
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool with given arguments"""
        try:
            if tool_name == "analyze_current_plots":
                return await self._analyze_current_plots(arguments)
            elif tool_name == "get_file_status":
                return await self._get_file_status()
            else:
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return f"Error executing {tool_name}: {str(e)}"
    
    async def _analyze_current_plots(self, args: Dict[str, Any]) -> str:
        """Analyze current plots and provide insights"""
        analysis_type = args.get("analysis_type", "general")
        specific_question = args.get("specific_question", "")
        
        # Get current analysis state
        results_dir = Path("results")
        plots_dir = results_dir / "plots"
        
        if not plots_dir.exists():
            return "No plots directory found. Please run an analysis first to generate visualizations."
        
        # Look for recent plot files
        plot_files = []
        for ext in ["*.png", "*.jpg", "*.jpeg", "*.svg"]:
            plot_files.extend(plots_dir.glob(ext))
        
        if not plot_files:
            return "No plot files found in the results directory."
        
        # Get the most recent plots
        recent_plots = sorted(plot_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]
        
        # Analyze based on type
        insights = []
        insights.append(f"Found {len(recent_plots)} recent plots in the analysis:")
        
        for plot_file in recent_plots:
            plot_name = plot_file.stem
            insights.append(f"- {plot_name}")
            
            # Provide context based on plot type
            if "qc" in plot_name.lower():
                insights.append("  → Quality control metrics - check for outliers and data quality")
            elif "filter" in plot_name.lower():
                insights.append("  → Filtering results - shows data before/after filtering")
            elif "pca" in plot_name.lower():
                insights.append("  → Principal component analysis - shows variance and sample relationships")
            elif "umap" in plot_name.lower() or "tsne" in plot_name.lower():
                insights.append("  → Dimensionality reduction - reveals cell clusters and structure")
            elif "volcano" in plot_name.lower():
                insights.append("  → Differential expression - shows significantly changed genes")
        
        # Add analysis-specific insights
        if analysis_type == "qc":
            insights.append("\nQC Analysis Tips:")
            insights.append("- Look for cells with very low/high gene counts")
            insights.append("- Check mitochondrial gene percentage")
            insights.append("- Identify potential doublets or low-quality cells")
        elif analysis_type == "clustering":
            insights.append("\nClustering Analysis Tips:")
            insights.append("- Examine cluster separation and overlap")
            insights.append("- Look for batch effects or technical artifacts")
            insights.append("- Consider biological relevance of clusters")
        
        if specific_question:
            insights.append(f"\nRegarding your question: '{specific_question}'")
            insights.append("Based on the available plots, I can help interpret the results you're seeing.")
        
        return "\n".join(insights)
    
    async def _get_file_status(self) -> str:
        """Get status of analysis files"""
        status = []
        
        # Check for data files
        data_dir = Path("data")
        if data_dir.exists():
            data_files = list(data_dir.glob("*.h5ad")) + list(data_dir.glob("*.csv")) + list(data_dir.glob("*.h5"))
            if data_files:
                status.append(f"Data files: {len(data_files)} found")
            else:
                status.append("No data files found")
        
        # Check for results
        results_dir = Path("results")
        if results_dir.exists():
            plot_files = list(results_dir.glob("**/*.png"))
            if plot_files:
                status.append(f"Generated plots: {len(plot_files)}")
            else:
                status.append("No plots generated yet")
        
        return "; ".join(status) if status else "No analysis files found"

# Global registry instance
_registry = None

def get_tool_registry() -> SimpleToolRegistry:
    """Get the global tool registry instance"""
    global _registry
    if _registry is None:
        _registry = SimpleToolRegistry()
    return _registry 