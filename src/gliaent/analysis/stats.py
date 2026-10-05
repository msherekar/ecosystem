"""Differential abundance statistics.

This module replaces the fabricated `np.random` "analysis" that previously
lived in the proteomics and ATAC-seq MCP servers. It computes real statistics
and, critically, always reports adjusted p-values alongside raw ones so a
caller cannot accidentally threshold on the wrong column.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from .params import AnalysisParams, MultipleTestingMethod

#: Added to a group mean before taking a ratio, so a zero mean does not produce
#: an infinite fold change. Chosen well below the smallest meaningful intensity
#: in label-free proteomics.
_PSEUDOCOUNT = 1e-9


def adjust_pvalues(
    pvalues: Sequence[float],
    method: MultipleTestingMethod = MultipleTestingMethod.BENJAMINI_HOCHBERG,
) -> np.ndarray:
    """Adjust p-values for multiple testing.

    NaN p-values (features that could not be tested) are excluded from the
    correction and returned as NaN, rather than being silently treated as 1.0
    — including them would inflate the denominator and make every other
    feature look more significant than it is.

    Args:
        pvalues: Raw p-values. May contain NaN.
        method: Adjustment method. `NONE` returns the input unchanged.

    Returns:
        Adjusted p-values, same length and order as the input.
    """
    raw = np.asarray(pvalues, dtype=float)
    if method is MultipleTestingMethod.NONE:
        return raw.copy()

    adjusted = np.full(raw.shape, np.nan, dtype=float)
    testable = ~np.isnan(raw)
    if not testable.any():
        return adjusted

    from statsmodels.stats.multitest import multipletests

    adjusted[testable] = multipletests(raw[testable], method=method.value)[1]
    return adjusted


@dataclass
class DifferentialResult:
    """Outcome of a differential abundance test.

    `table` has one row per feature with columns:
      feature, mean_group_a, mean_group_b, log2_fold_change, statistic,
      p_value, p_value_adjusted, significant, regulation

    `regulation` is one of "up", "down", "unchanged" and is consistent with
    `significant` by construction: a feature is only "up" or "down" if it
    passed both the adjusted-p and the fold-change threshold.
    """

    table: pd.DataFrame
    params: AnalysisParams
    group_a: str
    group_b: str
    n_tested: int
    n_skipped: int
    test: str

    @property
    def n_significant(self) -> int:
        return int(self.table["significant"].sum())

    def summary(self) -> Dict[str, Any]:
        """A result payload safe to return over an API.

        Includes the parameters that produced it, so a consumer never has to
        guess which cutoffs were applied.
        """
        sig = self.table["significant"]
        return {
            "test": self.test,
            "comparison": f"{self.group_b} vs {self.group_a}",
            "features_tested": self.n_tested,
            "features_skipped": self.n_skipped,
            "significant": int(sig.sum()),
            "upregulated": int((self.table["regulation"] == "up").sum()),
            "downregulated": int((self.table["regulation"] == "down").sum()),
            "params": self.params.to_dict(),
            "significance_criterion": self.params.describe(),
        }


def differential_expression(
    data: pd.DataFrame,
    metadata: pd.DataFrame,
    group_column: str,
    group_a: str | None = None,
    group_b: str | None = None,
    params: AnalysisParams | None = None,
    test: str = "welch_t",
) -> DifferentialResult:
    """Two-group differential abundance test.

    Args:
        data: Features x samples. Index is feature ids (protein/peak/gene),
            columns are sample ids. Values are assumed already normalised;
            this function does not normalise.
        metadata: Indexed by sample id, containing `group_column`.
        group_column: Column of `metadata` holding the group label.
        group_a: Reference group. Defaults to the first label encountered.
        group_b: Test group. Defaults to the second label encountered.
        params: Cutoffs. Defaults to `AnalysisParams()`.
        test: "welch_t" (unequal variances, the safe default), "student_t",
            or "mannwhitney" (rank-based, for small or non-normal samples).

    Returns:
        A `DifferentialResult`.

    Raises:
        ValueError: If the group column is missing, fewer than two groups are
            present, no samples overlap between `data` and `metadata`, or
            `test` is unknown.
    """
    params = params or AnalysisParams()

    if group_column not in metadata.columns:
        raise ValueError(
            f"group column {group_column!r} not in metadata "
            f"(have: {list(metadata.columns)})"
        )

    shared = [s for s in data.columns if s in metadata.index]
    if not shared:
        raise ValueError(
            "no sample ids shared between data columns and metadata index; "
            "check that the data matrix is features x samples, not samples x features"
        )

    labels = metadata.loc[shared, group_column]
    present = list(pd.unique(labels.dropna()))
    if len(present) < 2:
        raise ValueError(
            f"need at least 2 groups in {group_column!r} to compare, found {present}"
        )

    group_a = group_a if group_a is not None else present[0]
    group_b = group_b if group_b is not None else present[1]
    for g in (group_a, group_b):
        if g not in present:
            raise ValueError(f"group {g!r} not found in {group_column!r}: {present}")

    samples_a = [s for s in shared if labels[s] == group_a]
    samples_b = [s for s in shared if labels[s] == group_b]

    mat_a = data[samples_a].to_numpy(dtype=float)
    mat_b = data[samples_b].to_numpy(dtype=float)

    rows: List[Dict[str, Any]] = []
    n_skipped = 0

    for i, feature in enumerate(data.index):
        a = mat_a[i][~np.isnan(mat_a[i])]
        b = mat_b[i][~np.isnan(mat_b[i])]

        mean_a = float(np.mean(a)) if a.size else np.nan
        mean_b = float(np.mean(b)) if b.size else np.nan

        # A feature with too few observations, or no variance in either group,
        # is reported with a NaN p-value rather than a fabricated one.
        if a.size < params.min_count or b.size < params.min_count:
            n_skipped += 1
            statistic = p_value = np.nan
        else:
            statistic, p_value = _run_test(a, b, test)

        if np.isnan(mean_a) or np.isnan(mean_b):
            log2fc = np.nan
        else:
            log2fc = float(
                np.log2((abs(mean_b) + _PSEUDOCOUNT) / (abs(mean_a) + _PSEUDOCOUNT))
            )

        rows.append(
            {
                "feature": feature,
                "mean_group_a": mean_a,
                "mean_group_b": mean_b,
                "log2_fold_change": log2fc,
                "statistic": statistic,
                "p_value": p_value,
            }
        )

    table = pd.DataFrame(rows)
    table["p_value_adjusted"] = adjust_pvalues(
        table["p_value"].to_numpy(), params.multiple_testing
    )

    # Significance is defined once, here, against the ADJUSTED p-value, and
    # `regulation` is derived from it so the two can never disagree.
    passes_p = table["p_value_adjusted"] < params.alpha
    passes_fc = table["log2_fold_change"].abs() > params.log2fc_threshold
    table["significant"] = (passes_p & passes_fc).fillna(False)
    table["regulation"] = np.where(
        table["significant"] & (table["log2_fold_change"] > 0),
        "up",
        np.where(table["significant"] & (table["log2_fold_change"] < 0), "down", "unchanged"),
    )

    return DifferentialResult(
        table=table,
        params=params,
        group_a=str(group_a),
        group_b=str(group_b),
        n_tested=len(table) - n_skipped,
        n_skipped=n_skipped,
        test=test,
    )


def _run_test(a: np.ndarray, b: np.ndarray, test: str) -> tuple[float, float]:
    """Run one two-sample test, returning (statistic, p_value).

    Returns NaN for both when the test is undefined (e.g. zero variance in
    both groups), rather than letting scipy's warning-and-NaN behaviour pass
    silently as a real result.
    """
    if test in ("welch_t", "student_t"):
        if np.ptp(a) == 0 and np.ptp(b) == 0:
            return (np.nan, np.nan)
        result = scipy_stats.ttest_ind(b, a, equal_var=(test == "student_t"))
    elif test == "mannwhitney":
        if np.array_equal(np.unique(a), np.unique(b)) and np.ptp(a) == 0:
            return (np.nan, np.nan)
        result = scipy_stats.mannwhitneyu(b, a, alternative="two-sided")
    else:
        raise ValueError(
            f"unknown test {test!r}; expected 'welch_t', 'student_t' or 'mannwhitney'"
        )

    statistic = float(result.statistic)
    p_value = float(result.pvalue)
    if np.isnan(p_value):
        return (np.nan, np.nan)
    return (statistic, p_value)
