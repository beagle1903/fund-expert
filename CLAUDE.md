# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

`AGENTS.md` is the detailed live contract (full pipeline, conventions, gotchas) and is imported below. This file summarizes what you need first.

@AGENTS.md

## What this is

Fundexpert recommends a Turkish TEFAS/BEFAS investment-fund portfolio from local CSV exports. Two front ends share one pipeline: an interactive Python CLI (`fundexpert/cli.py`, Turkish strings) and a local web dashboard (FastAPI `fundexpert/api.py` + Vite/React `frontend/`, English UI). Code and identifiers are English. Windows/PowerShell is the primary dev environment.

## Commands

```powershell
# Setup (Python 3.11+, Node.js)
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev,web]"
npm --prefix frontend install

# Full quality gate (same as CI): pytest+coverage, vitest, oxlint, vite build, vulture, pip check, git diff --check
.\scripts\check.ps1

# Python tests (coverage floor 90% is enforced by addopts in pyproject.toml)
.venv\Scripts\python.exe -m pytest tests/
# Single test: --no-cov avoids the coverage-floor failure on partial runs
.venv\Scripts\python.exe -m pytest tests/test_pick.py::test_name --no-cov

# Frontend
npm --prefix frontend test                          # vitest run
npm --prefix frontend test -- src/App.test.jsx      # single file
npm --prefix frontend run lint                      # oxlint
npm --prefix frontend run build

# Run
.venv\Scripts\python.exe -m fundexpert.cli          # CLI (add --news, --refresh, --force-refresh)
.\scripts\run.ps1                                   # starts/reuses API :8000 + Vite :5173, prints JSON status; logs in .Agent/logs/

# Dead code and generated API docs
.venv\Scripts\python.exe -m vulture fundexpert --min-confidence 80
.\scripts\refresh-docs.ps1
```

## Architecture (big picture)

- **Data layer** (`fundexpert/data/`): `bundle.py` treats `getiri.csv`, `buyukluk.csv`, `yonetim ucreti.csv` as one acquisition — `validate_bundle` then `publish_bundle` (immutable version + atomic `current.json` swap); `resolve_active_bundle` also accepts legacy flat files. `refresh.py`/`tefas_export.py` fetch fresh bundles via the undocumented TEFAS web-export transport and fail closed. `loader.py` parses the Turkish CSVs; `merge.py` joins them into one universe and attributes `kurucu` via `fundexpert/founders.py`.
- **Pipeline** (`fundexpert/pipeline.py`, `run_pipeline(candidates, PipelineConfig)`): founder filter → `scoring/` (horizon averaging, normalized weighted score minus SRRI risk penalty) → strategy/sector buckets from `fundexpert/rules.json` keywords (`select/strategy.py`, `select/sector.py`) → optional news penalty (`news/`, Tavily) → `select/pick.py` (independent strategy and sector caps) → `select/weights.py` (5% units). Tunables in `fundexpert/config.py`; pandera schemas in `fundexpert/schemas.py`.
- **Outputs**: `render/` (rich tables for CLI), `history/store.py` (runs saved to `~/.fundexpert/runs`, fail-soft), and `api.py` endpoints consumed by `frontend/src/api/fundexpert.js`. Vite proxies `/api` to `127.0.0.1:8000`.
- **Editable config via the web UI**: selection rules (`GET/PUT /api/selection-rules` → `fundexpert/rules.json`, never touching `cleanup_rules`) and the build-plugin profile (`GET/PUT /api/build-profile` → personal `profiles/default.json`, separate from frontend `DEFAULT_CONFIG`; saving never generates a portfolio).

## Data and tests

- `data/` (TEFAS/BEFAS CSVs) is gitignored. `tests/test_smoke.py` uses real CSVs and skips without them (as in CI). Override the location with `FUNDEXPERT_DATA_DIR`.
- If any test fails, fix tests before continuing other work.
- After finishing a feature: run vulture and `refresh-docs.ps1`, and update `AGENTS.md` if the architecture changed.
