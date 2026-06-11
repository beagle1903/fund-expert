# Parallel Code Review Summary

This document synthesizes the findings of 5 specialized subagents (`security-reviewer`, `architecture-reviewer`, `test-coverage-reviewer`, `performance-reviewer`, and `business-logic-reviewer`) that ran in parallel against the `fundexpert` codebase.

The findings are prioritized below (P0, P1, P2) along with suggested fixes formatted as actionable prompts for an AI agent.

---

## 🔴 P0 (Critical / Blocker)

### 1. Failing Tests in News Module
- **Context:** 4 tests are failing in `tests/test_news_tavily.py` due to recent updates in client-side filtering logic. The mocks don't include the required keywords.
- **Agent Prompt:** Update the mock payloads in `tests/test_news_tavily.py`. For each failing test, ensure that the mocked JSON payload's `title` or `content` includes the keyword being queried (e.g., "ceza" or "soruşturma"). Ensure all 4 failing tests pass successfully.

### 2. Sequential Network I/O
- **Context:** In `fundexpert/news/penalty.py`, `apply_negative_news_penalty()` iterates over top-K candidates and issues synchronous HTTP requests sequentially, causing massive CLI slowdowns.
- **Agent Prompt:** Refactor `apply_negative_news_penalty` in `fundexpert/news/penalty.py` to use `concurrent.futures.ThreadPoolExecutor`. Instead of sequentially calling `query_negative_news` in a for-loop, submit the tasks to a thread pool and gather the results asynchronously. Ensure to associate the hits correctly with the fund indices.

---

## 🟠 P1 (High / Important)

### 3. Outlier Susceptibility in Scoring Normalization
- **Context:** The `minmax_normalize` function in `scoring/normalize.py` uses strict max/min values, meaning a single extreme financial outlier (e.g., massive AUM growth) squeezes scores for all other funds to near zero.
- **Agent Prompt:** Update `minmax_normalize` in `scoring/normalize.py` to use robust scaling. Calculate the 1st and 99th percentiles of the `finite` series. Use these percentiles as `lo` and `hi`. After applying the scaling formula, add a `.clip(0, 1)` step.

### 4. Turkish Casing Breaks Negative News Filter
- **Context:** In `news/tavily.py`, client-side validation uses standard Python `.lower()` which incorrectly maps the Turkish uppercase letters `İ` and `I`. Valid negative news hits (like "İFLAS") evaluate to `False` and are dropped.
- **Agent Prompt:** Fix the Turkish string case-conversion in `_post_tavily` within `news/tavily.py`. Before calling `.lower()` on `(title + ' ' + content)`, explicitly map the problematic characters by applying `.replace('I', 'ı').replace('İ', 'i')`.

### 5. Insecure Directory Permissions
- **Context:** Directories like `~/.fundexpert` (which cache sensitive user choices and history) are created with default system umask, exposing them on multi-user systems.
- **Agent Prompt:** Update the application's file and directory creation logic to use strict permissions. Modify the `mkdir()` calls in `fundexpert/cli.py`, `fundexpert/history/store.py`, and `fundexpert/news/tavily.py` to include `mode=0o700`.

### 6. Tight Orchestration Coupling in CLI
- **Context:** The orchestration logic in `fundexpert/cli.py` directly handles local disk I/O through `_load_one`, severely limiting testability without patching the filesystem.
- **Agent Prompt:** Refactor the core pipeline out of `fundexpert/cli.py` into a new module `fundexpert/pipeline.py`. Modify the `run_pipeline` signature to accept a `pd.DataFrame` of candidates instead of a `universe` string, fully decoupling it from disk I/O.

### 7. Inefficient CSV Parsing
- **Context:** In `fundexpert/data/loader.py`, `pd.read_csv` pulls in all columns before dropping unneeded ones, leading to high memory peaks.
- **Agent Prompt:** Optimize `_read_one` in `fundexpert/data/loader.py` by adding `usecols=lambda c: c in rename.keys()` to the `pd.read_csv` call.

### 8. Missing Test Coverage for Core Logic Edge Cases
- **Context:** Core pipeline files like `weights.py`, `sector.py`, `strategy.py`, and `normalize.py` have critical edge cases uncovered by tests.
- **Agent Prompt:** Add tests to `tests/` to cover: `compute_weights` with an empty DataFrame and N > 20 fallback; `sector_from_name` and `bucket_from_name` passing empty/whitespace strings; and `minmax_normalize` processing an all-NaN Series.

---

## 🟡 P2 (Medium / Low)

### 9. Missing Risk Values Propagate NaNs
- **Context:** In `scoring/score.py`, missing `risk` SRRI values evaluate to `NaN`, poisoning the score column and occasionally crashing downstream portfolio generation in `weights.py`.
- **Agent Prompt:** In `score_candidates` within `scoring/score.py`, safely impute missing `risk` values with `.fillna(7.0)` on `out['risk']` before converting to float to give them a maximum penalty.

### 10. Weight Calculation Fallback Exceeds 100%
- **Context:** The fallback condition in `weights.py` calculates `units_each = max(1, (100 // 5) // n)`. For `n > 20`, it assigns 5% to each fund, silently summing to >100%.
- **Agent Prompt:** Update the fallback block in `compute_weights` in `select/weights.py` to raise a `ValueError` if `n * _STEP > 100`, rather than allowing mathematically invalid portfolios.

### 11. Terminal Markup Injection
- **Context:** Untrusted external strings (Tavily API, TEFAS CSV) are passed to `rich` unescaped, allowing malicious actors to inject formatted terminal markup or clickable phishing links.
- **Agent Prompt:** In `fundexpert/render/table.py` and `fundexpert/render/diff.py`, import `escape` from `rich.markup` and wrap all untrusted string interpolations before passing them to `console.print()` or adding to the table.

### 12. Counterfactual Logic Mixed in Core Pipeline
- **Context:** Counterfactual "displaced" logic is inlined directly inside `run_pipeline` within `cli.py`, cluttering the main flow.
- **Agent Prompt:** Extract the counterfactual 'displaced' logic from `fundexpert/cli.py:run_pipeline` into a standalone helper function `compute_displaced_funds` inside `fundexpert/news/penalty.py`.

### 13. Unpinned Dependencies (Supply Chain Risk)
- **Context:** `pyproject.toml` lacks a lockfile mechanism to strictly pin transitive dependencies.
- **Agent Prompt:** Introduce a lockfile mechanism to the project. Add a step to generate a strict `requirements.txt` using `pip-compile`, or migrate dependency management to `uv` or `Poetry`.

### 14. Inefficient Pandas Iteration
- **Context:** `pick_top` uses `.iterrows()`, which creates series copies and adds major overhead.
- **Agent Prompt:** Refactor `pick_top` in `fundexpert/select/pick.py` to use `sorted_df.itertuples()` instead of `iterrows()`.

### 15. Sequential Index Updates
- **Context:** `compute_weights` iterates through indices using a python loop instead of vectorization.
- **Agent Prompt:** Update `compute_weights` in `fundexpert/select/weights.py` to use vectorized assignment (e.g., `units.loc[winners] += 1`) instead of `for idx in ...` loops.

### 16. Missing UI Test Coverage
- **Context:** Minor edge cases in UI rendering (`table.py`, `diff.py`) and CLI caching aren't covered by tests.
- **Agent Prompt:** Add tests covering the "Sektör" column rendering in `table.py`, default `Console()` fallback in `diff.py`, and exception handling for `last.json` load/write failures in `cli.py`.
