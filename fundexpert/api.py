"""FastAPI boundary for the local Fundexpert web application."""

from __future__ import annotations

import logging
import math
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from fundexpert.config import DATA_ROOT, DEFAULT_MAX_PER_SECTOR, DEFAULT_MAX_PER_TYPE
from fundexpert.data.bundle import (
    ActiveDataBundle,
    BundleValidationError,
    DataBundleManifest,
    load_bundle_frames,
    resolve_active_bundle,
)
from fundexpert.data.merge import merge_universe
from fundexpert.pipeline import PipelineConfig, run_pipeline

logger = logging.getLogger(__name__)

Universe = Literal["tefas", "befas"]
Priority = Literal["low", "medium", "high"]
Horizon = Literal["short", "medium", "long"]

app = FastAPI(title="Fundexpert API", version="0.1.0")


class GenerateRequest(BaseModel):
    """Strict public request contract for portfolio generation."""

    model_config = ConfigDict(extra="forbid", strict=True)

    universe: Universe
    risk_level: Priority = "medium"
    horizon: Horizon = "medium"
    volume_priority: Priority = "medium"
    fee_priority: Priority = "medium"
    momentum_priority: Priority = "medium"
    n: int = Field(default=8, ge=1, le=20)
    max_per_type: int = Field(default=DEFAULT_MAX_PER_TYPE, ge=1, le=20)
    max_per_sector: int = Field(default=DEFAULT_MAX_PER_SECTOR, ge=1, le=20)
    news_enabled: bool = False


class PortfolioFund(BaseModel):
    fon_kodu: str
    fon_adi: str
    strategy: str
    sector: str
    display_weight_pct: int
    score: float
    risk: int | None


class DataSnapshot(BaseModel):
    universe: Universe
    bundle_id: str
    source: str
    exported_at: datetime
    imported_at: datetime | None
    row_count: int


class DataFileStatus(BaseModel):
    filename: str
    exported_at: datetime
    reported_rows: int
    actual_rows: int
    sha256: str


class UniverseDataStatus(BaseModel):
    universe: Universe
    available: bool
    snapshot: DataSnapshot | None = None
    files: list[DataFileStatus] = Field(default_factory=list)
    error: dict[str, str] | None = None


class DataStatusResponse(BaseModel):
    universes: list[UniverseDataStatus]


class PortfolioHeader(BaseModel):
    timestamp: datetime
    universe: Universe
    candidate_total: int
    candidate_kept: int
    horizon: Horizon
    risk_level: Priority
    volume_priority: Priority
    fee_priority: Priority
    momentum_priority: Priority
    n: int
    warning: str | None
    excluded_horizon: int


class NewsHitResponse(BaseModel):
    title: str
    url: str
    source: str
    published: datetime | None = None


class DisplacedFundResponse(BaseModel):
    fon_kodu: str
    fon_adi: str
    score_pre: float
    score_post: float
    hits: list[NewsHitResponse]


class NewsMetaResponse(BaseModel):
    enabled: bool
    key_present: bool | None = None
    top_k: int | None = None
    total_hits: int = 0
    displaced: list[DisplacedFundResponse] = Field(default_factory=list)


class GenerateResponse(BaseModel):
    weighted: list[PortfolioFund]
    header: PortfolioHeader
    hits_for_render: dict[str, list[NewsHitResponse]]
    news_meta: NewsMetaResponse
    data_snapshot: DataSnapshot


@dataclass(frozen=True)
class _CachedCandidates:
    fingerprint: str
    candidates: pd.DataFrame
    manifest: DataBundleManifest


class DataUnavailableError(RuntimeError):
    """Internal marker for invalid or unavailable local data."""


_cache: dict[str, _CachedCandidates] = {}
_cache_lock = threading.Lock()


def clear_candidate_cache() -> None:
    """Clear the process-local data cache, primarily for tests and tooling."""
    with _cache_lock:
        _cache.clear()


def _load_candidates(bundle: ActiveDataBundle) -> pd.DataFrame:
    frames = load_bundle_frames(bundle)
    return merge_universe(frames, universe=bundle.manifest.universe)


def get_cached_candidates(universe: Universe) -> tuple[pd.DataFrame, DataBundleManifest]:
    """Return candidates keyed by the complete active-bundle fingerprint."""
    try:
        active = resolve_active_bundle(universe, DATA_ROOT)
    except (BundleValidationError, OSError, UnicodeError, ValueError) as exc:
        raise DataUnavailableError(f"Data for {universe} is unavailable.") from exc

    with _cache_lock:
        cached = _cache.get(universe)
        if cached is not None and cached.fingerprint == active.fingerprint:
            return cached.candidates, cached.manifest

    try:
        candidates = _load_candidates(active)
    except (BundleValidationError, OSError, UnicodeError, ValueError, KeyError) as exc:
        raise DataUnavailableError(f"Data for {universe} is unavailable.") from exc

    entry = _CachedCandidates(
        fingerprint=active.fingerprint,
        candidates=candidates,
        manifest=active.manifest,
    )
    with _cache_lock:
        _cache[universe] = entry
    return entry.candidates, entry.manifest


def _safe_number(value: Any) -> float:
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError("Portfolio output contains a non-finite score.")
    return numeric


def _project_portfolio(weighted: pd.DataFrame) -> list[PortfolioFund]:
    projected: list[PortfolioFund] = []
    for _, row in weighted.iterrows():
        risk = None if pd.isna(row["risk"]) else int(row["risk"])
        projected.append(
            PortfolioFund(
                fon_kodu=str(row["fon_kodu"]),
                fon_adi="" if pd.isna(row["fon_adi"]) else str(row["fon_adi"]),
                strategy=str(row["strategy"]),
                sector=str(row["sector"]),
                display_weight_pct=int(row["display_weight_pct"]),
                score=_safe_number(row["score"]),
                risk=risk,
            )
        )
    return projected


def _status_for(universe: Universe) -> UniverseDataStatus:
    try:
        manifest = resolve_active_bundle(universe, DATA_ROOT).manifest
    except (BundleValidationError, OSError, UnicodeError, ValueError, KeyError, TypeError):
        logger.warning("Data status unavailable for %s.", universe, exc_info=True)
        return UniverseDataStatus(
            universe=universe,
            available=False,
            error={
                "code": "DATA_UNAVAILABLE",
                "message": f"Data for {universe.upper()} is unavailable or invalid.",
            },
        )

    return UniverseDataStatus(
        universe=universe,
        available=True,
        snapshot=DataSnapshot.model_validate(manifest.to_snapshot_dict()),
        files=[DataFileStatus.model_validate(item.to_dict()) for item in manifest.files],
    )


@app.get("/api/data-status", response_model=DataStatusResponse)
def get_data_status() -> DataStatusResponse:
    return DataStatusResponse(universes=[_status_for("tefas"), _status_for("befas")])


@app.post("/api/generate", response_model=GenerateResponse)
def generate_portfolio(req: GenerateRequest) -> GenerateResponse:
    try:
        candidates, manifest = get_cached_candidates(req.universe)
    except DataUnavailableError as exc:
        logger.warning("Portfolio generation has no usable %s data.", req.universe, exc_info=True)
        raise HTTPException(
            status_code=503,
            detail={
                "code": "DATA_UNAVAILABLE",
                "message": f"Data for {req.universe.upper()} is unavailable or invalid.",
            },
        ) from exc

    config = PipelineConfig(
        universe=req.universe,
        risk_level=req.risk_level,
        horizon=req.horizon,
        volume_priority=req.volume_priority,
        fee_priority=req.fee_priority,
        momentum_priority=req.momentum_priority,
        n=req.n,
        max_per_type=req.max_per_type,
        max_per_sector=req.max_per_sector,
        now=datetime.now(),
        news_enabled=req.news_enabled,
        news_api_key=os.environ.get("TAVILY_API_KEY") if req.news_enabled else None,
    )

    try:
        result = run_pipeline(candidates, config)
        weighted = _project_portfolio(result.weighted)
        header = PortfolioHeader.model_validate(result.header)
        hits = {
            code: [NewsHitResponse.model_validate(hit) for hit in items]
            for code, items in result.hits_for_render.items()
        }
        news_meta = NewsMetaResponse.model_validate(result.news_meta)
    except Exception as exc:
        logger.exception("Unexpected portfolio generation failure.")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "Portfolio generation failed unexpectedly.",
            },
        ) from exc

    return GenerateResponse(
        weighted=weighted,
        header=header,
        hits_for_render=hits,
        news_meta=news_meta,
        data_snapshot=DataSnapshot.model_validate(manifest.to_snapshot_dict()),
    )
