import pytest

from fundexpert.news.match import extract_company_prefix


@pytest.mark.parametrize("fon_adi,expected", [
    # Standard PORTFÖY pattern at varying positions.
    ("ATA PORTFÖY ÇOKLU VARLIK DEĞİŞKEN FON", "ATA PORTFÖY"),
    ("AK PORTFÖY EUROBOND BORÇLANMA ARAÇLARI FONU", "AK PORTFÖY"),
    ("İŞ PORTFÖY BIST 30 ENDEKSİ HİSSE SENEDİ FONU", "İŞ PORTFÖY"),
    ("ZİRAAT PORTFÖY KİRA SERTİFİKALARI KATILIM FONU", "ZİRAAT PORTFÖY"),
    # Multi-word company names.
    ("BNP PARIBAS CARDIF EMEKLİLİK PORTFÖY DEĞİŞKEN FON", "BNP PARIBAS CARDIF EMEKLİLİK PORTFÖY"),
    # Lowercase Turkish input.
    ("ata portföy çoklu varlık fon", "ATA PORTFÖY"),
    # Lowercase dotted-i: tests the i→İ workaround.
    ("iş portföy bist hisse fonu", "İŞ PORTFÖY"),
    # Missing diacritic on PORTFOY (defensive).
    ("AK PORTFOY EUROBOND FONU", "AK PORTFOY"),
    # No PORTFÖY at all → first 3 tokens fallback.
    ("OPAQUE FUND NAME WITHOUT COMPANY", "OPAQUE FUND NAME"),
    # Single-word edge (fallback returns whatever there is).
    ("MYSTERY", "MYSTERY"),
    # Empty / None.
    ("", ""),
    (None, ""),
    ("   ", ""),
])
def test_extract_company_prefix(fon_adi, expected):
    assert extract_company_prefix(fon_adi) == expected


def test_extract_handles_trailing_punctuation_after_portfoy():
    """Defensive: titles may add trailing punctuation; the match must still bite."""
    assert extract_company_prefix("ATA PORTFÖY, ÇOKLU VARLIK FON") == "ATA PORTFÖY"
