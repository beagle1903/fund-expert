"""Compute per-fund score = base_score (weighted, normalized) − risk_penalty (SRRI λ)."""

import pandas as pd

from fundexpert.config import ScoringConfig
from fundexpert.scoring.normalize import minmax_normalize


def score_candidates(
    df: pd.DataFrame,
    volume_priority: str,
    fee_priority: str,
    risk_level: str,
    scoring_config: ScoringConfig,
) -> pd.DataFrame:
    """Add `score` and `_breakdown` columns. Input must already have `R` (from horizon)."""
    R_hat = minmax_normalize(df["R"])
    V_hat = minmax_normalize(df["aum_change_pct"])
    F_hat = minmax_normalize(df["applied_management_fee_pct"])

    # Priority → renormalized weights summing to 1.0
    w_return = 1.0
    w_volume = scoring_config.priority_weights[volume_priority]
    w_fee    = scoring_config.priority_weights[fee_priority]
    total = w_return + w_volume + w_fee
    w_return /= total
    w_volume /= total
    w_fee    /= total

    R_contrib = w_return * R_hat
    V_contrib = w_volume * V_hat
    F_contrib = w_fee * (1 - F_hat)
    base_score = R_contrib + V_contrib + F_contrib

    lam = scoring_config.risk_level_lambdas[risk_level]
    risk_norm = (df["risk"].astype(float).fillna(7.0) - 1.0) / 6.0
    risk_penalty = lam * (risk_norm ** 2)

    score = base_score - risk_penalty
    return df.assign(score=score)
