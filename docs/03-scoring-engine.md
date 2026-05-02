# 03 — Scoring Engine

Pure functions over the merged candidate DataFrame. No IO. Five steps: horizon mapping → normalization → priority weights → score formula → explainability dict.

## Step 1 — Pick the Return Signal (`scoring/horizon.py`)

The user's horizon choice maps to a fixed group of return columns.

| Horizon | Return columns averaged |
|---|---|
| Short | `ret_1m`, `ret_3m` |
| Medium | `ret_6m`, `ret_ytd`, `ret_1y` |
| Long | `ret_3y`, `ret_5y` |

If any column in the bucket is NaN for a fund, the bucket value is the mean of the available ones. If **all** columns in the bucket are NaN, the fund is excluded from the candidate pool. Excluded count is reported in the run header.

Output: a new `R` column on the candidate DataFrame.

## Step 2 — Normalize Features (`scoring/normalize.py`)

After horizon mapping and the universe filter, three raw features are min-max scaled to `[0, 1]` **on the candidate pool only** (so normalization adapts to the universe selection):

| Raw feature | Direction | Normalized symbol |
|---|---|---|
| `R` (horizon-bucket mean return) | higher = better | `R̂` |
| `aum_change_pct` | higher = better | `V̂` |
| `applied_management_fee_pct` | lower = better | `F̂` (used as `1 − F̂`) |

`risk` (SRRI 1–7) is not min-max normalized — it has a fixed integer scale and feeds the penalty term directly.

**Edge case:** if a feature column is constant across the pool (range = 0), normalization returns 0.5 for every row in that column. This avoids divide-by-zero and gives a neutral contribution.

## Step 3 — Priority Weights

The user's Low/Med/High choice for `volume` and `fee` maps to fixed scalar weights:

| Priority | Scalar weight |
|---|---|
| Low | 0.10 |
| Medium | 0.30 |
| High | 0.60 |

The **return weight** is fixed at `1.0` — returns are the always-on primary signal.

After collecting `(w_return=1.0, w_volume, w_fee)`, all three are renormalized to sum to 1.0 so `base_score` lives in `[0, 1]`.

```python
total = 1.0 + w_volume + w_fee
w_return /= total
w_volume /= total
w_fee    /= total
```

## Step 4 — Score Formula

For each candidate fund:

```
base_score   = w_return · R̂  +  w_volume · V̂  +  w_fee · (1 − F̂)
risk_penalty = λ · ((risk − 1) / 6)²
score        = base_score − risk_penalty
```

`(risk − 1) / 6` puts SRRI on `[0, 1]`; squaring makes high-risk funds penalized superlinearly.

`λ` is set by the user's risk priority:

| Risk priority | λ |
|---|---|
| Low (you don't mind risk) | 0.05 |
| Medium | 0.25 |
| High (you avoid risk) | 0.60 |

## Step 5 — Explainability

For each scored fund, `score.py` returns a small dict alongside the final number:

```python
{
    "base_score":    float,
    "R_contrib":     w_return * R̂,
    "V_contrib":     w_volume * V̂,
    "F_contrib":     w_fee * (1 - F̂),
    "risk_penalty":  float,
    "score":         float,
}
```

v1 prints only the final `score` column in the table. v2 will add a `--explain` flag that prints the per-fund breakdown.

## Calibration Caveats

- The Low/Med/High → 0.10/0.30/0.60 weights and λ values (0.05 / 0.25 / 0.60) are **calibrated guesses** — not derived from data.
- Score-proportional weighting (next section) is sensitive to score spread. If top-N scores are tightly clustered, weights will be near-equal; if scores have a long tail, weights skew hard. This is desired behavior for the scoring/weighting pair, not a bug.
- All constants live in `config.py`. Tuning is a one-file edit.
