"""
Server Registry - Centralized registry for all MCP server types

This module contains the mapping of server types to their implementations,
separated to avoid circular import issues.
"""

from .rnaseq_server import RNASeqMCPServer
from .scrnaseq_server import scRNASeqMCPServer
from .atacseq_server import ATACSeqMCPServer
from .data_server import DataMCPServer
from .visualization_server import VisualizationMCPServer
from .proteomics_server import ProteomicsMCPServer
from .search_server import SearchMCPServer

# Server registry for easy access
AVAILABLE_SERVERS = {
    "rnaseq": RNASeqMCPServer,
    "scrnaseq": scRNASeqMCPServer,
    "atacseq": ATACSeqMCPServer,
    "data": DataMCPServer,
    "visualization": VisualizationMCPServer,
    "proteomics": ProteomicsMCPServer,
    "search": SearchMCPServer
}

# List of server types for convenience
SERVER_TYPES = list(AVAILABLE_SERVERS.keys())

def get_server_class(server_type: str):
    """Get server class by type name"""
    return AVAILABLE_SERVERS.get(server_type)

def is_valid_server_type(server_type: str) -> bool:
    """Check if server type is valid"""
    return server_type in AVAILABLE_SERVERS

def get_available_server_types() -> list:
    """Get list of available server types"""
    return SERVER_TYPES.copy() 