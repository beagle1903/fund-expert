# Test Coverage & Quality Review: FundExpert

## 1. Executive Summary
The `fundexpert` codebase exhibits **excellent test coverage (97.25% overall)** and a high-quality test suite encompassing 207 tests. Testing methodologies are varied, combining classic unit tests (Pytest fixtures, parametrization) with property-based testing (Hypothesis) for critical mathematical components like scoring and weighting. The suite robustly handles numerous edge cases natively.

## 2. Coverage Findings
**Total Coverage:** 97% (836 statements, 23 missed)

**Areas Missing Coverage (P2 - Minor):**
- `fundexpert/__main__.py` (0%): Typical entry point file, mostly boilerplate.
- `fundexpert/cli.py` (91%): Some CLI interactions/branching paths are not fully covered.
- `fundexpert/news/tavily.py` (93%): Missing a few edge case scenarios (likely related to network error handling branches or caching).
- `fundexpert/ui.py` (95%), `fundexpert/data/merge.py` (96%), `fundexpert/render/diff.py` (97%), `fundexpert/news/report.py` (94%): Minor uncovered branches.

**Actionable Steps:**
- **[P2]** Add a quick integration/smoke test invoking `__main__.py` to catch any top-level module load errors.
- **[P2]** Ensure network-related exception branches in `tavily.py` are fully mocked and asserted.

## 3. Quality of Tests
The test quality is **High**.
- **Pytest Ecosystem:** Good use of `conftest.py` for fixtures. Heavy and effective use of `@pytest.mark.parametrize` makes the tests very readable and exhaustive without boilerplate code (e.g., parsing news names, picking buckets).
- **Pandera Schemas:** Intermediate data boundaries are validated automatically in tests when `PYTEST_CURRENT_TEST` is set, acting as an implicit invariant assertion system.
- **Mocking:** News API handles failures without relying on live endpoints during unit tests. Network exception handling is asserted.
- **Smoke Tests:** `test_smoke.py` acts as an integration sanity check using real CSVs, preventing regressions from structural data shifts.

## 4. Property-Based Testing Invariants
The team has integrated `Hypothesis` to effectively test the pure functional layers of the project (Scoring, Selection, and Weights).

**Current Covered Invariants:**
- **Score (`test_score.py`)**: 
  - Bounds limits (-2.0 <= score <= 2.0).
  - Returns monotonicity (higher R = higher score, given other parameters equal).
  - Fees monotonicity (higher F = lower score, given other parameters equal).
- **Pick (`test_pick.py`)**: 
  - Result size bounds.
  - Sector/Strategy cap bounding count checks.
  - Bypass cap check (when N = caps).
- **Weights (`test_weights.py`)**: 
  - Sum exactly equals 100%.
  - Every output weight is modulo 5 == 0.

**Suggested New Invariants (P1 - Recommended):**
- **[P1] Sector Count Exhaustiveness (`test_pick.py`)**: If the resulting portfolio is exactly N, and the sector cap is C, then there must be at least `ceil(N/C)` distinct sectors in the non-diversified picked funds.
- **[P1] News Penalty Monotonicity (`test_news_penalty.py`)**: For a given pair of funds $F_1, F_2$ where $Score(F_1) > Score(F_2)$, applying a negative news penalty only to $F_1$ should correctly invert their rank ordering if $Score(F_1) - Penalty < Score(F_2)$.
- **[P2] Horizon Averages (`test_horizon.py`)**: Generating arbitrary histories with identical returns across 1m, 3m, 6m, 1y should yield exactly the same return bucket value for `short`, `medium`, and `long` horizons.

## 5. Edge Cases Handled
The codebase gracefully accommodates various real-world anomalies.

**Currently Handled Edge Cases:**
- Empty DataFrames safely pass through all pipeline stages without `IndexError`.
- NaN or empty cells in the TEFAS/BEFAS CSV exports.
- Equal scoring funds.
- Negative scores (due to high risk penalties and/or bad news penalty) being mapped to valid display weights (minimum floor 5%).
- High $N$ configuration (e.g. $N > 20$) automatically truncating or safely allocating base percentage units.
- Tavily rate limits, JSON decoding errors, or timeouts.

**Suggested Additional Edge Cases (P1 - Edge Case Hardening):**
- **[P1] All-NaN Returns:** Test when an entire column (like `aum_last` or `applied_management_fee_pct`) is missing or filled with NaN for the entire dataset. Normalization mechanisms should handle global zero-variance.
- **[P2] Zero valid candidates:** Behavior when the filtering (e.g. long horizon restrictions on young funds) drops the candidate pool entirely. The weights algorithm must return a clean, empty result.
- **[P2] Extreme Outliers:** Fund returns going negative by > 100% or exploding to +10,000%. Verify that MinMax scaling limits bounds properly and doesn't squash the rest of the funds to identically 0 score.
