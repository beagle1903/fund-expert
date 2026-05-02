"""Join the three loaded frames per universe into one fund-per-row DataFrame."""

import pandas as pd


def merge_universe(frames: dict[str, pd.DataFrame], universe: str) -> pd.DataFrame:
    """Inner-join getiri + buyukluk + yonetim_ucreti on fon_kodu."""
    getiri = frames["getiri"]
    buyukluk = frames["buyukluk"]
    yonetim = frames["yonetim_ucreti"]

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


def merge_universes(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Concatenate already-merged universe frames (TEFAS + BEFAS codes are disjoint)."""
    return pd.concat(frames, ignore_index=True)
