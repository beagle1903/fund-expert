"""Map a Turkish fund name to a coarse sector bucket used as a second diversity cap.

Strategy alone (equity / debt / mixed / fund_of_funds…) doesn't catch sector
concentration: e.g. five tech-sector funds can satisfy a per-strategy cap if
one is HİSSE SENEDİ, one is FON SEPETİ, one is DEĞİŞKEN, etc. — and the
portfolio still ends up as a single-sector bet. This bucket caps that axis.

Funds without a sector keyword fall to "diversified" and are exempt from the
sector cap (most non-themed funds live there).
"""

from __future__ import annotations

from fundexpert.utils.rules import get_sector_rules, get_cleanup_rules

import re
import pandas as pd

import numpy as np
import pandas as pd

def _clean_names(names: pd.Series) -> pd.Series:
    """Vectorized cleanup of false positive issuer substrings before sector matching."""
    cleanup_rules = get_cleanup_rules()
    if not cleanup_rules:
        return names
    return names.replace(cleanup_rules, regex=True)

def sector_from_names(fon_adi_series: pd.Series) -> pd.Series:
    """Vectorized sector bucket assignment for a Pandas Series of names."""
    cleaned = _clean_names(fon_adi_series)
    rules = get_sector_rules()
    if not rules:
        return pd.Series("diversified", index=fon_adi_series.index)
    conditions = [cleaned.str.contains(k, case=False, na=False) for k, _ in rules]
    choices = [v for _, v in rules]
    return pd.Series(np.select(conditions, choices, default="diversified"), index=fon_adi_series.index)

def _clean_name(name: str) -> str:
    """Cleanup false positive issuer substrings before sector matching."""
    cleanup_rules = get_cleanup_rules()
    for pattern, repl in cleanup_rules.items():
        name = re.sub(pattern, repl, name)
    return name

def sector_from_name(fon_adi: str | None) -> str:
    """Return a coarse sector bucket for a Turkish fund name.

    Falls back to "diversified" when no rule matches or the input is empty.
    """
    if not fon_adi:
        return "diversified"
    stripped = fon_adi.strip()
    if not stripped:
        return "diversified"
    # Assume input is already fully normalized and uppercased by pipeline.py
    cleaned = _clean_name(stripped)
    for keyword, bucket in get_sector_rules():
        if keyword in cleaned:
            return bucket
    return "diversified"
