# Fund Expert

A Python CLI that recommends an investment-fund portfolio from Turkish TEFAS (regular funds) and BEFAS (retirement funds) data, based on user-provided criteria: risk tolerance, holding horizon, weight on recent volume change, weight on management fee, and target number of funds.

> Status: design complete, implementation pending. See `docs/` for the full spec and `docs/implementation-plan.md` for the build plan.

## How it works (in one paragraph)

You run the CLI; it prompts you in Turkish for a few choices (risk priority, horizon, volume/fee priorities, fund count). It loads three CSVs per universe (`buyukluk.csv`, `getiri.csv`, `yonetim ucreti.csv`) from `data/tefas/` and `data/befas/`, scores each fund with a weighted sum of normalized features minus a soft SRRI risk penalty, picks the top N respecting an umbrella-type diversification cap, weights them score-proportionally, and prints a `rich` table. Pass `--news` to also fetch RSS headlines from Turkish financial sites and annotate each pick.

## Repo layout

```
data/                  # local TEFAS/BEFAS CSV exports (gitignored)
docs/                  # design specs (8 docs) + implementation plan
fundexpert/            # Python package (to be built per the plan)
tests/                 # pytest suite (to be built per the plan)
```

## Bringing your own data

The `data/` folder is gitignored, since TEFAS/BEFAS CSV exports are easily re-downloadable from the official portals and don't need to be checked in. Place your exports as:

```
data/tefas/{getiri,buyukluk,yonetim ucreti}.csv
data/befas/{getiri,buyukluk,yonetim ucreti}.csv
```

Each file is the raw TEFAS/BEFAS web export (3 metadata rows + header + data). The loader handles Turkish decimals (`,`) and skips the metadata.

## Setup (after implementation)

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
fundexpert --news     # add RSS news annotations
```

## Test

```bash
pytest
```

## Design docs

- [docs/README.md](docs/README.md) — index + locked decisions
- [docs/01-architecture.md](docs/01-architecture.md)
- [docs/02-data-layer.md](docs/02-data-layer.md)
- [docs/03-scoring-engine.md](docs/03-scoring-engine.md)
- [docs/04-selection-and-weighting.md](docs/04-selection-and-weighting.md)
- [docs/05-cli-interaction.md](docs/05-cli-interaction.md)
- [docs/06-news-pass.md](docs/06-news-pass.md)
- [docs/07-output-and-testing.md](docs/07-output-and-testing.md)
- [docs/implementation-plan.md](docs/implementation-plan.md) — task-by-task build plan
