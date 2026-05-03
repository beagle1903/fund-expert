"""Behavior tests for fund-name → strategy bucket classifier."""

import pytest

from fundexpert.select.strategy import bucket_from_name


@pytest.mark.parametrize(
    "name,expected",
    [
        # equity (HİSSE SENEDİ) — wins even when SERBEST/KATILIM/ENDEKS also appear
        ("ATA PORTFÖY İKİNCİ HİSSE SENEDİ (TL) FONU (HİSSE SENEDİ YOĞUN FON)", "equity"),
        ("AK PORTFÖY BIST BANKA ENDEKSİ HİSSE SENEDİ (TL) FONU (HİSSE SENEDİ YOĞUN FON)", "equity"),
        ("PARDUS PORTFÖY İSTATİSTİKSEL ARBİTRAJ HİSSE SENEDİ SERBEST (TL) FON (HİSSE SENEDİ YOĞUN FON)", "equity"),

        # money_market — wins over KATILIM/SERBEST organisational labels
        ("ATA PORTFÖY PARA PİYASASI (TL) FONU", "money_market"),
        ("AK PORTFÖY PARA PİYASASI KATILIM FONU", "money_market"),
        ("GARANTİ PORTFÖY İKİNCİ PARA PİYASASI SERBEST (TL) FON", "money_market"),

        # precious metals
        ("AK PORTFÖY ALTIN FONU", "precious_metals"),
        ("İŞ PORTFÖY KIYMETLİ MADENLER FONU", "precious_metals"),

        # debt / fixed income
        ("ATLAS PORTFÖY BİRİNCİ ÖZEL SEKTÖR BORÇLANMA ARAÇLARI FONU", "debt"),
        ("AK PORTFÖY EUROBOND (AMERİKAN DOLARI) BORÇLANMA ARAÇLARI FONU", "debt"),
        ("ZİRAAT PORTFÖY KİRA SERTİFİKALARI KATILIM FONU", "debt"),

        # fund of funds
        ("AZİMUT PORTFÖY DENGELİ FON SEPETİ FONU", "fund_of_funds"),
        ("OSMANLI PORTFÖY BİRİNCİ FON SEPETİ FONU", "fund_of_funds"),

        # mixed / multi-asset
        ("ATA PORTFÖY ÇOKLU VARLIK DEĞİŞKEN FON", "mixed"),
        ("İŞ PORTFÖY DİJİTAL OYUN SEKTÖRÜ KARMA FON", "mixed"),
        ("AK PORTFÖY MUTLAK GETİRİ HEDEFLİ DEĞİŞKEN FON", "mixed"),

        # index (non-equity)
        ("ANONIM PORTFÖY BIST TAHVİL ENDEKSİ FONU", "index"),

        # fallback
        ("OPAQUE PORTFÖY MUTLAK GETİRİ SERBEST FONU", "other"),
    ],
)
def test_bucket_from_name_matches_expected(name: str, expected: str) -> None:
    assert bucket_from_name(name) == expected


def test_bucket_from_name_handles_lowercase_and_whitespace() -> None:
    assert bucket_from_name("  ata portföy hisse senedi fonu  ") == "equity"


def test_bucket_from_name_empty_or_none() -> None:
    assert bucket_from_name("") == "other"
    assert bucket_from_name(None) == "other"  # type: ignore[arg-type]
