# Spike: are horizon buckets, SRRI lambdas, and 5% weights stable?

Issue #9. Read-only. No scoring, selection, weight, or default changes.

**Answer:** the local files cannot say whether these defaults are stable. Leave them alone. This spike does not open a follow-on implementation issue.

## What is fixed today

Live defaults in `fundexpert/config.py`:

| Knob | Default |
|---|---|
| Horizon buckets | short = mean(`ret_1m`, `ret_3m`); medium = mean(`ret_6m`, `ret_1y`); long = mean(`ret_3y`, `ret_5y`) |
| SRRI λ | `low` 0.60, `medium` 0.25, `high` 0.05 |
| Weights | 5% floor, 5% steps, leftover units split in proportion to score (clipped at 0.01), largest remainder |

`low` means the investor wants less risk: the CLI prompt is “yüksek = yüksek risk tolere edilir”, and λ = 0.60 is the large penalty. Penalty is `λ · ((SRRI − 1) / 6)²`, subtracted from a base score in `[0, 1]`. At SRRI 7 the three lambdas remove 0.60, 0.25, or 0.05.

`apply_horizon` keeps a fund when the shortest column in the chosen bucket is present. Other columns in the bucket may be missing; `R` is the mean of the columns that exist.

`ret_ytd` is stored on every returns file and is not part of any bucket. `docs/03-scoring-engine.md` is an older design note: it still puts `ret_ytd` in the medium bucket and swaps the λ labels. The code and `tests/test_config.py` are the contract.

Score-proportional weights apply only after names are chosen. For a 5-fund portfolio, 25% is the floors and 75% follows the scores. For the API default of 8 funds, 40% is the floors and 60% follows the scores. At 20 funds every weight is 5%.

## Universe and the date range we actually have

Two universes, each an immutable bundle of `getiri.csv`, `buyukluk.csv`, and `yonetim ucreti.csv`. A bundle is one export. Each return column is a trailing window ending on that export date.

| Universe | Bundles on disk | Export dates | Span | Active bundle |
|---|---:|---|---:|---|
| TEFAS | 12 | 2026-07-28 through 2026-09-22 | 55 days | `20260922T081828-916bbeb4c5d4` (1,067 funds) |
| BEFAS | 4 | 2026-07-28 through 2026-08-19 | 21 days | `20260819T184519-1a8b6d9fd81b` (311 funds) |

Most TEFAS gaps are 0–3 days. The longer gaps are 12, 16, and 14 days. BEFAS has no export after 19 August 2026. Row counts drift slightly (TEFAS 1,041 → 1,067; BEFAS 310 → 311). There is no unit-price or daily NAV series. `~/.fundexpert/runs` stores generated portfolios, which is the same limitation.

Coverage on the active TEFAS file: `ret_1m` 1,058, `ret_3m` 1,036, `ret_6m` 1,012, `ret_1y` 921, `ret_3y` 580, `ret_5y` 367, SRRI 948. The long bucket therefore drops most of the universe, because `ret_3y` is required. On active BEFAS, five-year coverage is higher (250 of 311) and SRRI is complete.

Inside the 22 September TEFAS snapshot, rank correlation of the two columns that a bucket averages: short 0.71 (n = 1,036), medium 0.80 (n = 921), long 0.34 (n = 367). The same fund’s `ret_1y` on 28 July and 22 September still ranks at 0.47 (n = 878). That agreement is the shared part of two overlapping year windows.

## What a real holdout would require

A holdout scores a fund with fields published on date T, then measures what happened after T.

1. Freeze the candidate features as of T: the trailing windows, SRRI, fee, and size that the export carried that day. Later bundles can supply those features only when the decision date is the earlier export.
2. An outcome window that starts on or after T. Trailing columns on a later file qualify only when that column’s lookback does not reach back through T. A one-month column needs the next export to be at least about 31 days later. A three-month column needs about 90 days. A one-year column needs about a year. A five-year column needs about five years.
3. Enough non-overlapping outcomes to see more than one regime. One later month is one observation, even if several snapshot pairs point at it.
4. The same test run separately on TEFAS and BEFAS.
5. Knobs chosen before the outcome window is inspected.

Counted from the export dates: TEFAS has 29 snapshot pairs at least 31 days apart, and zero pairs at least 90 days apart. Those 29 pairs reuse one August–September stretch; the archive is 55 days, so it contains at most one non-overlapping one-month outcome, and that outcome still leaves a gap between 28 July and the start of the 22 September one-month window. BEFAS has zero pairs 31 days apart. Medium and long buckets have no holdout in this archive. Comparing `ret_1y` across these snapshots reuses the same year of performance.

## What “better” means

These three measures are properties of a portfolio after the decision. They are not `R`, not the min-max rank inside a snapshot, and not `score`.

**Realized return.** Percent change in fund value from decision time T to T + h, taken from a window that starts on or after T. Apply the weights chosen at T and hold them to the horizon. Compare with an equal-weight portfolio of the same names when the question is the 5% grid, and with the same portfolio construction under a single frozen alternative when the question is the bucket or λ. One month of TEFAS rankings against the September one-month window would be a single anecdote. It cannot crown a bucket, a lambda, or a weight grid.

**Concentration.** After selection, the weight vector’s Herfindahl index, the largest weight, and the effective number of holdings (`1 / HHI`). Strategy and sector caps already limit which names get in; they are outside this spike. The weight question is only how the 5% grid spreads the portfolio among names already chosen. A tighter grid is better only when it reduces single-name exposure without giving up the realized-return comparison above. The score spread produces that concentration mechanically; restating the spread is not evidence.

**Turnover.** Between two decision dates, the share of names replaced and half the sum of absolute weight changes. The scorer never sees turnover. A useful sample is a rebalance calendar (for example month-end) over many dates. Day-apart exports in this archive would measure file noise.

A change is supported only when it improves realized return at the horizon the bucket claims to serve, without a worse concentration or turnover result on later, non-overlapping windows. A knob that only reshuffles funds already ranked by an overlapping trailing return fails that test.

## Decision

Leave the horizon buckets, the SRRI lambdas, and the 5% score-proportional weights as they are.

The files show what each default does to a single cross-section, and they show that neighboring snapshots still share most of their long windows. They do not show that the defaults are stable in live use, and they do not show that a different bucket, lambda, or weight step would help. Shipping a new formula from this archive would fit the in-sample windows the score already uses.

No follow-on implementation issue. A later spike can revisit the question after the bundle archive covers non-overlapping outcome windows for the horizon under test: several one-month gaps before touching the short bucket, several quarter-long gaps before touching medium, and a multi-year point-in-time price history before touching long or the risk penalty.
