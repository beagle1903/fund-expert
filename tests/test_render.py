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
    assert "Olumsuz haberle penalize edilen fonlar (portföyde kaldı)" in captured.out
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


def test_render_header_news_line_disabled_omits_line(capsys):
    """news_meta=None → no 'Haber taraması' line at all."""
    render_portfolio(_selected(), _header(), news=None, news_meta=None)
    assert "Haber taraması" not in capsys.readouterr().out


def test_render_header_news_line_key_missing(capsys):
    news_meta = {"enabled": True, "key_present": False, "top_k": 9,
                 "total_hits": 0, "displaced": []}
    render_portfolio(_selected(), _header(), news=None, news_meta=news_meta)
    out = capsys.readouterr().out
    assert "Haber taraması: atlandı (TAVILY_API_KEY tanımsız)" in out


def test_render_header_news_line_zero_hits(capsys):
    news_meta = {"enabled": True, "key_present": True, "top_k": 24,
                 "total_hits": 0, "displaced": []}
    render_portfolio(_selected(), _header(), news=None, news_meta=news_meta)
    out = capsys.readouterr().out
    assert "Haber taraması: aktif" in out
    assert "top-K=24" in out
    assert "0 fonda olumsuz haber" in out
    assert "pick değişti" not in out
    assert "portföy değişmedi" not in out


def test_render_header_news_line_hits_but_picks_unchanged(capsys):
    news_meta = {"enabled": True, "key_present": True, "top_k": 24,
                 "total_hits": 3, "displaced": []}
    render_portfolio(_selected(), _header(), news=None, news_meta=news_meta)
    out = capsys.readouterr().out
    assert "3 fonda olumsuz haber" in out
    assert "portföy değişmedi" in out


def test_render_header_news_line_picks_changed(capsys):
    news_meta = {"enabled": True, "key_present": True, "top_k": 24,
                 "total_hits": 3,
                 "displaced": [{"fon_kodu": "ZZZ", "fon_adi": "Z FON",
                                "score_pre": 0.55, "score_post": 0.35, "hits": []}]}
    render_portfolio(_selected(), _header(), news=None, news_meta=news_meta)
    out = capsys.readouterr().out
    assert "3 fonda olumsuz haber" in out
    assert "1 pick değişti" in out


def test_render_marks_penalized_pick_in_fon_kodu_and_score(capsys):
    news = {"BBB": [{"title": "BBB hakkında soruşturma", "url": "https://x",
                     "source": "x.com"}]}
    news_meta = {"enabled": True, "key_present": True, "top_k": 9,
                 "total_hits": 1, "displaced": []}
    render_portfolio(_selected(), _header(), news=news, news_meta=news_meta)
    out = capsys.readouterr().out
    # Penalized row's fon_kodu cell carries the marker
    assert "BBB 📰" in out
    # Penalized row's score cell shows the delta (penalty value comes from config)
    assert "(−0.20)" in out
    # Clean row's score cell does NOT carry the delta
    assert "0.71 (−0.20)" not in out


def test_render_does_not_mark_rows_when_news_meta_absent(capsys):
    """Without news_meta, row markers are suppressed even if `news` is given."""
    news = {"BBB": [{"title": "x", "url": "https://x", "source": "x.com"}]}
    render_portfolio(_selected(), _header(), news=news, news_meta=None)
    out = capsys.readouterr().out
    # Row markers (fon_kodu cell + score delta) suppressed; footer 📰 heading is unrelated.
    assert "BBB 📰" not in out
    assert "(−0.20)" not in out


def test_render_displaced_footer_renders_when_news_meta_has_displaced(capsys):
    news = {}  # no surviving penalized picks for this case
    news_meta = {
        "enabled": True, "key_present": True, "top_k": 9, "total_hits": 1,
        "displaced": [{
            "fon_kodu": "ZZZ", "fon_adi": "Z PORTFÖY HİSSE FON",
            "score_pre": 0.55, "score_post": 0.35,
            "hits": [{"title": "Z hakkında dava açıldı",
                      "url": "https://news.example/z",
                      "source": "news.example"}],
        }],
    }
    render_portfolio(_selected(), _header(), news=news, news_meta=news_meta)
    out = capsys.readouterr().out
    assert "Habere takılıp portföyden düşen fonlar" in out
    assert "ZZZ" in out
    assert "habersiz skor 0.55" in out
    assert "0.35" in out
    assert "dava açıldı" in out
    assert "https://news.example/z" in out


def test_render_displaced_footer_omitted_when_no_displaced(capsys):
    news_meta = {"enabled": True, "key_present": True, "top_k": 9,
                 "total_hits": 0, "displaced": []}
    render_portfolio(_selected(), _header(), news={}, news_meta=news_meta)
    out = capsys.readouterr().out
    assert "Habere takılıp portföyden düşen fonlar" not in out


def test_render_displaced_footer_separates_multiple_entries_with_blank_line(capsys):
    """Spec: 'Multiple displaced funds → repeat the block, blank line between.'"""
    news_meta = {
        "enabled": True, "key_present": True, "top_k": 9, "total_hits": 2,
        "displaced": [
            {
                "fon_kodu": "AAA1", "fon_adi": "A FON",
                "score_pre": 0.55, "score_post": 0.35,
                "hits": [{"title": "A dava", "url": "https://a", "source": "a.com"}],
            },
            {
                "fon_kodu": "BBB1", "fon_adi": "B FON",
                "score_pre": 0.50, "score_post": 0.30,
                "hits": [{"title": "B ceza", "url": "https://b", "source": "b.com"}],
            },
        ],
    }
    render_portfolio(_selected(), _header(), news={}, news_meta=news_meta)
    out = capsys.readouterr().out
    # Both entries render
    assert "AAA1" in out
    assert "BBB1" in out
    # And there's a blank line between them — i.e. the second entry's header
    # is preceded by a blank line, not directly by the first entry's last url.
    aaa_url_idx = out.index("https://a")
    bbb_header_idx = out.index("BBB1 — habersiz skor")
    between = out[aaa_url_idx:bbb_header_idx]
    # Between the first entry's last line and the second entry's header,
    # there must be at least one fully-blank line (\n\n).
    assert "\n\n" in between, (
        f"Expected blank line between displaced entries, got:\n{between!r}"
    )


def test_render_both_footers_when_survivors_and_displaced(capsys):
    news = {"BBB": [{"title": "BBB ceza", "url": "https://b", "source": "b.com"}]}
    news_meta = {
        "enabled": True, "key_present": True, "top_k": 9, "total_hits": 2,
        "displaced": [{
            "fon_kodu": "ZZZ", "fon_adi": "Z FON",
            "score_pre": 0.55, "score_post": 0.35,
            "hits": [{"title": "Z dava", "url": "https://z", "source": "z.com"}],
        }],
    }
    render_portfolio(_selected(), _header(), news=news, news_meta=news_meta)
    out = capsys.readouterr().out
    assert "Olumsuz haberle penalize edilen fonlar (portföyde kaldı)" in out
    assert "Habere takılıp portföyden düşen fonlar" in out
    # Order: A precedes B
    assert out.index("portföyde kaldı") < out.index("portföyden düşen")
