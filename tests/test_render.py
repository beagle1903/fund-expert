from datetime import datetime

import pandas as pd

from fundexpert.render.table import render_portfolio


def _selected():
    return pd.DataFrame({
        "fon_kodu": ["AAA", "BBB"],
        "fon_adi":  ["ATA PORTFÖY ÇOKLU VARLIK FON", "BETA PORTFÖY HİSSE FON"],
        "umbrella_type": ["Değişken", "Hisse Senedi"],
        "risk":          [4, 6],
        "display_weight_pct": [60.0, 40.0],
        "score":         [0.71, 0.55],
    })


def _header():
    return {
        "timestamp": datetime(2026, 5, 2, 11, 42),
        "universe":  "tefas+befas",
        "candidate_total": 1308,
        "candidate_kept":  1107,
        "horizon": "long",
        "risk_level": "high",
        "volume_priority": "medium",
        "fee_priority": "high",
        "n": 5,
    }


def test_render_includes_fund_codes(capsys):
    render_portfolio(_selected(), _header(), news=None)
    captured = capsys.readouterr()
    assert "AAA" in captured.out
    assert "BBB" in captured.out


def test_render_includes_total_row(capsys):
    render_portfolio(_selected(), _header(), news=None)
    captured = capsys.readouterr()
    assert "Toplam" in captured.out
    assert "100" in captured.out


def test_render_includes_news_footer_when_provided(capsys):
    news = {"AAA": [{"title": "AAA hakkında soruşturma", "url": "https://x",
                     "source": "dunya.com"}]}
    render_portfolio(_selected(), _header(), news=news)
    captured = capsys.readouterr()
    assert "Olumsuz haber" in captured.out
    assert "soruşturma" in captured.out
    assert "AAA" in captured.out


def test_render_omits_news_section_when_no_hits(capsys):
    render_portfolio(_selected(), _header(), news={})
    captured = capsys.readouterr()
    assert "Olumsuz haber" not in captured.out


def test_render_accepts_news_meta_kwarg_without_error(capsys):
    news_meta = {"enabled": False}
    render_portfolio(_selected(), _header(), news=None, news_meta=news_meta)
    captured = capsys.readouterr()
    assert "AAA" in captured.out  # baseline output still renders
