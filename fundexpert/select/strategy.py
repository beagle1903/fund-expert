"""Map a Turkish fund name to a coarse strategy bucket used for diversity caps.

The umbrella type (Şemsiye Fon Türü) is too coarse on its own — for example,
"Serbest Şemsiye Fonu" lumps money-market, equity, and fund-of-funds together,
and "PARA PİYASASI" funds appear under three different umbrellas. So we cap
diversity on the strategy implied by the fund's *name* instead.
"""

from __future__ import annotations

import json
from pathlib import Path

_RULES_PATH = Path(__file__).resolve().parent.parent / "rules.json"
_RULES = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
_BUCKET_RULES: tuple[tuple[str, str], ...] = tuple(tuple(r) for r in _RULES["bucket_rules"])


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
    for keyword, bucket in _BUCKET_RULES:
        if keyword in stripped:
            return bucket
    return "other"
