"""ε-shifted score-proportional weights, with rounding reconciliation to sum=100.0."""

import pandas as pd

from fundexpert.config import WEIGHT_EPSILON


def compute_weights(selected: pd.DataFrame) -> pd.DataFrame:
    """Add `display_weight_pct` column. Sum is exactly 100.0 after rounding."""
    out = selected.copy()
    if len(out) == 0:
        out["display_weight_pct"] = pd.Series(dtype=float)
        return out

    scores = out["score"].astype(float)
    shifted = scores - scores.min() + WEIGHT_EPSILON
    raw_weight = shifted / shifted.sum()
    display = (raw_weight * 100).round(1)

    delta = round(100.0 - display.sum(), 1)
    if delta != 0.0:
        idx_max = display.idxmax()
        display.loc[idx_max] = round(display.loc[idx_max] + delta, 1)

    out["display_weight_pct"] = display
    return out
