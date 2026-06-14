"""Map a Turkish fund name to a coarse strategy bucket used for diversity caps.

The umbrella type (Şemsiye Fon Türü) is too coarse on its own — for example,
"Serbest Şemsiye Fonu" lumps money-market, equity, and fund-of-funds together,
and "PARA PİYASASI" funds appear under three different umbrellas. So we cap
diversity on the strategy implied by the fund's *name* instead.
"""

from __future__ import annotations

import json
import importlib.resources
from functools import lru_cache

@lru_cache(maxsize=1)
def _get_bucket_rules() -> tuple[tuple[str, str], ...]:
    text = importlib.resources.files("fundexpert").joinpath("rules.json").read_text(encoding="utf-8")
    _RULES = json.loads(text)
    return tuple(tuple(r) for r in _RULES["bucket_rules"])


import re
import pandas as pd

@lru_cache(maxsize=1)
def _get_bucket_regex_map() -> tuple[str, dict[str, str]]:
    rules = _get_bucket_rules()
    mapping = {k: v for k, v in rules}
    keys = sorted(mapping.keys(), key=len, reverse=True)
    pattern = f"({'|'.join(map(re.escape, keys))})"
    return pattern, mapping

def bucket_from_names(fon_adi_series: pd.Series) -> pd.Series:
    """Vectorized strategy bucket assignment for a Pandas Series of names."""
    pattern, mapping = _get_bucket_regex_map()
    extracted = fon_adi_series.str.extract(pattern, expand=False)
    return extracted.map(mapping).fillna("other")

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
    for keyword, bucket in _get_bucket_rules():
        if keyword in stripped:
            return bucket
    return "other"
