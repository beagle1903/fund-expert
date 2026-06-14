from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

from fundexpert.news.penalty import apply_negative_news_penalty
from fundexpert.news.tavily import NewsHit
from fundexpert.config import NewsConfig


@pytest.fixture
def scored():
    """5 candidates ranked by quant score, descending."""
    return pd.DataFrame({
        "fon_kodu": ["A", "B", "C", "D", "E"],
        "fon_adi":  [
            "AK PORTFÖY HİSSE FON",
            "BNP PORTFÖY DEĞİŞKEN FON",
            "CORE PORTFÖY KARMA FON",
            "DENEME PORTFÖY FON SEPETİ FON",
            "EFG PORTFÖY HİSSE FON",
        ],
        "score":    [0.90, 0.80, 0.70, 0.60, 0.50],
    })


@pytest.fixture
def cache_dir(tmp_path):
    return tmp_path / "news_cache"


def _make_hit(title: str = "BAD") -> list[NewsHit]:
    return [NewsHit(title=title, url="https://x.com/p",
                    published=datetime(2026, 4, 30), source="x.com")]


def test_no_api_key_skips_news_pass_with_warning(scored, cache_dir, capsys):
    out, hits = apply_negative_news_penalty(
        scored, top_k=3, api_key=None, news_config=NewsConfig(negative_news_keywords=("ceza",), negative_news_penalty=0.20, cache_dir=cache_dir),
    )
    pd.testing.assert_frame_equal(out, scored)
    assert hits == {}
    err = capsys.readouterr().err
    assert "TAVILY_API_KEY tanımlı değil" in err


def test_empty_api_key_string_also_skips(scored, cache_dir, capsys):
    out, hits = apply_negative_news_penalty(
        scored, top_k=3, api_key="", news_config=NewsConfig(negative_news_keywords=("ceza",), negative_news_penalty=0.20, cache_dir=cache_dir),
    )
    assert hits == {}
    pd.testing.assert_frame_equal(out, scored)
    assert "TAVILY_API_KEY" in capsys.readouterr().err


def test_top_k_zero_returns_unchanged(scored, cache_dir):
    out, hits = apply_negative_news_penalty(
        scored, top_k=0, api_key="k", news_config=NewsConfig(negative_news_keywords=("ceza",), negative_news_penalty=0.20, cache_dir=cache_dir),
    )
    pd.testing.assert_frame_equal(out, scored)
    assert hits == {}


def test_empty_dataframe_returns_unchanged(cache_dir):
    empty = pd.DataFrame(columns=["fon_kodu", "fon_adi", "score"])
    out, hits = apply_negative_news_penalty(
        empty, top_k=5, api_key="k", news_config=NewsConfig(negative_news_keywords=("ceza",), negative_news_penalty=0.20, cache_dir=cache_dir),
    )
    assert len(out) == 0
    assert hits == {}


def test_only_top_k_funds_are_queried(scored, cache_dir):
    """Funds outside top_k must NOT trigger a Tavily call."""
    with patch("fundexpert.news.penalty.query_negative_news",
               return_value=[]) as mock:
        apply_negative_news_penalty(
        scored, top_k=2, api_key="k", news_config=NewsConfig(negative_news_keywords=("ceza",), negative_news_penalty=0.20, cache_dir=cache_dir),
        )
    assert mock.call_count == 2
    # The two highest-scoring rows are A (0.90) and B (0.80).
    queried_prefixes = [c.kwargs["company_prefix"] for c in mock.call_args_list]
    assert sorted(queried_prefixes) == ["AK PORTFÖY", "BNP PORTFÖY"]


def test_matched_fund_loses_penalty_amount(scored, cache_dir):
    """Tavily returning a hit for one fund deducts exactly `penalty` from its score."""
    def fake_query(company_prefix, **_kw):
        return _make_hit() if company_prefix == "BNP PORTFÖY" else []
    with patch("fundexpert.news.penalty.query_negative_news", side_effect=fake_query):
        out, hits = apply_negative_news_penalty(
        scored, top_k=5, api_key="k", news_config=NewsConfig(negative_news_keywords=("ceza",), negative_news_penalty=0.20, cache_dir=cache_dir),
        )
    # B (BNP PORTFÖY) had 0.80 → 0.60 after −0.20.
    assert out.loc[out["fon_kodu"] == "B", "score"].iloc[0] == pytest.approx(0.60)
    # All other rows unchanged.
    for code, expected in [("A", 0.90), ("C", 0.70), ("D", 0.60), ("E", 0.50)]:
        assert out.loc[out["fon_kodu"] == code, "score"].iloc[0] == pytest.approx(expected)
    assert list(hits.keys()) == ["B"]
    assert hits["B"][0].title == "BAD"


def test_no_matches_returns_empty_hits_dict(scored, cache_dir):
    """When no fund has news hits, no penalties applied and dict is empty."""
    with patch("fundexpert.news.penalty.query_negative_news", return_value=[]):
        out, hits = apply_negative_news_penalty(
        scored, top_k=5, api_key="k", news_config=NewsConfig(negative_news_keywords=("ceza",), negative_news_penalty=0.20, cache_dir=cache_dir),
        )
    pd.testing.assert_frame_equal(out, scored)
    assert hits == {}


def test_binary_penalty_one_or_many_hits_same_amount(scored, cache_dir):
    """1 hit and 5 hits both produce exactly one −0.20 deduction."""
    many_hits = [
        NewsHit(title=f"hit {i}", url=f"https://x/{i}",
                published=datetime(2026, 4, 30), source="x.com")
        for i in range(5)
    ]
    with patch("fundexpert.news.penalty.query_negative_news", return_value=many_hits):
        out, hits = apply_negative_news_penalty(
        scored, top_k=1, api_key="k", news_config=NewsConfig(negative_news_keywords=("ceza",), negative_news_penalty=0.20, cache_dir=cache_dir),
        )
    assert out.loc[out["fon_kodu"] == "A", "score"].iloc[0] == pytest.approx(0.70)
    assert len(hits["A"]) == 5  # Hits dict still carries all of them for display.


def test_allowed_domains_and_exclusions_forwarded_to_tavily(scored, cache_dir):
    """Allowlist + issuer-exclusion config must reach query_negative_news."""
    with patch("fundexpert.news.penalty.query_negative_news",
               return_value=[]) as mock:
        apply_negative_news_penalty(
        scored, top_k=1, api_key="k", news_config=NewsConfig(negative_news_keywords=("ceza",), negative_news_penalty=0.20, cache_dir=cache_dir, domain_allowlist=("dunya.com", "kap.org.tr"), excluded_domain_substrings=("portfoy",)),
        )
    kwargs = mock.call_args.kwargs
    assert kwargs["allowed_domains"] == ("dunya.com", "kap.org.tr")
    assert kwargs["excluded_domain_substrings"] == ("portfoy",)


def test_fund_with_empty_company_prefix_is_skipped(cache_dir):
    """A fund whose name is empty-ish shouldn't generate a Tavily call."""
    df = pd.DataFrame({
        "fon_kodu": ["A", "B"],
        "fon_adi":  ["", "REAL PORTFÖY FON"],
        "score":    [0.99, 0.50],
    })
    with patch("fundexpert.news.penalty.query_negative_news",
               return_value=[]) as mock:
        apply_negative_news_penalty(
        df, top_k=5, api_key="k", news_config=NewsConfig(negative_news_keywords=("ceza",), negative_news_penalty=0.20, cache_dir=cache_dir),
        )
    # Only the second fund had a real prefix; only it gets queried.
    assert mock.call_count == 1
    assert mock.call_args.kwargs["company_prefix"] == "REAL PORTFÖY"

def test_network_exception_is_caught_gracefully(scored, cache_dir, capsys):
    with patch("fundexpert.news.penalty.query_negative_news", side_effect=Exception("Network down")):
        out, hits = apply_negative_news_penalty(
        scored, top_k=5, api_key="k", news_config=NewsConfig(negative_news_keywords=("ceza",), negative_news_penalty=0.20, cache_dir=cache_dir),
        )
    pd.testing.assert_frame_equal(out, scored)
    assert hits == {}
    err = capsys.readouterr().err
    assert "Network down" in err

def test_news_penalty_monotonicity(scored, cache_dir):
    """If $Score(F_1) - Penalty < Score(F_2)$, hitting F_1 inverts rank ordering."""
    def fake_query(company_prefix, **_kw):
        return _make_hit() if company_prefix == "AK PORTFÖY" else []
    with patch("fundexpert.news.penalty.query_negative_news", side_effect=fake_query):
        out, _ = apply_negative_news_penalty(
            scored, top_k=5, api_key="k", 
            news_config=NewsConfig(negative_news_keywords=("ceza",), negative_news_penalty=0.20, cache_dir=cache_dir)
        )
    assert out.loc[out["fon_kodu"] == "A", "score"].iloc[0] == pytest.approx(0.70)
    assert out.loc[out["fon_kodu"] == "B", "score"].iloc[0] == pytest.approx(0.80)
