# Architecture Review: fundexpert

- **Review date:** 2026-08-04
- **Reviewed commit:** `afb02eae4da6ceded239610fcab32af4820d4780` (detached worktree)
- **Comparison base:** `8bbb62d3`
- **Scope:** module boundaries, pipeline invariants, data-bundle publication, rule editing, founder attribution, state/caching, API/CLI parity, provenance, concurrency, and maintainability

## Executive summary

The expanded codebase keeps a strong functional core: bundle validation fails closed, immutable bundle IDs are content-derived, `current.json` is atomically replaced only after validation, the pipeline consistently applies founder filtering before cleaning/scoring, and the same resolved diversification caps feed both the real and counterfactual news selections. The full Python suite passed.

No P0 findings were found. Two P1 findings remain: the CLI offers founders that are not present in the active bundle and can therefore crash a valid interactive run, and saved/output run context is not sufficient to reproduce or audit a recommendation after mutable rules or policy change. Five P2 maintainability/state risks are also documented below.

## P0

None.

## P1

### A-01 — CLI founder choices are not derived from the active bundle

- **Severity:** P1
- **Evidence:** The web boundary correctly calls `get_cached_candidates()` and derives founder options with `available_founders()` (`fundexpert/api.py:397-415`). The CLI prompt instead calls `founder_choices()`, which returns the complete static catalog (`fundexpert/ui.py:48-73`; `fundexpert/founders.py:192-194`), before the active bundle is loaded at `fundexpert/cli.py:110-123`. `run_pipeline()` then raises when that catalog-valid founder has no active candidates (`fundexpert/pipeline.py:87-94`), and `main()` does not catch that domain error (`fundexpert/cli.py:128-150`). Against the current real bundles, TEFAS has 60 present founders but 61 catalog entries; `HAS PORTFÖY YÖNETİMİ A.Ş.` is offered by the CLI and a direct pipeline run with it raises `ValueError: No candidates remain ...`.
- **Affected code:** `fundexpert/ui.py:48-73`, `fundexpert/founders.py:159-194`, `fundexpert/cli.py:71-84`, `fundexpert/cli.py:110-150`, `fundexpert/pipeline.py:87-94`
- **Impact:** A user can make a choice that the application itself offered and receive an uncaught traceback instead of a portfolio or actionable validation message. The API and CLI expose different valid configuration spaces for the same data snapshot.
- **Concrete remediation:** Introduce one application service that resolves the active bundle, merges candidates, and returns universe-specific founder options plus the manifest. Use it in both API and CLI. Load those options before prompting, retain the same candidates/manifest for generation, and convert an empty-founder race into a user-facing retry/validation result. Add a regression test whose catalog includes a founder absent from the active bundle.

### A-02 — Recommendation outputs do not capture enough decision context for reproducibility

- **Severity:** P1
- **Evidence:** Classification and exclusion behavior is mutable at runtime through `PUT /api/selection-rules` (`fundexpert/api.py:433-446`; `fundexpert/utils/rules.py:48-75`), but `PipelineResult` and its header carry no rules revision/hash (`fundexpert/pipeline.py:52-57`, `fundexpert/pipeline.py:166-192`). The header also omits the resolved strategy/sector caps even though they materially affect selection (`fundexpert/pipeline.py:79-84`, `fundexpert/pipeline.py:166-181`). The API response includes the data bundle snapshot but not the rules or policy fingerprint (`fundexpert/api.py:212-217`, `fundexpert/api.py:518-524`). CLI loading discards the active manifest (`fundexpert/cli.py:110-131`), and history persistence saves only a subset of configuration: it omits `bundle_id`, rule revision, founder, momentum priority, diversification mode, resolved/explicit caps, and news decision context (`fundexpert/history/store.py:22-42`).
- **Affected code:** `fundexpert/pipeline.py:30-57`, `fundexpert/pipeline.py:79-84`, `fundexpert/pipeline.py:166-199`, `fundexpert/api.py:172-217`, `fundexpert/api.py:482-524`, `fundexpert/cli.py:110-143`, `fundexpert/history/store.py:10-42`, `fundexpert/utils/rules.py:17-24`
- **Impact:** Two recommendations can have the same saved timestamp/input subset yet differ because of data, rules, resolved cap policy, founder filtering, or news. `--diff-last` can show drift but cannot explain whether it came from market data or policy/configuration changes. This weakens auditability for a financial recommendation tool.
- **Concrete remediation:** Define a versioned `RunContext`/`RecommendationManifest` at the application boundary containing the data `bundle_id` and file hashes, a canonical SHA-256 of the full active rules document, all request inputs, resolved caps, scoring/news configuration version, and code/application version. Return it from the pipeline/application service, expose it in `GenerateResponse`, print it in CLI output, and persist it verbatim in history. Add round-trip and “same context gives same picks” tests.

## P2

### A-03 — Diversification policy is duplicated in Python and JavaScript

- **Severity:** P2
- **Evidence:** The authoritative schedule is encoded in `_DIVERSIFICATION_CAPS` and band logic in `fundexpert/config.py:51-83`. A second copy, including the same band calculation, lives in `frontend/src/config.js:1-15` and drives the user-facing statement in `frontend/src/components/ControlPanel.jsx:120-130`. The API/pipeline header does not return resolved caps (`fundexpert/pipeline.py:166-181`; `fundexpert/api.py:172-187`).
- **Affected code:** `fundexpert/config.py:51-83`, `fundexpert/pipeline.py:166-181`, `fundexpert/api.py:172-187`, `frontend/src/config.js:1-15`, `frontend/src/components/ControlPanel.jsx:120-130`
- **Impact:** A backend policy change can leave the UI displaying a different cap from the cap actually used to select funds. Existing tests verify each copy rather than preventing cross-language drift.
- **Concrete remediation:** Make the backend the policy source of truth. Expose either a small `/api/config` policy contract or the resolved `max_per_type`/`max_per_sector` in every generated header; render that server-provided value. Keep only display labels in JavaScript and add an API/UI contract test.

### A-04 — Editable rules combine package data, mutable user state, and process-local coordination

- **Severity:** P2
- **Evidence:** `RULES_FILE` points inside the installed/source Python package (`fundexpert/utils/rules.py:13-14`), and a PUT replaces that file in place (`fundexpert/utils/rules.py:48-75`). The lock and LRU invalidation are process-local (`fundexpert/utils/rules.py:14`, `fundexpert/utils/rules.py:22-33`), while the endpoint implements full-document last-write-wins PUT with no revision/ETag (`fundexpert/api.py:418-446`).
- **Affected code:** `fundexpert/utils/rules.py:13-75`, `fundexpert/api.py:143-169`, `fundexpert/api.py:418-446`, `frontend/src/components/RuleEditor.jsx:102-113`, `frontend/src/components/RuleEditor.jsx:152-178`
- **Impact:** An installation/upgrade can overwrite user edits; a read-only package location prevents editing; separate processes can retain stale cached rules; and two open editors can silently overwrite each other’s changes. Atomic replacement protects file integrity but not state ownership or lost updates.
- **Concrete remediation:** Treat packaged `rules.json` as immutable defaults and store the active user override under a configurable user-data directory. Return a content revision/hash from GET, require `If-Match` (or an explicit revision field) on PUT, and reject stale saves with `409`. Use a cross-process file lock or reload by on-disk fingerprint so API workers and CLI processes converge.

### A-05 — News-cache identity omits request-shaping parameters

- **Severity:** P2
- **Evidence:** `_cache_key()` includes only query text, allowlist, and excluded substrings (`fundexpert/news/tavily.py:81-86`). `query_negative_news()` then reuses that entry even though `max_age_days` and `max_results` shape the Tavily request and result set (`fundexpert/news/tavily.py:218-260`). Tests cover allowlist invalidation but not age/result-limit invalidation (`tests/test_news_tavily.py:291-304`).
- **Affected code:** `fundexpert/news/tavily.py:81-86`, `fundexpert/news/tavily.py:218-269`, `tests/test_news_tavily.py:291-304`
- **Impact:** Changing the news lookback or result cap can reuse a cache entry produced under the old policy until TTL expiry, so the same declared configuration may not receive the expected evidence set or penalty behavior.
- **Concrete remediation:** Build the key from a versioned canonical request descriptor containing query, allowed/excluded domains, `max_age_days`, `max_results`, and any search-depth/filter setting. Persist that descriptor in the cache payload and reject mismatches. Add tests for each request-shaping parameter.

### A-06 — Refresh serialization does not extend across processes

- **Severity:** P2
- **Evidence:** Refresh ownership is a module-level `threading.Lock` (`fundexpert/data/refresh.py:36-38`, `fundexpert/data/refresh.py:66-98`). It serializes all universes within one interpreter but does not coordinate a CLI and API process (or multiple API workers) sharing `DATA_ROOT`. `publish_bundle()` also uses check-then-create around a deterministic destination without a filesystem lock (`fundexpert/data/bundle.py:355-380`) and atomically swaps a shared pointer afterward (`fundexpert/data/bundle.py:382-400`). Tests only substitute/check the in-process lock (`tests/test_data_refresh.py:129-143`).
- **Affected code:** `fundexpert/data/refresh.py:36-98`, `fundexpert/data/bundle.py:334-401`, `tests/test_data_refresh.py:129-143`
- **Impact:** Concurrent CLI/web refreshes can both download, race bundle-directory publication, return an unclassified `OSError`, or activate different last-writer-wins snapshots. File validation and atomic pointers limit corruption, but the advertised busy/one-refresh behavior is not a system-wide invariant.
- **Concrete remediation:** Add a per-universe cross-process lock file under `data/<universe>/` held across the second freshness check, download, publication, and cache invalidation. Make “destination appeared concurrently” an idempotent validated success, and translate lock/publication OS failures into `DataRefreshBusyError` or `DataRefreshError`. Add a multiprocessing integration test.

### A-07 — Pipeline configuration defaults share mutable singleton objects

- **Severity:** P2
- **Evidence:** `ScoringConfig` and `SelectionConfig` are mutable dataclasses, and `ScoringConfig` contains mutable dictionaries (`fundexpert/config.py:7-18`). The defaults are singleton instances (`fundexpert/config.py:20-41`), while `PipelineConfig` factories return those same objects rather than copies (`fundexpert/pipeline.py:47-49`). A direct check confirmed that two default `PipelineConfig` objects have identical `scoring_config` and `priority_weights` identities.
- **Affected code:** `fundexpert/config.py:7-41`, `fundexpert/config.py:85-120`, `fundexpert/pipeline.py:30-49`
- **Impact:** A test, extension, or caller that adjusts one run’s tunables in place silently changes subsequent runs in the same process, undermining run isolation and determinism.
- **Concrete remediation:** Make configuration dataclasses frozen and use immutable mappings/tuples, or have each default factory construct/deep-copy a fresh configuration. Add an isolation test that mutating/replacing one run’s injected config cannot affect another.

## Validation and methods

- Inspected all Python source, React/API boundary files, tests, documentation, and dependency declarations relevant to the architecture.
- Reviewed `git log`, `git diff --stat`, and changed files for `8bbb62d3..afb02eae` (web/API, validated bundles, refresh acquisition, founder attribution, adaptive caps, and rule editor are the material additions).
- Ran `.venv/Scripts/python.exe -m pytest tests/`: **332 passed in 32.48s; 94.55% coverage; exit 0**.
- Loaded both current real bundles: **TEFAS 1,044 rows / 60 present founders / 0 unattributed; BEFAS 310 rows / 15 present founders / 0 unattributed**.
- Compared the current founder catalog to active data and reproduced A-01 with the absent TEFAS `HAS PORTFÖY YÖNETİMİ A.Ş.` choice.
- Confirmed by object identity that default pipeline configurations share the same mutable scoring configuration and dictionaries.
- No source, dependency, test, configuration, or other review report was modified.
