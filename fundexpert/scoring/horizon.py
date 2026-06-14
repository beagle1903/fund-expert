"""Map user-chosen horizon to a single mean-return signal column R."""

import pandas as pd

from fundexpert.config import ScoringConfig


def apply_horizon(df: pd.DataFrame, horizon: str, scoring_config: ScoringConfig) -> tuple[pd.DataFrame, int]:
    """Add column `R` = mean of horizon-bucket return columns; drop rows that are missing minimum track record."""
    cols = list(scoring_config.horizon_buckets[horizon])
    R = df[cols].mean(axis=1, skipna=True)
    # Require at least the shortest period (cols[0]) to exist to ensure a minimum track record
    keep_mask = df[cols[0]].notna()
    out = df.loc[keep_mask].assign(R=R[keep_mask])
    return out, int((~keep_mask).sum())
