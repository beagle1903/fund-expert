from datetime import datetime

import pandas as pd
import pytest

from fundexpert.data.loader import UniverseData, load_universe
from fundexpert.data.merge import merge_universe
from fundexpert.fund_scope import (
    OPEN_TO_PLATFORM_COLUMN,
    FundScopeUnavailableError,
    filter_by_fund_scope,
)
from fundexpert.pipeline import PipelineConfig, run_pipeline


def _frames(fixtures_dir, open_codes=None) -> UniverseData:
    frames = load_universe(
        getiri_path=fixtures_dir / "getiri_small.csv",
        buyukluk_path=fixtures_dir / "buyukluk_small.csv",
        yonetim_path=fixtures_dir / "yonetim_small.csv",
    )
    frames.open_codes = open_codes
    return frames


def _config(universe, **overrides) -> PipelineConfig:
    return PipelineConfig(
        universe=universe,
        risk_level="medium",
        horizon="medium",
        volume_priority="medium",
        fee_priority="medium",
        momentum_priority="medium",
        n=2,
        now=datetime(2026, 11, 2),
        **overrides,
    )


def test_merge_marks_open_funds_only_when_codes_are_known(fixtures_dir):
    known = merge_universe(_frames(fixtures_dir, frozenset({"AAA"})), "tefas")
    unknown = merge_universe(_frames(fixtures_dir), "tefas")

    assert known.set_index("fon_kodu")[OPEN_TO_PLATFORM_COLUMN].to_dict() == {
        "AAA": True,
        "BBB": False,
        "CCC": False,
    }
    assert OPEN_TO_PLATFORM_COLUMN not in unknown.columns


@pytest.mark.parametrize(
    ("scope", "expected"),
    [("open", ["AAA"]), ("all", ["AAA", "BBB"])],
)
def test_filter_uses_open_codes_when_known(scope, expected):
    candidates = pd.DataFrame(
        {"fon_kodu": ["AAA", "BBB"], OPEN_TO_PLATFORM_COLUMN: [True, False]}
    )

    filtered = filter_by_fund_scope(candidates, scope, "tefas")

    assert filtered["fon_kodu"].tolist() == expected


@pytest.mark.parametrize(
    ("universe", "served", "unavailable"),
    [("tefas", "open", "all"), ("befas", "all", "open")],
)
def test_filter_without_open_codes_serves_only_the_legacy_scope(
    universe, served, unavailable
):
    candidates = pd.DataFrame({"fon_kodu": ["AAA", "BBB"]})

    assert len(filter_by_fund_scope(candidates, served, universe)) == 2
    with pytest.raises(FundScopeUnavailableError, match=universe.upper()):
        filter_by_fund_scope(candidates, unavailable, universe)


@pytest.mark.parametrize(
    ("universe", "expected_total", "expected_scope"),
    [("tefas", 2, "open"), ("befas", 3, "all")],
)
def test_pipeline_without_a_scope_keeps_the_legacy_pool(
    fixtures_dir, universe, expected_total, expected_scope
):
    candidates = merge_universe(
        _frames(fixtures_dir, frozenset({"AAA", "BBB"})), universe
    )

    result = run_pipeline(candidates, _config(universe))

    assert result.header["candidate_total"] == expected_total
    assert result.header["fund_scope"] == expected_scope


def test_pipeline_never_picks_a_closed_fund_in_open_scope(fixtures_dir):
    candidates = merge_universe(
        _frames(fixtures_dir, frozenset({"AAA", "CCC"})), "befas"
    )

    result = run_pipeline(candidates, _config("befas", fund_scope="open"))

    assert set(result.weighted["fon_kodu"]) == {"AAA", "CCC"}
    assert result.header["fund_scope"] == "open"


def test_pipeline_validates_schemas_with_the_scope_column(fixtures_dir):
    candidates = merge_universe(
        _frames(fixtures_dir, frozenset({"AAA", "BBB"})), "tefas"
    )

    result = run_pipeline(
        candidates, _config("tefas", fund_scope="all", validate_schemas=True)
    )

    assert result.header["candidate_total"] == 3
