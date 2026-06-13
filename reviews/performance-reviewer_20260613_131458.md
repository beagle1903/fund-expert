# Performance Review: Fund Expert

## Executive Summary
Overall, the `fundexpert` pipeline is remarkably well-optimized for its scale. Heavy string matching (for sectors and strategies) is implemented properly without slow loops. Network operations for the optional Tavily news pass are correctly parallelized using `ThreadPoolExecutor`, and API queries are smartly deduplicated by `company_prefix` to minimize delays. 

However, the primary bottleneck in the application is the **Interactive CLI Startup Delay**, heavily driven by eager imports of large data science libraries (`pandera` and `pandas`) before user input is even requested.

Below are the key findings categorized by severity (P0/P1/P2).

---

## Findings

### 🔴 P0 - CLI Startup Delay Due to Eager Imports (UX Bottleneck)
**Location:** `fundexpert/cli.py`, `fundexpert/data/merge.py`
**Description:** 
When the user runs `fundexpert`, there is an approximate **1.3s to 2.5s delay** before the first interactive `questionary` prompt appears. This is a severe UX friction point for a command-line tool.
**Root Cause:**
`fundexpert/cli.py` performs top-level imports of heavy libraries (`pandas`, `pandera`, `rich`). `pandera` alone takes ~1.5 to 2.2 seconds to initialize because of its heavy dependency tree (`pydantic`, `typeguard`, etc.). This blocks the interactive UI from launching immediately.
**Actionable Recommendation:** 
1. **Defer CLI Imports:** Move all pipeline-related imports (like `from fundexpert.data.loader import ...`, `import pandas as pd`, `from fundexpert.pipeline import run_pipeline`) into `main()` **after** `prompt_user(last)` has finished gathering user input.
2. **Lazy Import Pandera:** In `fundexpert/data/merge.py`, move `import pandera as pa` inside the `merge_universe` function, or consider dropping `pandera` entirely in favor of lightweight pandas assertion checks if production speed is paramount.

### 🟠 P1 - Pandera Validation Runtime Overhead
**Location:** `fundexpert/data/merge.py`
**Description:** 
DataFrame validation is executed unconditionally every time data is loaded.
**Root Cause:** 
`merge_universe` returns `MergedUniverseSchema.validate(df)`. While extremely safe and beneficial for testing, the runtime performance overhead of executing these validation checks is non-negligible for a fast-executing CLI tool (adding ~150-200ms compared to ~30ms for standard `pd.read_csv`). 
**Actionable Recommendation:** 
Disable pandera validation in standard production runs (e.g. bypass it via an environment variable or a configuration flag), restricting it only to `--debug` or test suites. Alternatively, replace it with lightweight native pandas `.dtypes` coercion.

### 🟡 P2 - Python-level Loop for String Normalization
**Location:** `fundexpert/pipeline.py`
**Description:** 
List comprehensions are used for string normalization over the entire candidate pool.
```python
scored_fon_adi_upper = pd.Series(
    [turkish_upper(s) for s in scored["fon_adi"].fillna("")],
    index=scored.index
)
```
**Root Cause:** 
The pipeline invokes the custom `turkish_upper` function via list comprehension on every candidate fund (~400 funds). While Python list comprehensions are fast for datasets of this size (< 5ms), it scales poorly.
**Actionable Recommendation:** 
Refactor this to use vectorized Pandas string operations if the fund universe size grows significantly. For the current dataset size, it is an acceptable micro-bottleneck, but best-practice dictates utilizing `.str` accessors.

---

## What is Working Well 🟢
The codebase shines in several key areas where performance pitfalls were successfully avoided:

1. **Parallel Network I/O:** 
   The `news/penalty.py` module elegantly limits queries to only the `top_k` funds. More impressively, it maps candidate funds to their `company_prefix` and uses a `concurrent.futures.ThreadPoolExecutor(max_workers=10)` to parallelize the external HTTP requests to Tavily.
2. **API Call Deduplication:** 
   Multiple funds originating from the same issuer (e.g. 5 different funds starting with "AK PORTFÖY") are mapped to a single prefix. Only **one** network query is made for the entire prefix, drastically reducing both latency and API costs. Local JSON caching prevents repeat network traffic completely.
3. **Fast Iteration in Selection:** 
   `pick_top` heavily leverages Python's native `zip()` for iteration over columns, outright avoiding notoriously slow `DataFrame.iterrows()`. This keeps the sector and strategy cap-enforcement logic extremely lightweight and rapid.
