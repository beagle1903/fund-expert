"""Score-proportional weights, snapped to multiples of 5 with a 5% floor."""

import pandas as pd

from fundexpert.config import WEIGHT_EPSILON, WEIGHT_STEP_PCT


def compute_weights(selected: pd.DataFrame) -> pd.DataFrame:
    """Add `display_weight_pct` column.

    Each selected fund gets a 5% floor, the remaining 100 - 5*N is distributed
    score-proportionally using the largest-remainder method on units of 5%.
    Sum is exactly 100. With N=20 (the CLI cap), every fund gets exactly 5%.
    """
    out = selected.copy()
    n = len(out)
    if n == 0:
        out["display_weight_pct"] = pd.Series(dtype=int)
        return out
    if n * WEIGHT_STEP_PCT > 100:
        # Defensive: would never happen with the CLI's N≤20 cap, but stay safe
        # by falling back to equal weighting in 5% units.
        units_each = (100 // WEIGHT_STEP_PCT) // n
        display = pd.Series([units_each * WEIGHT_STEP_PCT] * n, index=out.index, dtype=int)
        # Top-up to 100 by adding leftover units to highest-score funds
        leftover = (100 // WEIGHT_STEP_PCT) - units_each * n
        winners_idx = out["score"].astype(float).nlargest(leftover).index
        display.loc[winners_idx] += WEIGHT_STEP_PCT
        out["display_weight_pct"] = display
        return out

    scores = out["score"].astype(float).clip(lower=WEIGHT_EPSILON)
    total_units = 100 // WEIGHT_STEP_PCT                      # 20 units of 5% each
    base_units = 1                                   # 5% floor per fund
    remaining_units = total_units - base_units * n   # units to distribute by score

    proportions = scores / scores.sum()
    raw_extra = proportions * remaining_units
    floor_extra = raw_extra.astype(int)
    leftover = int(remaining_units - floor_extra.sum())

    units = floor_extra + base_units
    if leftover > 0:
        # Largest-remainder: hand the leftover units to the funds with the
        # biggest fractional part. Stable on ties (pandas keeps insertion order).
        remainders = raw_extra - floor_extra
        winners = remainders.nlargest(leftover).index
        units.loc[winners] += 1

    out["display_weight_pct"] = (units * WEIGHT_STEP_PCT).astype(int)
    return out
