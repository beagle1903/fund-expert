# Test Coverage Review
*Date: 2026-06-12*

## Executive Summary
The `fundexpert` codebase exhibits **excellent test coverage**, achieving **95% overall line coverage** across the main package. The testing practices are mature, leveraging modern tools like `pytest`, `pytest-cov`, and `hypothesis` for property-based testing. The test suite is well-structured and mirrors the application architecture effectively.

## Detailed Findings

### 1. Test Tools & Infrastructure
- **Framework:** The project uses `pytest` as the core testing framework, configured cleanly in `pyproject.toml`.
- **Property-Based Testing:** `hypothesis` is integrated, particularly useful for logic-heavy operations such as weight calculations and scoring logic (as seen in `test_weights.py` and `test_score.py`).
- **Data-Driven Smoke Tests:** End-to-end tests in `test_smoke.py` validate the entire pipeline using real data inputs from the `data/` directory, testing core flows seamlessly against real-world artifacts (TEFAS and BEFAS universes).

### 2. Coverage Metrics
The test suite successfully executed 185 tests with a combined execution time of ~14 seconds.
Total statements: 653
Missed statements: 32
**Overall Coverage: 95%**

**Noteworthy Module Coverages:**
- `fundexpert/data/merge.py`: 100%
- `fundexpert/scoring/*`: 100%
- `fundexpert/select/*`: 100%
- `fundexpert/pipeline.py`: 100%
- `fundexpert/render/table.py`: 96%
- `fundexpert/cli.py`: 90%
- `fundexpert/news/penalty.py`: 95%

### 3. Gaps in Coverage (P2/P3 Priority)
The remaining 5% of uncovered lines consist almost entirely of acceptable edge cases, including:
- **CLI Boilerplate and File I/O Exceptions:** Handlers in `cli.py` for `json.JSONDecodeError` and `OSError` when reading/saving the local `.fundexpert/last.json` cache file.
- **Exception handling in async executions:** Lines 105-106 in `fundexpert/news/penalty.py` handling network failures (`except Exception`) during thread pool executor routines for Tavily API fetches.
- **Main guard:** The `if __name__ == "__main__":` block in `__main__.py` isn't executed during the test suite.

## Recommendations & Actionable Prompts

**P2: Cover Network Error Paths via Mocking**
- Currently, network/API failure paths in `news.penalty` are unexercised. We can mock the HTTP/API response to throw an exception to verify the graceful fallback behavior.
- *Prompt:* "Add a test case in `tests/test_news_penalty.py` that mocks `_query_for_prefix` to raise an Exception, asserting that the exception is caught, a warning is printed to stderr, and the execution continues without failing the pipeline."

**P2: Cover File System Error Paths in CLI**
- The `cli.py` file has untested branches for cache I/O (`_load_last_run`, `_save_last_run`).
- *Prompt:* "Add test cases in `tests/test_cli.py` to mock `LAST_RUN_FILE.read_text` to throw an `OSError` and `json.JSONDecodeError`, ensuring `_load_last_run` returns an empty dict safely."

**P3: Integrate Coverage Enforcement**
- *Prompt:* "Add `[tool.pytest.ini_options]` config in `pyproject.toml` to fail the build if coverage drops below 90% using `--cov-fail-under=90`."

## Conclusion
The testing setup requires no major architectural overhauls. The use of `hypothesis` for the algorithmic parts and real data for the pipeline are highly effective strategies that protect against regressions without creating overly brittle tests.
