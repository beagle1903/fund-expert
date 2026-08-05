import pandas as pd
import pytest

from fundexpert.data.loader import load_universe


def test_load_universe_returns_three_frames(fixtures_dir):
    frames = load_universe(
        getiri_path=fixtures_dir / "getiri_small.csv",
        buyukluk_path=fixtures_dir / "buyukluk_small.csv",
        yonetim_path=fixtures_dir / "yonetim_small.csv",
    )
    assert hasattr(frames, "getiri")
    assert hasattr(frames, "buyukluk")
    assert hasattr(frames, "yonetim_ucreti")


def test_loader_skips_metadata_rows(fixtures_dir):
    frames = load_universe(
        getiri_path=fixtures_dir / "getiri_small.csv",
        buyukluk_path=fixtures_dir / "buyukluk_small.csv",
        yonetim_path=fixtures_dir / "yonetim_small.csv",
    )
    assert len(frames.getiri) == 3
    assert "fon_kodu" in frames.getiri.columns


def test_loader_parses_turkish_decimals(fixtures_dir):
    frames = load_universe(
        getiri_path=fixtures_dir / "getiri_small.csv",
        buyukluk_path=fixtures_dir / "buyukluk_small.csv",
        yonetim_path=fixtures_dir / "yonetim_small.csv",
    )
    aaa = frames.getiri[frames.getiri["fon_kodu"] == "AAA"].iloc[0]
    assert pytest.approx(aaa["ret_3y"]) == 255.60
    assert aaa["risk"] == 4
    fee = frames.yonetim_ucreti[frames.yonetim_ucreti["fon_kodu"] == "AAA"].iloc[0]
    assert fee["applied_management_fee_pct"] == 1.5


def test_loader_preserves_nan_in_long_returns(fixtures_dir):
    frames = load_universe(
        getiri_path=fixtures_dir / "getiri_small.csv",
        buyukluk_path=fixtures_dir / "buyukluk_small.csv",
        yonetim_path=fixtures_dir / "yonetim_small.csv",
    )
    bbb = frames.getiri[frames.getiri["fon_kodu"] == "BBB"].iloc[0]
    import numpy as np
    assert np.isnan(bbb["ret_5y"])
    assert bbb["ret_3y"] == 320.40


def test_loader_renames_columns_to_internal_names(fixtures_dir):
    frames = load_universe(
        getiri_path=fixtures_dir / "getiri_small.csv",
        buyukluk_path=fixtures_dir / "buyukluk_small.csv",
        yonetim_path=fixtures_dir / "yonetim_small.csv",
    )
    expected_getiri = {"fon_kodu", "fon_adi", "umbrella_type", "risk",
                       "ret_1m", "ret_3m", "ret_6m", "ret_ytd",
                       "ret_1y", "ret_3y", "ret_5y"}
    assert expected_getiri.issubset(set(frames.getiri.columns))

    expected_buyukluk = {"fon_kodu", "aum_first", "aum_last", "aum_change_pct",
                         "units_first", "units_last", "units_change_pct"}
    assert expected_buyukluk.issubset(set(frames.buyukluk.columns))

    expected_yonetim = {"fon_kodu", "applied_management_fee_pct",
                        "bylaw_management_fee_pct"}
    assert expected_yonetim.issubset(set(frames.yonetim_ucreti.columns))


def test_loader_uses_compact_string_and_category_dtypes(fixtures_dir):
    frames = load_universe(
        getiri_path=fixtures_dir / "getiri_small.csv",
        buyukluk_path=fixtures_dir / "buyukluk_small.csv",
        yonetim_path=fixtures_dir / "yonetim_small.csv",
    )

    assert frames.getiri["fon_kodu"].dtype.storage == "pyarrow"
    assert frames.getiri["fon_adi"].dtype.storage == "pyarrow"
    assert isinstance(frames.getiri["umbrella_type"].dtype, pd.CategoricalDtype)


def test_loader_rejects_large_csv(fixtures_dir, monkeypatch):
    import fundexpert.data.loader
    monkeypatch.setattr(fundexpert.data.loader, "MAX_CSV_SIZE_BYTES", 0)
    with pytest.raises(ValueError, match="exceeds size limit"):
        load_universe(
            getiri_path=fixtures_dir / "getiri_small.csv",
            buyukluk_path=fixtures_dir / "buyukluk_small.csv",
            yonetim_path=fixtures_dir / "yonetim_small.csv",
        )
