# Fund Expert

A Python CLI that recommends an investment-fund portfolio from Turkish TEFAS
(regular funds) and BEFAS (retirement funds) data.

> Status: implemented and covered by unit, property, integration, and live-CSV
> smoke tests. The numbered design documents are retained as historical context;
> generated API documentation under `docs/fundexpert/` is the source-level
> reference.

## How it works (in one paragraph)

The CLI prompts in Turkish for risk level, horizon, volume, fee and momentum
priorities, and fund count. It loads three CSVs per universe, scores each fund
with normalized return/AUM/fee/momentum signals minus an SRRI risk penalty,
then picks the top N under independent strategy and sector caps. Weights are
snapped to 5% units and sum to 100%. The optional `--news` pass queries Tavily
for the top quantitative candidates and applies a fixed penalty when curated
negative-news terms are found.

## Repo layout

```
data/                  # local TEFAS/BEFAS CSV exports (gitignored)
docs/                  # historical design notes + generated API docs
fundexpert/            # Python package
tests/                 # unit, property, integration, and smoke tests
```

## Bringing your own data

The `data/` folder is gitignored, since TEFAS/BEFAS CSV exports are easily re-downloadable from the official portals and don't need to be checked in. Place your exports as:

```
data/tefas/{getiri,buyukluk,yonetim ucreti}.csv
data/befas/{getiri,buyukluk,yonetim ucreti}.csv
```

Each file is the raw TEFAS/BEFAS web export (3 metadata rows + header + data). The loader handles Turkish decimals (`,`) and skips the metadata.

Set `FUNDEXPERT_DATA_DIR` to override the default repository-local `data/`
directory.

## Setup

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e ".[dev]"
```

## Run

```bash
fundexpert            # interactive prompts
fundexpert --news     # add Tavily negative-news screening
python -m fundexpert  # equivalent module entry point
```

## Test

```bash
.venv/Scripts/python.exe -m pytest tests/
```

## Documentation

- [Generated API documentation](docs/fundexpert.html)
- [docs/README.md](docs/README.md) — historical design-document index
- [docs/01-architecture.md](docs/01-architecture.md)
- [docs/02-data-layer.md](docs/02-data-layer.md)
- [docs/03-scoring-engine.md](docs/03-scoring-engine.md)
- [docs/04-selection-and-weighting.md](docs/04-selection-and-weighting.md)
- [docs/05-cli-interaction.md](docs/05-cli-interaction.md)
- [docs/06-news-pass.md](docs/06-news-pass.md)
- [docs/07-output-and-testing.md](docs/07-output-and-testing.md)
- [docs/implementation-plan.md](docs/implementation-plan.md) — historical implementation plan
