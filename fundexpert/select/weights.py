"""Score-proportional weights, snapped to multiples of 5 with a 5% floor."""

import pandas as pd

from fundexpert.config import WEIGHT_EPSILON

_STEP = 5  # display weights are integer multiples of 5%


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
    if n * _STEP > 100:
        # Defensive: would never happen with the CLI's N≤20 cap, but stay safe
        # by falling back to equal weighting in 5% units.
        units_each = max(1, (100 // _STEP) // n)
        display = pd.Series([units_each * _STEP] * n, index=out.index, dtype=int)
        # Top-up to 100 by adding leftover units to highest-score funds
        leftover = (100 // _STEP) - units_each * n
        for idx in out["score"].astype(float).nlargest(leftover).index:
            display.loc[idx] += _STEP
        out["display_weight_pct"] = display
        return out

    scores = out["score"].astype(float).clip(lower=WEIGHT_EPSILON)
    total_units = 100 // _STEP                      # 20 units of 5% each
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
        for idx in winners:
            units.loc[idx] += 1

    out["display_weight_pct"] = (units * _STEP).astype(int)
    return out
