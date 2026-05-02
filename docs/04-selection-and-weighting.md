# 04 — Selection & Weighting

Two pure functions, both operating on the scored candidate DataFrame.

## Selector (`select/pick.py`)

**Inputs:** scored DataFrame, `N` (target count), `max_per_type` (default `2`).

**Algorithm:**

1. Sort candidates by `score` descending.
2. Walk down the sorted list. For each fund:
   - If its `umbrella_type` (`Şemsiye Fon Türü`) already has `max_per_type` selections → skip.
   - Else → select.
   - Stop when `N` picks reached or list exhausted.
3. **Up-to-N semantics:** if the cap blocks further selection before `N`, return what we have and emit a warning:
   > `Picked 4 of requested 5 — no further fund of a different umbrella type qualified.`
4. The cap is **never silently relaxed**. The user explicitly chose "cap per umbrella type" as the policy.
5. If the candidate pool itself is smaller than `N` (e.g., extreme NaN exclusions), return everything in the pool with the same warning style.

**Defaults:**

- `max_per_type = 2` — kept in `config.py`. Not exposed via prompt in v1 to avoid prompt fatigue.
- `--max-per-type N` is reserved as a future CLI flag for power-user override.

## Weight Calculator (`select/weights.py`)

**Inputs:** list of selected funds with their final `score` values.

**Why we shift before normalizing:** soft-penalty scores can go **negative** (e.g., a high-risk fund chosen under risk-priority High). Score-proportional weighting on raw scores would produce zero or negative weights, which is meaningless. The shift guarantees every selected fund gets a non-zero allocation while preserving relative score gaps.

**Formula:**

```
ε         = 0.01
shifted_i = score_i − min(scores) + ε
weight_i  = shifted_i / Σ shifted
display_i = round(weight_i · 100, 1)
```

**Rounding reconciliation:** after rounding to 1 decimal, displayed weights may sum to 99.9 or 100.1. The largest weight absorbs the delta so the printed total is exactly 100.0.

## Output of This Stage

A list of selected-fund records, each containing:

| Field | Source |
|---|---|
| `fon_kodu` | join key |
| `fon_adi` | full fund name |
| `umbrella_type` | `Şemsiye Fon Türü` |
| `risk` | SRRI 1–7 |
| `display_weight_pct` | float, sums to 100.0 |
| `score` | final score (post-penalty) |
| `_breakdown` | the explainability dict from scoring (kept for v2 `--explain`) |

This list is what the renderer consumes.
