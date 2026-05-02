import pandas as pd
import pytest

from fundexpert.scoring.score import score_candidates


@pytest.fixture
def horizon_ready():
    return pd.DataFrame({
        "fon_kodu": ["A", "B", "C"],
        "umbrella_type": ["X", "Y", "Z"],
        "R":                          [10.0, 30.0, 20.0],
        "aum_change_pct":             [5.0, -2.0, 8.0],
        "applied_management_fee_pct": [1.0, 2.0, 0.5],
        "risk":                       [3, 6, 2],
    })


def test_score_returns_score_column(horizon_ready):
    out = score_candidates(horizon_ready,
                           volume_priority="medium",
                           fee_priority="medium",
                           risk_priority="medium")
    assert "score" in out.columns
    assert len(out) == 3


def test_higher_R_with_equal_other_features_scores_higher():
    df = pd.DataFrame({
        "fon_kodu": ["LO", "HI"],
        "umbrella_type": ["X", "X"],
        "R":                          [10.0, 50.0],
        "aum_change_pct":             [0.0, 0.0],
        "applied_management_fee_pct": [1.0, 1.0],
        "risk":                       [3, 3],
    })
    out = score_candidates(df, "medium", "medium", "medium")
    hi = out.loc[out["fon_kodu"] == "HI", "score"].iloc[0]
    lo = out.loc[out["fon_kodu"] == "LO", "score"].iloc[0]
    assert hi > lo


def test_higher_risk_loses_score_under_high_risk_priority():
    df = pd.DataFrame({
        "fon_kodu": ["L", "H"],
        "umbrella_type": ["X", "X"],
        "R":                          [10.0, 10.0],
        "aum_change_pct":             [0.0, 0.0],
        "applied_management_fee_pct": [1.0, 1.0],
        "risk":                       [1, 7],
    })
    out = score_candidates(df, "medium", "medium", risk_priority="high")
    low_risk = out.loc[out["fon_kodu"] == "L", "score"].iloc[0]
    high_risk = out.loc[out["fon_kodu"] == "H", "score"].iloc[0]
    assert low_risk > high_risk
    assert pytest.approx(low_risk - high_risk, abs=1e-6) == 0.60


def test_lower_fee_scores_higher(horizon_ready):
    out = score_candidates(horizon_ready, "medium", "high", "low")
    out_sorted = out.sort_values("score", ascending=False)
    assert out_sorted.iloc[0]["fon_kodu"] == "C"


def test_breakdown_dict_per_fund(horizon_ready):
    out = score_candidates(horizon_ready, "medium", "medium", "medium")
    assert "_breakdown" in out.columns
    bd = out.iloc[0]["_breakdown"]
    assert set(bd.keys()) == {"base_score", "R_contrib", "V_contrib",
                              "F_contrib", "risk_penalty", "score"}
