"""Join the three loaded frames per universe into one fund-per-row DataFrame."""

import pandas as pd


import pandera as pa

from fundexpert.data.loader import UniverseData


MergedUniverseSchema = pa.DataFrameSchema({
    "fon_kodu": pa.Column(str, coerce=True),
    "fon_adi": pa.Column(str, nullable=True, coerce=True),
    "umbrella_type": pa.Column(str, nullable=True, coerce=True),
    "risk": pa.Column(float, nullable=True, coerce=True),
    "ret_1m": pa.Column(float, nullable=True, coerce=True),
    "ret_3m": pa.Column(float, nullable=True, coerce=True),
    "ret_6m": pa.Column(float, nullable=True, coerce=True),
    "ret_ytd": pa.Column(float, nullable=True, coerce=True),
    "ret_1y": pa.Column(float, nullable=True, coerce=True),
    "ret_3y": pa.Column(float, nullable=True, coerce=True),
    "ret_5y": pa.Column(float, nullable=True, coerce=True),
    "aum_first": pa.Column(float, nullable=True, coerce=True),
    "aum_last": pa.Column(float, nullable=True, coerce=True),
    "aum_change_pct": pa.Column(float, nullable=True, coerce=True),
    "units_first": pa.Column(float, nullable=True, coerce=True),
    "units_last": pa.Column(float, nullable=True, coerce=True),
    "units_change_pct": pa.Column(float, nullable=True, coerce=True),
    "applied_management_fee_pct": pa.Column(float, nullable=True, coerce=True),
    "bylaw_management_fee_pct": pa.Column(float, nullable=True, coerce=True),
    "universe": pa.Column(str, coerce=True),
})


def merge_universe(frames: UniverseData, universe: str) -> pd.DataFrame:
    """Inner-join getiri + buyukluk + yonetim_ucreti on fon_kodu."""
    getiri = frames.getiri
    buyukluk = frames.buyukluk
    yonetim = frames.yonetim_ucreti

    # Drop duplicated identity columns from buyukluk and yonetim before merge by slicing
    b_cols = [c for c in buyukluk.columns if c not in ("fon_adi", "umbrella_type")]
    buyukluk_keep = buyukluk[b_cols]

    y_cols = [c for c in yonetim.columns if c not in ("fon_adi", "umbrella_type")]
    yonetim_keep = yonetim[y_cols]

    df = getiri.merge(buyukluk_keep, on="fon_kodu", how="inner")
    df = df.merge(yonetim_keep, on="fon_kodu", how="inner")
    df["universe"] = universe
    
    return MergedUniverseSchema.validate(df)

def clean_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """Drop funds with missing fee or short history."""
    df = df[df["applied_management_fee_pct"].notna()]
    df = df[df["ret_3m"].notna()]
    return df
