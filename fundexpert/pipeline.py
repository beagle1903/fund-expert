from datetime import datetime
from dataclasses import dataclass, field
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
    ScoringConfig,
    SelectionConfig,
    DEFAULT_SCORING_CONFIG,
    DEFAULT_SELECTION_CONFIG,
)
from fundexpert.news.penalty import apply_negative_news_penalty
from fundexpert.scoring.horizon import apply_horizon
from fundexpert.scoring.score import score_candidates
from fundexpert.news.report import compute_displaced_funds
from fundexpert.select.pick import pick_top
from fundexpert.select.sector import sector_from_name
from fundexpert.select.strategy import bucket_from_name
from fundexpert.select.weights import compute_weights
from dataclasses import dataclass
from fundexpert.data.merge import clean_candidates
from fundexpert.utils.text import turkish_upper
import os


@dataclass
class PipelineConfig:
    universe: str
    risk_level: str
    horizon: str
    volume_priority: str
    fee_priority: str
    n: int
    max_per_type: int
    now: datetime
    max_per_sector: int = DEFAULT_MAX_PER_SECTOR
    news_enabled: bool = False
    news_api_key: str | None = None
    scoring_config: ScoringConfig = field(default_factory=lambda: DEFAULT_SCORING_CONFIG)
    selection_config: SelectionConfig = field(default_factory=lambda: DEFAULT_SELECTION_CONFIG)


@dataclass
class PipelineResult:
    weighted: pd.DataFrame
    header: dict[str, Any]
    hits_for_render: dict[str, list]
    news_meta: dict[str, Any]


def run_pipeline(
    candidates: pd.DataFrame,
    config: PipelineConfig,
) -> PipelineResult:
    """Run the full data → score → select pipeline for a single universe.

    Returns (selected_df, header_dict, hits_by_pick, news_meta). When
    `news_enabled` is False, `hits_by_pick` is always {} and `news_meta`
    is `{"enabled": False}`. When True, the news pass runs against the
    top-K candidates (K = NEWS_QUERY_TOP_K_MULTIPLIER * n) and returns
    matched articles for any of the *finally-picked* funds; `news_meta`
    carries metadata about the pass (key_present, top_k, total_hits,
    displaced).
    """
    if config.universe not in ("tefas", "befas"):
        raise ValueError(
            f"run_pipeline accepts 'tefas' or 'befas', got {config.universe!r}. "
            "Use main()'s 'both' option for dual-portfolio output."
        )
    total = len(candidates)

    # Drop funds with NaN primary fee and short history
    candidates = clean_candidates(candidates)

    horizoned = apply_horizon(candidates, config.horizon, config.scoring_config)
    excluded_horizon = horizoned.attrs.get("excluded_count", 0)

    scored = score_candidates(
        horizoned,
        volume_priority=config.volume_priority,
        fee_priority=config.fee_priority,
        risk_level=config.risk_level,
        scoring_config=config.scoring_config,
    )
    scored_fon_adi_upper = scored["fon_adi"].fillna("").apply(turkish_upper)
    scored = scored.assign(
        strategy=scored_fon_adi_upper.map(bucket_from_name),
        sector=scored_fon_adi_upper.map(sector_from_name),
    )
    
    if os.environ.get("DEBUG") == "1" or "PYTEST_CURRENT_TEST" in os.environ:
        from fundexpert.schemas import ScoredCandidatesSchema
        scored = ScoredCandidatesSchema.validate(scored)

    # Optional news pass: query Tavily for top-K candidates by quant score,
    # subtract a fixed penalty for any with negative-news hits. Penalty is
    # applied *before* pick_top so picks actually shift.
    hits_by_code: dict[str, list] = {}
    scored_pre = scored  # snapshot for counterfactual pick_top
    if config.news_enabled:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            scored, hits_by_code = apply_negative_news_penalty(
                scored,
                executor=executor,
                top_k=NEWS_QUERY_TOP_K_MULTIPLIER * config.n,
                keywords=NEGATIVE_NEWS_KEYWORDS,
                penalty=NEGATIVE_NEWS_PENALTY,
                api_key=config.news_api_key,
                cache_dir=NEWS_CACHE_DIR,
                ttl_seconds=NEWS_CACHE_TTL_SECONDS,
                max_age_days=NEWS_MAX_AGE_DAYS,
                max_results=NEWS_MAX_RESULTS_PER_FUND,
                timeout_seconds=NEWS_QUERY_TIMEOUT_SECONDS,
                allowed_domains=NEWS_DOMAIN_ALLOWLIST,
                excluded_domain_substrings=NEWS_EXCLUDED_DOMAIN_SUBSTRINGS,
            )

    selected, warning = pick_top(
        scored, n=config.n, max_per_type=config.max_per_type, max_per_sector=config.max_per_sector,
    )
    weighted = compute_weights(selected, config.selection_config)
    
    if os.environ.get("DEBUG") == "1" or "PYTEST_CURRENT_TEST" in os.environ:
        from fundexpert.schemas import SelectedPortfolioSchema
        weighted = SelectedPortfolioSchema.validate(weighted)

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
    if config.news_enabled and hits_by_code:
        displaced = compute_displaced_funds(
            scored_pre=scored_pre,
            picked_codes=picked_codes,
            hits_by_code=hits_by_code,
            n=config.n,
            max_per_type=config.max_per_type,
            max_per_sector=config.max_per_sector,
            penalty=NEGATIVE_NEWS_PENALTY,
        )

    header = {
        "timestamp": config.now,
        "universe":  config.universe,
        "candidate_total": total,
        "candidate_kept":  len(horizoned),
        "horizon":  config.horizon,
        "risk_level": config.risk_level,
        "volume_priority": config.volume_priority,
        "fee_priority": config.fee_priority,
        "n": config.n,
        "warning": warning,
        "excluded_horizon": excluded_horizon,
    }

    if not config.news_enabled:
        news_meta: dict[str, Any] = {"enabled": False}
    else:
        news_meta = {
            "enabled": True,
            "key_present": bool(config.news_api_key),
            "top_k": NEWS_QUERY_TOP_K_MULTIPLIER * config.n,
            "total_hits": len(hits_by_code),
            "displaced": displaced,
        }

    return PipelineResult(
        weighted=weighted,
        header=header,
        hits_for_render=hits_for_render,
        news_meta=news_meta,
    )
