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
    ("QNB SAĞLIK HAYAT SİGORTA VE EMEKLİLİK A.Ş. HİSSE SENEDİ FON", "diversified"),
    ("QNB SAĞLIK HAYAT SİGORTA VE  EMEKLİLİK A.Ş. DEĞİŞKEN FON", "diversified"),
    ("QNB FİNANS PORTFÖY BİRİNCİ DEĞİŞKEN FON", "diversified"),
    ("TARIM KREDİ PORTFÖY İKİNCİ DEĞİŞKEN FON", "diversified"),
    ("TARIM KREDİ PORTFÖY TARIM SEKTÖRÜ FONU", "agriculture"),
    ("QNB SAĞLIK HAYAT SİGORTA VE EMEKLİLİK A.Ş. SAĞLIK SEKTÖRÜ FONU", "health"),
    ("", "diversified"),
])
def test_sector_from_name(name, expected):
    assert sector_from_name(name) == expected


def test_sector_handles_lowercase_turkish_i():
    # Function now expects fully uppercased input from pipeline
    assert sector_from_name("TEKNOLOJİ SEKTÖRÜ HİSSE FON") == "tech"
    assert sector_from_name("SAĞLIK SEKTÖRÜ") == "health"


def test_sector_from_name_handles_none():
    assert sector_from_name(None) == "diversified"

def test_sector_from_name_handles_whitespace():
    assert sector_from_name("   ") == "diversified"
    assert sector_from_name("\t\n") == "diversified"
