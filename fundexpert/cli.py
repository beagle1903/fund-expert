"""Top-level CLI: prompts → run_pipeline → render."""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from fundexpert.config import (
    DEFAULT_MAX_PER_SECTOR,
    DEFAULT_MAX_PER_TYPE,
    LAST_RUN_FILE,
    NEGATIVE_NEWS_KEYWORDS,
    NEGATIVE_NEWS_PENALTY,
    NEWS_API_KEY_ENV,
    NEWS_CACHE_DIR,
    NEWS_CACHE_TTL_SECONDS,
    NEWS_MAX_AGE_DAYS,
    NEWS_MAX_RESULTS_PER_FUND,
    NEWS_QUERY_TIMEOUT_SECONDS,
    NEWS_QUERY_TOP_K_MULTIPLIER,
)
from fundexpert.data.loader import load_universe
from fundexpert.data.merge import merge_universe
from fundexpert.news.penalty import apply_negative_news_penalty
from fundexpert.render.table import render_portfolio
from fundexpert.scoring.horizon import apply_horizon
from fundexpert.scoring.score import score_candidates
from fundexpert.select.pick import pick_top
from fundexpert.select.sector import sector_from_name
from fundexpert.select.strategy import bucket_from_name
from fundexpert.select.weights import compute_weights

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"


def _load_one(universe: str) -> pd.DataFrame:
    """Load and merge a single universe (tefas or befas) into a candidate frame."""
    folder = DATA_ROOT / universe
    frames = load_universe(
        getiri_path=folder / "getiri.csv",
        buyukluk_path=folder / "buyukluk.csv",
        yonetim_path=folder / "yonetim ucreti.csv",
    )
    return merge_universe(frames, universe=universe)


def run_pipeline(
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
    candidates = _load_one(universe)
    total = len(candidates)

    # Drop funds with NaN primary fee (per missing-value policy)
    candidates = candidates[candidates["applied_management_fee_pct"].notna()]

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
            "displaced": [],  # filled in Task 2
        }

    return weighted, header, hits_for_render, news_meta


# --- Prompt layer (Turkish) -------------------------------------------------

UNIVERSE_CHOICES = ["tefas", "befas", "both"]
PRIORITY_CHOICES = ["low", "medium", "high"]
HORIZON_CHOICES = ["short", "medium", "long"]


def _load_last_run() -> dict[str, Any]:
    if not LAST_RUN_FILE.exists():
        return {}
    try:
        return json.loads(LAST_RUN_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_last_run(answers: dict[str, Any]) -> None:
    try:
        LAST_RUN_FILE.parent.mkdir(parents=True, exist_ok=True)
        LAST_RUN_FILE.write_text(json.dumps(answers, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass  # quality-of-life only — never fail the run on cache write errors


def _prompt(last: dict[str, Any]) -> dict[str, Any] | None:
    """Run interactive prompts. Returns None if the user cancelled (Ctrl+C / Esc)."""
    import questionary

    universe = questionary.select(
        "Fon evreni:", choices=UNIVERSE_CHOICES,
        default=last.get("universe", "tefas"),
    ).ask()
    if universe is None:
        return None

    risk_level = questionary.select(
        "Risk seviyesi (yüksek = yüksek risk tolere edilir):",
        choices=PRIORITY_CHOICES, default=last.get("risk_level", "medium"),
    ).ask()
    if risk_level is None:
        return None

    horizon = questionary.select(
        "Yatırım vadesi:",
        choices=HORIZON_CHOICES, default=last.get("horizon", "medium"),
    ).ask()
    if horizon is None:
        return None

    volume_priority = questionary.select(
        "Hacim değişimi önceliği:",
        choices=PRIORITY_CHOICES, default=last.get("volume_priority", "medium"),
    ).ask()
    if volume_priority is None:
        return None

    fee_priority = questionary.select(
        "Yönetim ücreti önceliği:",
        choices=PRIORITY_CHOICES, default=last.get("fee_priority", "medium"),
    ).ask()
    if fee_priority is None:
        return None

    n_raw = questionary.text(
        "Kaç fon istiyorsun (1-20)?",
        default=str(last.get("n", 5)),
        validate=lambda v: v.isdigit() and 1 <= int(v) <= 20,
    ).ask()
    if n_raw is None:
        return None

    return {
        "universe": universe,
        "risk_level": risk_level,
        "horizon": horizon,
        "volume_priority": volume_priority,
        "fee_priority": fee_priority,
        "n": int(n_raw),
    }


def _ensure_utf8_stdio() -> None:
    """Force UTF-8 on stdout/stderr so Turkish characters render on any terminal."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def main() -> int:
    _ensure_utf8_stdio()
    parser = argparse.ArgumentParser(prog="fundexpert")
    parser.add_argument(
        "--news", action="store_true",
        help="Tavily ile olumsuz haber taraması (gerekli: TAVILY_API_KEY env var)",
    )
    parser.add_argument(
        "--max-per-type", type=int, default=DEFAULT_MAX_PER_TYPE,
        help="Max funds per strateji (e.g. para piyasası, hisse, borçlanma)",
    )
    parser.add_argument(
        "--max-per-sector", type=int, default=DEFAULT_MAX_PER_SECTOR,
        help="Max funds per sektör (e.g. teknoloji, sağlık, enerji)",
    )
    args = parser.parse_args()

    last = _load_last_run()
    try:
        answers = _prompt(last)
    except KeyboardInterrupt:
        answers = None
    if answers is None:
        print("İptal edildi.", file=sys.stderr)
        return 130
    _save_last_run(answers)

    news_api_key = os.environ.get(NEWS_API_KEY_ENV) if args.news else None

    universes_to_run = (
        ["tefas", "befas"] if answers["universe"] == "both" else [answers["universe"]]
    )
    now = datetime.now()
    for u in universes_to_run:
        selected, header, hits_for_render, news_meta = run_pipeline(
            universe=u,
            risk_level=answers["risk_level"],
            horizon=answers["horizon"],
            volume_priority=answers["volume_priority"],
            fee_priority=answers["fee_priority"],
            n=answers["n"],
            max_per_type=args.max_per_type,
            max_per_sector=args.max_per_sector,
            now=now,
            news_enabled=args.news,
            news_api_key=news_api_key,
        )
        if header.get("warning"):
            print(f"Uyarı ({u}): {header['warning']}", file=sys.stderr)
        render_portfolio(selected, header, news=hits_for_render or None)
    return 0
