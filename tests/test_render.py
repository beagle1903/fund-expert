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
        "risk_priority": "high",
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
    news = {"AAA": [{"title": "Yeni fon ihracı", "url": "https://x", "source": "bigpara"}]}
    render_portfolio(_selected(), _header(), news=news)
    captured = capsys.readouterr()
    assert "Haberler" in captured.out
    assert "Yeni fon ihrac" in captured.out


def test_render_omits_news_section_when_no_hits(capsys):
    render_portfolio(_selected(), _header(), news={})
    captured = capsys.readouterr()
    assert "Haberler" not in captured.out
