import pandas as pd
import pytest

from fundexpert.select.pick import pick_top


@pytest.fixture
def scored():
    return pd.DataFrame({
        "fon_kodu":      ["A", "B", "C", "D", "E", "F"],
        "umbrella_type": ["X", "X", "X", "Y", "Y", "Z"],
        "score":         [0.9, 0.85, 0.8, 0.7, 0.6, 0.5],
    })


def test_pick_top_returns_n_when_cap_allows(scored):
    out, warning = pick_top(scored, n=3, max_per_type=2)
    assert list(out["fon_kodu"]) == ["A", "B", "D"]
    assert warning is None


def test_pick_top_respects_cap_and_skips_capped_types(scored):
    out, warning = pick_top(scored, n=4, max_per_type=2)
    assert list(out["fon_kodu"]) == ["A", "B", "D", "E"]
    assert warning is None


def test_pick_top_returns_partial_with_warning_when_cap_blocks(scored):
    out, warning = pick_top(scored, n=5, max_per_type=1)
    assert list(out["fon_kodu"]) == ["A", "D", "F"]
    assert warning is not None
    assert "3 of requested 5" in warning


def test_pick_top_returns_empty_when_pool_empty():
    empty = pd.DataFrame(columns=["fon_kodu", "umbrella_type", "score"])
    out, warning = pick_top(empty, n=3, max_per_type=2)
    assert len(out) == 0
    assert warning is not None
