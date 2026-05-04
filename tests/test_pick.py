import pandas as pd
import pytest

from fundexpert.select.pick import pick_top


@pytest.fixture
def scored():
    return pd.DataFrame({
        "fon_kodu":  ["A", "B", "C", "D", "E", "F"],
        "strategy":  ["X", "X", "X", "Y", "Y", "Z"],
        "score":     [0.9, 0.85, 0.8, 0.7, 0.6, 0.5],
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
    empty = pd.DataFrame(columns=["fon_kodu", "strategy", "score"])
    out, warning = pick_top(empty, n=3, max_per_type=2)
    assert len(out) == 0
    assert warning is not None


def test_pick_top_caps_on_strategy_not_umbrella():
    """Funds across different umbrellas but same strategy must respect the cap.

    Reproduces the screenshot bug: 6 PARA PİYASASI funds spread over Katılım /
    Serbest / Para Piyasası umbrellas were all selected because the cap was on
    umbrella_type. With strategy-based capping (max=2), only 2 should land.
    """
    df = pd.DataFrame({
        "fon_kodu":      ["RRP", "PIP", "TLV", "YIK", "ZBJ", "OSD"],
        "umbrella_type": ["Katılım", "Serbest", "Katılım", "Serbest", "Para Piyasası", "Borçlanma"],
        "strategy":      ["money_market"] * 5 + ["debt"],
        "score":         [0.58, 0.35, 0.35, 0.35, 0.34, 0.30],
    })
    out, _ = pick_top(df, n=4, max_per_type=2)
    assert list(out["fon_kodu"]) == ["RRP", "PIP", "OSD"]


def test_pick_top_caps_on_sector_across_strategies():
    """Reproduces the BEFAS tech-concentration bug: 5 picks, 5 different
    strategies (equity/fund_of_funds/mixed), but all sector=tech. The
    per-strategy cap is satisfied yet the portfolio is single-sector.

    With max_per_sector=2 only the top 2 tech funds qualify; the rest must
    come from different sectors (or 'diversified', which is exempt).
    """
    df = pd.DataFrame({
        "fon_kodu": ["YZD", "BHT", "MEV", "BZY", "AVR", "DIV"],
        "strategy": ["fund_of_funds", "equity", "fund_of_funds", "mixed", "mixed", "mixed"],
        "sector":   ["tech", "tech", "tech", "tech", "tech", "diversified"],
        "score":    [0.85, 0.82, 0.81, 0.80, 0.79, 0.50],
    })
    out, _ = pick_top(df, n=4, max_per_type=2, max_per_sector=2)
    # Only 2 tech funds (top scoring), then DIV (diversified is exempt).
    assert list(out["fon_kodu"]) == ["YZD", "BHT", "DIV"]


def test_pick_top_does_not_cap_diversified_sector():
    """'diversified' funds (no sector keyword) should never hit the sector cap."""
    df = pd.DataFrame({
        "fon_kodu": ["A", "B", "C", "D", "E"],
        "strategy": ["mixed", "equity", "debt", "fund_of_funds", "money_market"],
        "sector":   ["diversified"] * 5,
        "score":    [0.9, 0.8, 0.7, 0.6, 0.5],
    })
    out, _ = pick_top(df, n=5, max_per_type=2, max_per_sector=1)
    assert list(out["fon_kodu"]) == ["A", "B", "C", "D", "E"]


def test_pick_top_sector_cap_is_optional_for_legacy_callers():
    """Callers without a sector column or max_per_sector must still work."""
    df = pd.DataFrame({
        "fon_kodu": ["A", "B", "C"],
        "strategy": ["X", "X", "Y"],
        "score":    [0.9, 0.8, 0.7],
    })
    out, _ = pick_top(df, n=3, max_per_type=2)  # no max_per_sector
    assert list(out["fon_kodu"]) == ["A", "B", "C"]
