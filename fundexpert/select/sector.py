"""Map a Turkish fund name to a coarse sector bucket used as a second diversity cap.

Strategy alone (equity / debt / mixed / fund_of_funds…) doesn't catch sector
concentration: e.g. five tech-sector funds can satisfy a per-strategy cap if
one is HİSSE SENEDİ, one is FON SEPETİ, one is DEĞİŞKEN, etc. — and the
portfolio still ends up as a single-sector bet. This bucket caps that axis.

Funds without a sector keyword fall to "diversified" and are exempt from the
sector cap (most non-themed funds live there).
"""

from __future__ import annotations

# Order matters: first match wins. Place narrower keywords before broader ones.
_SECTOR_RULES: tuple[tuple[str, str], ...] = (
    ("TEKNOLOJİ", "tech"),
    ("DİJİTAL OYUN", "tech"),
    ("YAZILIM", "tech"),
    ("BİLİŞİM", "tech"),
    ("SAĞLIK", "health"),
    ("İLAÇ", "health"),
    ("PETROL", "energy"),
    ("ENERJİ", "energy"),
    ("BANKACILIK", "finance"),
    ("FİNANS", "finance"),
    ("GAYRİMENKUL", "real_estate"),
    ("İNŞAAT", "real_estate"),
    ("SANAYİ", "industrial"),
    ("METAL", "metals"),  # falls *after* precious metals are caught by strategy
    ("KİMYA", "chemicals"),
    ("GIDA", "consumer"),
    ("İÇECEK", "consumer"),
    ("PERAKENDE", "consumer"),
    ("TARIM", "agriculture"),
    ("TURİZM", "tourism"),
    ("TELEKOMÜNİKASYON", "telecom"),
    ("İLETİŞİM", "telecom"),
    ("ULAŞTIRMA", "transport"),
    ("HAVACILIK", "transport"),
    ("SAVUNMA", "defense"),
)


def sector_from_name(fon_adi: str | None) -> str:
    """Return a coarse sector bucket for a Turkish fund name.

    Falls back to "diversified" when no rule matches or the input is empty.
    """
    if not fon_adi:
        return "diversified"
    stripped = fon_adi.strip()
    if not stripped:
        return "diversified"
    # Same Turkish dotted-i workaround as strategy.py — str.upper() is locale-blind.
    upper = stripped.replace("i", "İ").replace("ı", "I").upper()
    for keyword, bucket in _SECTOR_RULES:
        if keyword in upper:
            return bucket
    return "diversified"
