# Architecture Review — 2026-06-12

## Executive Summary
The `fundexpert` architecture is structurally sound, clean, and follows a clear linear pipeline (`loader -> merge -> score -> select -> render`). Separation of concerns is largely well-respected. Some duplication exists around Turkish text handling, error logging in the API client, and candidate filtering boundaries. Addressing these will further improve maintainability, determinism, and extensibility. No critical (P0) architectural flaws were found.

## Findings

### [P1] Duplicated and Incomplete Turkish Text Normalization
- **File(s)**: `fundexpert/select/strategy.py:41`, `fundexpert/select/sector.py:55`, `fundexpert/news/match.py:37`, `fundexpert/news/tavily.py:180`
- **Issue**: Turkish string casing (`str.replace("i", "İ").replace("ı", "I").upper()` or its reverse) is duplicated across four modules. Furthermore, using this pattern misses standard lower-to-upper conversions for other Turkish characters when custom casing libraries aren't used, and duplicating it is a DRY violation that makes adding broader Turkish mapping harder in the future.
- **Impact**: Increased maintenance overhead and potential inconsistencies in how fund names and news contents are searched or mapped to buckets.
- **Recommendation**: Introduce a central `fundexpert.utils.text` module with `turkish_upper(s)` and `turkish_lower(s)` functions. Replace all scattered string replacement chains with these helpers.
- **Agent Prompt**: "Create a new module `fundexpert/utils/text.py` containing `turkish_upper` and `turkish_lower` helper functions. Refactor `strategy.py`, `sector.py`, `match.py`, and `tavily.py` to use these centralized helpers instead of raw string `.replace()` chains."

### [P1] Tightly Coupled Exception Handling in API Client
- **File(s)**: `fundexpert/news/tavily.py:239-242`
- **Issue**: The `query_negative_news` function traps network exceptions and outputs a warning via `print(..., file=sys.stderr)`. 
- **Impact**: This tightly couples a low-level data-fetching module to standard error output. If this module is ever used by a GUI or another library component, console side-effects cannot be cleanly suppressed or redirected.
- **Recommendation**: Replace `sys.stderr` printing with standard Python logging (a `logger` instance is already defined at line 29) or bubble up a structured warning.
- **Agent Prompt**: "In `fundexpert/news/tavily.py`, replace the `print(..., file=sys.stderr)` call in `query_negative_news` with `logger.warning(...)` to decouple console output from the API fetching logic."

### [P2] Missing Deterministic Tie-Breaking in Selection
- **File(s)**: `fundexpert/select/pick.py:22`
- **Issue**: `scored.sort_values("score", ascending=False)` does not provide a secondary sort key. If two funds receive identical scores (e.g., both receive neutral values), they tie, and `pandas` uses stable sorting based on the input index.
- **Impact**: Test flakiness and non-deterministic behavior between runs depending on upstream CSV order or data merge variations.
- **Recommendation**: Add `fon_kodu` as a secondary, deterministic sort key.
- **Agent Prompt**: "Modify `fundexpert/select/pick.py` to sort candidates by `['score', 'fon_kodu']` with `ascending=[False, True]` to ensure deterministic tie-breaking. Update any tests if necessary."

### [P2] Candidate Filtering Rules Mixed Into Pipeline Orchestration
- **File(s)**: `fundexpert/pipeline.py:60-63`
- **Issue**: The `run_pipeline` orchestration function directly implements business-rule data cleaning (dropping funds with missing `applied_management_fee_pct` and `ret_3m`).
- **Impact**: It blurs the line between pipeline orchestration and data validation/filtering, making `pipeline.py` harder to read and making these rules un-reusable outside the pipeline loop.
- **Recommendation**: Extract this cleaning logic into a `clean_candidates` function in `fundexpert/data/merge.py` or a dedicated filtering module, and invoke it in `pipeline.py`.
- **Agent Prompt**: "Extract the NaN-dropping logic for `applied_management_fee_pct` and `ret_3m` from `fundexpert/pipeline.py` into a new `clean_candidates(df)` function inside `fundexpert/data/merge.py`. Call this new function in `run_pipeline`."

### [P2] Hardcoded Constants and Magic Dictionary Keys
- **File(s)**: `fundexpert/select/weights.py:7`, `fundexpert/data/loader.py:63`
- **Issue**: 
  1. `weights.py` hardcodes `_STEP = 5` and a max percentage of 100%.
  2. `loader.py` returns an unstructured `dict[str, pd.DataFrame]` whose keys (`"getiri"`, `"buyukluk"`, `"yonetim_ucreti"`) are blindly expected by `merge_universe` in `merge.py`.
- **Impact**: Constants are hidden from the central configuration (`config.py`), and the lack of a structured type (like a `dataclass`) for the universe data makes the codebase less type-safe and more refactor-resistant.
- **Recommendation**: Move `_STEP` to `config.py` as `WEIGHT_STEP_PCT`, and use a `dataclass` (e.g. `UniverseData`) to pass loaded CSV frames to the merger.
- **Agent Prompt**: "Move `_STEP = 5` from `fundexpert/select/weights.py` to `fundexpert/config.py` as `WEIGHT_STEP_PCT`. Then, refactor `fundexpert/data/loader.py` to return a strongly-typed `UniverseData` dataclass instead of a dictionary, updating `merge.py` and `cli.py` to use it."
