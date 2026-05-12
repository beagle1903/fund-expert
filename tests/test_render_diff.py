"""Tests for fundexpert.render.diff."""

import io
from datetime import datetime

import pandas as pd
from rich.console import Console

from fundexpert.render.diff import render_diff


def _selected(codes=("AAK", "BBB"), weights=(60, 40), scores=(0.72, 0.55)) -> pd.DataFrame:
    return pd.DataFrame({
        "fon_kodu": list(codes),
        "fon_adi":  [f"{c} FON ADI" for c in codes],
        "display_weight_pct": list(weights),
        "score": list(scores),
    })


def _previous(codes=("AAK", "BBB"), weights=(60, 40), scores=(0.72, 0.55)) -> dict:
    return {
        "timestamp": datetime(2026, 5, 1, 9, 0).isoformat(),
        "universe": "tefas",
        "picks": [
            {"fon_kodu": c, "fon_adi": f"{c} FON ADI",
             "weight_pct": w, "score": s}
            for c, w, s in zip(codes, weights, scores)
        ],
    }


def _output(selected, previous) -> str:
    buf = io.StringIO()
    console = Console(file=buf, highlight=False)
    render_diff(selected, previous, console=console)
    return buf.getvalue()


def test_no_change_message_when_identical():
    out = _output(_selected(), _previous())
    assert "Değişiklik yok" in out


def test_entered_fund_appears():
    out = _output(
        _selected(codes=("AAK", "NEW")),
        _previous(codes=("AAK", "BBB")),
    )
    assert "Portföye girenler" in out
    assert "NEW" in out


def test_dropped_fund_appears():
    out = _output(
        _selected(codes=("AAK", "NEW")),
        _previous(codes=("AAK", "BBB")),
    )
    assert "Portföyden çıkanlar" in out
    assert "BBB" in out


def test_weight_change_shown():
    out = _output(
        _selected(codes=("AAK", "BBB"), weights=(70, 30)),
        _previous(codes=("AAK", "BBB"), weights=(60, 40)),
    )
    assert "Değişen ağırlık" in out
    assert "60→70" in out


def test_score_change_shown():
    out = _output(
        _selected(codes=("AAK",), weights=(100,), scores=(0.80,)),
        _previous(codes=("AAK",), weights=(100,), scores=(0.72,)),
    )
    assert "0.72→0.80" in out


def test_previous_timestamp_shown():
    out = _output(_selected(), _previous())
    assert "2026-05-01" in out


def test_no_change_section_when_no_drift():
    out = _output(_selected(), _previous())
    assert "Portföye girenler" not in out
    assert "Portföyden çıkanlar" not in out
