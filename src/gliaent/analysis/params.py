"""Analysis parameters.

Every statistical cutoff in Gliaent lives here rather than being hardcoded at
the call site. Three reasons:

1. A biochemist must be able to change alpha without editing plotting code.
2. A result is uninterpretable unless the cutoffs that produced it travel with
   it, so `AnalysisParams` is echoed into every result payload and written to
   the run log.
3. Clustering and dimensionality reduction are stochastic. Pinning `seed` is
   what makes a figure reproducible.
"""

from __future__ import annotations

import sys
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict


class MultipleTestingMethod(str, Enum):
    """Supported p-value adjustment methods.

    Values match `statsmodels.stats.multitest.multipletests` method names so
    they can be passed straight through.
    """

    BENJAMINI_HOCHBERG = "fdr_bh"
    BENJAMINI_YEKUTIELI = "fdr_by"
    BONFERRONI = "bonferroni"
    HOLM = "holm"
    NONE = "none"


@dataclass(frozen=True)
class AnalysisParams:
    """Cutoffs and settings for one analysis run.

    Frozen so a params object cannot be mutated after it has been recorded in
    a run log — if you need different settings, make a new one with
    `dataclasses.replace`.

    Attributes:
        alpha: Significance threshold, applied to ADJUSTED p-values.
        log2fc_threshold: Minimum absolute log2 fold change to call an effect.
            Applied together with `alpha`, never instead of it.
        multiple_testing: How raw p-values are adjusted. Defaults to
            Benjamini-Hochberg; `NONE` is permitted but must be chosen
            explicitly, because reporting raw p-values across thousands of
            features is the single most common statistical error in omics.
        seed: Random seed for every stochastic step (PCA, UMAP, Leiden,
            bootstraps). `None` means "not reproducible", which callers should
            treat as a warning rather than a default.
        min_count: Minimum observations per group required to test a feature.
    """

    alpha: float = 0.05
    log2fc_threshold: float = 1.0
    multiple_testing: MultipleTestingMethod = MultipleTestingMethod.BENJAMINI_HOCHBERG
    seed: int | None = 0
    min_count: int = 3

    def __post_init__(self) -> None:
        if not 0.0 < self.alpha < 1.0:
            raise ValueError(f"alpha must be in (0, 1), got {self.alpha!r}")
        if self.log2fc_threshold < 0.0:
            raise ValueError(
                f"log2fc_threshold must be >= 0, got {self.log2fc_threshold!r}"
            )
        if self.min_count < 2:
            raise ValueError(
                f"min_count must be >= 2 to compute a variance, got {self.min_count!r}"
            )
        # Accept a plain string so params can round-trip through JSON.
        if not isinstance(self.multiple_testing, MultipleTestingMethod):
            object.__setattr__(
                self, "multiple_testing", MultipleTestingMethod(self.multiple_testing)
            )

    @property
    def corrects_for_multiple_testing(self) -> bool:
        return self.multiple_testing is not MultipleTestingMethod.NONE

    def to_dict(self) -> Dict[str, Any]:
        """Serialise for a result payload or run-log entry."""
        out = asdict(self)
        out["multiple_testing"] = self.multiple_testing.value
        return out

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisParams":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})

    def describe(self) -> str:
        """One line fit for a plot caption or a log entry."""
        if self.corrects_for_multiple_testing:
            sig = f"adjusted p < {self.alpha} ({self.multiple_testing.value})"
        else:
            sig = f"RAW p < {self.alpha} (UNCORRECTED)"
        return f"{sig}, |log2FC| > {self.log2fc_threshold}, seed={self.seed}"


def environment_fingerprint() -> Dict[str, str]:
    """Library versions for the run log.

    Recorded alongside results because a figure is only reproducible if you
    know which scanpy or scipy produced it.
    """
    versions: Dict[str, str] = {
        "python": sys.version.split()[0],
    }
    for name in ("numpy", "scipy", "pandas", "statsmodels", "scanpy", "anndata"):
        try:
            versions[name] = __import__(name).__version__
        except Exception:
            # Absent is meaningful information; record it rather than omitting.
            versions[name] = "not installed"
    return versions
