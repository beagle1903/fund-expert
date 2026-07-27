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


def _fake_response(data: dict | list):
    class _Resp:
        def read(self, size=-1):
            return json.dumps(data).encode("utf-8")
        def __enter__(self): return self
        def __exit__(self, *args): pass
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
            "content": "... soruşturma ...",
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
        {"title": "Real one ceza", "url": "https://y/p", "published_date": "2026-01-02"},
        {"title": "No url", "url": "", "published_date": "2026-01-03"},
    ]}
    with patch("urllib.request.urlopen", return_value=_fake_response(payload)):
        hits = query_negative_news(
            "FOO PORTFÖY", ("ceza",), api_key="k", cache_dir=cache_dir,
        )
    assert len(hits) == 1
    assert hits[0].title == "Real one ceza"


def test_query_returns_empty_on_http_error(cache_dir, caplog):
    err = urllib.error.HTTPError(
        url="https://api.tavily.com/search", code=503,
        msg="Service Unavailable", hdrs=None, fp=io.BytesIO(b"down"),
    )
    with patch("urllib.request.urlopen", side_effect=err):
        hits = query_negative_news(
            "AK PORTFÖY", ("soruşturma",), api_key="k", cache_dir=cache_dir,
        )
    assert hits == []
    assert "Haber sorgusu başarısız" in caplog.text


def test_query_returns_empty_on_url_error(cache_dir, caplog):
    with patch("urllib.request.urlopen",
               side_effect=urllib.error.URLError("dns failed")):
        hits = query_negative_news(
            "AK PORTFÖY", ("ceza",), api_key="k", cache_dir=cache_dir,
        )
    assert hits == []
    assert "Haber sorgusu başarısız" in caplog.text


def test_query_returns_empty_on_timeout(cache_dir, caplog):
    with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
        hits = query_negative_news(
            "AK PORTFÖY", ("ceza",), api_key="k", cache_dir=cache_dir,
        )

    assert hits == []
    assert "Haber sorgusu başarısız" in caplog.text


def test_query_returns_empty_on_malformed_json(cache_dir, caplog):
    class _BadResp:
        def __enter__(self_inner): return self_inner
        def __exit__(self_inner, *_a): return False
        def read(self_inner, size=-1): return b"not json {{"
    with patch("urllib.request.urlopen", return_value=_BadResp()):
        hits = query_negative_news(
            "X PORTFÖY", ("dava",), api_key="k", cache_dir=cache_dir,
        )
    assert hits == []
    assert "başarısız" in caplog.text


def test_query_warns_on_exactly_5mb_response(cache_dir, caplog):
    class _BigResp:
        def read(self, size=-1):
            return b" " * (5 * 1024 * 1024)
        def __enter__(self): return self
        def __exit__(self, *args): pass
    with patch("urllib.request.urlopen", return_value=_BigResp()):
        with patch("json.loads", return_value={"results": []}):
            query_negative_news("AK PORTFÖY", ("ceza",), api_key="k", cache_dir=cache_dir)
    assert "exactly 5MB" in caplog.text


def test_query_raises_valueerror_on_non_https(cache_dir):
    with patch("urllib.request.Request") as mock_req:
        mock_req.return_value.full_url = "http://api.tavily.com/search"
        with pytest.raises(ValueError, match="Sadece HTTPS desteklenir"):
            query_negative_news("FOO", ("ceza",), api_key="k", cache_dir=cache_dir)


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

def test_cache_read_ignores_oserror_and_jsondecodeerror(cache_dir):
    from unittest.mock import patch
    # create a corrupt cache file
    cache_dir.mkdir(parents=True, exist_ok=True)
    with patch("pathlib.Path.read_text", side_effect=OSError("locked")):
        # If read_text throws OSError, it should gracefully fall back to network
        payload = {"results": []}
        with patch("urllib.request.urlopen", return_value=_fake_response(payload)) as mock:
            query_negative_news("AK PORTFÖY", ("ceza",), "k", cache_dir)
            assert mock.call_count == 1
    
    with patch("json.loads", side_effect=json.JSONDecodeError("bad", "", 0)):
        payload = {"results": []}
        with patch("urllib.request.urlopen", return_value=_fake_response(payload)) as mock:
            query_negative_news("AK PORTFÖY", ("ceza",), "k", cache_dir)
            assert mock.call_count == 1


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


# ---- domain allowlist + issuer exclusion --------------------------------

def _capturing_urlopen(payload: dict, captured: dict):
    """urlopen side_effect that records the POSTed JSON body for assertions."""
    def fake(req, **_kw):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _fake_response(payload)
    return fake


def test_query_passes_allowed_domains_to_tavily(cache_dir):
    """Non-empty allowlist must appear as include_domains in the POST body."""
    captured: dict = {}
    payload = {"results": []}
    with patch("urllib.request.urlopen",
               side_effect=_capturing_urlopen(payload, captured)):
        query_negative_news(
            "AK PORTFÖY", ("ceza",), api_key="k", cache_dir=cache_dir,
            allowed_domains=("dunya.com", "kap.org.tr"),
        )
    assert captured["body"]["include_domains"] == ["dunya.com", "kap.org.tr"]


def test_query_omits_include_domains_when_allowlist_empty(cache_dir):
    """Empty allowlist must not add include_domains (Tavily searches all)."""
    captured: dict = {}
    payload = {"results": []}
    with patch("urllib.request.urlopen",
               side_effect=_capturing_urlopen(payload, captured)):
        query_negative_news(
            "AK PORTFÖY", ("ceza",), api_key="k", cache_dir=cache_dir,
            allowed_domains=(),
        )
    assert "include_domains" not in captured["body"]


def test_query_filters_excluded_domain_substrings(cache_dir):
    """Hits whose hostname contains an excluded substring are dropped client-side."""
    payload = {"results": [
        {"title": "Real news ceza", "url": "https://www.dunya.com/x",
         "published_date": "2026-04-30"},
        {"title": "Issuer self-promo ceza", "url": "https://www.isportfoy.com.tr/x",
         "published_date": "2026-04-30"},
        {"title": "Other issuer ceza", "url": "https://akportfoy.com.tr/y",
         "published_date": "2026-04-30"},
    ]}
    with patch("urllib.request.urlopen", return_value=_fake_response(payload)):
        hits = query_negative_news(
            "AK PORTFÖY", ("ceza",), api_key="k", cache_dir=cache_dir,
            excluded_domain_substrings=("portfoy",),
        )
    assert [h.source for h in hits] == ["dunya.com"]


def test_excluded_substrings_match_case_insensitive(cache_dir):
    """Substring match is case-insensitive so PORTFOY/Portfoy/portföy all hit."""
    payload = {"results": [
        {"title": "A ceza", "url": "https://AKPORTFOY.COM.TR/x",
         "published_date": "2026-04-30"},
        {"title": "B ceza", "url": "https://www.dunya.com/y",
         "published_date": "2026-04-30"},
    ]}
    with patch("urllib.request.urlopen", return_value=_fake_response(payload)):
        hits = query_negative_news(
            "X", ("ceza",), api_key="k", cache_dir=cache_dir,
            excluded_domain_substrings=("portfoy",),
        )
    assert [h.source for h in hits] == ["dunya.com"]


def test_cache_key_differs_per_allowlist(cache_dir):
    """Same query + different allowlists must not share a cache entry."""
    payload = {"results": [
        {"title": "T", "url": "https://www.dunya.com/1",
         "published_date": "2026-01-01"},
    ]}
    with patch("urllib.request.urlopen",
               return_value=_fake_response(payload)) as mock:
        query_negative_news("AK PORTFÖY", ("ceza",), "k", cache_dir,
                            allowed_domains=("a.com",))
        query_negative_news("AK PORTFÖY", ("ceza",), "k", cache_dir,
                            allowed_domains=("b.com",))
    assert mock.call_count == 2


def test_query_filters_out_hits_missing_keywords(cache_dir):
    """Client-side filter drops hits that don't actually contain any of the keywords."""
    payload = {"results": [
        {"title": "Real ceza", "url": "https://x", "published_date": "2026-01-01", "content": "ceza yedi"},
        {"title": "False positive", "url": "https://y", "published_date": "2026-01-01", "content": "hello world"},
        {"title": "Another match", "url": "https://z", "published_date": "2026-01-01", "content": "SORUŞTURMA"},
    ]}
    from unittest.mock import patch
    with patch("urllib.request.urlopen", return_value=_fake_response(payload)):
        hits = query_negative_news(
            "FOO", ("ceza", "soruşturma"), api_key="k", cache_dir=cache_dir,
        )
    assert len(hits) == 2
    assert hits[0].title == "Real ceza"
    assert hits[1].title == "Another match"

def test_keyword_validation_is_turkish_case_insensitive(cache_dir):
    """Client-side filter handles Turkish I/ı correctly when checking keywords."""
    payload = {"results": [
        {"title": "Title with dolandırıcılık", "url": "https://x", "published_date": "2026-01-01", "content": "dolandırıcı"},
        {"title": "DOLANDIRICILIK", "url": "https://y", "published_date": "2026-01-01", "content": "büyük"},
        {"title": "İFLAS", "url": "https://z", "published_date": "2026-01-01", "content": "iflas etti"},
    ]}
    from unittest.mock import patch
    with patch("urllib.request.urlopen", return_value=_fake_response(payload)):
        hits = query_negative_news(
            "FOO", ("dolandırıcılık", "iflas"), api_key="k", cache_dir=cache_dir,
        )
    assert len(hits) == 3
