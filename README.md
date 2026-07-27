# Fundexpert

Fundexpert recommends a Turkish TEFAS or BEFAS investment-fund portfolio from
local CSV exports. It provides both an interactive Python CLI and a local
FastAPI/React dashboard.

The recommendation engine scores return, fund size, management fee, fund-flow
momentum, and SRRI risk. It then applies independent strategy and sector
diversification caps and assigns weights in 5% units.

## Setup

Python 3.11+ and Node.js are required.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev,web]"
npm --prefix frontend install
```

`pyproject.toml` is the dependency source of truth. `requirements.txt` is a
compiled development lock generated from `requirements.in`.

## Data

Place a complete three-file export under each universe:

```text
data/
  tefas/
    getiri.csv
    buyukluk.csv
    yonetim ucreti.csv
  befas/
    getiri.csv
    buyukluk.csv
    yonetim ucreti.csv
```

Each file must be a TEFAS/BEFAS CSV with the standard three-row preamble,
UTF-8/BOM encoding, Turkish headers, and comma decimals.

The loader validates all three files as one acquisition. It checks metadata,
required columns, numeric fields, reported row counts, fund-code coverage, and
that export timestamps fall within a 30-minute window.

The exports do not include a `Kurucu` column. Fundexpert attributes each row to
the canonical founder shown by the official TEFAS/BEFAS `Kurucu` selector,
using normalized official-title prefixes. TEFAS and BEFAS founder lists are
kept separate. Portfolio generation defaults to all founders; the CLI and web
dashboard can narrow the candidate pool to one founder before scoring.

Existing flat files remain supported. Future import automation can call
`fundexpert.data.bundle.validate_bundle` and `publish_bundle`; publication
stores an immutable version and atomically changes `current.json` only after
validation succeeds.

Set `FUNDEXPERT_DATA_DIR` to override the default `data/` directory.

## Run

CLI:

```powershell
.venv\Scripts\python.exe -m fundexpert.cli
.venv\Scripts\python.exe -m fundexpert.cli --news
```

Local web application:

```powershell
# Terminal 1
.venv\Scripts\python.exe -m uvicorn fundexpert.api:app --reload

# Terminal 2
npm --prefix frontend run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` to the local FastAPI server.

The optional news pass requires `TAVILY_API_KEY`. Without a key, it fails soft
and uses the quantitative portfolio unchanged.

## API

- `POST /api/generate` validates configuration and returns a projected
  portfolio, news metadata, and the exact data snapshot used. Optional
  `founder` limits the candidate pool before cleaning, scoring, and selection.
- `GET /api/founders?universe=tefas|befas` returns only canonical founders
  present in the active universe bundle, with fund counts.
- `GET /api/data-status` reports TEFAS/BEFAS availability, export metadata,
  record counts, and file hashes.

Invalid request values return `422`. Unavailable or invalid data returns a safe
`503 DATA_UNAVAILABLE`.

## Verification

Run the complete local quality gate:

```powershell
.\scripts\check.ps1
```

It runs the Python suite with coverage, frontend tests, frontend lint and
production build, dead-code analysis, dependency checks, and `git diff --check`.

To refresh generated API documentation:

```powershell
.\scripts\refresh-docs.ps1
```

Historical design documents under `docs/01-*.md` through
`docs/implementation-plan.md` describe the original pre-implementation design
and are retained for context. This README, `AGENTS.md`, the source, and tests
are the live contract.
