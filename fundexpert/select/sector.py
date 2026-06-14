"""Map a Turkish fund name to a coarse sector bucket used as a second diversity cap.

Strategy alone (equity / debt / mixed / fund_of_funds…) doesn't catch sector
concentration: e.g. five tech-sector funds can satisfy a per-strategy cap if
one is HİSSE SENEDİ, one is FON SEPETİ, one is DEĞİŞKEN, etc. — and the
portfolio still ends up as a single-sector bet. This bucket caps that axis.

Funds without a sector keyword fall to "diversified" and are exempt from the
sector cap (most non-themed funds live there).
"""

from __future__ import annotations

import json
import importlib.resources
from functools import lru_cache

@lru_cache(maxsize=1)
def _get_sector_rules() -> tuple[tuple[str, str], ...]:
    text = importlib.resources.files("fundexpert").joinpath("rules.json").read_text(encoding="utf-8")
    _RULES = json.loads(text)
    return tuple(tuple(r) for r in _RULES["sector_rules"])


import re
import pandas as pd

@lru_cache(maxsize=1)
def _get_sector_regex_map() -> tuple[str, dict[str, str]]:
    rules = _get_sector_rules()
    mapping = {k: v for k, v in rules}
    keys = sorted(mapping.keys(), key=len, reverse=True)
    pattern = f"({'|'.join(map(re.escape, keys))})"
    return pattern, mapping

def _clean_names(names: pd.Series) -> pd.Series:
    """Vectorized cleanup of false positive issuer substrings before sector matching."""
    res = names.str.replace(r"QNB SAĞLIK HAYAT(?: SİGORTA VE\s+EMEKLİLİK A\.Ş\.?)?", "QNB", regex=True)
    res = res.str.replace(r"QNB FİNANS PORTFÖY", "QNB PORTFÖY", regex=True)
    res = res.str.replace(r"TARIM KREDİ PORTFÖY", "TK PORTFÖY", regex=True)
    return res

def sector_from_names(fon_adi_series: pd.Series) -> pd.Series:
    """Vectorized sector bucket assignment for a Pandas Series of names."""
    pattern, mapping = _get_sector_regex_map()
    cleaned = _clean_names(fon_adi_series)
    extracted = cleaned.str.extract(pattern, expand=False)
    return extracted.map(mapping).fillna("diversified")

def _clean_name(name: str) -> str:
    """Cleanup false positive issuer substrings before sector matching."""
    name = re.sub(r"QNB SAĞLIK HAYAT(?: SİGORTA VE\s+EMEKLİLİK A\.Ş\.?)?", "QNB", name)
    name = re.sub(r"QNB FİNANS PORTFÖY", "QNB PORTFÖY", name)
    name = re.sub(r"TARIM KREDİ PORTFÖY", "TK PORTFÖY", name)
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
    for keyword, bucket in _get_sector_rules():
        if keyword in cleaned:
            return bucket
    return "diversified"
