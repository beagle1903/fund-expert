# Performance Review — 2026-06-12

## Executive Summary
Overall, the `fundexpert` pipeline is well-structured and uses vectorized operations for mathematical calculations (e.g., largest-remainder weight distributions). However, there are significant bottlenecks and safety risks in the network and file I/O layers (Tavily search API integration), as well as inefficiencies in how pandas string manipulations and iterators are used across the selection layer. Addressing these will improve both the single-run latency and robustness under concurrent execution.

## Findings

### [P0] Network Cache Stampede & Data Corruption Risk
- **File(s)**: `fundexpert/news/penalty.py` (lines 93-100), `fundexpert/news/tavily.py` (lines 122-142, 225-247)
- **Issue**: The `ThreadPoolExecutor` launches concurrent tasks for the top-K funds to fetch negative news. Because different funds can share the same portfolio management company prefix (e.g., multiple "AK PORTFÖY" funds), multiple threads can generate the exact same search query and cache key. These threads simultaneously read the empty cache, issue redundant API calls to Tavily, and then blindly write to the same JSON cache file simultaneously, leading to cache stampedes, wasted network quotas, and file corruption.
- **Impact**: Severe. Redundant API calls slow down the pipeline and waste Tavily API credits. Concurrent non-atomic file writes can corrupt the JSON cache, causing `JSONDecodeError`s on future runs.
- **Recommendation**: Deduplicate by `company_prefix` *before* submitting tasks to the ThreadPoolExecutor. Execute exactly one query per unique prefix, then map the hits back to all funds sharing that prefix. Additionally, make the disk cache write in `_write_cache` atomic using a temporary file and `os.replace`.
- **Agent Prompt**: "Refactor `apply_negative_news_penalty` to extract a set of unique `company_prefix` values from the top-K candidates. Map these unique prefixes to the ThreadPoolExecutor instead of querying per-fund. After queries complete, broadcast the results back to the respective funds. Additionally, modify `_write_cache` in `news/tavily.py` to write JSON to a `.tmp` file and rename it atomically."

### [P1] DataFrame Iteration Bottleneck in Selection Algorithm
- **File(s)**: `fundexpert/select/pick.py` (lines 29-41)
- **Issue**: The `pick_top` algorithm iterates through the pre-sorted candidate DataFrame using `sorted_df.iterrows()`. Although the loop breaks after `N` funds are picked, the iteration itself constructs a pandas `Series` for every visited row. In worst-case scenarios where early candidates breach type/sector caps, it iterates through many rows, incurring a heavy type-boxing penalty.
- **Impact**: Significant CPU overhead and latency. `iterrows()` is notoriously slow in pandas.
- **Recommendation**: Replace `iterrows()` with `itertuples(index=True)` or convert the relevant columns into a list of dictionaries before iterating.
- **Agent Prompt**: "Replace `sorted_df.iterrows()` in `fundexpert/select/pick.py` with `sorted_df.itertuples(index=True, name='Row')` and adjust column accesses to avoid the pandas Series allocation overhead of iterrows."

### [P1] Redundant and Unvectorized Turkish String Manipulations
- **File(s)**: `fundexpert/pipeline.py` (lines 74-77), `fundexpert/select/strategy.py` (lines 39-41), `fundexpert/select/sector.py` (lines 54-55)
- **Issue**: The `bucket_from_name` and `sector_from_name` functions perform manual Python-side string manipulations (`.replace("i", "İ").replace("ı", "I").upper()`) on every fund name. In `pipeline.py`, these functions are applied via `.map()` twice per row (once for strategy, once for sector), meaning the exact same string allocations are performed twice for all ~1000 funds.
- **Impact**: High memory allocation overhead and slower mapping across the candidate universe.
- **Recommendation**: Vectorize the uppercase Turkish transformation in `pipeline.py` using pandas string accessors and pass the pre-transformed strings to the selection modules.
- **Agent Prompt**: "In `pipeline.py`, pre-compute a Turkish-uppercased Series of `fon_adi` using vectorized `.str.replace` and `.str.upper`. Refactor `bucket_from_name` and `sector_from_name` to accept these pre-uppercased strings so we don't repeat the string transformation operations per row per column."

### [P2] Dead Code: Unused Dictionary Allocations in Scoring
- **File(s)**: `fundexpert/scoring/score.py` (lines 43-53)
- **Issue**: The `score_candidates` function constructs a `_breakdown` list via a large list comprehension containing dictionaries with individual score contributions for every single candidate. This `_breakdown` column is entirely unused downstream (neither rendered, persisted, nor evaluated).
- **Impact**: Minor memory bloat and CPU waste creating ~1000 dictionaries per run that are promptly discarded.
- **Recommendation**: Remove the `_breakdown` calculation completely.
- **Agent Prompt**: "Remove the `_breakdown` column assignment and its list comprehension from `fundexpert/scoring/score.py` as it constitutes unused dead code."

### [P2] CSV Loader Engine Optimization
- **File(s)**: `fundexpert/data/loader.py` (lines 45-54)
- **Issue**: The `_read_one` function uses the default pandas C engine to parse the TEFAS/BEFAS CSV exports.
- **Impact**: While not a strict bottleneck for datasets of ~1000 rows, using pyarrow is computationally more efficient and uses less memory.
- **Recommendation**: Switch the backend to `engine="pyarrow"` (ensuring it plays well with `decimal=","` and `thousands=None`).
- **Agent Prompt**: "Update `_read_one` in `fundexpert/data/loader.py` to specify `engine='pyarrow'` in `pd.read_csv`, provided it supports the specified decimal and thousands settings safely."
