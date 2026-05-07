"""Tavily search API client for the optional negative-news pass.

Issues per-fund queries like
    "AK PORTFÖY" (soruşturma OR dolandırıcılık OR ...)
restricted to the last N days, with a small disk cache so repeated runs
within the TTL skip the network entirely. All errors are fail-soft —
a network problem returns ``[]`` and logs a warning rather than crashing
the pipeline. This module is the *only* place fundexpert touches the
network at runtime.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_TAVILY_ENDPOINT = "https://api.tavily.com/search"
_USER_AGENT = "fundexpert/0.1 (+local)"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NewsHit:
    """A single negative-news hit returned by Tavily for a fund."""

    title: str
    url: str
    published: datetime | None
    source: str

    def to_render_dict(self) -> dict:
        """Shape expected by render.table.render_portfolio's news footer."""
        out = {"title": self.title, "url": self.url, "source": self.source}
        if self.published is not None:
            out["published"] = self.published
        return out


def build_query(company_prefix: str, keywords: tuple[str, ...]) -> str:
    """Combine the prefix with keyword OR-list using Tavily's query syntax."""
    if not company_prefix or not keywords:
        return ""
    or_clause = " OR ".join(keywords)
    return f'"{company_prefix}" ({or_clause})'


def _domain_of(url: str) -> str:
    """Extract a short source label from a URL (e.g. www.dunya.com → dunya.com)."""
    try:
        host = urllib.parse.urlparse(url).hostname or ""
    except ValueError:
        return ""
    return host.removeprefix("www.")


def _parse_published(raw: str | None) -> datetime | None:
    """Tavily emits ISO-ish dates; accept either full ISO or YYYY-MM-DD."""
    if not raw:
        return None
    try:
        # fromisoformat handles both "2026-01-15" and "2026-01-15T10:30:00".
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _cache_key(query: str, allowed_domains: tuple[str, ...],
               excluded_domain_substrings: tuple[str, ...]) -> str:
    """Cache key includes filter config so changing it invalidates old entries."""
    parts = [query, "|".join(sorted(allowed_domains)),
             "|".join(sorted(excluded_domain_substrings))]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _hostname(url: str) -> str:
    try:
        return (urllib.parse.urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def _is_excluded(url: str, substrings: tuple[str, ...]) -> bool:
    if not substrings:
        return False
    host = _hostname(url)
    return any(s.lower() in host for s in substrings)


def _read_cache(cache_dir: Path, key: str, ttl_seconds: int) -> list[NewsHit] | None:
    """Return cached hits if the cache entry exists and is fresh; else None."""
    path = cache_dir / f"{key}.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    queried_at = payload.get("queried_at", 0)
    if time.time() - queried_at > ttl_seconds:
        return None
    return [
        NewsHit(
            title=item["title"],
            url=item["url"],
            published=_parse_published(item.get("published")),
            source=item["source"],
        )
        for item in payload.get("hits", [])
    ]


def _write_cache(cache_dir: Path, key: str, hits: list[NewsHit]) -> None:
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        path = cache_dir / f"{key}.json"
        path.write_text(
            json.dumps({
                "queried_at": time.time(),
                "hits": [
                    {
                        "title": h.title,
                        "url": h.url,
                        "published": h.published.isoformat() if h.published else None,
                        "source": h.source,
                    }
                    for h in hits
                ],
            }, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as e:
        logger.info("News cache write failed: %s", e)


def _post_tavily(query: str, api_key: str, max_age_days: int,
                 max_results: int, timeout_seconds: int,
                 allowed_domains: tuple[str, ...] = ()) -> list[NewsHit]:
    """Single Tavily POST. Raises urllib.error.URLError or json.JSONDecodeError on failure."""
    payload: dict = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "days": max_age_days,
    }
    if allowed_domains:
        payload["include_domains"] = list(allowed_domains)
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        _TAVILY_ENDPOINT,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": _USER_AGENT,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return [
        NewsHit(
            title=r.get("title", "").strip(),
            url=r.get("url", ""),
            published=_parse_published(r.get("published_date")),
            source=_domain_of(r.get("url", "")),
        )
        for r in data.get("results", [])
        if r.get("title") and r.get("url")
    ]


def query_negative_news(
    company_prefix: str,
    keywords: tuple[str, ...],
    api_key: str,
    cache_dir: Path,
    ttl_seconds: int = 3600,
    max_age_days: int = 30,
    max_results: int = 3,
    timeout_seconds: int = 10,
    allowed_domains: tuple[str, ...] = (),
    excluded_domain_substrings: tuple[str, ...] = (),
) -> list[NewsHit]:
    """Search Tavily for the company prefix + keyword OR-list.

    Returns up to `max_results` hits from the last `max_age_days` days.
    Empty prefix or empty keywords → ``[]``. Any error (HTTP, JSON,
    timeout) → ``[]`` with a logged warning. Successful responses are
    cached on disk under ``cache_dir`` for ``ttl_seconds``.

    `allowed_domains` is forwarded to Tavily as ``include_domains`` —
    server-side restriction to trusted news outlets. Empty tuple → no
    restriction (broad search). `excluded_domain_substrings` is applied
    client-side: any hit whose hostname contains one of the substrings
    (case-insensitive) is dropped. Used as defense-in-depth against
    issuer-owned domains (e.g. ``*portfoy*``) slipping through.
    """
    query = build_query(company_prefix, keywords)
    if not query:
        return []

    key = _cache_key(query, allowed_domains, excluded_domain_substrings)
    cached = _read_cache(cache_dir, key, ttl_seconds)
    if cached is not None:
        return cached

    try:
        hits = _post_tavily(
            query, api_key,
            max_age_days=max_age_days,
            max_results=max_results,
            timeout_seconds=timeout_seconds,
            allowed_domains=allowed_domains,
        )
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            json.JSONDecodeError) as e:
        print(f"Haber sorgusu başarısız ({company_prefix}): {e}", file=sys.stderr)
        return []

    hits = [h for h in hits if not _is_excluded(h.url, excluded_domain_substrings)]

    _write_cache(cache_dir, key, hits)
    return hits
