"""
Coordination Package
High-level coordinators that orchestrate modular components.
"""

from .hybrid_coordinator import HybridCoordinator, get_hybrid_coordinator

__all__ = [
    'HybridCoordinator',
    'get_hybrid_coordinator'
] 