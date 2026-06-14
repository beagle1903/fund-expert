"""Apply the negative-news penalty to the top-K candidates by quant score.

Sits between ``score_candidates`` and ``pick_top``. For each of the top-K
funds (by quant score), issues a Tavily query for negative news; if any
result returns, subtracts a fixed penalty from that fund's score so it's
less likely to be picked.

This module is the *only* news entry point the rest of the pipeline knows
about. It encapsulates:
- the "skip everything if no API key" branch
- the top-K bound (we never query the full universe)
- the Tavily call (delegated to ``tavily.query_negative_news``)
- the score adjustment
- the per-fund hit dict for the renderer
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from fundexpert.news.match import extract_company_prefix
from fundexpert.news.tavily import NewsHit, query_negative_news
from fundexpert.config import NewsConfig


def apply_negative_news_penalty(
    scored: pd.DataFrame,
    top_k: int,
    api_key: str | None,
    news_config: NewsConfig,
) -> tuple[pd.DataFrame, dict[str, list[NewsHit]]]:
    """Penalise the top-K rows of ``scored`` for negative-news hits.

    Returns ``(adjusted_df, hits_by_fon_kodu)``. ``adjusted_df`` has the
    same shape as ``scored`` with the score column adjusted in place for
    matched funds. ``hits_by_fon_kodu`` only contains entries for funds
    that returned at least one Tavily hit.

    If ``api_key`` is None or empty, the function logs a warning to stderr
    and returns ``(scored, {})`` unchanged. This is the offline / missing-
    key path and is the most common failure mode.

    Funds outside the top-K are never queried. Their scores and the order
    of the returned DataFrame are otherwise untouched.
    """
    if not api_key:
        print(
            "Haber taraması atlandı: TAVILY_API_KEY tanımlı değil.",
            file=sys.stderr,
        )
        return scored, {}

    if top_k <= 0 or scored.empty:
        return scored, {}

    # Identify the top-K candidate indices by score.
    top_indices = scored["score"].nlargest(top_k).index

    import concurrent.futures

    hits_by_code: dict[str, list[NewsHit]] = {}
    adjusted = scored.copy()

    fon_adi_col = adjusted["fon_adi"]
    fon_kodu_col = adjusted["fon_kodu"]
    score_col = adjusted["score"]

    prefix_to_indices = {}
    for idx in top_indices:
        fon_adi = fon_adi_col.at[idx]
        prefix = extract_company_prefix(fon_adi)
        if prefix:
            prefix_to_indices.setdefault(prefix, []).append((
                idx, fon_kodu_col.at[idx], score_col.at[idx]
            ))

    def _query_for_prefix(prefix):
        hits = query_negative_news(
            company_prefix=prefix,
            keywords=news_config.negative_news_keywords,
            api_key=api_key,
            cache_dir=news_config.cache_dir,
            ttl_seconds=news_config.cache_ttl_seconds,
            max_age_days=news_config.max_age_days,
            max_results=news_config.max_results_per_fund,
            timeout_seconds=news_config.query_timeout_seconds,
            allowed_domains=news_config.domain_allowlist,
            excluded_domain_substrings=news_config.excluded_domain_substrings,
        )
        return prefix, hits

    updates = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=news_config.max_workers) as executor:
        futures = [executor.submit(_query_for_prefix, p) for p in prefix_to_indices]
        for future in concurrent.futures.as_completed(futures):
            try:
                prefix, hits = future.result()
                if hits:
                    for idx, code, score in prefix_to_indices[prefix]:
                        updates.append((idx, float(score) - news_config.negative_news_penalty, str(code), hits))
            except Exception as e:
                print(f"Uyarı: Haber sorgusu sırasında hata oluştu: {e}", file=sys.stderr)

    for idx, new_score, code, hits in updates:
        adjusted.at[idx, "score"] = new_score
        hits_by_code[code] = hits

    return adjusted, hits_by_code
