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
from pathlib import Path

_RULES_PATH = Path(__file__).resolve().parent.parent / "rules.json"
_RULES = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
_SECTOR_RULES: tuple[tuple[str, str], ...] = tuple(tuple(r) for r in _RULES["sector_rules"])


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
    for keyword, bucket in _SECTOR_RULES:
        if keyword in stripped:
            return bucket
    return "diversified"
