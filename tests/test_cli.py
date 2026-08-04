from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from fundexpert.cli import main, DATA_ROOT
from fundexpert.data.loader import load_candidates_for_universe
from fundexpert.pipeline import PipelineConfig, PipelineResult, run_pipeline
from fundexpert.ui import ensure_utf8_stdio, prompt_user


def _load_one(universe):
    return load_candidates_for_universe(universe, DATA_ROOT)


@pytest.fixture(autouse=True)
def isolate_cli_run_history(monkeypatch, tmp_path):
    """Never let CLI tests write fixture portfolios into the user's history."""
    monkeypatch.setattr("fundexpert.cli.HISTORY_DIR", tmp_path / "runs")


@pytest.fixture
def fake_universe_loader():
    from fundexpert.data.loader import UniverseData
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
    frames = UniverseData(getiri=getiri, buyukluk=buyukluk, yonetim_ucreti=yonetim)
    with patch("fundexpert.data.bundle.resolve_active_bundle"), \
         patch("fundexpert.data.bundle.load_bundle_frames", return_value=frames):
        yield


def test_run_pipeline_returns_selected_with_weights(fake_universe_loader):
    candidates = _load_one("tefas")

    res = run_pipeline(candidates=candidates, config=PipelineConfig(universe="tefas", risk_level="medium", horizon="medium", volume_priority="medium", fee_priority="medium", momentum_priority="medium", n=2, max_per_type=2, now=datetime(2026, 5, 2, 11, 42)))
    assert len(res.weighted) == 2
    assert "display_weight_pct" in res.weighted.columns
    assert sum(res.weighted["display_weight_pct"]) == pytest.approx(100.0)
    assert res.header["candidate_total"] == 3
    # News disabled by default → empty hits dict.
    assert res.hits_for_render == {}


def test_run_pipeline_returns_news_meta_with_enabled_false_when_news_off(fake_universe_loader):
    candidates = _load_one("tefas")

    res = run_pipeline(candidates=candidates, config=PipelineConfig(universe="tefas", risk_level="medium", horizon="medium", volume_priority="medium", fee_priority="medium", momentum_priority="medium", n=2, max_per_type=2, now=datetime(2026, 5, 2, 11, 42)))
    assert res.news_meta == {"enabled": False}


def test_run_pipeline_filters_by_founder_before_scoring(fake_universe_loader):
    candidates = _load_one("tefas").copy()
    founder = "AK PORTFÖY YÖNETİMİ A.Ş."
    candidates["kurucu"] = [founder, "ATA PORTFÖY YÖNETİMİ A.Ş.", founder]

    res = run_pipeline(
        candidates=candidates,
        config=PipelineConfig(
            universe="tefas",
            risk_level="medium",
            horizon="medium",
            volume_priority="medium",
            fee_priority="medium",
            momentum_priority="medium",
            n=2,
            max_per_type=2,
            now=datetime(2026, 5, 2, 11, 42),
            founder=founder,
        ),
    )

    assert set(res.weighted["fon_kodu"]) == {"A", "C"}
    assert res.header["candidate_total"] == 3
    assert res.header["candidate_after_founder"] == 2
    assert res.header["founder"] == founder


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


@pytest.mark.parametrize("cancel_at", range(8))
def test_prompt_returns_none_when_user_cancels(cancel_at):
    """Cancelling at any prompt step yields None instead of crashing on int(None)."""
    answers = [
        "tefas",
        "__all__",
        "medium",
        "medium",
        "medium",
        "medium",
        "medium",
        "5",
    ]
    answers[cancel_at] = None
    qmock = _make_questionary_mock(answers)
    with patch.dict("sys.modules", {"questionary": qmock}):
        assert prompt_user(last={}) is None


def test_main_exits_cleanly_on_cancellation(capsys):
    with patch("sys.argv", ["fundexpert"]), \
         patch("fundexpert.cli.prompt_user", return_value=None):
        rc = main()
    assert rc == 130
    assert "İptal" in capsys.readouterr().err


def test_main_exits_cleanly_on_keyboard_interrupt(capsys):
    with patch("sys.argv", ["fundexpert"]), \
         patch("fundexpert.cli.prompt_user", side_effect=KeyboardInterrupt):
        rc = main()
    assert rc == 130
    assert "İptal" in capsys.readouterr().err


def test_main_passes_diversification_mode_and_optional_overrides(monkeypatch):
    captured = []
    answers = {
        "universe": "tefas",
        "risk_level": "medium",
        "horizon": "medium",
        "volume_priority": "medium",
        "fee_priority": "medium",
        "momentum_priority": "medium",
        "n": 12,
    }

    monkeypatch.setattr(
        "sys.argv",
        [
            "fundexpert",
            "--diversification",
            "relaxed",
            "--max-per-sector",
            "6",
        ],
    )
    monkeypatch.setattr("fundexpert.cli.prompt_user", lambda _: answers)
    monkeypatch.setattr("fundexpert.cli.save_last_run_state", lambda _: None)
    monkeypatch.setattr(
        "fundexpert.cli.load_candidates_for_universe",
        lambda *args: object(),
    )

    def fake_run_pipeline(candidates, config):
        captured.append(config)
        return PipelineResult(
            weighted=pd.DataFrame(
                {
                    "fon_kodu": ["AAA"],
                    "fon_adi": ["ALPHA FON"],
                    "display_weight_pct": [100],
                    "score": [0.7],
                    "risk": [3],
                }
            ),
            header={"warning": None},
            hits_for_render={},
            news_meta={"enabled": False},
        )

    monkeypatch.setattr("fundexpert.cli.run_pipeline", fake_run_pipeline)
    monkeypatch.setattr("fundexpert.cli.save_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "fundexpert.cli.render_portfolio", lambda *args, **kwargs: None
    )

    assert main() == 0
    assert captured[0].diversification_mode == "relaxed"
    assert captured[0].max_per_type is None
    assert captured[0].max_per_sector == 6


@pytest.mark.parametrize(
    ("flag", "value"),
    [
        ("--max-per-type", "0"),
        ("--max-per-type", "21"),
        ("--max-per-sector", "0"),
        ("--max-per-sector", "21"),
    ],
)
def test_main_rejects_invalid_explicit_cap(monkeypatch, flag, value):
    monkeypatch.setattr("sys.argv", ["fundexpert", flag, value])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 2


def test_run_pipeline_rejects_both_universe():
    with pytest.raises(ValueError, match="tefas.*befas"):
        run_pipeline(candidates=None, config=PipelineConfig(universe="both", risk_level="medium", horizon="medium", volume_priority="medium", fee_priority="medium", momentum_priority="medium", n=2, max_per_type=2, now=datetime(2026, 5, 2)))


def test_main_renders_two_portfolios_when_universe_is_both():
    """`both` runs pipeline once per platform; render_portfolio is called twice."""
    answers = {
        "universe": "both", "risk_level": "medium", "horizon": "medium",
        "volume_priority": "medium", "fee_priority": "medium", "momentum_priority": "medium", "n": 3,
    }
    fake_selected = pd.DataFrame({
        "fon_kodu": ["AAK", "BBK"], "fon_adi": ["AK FON", "BK FON"],
        "umbrella_type": ["Değişken", "Hisse"], "risk": [3, 4],
        "display_weight_pct": [50.0, 50.0], "score": [0.7, 0.6],
    })
    fake_header = {"warning": None, "timestamp": datetime(2026, 1, 1), "universe": "both", "risk_level": "medium", "horizon": "medium", "volume_priority": "medium", "fee_priority": "medium", "n": 3, "candidate_total": 2}
    
    mock_res = PipelineResult(weighted=fake_selected, header=fake_header, hits_for_render={}, news_meta={"enabled": False})
    
    with patch("sys.argv", ["fundexpert"]), \
         patch("fundexpert.cli.prompt_user", return_value=answers), \
         patch("fundexpert.cli.save_last_run_state"), \
         patch("fundexpert.cli.run_pipeline", return_value=mock_res) as run_mock, \
         patch("fundexpert.cli.render_portfolio") as render_mock:
        rc = main()
    assert rc == 0
    assert render_mock.call_count == 2
    universes_called = [call.kwargs["config"].universe for call in run_mock.call_args_list]
    assert universes_called == ["tefas", "befas"]


def test_main_passes_news_api_key_when_news_flag_set(monkeypatch):
    """--news + TAVILY_API_KEY env var → run_pipeline called with news_enabled=True."""
    answers = {
        "universe": "tefas", "risk_level": "medium", "horizon": "medium",
        "volume_priority": "medium", "fee_priority": "medium", "momentum_priority": "medium", "n": 3,
    }
    fake_selected = pd.DataFrame({
        "fon_kodu": ["AAK"], "fon_adi": ["AK FON"],
        "umbrella_type": ["Değişken"], "risk": [3],
        "display_weight_pct": [100.0], "score": [0.7],
    })
    fake_header = {"warning": None, "timestamp": datetime(2026, 1, 1), "universe": "tefas", "risk_level": "medium", "horizon": "medium", "volume_priority": "medium", "fee_priority": "medium", "n": 3, "candidate_total": 1}
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")
    
    mock_res = PipelineResult(weighted=fake_selected, header=fake_header, hits_for_render={}, news_meta={"enabled": True, "key_present": True, "top_k": 9, "total_hits": 0, "displaced": []})
    
    with patch("sys.argv", ["fundexpert", "--news"]), \
         patch("fundexpert.cli.prompt_user", return_value=answers), \
         patch("fundexpert.cli.save_last_run_state"), \
         patch("fundexpert.cli.run_pipeline", return_value=mock_res) as run_mock, \
         patch("fundexpert.cli.render_portfolio"):
        rc = main()
    assert rc == 0
    assert run_mock.call_args.kwargs["config"].news_enabled is True
    assert run_mock.call_args.kwargs["config"].news_api_key == "tvly-test-key"


def test_main_passes_selected_founder_to_pipeline():
    founder = "AK PORTFÖY YÖNETİMİ A.Ş."
    answers = {
        "universe": "tefas",
        "founders": {"tefas": founder},
        "risk_level": "medium",
        "horizon": "medium",
        "volume_priority": "medium",
        "fee_priority": "medium",
        "momentum_priority": "medium",
        "n": 3,
    }
    fake_selected = pd.DataFrame(
        {
            "fon_kodu": ["AAK"],
            "fon_adi": ["AK FON"],
            "umbrella_type": ["Değişken"],
            "risk": [3],
            "display_weight_pct": [100.0],
            "score": [0.7],
        }
    )
    mock_res = PipelineResult(
        weighted=fake_selected,
        header={
            "warning": None,
            "timestamp": datetime(2026, 1, 1),
            "universe": "tefas",
            "risk_level": "medium",
            "horizon": "medium",
            "volume_priority": "medium",
            "fee_priority": "medium",
            "n": 3,
            "candidate_total": 1,
        },
        hits_for_render={},
        news_meta={"enabled": False},
    )

    with (
        patch("sys.argv", ["fundexpert"]),
        patch("fundexpert.cli.prompt_user", return_value=answers),
        patch("fundexpert.cli.save_last_run_state"),
        patch("fundexpert.cli.run_pipeline", return_value=mock_res) as run_mock,
        patch("fundexpert.cli.render_portfolio"),
    ):
        assert main() == 0

    assert run_mock.call_args.kwargs["config"].founder == founder


def test_main_default_run_does_not_pass_news_key(monkeypatch):
    """No --news flag → news_enabled=False, news_api_key=None."""
    answers = {
        "universe": "tefas", "risk_level": "medium", "horizon": "medium",
        "volume_priority": "medium", "fee_priority": "medium", "momentum_priority": "medium", "n": 3,
    }
    fake_selected = pd.DataFrame({
        "fon_kodu": ["AAK"], "fon_adi": ["AK FON"],
        "umbrella_type": ["Değişken"], "risk": [3],
        "display_weight_pct": [100.0], "score": [0.7],
    })
    fake_header = {"warning": None, "timestamp": datetime(2026, 1, 1), "universe": "tefas", "risk_level": "medium", "horizon": "medium", "volume_priority": "medium", "fee_priority": "medium", "n": 3, "candidate_total": 1}
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-shouldnt-be-used")
    
    mock_res = PipelineResult(weighted=fake_selected, header=fake_header, hits_for_render={}, news_meta={"enabled": False})
    
    with patch("sys.argv", ["fundexpert"]), \
         patch("fundexpert.cli.prompt_user", return_value=answers), \
         patch("fundexpert.cli.save_last_run_state"), \
         patch("fundexpert.cli.run_pipeline", return_value=mock_res) as run_mock, \
         patch("fundexpert.cli.render_portfolio"):
        main()
    assert run_mock.call_args.kwargs["config"].news_enabled is False
    assert run_mock.call_args.kwargs["config"].news_api_key is None


def test_run_pipeline_with_news_shifts_picks_when_top_fund_has_negative_news(
    fake_universe_loader,
):
    """End-to-end: hitting the leading fund with a Tavily match flips the order."""
    from fundexpert.news.tavily import NewsHit

    # First find what the top pick is without news, then put negative news on
    # exactly that fund and verify the next run picks something else.
    candidates = _load_one("tefas")

    res_no_news = run_pipeline(candidates=candidates, config=PipelineConfig(universe="tefas", risk_level="medium", horizon="medium", volume_priority="medium", fee_priority="medium", momentum_priority="medium", n=1, max_per_type=2, now=datetime(2026, 5, 2, 11, 42),
        news_enabled=False, news_api_key=None))
    leader_code = res_no_news.weighted.iloc[0]["fon_kodu"]
    leader_prefix = res_no_news.weighted.iloc[0]["fon_adi"].split()[0] + " FON"

    def fake_query(company_prefix, **_kw):
        if company_prefix == leader_prefix:
            return [NewsHit(title=f"{leader_code} hakkında soruşturma",
                            url="https://x.com/p", published=None, source="x.com")]
        return []

    with patch("fundexpert.news.penalty.query_negative_news", side_effect=fake_query):
        candidates = _load_one("tefas")

        res_news = run_pipeline(candidates=candidates, config=PipelineConfig(universe="tefas", risk_level="medium", horizon="medium", volume_priority="medium", fee_priority="medium", momentum_priority="medium", n=1, max_per_type=2, now=datetime(2026, 5, 2, 11, 42),
            news_enabled=True, news_api_key="tvly-test"))
    assert res_no_news.hits_for_render == {}
    assert res_no_news.weighted.iloc[0]["fon_kodu"] != res_news.weighted.iloc[0]["fon_kodu"]


def test_run_pipeline_news_meta_populates_displaced_when_top_fund_dropped(
    fake_universe_loader,
):
    """A Tavily hit on the top quant fund should land it in news_meta['displaced']."""
    from fundexpert.news.tavily import NewsHit

    candidates = _load_one("tefas")

    res_no_news = run_pipeline(candidates=candidates, config=PipelineConfig(universe="tefas", risk_level="medium", horizon="medium", volume_priority="medium", fee_priority="medium", momentum_priority="medium", n=1, max_per_type=2, now=datetime(2026, 5, 2),
        news_enabled=False, news_api_key=None))
    leader_code = res_no_news.weighted.iloc[0]["fon_kodu"]
    leader_prefix = res_no_news.weighted.iloc[0]["fon_adi"].split()[0] + " FON"

    def fake_query(company_prefix, **_kw):
        if company_prefix == leader_prefix:
            return [NewsHit(title="dava açıldı", url="https://x.com/p",
                            published=None, source="x.com")]
        return []

    with patch("fundexpert.news.penalty.query_negative_news", side_effect=fake_query):
        candidates = _load_one("tefas")

        res_news = run_pipeline(candidates=candidates, config=PipelineConfig(universe="tefas", risk_level="medium", horizon="medium", volume_priority="medium", fee_priority="medium", momentum_priority="medium", n=1, max_per_type=2, now=datetime(2026, 5, 2),
            news_enabled=True, news_api_key="tvly-test"))

    assert res_news.weighted.iloc[0]["fon_kodu"] != leader_code
    assert res_news.news_meta["enabled"] is True
    assert res_news.news_meta["total_hits"] == 1
    assert len(res_news.news_meta["displaced"]) == 1
    d = res_news.news_meta["displaced"][0]
    assert d["fon_kodu"] == leader_code
    assert d["score_pre"] > d["score_post"]
    assert d["score_pre"] - d["score_post"] == pytest.approx(0.20)
    assert len(d["hits"]) == 1
    assert d["hits"][0]["title"] == "dava açıldı"


def test_run_pipeline_news_meta_displaced_sorted_by_score_pre_desc(
    fake_universe_loader,
):
    """Multiple displaced funds must come back in deterministic order
    (strongest pre-penalty score first), not set-iteration order."""
    from fundexpert.news.tavily import NewsHit

    def fake_query(company_prefix, **_kw):
        # Match every fund — penalty pushes them all out, displacing 2 of 3.
        return [NewsHit(title=f"{company_prefix} soruşturma",
                        url="https://x", published=None, source="x.com")]

    with patch("fundexpert.news.penalty.query_negative_news", side_effect=fake_query):
        candidates = _load_one("tefas")

        res = run_pipeline(candidates=candidates, config=PipelineConfig(universe="tefas", risk_level="medium", horizon="medium", volume_priority="medium", fee_priority="medium", momentum_priority="medium", n=1, max_per_type=2, now=datetime(2026, 5, 2),
            news_enabled=True, news_api_key="tvly-test"))

    if len(res.news_meta["displaced"]) >= 2:
        scores = [d["score_pre"] for d in res.news_meta["displaced"]]
        assert scores == sorted(scores, reverse=True), (
            f"Expected displaced sorted by score_pre desc, got {scores}"
        )


def test_run_pipeline_news_meta_displaced_empty_when_no_hits(fake_universe_loader):
    with patch("fundexpert.news.penalty.query_negative_news", return_value=[]):
        candidates = _load_one("tefas")

        res = run_pipeline(candidates=candidates, config=PipelineConfig(universe="tefas", risk_level="medium", horizon="medium", volume_priority="medium", fee_priority="medium", momentum_priority="medium", n=2, max_per_type=2, now=datetime(2026, 5, 2),
            news_enabled=True, news_api_key="tvly-test"))
    assert res.news_meta["total_hits"] == 0
    assert res.news_meta["displaced"] == []


def test_run_pipeline_news_enabled_without_api_key_falls_back_to_quant(
    fake_universe_loader, capsys,
):
    """news_enabled=True but no key → no penalty, picks identical to news=off."""
    candidates = _load_one("tefas")

    res_no_news = run_pipeline(candidates=candidates, config=PipelineConfig(universe="tefas", risk_level="medium", horizon="medium", volume_priority="medium", fee_priority="medium", momentum_priority="medium", n=2, max_per_type=2, now=datetime(2026, 5, 2),
        news_enabled=False, news_api_key=None))
    candidates = _load_one("tefas")

    res_news_no_key = run_pipeline(candidates=candidates, config=PipelineConfig(universe="tefas", risk_level="medium", horizon="medium", volume_priority="medium", fee_priority="medium", momentum_priority="medium", n=2, max_per_type=2, now=datetime(2026, 5, 2),
        news_enabled=True, news_api_key=None))
    assert list(res_no_news.weighted["fon_kodu"]) == list(res_news_no_key.weighted["fon_kodu"])
    assert res_news_no_key.hits_for_render == {}
    assert "TAVILY_API_KEY tanımlı değil" in capsys.readouterr().err


def test_main_saves_run_on_every_execution(monkeypatch):
    """save_run is called once per universe even without --diff-last."""
    monkeypatch.setattr("sys.argv", ["fundexpert"])
    monkeypatch.setattr("fundexpert.cli.prompt_user", lambda _: {
        "universe": "tefas", "risk_level": "medium", "horizon": "medium",
        "volume_priority": "medium", "fee_priority": "medium", "momentum_priority": "medium", "n": 5,
    })
    full_header = {
        "timestamp": datetime(2026, 5, 12, 10, 0),
        "universe": "tefas", "risk_level": "medium", "horizon": "medium",
        "volume_priority": "medium", "fee_priority": "medium", "n": 5,
        "candidate_total": 100, "candidate_kept": 90, "warning": None,
        "excluded_horizon": 0,
    }
    fake_selected = pd.DataFrame({
        "fon_kodu": ["AAK"], "fon_adi": ["AK FON"],
        "umbrella_type": ["Değişken"], "risk": [3],
        "display_weight_pct": [100.0], "score": [0.7],
    })
    
    mock_res = PipelineResult(weighted=fake_selected, header=full_header, hits_for_render={}, news_meta={"enabled": False})
    
    monkeypatch.setattr("fundexpert.cli.run_pipeline", lambda **kw: mock_res)
    save_calls = []
    monkeypatch.setattr("fundexpert.cli.save_run",
                        lambda selected, header, history_dir: save_calls.append(1) or Path("/tmp/x.json"))
    monkeypatch.setattr("fundexpert.cli.render_portfolio", lambda *a, **kw: None)
    from fundexpert.cli import main
    result = main()
    assert result == 0
    assert len(save_calls) == 1


def test_main_diff_last_calls_render_diff_when_previous_exists(monkeypatch):
    """--diff-last calls render_diff when a previous run is available."""
    monkeypatch.setattr("sys.argv", ["fundexpert", "--diff-last"])
    monkeypatch.setattr("fundexpert.cli.prompt_user", lambda _: {
        "universe": "tefas", "risk_level": "medium", "horizon": "medium",
        "volume_priority": "medium", "fee_priority": "medium", "momentum_priority": "medium", "n": 5,
    })
    full_header = {
        "timestamp": datetime(2026, 5, 12, 10, 0),
        "universe": "tefas", "risk_level": "medium", "horizon": "medium",
        "volume_priority": "medium", "fee_priority": "medium", "n": 5,
        "candidate_total": 100, "candidate_kept": 90, "warning": None,
        "excluded_horizon": 0,
    }
    from pathlib import Path
    fake_selected = pd.DataFrame({
        "fon_kodu": ["AAK"], "fon_adi": ["AK FON"],
        "umbrella_type": ["Değişken"], "risk": [3],
        "display_weight_pct": [100.0], "score": [0.7],
    })
    fake_previous = {"timestamp": "2026-05-01T09:00:00", "universe": "tefas", "picks": []}
    
    mock_res = PipelineResult(weighted=fake_selected, header=full_header, hits_for_render={}, news_meta={"enabled": False})
    
    monkeypatch.setattr("fundexpert.cli.run_pipeline", lambda **kw: mock_res)
    monkeypatch.setattr("fundexpert.cli.save_run",
                        lambda selected, header, history_dir: Path("/tmp/x.json"))
    monkeypatch.setattr("fundexpert.cli.load_last_run",
                        lambda universe, history_dir: fake_previous)
    monkeypatch.setattr("fundexpert.cli.render_portfolio", lambda *a, **kw: None)
    diff_calls = []
    monkeypatch.setattr("fundexpert.cli.render_diff",
                        lambda selected, previous: diff_calls.append(previous))
    from fundexpert.cli import main
    result = main()
    assert result == 0
    assert len(diff_calls) == 1
    assert diff_calls[0] == fake_previous


def test_ensure_utf8_stdio():
    from unittest.mock import MagicMock
    import sys
    mock_stdout = MagicMock()
    mock_stderr = MagicMock()
    
    orig_stdout = sys.stdout
    orig_stderr = sys.stderr
    
    try:
        sys.stdout = mock_stdout
        sys.stderr = mock_stderr
        ensure_utf8_stdio()
        mock_stdout.reconfigure.assert_called_once_with(encoding="utf-8", errors="replace")
        mock_stderr.reconfigure.assert_called_once_with(encoding="utf-8", errors="replace")
    finally:
        sys.stdout = orig_stdout
        sys.stderr = orig_stderr


def test_main_refreshes_each_selected_universe_before_generation(monkeypatch):
    from fundexpert.data.refresh import DataRefreshResult
    from fundexpert.data.bundle import resolve_active_bundle

    answers = {
        "universe": "both",
        "risk_level": "medium",
        "horizon": "medium",
        "volume_priority": "medium",
        "fee_priority": "medium",
        "momentum_priority": "medium",
        "n": 3,
    }
    calls = []

    def refresh(universe, data_root, *, force, now):
        calls.append((universe, force))
        manifest = resolve_active_bundle(universe, data_root).manifest
        return DataRefreshResult(universe, False, manifest)

    monkeypatch.setattr("sys.argv", ["fundexpert", "--refresh"])
    monkeypatch.setattr("fundexpert.cli.prompt_user", lambda _: answers)
    monkeypatch.setattr("fundexpert.cli.save_last_run_state", lambda _: None)
    monkeypatch.setattr("fundexpert.cli.refresh_universe", refresh)
    monkeypatch.setattr("fundexpert.cli.render_portfolio", lambda *args, **kwargs: None)
    monkeypatch.setattr("fundexpert.cli.save_run", lambda *args, **kwargs: None)

    assert main() == 0
    assert calls == [
        ("tefas", False),
        ("befas", False),
    ]

def test_load_last_run_returns_empty_on_oserror():
    from fundexpert.history.store import load_last_run
    from pathlib import Path
    with patch("pathlib.Path.read_text", side_effect=OSError("Permission denied")), \
         patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.glob", return_value=[Path("/tmp/foo")]):
        assert load_last_run("tefas", Path("/tmp")) is None

def test_load_last_run_returns_empty_on_json_error():
    from fundexpert.history.store import load_last_run
    import json
    from pathlib import Path
    with patch("pathlib.Path.read_text", side_effect=json.JSONDecodeError("msg", "doc", 0)), \
         patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.glob", return_value=[Path("/tmp/foo")]):
        assert load_last_run("tefas", Path("/tmp")) is None
