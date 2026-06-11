# Test Coverage and Quality Review

## Executive Summary

The `fundexpert` project has a high overall coverage (92%), but the test suite currently contains **4 failing tests** related to the negative news pass (`tavily.py`). In addition, some critical edge cases in the scoring, weighting, and selection logic are currently untested. 

This review categorizes findings into P0 (Critical/Blocker), P1 (High/Important), and P2 (Medium/Low).

---

## P0: Failing Tests in `test_news_tavily.py`

### Context
When running the test suite, 4 tests fail in `tests/test_news_tavily.py`:
- `test_query_returns_parsed_hits_on_success`
- `test_query_skips_results_missing_title_or_url`
- `test_query_filters_excluded_domain_substrings`
- `test_excluded_substrings_match_case_insensitive`

These tests fail because of a mismatch between the test mocks and the client-side validation logic introduced in `fundexpert/news/tavily.py` (lines 179-182). The production code checks if the search results actually contain at least one of the queried `keywords` (e.g., "ceza", "soruşturma") in their title or content. The test mock payloads are missing these keywords, causing the valid results to be silently dropped and leading to assertion errors.

### Suggested Fix (Actionable Prompt for AI Agent)
> Update the mock payloads in `tests/test_news_tavily.py`. For each failing test, ensure that the mocked JSON payload's `title` or `content` includes the keyword being queried (e.g., "ceza" or "soruşturma"). For example, in `test_query_returns_parsed_hits_on_success`, add "soruşturma" to the title or content of the second mock result. Ensure all 4 failing tests pass successfully.

---

## P1: Missing Coverage for Edge Cases in Core Pipeline

### 1. Missing Coverage in `select/weights.py`
**Context:** Lines 20-21 (when `len(out) == 0`) and lines 25-32 (fallback logic when `n * _STEP > 100`) are completely untested. While the CLI caps `N` at 20 (making the latter case unreachable through the normal CLI), the pipeline functions are exposed and could be called programmatically.
**File Reference:** `fundexpert/select/weights.py`

**Suggested Fix (Actionable Prompt for AI Agent)**
> Add two tests to `tests/test_weights.py` to cover `compute_weights` edge cases. First, pass an empty Pandas DataFrame and assert that it returns an empty DataFrame with the `display_weight_pct` column without errors. Second, create a mock DataFrame with 21 or more rows (where N > 20) and assert that it gracefully falls back to equal weighting and distributes leftovers without exceeding a total sum of 100%.

### 2. Missing Coverage for Empty Strings in Sector and Strategy Selection
**Context:** The helper functions `sector_from_name` (`fundexpert/select/sector.py`, line 53) and `bucket_from_name` (`fundexpert/select/strategy.py`, line 38) contain defensive checks for empty strings after stripping whitespace (`if not stripped:`). These branches are currently not covered by any test.
**File Reference:** `fundexpert/select/sector.py`, `fundexpert/select/strategy.py`

**Suggested Fix (Actionable Prompt for AI Agent)**
> In the relevant test files (e.g., `tests/test_select_sector.py` and `tests/test_select_strategy.py`), add test cases that pass whitespace strings (e.g., `"   "`) to `sector_from_name` and `bucket_from_name`. Assert that they return the default fallbacks `"diversified"` and `"other"`, respectively.

### 3. Missing Coverage for All-NaN Series in Normalization
**Context:** The `minmax_normalize` function correctly identifies when a Series contains only `NaN` values and defaults to neutral scores (`0.5`), but line 15 `return pd.Series([0.5] * len(s), index=s.index)` is never hit by tests.
**File Reference:** `fundexpert/scoring/normalize.py`

**Suggested Fix (Actionable Prompt for AI Agent)**
> Add a test case in `tests/test_scoring.py` for `minmax_normalize`. Pass a Pandas Series containing exclusively `NaN` values, and assert that the returned Series contains only `0.5`s while maintaining the original index.

---

## P2: Missing Coverage in Presentation & CLI Logic

### 1. Rendering Sectors in `render_portfolio`
**Context:** In `fundexpert/render/table.py`, lines 72, 92, and 102 add the "Sektör" column to the Rich table. These lines are only executed if `show_sector` is true (i.e., the `sector` column exists and contains at least one non-"diversified" value). Currently, no test provides this condition.
**File Reference:** `fundexpert/render/table.py`

**Suggested Fix (Actionable Prompt for AI Agent)**
> In `tests/test_render_table.py` (or equivalent), add a test that calls `render_portfolio` with a `selected` DataFrame containing a `sector` column with at least one value set to `"tech"` or another non-default sector. Assert that the rendered output (captured via `capsys` or Rich's mock console) includes the "Sektör" column header.

### 2. Default Console in `render_diff`
**Context:** Line 21 in `fundexpert/render/diff.py` instantiates a `Console()` if none is injected. Test cases likely inject a mock console, missing this branch.
**File Reference:** `fundexpert/render/diff.py`

**Suggested Fix (Actionable Prompt for AI Agent)**
> Add a test in `tests/test_render_diff.py` that calls `render_diff` without passing a `console` argument, relying on the default instantiation. Assert that it runs without errors.

### 3. Exception Handling in CLI Cache Reads/Writes
**Context:** In `fundexpert/cli.py`, multiple `try...except` blocks exist for managing `~/.fundexpert/last.json` (lines 209-210, 217-218) and configuring stdio encoding (lines 286-287). These paths represent graceful fallbacks and aren't covered by tests.
**File Reference:** `fundexpert/cli.py`

**Suggested Fix (Actionable Prompt for AI Agent)**
> In `tests/test_cli.py`, write tests that use `unittest.mock.patch` to simulate `json.loads` raising a `JSONDecodeError`, or `LAST_RUN_FILE.write_text` raising an `OSError`. Assert that the CLI handles these smoothly and falls back to default prompt configurations without crashing.
