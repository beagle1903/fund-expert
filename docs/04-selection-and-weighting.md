# 04 — Selection & Weighting

Two pure functions, both operating on the scored candidate DataFrame.

## Selector (`select/pick.py`)

**Inputs:** scored DataFrame, `N` (target count), a diversification mode, and
optional `max_per_type` / `max_per_sector` overrides.

The selector applies two independent caps:

- **Strategy cap:** `strategy`, derived from the fund name, is the cap key. It
  is not `umbrella_type` (`Şemsiye Fon Türü`), which is too coarse to represent
  the portfolio strategy reliably.
- **Named-sector cap:** `sector`, also derived from the fund name, limits
  concentration in a named sector independently of strategy.

The `"other"` strategy and `"diversified"` sector are exempt. The latter keeps
otherwise-diversified funds from being artificially limited when they do not
have a sector keyword.

### Diversification schedules

The same derived cap is used independently for strategy and named sector unless
an explicit override is supplied.

| Mode | N = 1–11 | N = 12–15 | N = 16–20 |
|---|---:|---:|---:|
| Strict | 2 | 2 | 2 |
| Balanced (default) | 2 | 3 | 4 |
| Relaxed | 3 | 4 | 5 |

Balanced is the default in the API, CLI, and web UI. `--max-per-type N` and
`--max-per-sector N` are independent power-user overrides: each provided
numeric value replaces only its corresponding derived cap, while the other cap
continues to follow the selected mode.

**Algorithm:**

1. Sort candidates by `score` descending.
2. Walk down the sorted list. For each fund:
   - If its non-exempt `strategy` already has its strategy cap selections,
     skip it.
   - If its non-exempt `sector` already has its sector cap selections, skip it.
   - Otherwise select it.
   - Stop when `N` picks are reached or the list is exhausted.
3. **Up-to-N semantics:** if either constraint or the candidate pool prevents
   reaching `N`, return the eligible picks and emit the existing partial-result
   warning.
4. Caps are never silently relaxed.

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
