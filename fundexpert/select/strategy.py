"""Map a Turkish fund name to a coarse strategy bucket used for diversity caps.

The umbrella type (Şemsiye Fon Türü) is too coarse on its own — for example,
"Serbest Şemsiye Fonu" lumps money-market, equity, and fund-of-funds together,
and "PARA PİYASASI" funds appear under three different umbrellas. So we cap
diversity on the strategy implied by the fund's *name* instead.
"""

from __future__ import annotations

from fundexpert.utils.rules import get_bucket_rules


import re
import pandas as pd

import numpy as np
import pandas as pd

def bucket_from_names(fon_adi_series: pd.Series) -> pd.Series:
    """Vectorized strategy bucket assignment for a Pandas Series of names."""
    rules = get_bucket_rules()
    if not rules:
        return pd.Series("other", index=fon_adi_series.index)
    conditions = [fon_adi_series.str.contains(k, case=False, na=False) for k, _ in rules]
    choices = [v for _, v in rules]
    return pd.Series(np.select(conditions, choices, default="other"), index=fon_adi_series.index)

def bucket_from_name(fon_adi: str | None) -> str:
    """Return a coarse strategy bucket for a Turkish fund name.

    Falls back to "other" when no rule matches or the input is empty.
    """
    if not fon_adi:
        return "other"
    stripped = fon_adi.strip()
    if not stripped:
        return "other"
    # Assume input is already fully normalized and uppercased by pipeline.py
    for keyword, bucket in get_bucket_rules():
        if keyword in stripped:
            return bucket
    return "other"
