"""AnalysisParams validation and serialisation."""

import dataclasses

import pytest

from gliaent.analysis import AnalysisParams, MultipleTestingMethod


@pytest.mark.parametrize("alpha", [0.0, 1.0, -0.1, 1.5])
def test_alpha_must_be_a_probability(alpha):
    with pytest.raises(ValueError, match="alpha"):
        AnalysisParams(alpha=alpha)


def test_negative_fold_change_threshold_rejected():
    with pytest.raises(ValueError, match="log2fc_threshold"):
        AnalysisParams(log2fc_threshold=-1.0)


def test_min_count_below_two_rejected():
    # Fewer than 2 observations per group has no variance, so no test.
    with pytest.raises(ValueError, match="min_count"):
        AnalysisParams(min_count=1)


def test_defaults_correct_for_multiple_testing():
    # Regression guard: the default must never silently become uncorrected.
    params = AnalysisParams()
    assert params.multiple_testing is MultipleTestingMethod.BENJAMINI_HOCHBERG
    assert params.corrects_for_multiple_testing


def test_uncorrected_is_flagged_loudly_in_description():
    described = AnalysisParams(multiple_testing="none").describe()
    assert "UNCORRECTED" in described


def test_round_trips_through_dict():
    params = AnalysisParams(alpha=0.01, log2fc_threshold=0.5, seed=7)
    assert AnalysisParams.from_dict(params.to_dict()) == params


def test_to_dict_is_json_serialisable():
    import json

    json.dumps(AnalysisParams().to_dict())


def test_is_frozen():
    # Params recorded in a run log must not be mutable afterwards.
    params = AnalysisParams()
    with pytest.raises(dataclasses.FrozenInstanceError):
        params.alpha = 0.1


def test_string_multiple_testing_is_coerced():
    assert AnalysisParams(multiple_testing="bonferroni").multiple_testing is (
        MultipleTestingMethod.BONFERRONI
    )
