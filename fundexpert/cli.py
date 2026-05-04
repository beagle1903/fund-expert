"""Top-level CLI: prompts → run_pipeline → render."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from fundexpert.config import (
    DEFAULT_MAX_PER_SECTOR,
    DEFAULT_MAX_PER_TYPE,
    LAST_RUN_FILE,
)
from fundexpert.data.loader import load_universe
from fundexpert.data.merge import merge_universe
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
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run the full data → score → select pipeline for a single universe."""
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
    selected, warning = pick_top(
        scored, n=n, max_per_type=max_per_type, max_per_sector=max_per_sector,
    )
    weighted = compute_weights(selected)

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
        help="(Reserved for v2 — RSS news annotation. No-op in v1.)",
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

    if args.news:
        print(
            "Not: --news özelliği v2 için planlandı, henüz aktif değil.",
            file=sys.stderr,
        )

    universes_to_run = (
        ["tefas", "befas"] if answers["universe"] == "both" else [answers["universe"]]
    )
    now = datetime.now()
    for u in universes_to_run:
        selected, header = run_pipeline(
            universe=u,
            risk_level=answers["risk_level"],
            horizon=answers["horizon"],
            volume_priority=answers["volume_priority"],
            fee_priority=answers["fee_priority"],
            n=answers["n"],
            max_per_type=args.max_per_type,
            max_per_sector=args.max_per_sector,
            now=now,
        )
        if header.get("warning"):
            print(f"Uyarı ({u}): {header['warning']}", file=sys.stderr)
        render_portfolio(selected, header, news=None)
    return 0
