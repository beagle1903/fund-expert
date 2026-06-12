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
    HISTORY_DIR,
    LAST_RUN_FILE,
    NEGATIVE_NEWS_KEYWORDS,
    NEGATIVE_NEWS_PENALTY,
    NEWS_API_KEY_ENV,
    NEWS_CACHE_DIR,
    NEWS_CACHE_TTL_SECONDS,
    NEWS_DOMAIN_ALLOWLIST,
    NEWS_EXCLUDED_DOMAIN_SUBSTRINGS,
    NEWS_MAX_AGE_DAYS,
    NEWS_MAX_RESULTS_PER_FUND,
    NEWS_QUERY_TIMEOUT_SECONDS,
    NEWS_QUERY_TOP_K_MULTIPLIER,
)
from fundexpert.data.loader import load_universe
from fundexpert.data.merge import merge_universe
from fundexpert.history.store import load_last_run, save_run
from fundexpert.pipeline import run_pipeline, PipelineConfig
from fundexpert.render.diff import render_diff
from fundexpert.render.table import render_portfolio

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
    import tempfile
    import os
    try:
        LAST_RUN_FILE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=LAST_RUN_FILE.parent, delete=False) as tmp:
            tmp.write(json.dumps(answers, ensure_ascii=False))
            tmp_name = tmp.name
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, LAST_RUN_FILE)
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
    parser.add_argument(
        "--diff-last", action="store_true",
        help="Önceki run ile portföy karşılaştırması göster",
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
        candidates = _load_one(u)
        config = PipelineConfig(
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
        selected, header, hits_for_render, news_meta = run_pipeline(
            candidates=candidates,
            config=config,
        )
        if header.get("warning"):
            print(f"Uyarı ({u}): {header['warning']}", file=sys.stderr)

        # Load previous run BEFORE saving current (so we retrieve the old one).
        previous_run = load_last_run(u, history_dir=HISTORY_DIR) if args.diff_last else None

        try:
            save_run(selected, header, history_dir=HISTORY_DIR)
        except Exception:
            pass  # history is quality-of-life only; never fail the run

        render_portfolio(selected, header, news=hits_for_render or None, news_meta=news_meta)

        if args.diff_last:
            if previous_run is None:
                print("(Karşılaştırma: daha önce kaydedilmiş run bulunamadı.)", file=sys.stderr)
            else:
                render_diff(selected, previous_run)
    return 0

if __name__ == "__main__":
    sys.exit(main())
