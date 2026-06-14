import pandas as pd
import numpy as np
import pytest

from fundexpert.scoring.horizon import apply_horizon
from fundexpert.config import DEFAULT_SCORING_CONFIG


@pytest.fixture
def candidates():
    return pd.DataFrame({
        "fon_kodu": ["A", "B", "C", "D"],
        "ret_1m":  [4.0,  6.0, 2.0,  float("nan")],
        "ret_3m":  [2.0,  4.0, 1.0,  float("nan")],
        "ret_6m":  [10.0, 12.0, 5.0, 8.0],
        "ret_ytd": [14.0, 16.0, 7.0, 9.0],
        "ret_1y":  [40.0, 50.0, 15.0, 20.0],
        "ret_3y":  [200.0, 300.0, float("nan"), 100.0],
        "ret_5y":  [600.0, float("nan"), float("nan"), 200.0],
    })


def test_short_horizon_uses_1m_and_3m(candidates):
    out, _ = apply_horizon(candidates, "short", DEFAULT_SCORING_CONFIG)
    assert out.loc[out["fon_kodu"] == "A", "R"].iloc[0] == 3.0


def test_medium_horizon_uses_6m_1y(candidates):
    out, _ = apply_horizon(candidates, "medium", DEFAULT_SCORING_CONFIG)
    expected_b = (12.0 + 50.0) / 2
    assert out.loc[out["fon_kodu"] == "B", "R"].iloc[0] == pytest.approx(expected_b)


def test_long_horizon_keeps_incomplete_data_if_minimum_met():
    # Enforcing minimum track record: if the first column exists, row is kept.
    df = pd.DataFrame({
        "fon_kodu": ["A"],
        "ret_3y": [30.0],
        "ret_5y": [np.nan],
    })
    out, excl = apply_horizon(df, "long", DEFAULT_SCORING_CONFIG)
    assert len(out) == 1
    assert out["R"].iloc[0] == 30.0
    assert excl == 0


def test_long_horizon_excludes_fund_with_all_bucket_nans(candidates):
    out, _ = apply_horizon(candidates, "long", DEFAULT_SCORING_CONFIG)
    assert "C" not in out["fon_kodu"].values


def test_short_horizon_excludes_fund_with_all_bucket_nans(candidates):
    out, _ = apply_horizon(candidates, "short", DEFAULT_SCORING_CONFIG)
    assert "D" not in out["fon_kodu"].values


def test_excluded_count_returned():
    df = pd.DataFrame({
        "fon_kodu": ["X", "Y"],
        "ret_3y": [float("nan"), 10.0],
        "ret_5y": [float("nan"), 20.0],
    })
    out, excl = apply_horizon(df, "long", DEFAULT_SCORING_CONFIG)
    assert excl == 1
