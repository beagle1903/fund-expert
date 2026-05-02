# 01 — Architecture

The CLI is a single-process Python app organized into modules with clear boundaries so each piece is testable in isolation.

## Module Layout

```
fundexpert/
├── cli.py              # entry point: argparse → interactive prompts → run pipeline
├── data/
│   ├── loader.py       # read CSVs (skip metadata rows), parse Turkish numbers
│   └── merge.py        # join getiri + buyukluk + yonetim_ucreti per universe by Fon Kodu
├── scoring/
│   ├── normalize.py    # min-max scaling per feature within candidate pool
│   ├── score.py        # weighted-sum score + soft risk penalty
│   └── horizon.py      # map Short/Medium/Long → return-column groups
├── select/
│   ├── pick.py         # top-N with umbrella-type cap; up-to-N semantics
│   └── weights.py      # score-proportional weight % (sum to 100)
├── news/
│   └── rss.py          # --news pass: fetch + match + annotate (no scoring impact in v1)
├── render/
│   └── table.py        # rich-based pretty table on stdout
└── config.py           # tunable constants (priority weights, risk λ, max_per_type, RSS URLs)
```

## Data Flow (Single Run)

1. **CLI prompts** for: universe (tefas/befas/both), risk priority (Low/Med/High), horizon (S/M/L), volume-change priority (L/M/H), fee priority (L/M/H), N.
2. **`loader`** reads the 3 CSVs for the chosen universe(s).
3. **`merge`** joins on `Fon Kodu` → one DataFrame per universe → concatenate if "both".
4. **`horizon`** picks return columns based on chosen duration.
5. **`normalize`** min-max scales each feature on the candidate pool.
6. **`score`** computes the per-fund score (see [03-scoring-engine](03-scoring-engine.md)).
7. **`pick`** selects top-N respecting the umbrella cap, with graceful fallback if N can't be filled.
8. **`weights`** converts scores to display percentages.
9. **`news.rss`** (only if `--news`) annotates picks with RSS headlines.
10. **`render`** prints a `rich` table on stdout.

## Isolation Principles

- **Pure cores:** `scoring/` and `select/` take DataFrames in, return DataFrames out — no IO, no globals. Easy to unit-test with hand-built fixtures.
- **IO at the edges:** Only `data/loader.py` (filesystem) and `news/rss.py` (network) touch external resources.
- **CLI is a thin orchestrator:** `cli.py` collects inputs and threads them through the pipeline. No business logic.
- **Constants in one place:** `config.py` holds every tunable scalar so post-launch calibration is a single-file change.
- **Optional dependencies isolated:** `feedparser` is imported inside `news/rss.py` only when `--news` is set, so a default run has zero network surface.

## Why this shape

- Each module has one purpose, a small surface, and can be understood without reading siblings.
- The pipeline is linear — no shared mutable state between stages — which makes failures easy to localize and re-runs deterministic given the same CSVs.
