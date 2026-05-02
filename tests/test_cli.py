from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

from fundexpert.cli import run_pipeline


@pytest.fixture
def fake_universe_loader():
    """Patch loaders so cli.run_pipeline doesn't read the filesystem."""
    getiri = pd.DataFrame({
        "fon_kodu": ["A", "B", "C"],
        "fon_adi":  ["A FON", "B FON", "C FON"],
        "umbrella_type": ["Değişken", "Hisse", "Borçlanma"],
        "risk": [3, 6, 2],
        "ret_1m": [4.0, 7.0, 1.0],
        "ret_3m": [2.0, 5.0, 0.5],
        "ret_6m": [10.0, 20.0, 4.0],
        "ret_ytd":[14.0, 18.0, 3.0],
        "ret_1y": [40.0, 55.0, 12.0],
        "ret_3y": [200.0, 300.0, 60.0],
        "ret_5y": [600.0, 700.0, 180.0],
    })
    buyukluk = pd.DataFrame({
        "fon_kodu": ["A", "B", "C"],
        "fon_adi": ["A FON", "B FON", "C FON"],
        "umbrella_type": ["Değişken", "Hisse", "Borçlanma"],
        "aum_first": [1, 1, 1], "aum_last": [1, 1, 1],
        "aum_change_pct": [5.0, -2.0, 8.0],
        "units_first": [1, 1, 1], "units_last": [1, 1, 1],
        "units_change_pct": [0, 0, 0],
    })
    yonetim = pd.DataFrame({
        "fon_kodu": ["A", "B", "C"],
        "fon_adi": ["A FON", "B FON", "C FON"],
        "umbrella_type": ["Değişken", "Hisse", "Borçlanma"],
        "applied_management_fee_pct": [1.0, 2.0, 0.5],
        "bylaw_management_fee_pct": [1.0, 2.0, 0.5],
        "max_total_expense_pct": [3.0, 4.0, 1.5],
    })
    frames = {"getiri": getiri, "buyukluk": buyukluk, "yonetim_ucreti": yonetim}
    with patch("fundexpert.cli.load_universe", return_value=frames):
        yield


def test_run_pipeline_returns_selected_with_weights(fake_universe_loader):
    selected, header = run_pipeline(
        universe="tefas",
        risk_priority="medium",
        horizon="medium",
        volume_priority="medium",
        fee_priority="medium",
        n=2,
        max_per_type=2,
        now=datetime(2026, 5, 2, 11, 42),
    )
    assert len(selected) == 2
    assert "display_weight_pct" in selected.columns
    assert sum(selected["display_weight_pct"]) == pytest.approx(100.0)
    assert header["candidate_total"] == 3
