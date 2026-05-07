from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from fundexpert.cli import _prompt, main, run_pipeline


@pytest.fixture
def fake_universe_loader():
    """Patch loaders so cli.run_pipeline doesn't read the filesystem."""
    getiri = pd.DataFrame({
        "fon_kodu": ["A", "B", "C"],
        "fon_adi":  ["A FON", "B FON", "C FON"],
        "umbrella_type": ["Değişken", "Hisse", "Borçlanma"],
        "risk": [3, 6, 2],
        "ret_1m": [4.0, 7.0, 1.0],
        "ret_3m": [2.0, 5.0, 0.5],
        "ret_6m": [10.0, 20.0, 4.0],
        "ret_ytd":[14.0, 18.0, 3.0],
        "ret_1y": [40.0, 55.0, 12.0],
        "ret_3y": [200.0, 300.0, 60.0],
        "ret_5y": [600.0, 700.0, 180.0],
    })
    buyukluk = pd.DataFrame({
        "fon_kodu": ["A", "B", "C"],
        "fon_adi": ["A FON", "B FON", "C FON"],
        "umbrella_type": ["Değişken", "Hisse", "Borçlanma"],
        "aum_first": [1, 1, 1], "aum_last": [1, 1, 1],
        "aum_change_pct": [5.0, -2.0, 8.0],
        "units_first": [1, 1, 1], "units_last": [1, 1, 1],
        "units_change_pct": [0, 0, 0],
    })
    yonetim = pd.DataFrame({
        "fon_kodu": ["A", "B", "C"],
        "fon_adi": ["A FON", "B FON", "C FON"],
        "umbrella_type": ["Değişken", "Hisse", "Borçlanma"],
        "applied_management_fee_pct": [1.0, 2.0, 0.5],
        "bylaw_management_fee_pct": [1.0, 2.0, 0.5],
        "max_total_expense_pct": [3.0, 4.0, 1.5],
    })
    frames = {"getiri": getiri, "buyukluk": buyukluk, "yonetim_ucreti": yonetim}
    with patch("fundexpert.cli.load_universe", return_value=frames):
        yield


def test_run_pipeline_returns_selected_with_weights(fake_universe_loader):
    selected, header, hits, _ = run_pipeline(
        universe="tefas",
        risk_level="medium",
        horizon="medium",
        volume_priority="medium",
        fee_priority="medium",
        n=2,
        max_per_type=2,
        now=datetime(2026, 5, 2, 11, 42),
    )
    assert len(selected) == 2
    assert "display_weight_pct" in selected.columns
    assert sum(selected["display_weight_pct"]) == pytest.approx(100.0)
    assert header["candidate_total"] == 3
    # News disabled by default → empty hits dict.
    assert hits == {}


def test_run_pipeline_returns_news_meta_with_enabled_false_when_news_off(fake_universe_loader):
    selected, header, hits, news_meta = run_pipeline(
        universe="tefas", risk_level="medium", horizon="medium",
        volume_priority="medium", fee_priority="medium",
        n=2, max_per_type=2, now=datetime(2026, 5, 2, 11, 42),
    )
    assert news_meta == {"enabled": False}


def _make_questionary_mock(answers: list):
    """Build a questionary stub whose .select/.text(...).ask() returns answers in order."""
    iterator = iter(answers)

    def _factory(*_args, **_kwargs):
        prompt = MagicMock()
        prompt.ask.return_value = next(iterator)
        return prompt

    qmock = MagicMock()
    qmock.select.side_effect = _factory
    qmock.text.side_effect = _factory
    return qmock


@pytest.mark.parametrize("cancel_at", range(6))
def test_prompt_returns_none_when_user_cancels(cancel_at):
    """Cancelling at any prompt step yields None instead of crashing on int(None)."""
    answers = ["tefas", "medium", "medium", "medium", "medium", "5"]
    answers[cancel_at] = None
    qmock = _make_questionary_mock(answers)
    with patch.dict("sys.modules", {"questionary": qmock}):
        assert _prompt(last={}) is None


def test_main_exits_cleanly_on_cancellation(capsys):
    with patch("sys.argv", ["fundexpert"]), \
         patch("fundexpert.cli._prompt", return_value=None):
        rc = main()
    assert rc == 130
    assert "İptal" in capsys.readouterr().err


def test_main_exits_cleanly_on_keyboard_interrupt(capsys):
    with patch("sys.argv", ["fundexpert"]), \
         patch("fundexpert.cli._prompt", side_effect=KeyboardInterrupt):
        rc = main()
    assert rc == 130
    assert "İptal" in capsys.readouterr().err


def test_run_pipeline_rejects_both_universe():
    with pytest.raises(ValueError, match="tefas.*befas"):
        run_pipeline(
            universe="both", risk_level="medium", horizon="medium",
            volume_priority="medium", fee_priority="medium",
            n=2, max_per_type=2, now=datetime(2026, 5, 2),
        )


def test_main_renders_two_portfolios_when_universe_is_both():
    """`both` runs pipeline once per platform; render_portfolio is called twice."""
    answers = {
        "universe": "both", "risk_level": "medium", "horizon": "medium",
        "volume_priority": "medium", "fee_priority": "medium", "n": 3,
    }
    fake_selected = pd.DataFrame({"display_weight_pct": [50, 50]})
    fake_header = {"warning": None}
    fake_hits: dict = {}
    with patch("sys.argv", ["fundexpert"]), \
         patch("fundexpert.cli._prompt", return_value=answers), \
         patch("fundexpert.cli._save_last_run"), \
         patch("fundexpert.cli.run_pipeline",
               return_value=(fake_selected, fake_header, fake_hits, {"enabled": False})) as run_mock, \
         patch("fundexpert.cli.render_portfolio") as render_mock:
        rc = main()
    assert rc == 0
    assert render_mock.call_count == 2
    universes_called = [call.kwargs["universe"] for call in run_mock.call_args_list]
    assert universes_called == ["tefas", "befas"]


def test_main_passes_news_api_key_when_news_flag_set(monkeypatch):
    """--news + TAVILY_API_KEY env var → run_pipeline called with news_enabled=True."""
    answers = {
        "universe": "tefas", "risk_level": "medium", "horizon": "medium",
        "volume_priority": "medium", "fee_priority": "medium", "n": 3,
    }
    fake_selected = pd.DataFrame({"display_weight_pct": [100]})
    fake_header = {"warning": None}
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")
    with patch("sys.argv", ["fundexpert", "--news"]), \
         patch("fundexpert.cli._prompt", return_value=answers), \
         patch("fundexpert.cli._save_last_run"), \
         patch("fundexpert.cli.run_pipeline",
               return_value=(fake_selected, fake_header, {}, {"enabled": True, "key_present": True, "top_k": 9, "total_hits": 0, "displaced": []})) as run_mock, \
         patch("fundexpert.cli.render_portfolio"):
        rc = main()
    assert rc == 0
    assert run_mock.call_args.kwargs["news_enabled"] is True
    assert run_mock.call_args.kwargs["news_api_key"] == "tvly-test-key"


def test_main_default_run_does_not_pass_news_key(monkeypatch):
    """No --news flag → news_enabled=False, news_api_key=None."""
    answers = {
        "universe": "tefas", "risk_level": "medium", "horizon": "medium",
        "volume_priority": "medium", "fee_priority": "medium", "n": 3,
    }
    fake_selected = pd.DataFrame({"display_weight_pct": [100]})
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-shouldnt-be-used")
    with patch("sys.argv", ["fundexpert"]), \
         patch("fundexpert.cli._prompt", return_value=answers), \
         patch("fundexpert.cli._save_last_run"), \
         patch("fundexpert.cli.run_pipeline",
               return_value=(fake_selected, {"warning": None}, {}, {"enabled": False})) as run_mock, \
         patch("fundexpert.cli.render_portfolio"):
        main()
    assert run_mock.call_args.kwargs["news_enabled"] is False
    assert run_mock.call_args.kwargs["news_api_key"] is None


def test_run_pipeline_with_news_shifts_picks_when_top_fund_has_negative_news(
    fake_universe_loader,
):
    """End-to-end: hitting the leading fund with a Tavily match flips the order."""
    from fundexpert.news.tavily import NewsHit

    # First find what the top pick is without news, then put negative news on
    # exactly that fund and verify the next run picks something else.
    sel_no_news, _, hits_no_news, _ = run_pipeline(
        universe="tefas", risk_level="medium", horizon="medium",
        volume_priority="medium", fee_priority="medium",
        n=1, max_per_type=2, now=datetime(2026, 5, 2, 11, 42),
        news_enabled=False, news_api_key=None,
    )
    leader_code = sel_no_news.iloc[0]["fon_kodu"]
    leader_prefix = sel_no_news.iloc[0]["fon_adi"].split()[0] + " FON"

    def fake_query(company_prefix, **_kw):
        if company_prefix == leader_prefix:
            return [NewsHit(title=f"{leader_code} hakkında soruşturma",
                            url="https://x.com/p", published=None, source="x.com")]
        return []

    with patch("fundexpert.news.penalty.query_negative_news", side_effect=fake_query):
        sel_with_news, _, _, _ = run_pipeline(
            universe="tefas", risk_level="medium", horizon="medium",
            volume_priority="medium", fee_priority="medium",
            n=1, max_per_type=2, now=datetime(2026, 5, 2, 11, 42),
            news_enabled=True, news_api_key="tvly-test",
        )
    assert hits_no_news == {}
    assert sel_no_news.iloc[0]["fon_kodu"] != sel_with_news.iloc[0]["fon_kodu"]


def test_run_pipeline_news_meta_populates_displaced_when_top_fund_dropped(
    fake_universe_loader,
):
    """A Tavily hit on the top quant fund should land it in news_meta['displaced']."""
    from fundexpert.news.tavily import NewsHit

    sel_no_news, _, _, _ = run_pipeline(
        universe="tefas", risk_level="medium", horizon="medium",
        volume_priority="medium", fee_priority="medium",
        n=1, max_per_type=2, now=datetime(2026, 5, 2),
        news_enabled=False, news_api_key=None,
    )
    leader_code = sel_no_news.iloc[0]["fon_kodu"]
    leader_prefix = sel_no_news.iloc[0]["fon_adi"].split()[0] + " FON"

    def fake_query(company_prefix, **_kw):
        if company_prefix == leader_prefix:
            return [NewsHit(title="dava açıldı", url="https://x.com/p",
                            published=None, source="x.com")]
        return []

    with patch("fundexpert.news.penalty.query_negative_news", side_effect=fake_query):
        sel_news, _, _, news_meta = run_pipeline(
            universe="tefas", risk_level="medium", horizon="medium",
            volume_priority="medium", fee_priority="medium",
            n=1, max_per_type=2, now=datetime(2026, 5, 2),
            news_enabled=True, news_api_key="tvly-test",
        )

    assert sel_news.iloc[0]["fon_kodu"] != leader_code
    assert news_meta["enabled"] is True
    assert news_meta["total_hits"] == 1
    assert len(news_meta["displaced"]) == 1
    d = news_meta["displaced"][0]
    assert d["fon_kodu"] == leader_code
    assert d["score_pre"] > d["score_post"]
    assert d["score_pre"] - d["score_post"] == pytest.approx(0.20)
    assert len(d["hits"]) == 1
    assert d["hits"][0]["title"] == "dava açıldı"


def test_run_pipeline_news_meta_displaced_empty_when_no_hits(fake_universe_loader):
    with patch("fundexpert.news.penalty.query_negative_news", return_value=[]):
        _, _, _, news_meta = run_pipeline(
            universe="tefas", risk_level="medium", horizon="medium",
            volume_priority="medium", fee_priority="medium",
            n=2, max_per_type=2, now=datetime(2026, 5, 2),
            news_enabled=True, news_api_key="tvly-test",
        )
    assert news_meta["total_hits"] == 0
    assert news_meta["displaced"] == []


def test_run_pipeline_news_enabled_without_api_key_falls_back_to_quant(
    fake_universe_loader, capsys,
):
    """news_enabled=True but no key → no penalty, picks identical to news=off."""
    sel_no_news, _, _, _ = run_pipeline(
        universe="tefas", risk_level="medium", horizon="medium",
        volume_priority="medium", fee_priority="medium",
        n=2, max_per_type=2, now=datetime(2026, 5, 2),
        news_enabled=False, news_api_key=None,
    )
    sel_news_no_key, _, hits, _ = run_pipeline(
        universe="tefas", risk_level="medium", horizon="medium",
        volume_priority="medium", fee_priority="medium",
        n=2, max_per_type=2, now=datetime(2026, 5, 2),
        news_enabled=True, news_api_key=None,
    )
    assert list(sel_no_news["fon_kodu"]) == list(sel_news_no_key["fon_kodu"])
    assert hits == {}
    assert "TAVILY_API_KEY tanımlı değil" in capsys.readouterr().err
