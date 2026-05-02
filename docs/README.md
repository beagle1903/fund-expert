# Fund Expert — Design Docs

Design specs for the **Fund Expert** CLI: a Python tool that recommends a Turkish investment-fund portfolio (TEFAS regular funds and BEFAS retirement funds) based on user-provided criteria.

Date: 2026-05-02
Status: Design approved, ready for implementation plan.

## Sections

1. [Architecture](01-architecture.md) — module layout, data flow, isolation principles.
2. [Data Layer](02-data-layer.md) — CSV loading, Turkish locale, merge, missing-value policy.
3. [Scoring Engine](03-scoring-engine.md) — horizon mapping, normalization, weighted-sum + risk penalty.
4. [Selection & Weighting](04-selection-and-weighting.md) — top-N picker, umbrella-type cap, score-proportional weights.
5. [CLI Interaction](05-cli-interaction.md) — Turkish prompts, flags, validation.
6. [News Pass](06-news-pass.md) — `--news` flag, RSS sources, annotation only.
7. [Output & Testing](07-output-and-testing.md) — `rich` table, test strategy, dependencies.

## Locked Decisions (Recap)

| Area | Decision |
|---|---|
| Language / runtime | Python (3.11+) |
| Input mode | Interactive prompts (Turkish) |
| Universe | Asked per run: tefas / befas / both. Codes are disjoint, safe to combine. |
| "Volume change" column | `Portföy Büyüklüğü Değişimi (%)` (AUM change) |
| Horizon model | Duration alone selects return columns; "short-term profit" slider dropped |
| Horizon mapping | Short → 1ay, 3ay · Medium → 6ay, YTD, 1yıl · Long → 3yıl, 5yıl |
| Risk handling | Soft penalty in scoring (no hard cutoff) |
| Risk scale | SRRI 1–7 (verified: EU standard `Synthetic Risk and Reward Indicator`) |
| Priority scale | Low / Medium / High buckets → fixed weights 0.10 / 0.30 / 0.60 |
| Diversification | Cap per `Şemsiye Fon Türü`, default `max_per_type = 2` |
| Fund count | Up-to N (graceful fallback, never inflates) |
| Portfolio weights | Score-proportional (with ε-shift for negatives) |
| Scoring engine | Weighted sum of min-max-normalized features + soft risk penalty |
| News integration | On-demand via `--news` flag, RSS feeds, annotation only (no scoring impact) |
| Output | Pretty `rich` table on stdout (no file persistence in v1) |

## Out of Scope (v1)

- Hard risk cap or portfolio-average risk targeting
- Optimization-based portfolio construction (LP/QP)
- News-driven scoring or sentiment analysis
- KAP/SPK regulator-bulletin integration
- File output (JSON/CSV/MD reports)
- Multi-language UI (Turkish only)
- `--explain` per-fund breakdown (planned for v2)

## Open Items Tracked for Implementation

- The Low/Med/High → 0.10/0.30/0.60 weights and risk-penalty λ values (0.05 / 0.25 / 0.60) are calibrated guesses. Expect to tune after a few real runs. All constants live in one config module.
- The 3 RSS feed URLs in [News Pass](06-news-pass.md) are based on common Turkish finance sites but **not yet verified live**. Implementer must confirm each feed parses, has timestamps, and surfaces fund-relevant content before locking the list.
- Decimal handling: source CSVs use comma decimals with no thousands separator in observed rows. Loader will use `decimal=','` only; a unit test asserts numeric parsing on a known row in case real data contains thousands grouping.
