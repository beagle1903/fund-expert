# Business Logic Review - Fund Expert

## Overview
A comprehensive review of the business logic within the `fundexpert` codebase was conducted. The focus was on the scoring mechanics, candidate selection logic, constraints/caps enforcement, weighting, and data cleaning.

## Findings & Evaluation

### P0 (Critical)
*   **None**. The core business logic is robust, mathematically sound, and handles missing/dirty data conservatively without producing invalid outputs.

### P1 (High Priority / High Impact)
*   **None**.

### P2 (Enhancements / Considerations)
*   **Horizon Scoring with Partial Data (`horizon.py` & `merge.py`)**: 
    The `clean_candidates` function drops funds missing `ret_3m`, enforcing a 3-month history baseline. In `apply_horizon`, the horizon return score `R` averages the available target columns using `mean(skipna=True)`. If `horizon="medium"` (`ret_6m`, `ret_ytd`, `ret_1y`), a fund that is exactly 4 months old might only have `ret_ytd` (if the year rolled over), and will be evaluated against older funds using just this single metric. While `skipna=True` is forgiving and retains more candidates, comparing partial-period returns to full-period returns could slightly skew `R_hat` calculations. 
    *Recommendation*: Consider enforcing a stricter data completeness check depending on the horizon bucket (e.g., if `horizon="medium"`, drop funds where `ret_6m` is missing), or heavily penalizing the score for funds lacking the full history for their target horizon bucket.

*   **News Penalty Scope (`penalty.py`)**:
    The optimization to group Tavily queries by `company_prefix` is excellent for saving API calls and recognizing that negative news (e.g., "soruşturma", "iflas") usually applies to the asset management company rather than an individual fund. Consequently, the penalty is applied to *all top-K queried funds* that belong to that company prefix. 
    *Consideration*: Since the news penalty is binary and fixed (`-0.20`), this behaves as a strong issuer-level penalty rather than a fund-level penalty. Ensure this is the intended behavior (it usually is for governance-related news in the Turkish market).

### General Observations
1.  **Scoring Equation**: The scoring formula in `score.py` accurately normalizes attributes using MinMax, applies user-defined weighting (pre-normalized to sum to 1.0), and penalizes risk utilizing a squared normalized SRRI scale. This correctly introduces a non-linear penalty for high risk when lambda is high.
2.  **Missing Risk Handling**: If the `risk` (SRRI) value is NaN, it defaults to `7.0` (maximum risk), thereby conservatively applying the highest risk penalty rather than assuming it is safe. This is a robust safety mechanism.
3.  **Caps and Diversity Rules**: `pick.py` enforces per-sector and per-strategy caps flawlessly via greedy selection. It never silently relaxes the caps; it halts selection and returns a warning if it exhausts candidates, preserving the user's diversity constraint strictly.
4.  **Turkish Locale Awareness**: The use of `turkish_upper()` for strategy and sector classification cleanly solves Python's locale-blind string methods (preventing "i" from mapping to "I").
5.  **Weighting Algorithm**: The `largest-remainder` algorithm in `weights.py` reliably guarantees that weights snap to exactly 5% intervals while summing to precisely 100%, and correctly respects the 5% minimum floor.

## Conclusion
The application's logic is extremely well thought out, with strong guardrails in place for typical market data flaws (missing fees, short history, missing risk scores). No critical business logic flaws were identified.
