import pandas as pd
import pytest

from fundexpert.scoring.score import score_candidates
from fundexpert.config import DEFAULT_SCORING_CONFIG
from hypothesis import given, settings
import hypothesis.strategies as st


@pytest.fixture
def horizon_ready():
    return pd.DataFrame({
        "fon_kodu": ["A", "B", "C"],
        "umbrella_type": ["X", "Y", "Z"],
        "R":                          [10.0, 30.0, 20.0],
        "aum_last":             [5.0, -2.0, 8.0],
        "applied_management_fee_pct": [1.0, 2.0, 0.5],
        "risk":                       [3, 6, 2],
        "universe":                   ["tefas", "tefas", "tefas"],
        "fon_adi":                    ["A", "B", "C"],
        "units_change_pct":           [0, 0, 0],
    })


def test_score_returns_score_column(horizon_ready):
    out = score_candidates(horizon_ready,
                           volume_priority="medium",
                           fee_priority="medium",
                           momentum_priority="medium",
                           risk_level="medium",
                           scoring_config=DEFAULT_SCORING_CONFIG)
    assert "score" in out.columns
    assert len(out) == 3


def test_higher_R_with_equal_other_features_scores_higher():
    df = pd.DataFrame({
        "fon_kodu": ["LO", "HI"],
        "umbrella_type": ["X", "X"],
        "R":                          [10.0, 50.0],
        "aum_last":             [0.0, 0.0],
        "applied_management_fee_pct": [1.0, 1.0],
        "risk":                       [3, 3],
        "universe":                   ["tefas", "tefas"],
        "fon_adi":                    ["A", "B"],
        "units_change_pct":           [0, 0],
    })
    out = score_candidates(df, "medium", "medium", "medium", "medium", scoring_config=DEFAULT_SCORING_CONFIG)
    hi = out.loc[out["fon_kodu"] == "HI", "score"].iloc[0]
    lo = out.loc[out["fon_kodu"] == "LO", "score"].iloc[0]
    assert hi > lo


def test_higher_risk_loses_score_under_low_risk_level():
    """When user wants 'low' risk level, λ is large (0.60) so risky funds lose
    the most score: a SRRI-7 fund should score 0.60 below a SRRI-1 fund."""
    df = pd.DataFrame({
        "fon_kodu": ["L", "H"],
        "umbrella_type": ["X", "X"],
        "R":                          [10.0, 10.0],
        "aum_last":             [0.0, 0.0],
        "applied_management_fee_pct": [1.0, 1.0],
        "risk":                       [1, 7],
        "universe":                   ["tefas", "tefas"],
        "fon_adi":                    ["A", "B"],
        "units_change_pct":           [0, 0],
    })
    out = score_candidates(df, "medium", "medium", "medium", risk_level="low", scoring_config=DEFAULT_SCORING_CONFIG)
    low_risk = out.loc[out["fon_kodu"] == "L", "score"].iloc[0]
    high_risk = out.loc[out["fon_kodu"] == "H", "score"].iloc[0]
    assert low_risk > high_risk
    assert pytest.approx(low_risk - high_risk, abs=1e-6) == 0.60


def test_high_risk_level_barely_penalises_risky_funds():
    """When user wants 'high' risk level, λ is tiny (0.05) so the penalty
    gap between SRRI-7 and SRRI-1 is only 0.05."""
    df = pd.DataFrame({
        "fon_kodu": ["L", "H"],
        "umbrella_type": ["X", "X"],
        "R":                          [10.0, 10.0],
        "aum_last":             [0.0, 0.0],
        "applied_management_fee_pct": [1.0, 1.0],
        "risk":                       [1, 7],
        "universe":                   ["tefas", "tefas"],
        "fon_adi":                    ["A", "B"],
        "units_change_pct":           [0, 0],
    })
    out = score_candidates(df, "medium", "medium", "medium", risk_level="high", scoring_config=DEFAULT_SCORING_CONFIG)
    low_risk = out.loc[out["fon_kodu"] == "L", "score"].iloc[0]
    high_risk = out.loc[out["fon_kodu"] == "H", "score"].iloc[0]
    assert pytest.approx(low_risk - high_risk, abs=1e-6) == 0.05


def test_lower_fee_scores_higher():
    df = pd.DataFrame({
        "fon_kodu": ["A", "B", "C"],
        "umbrella_type": ["X", "X", "X"],
        "R":                          [10.0, 10.0, 10.0],
        "aum_last":             [5.0, 5.0, 5.0],
        "applied_management_fee_pct": [3.0, 2.0, 1.0],
        "risk":                       [3, 3, 3],
        "universe":                   ["tefas", "tefas", "tefas"],
        "fon_adi":                    ["A", "B", "C"],
        "units_change_pct":           [0, 0, 0],
    })
    out = score_candidates(df, "medium", "high", "medium", "low", scoring_config=DEFAULT_SCORING_CONFIG)
    out_sorted = out.sort_values("score", ascending=False)
    assert out_sorted.iloc[0]["fon_kodu"] == "C"


def test_score_handles_empty_dataframe():
    df = pd.DataFrame(columns=["fon_kodu", "R", "aum_last", "applied_management_fee_pct", "risk", "fon_adi", "umbrella_type", "universe", "units_change_pct"])
    out = score_candidates(df, "medium", "medium", "medium", "medium", scoring_config=DEFAULT_SCORING_CONFIG)
    assert out.empty
    assert "score" in out.columns

@given(
    R=st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    V=st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    F=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    risk=st.integers(min_value=1, max_value=7),
)
@settings(max_examples=50, deadline=None)
def test_score_bounds_invariant(R, V, F, risk):
    df = pd.DataFrame({
        "fon_kodu": ["A", "B"],
        "R": [R, 0.0],
        "aum_last": [V, 0.0],
        "applied_management_fee_pct": [F, 1.0],
        "risk": [risk, 3],
        "fon_adi": ["A", "B"],
        "umbrella_type": ["X", "X"],
        "universe": ["tefas", "tefas"],
        "units_change_pct": [0, 0],
    })
    out = score_candidates(df, "medium", "medium", "medium", "medium", scoring_config=DEFAULT_SCORING_CONFIG)
    score = out.loc[0, "score"]
    assert -2.0 <= score <= 2.0

@given(
    R1=st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    R2=st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=20, deadline=None)
def test_score_monotonicity_invariant(R1, R2):
    if R1 == R2:
        return
    df = pd.DataFrame({
        "fon_kodu": ["A", "B", "C"],
        "R": [R1, R2, min(R1,R2)-1],
        "aum_last": [0.0, 0.0, 0.0],
        "applied_management_fee_pct": [1.0, 1.0, 1.0],
        "risk": [3, 3, 3],
        "fon_adi": ["A", "B", "C"],
        "umbrella_type": ["X", "X", "X"],
        "universe": ["tefas", "tefas", "tefas"],
        "units_change_pct": [0, 0, 0],
    })
    out = score_candidates(df, "medium", "medium", "medium", "medium", scoring_config=DEFAULT_SCORING_CONFIG)
    s1 = out.loc[0, "score"]
    s2 = out.loc[1, "score"]
    if R1 > R2:
        assert s1 >= s2
    elif R1 < R2:
        assert s1 <= s2

@given(
    F1=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    F2=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=20, deadline=None)
def test_score_fee_monotonicity_invariant(F1, F2):
    if F1 == F2: return
    df = pd.DataFrame({
        "fon_kodu": ["A", "B"],
        "R": [0.0, 0.0],
        "aum_last": [10.0, 10.0],
        "applied_management_fee_pct": [F1, F2],
        "risk": [3, 3],
        "fon_adi": ["A", "B"],
        "umbrella_type": ["X", "X"],
        "universe": ["tefas", "tefas"],
        "units_change_pct": [0, 0],
    })
    out = score_candidates(df, "medium", "medium", "medium", "medium", scoring_config=DEFAULT_SCORING_CONFIG)
    s1 = out.loc[0, "score"]
    s2 = out.loc[1, "score"]
    if F1 > F2:
        assert s1 <= s2
    elif F1 < F2:
        assert s1 >= s2

import numpy as np

def test_score_handles_all_nan_columns():
    df = pd.DataFrame({
        "fon_kodu": ["A", "B", "C"],
        "umbrella_type": ["X", "X", "X"],
        "R": [10.0, 20.0, 30.0],
        "aum_last": [np.nan, np.nan, np.nan],
        "applied_management_fee_pct": [np.nan, np.nan, np.nan],
        "risk": [3, 4, 5],
        "fon_adi": ["A", "B", "C"],
        "universe": ["tefas", "tefas", "tefas"],
        "units_change_pct": [0, 0, 0],
    })
    out = score_candidates(df, "medium", "medium", "medium", "medium", scoring_config=DEFAULT_SCORING_CONFIG)
    assert not out.empty
    assert "score" in out.columns
    assert np.isfinite(out["score"]).all()
