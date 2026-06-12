"""Map a Turkish fund name to a coarse strategy bucket used for diversity caps.

The umbrella type (Şemsiye Fon Türü) is too coarse on its own — for example,
"Serbest Şemsiye Fonu" lumps money-market, equity, and fund-of-funds together,
and "PARA PİYASASI" funds appear under three different umbrellas. So we cap
diversity on the strategy implied by the fund's *name* instead.
"""

from __future__ import annotations

# Order matters: the first keyword that matches wins. Place the most specific
# strategy keywords before broader organisational labels (KATILIM, SERBEST).
_BUCKET_RULES: tuple[tuple[str, str], ...] = (
    ("HİSSE SENEDİ", "equity"),
    ("PARA PİYASASI", "money_market"),
    ("ALTIN", "precious_metals"),
    ("KIYMETLİ MADEN", "precious_metals"),
    ("BORÇLANMA ARAÇLARI", "debt"),
    ("EUROBOND", "debt"),
    ("KİRA SERTİFİKALARI", "debt"),
    ("FON SEPETİ", "fund_of_funds"),
    ("ENDEKS", "index"),
    ("DEĞİŞKEN", "mixed"),
    ("KARMA", "mixed"),
    ("ÇOKLU VARLIK", "mixed"),
)


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
