"""Tunable constants for fundexpert. One file changes calibrate everything."""

import os
from pathlib import Path
from typing import Literal

from dataclasses import dataclass

@dataclass
class ScoringConfig:
    priority_weights: dict[str, float]
    risk_level_lambdas: dict[str, float]
    horizon_buckets: dict[str, tuple[str, ...]]

@dataclass
class SelectionConfig:
    weight_epsilon: float
    weight_step_pct: int

DEFAULT_SCORING_CONFIG = ScoringConfig(
    priority_weights={
        "low": 0.10,
        "medium": 0.30,
        "high": 0.60,
    },
    risk_level_lambdas={
        "low": 0.60,
        "medium": 0.25,
        "high": 0.05,
    },
    horizon_buckets={
        "short":  ("ret_1m", "ret_3m"),
        "medium": ("ret_6m", "ret_1y"),
        "long":   ("ret_3y", "ret_5y"),
    }
)

DEFAULT_SELECTION_CONFIG = SelectionConfig(
    weight_epsilon=0.01,
    weight_step_pct=5,
)

# --- Selection constants ------------------------------------------------------

DEFAULT_MAX_PER_TYPE: int = 2

# Per-sector cap. "diversified" sector (no sector keyword in name) is exempt.
DEFAULT_MAX_PER_SECTOR: int = 2


DiversificationMode = Literal["strict", "balanced", "relaxed"]

_DIVERSIFICATION_CAPS: dict[DiversificationMode, tuple[int, int, int]] = {
    "strict": (2, 2, 2),
    "balanced": (2, 3, 4),
    "relaxed": (3, 4, 5),
}


def resolve_diversification_caps(
    n: int,
    mode: DiversificationMode = "balanced",
    *,
    max_per_type: int | None = None,
    max_per_sector: int | None = None,
) -> tuple[int, int]:
    if not 1 <= n <= 20:
        raise ValueError("Portfolio size must be between 1 and 20.")
    if mode not in _DIVERSIFICATION_CAPS:
        raise ValueError(f"Unsupported diversification mode: {mode!r}.")
    for name, value in (
        ("max_per_type", max_per_type),
        ("max_per_sector", max_per_sector),
    ):
        if value is not None and not 1 <= value <= 20:
            raise ValueError(f"{name} must be between 1 and 20.")

    band = 0 if n <= 11 else 1 if n <= 15 else 2
    derived = _DIVERSIFICATION_CAPS[mode][band]
    return (
        derived if max_per_type is None else max_per_type,
        derived if max_per_sector is None else max_per_sector,
    )

MAX_CSV_SIZE_BYTES: int = 50 * 1024 * 1024
@dataclass
class NewsConfig:
    api_key_env: str = "TAVILY_API_KEY"
    query_top_k_multiplier: int = 3
    max_age_days: int = 30
    max_results_per_fund: int = 3
    query_timeout_seconds: int = 10
    negative_news_keywords: tuple[str, ...] = (
        "soruşturma", "dolandırıcılık", "iflas", "dava",
        "ceza", "fesih", "suspansiyon", "kapatma", "şikayet",
    )
    negative_news_penalty: float = 0.20
    domain_allowlist: tuple[str, ...] = (
        "kap.org.tr",
        "spk.gov.tr",
        "dunya.com",
        "bloomberght.com",
        "ekonomim.com",
        "paraanaliz.com",
        "fortuneturkey.com",
        "bigpara.hurriyet.com.tr",
        "ntv.com.tr",
        "haberturk.com",
        "sozcu.com.tr",
        "cumhuriyet.com.tr",
        "t24.com.tr",
        "aa.com.tr",
        "reuters.com",
    )
    excluded_domain_substrings: tuple[str, ...] = ("portfoy", "portföy")
    cache_dir: Path = Path.home() / ".fundexpert" / "news_cache"
    cache_ttl_seconds: int = 3600
    max_workers: int = 25

DEFAULT_NEWS_CONFIG = NewsConfig()

# Export backward-compatible aliases for cli.py and render/table.py
NEWS_API_KEY_ENV = DEFAULT_NEWS_CONFIG.api_key_env
NEGATIVE_NEWS_PENALTY = DEFAULT_NEWS_CONFIG.negative_news_penalty

# --- Paths -------------------------------------------------------------------

LAST_RUN_FILE: Path = Path.home() / ".fundexpert" / "last.json"

HISTORY_DIR: Path = Path.home() / ".fundexpert" / "runs"

DATA_ROOT: Path = Path(os.environ.get("FUNDEXPERT_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
