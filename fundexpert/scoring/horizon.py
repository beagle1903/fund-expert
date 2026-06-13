"""Map user-chosen horizon to a single mean-return signal column R."""

import pandas as pd

from fundexpert.config import ScoringConfig


def apply_horizon(df: pd.DataFrame, horizon: str, scoring_config: ScoringConfig) -> pd.DataFrame:
    """Add column `R` = mean of horizon-bucket return columns; drop all-NaN rows.

    `df.attrs["excluded_count"]` is set to the number of rows dropped.
    """
    cols = list(scoring_config.horizon_buckets[horizon])
    R = df[cols].mean(axis=1, skipna=False)
    keep_mask = R.notna()
    out = df.loc[keep_mask].copy()
    out["R"] = R[keep_mask]
    out.attrs["excluded_count"] = int((~keep_mask).sum())
    return out
