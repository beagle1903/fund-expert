# fundexpert

CLI that recommends a Turkish investment-fund portfolio from TEFAS/BEFAS CSVs.
User-facing strings are Turkish; code/identifiers are English.

## Running

```bash
# Interactive (questionary prompts)
.venv/Scripts/python.exe -m fundexpert.cli
# or after `pip install -e .`
fundexpert

# Non-interactive (skip prompts, useful from Agent shell)
.venv/Scripts/python.exe -c "
from datetime import datetime
from fundexpert.cli import run_pipeline, _ensure_utf8_stdio
from fundexpert.render.table import render_portfolio
from fundexpert.config import DEFAULT_MAX_PER_TYPE
_ensure_utf8_stdio()
selected, header, hits, _ = run_pipeline(
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

Smoke tests in `tests/test_smoke.py` read real CSVs from `data/`. When working in a git worktree under `.Agent/worktrees/`, junction the data dir in:

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
  → render.table.render_portfolio (--news adds: header line summarising top-K/hits/picks-changed, 📰+(−0.20) markers on penalised picks, "portföyde kaldı" footer for surviving hits, "portföyden düşen" footer for funds the penalty pushed out)
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
- **News source filtering**: `NEWS_DOMAIN_ALLOWLIST` (config.py) is forwarded to Tavily as `include_domains`, restricting search server-side to a curated list of neutral Turkish financial outlets (KAP/SPK regulators + business press). Extend the list as new neutral outlets show up — **never add issuer-owned domains** (Spotify/Instagram/complaint-sites and `*portfoy*.com.tr` were the false-positive drivers). `NEWS_EXCLUDED_DOMAIN_SUBSTRINGS` is a client-side belt-and-suspenders filter dropping any hostname containing `portfoy`/`portföy` even if mistakenly allowlisted. Cache key incorporates both lists so config changes invalidate stale entries automatically.

## Gotchas

- `str.upper()` in Python is *not* Turkish-aware: `"i".upper() == "I"`, not `"İ"`. Use the i↔İ / ı↔I replace before `.upper()` (see `select/strategy.py`).
- Stdout encoding: `_ensure_utf8_stdio()` must be called before any rendering on Windows or Turkish characters break.
- Last-run answers cached at `~/.fundexpert/last.json`; safe to delete.
- `LSP` MCP tool occasionally disconnects mid-session — not a code issue.

## AI Harness Protocol (Post-Feature Routine)

Whenever we finish implementing a new feature, the AI assistant MUST automatically run a wrap-up routine before moving on. This includes:
1. **Dead Code Analysis**: Run a dead-code finder (e.g. `vulture fundexpert/`) and actively clean up any orphaned code or unused imports.
2. **Documentation Update**: Run doc generators (e.g. `pdoc -o docs/ fundexpert/` or similar) to ensure the `docs/` folder is up to date, and revise `AGENTS.md` / `todos.md` if the architecture changed.

## Agent Insights
- Create a parallel code review system for my repos. In `.Agent/agents/` define 5 specialized review subagents: security-reviewer, architecture-reviewer, test-coverage-reviewer, performance-reviewer, and business-logic-reviewer. Each should have a focused system prompt, a clear output schema, and write to `reviews/<agent-name>.md`. Then create a `/review-parallel` slash command that launches all 5 in parallel via the Task tool against the current repo, waits for completion, and runs a final synthesizer agent that reads all 5 outputs and produces `reviews/SUMMARY.md` with prioritized P0/P1/P2 findings and suggested fixes as actionable Agent prompts. Run it once on fundexpert as a demo.

- Build me a test-driven auto-healing workflow for fundexpert. (1) Write `scripts/auto-heal.ps1` that takes a failing test name, runs it, pipes the failure output to `Agent -p` with a strict 'diagnose-then-fix-then-verify' system prompt, applies the patch, re-runs tests, and loops up to 5 times before escalating with a summary. (2) Add Hypothesis to the project and write property-based tests for the scoring, selection, and sector-cap modules—have Agent propose 3 invariants per module and implement them. (3) Run the auto-heal loop against any newly-failing properties and report which invariants caught real bugs vs needed loosening. Commit each successful auto-heal as a separate commit with a `auto-heal:` prefix so I can audit.

## Agent Testing Protocol

Whenever any of the tests fail, the AI assistant MUST immediately stop its current task and focus on fixing the tests. Make them pass first. Only after the tests are passing should the assistant continue working on its current task. If you are stuck for multiple turns trying to fix a test, raise an alarm and request manual interference from the user.
