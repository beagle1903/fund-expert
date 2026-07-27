"""Canonical TEFAS/BEFAS founder attribution for locally exported fund rows."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from functools import lru_cache

import pandas as pd


FOUNDER_NAMES: dict[str, tuple[str, ...]] = {
    "tefas": (
        "AHLATCI PORTFÖY YÖNETİMİ ANONİM ŞİRKETİ",
        "AK PORTFÖY YÖNETİMİ A.Ş.",
        "AKTİF PORTFÖY YÖNETİMİ A.Ş.",
        "ALBARAKA PORTFÖY YÖNETİMİ A.Ş.",
        "ALLBATROSS PORTFÖY YÖNETİMİ ANONİM ŞİRKETİ",
        "ASTRA PORTFÖY YÖNETİMİ A.Ş.",
        "ATA PORTFÖY YÖNETİMİ A.Ş.",
        "ATLAS PORTFÖY YÖNETİMİ A.Ş.",
        "AURA PORTFÖY YÖNETİMİ A.Ş.",
        "AZİMUT PORTFÖY YÖNETİMİ A.Ş.",
        "A1 CAPİTAL PORTFÖY YÖNETİMİ A.Ş.",
        "BULLS PORTFÖY YÖNETİMİ ANONİM ŞİRKETİ",
        "BV PORTFÖY YÖNETİMİ A.Ş.",
        "DENİZ PORTFÖY YÖNETİMİ A.Ş",
        "EMAA BLUE PORTFÖY YÖNETİMİ ANONİM ŞİRKETİ",
        "EMLAK KATILIM PORTFÖY YÖNETİMİ A.Ş.",
        "FİBA PORTFÖY YÖNETİMİ A.Ş.",
        "FONMAP PORTFÖY YÖNETİMİ ANONİM ŞİRKETİ",
        "GARANTİ PORTFÖY YÖNETİMİ A.Ş.",
        "GLOBAL MD PORTFÖY YÖNETİMİ A.Ş.",
        "GOLDEN GLOBAL PORTFÖY YÖNETİMİ A.Ş.",
        "HAS PORTFÖY YÖNETİMİ A.Ş.",
        "HEDEF PORTFÖY YÖNETİMİ A.Ş",
        "HSBC PORTFÖY YÖNETİMİ A.Ş.",
        "ICBC TURKEY PORTFÖY YÖNETİMİ A.Ş.",
        "INVEO PORTFÖY YÖNETİMİ A.Ş.",
        "İNCİR PORTFÖY YÖNETİMİ ANONİM ŞİRKETİ",
        "İSTANBUL PORTFÖY YÖNETİMİ A.Ş.",
        "İŞ PORTFÖY YÖNETİMİ A.Ş.",
        "KARE PORTFÖY YÖNETİMİ A.Ş.",
        "KUVEYT TÜRK PORTFÖY YÖNETİMİ A.Ş.",
        "LOGOS PORTFÖY YÖNETİMİ A.Ş.",
        "MARMARA CAPİTAL PORTFÖY YÖNETİMİ A.Ş.",
        "MEKSA PORTFÖY YÖNETİMİ A.Ş.",
        "MT PORTFÖY YÖNETİMİ ANONİM ŞİRKETİ",
        "NEO PORTFÖY YÖNETİMİ A.Ş.",
        "NUROL PORTFÖY YÖNETİMİ A.Ş.",
        "ONE PORTFÖY YÖNETİMİ A.Ş.",
        "OSMANLI PORTFÖY YÖNETİMİ A.Ş.",
        "OYAK PORTFÖY YÖNETİMİ A.Ş.",
        "PARDUS PORTFÖY YÖNETİMİ A.Ş.",
        "PERFORM PORTFÖY YÖNETİMİ A.Ş.",
        "PHİLLİP PORTFÖY YÖNETİMİ A.Ş.",
        "PİRAMİT PORTFÖY YÖNETİMİ ANONİM ŞİRKETİ",
        "PUSULA PORTFÖY YÖNETİMİ A.Ş.",
        "QNB PORTFÖY YÖNETİMİ A.Ş.",
        "RE-PIE PORTFÖY YÖNETİMİ A.Ş.",
        "ROTA PORTFÖY YÖNETİMİ A.Ş.",
        "SPARTA PORTFÖY YÖNETİMİ A.Ş.",
        "STATECH PORTFÖY YÖNETİMİ A.Ş.",
        "STRATEJİ PORTFÖY YÖNETİMİ A.Ş.",
        "TACİRLER PORTFÖY YÖNETİMİ A.Ş.",
        "TEB PORTFÖY YÖNETİMİ A.Ş.",
        "TERA PORTFÖY YÖNETİMİ A.Ş.",
        "TRIVE PORTFÖY YÖNETİMİ A.Ş.",
        "ÜNLÜ PORTFÖY YÖNETİMİ A.Ş.",
        "V PORTFÖY YÖNETİMİ ANONİM ŞİRKETİ",
        "VAKIF KATILIM PORTFÖY YÖNETİMİ ANONİM ŞİRKETİ",
        "VEGA PORTFÖY YÖNETİMİ ANONİM ŞİRKETİ",
        "YAPI KREDİ PORTFÖY YÖNETİMİ A.Ş.",
        "ZİRAAT PORTFÖY YÖNETİMİ A.Ş.",
    ),
    "befas": (
        "AGESA HAYAT VE EMEKLİLİK A.Ş.",
        "ALLIANZ YAŞAM VE EMEKLİLİK A.Ş.",
        "ALLİANZ HAYAT VE EMEKLİLİK A.Ş.",
        "ANADOLU HAYAT EMEKLİLİK A.Ş.",
        "AXA HAYAT VE EMEKLİLİK A.Ş.",
        "BEREKET EMEKLİLİK VE HAYAT A.Ş.",
        "BNP PARİBAS CARDİF EMEKLİLİK A.Ş.",
        "GARANTİ EMEKLİLİK VE HAYAT A.Ş.",
        "HDI FİBA EMEKLİLİK VE HAYAT A.Ş.",
        "KATILIM EMEKLİLİK VE HAYAT A.Ş.",
        "METLİFE EMEKLİLİK VE HAYAT A.Ş.",
        "QNB SAĞLIK HAYAT SİGORTA VE EMEKLİLİK A.Ş.",
        "TÜRKİYE HAYAT VE EMEKLİLİK A.Ş.",
        "VİENNALİFE EMEKLİLİK VE HAYAT A.Ş.",
        "ZURICH YAŞAM VE EMEKLİLİK A.Ş.",
    ),
}

_TURKISH_ASCII = str.maketrans(
    {
        "Ç": "C",
        "Ğ": "G",
        "İ": "I",
        "Ö": "O",
        "Ş": "S",
        "Ü": "U",
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
    }
)


def _match_key(value: str) -> str:
    translated = value.translate(_TURKISH_ASCII)
    decomposed = unicodedata.normalize("NFKD", translated)
    ascii_value = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^A-Z0-9]+", " ", ascii_value.upper()).strip()


def _tefas_prefix(founder: str) -> str:
    return _match_key(founder).split(" YONETIMI", maxsplit=1)[0]


@lru_cache(maxsize=2)
def _prefix_map(universe: str) -> tuple[tuple[str, str], ...]:
    if universe not in FOUNDER_NAMES:
        raise ValueError(f"Unsupported universe: {universe!r}.")

    if universe == "tefas":
        entries = [(_tefas_prefix(founder), founder) for founder in FOUNDER_NAMES[universe]]
        entries.extend(
            [
                ("AZIMUT PYS", "AZİMUT PORTFÖY YÖNETİMİ A.Ş."),
                ("HSBC PYS", "HSBC PORTFÖY YÖNETİMİ A.Ş."),
            ]
        )
    else:
        entries = [(_match_key(founder), founder) for founder in FOUNDER_NAMES[universe]]
    return tuple(sorted(entries, key=lambda item: len(item[0]), reverse=True))


def founder_from_name(fund_name: object, universe: str) -> str | None:
    """Return the canonical founder whose official prefix matches a fund title."""
    if not isinstance(fund_name, str) or not fund_name.strip():
        return None
    name_key = _match_key(fund_name)
    for prefix, founder in _prefix_map(universe):
        if name_key == prefix or name_key.startswith(f"{prefix} "):
            return founder
    return None


def attribute_founders(fund_names: pd.Series, universe: str) -> pd.Series:
    """Map a series of official fund titles to canonical founder names."""
    return fund_names.map(lambda value: founder_from_name(value, universe)).astype("string")


def available_founders(
    candidates: pd.DataFrame,
) -> list[dict[str, int | str]]:
    """Return founder names and row counts in canonical platform order."""
    if "kurucu" not in candidates.columns:
        return []
    universe_values = candidates["universe"].dropna().astype(str).unique()
    if len(universe_values) != 1 or universe_values[0] not in FOUNDER_NAMES:
        return []

    counts = candidates["kurucu"].value_counts()
    return [
        {"name": founder, "fund_count": int(counts[founder])}
        for founder in FOUNDER_NAMES[universe_values[0]]
        if founder in counts
    ]


def validate_founder(founder: str, universe: str) -> None:
    """Reject a founder that does not belong to the requested platform."""
    if founder not in FOUNDER_NAMES.get(universe, ()):
        raise ValueError(f"Founder {founder!r} is not valid for {universe}.")


def filter_by_founder(candidates: pd.DataFrame, founder: str | None) -> pd.DataFrame:
    """Apply an exact canonical founder filter without mutating the input."""
    if founder is None:
        return candidates
    if "kurucu" not in candidates.columns:
        raise ValueError("Candidates do not include founder attribution.")
    return candidates[candidates["kurucu"] == founder]


def founder_choices(universe: str) -> Iterable[str]:
    """Expose the canonical founder list for interactive clients."""
    return FOUNDER_NAMES.get(universe, ())
