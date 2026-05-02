"""Tunable constants for fundexpert. One file changes calibrate everything."""

from pathlib import Path

# --- Scoring constants --------------------------------------------------------

# Low/Med/High user priorities map to scalar weights, then re-normalized in score.py
PRIORITY_WEIGHTS: dict[str, float] = {
    "low": 0.10,
    "medium": 0.30,
    "high": 0.60,
}

# λ multiplier for the SRRI risk penalty: penalty = λ · ((risk - 1)/6)²
RISK_LAMBDAS: dict[str, float] = {
    "low": 0.05,
    "medium": 0.25,
    "high": 0.60,
}

# Horizon → return columns averaged for the primary return signal
HORIZON_BUCKETS: dict[str, tuple[str, ...]] = {
    "short":  ("ret_1m", "ret_3m"),
    "medium": ("ret_6m", "ret_ytd", "ret_1y"),
    "long":   ("ret_3y", "ret_5y"),
}

# --- Selection constants ------------------------------------------------------

DEFAULT_MAX_PER_TYPE: int = 2

WEIGHT_EPSILON: float = 0.01  # shift used by select/weights.py to avoid zero weights

# --- Paths -------------------------------------------------------------------

LAST_RUN_FILE: Path = Path.home() / ".fundexpert" / "last.json"
