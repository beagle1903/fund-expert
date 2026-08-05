# Test Coverage Review — 2026-08-04

## Executive summary

No P0 findings were identified. Two P1 and three P2 test gaps remain.

The Python suite is healthy and substantially broader than the prior review: 332 tests pass with 94.55% statement coverage. Property tests protect score bounds and monotonicity, selection caps and ordering, weight granularity, and news-penalty ordering. API contracts, TEFAS/BEFAS response alignment, current real-data smoke paths, founder filtering, and adaptive diversification schedules all have useful behavioral tests.

The most important remaining gaps are state-transition tests rather than percentage chasing. The immutable-bundle publication seam is not fault-injected after initial validation, the production rule editor is not tested through failed load/save-and-retry flows, and real refresh contention is represented only by a fake lock. Frontend coverage is not measured, and the frontend suite could not be executed in this read-only reviewer checkout because `frontend/node_modules` is absent.

## Scope and methods

- Reviewed HEAD `afb02eae4da6ceded239610fcab32af4820d4780` and all 21 commits since prior reviewed commit `8bbb62d3`.
- Inspected changed production and test code for the FastAPI boundary, React frontend, bundle validation/publication, automated TEFAS/BEFAS refresh, founder attribution, adaptive diversification, and selection-rule persistence.
- Ran `.venv/Scripts/python.exe -m pytest tests/ -q --cov-report=term-missing`:
  - **332 passed**
  - **94.55% statement coverage** (`1616` source statements, `88` missed)
  - Lowest material source module: `fundexpert/data/bundle.py`, 86% statement coverage.
- Ran an isolated branch-aware pass with a unique temporary coverage data file: `.venv/Scripts/python.exe -m coverage run --branch -m pytest tests/ -q --no-cov`, followed by `.venv/Scripts/python.exe -m coverage report -m`:
  - **332 passed**
  - `fundexpert/data/bundle.py`: **83% branch-aware coverage**, with 15 partial branch lines.
  - `fundexpert/founders.py`: 86%; `fundexpert/utils/rules.py`: 91%; `fundexpert/api.py`: 94%.
- Attempted `npm.cmd --prefix frontend test`:
  - Not executed; command exited 1 because `vitest` was not installed/resolvable and `frontend/node_modules` does not exist.
  - No install was performed because this reviewer was explicitly read-only with respect to dependencies.
- Static frontend inventory: 15 Vitest cases, concentrated in `App.test.jsx`, `AllocationChart.test.jsx`, and `NewsResults.test.jsx`; no frontend coverage provider or threshold is configured.

## Findings

### TC-01 — P1 — Atomic bundle activation is not tested under mid-publication I/O failures

**Evidence**

- `fundexpert/data/bundle.py:334-400` implements the critical transaction: validate staged data, copy into a temporary immutable directory, validate the copy, `os.replace` the bundle directory, write a temporary pointer, and `os.replace` `current.json`.
- `fundexpert/data/bundle.py:291-324` resolves and revalidates the pointer, persisted manifest, immutable ID, and file contents.
- `fundexpert/data/bundle.py:404-415` validates an already-existing immutable destination, used by the idempotent publication branch.
- Existing `tests/test_data_bundle.py:133-145` fails publication by deleting a required staged file. That failure occurs during the first validation, before any copy, manifest write, destination replace, or pointer replace is attempted.
- Existing `tests/test_data_bundle.py:148-165` covers post-publication file tampering but not malformed pointer/manifest metadata or publication interruption.
- Branch-aware coverage for `fundexpert/data/bundle.py` is 83%. Unexecuted lines include unsupported/malformed pointer checks (`303`, `306`, `312`, `323`), idempotent destination reuse (`360-362`), staged-data mutation detection (`375`), temporary-directory cleanup (`380`), and published-directory validation (`406-415`).

**Affected code**

- `fundexpert/data/bundle.py:281-324`
- `fundexpert/data/bundle.py:334-415`
- `tests/test_data_bundle.py:100-165`

**Impact**

A regression in the atomic publication protocol could leave temporary directories behind, incorrectly advance `current.json`, reject an idempotent re-publication, or serve an invalid active bundle after a disk/permission/replace failure while all 332 tests still pass. This seam is the safety boundary that prevents partially acquired financial data from becoming operational.

**Concrete remediation**

Add deterministic failure-injection tests around each mutation boundary. Preserve an already-active pointer, monkeypatch one operation at a time (`shutil.copy2`, copied-bundle validation, bundle-directory `os.replace`, and pointer `os.replace`) to raise, and assert that the old pointer bytes and old resolved bundle remain unchanged. Assert `.bundle-*` and temporary pointer files are cleaned. Add an idempotent re-publication case for an existing bundle ID and malformed `current.json`/`manifest.json` cases for schema mismatch, missing ID, universe mismatch, immutable-ID mismatch, and persisted-content mismatch.

**Actionable agent prompt**

> In `tests/test_data_bundle.py`, add fault-injection coverage for `publish_bundle` and fail-closed resolution coverage for `resolve_active_bundle`. Start with a valid active bundle and preserve its exact `current.json` bytes. Parameterize failures in copy, copied validation, destination replace, and pointer replace; after each failure assert the old pointer and old active bundle remain valid and temporary artifacts are removed. Add idempotent re-publication of the same immutable bundle and malformed pointer/manifest cases for schema, bundle ID, universe, immutable ID, and persisted metadata. Do not weaken production validation. Run the complete Python suite and retain only tests that are deterministic on Windows.

### TC-02 — P1 — Rule-editor load/save failure and retry behavior is untested

**Evidence**

- `frontend/src/components/RuleEditor.jsx:102-113` loads persisted rules asynchronously and handles non-abort errors.
- `frontend/src/components/RuleEditor.jsx:152-179` validates, saves, reports request errors, and invokes `onSaved`; `frontend/src/App.jsx:89-92` closes the editor and rebuilds the portfolio without a data refresh only after `onSaved`.
- `frontend/src/components/RuleEditor.jsx:213-351` contains three editable sections, add/delete/reorder operations, five validation outcomes, loading state, and save-disabled state.
- The only rule-editor cases are `frontend/src/App.test.jsx:274-314` (successful strategy edit/reorder/save/rebuild) and `frontend/src/App.test.jsx:316-339` (duplicate strategy keyword blocked).
- There is no test for GET failure, PUT failure, retry, save-pending state, blank/category/exclusion validation, sector or exclusion edits, cancel behavior, or editor unmount abort.

**Affected code**

- `frontend/src/components/RuleEditor.jsx:58-179`
- `frontend/src/components/RuleEditor.jsx:213-351`
- `frontend/src/App.jsx:89-92`
- `frontend/src/App.test.jsx:274-339`

**Impact**

This UI mutates the production selection taxonomy stored in `fundexpert/rules.json`. A regression could close the editor or rebuild against stale rules after a failed PUT, issue duplicate writes, lose section edits, or leave the UI stuck after a transient failure. The backend’s safe-write tests do not verify the browser’s state machine.

**Concrete remediation**

Add focused `RuleEditor.test.jsx` cases. Mock a failed GET and assert a safe error while the dialog remains closable. Mock a pending then failed PUT and assert the save button is disabled only while pending, the dialog remains open, `onSaved` is not called, no portfolio rebuild occurs, and a retry can succeed. Cover sector/exclusion add-edit-delete-reorder serialization and each validation message with no network write. Verify unmount aborts the rules GET.

**Actionable agent prompt**

> Create `frontend/src/components/RuleEditor.test.jsx` using Testing Library and Vitest. Exercise failed GET, failed PUT followed by successful retry, pending-save button state, cancel/unmount abort, and edits in strategy, sector, and exclusion tabs. Assert failed saves keep the dialog open, never invoke `onSaved`, and never trigger `/api/generate`; successful retry must invoke `onSaved` exactly once with trimmed serialized rules. Parameterize blank fields, invalid category slugs, duplicate Turkish-case keywords, blank exclusions, and duplicate exclusions, asserting no PUT for invalid input. Run frontend tests, lint, and build.

### TC-03 — P2 — Refresh concurrency is mocked at the lock boundary instead of tested as a state transition

**Evidence**

- `fundexpert/data/refresh.py:66-98` performs a pre-lock freshness check, non-blocking lock acquisition, a second post-lock freshness check, download/publication, exception translation, and unconditional lock release.
- `tests/test_data_refresh.py:134-143` replaces `_REFRESH_LOCK` with a fake object that always reports busy. It does not prove behavior with two real callers.
- The second freshness-return branch at `fundexpert/data/refresh.py:77` remains uncovered.
- Failure tests at `tests/test_data_refresh.py:90-126` verify pointer safety but do not explicitly prove a subsequent refresh can acquire the released lock.

**Affected code**

- `fundexpert/data/refresh.py:66-98`
- `tests/test_data_refresh.py:90-143`

**Impact**

Lock release, redundant-download suppression, and post-contention recovery could regress without detection. That can produce unnecessary network acquisition, permanent `REFRESH_BUSY` behavior after an exception, or conflicting refresh assumptions between API and CLI callers.

**Concrete remediation**

Use events and two threads with a blocking fake downloader. Assert the second simultaneous call receives `DataRefreshBusyError`, the first publishes once, and a later non-forced call observes the new same-day bundle without downloading. After both `WebExportError` and `BundleValidationError`, immediately run a successful refresh to prove lock release.

**Actionable agent prompt**

> In `tests/test_data_refresh.py`, add deterministic Windows-safe concurrency tests using `threading.Event` and bounded joins. Hold the first downloader after lock acquisition, call `refresh_universe` concurrently, and assert the second call gets `DataRefreshBusyError` without downloading. Release the first call, assert exactly one publication, then call again for the same local date and assert the post-lock freshness path skips acquisition. Parameterize downloader and validation failures followed by a successful call to prove `_REFRESH_LOCK` is always released. Do not use sleeps for coordination.

### TC-04 — P2 — Frontend API error normalization has no direct contract tests

**Evidence**

- `frontend/src/api/fundexpert.js:9-27` handles string details, structured `{message}` details, FastAPI validation arrays, and a status fallback.
- `frontend/src/api/fundexpert.js:30-96` independently parses JSON and throws `ApiError` for generate, founders, and rule requests.
- `frontend/src/App.test.jsx:217-236` covers only a structured `{detail: {message}}` failure surfaced by `App`.
- No test imports `ApiError`, `extractApiError`, `generatePortfolio`, `getFounders`, `getSelectionRules`, or `updateSelectionRules` directly.

**Affected code**

- `frontend/src/api/fundexpert.js:1-96`
- `frontend/src/App.test.jsx:217-236`

**Impact**

Pydantic’s normal 422 payload is an array, while reverse proxies or server failures can return non-JSON bodies. A regression could replace useful validation feedback with a generic message, lose status codes, omit abort signals, or serialize selection-rule writes incorrectly.

**Concrete remediation**

Add a small API-client test file that parameterizes every error payload shape and asserts message, `ApiError.status`, method, headers, body, encoded universe, and signal forwarding. Include successful and malformed-JSON responses for all three request families.

**Actionable agent prompt**

> Add `frontend/src/api/fundexpert.test.js`. Mock `fetch` and parameterize string detail, object-message detail, FastAPI validation arrays, empty/malformed JSON, and generic status fallback. Assert `ApiError` name/status/message, abort-signal forwarding, encoded founder query, generate payload, and PUT selection-rule serialization. Keep these tests independent of React rendering, then run frontend tests and lint.

### TC-05 — P2 — Coverage governance measures only Python statements and leaves the frontend unmeasured

**Evidence**

- `pyproject.toml:41-46` enforces only statement coverage through `--cov=fundexpert --cov-fail-under=90`; branch coverage is not enabled.
- Branch-aware review shows `fundexpert/data/bundle.py` at 83%, materially below its 86% statement result because state-transition branches are not exercised.
- `frontend/vite.config.js:17-22` configures the test environment but no coverage provider, include list, or threshold.
- `scripts/check.ps1:15-25` runs Python tests and frontend tests/lint/build, but records no frontend coverage.
- The checkout had no `frontend/node_modules`, so `npm.cmd --prefix frontend test` exited with `'vitest' is not recognized`; Python-only baseline success therefore did not validate any of the 15 frontend cases in this run.

**Affected code**

- `pyproject.toml:41-46`
- `frontend/vite.config.js:17-22`
- `frontend/package.json:8-11`
- `scripts/check.ps1:13-25`

**Impact**

Complex backend branches and the whole browser state machine can regress while the sole numerical gate remains green. The immediate issue is observability, not a demand for blanket 100% coverage.

**Concrete remediation**

Enable Python branch coverage and add Vitest V8 coverage for production JS/JSX, excluding entrypoint/style/setup files. Establish initial thresholds from a clean measured run, then raise only around critical API, RuleEditor, and App state paths. Ensure CI/review setup performs a deterministic `npm ci` before `scripts/check.ps1`; do not make the check script mutate dependencies implicitly.

**Actionable agent prompt**

> Add branch coverage to the Python coverage gate and configure `@vitest/coverage-v8` for `frontend/src/**/*.{js,jsx}` with sensible exclusions for `main.jsx` and test setup. Run a clean `npm ci`, capture the initial frontend statement/branch/function/line values, and set non-inflated thresholds that the current suite passes. Update the documented setup/CI workflow so dependencies are installed explicitly before `scripts/check.ps1`. Add tests for TC-02 and TC-04 before raising thresholds; do not chase coverage in generated or presentational-only code.

## Positive coverage observations

- `tests/test_score.py`, `tests/test_pick.py`, `tests/test_weights.py`, and `tests/test_news_penalty.py` contain useful Hypothesis invariants. The previously suggested sector-count exhaustiveness and news-penalty monotonicity properties are now present.
- `tests/test_tefas_export.py` validates the three-request contract, row floors, TEFAS’s bounded five-code alignment exception, exact BEFAS coverage, transport failures, malformed JSON, and date-window edge cases.
- `tests/test_api.py` validates strict request types, extra-field rejection, safe server errors, active-bundle cache invalidation, founder options, selection-rule persistence, and snapshot provenance.
- `tests/test_smoke.py` runs both universes against real CSVs and covers zero-candidate behavior.
- Adaptive cap schedules are thoroughly parameterized in `tests/test_config.py`; pipeline propagation and news counterfactual reuse are explicitly covered in `tests/test_pipeline_diversification.py`.

## Final reviewer status

- P0: 0
- P1: 2
- P2: 3
- Python validation: 332 passed; 94.55% statement coverage.
- Isolated branch-aware validation: 332 passed.
- Frontend validation: not run because local frontend dependencies were absent; this is an unresolved validation limitation, not a reported frontend test failure.
- Source, tests, dependency declarations, and configuration were not modified by this reviewer.
