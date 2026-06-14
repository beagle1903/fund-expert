"""Top-level CLI: prompts → run_pipeline → render."""

import argparse
import os
import sys
from datetime import datetime

from fundexpert.config import (
    DEFAULT_MAX_PER_SECTOR,
    DEFAULT_MAX_PER_TYPE,
    HISTORY_DIR,
    NEWS_API_KEY_ENV,
    DATA_ROOT,
)
from fundexpert.ui import ensure_utf8_stdio, load_last_run_state, prompt_user, save_last_run_state
from fundexpert.pipeline import run_pipeline, PipelineConfig
from fundexpert.history.store import load_last_run, save_run
from fundexpert.render.diff import render_diff
from fundexpert.render.table import render_portfolio




from fundexpert.data.loader import load_candidates_for_universe




def main() -> int:
    ensure_utf8_stdio()
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

    last = load_last_run_state()
    try:
        answers = prompt_user(last)
    except KeyboardInterrupt:
        answers = None
    if answers is None:
        print("İptal edildi.", file=sys.stderr)
        return 130
    save_last_run_state(answers)

    news_api_key = os.environ.get(NEWS_API_KEY_ENV) if args.news else None

    universes_to_run = (
        ["tefas", "befas"] if answers["universe"] == "both" else [answers["universe"]]
    )
    now = datetime.now()
    
    for u in universes_to_run:
        candidates = load_candidates_for_universe(u, DATA_ROOT)
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
        result = run_pipeline(
            candidates=candidates,
            config=config,
        )
        if result.header.get("warning"):
            print(f"Uyarı ({u}): {result.header['warning']}", file=sys.stderr)

        # Load previous run BEFORE saving current (so we retrieve the old one).
        previous_run = load_last_run(u, history_dir=HISTORY_DIR) if args.diff_last else None

        try:
            save_run(result.weighted, result.header, history_dir=HISTORY_DIR)
        except OSError as e:
            print(f"Uyarı: Tarihçe kaydedilemedi: {e}", file=sys.stderr)

        render_portfolio(result.weighted, result.header, news=result.hits_for_render or None, news_meta=result.news_meta)

        if args.diff_last:
            if previous_run is None:
                print("(Karşılaştırma: daha önce kaydedilmiş run bulunamadı.)", file=sys.stderr)
            else:
                render_diff(result.weighted, previous_run)
    return 0

if __name__ == "__main__":
    sys.exit(main())
