# Business Logic Review

## Summary
The core domain logic of `fundexpert` is well-structured and properly encapsulates the data merging, scoring, filtering, and news-penalty pipelines. However, there are a few critical flaws in the scoring normalization, string-handling for Turkish keyword matching, and edge-case handling for missing data and weight constraints.

Below are the prioritized findings and actionable prompts for fixing them.

---

## Findings

### 1. P1 (Critical) - Scoring algorithm lacks outlier robustness, leading to squeezed normalization
**Context:**  
In `fundexpert/scoring/normalize.py`, the `minmax_normalize` function scales columns (`R`, `aum_change_pct`, `applied_management_fee_pct`) using strict minimum and maximum values `(s - lo) / (hi - lo)`. Financial data frequently contains extreme outliers (e.g., a newly established micro-fund showing a 99,000% AUM growth, or an outlier 1000% return). A single extreme outlier will cause the `hi` boundary to explode, squeezing the normalized scores of all regular funds into an indistinguishable, near-zero range. This renders the `V_contrib` or `R_contrib` signals meaningless and arbitrarily distorts the final rankings.

**File:** `fundexpert/scoring/normalize.py`

**Suggested Fix / Prompt:**
> Update `minmax_normalize` in `scoring/normalize.py` to use robust scaling. Before calculating `lo` and `hi`, calculate the 1st and 99th percentiles of the `finite` series (e.g., using `.quantile(0.01)` and `.quantile(0.99)`). Use these percentiles as `lo` and `hi`. After applying the scaling formula, add a `.clip(0, 1)` step so that the outliers themselves are safely capped at 0 and 1, preserving the scoring distribution for the rest of the funds.


### 2. P1 (Critical) - Turkish character casing completely breaks client-side negative news filtering
**Context:**  
In `fundexpert/news/tavily.py`, the `_post_tavily` function validates whether the returned articles actually contain the requested negative keywords using `text_to_check = (title + " " + content).lower()`. Python's native `.lower()` does not correctly handle the Turkish characters `İ` and `I`. For example, `"İFLAS".lower()` becomes `"i\u0307flas"`, and `"DOLANDIRICILIK".lower()` becomes `"dolandiricilik"`. Because the target `keywords` list uses correct Turkish lowercase (`"iflas"`, `"dolandırıcılık"`), the `in` check will evaluate to `False` for any valid uppercase hits. This silently drops highly relevant negative news articles.

**File:** `fundexpert/news/tavily.py`

**Suggested Fix / Prompt:**
> Fix the Turkish string case-conversion in `_post_tavily` within `news/tavily.py`. Before calling `.lower()` on `(title + ' ' + content)`, explicitly map the problematic characters by applying `.replace("I", "ı").replace("İ", "i")`. This ensures that uppercase Turkish text properly matches the lowercase target keywords during the client-side validation check.


### 3. P2 (Medium) - Missing risk values propagate `NaN` scores and can crash portfolio calculations
**Context:**  
In `fundexpert/scoring/score.py`, the risk penalty is calculated as `risk_norm = (out["risk"].astype(float) - 1.0) / 6.0`. If a fund is missing its SRRI risk rating (e.g. data anomaly where risk is empty or `NaN`), `risk_norm` evaluates to `NaN`. This turns the entire `score` column for that fund into `NaN`. While the sorting mechanism pushes `NaN`s to the bottom, if the candidate pool is small enough, these funds may still be selected. If a `NaN` score reaches `select/weights.py`, the proportion math (`scores / scores.sum()`) propagates the `NaN`, causing a crash (`IntCastingNaNError`) during the integer conversion step for leftover units.

**File:** `fundexpert/scoring/score.py`

**Suggested Fix / Prompt:**
> In `score_candidates` within `scoring/score.py`, safely impute missing `risk` values before converting them to float. Use `.fillna(7.0)` on `out["risk"]` so that funds with unknown risk levels receive the maximum possible penalty, preventing `NaN` propagation from breaking the downstream weight allocation.


### 4. P2 (Medium) - Weight calculation fallback breaks the strict 100% sum constraint for N > 20
**Context:**  
In `fundexpert/select/weights.py`, `compute_weights` distributes weights in strict 5% steps with a 5% minimum floor per fund. The algorithm has a fallback condition for when the requested `n` funds exceed the maximum possible distribution (e.g. `n * 5 > 100`). The fallback block calculates `units_each = max(1, (100 // 5) // n)`. For `n > 20`, this assigns exactly 5% to each fund, causing the total weight to exceed 100% (e.g. `n=25` yields 125%). While the CLI currently caps `n` at 20, as a core library function, it should not silently return an invalid portfolio mathematically violating the `sum == 100` business rule.

**File:** `fundexpert/select/weights.py`

**Suggested Fix / Prompt:**
> Update the fallback block in `compute_weights` in `select/weights.py`. Instead of allowing the calculation to return a sum greater than 100%, check if `n * _STEP > 100` and immediately raise a `ValueError` indicating that distributing 100% across more than 20 funds with a 5% floor is mathematically impossible.
