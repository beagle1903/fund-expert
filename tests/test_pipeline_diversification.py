from datetime import datetime

import fundexpert.pipeline as pipeline
from fundexpert.data.loader import load_universe
from fundexpert.data.merge import merge_universe
from fundexpert.pipeline import PipelineConfig, run_pipeline


def _config(**overrides):
    values = {
        "universe": "tefas",
        "risk_level": "medium",
        "horizon": "medium",
        "volume_priority": "medium",
        "fee_priority": "medium",
        "momentum_priority": "medium",
        "n": 12,
        "now": datetime(2026, 7, 29),
    }
    values.update(overrides)
    return PipelineConfig(**values)


def _candidates(fixtures_dir):
    return merge_universe(
        load_universe(
            fixtures_dir / "getiri_small.csv",
            fixtures_dir / "buyukluk_small.csv",
            fixtures_dir / "yonetim_small.csv",
        ),
        universe="tefas",
    )


def test_pipeline_passes_balanced_caps_to_selection(fixtures_dir, monkeypatch):
    candidates = _candidates(fixtures_dir)
    calls = []
    real_pick_top = pipeline.pick_top

    def capture(scored, n, max_per_type, max_per_sector, **kwargs):
        calls.append((max_per_type, max_per_sector))
        return real_pick_top(
            scored,
            n=n,
            max_per_type=max_per_type,
            max_per_sector=max_per_sector,
            **kwargs,
        )

    monkeypatch.setattr(pipeline, "pick_top", capture)

    run_pipeline(candidates, _config())

    assert calls == [(3, 3)]


def test_pipeline_preserves_independent_explicit_override(fixtures_dir, monkeypatch):
    candidates = _candidates(fixtures_dir)
    calls = []
    real_pick_top = pipeline.pick_top

    def capture(scored, n, max_per_type, max_per_sector, **kwargs):
        calls.append((max_per_type, max_per_sector))
        return real_pick_top(
            scored,
            n=n,
            max_per_type=max_per_type,
            max_per_sector=max_per_sector,
            **kwargs,
        )

    monkeypatch.setattr(pipeline, "pick_top", capture)

    run_pipeline(
        candidates,
        _config(
            n=16,
            diversification_mode="relaxed",
            max_per_type=7,
        ),
    )

    assert calls == [(7, 5)]


def test_news_counterfactual_uses_resolved_relaxed_caps(fixtures_dir, monkeypatch):
    candidates = _candidates(fixtures_dir)
    captured = {}

    def fake_penalty(scored, **kwargs):
        hit = type("Hit", (), {"to_render_dict": lambda self: {}})()
        return scored, {str(scored.iloc[0]["fon_kodu"]): [hit]}

    def fake_displaced(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(pipeline, "apply_negative_news_penalty", fake_penalty)
    monkeypatch.setattr(pipeline, "compute_displaced_funds", fake_displaced)

    run_pipeline(
        candidates,
        _config(
            diversification_mode="relaxed",
            news_enabled=True,
            news_api_key="test-key",
        ),
    )

    assert captured["max_per_type"] == 4
    assert captured["max_per_sector"] == 4
