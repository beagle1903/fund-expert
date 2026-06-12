from datetime import datetime

import pytest

from fundexpert.pipeline import run_pipeline
from fundexpert.cli import _load_one


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
    )
    selected, header, hits, _ = run_pipeline(
        candidates=candidates,
        config=config,
    )
    assert 0 < len(selected) <= 5
    assert sum(selected["display_weight_pct"]) == pytest.approx(100.0, abs=0.05)
    assert header["candidate_total"] > 0
    assert header["candidate_kept"] > 0
    assert (selected["risk"].between(1, 7)).all()
    # News disabled by default in smoke test.
    assert hits == {}


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
    )
    selected, header, _, _ = run_pipeline(
        candidates=candidates,
        config=config,
    )
    assert header["excluded_horizon"] > 0
    assert len(selected) > 0
