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
    selected, header = run_pipeline(
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
    with patch("sys.argv", ["fundexpert"]), \
         patch("fundexpert.cli._prompt", return_value=answers), \
         patch("fundexpert.cli._save_last_run"), \
         patch("fundexpert.cli.run_pipeline",
               return_value=(fake_selected, fake_header)) as run_mock, \
         patch("fundexpert.cli.render_portfolio") as render_mock:
        rc = main()
    assert rc == 0
    assert render_mock.call_count == 2
    universes_called = [call.kwargs["universe"] for call in run_mock.call_args_list]
    assert universes_called == ["tefas", "befas"]
