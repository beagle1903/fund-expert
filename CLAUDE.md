# fundexpert

CLI that recommends a Turkish investment-fund portfolio from TEFAS/BEFAS CSVs.
User-facing strings are Turkish; code/identifiers are English.

## Running

```bash
# Interactive (questionary prompts)
.venv/Scripts/python.exe -m fundexpert.cli
# or after `pip install -e .`
fundexpert

# Non-interactive (skip prompts, useful from Claude shell)
.venv/Scripts/python.exe -c "
from datetime import datetime
from fundexpert.cli import run_pipeline, _ensure_utf8_stdio
from fundexpert.render.table import render_portfolio
from fundexpert.config import DEFAULT_MAX_PER_TYPE
_ensure_utf8_stdio()
selected, header, hits = run_pipeline(
    universe='tefas', risk_level='medium', horizon='medium',
    volume_priority='medium', fee_priority='medium',
    n=8, max_per_type=DEFAULT_MAX_PER_TYPE, now=datetime.now())
render_portfolio(selected, header, news=hits or None)
"
```

`wt.exe` (Windows Terminal) cannot be launched from a non-interactive shell — invoke Python directly instead.

## Testing

```bash
.venv/Scripts/python.exe -m pytest tests/
```

Smoke tests in `tests/test_smoke.py` read real CSVs from `data/`. When working in a git worktree under `.claude/worktrees/`, junction the data dir in:

```powershell
New-Item -ItemType Junction -Path "<worktree>/data" -Target "<repo>/data"
```

## Pipeline

```
loader.load_universe(getiri, buyukluk, yonetim)
  → merge.merge_universe (one universe per run; `both` runs the pipeline twice and renders two portfolios)
  → drop NaN applied_management_fee_pct
  → scoring.horizon.apply_horizon (averages return columns per horizon bucket)
  → scoring.score.score_candidates (weighted sum of R̂, V̂, 1−F̂; minus SRRI risk penalty)
  → assign strategy bucket via select.strategy.bucket_from_name(fon_adi)
  → assign sector bucket via select.sector.sector_from_name(fon_adi)
  → (--news only) news.penalty.apply_negative_news_penalty (top-K Tavily query, −0.20 binary penalty per fund with hits)
  → select.pick.pick_top (N picks, capped at max_per_type per strategy AND max_per_sector per sector; "diversified" sector exempt)
  → select.weights.compute_weights (5% units, largest-remainder, 5% floor)
  → render.table.render_portfolio (news hits surface as "⚠️ Olumsuz haber:" footer)
```

## Conventions

- **CSV ingestion**: TEFAS/BEFAS export files have a 3-row preamble (`skiprows=3`), UTF-8 BOM, comma decimal separator inside quoted strings. Column names are Turkish — see `loader.py` for the rename map.
- **Risk** = SRRI scale 1–7 (column `Fonun Risk Değeri` → `risk`).
- **Score** = base ∈ [0,1] minus risk penalty; can go slightly negative.
- **Strategy bucket** is derived from the fund name keyword, *not* `umbrella_type` (Şemsiye Fon Türü) — Şemsiye is too coarse (Serbest/Katılım umbrellas span multiple strategies). See `select/strategy.py`.
- **Sector bucket** is also derived from the fund name (`select/sector.py`) and capped independently from strategy. Without it, multiple sector-themed funds (e.g. 5 different TEKNOLOJİ funds across HİSSE/FON SEPETİ/DEĞİŞKEN strategies) can satisfy the strategy cap while still producing a single-sector portfolio. Funds without a sector keyword fall to `"diversified"` and are exempt from the sector cap. Add new sector keywords as new sectors show up in real picks.
- **Weights** are integer multiples of 5%, every selected fund gets ≥5%, sum = 100. With N=20 every fund gets exactly 5%.
- **Tunables** live in `fundexpert/config.py` — priority weights, risk λ, horizon buckets, default cap, weight epsilon, news pass (Tavily query top-K, keywords, penalty, cache TTL).
- **News pass** (`--news`, opt-in): Tavily search per top-K candidate by quant score; any hit on a Turkish negative-news keyword (`soruşturma`, `iflas`, etc.) deducts a fixed `−0.20` from the fund's score before `pick_top`. Requires `TAVILY_API_KEY` env var; missing key → fail-soft (warning + skip). Module: `fundexpert/news/` (`match.py`, `tavily.py`, `penalty.py`). Cache: `~/.fundexpert/news_cache/` 1h TTL.

## Gotchas

- `str.upper()` in Python is *not* Turkish-aware: `"i".upper() == "I"`, not `"İ"`. Use the i↔İ / ı↔I replace before `.upper()` (see `select/strategy.py`).
- Stdout encoding: `_ensure_utf8_stdio()` must be called before any rendering on Windows or Turkish characters break.
- Last-run answers cached at `~/.fundexpert/last.json`; safe to delete.
- `LSP` MCP tool occasionally disconnects mid-session — not a code issue.
