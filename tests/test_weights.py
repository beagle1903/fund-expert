import pandas as pd
import pytest

from fundexpert.select.weights import compute_weights


def test_weights_sum_to_100_and_are_multiples_of_5():
    df = pd.DataFrame({"fon_kodu": ["A", "B", "C"], "score": [0.9, 0.6, 0.3]})
    out = compute_weights(df)
    weights = out["display_weight_pct"].tolist()
    assert sum(weights) == 100
    assert all(int(w) % 5 == 0 for w in weights)


def test_positive_scores_proportional():
    df = pd.DataFrame({"fon_kodu": ["A", "B", "C"], "score": [0.9, 0.6, 0.3]})
    out = compute_weights(df)
    weights = out["display_weight_pct"].tolist()
    assert weights[0] > weights[1] > weights[2]


def test_every_selected_fund_gets_at_least_5_percent():
    """Even funds with very low or negative scores must show at least 5%."""
    df = pd.DataFrame({"fon_kodu": ["A", "B"], "score": [0.5, -0.2]})
    out = compute_weights(df)
    weights = out["display_weight_pct"].tolist()
    assert all(w >= 5 for w in weights)
    assert sum(weights) == 100


def test_equal_scores_yield_near_equal_weights():
    df = pd.DataFrame({"fon_kodu": ["A", "B", "C"], "score": [0.5, 0.5, 0.5]})
    out = compute_weights(df)
    weights = sorted(out["display_weight_pct"].tolist())
    # Step is 5, so the closest possible equal-ish split of 100 across 3 is 30/35/35
    assert weights == [30, 35, 35]


def test_single_fund_gets_full_weight():
    df = pd.DataFrame({"fon_kodu": ["A"], "score": [0.7]})
    out = compute_weights(df)
    assert out["display_weight_pct"].iloc[0] == 100


def test_clustered_scores_produce_clustered_weights():
    """Top fund should not dominate when scores are tightly clustered."""
    df = pd.DataFrame({
        "fon_kodu": ["A", "B", "C", "D", "E", "F", "G", "H"],
        "score":    [0.58, 0.35, 0.35, 0.34, 0.34, 0.34, 0.33, 0.33],
    })
    out = compute_weights(df).sort_values("score", ascending=False)
    weights = out["display_weight_pct"].tolist()
    assert weights[0] / weights[-1] < 3.0
    assert weights[0] <= 25
    assert all(int(w) % 5 == 0 for w in weights)
    assert sum(weights) == 100


def test_handles_n_equals_max_20():
    """With N=20 and 5% min, every fund must get exactly 5%."""
    df = pd.DataFrame({
        "fon_kodu": [f"F{i}" for i in range(20)],
        "score":    [0.5 - i * 0.01 for i in range(20)],
    })
    out = compute_weights(df)
    assert out["display_weight_pct"].tolist() == [5] * 20
