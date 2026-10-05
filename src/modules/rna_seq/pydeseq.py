"""DESeq2 differential expression via pydeseq2.

This is the real implementation. `src/mcp/servers/rnaseq_server.py` used to
ignore it and return `significant_genes = int(n_genes * 0.1)` — a hardcoded
10% — with `success: True`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from pydeseq2.dds import DeseqDataSet
from pydeseq2.default_inference import DefaultInference
from pydeseq2.ds import DeseqStats

_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:  # pragma: no cover - import plumbing
    sys.path.insert(0, str(_SRC))

from gliaent.analysis import AnalysisParams  # noqa: E402

#: Genes with fewer total counts than this across all samples are dropped
#: before fitting, per the DESeq2 authors' guidance on independent filtering.
MIN_TOTAL_COUNTS = 10


def run_pydeseq2(
    counts_df: pd.DataFrame,
    metadata_df: pd.DataFrame,
    condition_column: str = "condition",
    params: Optional[AnalysisParams] = None,
    n_cpus: Optional[int] = None,
) -> pd.DataFrame:
    """Run a two-condition DESeq2 analysis.

    Args:
        counts_df: Raw integer counts, genes x samples. Must not be
            normalised — DESeq2 models counts directly.
        metadata_df: Indexed by sample id, containing `condition_column`.
        condition_column: Column holding the two condition labels.
        params: Significance cutoffs. Defaults to `AnalysisParams()`. The
            `alpha` is applied to `padj`, never to the raw p-value.
        n_cpus: Inference parallelism. Defaults to the machine's CPU count
            (was previously hardcoded to 4, which oversubscribed small
            containers and underused large ones).

    Returns:
        The DESeq2 results frame with added `gene`, `-log10(padj)` and
        `significant` columns, plus a `gliaent_params` attribute recording
        the cutoffs used.

    Raises:
        ValueError: If no samples are shared, the condition column is
            missing, or the comparison is not two-group. These were
            previously bare `assert`s, which vanish under `python -O`.
    """
    params = params or AnalysisParams()

    counts_df = counts_df.copy()
    metadata_df = metadata_df.copy()
    counts_df.columns = counts_df.columns.astype(str).str.strip()
    metadata_df.index = metadata_df.index.astype(str).str.strip()

    if condition_column not in metadata_df.columns:
        raise ValueError(
            f"condition column {condition_column!r} not in metadata "
            f"(have: {list(metadata_df.columns)})"
        )

    # Preserve the counts matrix column order rather than using set(), which
    # is non-deterministic across runs and silently reorders samples.
    common_samples = [s for s in counts_df.columns if s in metadata_df.index]
    if not common_samples:
        raise ValueError(
            "no sample ids shared between counts columns and metadata index; "
            "counts must be genes x samples"
        )

    counts_t = counts_df[common_samples].T
    metadata_df = metadata_df.loc[common_samples]

    counts_t = counts_t.loc[:, counts_t.sum(axis=0) >= MIN_TOTAL_COUNTS]
    if counts_t.shape[1] == 0:
        raise ValueError(
            f"no genes have at least {MIN_TOTAL_COUNTS} total counts; "
            "check that the matrix holds raw counts, not normalised values"
        )

    conditions = metadata_df[condition_column].dropna().unique().tolist()
    if len(conditions) != 2:
        raise ValueError(
            f"DESeq2 here supports exactly 2 conditions, found {len(conditions)}: "
            f"{conditions}"
        )

    inference = DefaultInference(n_cpus=n_cpus or _default_cpus())

    dds = DeseqDataSet(
        counts=counts_t,
        metadata=metadata_df,
        design=f"~{condition_column}",
        refit_cooks=True,
        inference=inference,
    )
    dds.deseq2()

    stats = DeseqStats(
        dds,
        contrast=[condition_column, conditions[1], conditions[0]],
        inference=inference,
    )
    stats.summary()
    results = stats.results_df.copy()

    # -log10 of a missing padj is undefined; keep it NaN rather than
    # collapsing it to 0, which plots as "not significant at all" and is
    # indistinguishable from a real padj of 1.0.
    with np.errstate(divide="ignore"):
        results["-log10(padj)"] = -np.log10(
            results["padj"].where(results["padj"] > 0)
        )

    results["significant"] = (
        results["padj"].lt(params.alpha)
        & results["log2FoldChange"].abs().ge(params.log2fc_threshold)
    ).fillna(False)
    results["gene"] = results.index

    results.attrs["gliaent_params"] = params.to_dict()
    results.attrs["gliaent_contrast"] = f"{conditions[1]} vs {conditions[0]}"
    return results


def _default_cpus() -> int:
    import os

    return max(1, (os.cpu_count() or 2) - 1)
