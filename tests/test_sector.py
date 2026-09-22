import pytest

import pandas as pd
from fundexpert.select.sector import sector_from_names


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
    assert sector_from_names(pd.Series([name])).iloc[0] == expected


def test_sector_handles_lowercase_turkish_i():
    # Function now expects fully uppercased input from pipeline
    assert sector_from_names(pd.Series(["TEKNOLOJİ SEKTÖRÜ HİSSE FON"])).iloc[0] == "tech"
    assert sector_from_names(pd.Series(["SAĞLIK SEKTÖRÜ"])).iloc[0] == "health"


def test_sector_from_name_handles_none():
    assert sector_from_names(pd.Series([None])).iloc[0] == "diversified"

def test_sector_from_name_handles_whitespace():
    assert sector_from_names(pd.Series(["   "])).iloc[0] == "diversified"
    assert sector_from_names(pd.Series(["\t\n"])).iloc[0] == "diversified"


def test_sector_priority_follows_rules_not_textual_order():
    names = pd.Series([
        "SAĞLIK VE TEKNOLOJİ SEKTÖRLERİ FONU",
        "ENERJİ VE BANKACILIK SEKTÖRLERİ FONU",
    ])

    assert sector_from_names(names).tolist() == ["tech", "energy"]


@pytest.mark.parametrize("name,expected", [
    # EMLAK SEKTÖRÜ is the live real-estate wording. The Emlak Katılım issuer is not.
    ("İŞ PORTFÖY EMLAK SEKTÖRÜ HİSSE SENEDİ FONU (HİSSE SENEDİ YOĞUN FON)", "real_estate"),
    ("AK PORTFÖY EMLAK SEKTÖRÜ DEĞİŞKEN FON", "real_estate"),
    (
        "ANADOLU HAYAT EMEKLİLİK A.Ş. EMLAK SEKTÖRÜ HİSSE SENEDİ EMEKLİLİK YATIRIM FONU",
        "real_estate",
    ),
    ("EMLAK KATILIM PORTFÖY PARA PİYASASI KATILIM (TL) FONU", "diversified"),
    # "BANKA ENDEKS" matches the banking index without matching BANKASI.
    (
        "AK PORTFÖY BIST BANKA ENDEKSİ HİSSE SENEDİ (TL) FONU (HİSSE SENEDİ YOĞUN FON)",
        "finance",
    ),
    (
        "İŞ PORTFÖY İŞ BANKASI İŞTİRAKLERİ ENDEKSİ HİSSE SENEDİ (TL) FONU (HİSSE SENEDİ YOĞUN FON)",
        "diversified",
    ),
    (
        "İŞ PORTFÖY SÜRDÜRÜLEBİLİRLİK HİSSE SENEDİ (TL) FONU (HİSSE SENEDİ YOĞUN FON)",
        "sustainability",
    ),
    ("DENİZ PORTFÖY ESG-SÜRDÜRÜLEBİLİRLİK FON SEPETİ FONU", "sustainability"),
    # TARIM stays ahead of the broader sustainability keyword.
    ("İŞ PORTFÖY SÜRDÜRÜLEBİLİRLİK VE TARIM FON SEPETİ FONU", "agriculture"),
    ("AKTİF PORTFÖY TARIM VE SÜRDÜRÜLEBİLİRLİK FON SEPETİ FONU", "agriculture"),
    (
        "GARANTİ PORTFÖY GARANTİ BBVA İKLİM ENDEKSİ HİSSE SENEDİ (TL) FONU (HİSSE SENEDİ YOĞUN FON)",
        "sustainability",
    ),
    ("ROTA PORTFÖY İKLİM DEĞİŞİKLİĞİ ÇÖZÜMLERİ DEĞİŞKEN FON", "sustainability"),
    ("AZİMUT PORTFÖY EMTİA FON SEPETİ FONU", "commodities"),
    ("AURA PORTFÖY EMTİA SERBEST FON", "commodities"),
    (
        "DENİZ PORTFÖY BİST TEMETTÜ 25 ENDEKSİ HİSSE SENEDİ FONU ( HİSSE SENEDİ YOĞUN FON )",
        "dividend",
    ),
    ("DENİZ PORTFÖY TEMETTÜ ÖDEYEN ŞİRKETLER DEĞİŞKEN FON", "dividend"),
    (
        "ALLIANZ YAŞAM VE EMEKLİLİK A.Ş. BIST TEMETTÜ ENDEKSİ EMEKLİLİK YATIRIM FONU",
        "dividend",
    ),
])
def test_sector_from_name_covers_live_keyword_gaps(name, expected):
    assert sector_from_names(pd.Series([name])).iloc[0] == expected
