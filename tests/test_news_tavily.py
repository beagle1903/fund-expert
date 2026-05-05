import io
import json
import time
import urllib.error
from datetime import datetime
from unittest.mock import patch

import pytest

from fundexpert.news.tavily import (
    NewsHit,
    build_query,
    query_negative_news,
)


# ---- build_query --------------------------------------------------------

def test_build_query_combines_prefix_and_keywords():
    q = build_query("AK PORTFÖY", ("soruşturma", "iflas", "ceza"))
    assert q == '"AK PORTFÖY" (soruşturma OR iflas OR ceza)'


def test_build_query_empty_inputs_return_empty_string():
    assert build_query("", ("foo",)) == ""
    assert build_query("AK PORTFÖY", ()) == ""


# ---- query_negative_news (network mocked) -------------------------------

@pytest.fixture
def cache_dir(tmp_path):
    return tmp_path / "news_cache"


def _fake_response(payload: dict):
    """Return an object usable as the context-manager result of urlopen()."""
    body = json.dumps(payload).encode("utf-8")

    class _Resp:
        def __enter__(self_inner):
            return self_inner
        def __exit__(self_inner, *_a):
            return False
        def read(self_inner):
            return body
    return _Resp()


def test_query_returns_parsed_hits_on_success(cache_dir):
    payload = {"results": [
        {
            "title": "AK PORTFÖY hakkında SPK soruşturması",
            "url": "https://www.dunya.com/finans/123",
            "published_date": "2026-04-30",
            "content": "...",
        },
        {
            "title": "İkinci başlık",
            "url": "https://bigpara.hurriyet.com.tr/x",
            "published_date": "2026-04-29T08:15:00",
            "content": "...",
        },
    ]}
    with patch("urllib.request.urlopen", return_value=_fake_response(payload)):
        hits = query_negative_news(
            "AK PORTFÖY", ("soruşturma",), api_key="tvly-test",
            cache_dir=cache_dir,
        )
    assert [h.title for h in hits] == [
        "AK PORTFÖY hakkında SPK soruşturması", "İkinci başlık",
    ]
    assert hits[0].source == "dunya.com"
    assert hits[0].published == datetime(2026, 4, 30)
    assert hits[1].published == datetime(2026, 4, 29, 8, 15)


def test_query_skips_results_missing_title_or_url(cache_dir):
    """Defensive: malformed result entries are dropped, not crash the parse."""
    payload = {"results": [
        {"title": "", "url": "https://x", "published_date": "2026-01-01"},
        {"title": "Real one", "url": "https://y/p", "published_date": "2026-01-02"},
        {"title": "No url", "url": "", "published_date": "2026-01-03"},
    ]}
    with patch("urllib.request.urlopen", return_value=_fake_response(payload)):
        hits = query_negative_news(
            "FOO PORTFÖY", ("ceza",), api_key="k", cache_dir=cache_dir,
        )
    assert len(hits) == 1
    assert hits[0].title == "Real one"


def test_query_returns_empty_on_http_error(cache_dir, capsys):
    err = urllib.error.HTTPError(
        url="https://api.tavily.com/search", code=503,
        msg="Service Unavailable", hdrs=None, fp=io.BytesIO(b"down"),
    )
    with patch("urllib.request.urlopen", side_effect=err):
        hits = query_negative_news(
            "AK PORTFÖY", ("soruşturma",), api_key="k", cache_dir=cache_dir,
        )
    assert hits == []
    err_out = capsys.readouterr().err
    assert "Haber sorgusu başarısız" in err_out


def test_query_returns_empty_on_url_error(cache_dir, capsys):
    with patch("urllib.request.urlopen",
               side_effect=urllib.error.URLError("dns failed")):
        hits = query_negative_news(
            "AK PORTFÖY", ("ceza",), api_key="k", cache_dir=cache_dir,
        )
    assert hits == []
    assert "Haber sorgusu başarısız" in capsys.readouterr().err


def test_query_returns_empty_on_malformed_json(cache_dir, capsys):
    class _BadResp:
        def __enter__(self_inner): return self_inner
        def __exit__(self_inner, *_a): return False
        def read(self_inner): return b"not json {{"
    with patch("urllib.request.urlopen", return_value=_BadResp()):
        hits = query_negative_news(
            "X PORTFÖY", ("dava",), api_key="k", cache_dir=cache_dir,
        )
    assert hits == []
    assert "başarısız" in capsys.readouterr().err


def test_query_skips_when_prefix_or_keywords_empty(cache_dir):
    """No network call when query would be empty."""
    with patch("urllib.request.urlopen", side_effect=AssertionError("called!")):
        assert query_negative_news("", ("ceza",), "k", cache_dir) == []
        assert query_negative_news("AK PORTFÖY", (), "k", cache_dir) == []


def test_query_uses_cache_within_ttl(cache_dir):
    """Second call within TTL must not hit the network."""
    payload = {"results": [
        {"title": "T", "url": "https://x.com/1", "published_date": "2026-01-01"},
    ]}
    with patch("urllib.request.urlopen", return_value=_fake_response(payload)) as mock:
        first = query_negative_news(
            "AK PORTFÖY", ("ceza",), "k", cache_dir, ttl_seconds=3600,
        )
        second = query_negative_news(
            "AK PORTFÖY", ("ceza",), "k", cache_dir, ttl_seconds=3600,
        )
    assert mock.call_count == 1
    assert [h.title for h in first] == [h.title for h in second]


def test_query_refetches_when_cache_expired(cache_dir):
    """Cache entries older than TTL trigger a fresh fetch."""
    payload = {"results": [
        {"title": "T", "url": "https://x.com/1", "published_date": "2026-01-01"},
    ]}
    with patch("urllib.request.urlopen", return_value=_fake_response(payload)) as mock:
        query_negative_news("AK PORTFÖY", ("ceza",), "k", cache_dir, ttl_seconds=1)
        time.sleep(1.1)
        query_negative_news("AK PORTFÖY", ("ceza",), "k", cache_dir, ttl_seconds=1)
    assert mock.call_count == 2


def test_news_hit_to_render_dict_round_trip():
    h = NewsHit(title="t", url="https://x.com/p", published=datetime(2026, 1, 1),
                source="x.com")
    d = h.to_render_dict()
    assert d["title"] == "t"
    assert d["url"] == "https://x.com/p"
    assert d["source"] == "x.com"
    assert d["published"] == datetime(2026, 1, 1)


def test_news_hit_to_render_dict_omits_published_when_none():
    h = NewsHit(title="t", url="https://x.com/p", published=None, source="x.com")
    d = h.to_render_dict()
    assert "published" not in d
