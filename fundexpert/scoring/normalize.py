"""Per-column min-max scaling with constant-range and NaN guards."""

import pandas as pd


def minmax_normalize(series: pd.Series) -> pd.Series:
    """Scale a numeric series to [0, 1].

    - Constant columns (max == min) return 0.5 everywhere (neutral).
    - NaN values become 0.5 (neutral contribution).
    """
    s = series.astype(float)
    finite = s.dropna()
    if len(finite) == 0:
        return pd.Series([0.5] * len(s), index=s.index)

    lo, hi = finite.quantile(0.01), finite.quantile(0.99)
    if hi == lo:
        return pd.Series([0.5] * len(s), index=s.index)

    out = (s - lo) / (hi - lo)
    return out.clip(0, 1).fillna(0.5)
