import pandas as pd
import pytest

from fundexpert.data.merge import merge_universe


@pytest.fixture
def small_frames():
    getiri = pd.DataFrame({
        "fon_kodu": ["AAA", "BBB", "CCC"],
        "fon_adi":  ["A FON", "B FON", "C FON"],
        "umbrella_type": ["Değişken", "Hisse", "Borç"],
        "risk":   [4, 6, 2],
        "ret_1m": [4.5, 7.1, 1.2],
        "ret_3m": [2.3, 5.4, 0.8],
        "ret_6m": [16.2, 22.8, 4.5],
        "ret_ytd":[14.1, 18.5, 3.9],
        "ret_1y": [40.2, 55.3, 12.4],
        "ret_3y": [255.6, 320.4, 60.1],
        "ret_5y": [692.75, float("nan"), 180.20],
    })
    buyukluk = pd.DataFrame({
        "fon_kodu": ["AAA", "BBB", "CCC"],
        "fon_adi":  ["A FON", "B FON", "C FON"],
        "umbrella_type": ["Değişken", "Hisse", "Borç"],
        "aum_first":  [36e6, 50e6, 15e6],
        "aum_last":   [34.8e6, 60e6, 15.5e6],
        "aum_change_pct":   [-3.45, 20.0, 3.33],
        "units_first":      [1057059, 2e6, 8e5],
        "units_last":       [989575, 2.2e6, 8.1e5],
        "units_change_pct": [-6.38, 10.0, 1.25],
    })
    yonetim = pd.DataFrame({
        "fon_kodu": ["AAA", "BBB", "CCC"],
        "fon_adi":  ["A FON", "B FON", "C FON"],
        "umbrella_type": ["Değişken", "Hisse", "Borç"],
        "applied_management_fee_pct": [1.5, 2.0, 0.8],
        "bylaw_management_fee_pct":   [1.5, 2.0, 0.8],
        "max_total_expense_pct":      [3.65, 4.50, 1.20],
    })
    return {"getiri": getiri, "buyukluk": buyukluk, "yonetim_ucreti": yonetim}


def test_merge_universe_inner_joins_on_fon_kodu(small_frames):
    df = merge_universe(small_frames, universe="tefas")
    assert len(df) == 3
    assert set(df["fon_kodu"]) == {"AAA", "BBB", "CCC"}


def test_merge_universe_adds_universe_column(small_frames):
    df = merge_universe(small_frames, universe="tefas")
    assert (df["universe"] == "tefas").all()


def test_merge_universe_includes_all_internal_columns(small_frames):
    df = merge_universe(small_frames, universe="tefas")
    expected = {"fon_kodu", "fon_adi", "umbrella_type", "risk",
                "ret_1m", "ret_3m", "ret_6m", "ret_ytd", "ret_1y", "ret_3y", "ret_5y",
                "aum_change_pct", "applied_management_fee_pct",
                "max_total_expense_pct", "universe"}
    assert expected.issubset(set(df.columns))


def test_merge_universe_drops_funds_missing_in_one_file(small_frames):
    small_frames["yonetim_ucreti"] = small_frames["yonetim_ucreti"][
        small_frames["yonetim_ucreti"]["fon_kodu"] != "BBB"
    ]
    df = merge_universe(small_frames, universe="tefas")
    assert set(df["fon_kodu"]) == {"AAA", "CCC"}


