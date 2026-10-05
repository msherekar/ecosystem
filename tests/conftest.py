"""Shared test fixtures.

Adds `src/` to the path so tests run against the working tree without
requiring an editable install.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def null_dataset():
    """Features x samples drawn from ONE distribution, i.e. no real effect.

    The point of this fixture: a correct differential test finds roughly
    `alpha` false positives here and nothing more. The `np.random` code this
    replaces reported ~hundreds of "significant" hits on data like this.
    """
    rng = np.random.default_rng(1234)
    n_features, n_per_group = 500, 6
    samples = [f"a{i}" for i in range(n_per_group)] + [
        f"b{i}" for i in range(n_per_group)
    ]
    data = pd.DataFrame(
        rng.normal(10.0, 1.0, size=(n_features, 2 * n_per_group)),
        index=[f"P{i:05d}" for i in range(n_features)],
        columns=samples,
    )
    metadata = pd.DataFrame(
        {"condition": ["control"] * n_per_group + ["treated"] * n_per_group},
        index=samples,
    )
    return data, metadata


@pytest.fixture
def spiked_dataset():
    """Like `null_dataset` but with 20 features given a real 4x increase."""
    rng = np.random.default_rng(99)
    n_features, n_per_group = 300, 8
    samples = [f"a{i}" for i in range(n_per_group)] + [
        f"b{i}" for i in range(n_per_group)
    ]
    values = rng.normal(10.0, 0.5, size=(n_features, 2 * n_per_group))
    spiked = [f"P{i:05d}" for i in range(20)]
    values[:20, n_per_group:] *= 4.0
    data = pd.DataFrame(
        values,
        index=[f"P{i:05d}" for i in range(n_features)],
        columns=samples,
    )
    metadata = pd.DataFrame(
        {"condition": ["control"] * n_per_group + ["treated"] * n_per_group},
        index=samples,
    )
    return data, metadata, spiked
