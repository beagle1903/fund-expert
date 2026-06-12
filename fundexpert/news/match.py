"""Pure functions for mapping a Turkish fund name to a search-query prefix.

The portfolio-management company is the cleanest signal we can extract from
`fon_adi` for a search query: a name like
``ATA PORTFÖY ÇOKLU VARLIK DEĞİŞKEN FON`` belongs to ATA PORTFÖY, and any
negative news about that company is a reasonable proxy for fund-level risk.
"""

from __future__ import annotations

from fundexpert.utils.text import turkish_upper

_PORTFOY_VARIANTS = ("PORTFÖY", "PORTFOY")  # second guards against missing diacritics


def extract_company_prefix(fon_adi: str | None) -> str:
    """Return the portfolio-management company prefix from a fund name.

    Examples
    --------
    >>> extract_company_prefix("ATA PORTFÖY ÇOKLU VARLIK DEĞİŞKEN FON")
    'ATA PORTFÖY'
    >>> extract_company_prefix("ak portföy eurobond fonu")
    'AK PORTFÖY'
    >>> extract_company_prefix("OPAQUE FUND NAME WITHOUT COMPANY")
    'OPAQUE FUND NAME'

    Strategy: take everything up to and including the first ``PORTFÖY`` token.
    If no ``PORTFÖY`` token is present, fall back to the first three
    whitespace-separated words. Empty / None / whitespace-only → ``''``.
    """
    if not fon_adi:
        return ""
    stripped = fon_adi.strip()
    if not stripped:
        return ""

    # Turkish-i fix: str.upper() is locale-blind, 'i' → 'I' not 'İ'.
    upper = turkish_upper(stripped)
    tokens = upper.split()

    for i, token in enumerate(tokens):
        # Strip trailing punctuation so e.g. "PORTFÖY," still matches.
        bare = token.rstrip(".,;:")
        if bare in _PORTFOY_VARIANTS:
            return " ".join(tokens[: i + 1]).rstrip(".,;:")

    # Fallback: first 3 words.
    return " ".join(tokens[:3])
