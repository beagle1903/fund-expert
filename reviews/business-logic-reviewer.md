# Business Logic Review: fundexpert

## Overview
I have conducted a deep review of the `fundexpert` codebase focusing on the correctness of its core domain logic: Turkish investment-fund portfolio selection, scoring, capping, and the negative-news penalty module.

The system is highly robust. The pipeline is thoughtfully constructed with defense-in-depth measures protecting against data anomalies, edge cases in the Turkish locale, and search API hallucinations.

## Findings

### 1. Scoring & Normalization (P0 - Flawless)
- **Min-Max Normalization (`scoring/normalize.py`)**: Safely handles outliers by clipping at the 1st and 99th percentiles, ensuring extreme values do not distort the `[0, 1]` scale. Constant inputs are gracefully degraded to a neutral `0.5` score.
- **Risk Penalty (`scoring/score.py`)**: The SRRI penalty scales quadratically `lam * ((risk - 1)/6)²`. This perfectly maps SRRI `1–7` to a `[0, 1]` curve, harshly penalizing high risk when the user sets a "low" risk tolerance (`lam=0.60`) while nearly ignoring it for "high" (`lam=0.05`). A missing risk level conservatively falls back to `7.0`.
- **Weighting Coefficients**: Setting the base return weight to `1.0` and scaling volume and fee weights between `[0.10, 0.60]` ensures that historical returns act as the primary driver, while volume and fees serve as meaningful secondary tie-breakers.

### 2. Diversification Caps (P0 - Flawless)
- **Sector and Strategy Mapping (`select/sector.py`, `select/strategy.py`)**: The strategy and sector mappings apply strict `first-match` substring logic, allowing granular control without relying on the overly broad TEFAS umbrella types. Extracting themes directly from the `fon_adi` string is the correct approach.
- **Turkish Case Normalization**: The pipeline correctly mirrors the `turkish_upper` rules (`i -> İ`, `ı -> I`) inline via Pandas string replacements before mapping names to buckets, averting locale-blind matching failures.
- **Exemptions (`select/pick.py`)**: The `diversified` sector is deliberately exempt from the sector cap. The logic correctly tracks counts but deliberately bypasses the `continue` drop condition. The dual-cap (max per strategy AND max per sector) solves the vulnerability where multiple themed funds (e.g., 5 tech funds) could saturate the portfolio if they had different umbrella strategies.

### 3. Horizon Buckets (P1 - Contextual Observation)
- **Strict NaN Dropping (`scoring/horizon.py`)**: `skipna=False` intentionally excludes a fund if it lacks *any* return in the selected horizon bucket. For example, a 9-month-old fund will be dropped from the "medium" horizon because it lacks `ret_1y`. This is correct financial logic: funds must possess a verifiable track record across the entirety of the chosen horizon.
- **YTD Volatility (`config.py`)**: The `medium` horizon bucket averages `ret_6m`, `ret_ytd`, and `ret_1y`. Note that the Year-To-Date (`ret_ytd`) metric's duration varies wildly depending on the calendar month (i.e., a 1-month return in February vs. an 11-month return in December). While averaging smooths this, users running the tool early in the year will have the `medium` bucket skewed slightly more toward short-term momentum. Given typical TEFAS usage, this is acceptable but worth acknowledging.

### 4. News Penalty Module (P0 - Flawless)
- **Prefix Extraction (`news/match.py`)**: Reliably trims the fund name to isolate the portfolio management company (e.g., `AK PORTFÖY`), allowing the search query to focus on the actual corporate entity rather than the esoteric fund name.
- **Query Bounding & Parallelism (`news/penalty.py`)**: The system smartly limits the expensive API calls to `3 * N` candidates rather than querying the entire 1000+ universe. By bucketing funds by their company prefix before submitting parallel requests, the system prevents duplicate queries for sister funds managed by the same company.
- **Defense-In-Depth Validation (`news/tavily.py`)**:
    - **Server-Side Trust**: Forwarding the curated `NEWS_DOMAIN_ALLOWLIST` blocks spam, forums, and unrelated social media platforms natively at the search provider level.
    - **Client-Side Exclusion**: Filtering out URLs containing `"portfoy"` or `"portföy"` cleanly neutralizes publisher bias by issuer-owned domains.
    - **Anti-Hallucination**: Extracting and re-validating the presence of negative keywords against `turkish_lower(title + " " + content)` acts as an excellent safeguard against the search API returning irrelevant results.

### 5. Final Weighting Mathematics (P0 - Flawless)
- **Largest-Remainder Method (`select/weights.py`)**: Distributing the 100% total allocation into 5% increment units using the largest-remainder method guarantees precision without fractional shares, summing perfectly to 100%. Providing a 5% baseline ensures no selected fund sits in the portfolio trivially.

## Summary
The business logic implementation in `fundexpert` is highly accurate, logically cohesive, and resilient against anomalies. All constraints specified in the prompt/domain rules are faithfully satisfied. No critical bugs or misalignments were found in the core algorithms.
