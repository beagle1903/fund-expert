"""Restrict one universe's candidates to the selected fund scope."""

from __future__ import annotations

import pandas as pd

from fundexpert.config import LEGACY_FUND_SCOPE, FundScope

OPEN_TO_PLATFORM_COLUMN = "open_to_platform"


class FundScopeUnavailableError(ValueError):
    """Raised when the active bundle cannot tell which funds are in scope."""


def filter_by_fund_scope(
    candidates: pd.DataFrame,
    scope: FundScope,
    universe: str,
) -> pd.DataFrame:
    """Return the funds in ``scope``, failing closed if the data cannot serve it."""
    if OPEN_TO_PLATFORM_COLUMN not in candidates.columns:
        # Bundles without open codes hold exactly the universe's legacy scope.
        if scope == LEGACY_FUND_SCOPE[universe]:
            return candidates
        raise FundScopeUnavailableError(
            f"The active {universe.upper()} data has no fund-scope information."
        )
    if scope == "all":
        return candidates
    return candidates[candidates[OPEN_TO_PLATFORM_COLUMN]]
