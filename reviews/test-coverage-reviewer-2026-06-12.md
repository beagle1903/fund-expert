# Test Coverage Review — 2026-06-12

## Executive Summary
The test coverage for the `fundexpert` codebase is generally excellent, reflecting a highly testable, well-factored data pipeline architecture. Core business logic (scoring, capping, weighting) is comprehensively tested, and mocking strategies for external APIs (Tavily) are effective. 

However, deep review reveals a few critical gaps:
1. **Client-side keyword validation** in the Tavily API client lacks tests, specifically around Turkish character normalization, which could lead to false-positive penalizations.
2. **Property-based testing** is missing for complex algorithmic components (`weights.py` and `pick.py`). The current tests rely on crafted fixtures but do not enforce mathematical invariants across arbitrary datasets.
3. Minor **untested edge cases**, such as OS interactions (`_ensure_utf8_stdio`), ThreadPoolExecutor unhandled exceptions, and empty DataFrames.

## Coverage Matrix

| Module | Test File | Estimated Coverage | Notes |
|---|---|---|---|
| `cli.py` | `test_cli.py` | High | Interactive prompts and pipeline bindings well covered. OS-specific configuration (`_ensure_utf8_stdio`) and cache file OS errors are untested. |
| `pipeline.py` | `test_smoke.py`, `test_cli.py` | High | Pipeline integration thoroughly tested via smoke tests against real CSVs. Negative data edge cases (all candidates dropped) lack specific integration assertions. |
| `config.py` | `test_config.py` | High | Static configuration correctly validated. |
| `data/loader.py` | `test_loader.py` | High | Missing filesystem `OSError` and empty-file tests. |
| `data/merge.py` | `test_merge.py` | High | Handles missing funds cleanly. |
| `scoring/horizon.py` | `test_horizon.py` | High | NaN exclusions tested nicely. |
| `scoring/normalize.py` | `test_normalize.py` | High | Missing true 0-length series edge case test. |
| `scoring/score.py` | `test_score.py` | High | Missing empty DataFrame input tests. |
| `select/pick.py` | `test_pick.py` | High | Strong unit coverage, but missing property-based testing for constraint resolution. |
| `select/sector.py` | `test_sector.py` | High | Comprehensive Turkish keyword testing. |
| `select/strategy.py`| `test_strategy.py` | High | Comprehensive Turkish keyword testing. |
| `select/weights.py` | `test_weights.py` | High | Largest-remainder algorithm heavily unit tested, but lacks property-based invariant verification. |
| `news/match.py` | `test_news_match.py` | High | Extractors tested thoroughly against diacritics and missing punctuation. |
| `news/penalty.py` | `test_news_penalty.py` | High | Unhandled exception propagation from concurrent queries is untested. |
| `news/tavily.py` | `test_news_tavily.py` | Medium | **Gap**: Client-side keyword validation and its Turkish-case normalization are entirely untested. |
| `render/table.py` | `test_render.py` | High | Rendering branches extensively covered. |
| `render/diff.py` | `test_render_diff.py`| High | Good output verifications. |
| `history/store.py`| `test_history_store.py`| High | Happy path tested. |

## Findings

### [P1] Untested Client-Side Keyword Validation for Tavily Hits
- **File(s)**: `fundexpert/news/tavily.py` (lines 180-182), `tests/test_news_tavily.py`
- **Issue**: `_post_tavily` validates that the returned hits actually contain at least one of the query keywords to drop hallucinated results. This logic includes a Turkish-specific lowercase conversion `replace("I", "ı").replace("İ", "i").lower()`. There are absolutely no tests validating that hits missing the keywords are dropped, nor any testing of the Turkish case insensitivity here.
- **Risk**: If this filtering breaks or fails on Turkish characters, funds could be erroneously penalized for unrelated news, defeating the purpose of the news pass.
- **Recommendation**: Add a test in `test_news_tavily.py` simulating a `_post_tavily` JSON response where `content` and `title` lack the keywords, and assert it is dropped. Add another test verifying the case-insensitivity of Turkish keywords (e.g., keyword "İFLAS" matches "iflas" in content).
- **Agent Prompt**: `Add unit tests to test_news_tavily.py for the client-side keyword filtering logic in _post_tavily. Ensure you test that false-positive results are dropped, and that Turkish characters (I/ı, İ/i) are matched case-insensitively.`

### [P1] Property-Based Testing Opportunities for Algorithmic Modules
- **File(s)**: `tests/test_weights.py`, `tests/test_pick.py`
- **Issue**: `compute_weights` uses a largest-remainder algorithm to distribute 5% blocks to exactly 100%. `pick_top` enforces per-sector and per-strategy caps. These algorithmic invariants are manually tested with a few crafted examples but are ripe for property-based testing.
- **Risk**: Subtle edge cases involving ties, zero-scores, or highly skewed score distributions could break the 100% sum invariant or the diversity caps in unpredicted ways.
- **Recommendation**: Introduce `hypothesis` to the test suite. Write a property-based test for `compute_weights` asserting: sum is exactly 100, all are multiples of 5, minimum is 5%. Write another for `pick_top` asserting caps are never exceeded.
- **Agent Prompt**: `Install hypothesis and add property-based tests to test_weights.py and test_pick.py. For weights, assert the sum is 100 and multiples of 5. For pick, assert max_per_type and max_per_sector are strictly respected across arbitrary candidate DataFrames.`

### [P2] `_ensure_utf8_stdio` is Untested
- **File(s)**: `fundexpert/cli.py` (lines 134-144), `tests/test_cli.py`
- **Issue**: `_ensure_utf8_stdio` modifies `sys.stdout` and `sys.stderr` to force UTF-8 on Windows. It catches `OSError` and `ValueError`, but this is entirely untested.
- **Risk**: Low, but an unexpected exception type (e.g., `AttributeError` from a mocked stdout in an IDE environment) could crash the CLI immediately upon startup.
- **Recommendation**: Add a test mocking `sys.stdout` to test both the happy path (where `reconfigure` succeeds) and error paths (where it throws or doesn't exist).
- **Agent Prompt**: `Add a unit test in test_cli.py to cover _ensure_utf8_stdio in cli.py. Mock sys.stdout.reconfigure to ensure exceptions like ValueError or OSError are safely caught.`

### [P2] ThreadPoolExecutor Unhandled Exceptions
- **File(s)**: `fundexpert/news/penalty.py` (lines 95-99)
- **Issue**: `future.result()` is called on the threads querying Tavily. If `_query_for_index` were to raise an unhandled exception (e.g., an unexpected `TypeError` parsing a URL), it would propagate and crash the entire pipeline run.
- **Risk**: A single malformed fund or unexpected exception kills the whole process rather than just skipping the news check for that fund.
- **Recommendation**: Wrap `future.result()` in a try-except block, log the error, and continue.
- **Agent Prompt**: `In penalty.py, wrap the future.result() call inside the ThreadPoolExecutor loop in a broad try-except block. Catch Exception, log it via sys.stderr, and gracefully skip that fund instead of crashing.`

### [P2] Empty DataFrame Handlings in Scoring
- **File(s)**: `fundexpert/scoring/score.py`, `fundexpert/scoring/normalize.py`
- **Issue**: There are no explicit tests verifying that `score_candidates` handles a completely empty DataFrame gracefully without crashing.
- **Risk**: If the universe is fully filtered out before scoring, the pipeline could crash with a Pandas `ValueError` rather than a graceful "pool empty" message.
- **Recommendation**: Pass an empty DataFrame to `score_candidates` and `minmax_normalize` and assert they return empty structures rather than throwing errors.
- **Agent Prompt**: `Add tests to test_score.py and test_normalize.py verifying that passing a completely empty DataFrame or Series returns an empty structure without throwing exceptions.`
