import pandas as pd
import pytest

from fundexpert.select.weights import compute_weights


def test_positive_scores_proportional():
    df = pd.DataFrame({"fon_kodu": ["A", "B", "C"], "score": [0.9, 0.6, 0.3]})
    out = compute_weights(df)
    weights = out["display_weight_pct"].tolist()
    assert sum(weights) == pytest.approx(100.0)
    assert weights[0] > weights[1] > weights[2]


def test_negative_score_still_gets_nonzero_weight():
    df = pd.DataFrame({"fon_kodu": ["A", "B"], "score": [0.5, -0.2]})
    out = compute_weights(df)
    assert (out["display_weight_pct"] > 0).all()
    assert sum(out["display_weight_pct"]) == pytest.approx(100.0)


def test_equal_scores_yield_equal_weights():
    df = pd.DataFrame({"fon_kodu": ["A", "B", "C"], "score": [0.5, 0.5, 0.5]})
    out = compute_weights(df)
    assert sum(out["display_weight_pct"]) == pytest.approx(100.0)
    # Each should be ~33.3 with one absorbing the rounding delta
    weights = sorted(out["display_weight_pct"].tolist())
    assert weights[0] == pytest.approx(33.3)
    assert weights[1] == pytest.approx(33.3)
    assert weights[2] == pytest.approx(33.4)


def test_single_fund_gets_full_weight():
    df = pd.DataFrame({"fon_kodu": ["A"], "score": [0.7]})
    out = compute_weights(df)
    assert out["display_weight_pct"].iloc[0] == 100.0


def test_clustered_scores_produce_clustered_weights():
    """Top fund should not dominate when scores are tightly clustered.

    Reproduces the deployed-portfolio bug: scores [0.58, 0.35, 0.35, 0.34, 0.34,
    0.34, 0.33, 0.33] used to put 65.7% in the top fund because weights subtracted
    min before normalising. With raw-proportional weighting, the top weight should
    be at most ~2× the smallest, matching the underlying score ratio.
    """
    df = pd.DataFrame({
        "fon_kodu": ["A", "B", "C", "D", "E", "F", "G", "H"],
        "score":    [0.58, 0.35, 0.35, 0.34, 0.34, 0.34, 0.33, 0.33],
    })
    out = compute_weights(df).sort_values("score", ascending=False)
    weights = out["display_weight_pct"].tolist()
    # Top fund's weight must be within 2.5× the smallest (score ratio is ~1.76×)
    assert weights[0] / weights[-1] < 2.5
    # And the top fund should be well under 30% with N=8
    assert weights[0] < 30.0
