from datetime import datetime

import pytest

from fundexpert.pipeline import run_pipeline
from fundexpert.cli import DATA_ROOT
from fundexpert.data.loader import load_candidates_for_universe

def _load_one(universe):
    return load_candidates_for_universe(universe, DATA_ROOT)


@pytest.mark.parametrize("universe", ["tefas", "befas"])
def test_pipeline_runs_against_real_csvs(universe):
    from fundexpert.pipeline import PipelineConfig
    candidates = _load_one(universe)
    config = PipelineConfig(
        universe=universe,
        risk_level="medium",
        horizon="medium",
        volume_priority="medium",
        fee_priority="medium",
        n=5,
        max_per_type=2,
        now=datetime(2026, 5, 2, 11, 42),
        validate_schemas=True,
    )
    res = run_pipeline(
        candidates=candidates,
        config=config,
    )
    assert 0 < len(res.weighted) <= 5
    assert sum(res.weighted["display_weight_pct"]) == pytest.approx(100.0, abs=0.05)
    assert res.header["candidate_total"] > 0
    assert res.header["candidate_kept"] > 0
    assert (res.weighted["risk"].between(1, 7)).all()
    # News disabled by default in smoke test.
    assert res.hits_for_render == {}


def test_pipeline_long_horizon_drops_funds_with_no_long_history():
    from fundexpert.pipeline import PipelineConfig
    candidates = _load_one("tefas")
    config = PipelineConfig(
        universe="tefas",
        risk_level="high",
        horizon="long",
        volume_priority="low",
        fee_priority="high",
        n=5,
        max_per_type=2,
        now=datetime(2026, 5, 2, 11, 42),
        validate_schemas=True,
    )
    res = run_pipeline(
        candidates=candidates,
        config=config,
    )
    assert res.header["excluded_horizon"] > 0
    assert len(res.weighted) > 0
