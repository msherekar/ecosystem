"""
MCP Servers Package

Contains all bioinformatics MCP server implementations.
"""

from .rnaseq_server import RNASeqMCPServer
from .scrnaseq_server import scRNASeqMCPServer
from .atacseq_server import ATACSeqMCPServer
from .data_server import DataMCPServer
from .visualization_server import VisualizationMCPServer
from .proteomics_server import ProteomicsMCPServer

__all__ = [
    "RNASeqMCPServer",
    "scRNASeqMCPServer", 
    "ATACSeqMCPServer",
    "DataMCPServer",
    "VisualizationMCPServer",
    "ProteomicsMCPServer"
]

# Server registry for easy access
AVAILABLE_SERVERS = {
    "rnaseq": RNASeqMCPServer,
    "scrnaseq": scRNASeqMCPServer,
    "atacseq": ATACSeqMCPServer
} 