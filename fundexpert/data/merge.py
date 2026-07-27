"""Join the three loaded frames per universe into one fund-per-row DataFrame."""

import re

import pandas as pd

from fundexpert.schemas import MergedUniverseSchema
from fundexpert.data.loader import UniverseData
from fundexpert.founders import attribute_founders
from fundexpert.utils.rules import get_exclusion_rules


def merge_universe(frames: UniverseData, universe: str, validate_schemas: bool = False) -> pd.DataFrame:
    """Inner-join getiri + buyukluk + yonetim_ucreti on fon_kodu."""
    getiri = frames.getiri.drop_duplicates(subset=["fon_kodu"])
    buyukluk = frames.buyukluk.drop_duplicates(subset=["fon_kodu"])
    yonetim = frames.yonetim_ucreti.drop_duplicates(subset=["fon_kodu"])

    # Drop duplicated identity columns from buyukluk and yonetim before merge by slicing
    b_cols = [c for c in buyukluk.columns if c not in ("fon_adi", "umbrella_type")]
    buyukluk_keep = buyukluk[b_cols]

    y_cols = [c for c in yonetim.columns if c not in ("fon_adi", "umbrella_type")]
    yonetim_keep = yonetim[y_cols]

    df = getiri.merge(buyukluk_keep, on="fon_kodu", how="inner")
    df = df.merge(yonetim_keep, on="fon_kodu", how="inner")
    df["universe"] = universe
    df["kurucu"] = attribute_founders(df["fon_adi"], universe)

    if validate_schemas:
        return MergedUniverseSchema.validate(df)
    return df


def clean_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """Drop funds with missing fee or explicit exclusions (e.g., OKS)."""
    mask = df["applied_management_fee_pct"].notna()

    exclusions = get_exclusion_rules()
    if exclusions:
        pattern = re.compile(
            r"\b(?:" + "|".join(re.escape(rule) for rule in exclusions) + r")\b",
            flags=re.IGNORECASE,
        )
        bad_name = df["fon_adi"].str.contains(pattern, na=False)
        bad_umbrella = df["umbrella_type"].str.contains(pattern, na=False)
        mask = mask & ~bad_name & ~bad_umbrella

    return df[mask]
