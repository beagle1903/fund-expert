"""Tests for fundexpert.history.store."""

import json
from datetime import datetime

import pandas as pd

from fundexpert.history.store import load_last_run, save_run


def _make_selected() -> pd.DataFrame:
    return pd.DataFrame({
        "fon_kodu": ["AAK", "BBB"],
        "fon_adi":  ["AK PORTFÖY PARA PİYASASI", "BETA PORTFÖY HİSSE FON"],
        "umbrella_type": ["Para Piyasası", "Hisse Senedi"],
        "risk":          [2, 6],
        "display_weight_pct": [60.0, 40.0],
        "score":         [0.72, 0.55],
        "strategy":      ["para_piyasasi", "hisse"],
        "sector":        ["diversified", "diversified"],
    })


def _make_header(universe: str = "tefas") -> dict:
    return {
        "timestamp": datetime(2026, 5, 12, 10, 30),
        "universe": universe,
        "risk_level": "medium",
        "horizon": "medium",
        "volume_priority": "medium",
        "fee_priority": "medium",
        "n": 8,
        "candidate_total": 1000,
        "candidate_kept": 950,
        "warning": None,
        "excluded_horizon": 0,
    }


def test_save_run_creates_file(tmp_path):
    path = save_run(_make_selected(), _make_header(), history_dir=tmp_path)
    assert path.exists()
    assert path.suffix == ".json"


def test_save_run_filename_contains_universe_and_timestamp(tmp_path):
    path = save_run(_make_selected(), _make_header("befas"), history_dir=tmp_path)
    assert "befas" in path.name
    assert "2026-05-12" in path.name


def test_save_run_record_structure(tmp_path):
    path = save_run(_make_selected(), _make_header(), history_dir=tmp_path)
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["universe"] == "tefas"
    assert record["horizon"] == "medium"
    assert len(record["picks"]) == 2
    pick = record["picks"][0]
    assert pick["fon_kodu"] == "AAK"
    assert pick["weight_pct"] == 60
    assert isinstance(pick["score"], float)


def test_save_run_creates_history_dir_if_missing(tmp_path):
    nested = tmp_path / "does" / "not" / "exist"
    save_run(_make_selected(), _make_header(), history_dir=nested)
    assert nested.exists()


def test_load_last_run_returns_none_when_dir_missing(tmp_path):
    result = load_last_run("tefas", history_dir=tmp_path / "empty")
    assert result is None


def test_load_last_run_returns_none_when_no_matching_universe(tmp_path):
    save_run(_make_selected(), _make_header("tefas"), history_dir=tmp_path)
    result = load_last_run("befas", history_dir=tmp_path)
    assert result is None


def test_load_last_run_returns_most_recent(tmp_path):
    h1 = {**_make_header(), "timestamp": datetime(2026, 5, 1, 9, 0)}
    h2 = {**_make_header(), "timestamp": datetime(2026, 5, 12, 10, 30)}
    save_run(_make_selected(), h1, history_dir=tmp_path)
    save_run(_make_selected(), h2, history_dir=tmp_path)
    result = load_last_run("tefas", history_dir=tmp_path)
    assert "2026-05-12" in result["timestamp"]


def test_load_last_run_filters_by_universe(tmp_path):
    save_run(_make_selected(), _make_header("tefas"), history_dir=tmp_path)
    save_run(_make_selected(), _make_header("befas"), history_dir=tmp_path)
    result = load_last_run("befas", history_dir=tmp_path)
    assert result["universe"] == "befas"


def test_load_last_run_returns_none_on_corrupt_json(tmp_path):
    corrupt = tmp_path / "2026-05-12_10-30-00_tefas.json"
    corrupt.write_text("not valid json", encoding="utf-8")
    result = load_last_run("tefas", history_dir=tmp_path)
    assert result is None

def test_save_run_ignores_oserror_on_replace_latest(tmp_path):
    from unittest.mock import patch
    import os
    original_replace = os.replace
    def mock_replace(src, dst):
        if "latest" in str(dst):
            raise OSError("Disk full")
        original_replace(src, dst)
        
    with patch("os.replace", side_effect=mock_replace):
        path = save_run(_make_selected(), _make_header(), history_dir=tmp_path)
    # the function should complete and return the path, catching the OSError
    assert path.exists()
