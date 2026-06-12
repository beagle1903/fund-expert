"""Join the three loaded frames per universe into one fund-per-row DataFrame."""

import pandas as pd


from fundexpert.data.loader import UniverseData

def merge_universe(frames: UniverseData, universe: str) -> pd.DataFrame:
    """Inner-join getiri + buyukluk + yonetim_ucreti on fon_kodu."""
    getiri = frames.getiri
    buyukluk = frames.buyukluk
    yonetim = frames.yonetim_ucreti

    # Drop duplicated identity columns from buyukluk and yonetim before merge
    buyukluk_keep = buyukluk.drop(
        columns=[c for c in ("fon_adi", "umbrella_type") if c in buyukluk.columns]
    )
    yonetim_keep = yonetim.drop(
        columns=[c for c in ("fon_adi", "umbrella_type") if c in yonetim.columns]
    )

    df = getiri.merge(buyukluk_keep, on="fon_kodu", how="inner")
    df = df.merge(yonetim_keep, on="fon_kodu", how="inner")
    df["universe"] = universe
    return df

def clean_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """Drop funds with missing fee or short history."""
    df = df[df["applied_management_fee_pct"].notna()]
    df = df[df["ret_3m"].notna()]
    return df
