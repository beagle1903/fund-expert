import pytest

from fundexpert.select.sector import sector_from_name


@pytest.mark.parametrize("name,expected", [
    ("ALLIANZ YAŞAM VE EMEKLİLİK A.Ş. TEKNOLOJİ SEKTÖRÜ FON SEPETİ EMEKLİLİK YATIRIM FONU", "tech"),
    ("ANADOLU HAYAT EMEKLİLİK A.Ş. TEKNOLOJİ SEKTÖRÜ HİSSE SENEDİ EMEKLİLİK YATIRIM FONU", "tech"),
    ("İŞ PORTFÖY DİJİTAL OYUN SEKTÖRÜ KARMA FON", "tech"),
    ("X PORTFÖY SAĞLIK SEKTÖRÜ HİSSE SENEDİ FON", "health"),
    ("AK PORTFÖY PETROL YABANCI BYF FON SEPETİ FONU", "energy"),
    ("Y PORTFÖY ENERJİ SEKTÖRÜ HİSSE SENEDİ FON", "energy"),
    ("Z PORTFÖY BANKACILIK SEKTÖRÜ HİSSE SENEDİ FON", "finance"),
    ("Q PORTFÖY GAYRİMENKUL HİSSE SENEDİ FON", "real_estate"),
    ("PUSULA PORTFÖY BİRİNCİ DEĞİŞKEN FON", "diversified"),
    ("AK PORTFÖY EUROBOND BORÇLANMA ARAÇLARI FONU", "diversified"),
    ("", "diversified"),
])
def test_sector_from_name(name, expected):
    assert sector_from_name(name) == expected


def test_sector_handles_lowercase_turkish_i():
    """str.upper() in Python is locale-blind: 'i' → 'I' not 'İ'. Verify the fix."""
    assert sector_from_name("teknoloji sektörü hisse fon") == "tech"
    assert sector_from_name("sağlık sektörü") == "health"


def test_sector_from_name_handles_none():
    assert sector_from_name(None) == "diversified"
