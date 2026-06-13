# Test Coverage Review
**Date:** 2026-06-13
**Reviewer:** Test Coverage Subagent

## Overall Metrics
- **Current Coverage**: 94.73% (702 statements, 37 missing)
- **Minimum Requirement**: 90%
- **Status**: Excellent. The core analytical pipeline (`score.py`, `pick.py`, `weights.py`, `horizon.py`, `merge.py`, `normalize.py`) sits at a solid 100% test coverage.

Despite the high coverage, a deep dive reveals some gaps in testing negative pathways (I/O exceptions, network fallbacks) and an absence of property-based testing in the scoring logic.

---

## P0: Critical Coverage Gaps
*None.* The fundamental business logic (fetching, merging, calculating, and picking funds) is comprehensively tested under both positive conditions and deterministic negative conditions.

---

## P1: High-Priority Coverage Gaps (Negative Paths)
The test suite heavily relies on the "happy path" when interacting with the file system and external APIs. The following exception blocks are unexercised and could obscure runtime crashes or silent failures:

1. **`fundexpert/news/tavily.py` (Lines 65-66, 73, 77-78, 92-93, 110-111, 145-146, 173)**
   - **Cache I/O:** Exceptions (`OSError`, `json.JSONDecodeError`) thrown during `_read_cache` and `_write_cache` are never simulated. 
   - **Malformed Data:** Missing coverage for URL parsers (`_domain_of`, `_hostname`) when hitting a `ValueError`.
   - **Action:** Mock `pathlib.Path.read_text`/`write_text` with side effects in `tests/test_news_tavily.py` to trigger these cache rescues.

2. **`fundexpert/history/store.py` (Lines 55-56)**
   - **File System Errors:** When `save_run` attempts to `shutil.copy2` to update `latest_{universe}.json`, the fallback `except OSError: pass` is never triggered.
   - **Action:** Mock `shutil.copy2` with a side effect of `OSError`.

3. **`fundexpert/cli.py` & `fundexpert/ui.py`**
   - **CLI fallbacks (cli.py: 106, 113-114, 120, 126):** Missing coverage for when `save_run` fails (`OSError`), when `result.header.get("warning")` prints to stderr, or when `--diff-last` is invoked but `previous_run` is `None`.
   - **UI persistence (ui.py: 15, 18-19, 31-32, 100-101):** Reading/writing the `LAST_RUN_FILE` has uncovered exception handlers. Also, `ensure_utf8_stdio` does not test the `OSError` catch block.

---

## P2: Testing Strategies & Weak Assertions

1. **Unreachable Presentation Logic in `render/table.py` (Lines 73, 94, 104)**
   - **Finding:** The conditional logic `if show_sector:` is currently untested. The mock `_selected()` dataframe in `tests/test_render.py` doesn't include the `"sector"` column, meaning tests never render the sector column on the Rich table.
   - **Action:** Update the mock dataframe in `test_render.py` to include a dummy `"sector"` column for at least one rendering test.

2. **Missing Property-Based Tests in `fundexpert/scoring/score.py`**
   - **Finding:** While `Hypothesis` properties are beautifully utilized in `select/pick.py` and `select/weights.py`, the core scoring mechanism relies purely on standard parametrized examples. 
   - **Action:** Implement property tests proposing these invariants:
     - *Range Invariant:* `score` values should never break bounds (e.g., `-2.0 <= score <= 2.0` depending on the max penalty).
     - *Monotonicity Invariant:* Assuming identical fee, risk, and volume metrics, an increase in `R` strictly guarantees `score_new > score_old`.
     - *Risk Penalty Invariant:* Given the identical metrics, increasing the SRRI risk level (from 1 to 7) strictly decreases the score when the `risk_level` profile is set to `low` or `medium`.

3. **Missing default argument instantiation in `render/diff.py` (Line 21)**
   - **Finding:** `if console is None: console = Console()` is uncovered because all tests inject a `MagicMock()` console.
   - **Action:** Add a test that calls `render_diff` without the `console` argument to assert it successfully falls back to stdout.
