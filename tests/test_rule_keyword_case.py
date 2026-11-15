"""Selection-rule keywords match regardless of the case they were saved in."""

import pandas as pd
import pytest

from fundexpert.data.merge import clean_candidates
from fundexpert.select.sector import sector_from_names
from fundexpert.select.strategy import bucket_from_names
from fundexpert.utils import rules as rules_module
from fundexpert.utils.text import turkish_upper_series


@pytest.fixture
def install_rules(monkeypatch):
    def install(**rules):
        monkeypatch.setattr(rules_module, "_read_rules_json", lambda: rules)
        rules_module.clear_rules_cache()

    yield install
    monkeypatch.undo()
    rules_module.clear_rules_cache()


@pytest.mark.parametrize(
    "keyword",
    ["hisse senedi", "Hisse Senedi", "HİSSE SENEDİ", "hİSSE sENEDİ"],
)
def test_strategy_keyword_matches_in_any_case(install_rules, keyword):
    install_rules(bucket_rules=[[keyword, "equity"]])
    names = turkish_upper_series(
        pd.Series(["AK PORTFÖY HİSSE SENEDİ FONU", "Ak Portföy Hisse Senedi Fonu"])
    )

    assert bucket_from_names(names).tolist() == ["equity", "equity"]


@pytest.mark.parametrize("keyword", ["altın", "Altın", "ALTIN"])
def test_strategy_keyword_folds_dotless_i(install_rules, keyword):
    install_rules(bucket_rules=[[keyword, "precious_metals"]])
    names = turkish_upper_series(pd.Series(["X PORTFÖY ALTIN FONU"]))

    assert bucket_from_names(names).tolist() == ["precious_metals"]


def test_strategy_keyword_keeps_dotted_and_dotless_i_apart(install_rules):
    # Live titles spell some words with ASCII I, so the two letters stay distinct.
    install_rules(bucket_rules=[["değişken", "mixed"]])
    names = pd.Series(["A PORTFÖY DEĞİŞKEN FON", "B PORTFÖY DEĞIŞKEN FON"])

    assert bucket_from_names(names).tolist() == ["mixed", "other"]


@pytest.mark.parametrize(
    ("keyword", "name"),
    [
        ("teknoloji", "X PORTFÖY TEKNOLOJİ SEKTÖRÜ FONU"),
        ("Sağlık", "X PORTFÖY SAĞLIK SEKTÖRÜ FONU"),
        ("bankacılık", "X PORTFÖY BANKACILIK FONU"),
    ],
)
def test_sector_keyword_matches_in_any_case(install_rules, keyword, name):
    install_rules(sector_rules=[[keyword, "themed"]])

    assert sector_from_names(pd.Series([name])).tolist() == ["themed"]


def test_loaded_rules_keep_first_match_order_and_categories(install_rules):
    install_rules(
        bucket_rules=[["para piyasası", "money_market"], ["serbest", "unconstrained"]],
        sector_rules=[["enerji", "energy"]],
    )

    assert rules_module.get_bucket_rules() == (
        ("PARA PİYASASI", "money_market"),
        ("SERBEST", "unconstrained"),
    )
    assert rules_module.get_sector_rules() == (("ENERJİ", "energy"),)


@pytest.mark.parametrize("keyword", ["katılım", "Katılım", "KATILIM"])
def test_exclusion_keyword_matches_in_any_case(install_rules, keyword):
    install_rules(exclusion_rules=[keyword])
    candidates = pd.DataFrame(
        {
            "fon_kodu": ["AAA", "BBB", "CCC"],
            "fon_adi": [
                "A PORTFÖY KATILIM FONU",
                "B PORTFÖY PARA PİYASASI FONU",
                "C PORTFÖY HİSSE SENEDİ FONU",
            ],
            "umbrella_type": [
                "Hisse Senedi Şemsiye Fonu",
                "Katılım Şemsiye Fonu",
                "Hisse Senedi Şemsiye Fonu",
            ],
            "applied_management_fee_pct": [1.0, 1.0, 1.0],
        }
    )

    assert clean_candidates(candidates)["fon_kodu"].tolist() == ["CCC"]
