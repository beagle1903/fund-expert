from datetime import datetime
from typing import Any

import pandas as pd

from fundexpert.config import (
    DEFAULT_MAX_PER_SECTOR,
    NEGATIVE_NEWS_KEYWORDS,
    NEGATIVE_NEWS_PENALTY,
    NEWS_CACHE_DIR,
    NEWS_CACHE_TTL_SECONDS,
    NEWS_DOMAIN_ALLOWLIST,
    NEWS_EXCLUDED_DOMAIN_SUBSTRINGS,
    NEWS_MAX_AGE_DAYS,
    NEWS_MAX_RESULTS_PER_FUND,
    NEWS_QUERY_TIMEOUT_SECONDS,
    NEWS_QUERY_TOP_K_MULTIPLIER,
)
from fundexpert.news.penalty import apply_negative_news_penalty
from fundexpert.scoring.horizon import apply_horizon
from fundexpert.scoring.score import score_candidates
from fundexpert.select.pick import pick_top
from fundexpert.select.sector import sector_from_name
from fundexpert.select.strategy import bucket_from_name
from fundexpert.select.weights import compute_weights


def run_pipeline(
    candidates: pd.DataFrame,
    universe: str,
    risk_level: str,
    horizon: str,
    volume_priority: str,
    fee_priority: str,
    n: int,
    max_per_type: int,
    now: datetime,
    max_per_sector: int = DEFAULT_MAX_PER_SECTOR,
    news_enabled: bool = False,
    news_api_key: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, list], dict[str, Any]]:
    """Run the full data → score → select pipeline for a single universe.

    Returns (selected_df, header_dict, hits_by_pick, news_meta). When
    `news_enabled` is False, `hits_by_pick` is always {} and `news_meta`
    is `{"enabled": False}`. When True, the news pass runs against the
    top-K candidates (K = NEWS_QUERY_TOP_K_MULTIPLIER * n) and returns
    matched articles for any of the *finally-picked* funds; `news_meta`
    carries metadata about the pass (key_present, top_k, total_hits,
    displaced).
    """
    if universe not in ("tefas", "befas"):
        raise ValueError(
            f"run_pipeline accepts 'tefas' or 'befas', got {universe!r}. "
            "Use main()'s 'both' option for dual-portfolio output."
        )
    total = len(candidates)

    # Drop funds with NaN primary fee (per missing-value policy)
    candidates = candidates[candidates["applied_management_fee_pct"].notna()]

    # Drop funds without at least 3 months of performance history
    candidates = candidates[candidates["ret_3m"].notna()]

    horizoned = apply_horizon(candidates, horizon)
    excluded_horizon = horizoned.attrs.get("excluded_count", 0)

    scored = score_candidates(
        horizoned,
        volume_priority=volume_priority,
        fee_priority=fee_priority,
        risk_level=risk_level,
    )
    scored = scored.assign(
        strategy=scored["fon_adi"].map(bucket_from_name),
        sector=scored["fon_adi"].map(sector_from_name),
    )

    # Optional news pass: query Tavily for top-K candidates by quant score,
    # subtract a fixed penalty for any with negative-news hits. Penalty is
    # applied *before* pick_top so picks actually shift.
    hits_by_code: dict[str, list] = {}
    scored_pre = scored  # snapshot for counterfactual pick_top
    if news_enabled:
        scored, hits_by_code = apply_negative_news_penalty(
            scored,
            top_k=NEWS_QUERY_TOP_K_MULTIPLIER * n,
            keywords=NEGATIVE_NEWS_KEYWORDS,
            penalty=NEGATIVE_NEWS_PENALTY,
            api_key=news_api_key,
            cache_dir=NEWS_CACHE_DIR,
            ttl_seconds=NEWS_CACHE_TTL_SECONDS,
            max_age_days=NEWS_MAX_AGE_DAYS,
            max_results=NEWS_MAX_RESULTS_PER_FUND,
            timeout_seconds=NEWS_QUERY_TIMEOUT_SECONDS,
            allowed_domains=NEWS_DOMAIN_ALLOWLIST,
            excluded_domain_substrings=NEWS_EXCLUDED_DOMAIN_SUBSTRINGS,
        )

    selected, warning = pick_top(
        scored, n=n, max_per_type=max_per_type, max_per_sector=max_per_sector,
    )
    weighted = compute_weights(selected)

    # Project hits down to just the picked funds for the renderer.
    picked_codes = set(weighted["fon_kodu"].astype(str))
    hits_for_render = {
        code: [hit.to_render_dict() for hit in hits]
        for code, hits in hits_by_code.items()
        if code in picked_codes
    }

    # Compute "displaced" funds: those that would have been picked without the
    # news penalty but got pushed out by it. Only meaningful when news is on
    # and at least one fund got hits — otherwise pre/post pick_top runs are
    # identical by construction.
    displaced: list[dict[str, Any]] = []
    if news_enabled and hits_by_code:
        would_be, _ = pick_top(
            scored_pre, n=n, max_per_type=max_per_type, max_per_sector=max_per_sector,
        )
        would_be_codes = set(would_be["fon_kodu"].astype(str))
        displaced_codes = would_be_codes - picked_codes
        scored_pre_indexed = scored_pre.set_index(scored_pre["fon_kodu"].astype(str))
        for code in displaced_codes:
            row = scored_pre_indexed.loc[code]
            hits = hits_by_code.get(code, [])
            displaced.append({
                "fon_kodu": code,
                "fon_adi": str(row["fon_adi"]),
                "score_pre":  float(row["score"]),
                "score_post": float(row["score"]) - NEGATIVE_NEWS_PENALTY,
                "hits": [hit.to_render_dict() for hit in hits],
            })
        # Sort by pre-penalty score descending: the strongest fund we lost
        # appears first. Set iteration above is hash-dependent and would
        # otherwise leak into the rendered output.
        displaced.sort(key=lambda d: d["score_pre"], reverse=True)

    header = {
        "timestamp": now,
        "universe":  universe,
        "candidate_total": total,
        "candidate_kept":  len(horizoned),
        "horizon":  horizon,
        "risk_level": risk_level,
        "volume_priority": volume_priority,
        "fee_priority": fee_priority,
        "n": n,
        "warning": warning,
        "excluded_horizon": excluded_horizon,
    }

    if not news_enabled:
        news_meta: dict[str, Any] = {"enabled": False}
    else:
        news_meta = {
            "enabled": True,
            "key_present": bool(news_api_key),
            "top_k": NEWS_QUERY_TOP_K_MULTIPLIER * n,
            "total_hits": len(hits_by_code),
            "displaced": displaced,
        }

    return weighted, header, hits_for_render, news_meta
