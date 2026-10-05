"""Analysis primitives: parameters, statistics, and result containers."""

from .params import AnalysisParams, MultipleTestingMethod
from .stats import DifferentialResult, adjust_pvalues, differential_expression

__all__ = [
    "AnalysisParams",
    "MultipleTestingMethod",
    "DifferentialResult",
    "adjust_pvalues",
    "differential_expression",
]
