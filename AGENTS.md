# fundexpert

CLI and local web app that recommend a Turkish investment-fund portfolio from
TEFAS/BEFAS CSVs. CLI strings are Turkish; the web UI, code, and identifiers
are English.

## Running

```bash
# Interactive (questionary prompts)
.venv/Scripts/python.exe -m fundexpert.cli
# or after `pip install -e ".[dev,web]"`
fundexpert

# Web UI (FastAPI backend + Vite/React frontend)
# In terminal 1 (Backend):
.venv/Scripts/python.exe -m uvicorn fundexpert.api:app --reload
# In terminal 2 (Frontend):
cd frontend && npm run dev

# Non-interactive (skip prompts, useful from Agent shell)
.venv/Scripts/python.exe -c "
from datetime import datetime
from fundexpert.data.loader import load_candidates_for_universe
from fundexpert.pipeline import run_pipeline, PipelineConfig
from fundexpert.ui import ensure_utf8_stdio
from fundexpert.config import DATA_ROOT
from fundexpert.render.table import render_portfolio

ensure_utf8_stdio()
u = 'tefas'
candidates = load_candidates_for_universe(u, DATA_ROOT)
config = PipelineConfig(
    universe=u, risk_level='medium', horizon='medium',
    volume_priority='medium', fee_priority='medium', momentum_priority='medium',
    n=8,
    now=datetime.now()
)
result = run_pipeline(candidates, config)
render_portfolio(result.weighted, result.header, news=result.hits_for_render or None, news_meta=result.news_meta)
"
```

`wt.exe` (Windows Terminal) cannot be launched from a non-interactive shell — invoke Python directly instead.

## Testing

```bash
./scripts/check.ps1
```

Smoke tests in `tests/test_smoke.py` read real CSVs from `data/`. When working in a git worktree under `.Agent/worktrees/`, junction the data dir in:

```powershell
New-Item -ItemType Junction -Path "<worktree>/data" -Target "<repo>/data"
```

## Pipeline

```
optional refresh.refresh_universe
  → tefas_export.download_web_export_bundle (one request per required view)
  → validate_bundle + publish_bundle (immutable version + atomic current.json)
bundle.resolve_active_bundle (versioned current.json or validated legacy files)
  → loader.load_universe(getiri, buyukluk, yonetim)
  → merge.merge_universe (one universe per run; attributes canonical `kurucu` from the official fund-title prefix; `both` runs the pipeline twice and renders two portfolios)
  → optional founder filter (TEFAS and BEFAS have separate canonical lists)
  → drop NaN applied_management_fee_pct
  → scoring.horizon.apply_horizon (averages return columns per horizon bucket)
  → scoring.score.score_candidates (weighted sum of R̂, V̂, 1−F̂, M̂; minus SRRI risk penalty)
  → assign strategy bucket via select.strategy.bucket_from_name(fon_adi)
  → assign sector bucket via select.sector.sector_from_name(fon_adi)
  → (--news only) news.penalty.apply_negative_news_penalty (top-K Tavily query, −0.20 binary penalty per fund with hits)
  → select.pick.pick_top (N picks, capped independently per strategy and named
    sector; default Balanced caps scale 2/3/4 for N=1–11/12–15/16–20, Strict stays
    at 2, Relaxed scales 3/4/5; "other" strategy and "diversified" sector are
    exempt; explicit numeric overrides win)
  → select.weights.compute_weights (5% units, largest-remainder, 5% floor)
  → render.table.render_portfolio (--news adds: header line summarising top-K/hits/picks-changed, 📰+(−0.20) markers on penalised picks, "portföyde kaldı" footer for surviving hits, "portföyden düşen" footer for funds the penalty pushed out)
```

## Conventions

- **CSV ingestion**: TEFAS/BEFAS export files have a 3-row preamble (`skiprows=3`), UTF-8 BOM, comma decimal separator inside quoted strings. Column names are Turkish — see `loader.py` for the rename map.
- **Data bundles**: Treat `getiri.csv`, `buyukluk.csv`, and `yonetim ucreti.csv` as one acquisition. `validate_bundle` checks metadata, schemas, numeric values, exact code-set coverage, row counts, and a 30-minute timestamp window. `publish_bundle` writes an immutable version and atomically swaps `current.json`; every automated acquisition must publish only through this seam.
- **Automated refresh**: `tefas_export.py` calls the undocumented web-export transport used by the public TEFAS returns page. It is not an official API. Make exactly one request per required view and selected universe. For TEFAS only, up to five codes that are not shared by all three views may be excluded from every staged file; the aligned files must still meet row floors and exact code-set coverage. BEFAS retains exact raw coverage. Six or more TEFAS differences and all other transport/schema drift fail closed. `refresh_universe` skips an already-current local-day bundle unless forced. Web generation opts in with `refresh_data`; CLI uses `--refresh` or `--force-refresh`.
- **Founder (`kurucu`) filter**: The exported CSVs omit `Kurucu`. `fundexpert/founders.py` holds the separate official TEFAS and BEFAS labels and deterministically attributes rows from normalized official fund-title prefixes (including known `PYŞ` aliases). API options must come from the active bundle through `GET /api/founders`, so clients cannot select a founder with zero current candidates. Apply the filter before cleaning/scoring and reset it when the universe changes.
- **Legacy compatibility**: Flat `data/<universe>/*.csv` files remain valid until the first versioned bundle is published. Never silently use cached candidates if the active bundle is missing or invalid.
- **Risk** = SRRI scale 1–7 (column `Fonun Risk Değeri` → `risk`).
- **Score** = base ∈ [0,1] minus risk penalty; can go slightly negative.
- **Strategy bucket** is derived from the fund name keyword using `fundexpert/rules.json`, *not* `umbrella_type` (Şemsiye Fon Türü) — Şemsiye is too coarse (Serbest/Katılım umbrellas span multiple strategies). See `select/strategy.py`.
- **Sector bucket** is also derived from the fund name (`select/sector.py`) using `rules.json` and capped independently from strategy. Without it, multiple sector-themed funds (e.g. 5 different TEKNOLOJİ funds across HİSSE/FON SEPETİ/DEĞİŞKEN strategies) can satisfy the strategy cap while still producing a single-sector portfolio. Funds without a sector keyword fall to `"diversified"` and are exempt from the sector cap. Add new sector keywords as new sectors show up in real picks.
- **Selection-rule editor**: The local web UI edits ordered strategy, sector, and exclusion rules through `GET/PUT /api/selection-rules`. Treat user keywords as case-insensitive plain text, preserve first-match ordering, validate blanks/duplicates/category slugs, and atomically replace `fundexpert/rules.json`. Never expose or overwrite `cleanup_rules` through this UI. Clear the process-local rule caches after a successful save and rebuild from the existing data snapshot without forcing a data refresh.
- **Build-plugin profile editor**: The local web UI manages the complete English `fund-expert:build-fund-portfolio` schema through `GET/PUT /api/build-profile`. Read and atomically replace the same personal `profiles/default.json` resolved from `FUND_EXPERT_STATE_DIR` or `~/Documents/Codex/Fund Expert`; validate every field and 5%-allocation feasibility before saving. This is separate from frontend `DEFAULT_CONFIG`, and saving it must never trigger portfolio generation.
- **Validation**: Intermediate pipeline steps (Scored, Weighted) are validated against `pandera` schemas in `fundexpert/schemas.py` when `PipelineConfig.validate_schemas=True`; real-data smoke tests enable it.
- **Weights** are integer multiples of 5%, every selected fund gets ≥5%, sum = 100. With N=20 every fund gets exactly 5%.
- **Tunables** live in `fundexpert/config.py` — priority weights, risk λ, horizon buckets, default cap, weight epsilon, news pass (Tavily query top-K, keywords, penalty, cache TTL).
- **News pass** (`--news`, opt-in): Tavily search per top-K candidate by quant score; any hit on a Turkish negative-news keyword (`soruşturma`, `iflas`, etc.) deducts a fixed `−0.20` from the fund's score before `pick_top`. Requires `TAVILY_API_KEY` env var; missing key → fail-soft (warning + skip). Module: `fundexpert/news/` (`match.py`, `tavily.py`, `penalty.py`). Cache: `~/.fundexpert/news_cache/` 1h TTL.
- **News source filtering**: `NewsConfig.domain_allowlist` is forwarded to Tavily as `include_domains`, restricting search server-side to curated neutral Turkish financial outlets. Extend it only with neutral sources—never issuer-owned domains. `excluded_domain_substrings` drops hostnames containing `portfoy`/`portföy` as defense in depth. The cache key includes both lists.

## Gotchas

- `str.upper()` in Python is *not* Turkish-aware: `"i".upper() == "I"`, not `"İ"`. Use the i↔İ / ı↔I replace before `.upper()` (see `select/strategy.py`).
- Stdout encoding: `ensure_utf8_stdio()` must be called before any rendering on Windows or Turkish characters break.
- Last-run answers cached at `~/.fundexpert/last.json`; safe to delete.
- Playwright-controlled Edge is rejected by the TEFAS WAF. Do not add anti-detection flags or attempt to bypass that control; use the bounded web-export adapter and fail closed if it becomes unavailable.
- `LSP` MCP tool occasionally disconnects mid-session — not a code issue.

## AI Harness Protocol (Post-Feature Routine)

Whenever we finish implementing a new feature, the AI assistant MUST automatically run a wrap-up routine before moving on. This includes:
1. **Dead Code Analysis**: Run a dead-code finder (e.g. `vulture fundexpert/`) and actively clean up any orphaned code or unused imports.
2. **Documentation Update**: Run `./scripts/refresh-docs.ps1` to ensure the `docs/` folder is up to date, and revise `AGENTS.md` / `todos.md` if the architecture changed.

## Agent Insights
- Create a parallel code review system for my repos. In `.Agent/agents/` define 5 specialized review subagents: security-reviewer, architecture-reviewer, test-coverage-reviewer, performance-reviewer, and business-logic-reviewer. Each should have a focused system prompt, a clear output schema, and write to `reviews/<agent-name>.md`. Then create a `/review-parallel` slash command that launches all 5 in parallel via the Task tool against the current repo, waits for completion, and runs a final synthesizer agent that reads all 5 outputs and produces `reviews/SUMMARY.md` with prioritized P0/P1/P2 findings and suggested fixes as actionable Agent prompts. Run it once on fundexpert as a demo.

- Build me a test-driven auto-healing workflow for fundexpert. (1) Write `scripts/auto-heal.ps1` that takes a failing test name, runs it, pipes the failure output to `Agent -p` with a strict 'diagnose-then-fix-then-verify' system prompt, applies the patch, re-runs tests, and loops up to 5 times before escalating with a summary. (2) Add Hypothesis to the project and write property-based tests for the scoring, selection, and sector-cap modules—have Agent propose 3 invariants per module and implement them. (3) Run the auto-heal loop against any newly-failing properties and report which invariants caught real bugs vs needed loosening. Commit each successful auto-heal as a separate commit with a `auto-heal:` prefix so I can audit.

## Agent Testing Protocol

Whenever any of the tests fail, the AI assistant MUST immediately stop its current task and focus on fixing the tests. Make them pass first. Only after the tests are passing should the assistant continue working on its current task. If you are stuck for multiple turns trying to fix a test, raise an alarm and request manual interference from the user.
