"""Compute per-fund score = base_score (weighted, normalized) − risk_penalty (SRRI λ)."""

import pandas as pd

from fundexpert.config import PRIORITY_WEIGHTS, RISK_LAMBDAS
from fundexpert.scoring.normalize import minmax_normalize


def score_candidates(
    df: pd.DataFrame,
    volume_priority: str,
    fee_priority: str,
    risk_priority: str,
) -> pd.DataFrame:
    """Add `score` and `_breakdown` columns. Input must already have `R` (from horizon)."""
    out = df.copy()

    R_hat = minmax_normalize(out["R"])
    V_hat = minmax_normalize(out["aum_change_pct"])
    F_hat = minmax_normalize(out["applied_management_fee_pct"])

    # Priority → renormalized weights summing to 1.0
    w_return = 1.0
    w_volume = PRIORITY_WEIGHTS[volume_priority]
    w_fee    = PRIORITY_WEIGHTS[fee_priority]
    total = w_return + w_volume + w_fee
    w_return /= total
    w_volume /= total
    w_fee    /= total

    R_contrib = w_return * R_hat
    V_contrib = w_volume * V_hat
    F_contrib = w_fee * (1 - F_hat)
    base_score = R_contrib + V_contrib + F_contrib

    lam = RISK_LAMBDAS[risk_priority]
    risk_norm = (out["risk"].astype(float) - 1.0) / 6.0
    risk_penalty = lam * (risk_norm ** 2)

    score = base_score - risk_penalty
    out["score"] = score

    out["_breakdown"] = [
        {
            "base_score":   float(b),
            "R_contrib":    float(r),
            "V_contrib":    float(v),
            "F_contrib":    float(f),
            "risk_penalty": float(p),
            "score":        float(s),
        }
        for b, r, v, f, p, s in zip(base_score, R_contrib, V_contrib, F_contrib, risk_penalty, score)
    ]
    return out
