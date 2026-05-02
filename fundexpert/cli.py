"""Top-level CLI: prompts → run_pipeline → render."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from fundexpert.config import (
    DEFAULT_MAX_PER_TYPE,
    LAST_RUN_FILE,
)
from fundexpert.data.loader import load_universe
from fundexpert.data.merge import merge_universe, merge_universes
from fundexpert.render.table import render_portfolio
from fundexpert.scoring.horizon import apply_horizon
from fundexpert.scoring.score import score_candidates
from fundexpert.select.pick import pick_top
from fundexpert.select.weights import compute_weights

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"


def _load_combined(universe: str) -> pd.DataFrame:
    """Load and merge one or both universes into a single candidate frame."""
    parts: list[pd.DataFrame] = []
    universes = ["tefas", "befas"] if universe == "both" else [universe]
    for u in universes:
        folder = DATA_ROOT / u
        frames = load_universe(
            getiri_path=folder / "getiri.csv",
            buyukluk_path=folder / "buyukluk.csv",
            yonetim_path=folder / "yonetim ucreti.csv",
        )
        parts.append(merge_universe(frames, universe=u))
    return merge_universes(parts) if len(parts) > 1 else parts[0]


def run_pipeline(
    universe: str,
    risk_priority: str,
    horizon: str,
    volume_priority: str,
    fee_priority: str,
    n: int,
    max_per_type: int,
    now: datetime,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run the full data → score → select pipeline. Returns (selected, header)."""
    candidates = _load_combined(universe)
    total = len(candidates)

    # Drop funds with NaN primary fee (per missing-value policy)
    candidates = candidates[candidates["applied_management_fee_pct"].notna()]

    horizoned = apply_horizon(candidates, horizon)
    excluded_horizon = horizoned.attrs.get("excluded_count", 0)

    scored = score_candidates(
        horizoned,
        volume_priority=volume_priority,
        fee_priority=fee_priority,
        risk_priority=risk_priority,
    )
    selected, warning = pick_top(scored, n=n, max_per_type=max_per_type)
    weighted = compute_weights(selected)

    header = {
        "timestamp": now,
        "universe":  universe,
        "candidate_total": total,
        "candidate_kept":  len(horizoned),
        "horizon":  horizon,
        "risk_priority": risk_priority,
        "volume_priority": volume_priority,
        "fee_priority": fee_priority,
        "n": n,
        "warning": warning,
        "excluded_horizon": excluded_horizon,
    }
    return weighted, header


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


def _prompt(last: dict[str, Any]) -> dict[str, Any]:
    import questionary

    universe = questionary.select(
        "Fon evreni:", choices=UNIVERSE_CHOICES,
        default=last.get("universe", "tefas"),
    ).ask()

    risk_priority = questionary.select(
        "Risk önceliği (yüksek = riskten kaçınma):",
        choices=PRIORITY_CHOICES, default=last.get("risk_priority", "medium"),
    ).ask()

    horizon = questionary.select(
        "Yatırım vadesi:",
        choices=HORIZON_CHOICES, default=last.get("horizon", "medium"),
    ).ask()

    volume_priority = questionary.select(
        "Hacim değişimi önceliği:",
        choices=PRIORITY_CHOICES, default=last.get("volume_priority", "medium"),
    ).ask()

    fee_priority = questionary.select(
        "Yönetim ücreti önceliği:",
        choices=PRIORITY_CHOICES, default=last.get("fee_priority", "medium"),
    ).ask()

    n_raw = questionary.text(
        "Kaç fon istiyorsun (1-20)?",
        default=str(last.get("n", 5)),
        validate=lambda v: v.isdigit() and 1 <= int(v) <= 20,
    ).ask()

    return {
        "universe": universe,
        "risk_priority": risk_priority,
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
        help="(Reserved for v2 — RSS news annotation. No-op in v1.)",
    )
    parser.add_argument(
        "--max-per-type", type=int, default=DEFAULT_MAX_PER_TYPE,
        help="Max funds per Şemsiye Fon Türü",
    )
    args = parser.parse_args()

    last = _load_last_run()
    answers = _prompt(last)
    _save_last_run(answers)

    selected, header = run_pipeline(
        universe=answers["universe"],
        risk_priority=answers["risk_priority"],
        horizon=answers["horizon"],
        volume_priority=answers["volume_priority"],
        fee_priority=answers["fee_priority"],
        n=answers["n"],
        max_per_type=args.max_per_type,
        now=datetime.now(),
    )

    if header.get("warning"):
        print(f"Uyarı: {header['warning']}", file=sys.stderr)

    if args.news:
        print(
            "Not: --news özelliği v2 için planlandı, henüz aktif değil.",
            file=sys.stderr,
        )

    render_portfolio(selected, header, news=None)
    return 0
