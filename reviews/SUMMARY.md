# Parallel Code Review Summary

This document synthesizes the findings from 5 parallel AI code reviewers: Architecture, Security, Test Coverage, Performance, and Business Logic. 

## P0: Critical Findings & Bugs

- **[Performance] Concurrent DataFrame Mutation**: Modifying a Pandas DataFrame from multiple threads concurrently (`news/penalty.py` using `ThreadPoolExecutor`) is thread-unsafe and can cause memory corruption.
  - **Agent Prompt**: `Fix the concurrent pandas dataframe mutation in news/penalty.py. Collect results inside the thread pool first, then apply updates sequentially or vectorized in the main thread.`
- **[Test/Performance] Missing `utils/text.py`**: The file was missing and broke imports (`tavily.py`), causing tests to fail. (Note: The test coverage agent recreated it during its review).

## P1: Major Issues & Bottlenecks

- **[Security] Missing URL Scheme Validation**: `news/tavily.py` uses `urllib.request.urlopen` without explicitly validating the URL scheme (allowing potentially unsafe `file://` scheme).
  - **Agent Prompt**: `Update news/tavily.py to enforce that URLs passed to urllib.request.urlopen strictly start with 'https://'.`
- **[Architecture] Leaky Text Normalization**: Turkish string capitalization happens inline in `pipeline.py`, while other modules assume it's already done.
  - **Agent Prompt**: `Extract the Turkish string normalization logic from pipeline.py into a reusable helper function in utils/text.py, and use that function consistently.`
- **[Performance] Pandas Anti-Patterns**: Sequential masking in `clean_candidates`, chained `.str` operations in `pipeline.py`, iterative `.loc` assignments inside loops in `select/weights.py`, and double quantile sorting in `scoring/normalize.py`.
  - **Agent Prompt**: `Optimize pandas performance across the codebase: combine boolean masks in data/merge.py, use list comprehensions for strings in pipeline.py, vectorize loc assignments in select/weights.py, and compute quantiles in a single pass in scoring/normalize.py.`

## P2: Minor Issues & Improvements

- **[Security] Swallowed Exception**: Generic `except Exception: pass` in `cli.py` history saving.
  - **Agent Prompt**: `Replace the bare except Exception: pass in cli.py with catching a specific IOError and logging it.`
- **[Test Coverage] Weak Assertions & Misleading Names**: The `test_lower_fee_scores_higher` test varies too many fields in its fixture. `test_long_horizon_takes_mean_when_one_nan` name is contradictory.
  - **Agent Prompt**: `Refactor tests/test_score.py test_lower_fee_scores_higher to strictly isolate fee variance. Rename test_long_horizon_takes_mean_when_one_nan in tests/test_horizon.py to reflect that it drops incomplete data.`
- **[Architecture] Pipeline Return Signature & CLI Decoupling**: Returning a bulky 4-tuple from `run_pipeline` makes the API fragile. `cli.py` has too many UI/state responsibilities.
  - **Agent Prompt**: `Refactor run_pipeline in pipeline.py to return a strongly typed PipelineResult dataclass instead of a tuple.`
- **[Performance] Minor Optimizations**: Double dataframe sorting in `pick_top` and inefficient globs for history.
  - **Agent Prompt**: `Pass an is_sorted=True flag to pick_top to avoid double sorting in pipeline.py, and optimize the glob loading in history/store.py.`
- **[Test Coverage] Strategic**: Expand Hypothesis property tests to numerical bounds validation.
  - **Agent Prompt**: `Add Hypothesis property-based testing to scoring/normalize.py to verify bounds and float precision.`

## Business Logic Health

- **Status**: Excellent.
- **Findings**: The core domain correctly implements the dual-axis capping (strategy & sector) constraints, min-max normalization, and largest-remainder weight allocation. No logical defects were found.
