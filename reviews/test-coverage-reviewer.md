# Test Coverage Review: fundexpert

## Executive Summary
The test suite for `fundexpert` is exceptionally strong, achieving an overall **96.57% test coverage**. This comfortably exceeds the standard 90% benchmark. Most impressively, the core business logic—including data pipelines, scoring logic, constraint solvers (caps and weighting algorithms), and rendering layers—all boast **100% test coverage**. The test suite also robustly utilizes property-based testing (`hypothesis`) to enforce system invariants.

The missing 3.43% consists entirely of OS-level error catching, edge-case network safeguards, and top-level CLI boilerplate that is notoriously difficult to hit without explicit monkey-patching. There are no severe coverage gaps or untested core flows.

---

## Detailed Findings

### P0 (Critical Logic Gaps)
**None.** 
The data parsing, transformations, scoring engines, picking routines, and tabular UI modules are completely covered. The application guarantees correctness on all major use cases across its internal logic.

### P1 (Important Edge Cases Missing Coverage)
These misses revolve around infrastructure and outer bounds that should ideally be hardened using mocked environments.

- **`fundexpert/news/tavily.py` (92% Coverage):** 
  - Several exception handlers are uncovered. For example, malformed URL parsing (`ValueError` inside `urllib.parse.urlparse`), or `OSError` blocks where caching fails to write to disk.
  - The security invariant that blocks non-HTTPS API traffic (lines 173-174: `if not req.full_url.startswith("https://")`) currently goes untested.
- **`fundexpert/history/store.py` (95% Coverage):** 
  - A fallback `except OSError` block (lines 59-60) designed to suppress failures when attempting to replace `last.json` is unexercised.
- **`fundexpert/data/loader.py` (96% Coverage):** 
  - The file size safeguard that throws a `ValueError` if the candidate dataset exceeds `MAX_CSV_SIZE_BYTES` (line 55) has no test case verifying its trigger.

### P2 (Minor & Boilerplate Uncovered)
These are acceptable misses typically excluded via `.coveragerc` or `pragma: no cover`.

- **`fundexpert/__main__.py` & `fundexpert/cli.py`:**
  - Standard top-level module execution boilerplate (`if __name__ == '__main__':`) and raw `KeyboardInterrupt` exit nodes.
- **`fundexpert/ui.py`:**
  - The fallback `except (OSError, ValueError): pass` inside `ensure_utf8_stdio()` which suppresses errors if stream reconfiguration fails on certain terminal emulators.

---

## Recommended Fixes

To achieve an even tighter state and near-100% genuine coverage, implement the following quick fixes:

1. **Test CSV Bounds:** In `test_loader.py`, use Pytest's `monkeypatch` to mock `path.stat().st_size` returning a value greater than `MAX_CSV_SIZE_BYTES` and `pytest.raises(ValueError)` to verify the system rejects bloated source files.
2. **Network Protocol Validation:** In `test_news_tavily.py`, write a brief test passing an explicit HTTP (or ftp) endpoint string or monkey-patching `req.full_url` to assert the "HTTPS only" exception evaluates correctly.
3. **Mock File System Fails:** In `test_history_store.py`, mock `os.replace` to deliberately throw an `OSError` to prove the application successfully silently handles and absorbs cache/storage misses without crashing the main user session.
4. **Update Coverage Config:** Add `# pragma: no cover` to standard boilerplate lines such as `if __name__ == "__main__":` in `__main__.py` to ignore meaningless coverage dips.
