from datetime import datetime
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from fundexpert.config import (
    DiversificationMode,
    ScoringConfig,
    SelectionConfig,
    DEFAULT_SCORING_CONFIG,
    DEFAULT_SELECTION_CONFIG,
    NewsConfig,
    DEFAULT_NEWS_CONFIG,
    resolve_diversification_caps,
)
from fundexpert.news.penalty import apply_negative_news_penalty
from fundexpert.scoring.horizon import apply_horizon
from fundexpert.scoring.score import score_candidates
from fundexpert.news.report import compute_displaced_funds
from fundexpert.select.pick import pick_top
from fundexpert.select.sector import sector_from_names
from fundexpert.select.strategy import bucket_from_names
from fundexpert.select.weights import compute_weights
from fundexpert.data.merge import clean_candidates
from fundexpert.founders import filter_by_founder, validate_founder
from fundexpert.utils.text import turkish_upper_series


@dataclass
class PipelineConfig:
    universe: str
    risk_level: str
    horizon: str
    volume_priority: str
    fee_priority: str
    momentum_priority: str
    n: int
    now: datetime
    diversification_mode: DiversificationMode = "balanced"
    max_per_type: int | None = None
    max_per_sector: int | None = None
    founder: str | None = None
    news_enabled: bool = False
    news_api_key: str | None = None
    validate_schemas: bool = False
    scoring_config: ScoringConfig = field(default_factory=lambda: DEFAULT_SCORING_CONFIG)
    selection_config: SelectionConfig = field(default_factory=lambda: DEFAULT_SELECTION_CONFIG)
    news_config: NewsConfig = field(default_factory=lambda: DEFAULT_NEWS_CONFIG)


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
    max_per_type, max_per_sector = resolve_diversification_caps(
        config.n,
        config.diversification_mode,
        max_per_type=config.max_per_type,
        max_per_sector=config.max_per_sector,
    )
    total = len(candidates)

    if config.founder is not None:
        validate_founder(config.founder, config.universe)
    candidates = filter_by_founder(candidates, config.founder)
    candidate_after_founder = len(candidates)
    if config.founder is not None and candidate_after_founder == 0:
        raise ValueError(
            f"No candidates remain for founder {config.founder!r} in {config.universe}."
        )

    # Drop funds with NaN primary fee and short history
    candidates = clean_candidates(candidates)

    horizoned, excluded_horizon = apply_horizon(candidates, config.horizon, config.scoring_config)

    scored = score_candidates(
        horizoned,
        volume_priority=config.volume_priority,
        fee_priority=config.fee_priority,
        momentum_priority=config.momentum_priority,
        risk_level=config.risk_level,
        scoring_config=config.scoring_config,
        validate_schema=config.validate_schemas,
    )
    scored_fon_adi_upper = turkish_upper_series(scored["fon_adi"])
    scored = scored.assign(
        strategy=bucket_from_names(scored_fon_adi_upper),
        sector=sector_from_names(scored_fon_adi_upper),
    )

    if config.validate_schemas:
        from fundexpert.schemas import ScoredCandidatesSchema
        scored = ScoredCandidatesSchema.validate(scored)

    # Optional news pass: query Tavily for top-K candidates by quant score,
    # subtract a fixed penalty for any with negative-news hits. Penalty is
    # applied *before* pick_top so picks actually shift.
    hits_by_code: dict[str, list] = {}
    scored_pre = scored  # snapshot for counterfactual pick_top
    if config.news_enabled:
        scored, hits_by_code = apply_negative_news_penalty(
            scored,
            top_k=config.n * config.news_config.query_top_k_multiplier,
            api_key=config.news_api_key,
            news_config=config.news_config,
        )

    selected, warning = pick_top(
        scored, n=config.n, max_per_type=max_per_type, max_per_sector=max_per_sector,
    )
    weighted = compute_weights(selected, config.selection_config)

    if config.validate_schemas:
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
            max_per_type=max_per_type,
            max_per_sector=max_per_sector,
            penalty=config.news_config.negative_news_penalty,
        )

    header = {
        "timestamp": config.now,
        "universe":  config.universe,
        "candidate_total": total,
        "candidate_after_founder": candidate_after_founder,
        "candidate_kept":  len(horizoned),
        "founder": config.founder,
        "horizon":  config.horizon,
        "risk_level": config.risk_level,
        "volume_priority": config.volume_priority,
        "fee_priority": config.fee_priority,
        "momentum_priority": config.momentum_priority,
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
            "top_k": config.news_config.query_top_k_multiplier * config.n,
            "total_hits": len(hits_by_code),
            "displaced": displaced,
        }

    return PipelineResult(
        weighted=weighted,
        header=header,
        hits_for_render=hits_for_render,
        news_meta=news_meta,
    )
