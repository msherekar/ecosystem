"""MCP server implementations and orchestration.

Server classes are resolved lazily. Importing them eagerly meant that
touching anything in this package loaded every analysis server and, through
them, every heavy optional dependency — scanpy, pydeseq2, streamlit. A
missing one took down the whole package, and a process that only needed the
search server still paid to import DESeq2.
"""

from __future__ import annotations

import importlib
from typing import Any

#: Exported name -> the submodule that defines it.
_LAZY_EXPORTS = {
    "RNASeqMCPServer": ".rnaseq_server",
    "scRNASeqMCPServer": ".scrnaseq_server",
    "ATACSeqMCPServer": ".atacseq_server",
    "DataMCPServer": ".data_server",
    "VisualizationMCPServer": ".visualization_server",
    "ProteomicsMCPServer": ".proteomics_server",
    "SearchMCPServer": ".search_server",
    "AVAILABLE_SERVERS": ".server_registry",
    "SERVER_TYPES": ".server_registry",
    "MCPServerOrchestrator": ".__main__",
    "ServerContext": ".__main__",
    "get_orchestrator": ".__main__",
    "ServerConfig": "..core.config",
}

__all__ = sorted(_LAZY_EXPORTS)


def __getattr__(name: str) -> Any:
    """Resolve an exported name on first access.

    Raises:
        AttributeError: If `name` is not exported.
        ImportError: Re-raised with the missing dependency named, so a server
            that cannot load says why instead of failing the whole package.
    """
    module_name = _LAZY_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    try:
        module = importlib.import_module(module_name, __name__)
    except ImportError as exc:
        raise ImportError(
            f"{name} is unavailable because {module_name} could not be "
            f"imported: {exc}. Install the dependency it needs, or use a "
            f"different server."
        ) from exc

    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list:
    return sorted(set(globals()) | set(_LAZY_EXPORTS))
