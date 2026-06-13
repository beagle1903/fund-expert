# Business Logic Review: fundexpert

## Overview
A deep dive into the core business logic of the `fundexpert` codebase (data ingestion, scoring, capping, news penalty, and weights). The logic largely matches the domain constraints correctly, applying rigorous sector/strategy caps and handling news parsing effectively. However, there are a few edge cases and bugs that require attention.

---

## P1 (Critical/High Impact)

### 1. Missing Risk Value Causes History Save Crash
**Location:** `fundexpert/history/store.py:36` (`save_run`)
**Issue:** If a fund has a missing `risk` value (NaN), `score.py` safely falls back to a penalty corresponding to risk level 7.0, meaning the fund can still be selected if its returns are stellar enough or if the requested risk level is "high". However, `history/store.py` attempts to cast the risk value directly to `int`: 
```python
"risk": int(r["risk"]),
```
When `r["risk"]` is NaN, this throws `ValueError: cannot convert float NaN to integer` and completely crashes the pipeline during the save process. 
**Fix:** Check for NaN before casting, similar to how it is handled in `render/table.py`:
```python
"risk": int(r["risk"]) if pd.notna(r["risk"]) else None
```

---

## P2 (Edge Cases & Medium Impact)

### 1. Invariant Violation on N > 20
**Location:** `fundexpert/select/weights.py:23` (`compute_weights`)
**Issue:** The project rules state: *"every selected fund gets >=5%, sum = 100."* 
While the interactive CLI caps `N` to 20, a programmatic call (or Agent shell script) might pass `n=21` or more. The fallback code handles this by calculating:
```python
units_each = (100 // 5) // n  # 20 // 21 = 0
```
This distributes `0` base units to all funds, then uses `leftover` to give `5%` to the top 20 funds. The 21st fund will end up with a weight of `0%`, violating the `>=5%` invariant and keeping a zero-weighted fund in the selected output.
**Fix:** Either explicitly enforce `n <= 20` inside `pick_top()` / `run_pipeline()`, or raise an explicit `ValueError` in `compute_weights` when `n * WEIGHT_STEP_PCT > 100` instead of a silent `0%` assignment.

### 2. Strict Exclusions on "Long" Horizon
**Location:** `fundexpert/scoring/horizon.py:14` (`apply_horizon`)
**Issue:** `df[cols].mean(axis=1, skipna=False)` enforces absolute completeness. For the `long` horizon, it requires both `ret_3y` and `ret_5y`. If a fund is 4.5 years old, it has a 3-year return but is missing the 5-year return. With `skipna=False`, its mean return becomes `NaN` and the fund is completely excluded. 
While tests indicate this is intended for data completeness, dropping a well-performing 4-year-old fund entirely when calculating a long horizon might be overly strict for business logic.
**Fix:** Confirm if this strictness is fully intended. If partial long-term data is acceptable, `skipna=True` could be used, or a weighted imputation could be considered.

### 3. Overlapping Strategy and Sector Rules
**Location:** `fundexpert/select/strategy.py` & `fundexpert/select/sector.py`
**Issue:** The keywords `"ALTIN"` and `"KIYMETLİ MADEN"` exist in both `_BUCKET_RULES` (strategy) and `_SECTOR_RULES` (sector). 
Because strategy and sector caps are independent, a fund named `"ALTIN FONU"` will hit both the `precious_metals` strategy cap and the `precious_metals` sector cap. Functionally this works fine without crashing, but it effectively counts precious metals against both diversity budgets unnecessarily.
**Fix:** Consider removing `"ALTIN"` and `"KIYMETLİ MADEN"` from `_SECTOR_RULES` and letting them fall back to the `"diversified"` sector, since their concentration is already constrained by the strategy cap.

---

## P3 (Minor Notes & Observations)

- **Tavily `days` Argument in News Search:** `tavily.py` passes the `days: max_age_days` payload directly. While Tavily generally expects this for advanced search, testing shows this works fine with `search_depth="basic"`. 
- **Graceful Fail-Soft:** The `apply_negative_news_penalty` correctly acts as a fail-soft boundary. Missing API keys, network timeouts, and JSON parsing errors correctly return `[]` and allow the purely quant-driven portfolio to survive.
- **UTF-8 BOM Bypass:** `loader.py` reads with `encoding="utf-8"`, but because `skiprows=3` drops the first three metadata rows, it elegantly avoids the `utf-8-sig` BOM header parsing bug on the header row.
