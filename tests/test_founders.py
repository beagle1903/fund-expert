from pathlib import Path

import pandas as pd
import pytest

from fundexpert.config import DATA_ROOT
from fundexpert.data.loader import load_candidates_for_universe
from fundexpert.founders import (
    available_founders,
    filter_by_founder,
    founder_from_name,
    validate_founder,
)


@pytest.mark.parametrize(
    ("universe", "fund_name", "expected"),
    [
        (
            "tefas",
            "AK PORTFÖY İKİNCİ PARA PİYASASI (TL) FONU",
            "AK PORTFÖY YÖNETİMİ A.Ş.",
        ),
        (
            "tefas",
            "AZİMUT PYŞ BİRİNCİ HİSSE SENEDİ FONU",
            "AZİMUT PORTFÖY YÖNETİMİ A.Ş.",
        ),
        (
            "befas",
            "ANADOLU HAYAT EMEKLİLİK A.Ş.S&P 500 YABANCI BYF FON SEPETİ",
            "ANADOLU HAYAT EMEKLİLİK A.Ş.",
        ),
        (
            "befas",
            "ALLIANZ YAŞAM VE EMEKLİLİK A.Ş. ALTIN EMEKLİLİK YATIRIM FONU",
            "ALLIANZ YAŞAM VE EMEKLİLİK A.Ş.",
        ),
    ],
)
def test_founder_from_name_handles_platform_specific_titles(
    universe, fund_name, expected
):
    assert founder_from_name(fund_name, universe) == expected


def test_current_real_bundles_have_complete_founder_attribution():
    for universe in ("tefas", "befas"):
        candidates = load_candidates_for_universe(universe, Path(DATA_ROOT))

        assert candidates["kurucu"].notna().all()
        assert available_founders(candidates)


def test_filter_by_founder_keeps_only_exact_canonical_match():
    candidates = pd.DataFrame(
        {
            "kurucu": ["A", "B", "A"],
            "fon_kodu": ["AAA", "BBB", "CCC"],
        }
    )

    filtered = filter_by_founder(candidates, "A")

    assert list(filtered["fon_kodu"]) == ["AAA", "CCC"]


def test_validate_founder_rejects_cross_platform_value():
    with pytest.raises(ValueError, match="not valid for befas"):
        validate_founder("AK PORTFÖY YÖNETİMİ A.Ş.", "befas")
