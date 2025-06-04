"""
Model Context Protocol (MCP) Implementation for Bioinformatics Platform

This package provides a scalable MCP architecture for connecting AI agents
with bioinformatics analysis tools and data sources.
"""

from .core.server import MCPServer
from .core.client import MCPClient
from .core.registry import MCPRegistry
from .servers.rnaseq_server import RNASeqMCPServer
from .servers.scrnaseq_server import scRNASeqMCPServer
from .servers.data_server import DataMCPServer
from .servers.visualization_server import VisualizationMCPServer

__version__ = "1.0.0"
__all__ = [
    "MCPServer",
    "MCPClient", 
    "MCPRegistry",
    "RNASeqMCPServer",
    "scRNASeqMCPServer",
    "DataMCPServer",
    "VisualizationMCPServer"
] 