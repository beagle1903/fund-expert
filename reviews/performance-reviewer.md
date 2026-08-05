# Performance Review: `fundexpert`

**Review date:** 2026-08-04

**Commit reviewed:** `afb02eae4da6ceded239610fcab32af4820d4780`

**Recent-change baseline:** `8bbb62d3..afb02eae`

**Scope:** CSV ingestion and memory, active-bundle validation/hashing, API caching and locking, rule/classification work, scoring/selection complexity, optional news concurrency, frontend renders and network calls, and documentation/startup cost.

## Executive summary

- **P0:** none.
- **P1:** 2 findings.
- **P2:** 4 findings.
- The normal offline pipeline is fast at the current 1,044-row TEFAS scale, but its API cache does not avoid bundle parsing/hashing. A warm lookup spent a median **24.53 ms** validating the immutable bundle before returning the cached frame, while the complete no-news pipeline itself took a median **36.08 ms**.
- The optional news pass is the largest availability risk: one request can schedule up to 60 searches, create 25 worker threads, and has no request-wide deadline or global concurrency budget.
- Current candidate-frame memory is small: approximately **271,260 bytes** for TEFAS and **90,989 bytes** for BEFAS (deep pandas accounting). The Arrow-backed code/name columns, categorical umbrella type, and `usecols` ingestion are effective; no memory-leak or high-memory finding was identified.

## Findings

### P1-1 — Full CSV parsing and hashing runs before every candidate-cache hit

**Severity:** P1

**Evidence**

- `get_cached_candidates` calls `resolve_active_bundle` before it takes the cache lock or compares the cached fingerprint (`fundexpert/api.py:279-289`).
- For a versioned bundle, `resolve_active_bundle` calls `validate_bundle` on every invocation and compares the newly generated manifest with the persisted one (`fundexpert/data/bundle.py:291-324`).
- `validate_bundle` parses all three CSVs into dataframes (`fundexpert/data/bundle.py:216-229`), validates every numeric column and code set (`fundexpert/data/bundle.py:168-189`, `233-258`), and hashes all three files (`fundexpert/data/bundle.py:136-141`, `243-250`). Only after that work does the API compare `active.fingerprint` with the cached entry.
- On the active 1,044-row TEFAS bundle (three CSVs totalling 423,101 bytes), 10 warm measurements produced:
  - `resolve_active_bundle`: median **23.86 ms**, range 21.79-26.61 ms.
  - `get_cached_candidates` after a warm cache: median **24.53 ms**, range 22.80-31.41 ms.
  - A full no-news pipeline over the already-loaded candidates: median **36.08 ms** over 30 runs.
- `GET /api/founders`, `POST /api/generate`, and each universe in `GET /api/data-status` all cross this validation path (`fundexpert/api.py:331-350`, `397-415`, `449-500`).
- On a cold miss, the CSVs are parsed once for validation and then parsed a second time by `_load_candidates` via `load_bundle_frames` (`fundexpert/api.py:274-276`, `291-303`; `fundexpert/data/bundle.py:418-424`).

**Expected impact**

The process-local candidate cache saves the merge and founder attribution but not most disk I/O or integrity-validation CPU. At the current dataset size, validation alone is roughly two-thirds of the median pipeline time; it scales with file size and request count. The initial page also requests founders and a portfolio concurrently, amplifying this cost. This is an architectural cache-boundary issue, not a micro-optimization.

**Concrete remediation**

Introduce a cheap active-bundle identity/signature path for hot reads. Read and validate the small `current.json`, derive the bundle directory, and compare a cached signature containing the bundle ID plus `stat` identity for `manifest.json` and all three required CSVs (size, `mtime_ns`, and `ctime_ns`). Run the existing full `validate_bundle` only on the first access, pointer/signature change, or an explicit integrity/status check; then reuse the validated `ActiveDataBundle` and merged candidates. Preserve fail-closed behavior for missing/deleted/changed files and pointer swaps. On cold validation, consider returning/reusing the already parsed frames so `_load_candidates` does not parse the same files again. Add tests proving that warm calls do not invoke `load_universe` or `_sha256`, while pointer changes, deletion, and tampering invalidate the cache and still return the existing safe 503 behavior.

**Actionable agent prompt**

> Refactor the Fundexpert API bundle cache so a warm `get_cached_candidates` call does not re-parse and re-hash all three immutable CSVs. Add a cheap active signature based on validated `current.json` plus manifest/CSV stat identity, cache the validated bundle and merged candidates per universe, and perform full `validate_bundle` only on a signature miss/change or explicit integrity check. Reuse validated frames on a cold miss if practical. Preserve the current fail-closed behavior for a missing file, invalid pointer, changed bundle, and tampered content. Add focused tests that count `load_universe`/`_sha256` calls on warm hits and cover pointer swaps, deletion, and mutation; then run the complete Python suite.

### P1-2 — News generation has per-request thread pools but no global work budget or deadline

**Severity:** P1

**Evidence**

- The API accepts `n <= 20` (`fundexpert/api.py:46-63`), and the pipeline queries up to `n * query_top_k_multiplier`, where the multiplier is 3 (`fundexpert/pipeline.py:120-131`; `fundexpert/config.py:87-92`). A single request can therefore select up to **60** query candidates.
- `apply_negative_news_penalty` creates a new `ThreadPoolExecutor` for every generate request and submits every unique prefix immediately (`fundexpert/news/penalty.py:69-101`). The configured executor size is **25 workers** (`fundexpert/config.py:116-118`).
- Each network query has a 10-second socket timeout and can make three attempts with 1- and 2-second sleeps (`fundexpert/news/tavily.py:150-190`). In a timeout scenario, one worker can remain occupied for approximately 33 seconds. Sixty unique prefixes require up to three worker batches, so the request has an approximately **99-second theoretical path** before executor shutdown, with no request-wide deadline.
- `POST /api/generate` is synchronous and runs the entire pipeline inline (`fundexpert/api.py:449-500`). Client-side `AbortController` cancellation only stops the browser from consuming the response; there is no server cancellation/deadline signal in this path (`frontend/src/App.jsx:22-45`).
- Concurrent requests each create their own pool, so aggregate threads and Tavily calls are unbounded by the process. The disk cache has no per-key single-flight lock (`fundexpert/news/tavily.py:103-147`, `218-270`), allowing simultaneous requests for the same cold key to duplicate external work.

**Expected impact**

A slow or degraded Tavily service can tie up API request workers for a long period, multiply threads and outbound calls across concurrent requests, consume quota, and make subsequent local UI actions sluggish. Aborting or superseding a browser request does not reclaim the backend work. Although news is opt-in, this is a significant resource/availability risk when enabled.

**Concrete remediation**

Use a shared, process-wide bounded news executor or semaphore rather than a pool per request; apply a strict request-wide monotonic deadline; reduce or budget per-attempt timeouts/retries so all work fits inside that deadline; stop scheduling/cancel pending futures when the budget expires; and single-flight cold cache keys so concurrent identical searches share one result. Consider returning a partial result with explicit timeout metadata rather than waiting for every query. Add concurrency tests that prove the global active-query count never exceeds the configured cap, identical cold keys issue one outbound call, and the request returns within its total deadline under simulated timeouts.

**Actionable agent prompt**

> Bound the optional Fundexpert news pass end to end. Replace the per-request 25-thread executor with a shared process-wide concurrency limiter, add a request-wide monotonic deadline that includes retries and queue time, stop/cancel pending work when the deadline expires, and coalesce concurrent identical cache keys. Keep fail-soft semantics and report timed-out/partial work explicitly in `news_meta`. Add deterministic tests with mocked slow/timeouting Tavily calls to verify the global concurrency cap, single-flight behavior, and total deadline, then run the full suite.

### P2-1 — Concurrent cold candidate-cache misses duplicate parsing and merging

**Severity:** P2

**Evidence**

- The cache lock protects only lookup and assignment. It is released before `_load_candidates`, so two misses for the same universe can both parse, merge, and attribute founders (`fundexpert/api.py:286-303`).
- A safe two-thread probe wrapped `_load_candidates` with a barrier and then called `get_cached_candidates("tefas")` concurrently after clearing the cache. The observed load count was **2**, confirming that the cache does not single-flight admission.
- The frontend initiates the initial portfolio and founder requests in separate effects (`frontend/src/App.jsx:48-64`), so a cold process naturally creates overlapping requests for the same universe.

**Expected impact**

Cold startup and post-refresh bursts can duplicate the most expensive cache-fill work and temporarily double dataframe allocations. Current frames are small, so the impact is bounded today, but it compounds P1-1 and grows with future bundle size or more clients.

**Concrete remediation**

Add per-universe single-flight state (for example, a condition/future stored under the cache lock). The first miss validates and loads outside the global lock; same-universe waiters await that result; different universes remain independent. Propagate the loader exception to all waiters and always clear in-flight state. Add a barrier-based concurrency test asserting one `_load_candidates` call and identical returned cache entries.

**Actionable agent prompt**

> Make `get_cached_candidates` single-flight per universe. Let one thread perform a cold validation/load while same-universe callers wait and reuse its result; allow TEFAS and BEFAS loads concurrently; propagate failures safely and clear in-flight markers in `finally`. Add a deterministic two-thread test that forces overlap and asserts exactly one `_load_candidates` invocation, then run the full suite.

### P2-2 — Static rule classification is recomputed on every portfolio generation

**Severity:** P2

**Evidence**

- Every pipeline run uppercases all candidate names and reruns both classifiers (`fundexpert/pipeline.py:96-114`), even when the user changes only risk, horizon, priorities, portfolio size, or diversification mode.
- Strategy classification makes one full-series plain-text scan per strategy rule (`fundexpert/select/strategy.py:18-28`). Sector classification first applies three regex cleanup rules and then one scan per sector rule (`fundexpert/select/sector.py:20-38`). The current rules file contains 13 strategy rules, 25 sector rules, and 3 cleanup rules.
- Rule loading itself is not the problem: `_load_rules_json` and all four rule accessors are `lru_cache`-backed and correctly cleared after a save (`fundexpert/utils/rules.py:22-33`, `75-95`).
- In a 20-run `cProfile` sample on the 1,044-row TEFAS frame, `turkish_upper_series`, `bucket_from_names`, and `sector_from_names` accumulated **0.533 seconds of 1.157 seconds total** (approximately 46% of profiled pipeline time). Profiling overhead means the absolute figures are not latency measurements, but the relative hotspot is stable.

**Expected impact**

Interactive regenerations repeatedly spend a large share of CPU on values determined only by fund name and the current rule revision. Cost grows linearly with both candidates and editable rules. Current absolute latency is acceptable, so this is P2 rather than P1.

**Concrete remediation**

Cache/precompute `strategy` and `sector` per candidate bundle and rule revision. Use a deterministic rules revision (for example, a hash of the normalized classification/cleanup rule content), invalidate on successful `PUT /api/selection-rules`, and retain the current compute path for arbitrary CLI/test dataframes that are not preclassified. Do not cache scoring, which depends on request settings. Add a test showing repeated generations reuse classification and a rule save invalidates it immediately.

**Actionable agent prompt**

> Cache Fundexpert strategy/sector classification by active bundle fingerprint plus a deterministic rules revision. Reuse classifications across requests that change only scoring/selection controls, invalidate immediately after a successful rule save, and keep a safe fallback for uncached CLI/test dataframes. Add tests that spy on both classifiers across repeated generations and after a rule update; benchmark the current 1,044-row bundle and run the full suite.

### P2-3 — One global refresh lock unnecessarily serializes TEFAS and BEFAS

**Severity:** P2

**Evidence**

- `_REFRESH_LOCK` is a single module-level lock (`fundexpert/data/refresh.py:36-37`).
- Every universe attempts to acquire that same non-blocking lock and returns `DataRefreshBusyError` on contention (`fundexpert/data/refresh.py:52-77`).
- TEFAS and BEFAS download and publish to distinct universe directories, and the API explicitly exposes universe-specific refreshes (`fundexpert/api.py:105-115`, `384-394`).

**Expected impact**

A long TEFAS acquisition blocks an independent BEFAS refresh and returns 409 instead of allowing useful parallel work. This is infrequent in the current local workflow, so it is P2, but the lock scope is broader than the protected resource.

**Concrete remediation**

Use one lock per supported universe, keeping same-universe acquisition/publish mutually exclusive while allowing TEFAS and BEFAS to run independently. Do not reduce the lock duration around a single universe's download and atomic publication. Add concurrency tests proving same-universe contention fails busy and different-universe refreshes overlap safely.

**Actionable agent prompt**

> Replace the process-wide Fundexpert refresh lock with stable per-universe locks. Preserve non-blocking busy behavior for two refreshes of the same universe and the full acquisition-to-publication critical section, while allowing TEFAS and BEFAS refreshes concurrently. Add deterministic concurrency tests for both cases and run the complete suite.

### P2-4 — Development StrictMode can duplicate initial expensive requests

**Severity:** P2

**Evidence**

- The root renders the app inside React `StrictMode` (`frontend/src/main.jsx:1-9`). React development StrictMode intentionally performs an extra effect setup/cleanup cycle.
- On mount, one effect posts the default portfolio request and a second fetches founders (`frontend/src/App.jsx:48-64`). The default portfolio request has `refresh_data: true` (`frontend/src/config.js:18-29`).
- Cleanup aborts the browser request (`frontend/src/App.jsx:48-51`), but once the synchronous FastAPI handler has started, aborting fetch does not cancel bundle validation, refresh, news, or pipeline work. A second development setup can therefore start equivalent work. If the first call owns the non-blocking refresh lock, the visible replacement call can receive `REFRESH_BUSY` (`fundexpert/data/refresh.py:71-77`; `fundexpert/api.py:241-259`).
- Frontend tests render `<App />` directly rather than under the production root's `<StrictMode>`, so they do not exercise this request pattern (`frontend/src/App.test.jsx:100-113` and subsequent tests).

**Expected impact**

During the documented Vite development workflow, startup can duplicate validation/load/network work; on a stale local day it can also contend with its own refresh. This does not affect a production build's effect count and is therefore P2.

**Concrete remediation**

Make initial data acquisition idempotent across StrictMode setup/cleanup by coalescing identical in-flight API requests or introducing a single bootstrap resource/request. Do not simply retain a `useRef` guard while aborting the first request, because the StrictMode cleanup could abort the only request. Add a test that renders the actual StrictMode root and verifies one underlying generate and founder operation (or one documented bootstrap operation), including the stale-refresh case.

**Actionable agent prompt**

> Make Fundexpert's initial frontend data load StrictMode-safe. Coalesce identical in-flight generate/founder work or replace the two mount effects with one idempotent bootstrap resource; preserve stale-response suppression and unmount cleanup without aborting the only shared request. Add a test that renders `<StrictMode><App /></StrictMode>` and proves that initial refresh/generation and founder loading do not duplicate backend work or produce a self-inflicted `REFRESH_BUSY` error.

## Validated non-findings and positive observations

- **CSV memory:** `_read_one` limits columns and uses `string[pyarrow]` for code/name plus `category` for umbrella type (`fundexpert/data/loader.py:53-66`). Deep memory was approximately 271 KB for 1,044 TEFAS candidates and 91 KB for 310 BEFAS candidates. No object-string memory regression was found.
- **Bundle publication:** The staged/copy validation in `publish_bundle` (`fundexpert/data/bundle.py:334-400`) is deliberate low-frequency integrity/TOCTOU protection. It should not be removed to optimize the interactive read path.
- **Rule file reads:** Pipeline rule access is cached; only the small editable-rules endpoint deliberately rereads JSON. There is no repeated rules-file I/O in normal generation.
- **Selection complexity:** `pick_top` sorts once and then stops after selecting at most 20 funds (`fundexpert/select/pick.py:23-49`). At current row counts this is not a bottleneck.
- **Frontend rendering:** The allocation chart is lazy-loaded (`frontend/src/App.jsx:1-12`, `116-125`) and portfolio/chart collections are limited to at most 20 rows. No material rerender hotspot was identified.
- **Docs/startup:** Generated pdoc output is not imported by application startup. `scripts/refresh-docs.ps1` scans generated HTML/JS only when explicitly invoked; it does not affect API or CLI runtime.

## Methods and commands

- Inspected the full tracked source and recent changes with `rg --files`, targeted `rg -n` searches, `git log --oneline 8bbb62d3..HEAD`, and `git diff 8bbb62d3..HEAD`.
- Timed `resolve_active_bundle`, cold/warm `get_cached_candidates`, and 30 no-news pipeline runs with `time.perf_counter` and `statistics.median` using `.venv/Scripts/python.exe`.
- Profiled 20 no-news pipeline runs with `cProfile`/`pstats` against the current 1,044-row TEFAS bundle.
- Measured dataframe memory with `DataFrame.memory_usage(deep=True)` and inspected active CSV sizes.
- Used an in-process two-thread barrier probe to verify duplicate `_load_candidates` calls on a concurrent cold miss. The probe modified only the temporary Python process and wrote no repository files.
- No network benchmark was run and no external service was contacted. The news worst-case is derived directly from configured caps, retry count, and timeouts.
- This reviewer made no source, dependency, configuration, test, or documentation changes. Only this report was replaced.
