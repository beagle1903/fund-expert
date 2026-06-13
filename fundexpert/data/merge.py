"""Join the three loaded frames per universe into one fund-per-row DataFrame."""

import pandas as pd
import os


from fundexpert.schemas import MergedUniverseSchema

from fundexpert.data.loader import UniverseData


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
    
    if os.environ.get("DEBUG") == "1" or "PYTEST_CURRENT_TEST" in os.environ:
        return MergedUniverseSchema.validate(df)
    return df

def clean_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """Drop funds with missing fee, short history, or OKS restriction."""
    mask = df["applied_management_fee_pct"].notna() & df["ret_3m"].notna()
    
    # Exclude OKS (Otomatik Katılım Sistemi) funds as they are not available to the public
    oks_in_name = df["fon_adi"].str.contains(r"\bOKS\b", case=False, na=False, regex=True)
    oks_in_umbrella = df["umbrella_type"].str.contains(r"\bOKS\b", case=False, na=False, regex=True)
    mask = mask & ~oks_in_name & ~oks_in_umbrella
    
    return df[mask]
