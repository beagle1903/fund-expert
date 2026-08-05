# Weekly Parallel Code Health Review — 2026-08-04

## Outcome

- Reviewed detached commit `afb02eae4da6ceded239610fcab32af4820d4780`; the starting tree was clean.
- Comparison base from the previous weekly run: `8bbb62d3c1301dfebf90b456f91b8548bd3c3738`.
- Seven specialist reports completed. No P0 finding was identified.
- Baseline: **332 passed**, **94.55% coverage**.
- Final combined validation in the isolated upgraded Python environment: **332 passed in 40.31s**, **94.55% coverage**.
- Frontend: **3 files / 15 tests passed**, lint passed, production build passed, and `npm audit` reported **0 vulnerabilities**.
- Ruff passed. Vulture's 32 low-confidence findings were reviewed as Pydantic/FastAPI registrations or compatibility exports; no production deletion was justified.
- `pip check` and `git diff --check` passed.
- No files were staged or committed; nothing was pushed and no pull request was opened.

## P0 — Critical

None.

## P1 — High priority

### 1. Retail recommendations do not exclude Serbest/restricted funds

- **Severity:** P1
- **Evidence:** The active TEFAS bundle has 376 Serbest rows, and six of eight default picks were Serbest. The only configured exclusion is `OKS`; eligibility is absent from `fundexpert/rules.json:44`, `fundexpert/data/merge.py:36-49`, and `fundexpert/pipeline.py:87-99`.
- **Affected code:** `fundexpert/rules.json:44`, `fundexpert/data/merge.py:36-49`, `fundexpert/pipeline.py:87-99`, `fundexpert/api.py:46-63`, `fundexpert/ui.py:37-127`.
- **Expected impact:** A normal retail user can receive a portfolio dominated by products they may not be eligible to buy, making the recommendation operationally unusable and unsuitable.
- **Actionable agent prompt:** "Add a controlled investor-eligibility policy with a safe retail default and an explicit qualified-investor opt-in. Filter restricted products before scoring, surface the assumption and excluded count in API/CLI output, and add fixture plus active-data tests proving retail portfolios contain no restricted funds while qualified runs may include them. Keep this policy separate from editable keyword rules and run the full Python and frontend suites."

### 2. Low risk is a soft preference, not a suitability ceiling

- **Severity:** P1
- **Evidence:** `fundexpert/scoring/score.py:54-64` applies only a quadratic penalty; it never caps SRRI. A reproduced low-risk BEFAS run with 20 funds selected an SRRI-5 fund, while both clients label the control as a risk level (`fundexpert/ui.py:75-78`, `frontend/src/components/ControlPanel.jsx:67-72`).
- **Affected code:** `fundexpert/config.py:26-30`, `fundexpert/scoring/score.py:54-64`, `fundexpert/pipeline.py:96-109`, both client controls.
- **Expected impact:** Users reasonably interpreting “low risk” as a suitability boundary can receive materially higher-risk products.
- **Actionable agent prompt:** "Define and implement the Fundexpert risk contract. Prefer explicit SRRI ceilings by risk band, applied before normalization/scoring, with a conservative missing-SRRI policy and a visible warning when N cannot be filled. Add selection invariants and API/CLI/UI contract tests. If the product intentionally uses only a soft penalty, rename and explain the control everywhere instead."

### 3. Horizon scoring compares non-comparable cumulative returns

- **Severity:** P1
- **Evidence:** `fundexpert/scoring/horizon.py:8-15` averages raw 1m/3m, 6m/1y, or 3y/5y cumulative percentages and accepts rows with only the shorter period. In active TEFAS data, median 3y return was 165.96% versus 618.28% for 5y, while 213 funds had 3y but no 5y.
- **Affected code:** `fundexpert/config.py:31-35`, `fundexpert/scoring/horizon.py:8-15`, `tests/test_horizon.py:23-64`.
- **Expected impact:** Ranking can reflect period scale and fund age rather than superior comparable performance; incomplete histories use a different formula from complete histories.
- **Actionable agent prompt:** "Redesign horizon scoring around comparable periodic returns. Annualize multi-year cumulative returns, define the short/medium conversion, and explicitly choose either a 5y eligibility rule or a missing-period penalty. Reject impossible inputs, compare old/new rankings on active data, add complete-versus-incomplete property tests, document the migration, and run the full suite."

### 4. The volume-change control scores absolute AUM

- **Severity:** P1
- **Evidence:** The loader exposes `aum_change_pct`, but `fundexpert/scoring/score.py:33` builds the volume feature from `log1p(aum_last)`. The CLI says `Hacim değişimi önceliği` and the web says `Volume Priority`.
- **Affected code:** `fundexpert/data/loader.py:24-35`, `fundexpert/scoring/score.py:24-52`, `fundexpert/ui.py:89-92`, `frontend/src/components/ControlPanel.jsx:85-90`, `docs/03-scoring-engine.md:23-29`.
- **Expected impact:** Raising the advertised change/flow preference favors already-large funds, potentially producing the opposite ranking from the user's intent.
- **Actionable agent prompt:** "Choose one volume-feature contract. If size/liquidity is intended, rename the field, API, clients, saved settings, and docs to fund-size priority. If growth is intended, score a robustly clipped `aum_change_pct`. Add a two-fund regression where absolute AUM and AUM growth point in opposite directions, migrate compatibility safely, and run all tests."

### 5. Local mutating API endpoints lack a browser trust boundary

- **Severity:** P1
- **Evidence:** `fundexpert/api.py:43` installs no trusted-host, authentication, origin, or capability control. Arbitrary `Host` values were accepted. Endpoints at `fundexpert/api.py:384-394`, `433-446`, and `449-500` can refresh/publish data, rewrite rules, and consume the Tavily credential.
- **Affected code:** `fundexpert/api.py:43-500`, server startup documentation, API tests.
- **Expected impact:** A DNS-rebinding page or an accidentally non-loopback deployment can mutate local recommendation state or spend the user's search credential.
- **Actionable agent prompt:** "Harden the local FastAPI boundary. Add `TrustedHostMiddleware` for exact loopback hosts, a random session-bound capability/CSRF token for state-changing or credential-consuming endpoints, and Origin/Sec-Fetch-Site checks as defense in depth. Keep loopback-only startup, reject suffix-confusion hosts, add browser-style DNS-rebinding tests, and do not enable wildcard CORS."

### 6. Recommendation records are not reproducible

- **Severity:** P1
- **Evidence:** Mutable rules and resolved caps affect picks, but `fundexpert/pipeline.py:166-199`, `fundexpert/api.py:482-524`, and `fundexpert/history/store.py:22-42` omit combinations of bundle ID/file hashes, rules hash, founder, momentum, diversification mode, resolved caps, news context, and code/model version.
- **Affected code:** `fundexpert/pipeline.py:30-199`, `fundexpert/api.py:172-524`, `fundexpert/cli.py:110-143`, `fundexpert/history/store.py:10-42`, `fundexpert/utils/rules.py:17-24`.
- **Expected impact:** Historical drift cannot be attributed to data, rules, policy, configuration, or code changes; web output has no durable audit record.
- **Actionable agent prompt:** "Create a versioned `RecommendationManifest` shared by CLI and API. Include bundle ID and file hashes, canonical full-rules SHA-256, every request input, resolved caps, scoring/news config version, application revision, warnings, and picks. Persist it through one history seam, return/print it, add round-trip reconstruction tests, and prove that materially different rules or snapshots yield distinct contexts."

### 7. The CLI offers founders absent from the active bundle

- **Severity:** P1
- **Evidence:** The API derives options from active candidates (`fundexpert/api.py:397-415`), but the CLI uses the static catalog before loading data (`fundexpert/ui.py:48-73`, `fundexpert/cli.py:110-123`). Current TEFAS has 60 present founders versus 61 catalog entries; choosing absent `HAS PORTFÖY YÖNETİMİ A.Ş.` raises an uncaught `ValueError`.
- **Affected code:** `fundexpert/ui.py:48-73`, `fundexpert/founders.py:159-194`, `fundexpert/cli.py:71-150`, `fundexpert/pipeline.py:87-94`.
- **Expected impact:** A valid choice offered by the application can terminate an interactive run with a traceback, and CLI/API valid configurations differ.
- **Actionable agent prompt:** "Introduce one bundle-loading service that returns candidates, manifest, and current founder counts. Use it before both API and CLI selection; build CLI choices from active candidates, reuse the same snapshot for generation, handle a late empty-founder race with a user-facing retry, and add a catalog-present/bundle-absent regression test."

### 8. Warm candidate-cache hits still fully parse and hash every CSV

- **Severity:** P1
- **Evidence:** `get_cached_candidates` resolves and fully validates the active bundle before checking the cache (`fundexpert/api.py:279-303`; `fundexpert/data/bundle.py:291-324`). Measured warm validation was 24.53 ms median versus 36.08 ms for the no-news pipeline; cold misses parse the CSVs again during loading.
- **Affected code:** `fundexpert/api.py:274-303`, `fundexpert/data/bundle.py:136-324`, `fundexpert/data/bundle.py:418-424`.
- **Expected impact:** The cache avoids little of the dominant I/O/integrity cost, and repeated founder/generate/status requests amplify it.
- **Actionable agent prompt:** "Refactor the active-bundle cache to use a cheap validated pointer plus manifest/CSV stat signature on warm reads, retaining full validation on first access, signature change, or explicit integrity checks. Reuse parsed frames on cold fill if practical. Add call-count tests proving warm hits skip hashing/parsing while pointer changes, deletion, and tampering still fail closed."

### 9. News generation has no global work budget or deadline

- **Severity:** P1
- **Evidence:** One request can schedule up to 60 searches, create a 25-thread pool, and retry each query three times with 10-second socket timeouts (`fundexpert/config.py:87-118`, `fundexpert/news/penalty.py:69-101`, `fundexpert/news/tavily.py:150-190`). Concurrent requests create additional pools, and client abort does not cancel synchronous backend work.
- **Affected code:** `fundexpert/news/penalty.py:59-107`, `fundexpert/news/tavily.py:103-270`, `fundexpert/api.py:449-500`, `frontend/src/App.jsx:22-45`.
- **Expected impact:** A degraded Tavily service can occupy request workers for roughly 99 seconds, multiply threads/calls, consume quota, and degrade the local app.
- **Actionable agent prompt:** "Bound the optional news pass end to end. Use a shared process-wide executor or semaphore, add a strict monotonic request deadline including retries and queue time, cancel pending work at expiry, coalesce identical cold cache keys, and report partial/time-out metadata. Add deterministic concurrency and deadline tests, then run the full suite."

### 10. Atomic bundle publication lacks mid-transaction failure tests

- **Severity:** P1
- **Evidence:** `fundexpert/data/bundle.py:334-415` validates, copies, replaces the immutable directory, and swaps `current.json`, but `tests/test_data_bundle.py:133-165` fails only before copy/publication. Branch-aware coverage leaves pointer/manifest validation, idempotent reuse, mutation detection, and cleanup branches untested.
- **Affected code:** `fundexpert/data/bundle.py:281-415`, `tests/test_data_bundle.py:100-165`.
- **Expected impact:** A regression around disk/permission/replace failures could advance the pointer incorrectly or leave invalid/temporary state while the suite remains green.
- **Actionable agent prompt:** "Add Windows-safe fault-injection tests around every `publish_bundle` mutation boundary: copy, copied validation, destination replace, and pointer replace. Preserve and assert exact old pointer bytes and resolvability after each failure, verify temporary cleanup, cover idempotent re-publication, and reject malformed pointer/manifest schema, universe, bundle ID, and persisted metadata."

### 11. Rule-editor failure and retry state is largely untested

- **Severity:** P1
- **Evidence:** `frontend/src/components/RuleEditor.jsx:102-179` implements asynchronous load/save/error behavior, but tests cover only successful strategy save/rebuild and duplicate blocking (`frontend/src/App.test.jsx:274-339`). GET/PUT failure, retry, pending, cancel, abort, sector/exclusion edits, and most validation paths are absent.
- **Affected code:** `frontend/src/components/RuleEditor.jsx:58-351`, `frontend/src/App.jsx:89-92`, `frontend/src/App.test.jsx:274-339`.
- **Expected impact:** Failed writes can close the editor, rebuild from stale rules, duplicate writes, lose edits, or leave the UI stuck without detection.
- **Actionable agent prompt:** "Create focused `RuleEditor.test.jsx` coverage for failed GET, failed PUT then successful retry, pending-save state, cancel/unmount abort, and strategy/sector/exclusion add-edit-delete-reorder. Assert failed saves keep the dialog open and never call `onSaved` or `/api/generate`; parameterize all validation outcomes and run tests, lint, and build."

## P2 — Medium priority

### 1. API payload and exclusion lengths are unbounded

- **Severity:** P2
- **Evidence:** Exclusions are plain `list[str]` with no per-string bound (`fundexpert/api.py:143-148`), and no early request-body limit is configured. A one-million-character exclusion validated successfully.
- **Affected code:** `fundexpert/api.py:128-169`, `fundexpert/api.py:433-446`.
- **Expected impact:** Reachable callers can consume memory/CPU/disk and make later rule loads expensive.
- **Actionable agent prompt:** "Add an early ASGI body-size limit that handles Content-Length and streaming/chunked overflow, constrain exclusion lengths and total serialized rules size, and test exact-boundary, overlong, and streamed-overflow requests."

### 2. TEFAS responses have no byte, row, or field ceiling

- **Severity:** P2
- **Evidence:** `fundexpert/data/tefas_export.py:157-180` calls unbounded `response.read()` and parses the entire body; later bundle checks occur only after materialization. Only row floors are enforced at `fundexpert/data/tefas_export.py:270-290`.
- **Affected code:** `fundexpert/data/tefas_export.py:147-208,270-298`, related tests.
- **Expected impact:** A malfunctioning upstream can exhaust process memory before fail-closed bundle validation runs.
- **Actionable agent prompt:** "Bound TEFAS compressed/decompressed bytes, rows, and selected-field lengths. Reject excessive Content-Length, read at most limit+1 bytes, fail before JSON parsing, and add missing/misleading-length, chunked overflow, boundary, excessive-row, and oversized-field tests."

### 3. Tavily result/query/cache validation is incomplete

- **Severity:** P2
- **Evidence:** Returned and cached URLs are not locally checked against the allowlist (`fundexpert/news/tavily.py:103-123,193-215`); valid-JSON schema errors can escape fail-soft handling; and unescaped fund prefixes can alter query syntax (`fundexpert/news/match.py:35-49`, `fundexpert/news/tavily.py:53-58`).
- **Affected code:** `fundexpert/news/match.py:28-49`, `fundexpert/news/tavily.py:53-270`, `frontend/src/components/NewsResults.jsx:3-12`.
- **Expected impact:** Off-policy or malformed results can alter scores, surface unsafe links, fail open, or redirect search semantics.
- **Actionable agent prompt:** "Create one bounded Tavily/cache decoder that validates mapping/list/string schemas and exact HTTPS allowlisted hosts, revalidates cached hits, skips invalid siblings, and safely handles corrupt roots. Bound and escape issuer query data or use a provider mode that treats it as data. Add off-list, suffix-confusion, IDNA, malformed schema/cache, oversized field, quote/operator, and control-character tests."

### 4. Refresh and editable-rule coordination is only process-local

- **Severity:** P2
- **Evidence:** Refresh and rules use `threading.Lock` (`fundexpert/data/refresh.py:36-98`, `fundexpert/utils/rules.py:14-75`), rules are overwritten inside package data with last-write-wins PUT, and one global refresh lock serializes both universes. Existing refresh contention tests replace the lock rather than exercise real callers.
- **Affected code:** `fundexpert/data/refresh.py:36-98`, `fundexpert/data/bundle.py:334-401`, `fundexpert/utils/rules.py:13-75`, `fundexpert/api.py:418-446`, `tests/test_data_refresh.py:90-143`.
- **Expected impact:** CLI/API workers can race publication or lose/stale rule updates; TEFAS unnecessarily blocks BEFAS; installation upgrades can overwrite user rules.
- **Actionable agent prompt:** "Move editable rule overrides to a user-data directory, add revision/ETag conflict detection, and use cross-process per-universe refresh locks plus an OS-visible rule lock/fingerprint reload. Treat concurrent identical bundle creation as idempotent success. Add thread and multiprocessing tests for same-universe busy, different-universe overlap, stale rule PUT rejection, failure recovery, and lock release."

### 5. Concurrent cold cache misses duplicate loading

- **Severity:** P2
- **Evidence:** The cache lock is released before `_load_candidates` (`fundexpert/api.py:286-303`); a two-thread probe observed two loads for the same universe.
- **Affected code:** `fundexpert/api.py:279-303`.
- **Expected impact:** Startup and post-refresh bursts duplicate CSV parsing/merging and dataframe allocation.
- **Actionable agent prompt:** "Add per-universe single-flight state to `get_cached_candidates`: one loader, same-universe waiters sharing success/failure, independent TEFAS/BEFAS fills, and guaranteed in-flight cleanup. Add a barrier-based two-thread test asserting exactly one load."

### 6. Static strategy/sector classification is recomputed every run

- **Severity:** P2
- **Evidence:** `fundexpert/pipeline.py:96-114` reruns classification for each request; profiling attributed about 46% of pipeline CPU to name normalization/classification across 13 strategy and 25 sector rules.
- **Affected code:** `fundexpert/pipeline.py:96-114`, `fundexpert/select/strategy.py:18-28`, `fundexpert/select/sector.py:20-38`, rule-cache invalidation.
- **Expected impact:** Interactive regeneration repeatedly pays a cost determined only by bundle and rules revision.
- **Actionable agent prompt:** "Cache strategy/sector columns by active bundle fingerprint plus canonical rules revision, invalidate immediately after rule save, retain a fallback for arbitrary caller dataframes, add classifier call-count tests, and benchmark active TEFAS before/after."

### 7. Development StrictMode can duplicate expensive initial requests

- **Severity:** P2
- **Evidence:** The production root uses StrictMode (`frontend/src/main.jsx:1-9`), while mount effects independently generate/refresh and load founders (`frontend/src/App.jsx:48-64`). Browser abort does not cancel already-running synchronous backend work; tests do not render the real StrictMode root.
- **Affected code:** `frontend/src/main.jsx:1-9`, `frontend/src/App.jsx:22-64`, refresh busy behavior.
- **Expected impact:** Development startup can duplicate validation/network work or produce a self-inflicted `REFRESH_BUSY` response.
- **Actionable agent prompt:** "Coalesce identical in-flight bootstrap requests or provide one idempotent bootstrap resource that survives StrictMode setup/cleanup. Preserve stale-response and unmount handling, and add a StrictMode test proving one underlying generation/refresh and founder load."

### 8. Fee priority ignores the available total-expense field

- **Severity:** P2
- **Evidence:** Export includes `Yıllık Azami Fon Toplam Gider Oranı (%)`, but `fundexpert/data/loader.py:37-43,58-66` does not ingest it; scoring uses only management fee.
- **Affected code:** `fundexpert/data/tefas_export.py:49-62`, `fundexpert/data/loader.py:37-66`, `fundexpert/scoring/score.py:34-50`, client labels.
- **Expected impact:** The generic fee control can order funds using only one cost component and imply broader cost comparison than provided.
- **Actionable agent prompt:** "Ingest and validate a canonical total-expense metric, define an explicit cost-feature fallback, expose the metric/value used per pick, and add opposing-management-versus-total-cost tests. If management fee remains intentional, rename the control everywhere."

### 9. The uncategorized `other` strategy bypasses diversification caps

- **Severity:** P2
- **Evidence:** `fundexpert/select/pick.py:37-47` exempts `other`; 261/1,044 active TEFAS candidates and four of eight default picks are `other`.
- **Affected code:** `fundexpert/rules.json:2-16`, `fundexpert/select/strategy.py:18-28`, `fundexpert/select/pick.py:37-47`, UI cap copy.
- **Expected impact:** The UI's advertised maximum per strategy does not guarantee actual diversification for a large unclassified pool.
- **Actionable agent prompt:** "Add classification-coverage telemetry and an explicit unknown threshold/warning, expand reviewed rules or add a controlled fallback, show selected unknown counts, and add active-bundle regression tests for maximum unclassified share without treating unknown as diversified."

### 10. Successful TEFAS alignment omits provenance for dropped codes

- **Severity:** P2
- **Evidence:** Up to five non-common codes are removed from all three views at `fundexpert/data/tefas_export.py:211-242`, but `DataBundleManifest` records no excluded codes or missing views (`fundexpert/data/bundle.py:45-118`).
- **Affected code:** `fundexpert/data/tefas_export.py:211-298`, `fundexpert/data/bundle.py:45-118,269-277`.
- **Expected impact:** A top candidate can silently disappear from a successful bundle with no later audit trail.
- **Actionable agent prompt:** "Return structured alignment metadata containing excluded codes, missing views, and original counts; persist and hash it in the immutable manifest; surface a data-quality warning in status/generation responses; and test the five-code boundary and immutable provenance."

### 11. BEFAS news prefixes ignore canonical founder attribution

- **Severity:** P2
- **Evidence:** News derives prefixes only from fund names (`fundexpert/news/penalty.py:65-76`); BEFAS legal names without `PORTFÖY` fall back to three words even though canonical `kurucu` already exists (`fundexpert/data/merge.py:26-30`).
- **Affected code:** `fundexpert/news/match.py:16-49`, `fundexpert/news/penalty.py:65-107`, `fundexpert/data/merge.py:26-30`.
- **Expected impact:** Truncated/ambiguous issuer searches can create false positives or negatives that change the fixed news penalty.
- **Actionable agent prompt:** "Group news searches by canonical `kurucu` and use a normalized legal-entity query name, retaining name parsing only as fallback. Add representative real TEFAS/BEFAS tests proving funds from one founder share one query/result set."

### 12. Scoring documentation contradicts runtime semantics

- **Severity:** P2
- **Evidence:** `docs/03-scoring-engine.md:23-74` describes AUM change rather than size, omits momentum, and reverses low/high risk meaning; `docs/02-data-layer.md:74-77` documents a total-expense field the loader drops.
- **Affected code/docs:** current scoring/config/client code and `docs/02-data-layer.md`, `docs/03-scoring-engine.md`.
- **Expected impact:** Maintainers can test, tune, or explain the wrong financial model.
- **Actionable agent prompt:** "Archive superseded design text or add a prominent runtime-difference table, regenerate a current scoring contract from named constants where practical, and add a docs check for feature names, horizon columns, and risk-band meaning."

### 13. Diversification policy is duplicated across Python and JavaScript

- **Severity:** P2
- **Evidence:** `_DIVERSIFICATION_CAPS` and band logic live in `fundexpert/config.py:51-83`, with a second implementation in `frontend/src/config.js:1-15`; generated responses do not provide resolved caps.
- **Affected code:** backend config/pipeline/API and `frontend/src/config.js`, `frontend/src/components/ControlPanel.jsx:120-130`.
- **Expected impact:** Backend changes can leave the UI displaying a cap different from the one used for selection.
- **Actionable agent prompt:** "Make the backend the diversification-policy source of truth by exposing the policy or resolved caps, render server-provided values, remove JS scheduling logic, and add an API/UI contract test."

### 14. News cache identity omits request-shaping parameters

- **Severity:** P2
- **Evidence:** `_cache_key()` includes query and domain lists but omits `max_age_days` and `max_results` even though they shape requests (`fundexpert/news/tavily.py:81-86,218-260`).
- **Affected code:** `fundexpert/news/tavily.py:81-269`, `tests/test_news_tavily.py:291-304`.
- **Expected impact:** Changed news policy can reuse evidence cached under a previous lookback/result cap.
- **Actionable agent prompt:** "Version the cache key and payload with a canonical descriptor containing query, domain policy, lookback, result cap, and search settings; reject descriptor mismatches and add one invalidation test per parameter."

### 15. Pipeline defaults share mutable singleton configuration

- **Severity:** P2
- **Evidence:** Mutable config dataclasses/dictionaries are stored in module-level defaults, and `PipelineConfig` factories return the same objects (`fundexpert/config.py:7-41`, `fundexpert/pipeline.py:47-49`).
- **Affected code:** `fundexpert/config.py:7-41,85-120`, `fundexpert/pipeline.py:30-49`.
- **Expected impact:** One caller mutating tunables can silently alter later runs in the same process.
- **Actionable agent prompt:** "Freeze configuration dataclasses and replace mutable mappings with immutable structures, or deep-copy fresh defaults per pipeline config. Add identity/isolation tests proving one run cannot mutate another."

### 16. Frontend API error normalization lacks direct contract tests

- **Severity:** P2
- **Evidence:** `frontend/src/api/fundexpert.js:9-96` handles several response shapes, but only one structured error is covered indirectly by `frontend/src/App.test.jsx:217-236`.
- **Affected code:** `frontend/src/api/fundexpert.js:1-96`, frontend tests.
- **Expected impact:** FastAPI 422 arrays, proxy text responses, abort signals, or serialized rule writes can regress behind generic UI errors.
- **Actionable agent prompt:** "Add `frontend/src/api/fundexpert.test.js` with mocked fetch cases for string/object/validation-array/malformed/empty responses, status preservation, signals, encoded founders, generate payloads, and rule PUT serialization; then run tests and lint."

### 17. Coverage governance excludes Python branches and frontend metrics

- **Severity:** P2
- **Evidence:** `pyproject.toml:41-46` gates only Python statements, `frontend/vite.config.js:17-22` has no coverage provider, and branch-aware review placed critical `bundle.py` at 83%.
- **Affected code:** `pyproject.toml`, `frontend/vite.config.js`, `frontend/package.json`, `scripts/check.ps1`.
- **Expected impact:** Critical state-machine branches and the entire browser layer can regress while the numerical gate stays green.
- **Actionable agent prompt:** "Enable Python branch coverage and Vitest V8 coverage with sensible production-file exclusions. Add the critical bundle, rule-editor, and API-client tests first, capture honest baseline thresholds, and document deterministic `npm ci` before the check workflow."

## Automated fixes integrated

- Removed eight unused test imports, moved four late imports to module scope, and expanded one one-line guard across eight test files.
- No production code, architecture, or public behavior changed; the post-feature documentation routine was therefore not triggered.
- Final Ruff result: clean. Vulture produced no safe production deletion candidate.

## Dependency results integrated

Successful Python upgrades:

- `annotated-doc` 0.0.4 → 0.0.5
- `annotated-types` 0.7.0 → 0.8.0
- `coverage` 7.15.2 → 7.15.3
- `fastapi` 0.139.2 → 0.141.1
- `hypothesis` 6.156.6 → 6.165.0
- `pandas` 3.0.3 → 3.0.5
- `prompt-toolkit` 3.0.52 → 3.0.53
- `typeguard` 4.5.2 → 4.6.0
- `uvicorn` 0.51.0 → 0.52.1

Successful frontend upgrades:

- `lucide-react` 1.25.0 → 1.28.0
- `recharts` 3.9.2 → 3.10.1
- `@testing-library/user-event` 14.6.1 → 14.6.3
- transitive `postcss` 8.5.19 → 8.5.25, resolving `GHSA-fxqj-rqcc-2cmp`

Rolled back or skipped:

- `pip` 26.2 was rolled back to 26.1.2 because it breaks pip-tools 7.6's `stdlib_pkgs` import; rollback restored pip-compile, pip check, and the full suite.
- `pydantic-core` 2.47.0 is incompatible with Pydantic 2.13.4's exact 2.46.4 requirement and remained unchanged.
- React/react-dom 19.2.8 were restored to 19.2.7 because independent updates are invalid; treat them as one coordinated future change.
- Unsupported-major `@testing-library/jest-dom` 7 and surfaced dev-tool minors were not attempted in this bounded run.

## Changed files

Dependency declarations and lockfiles:

- `pyproject.toml`
- `requirements.txt`
- `frontend/package.json`
- `frontend/package-lock.json`

Automated test cleanup:

- `tests/test_cli.py`
- `tests/test_history_store.py`
- `tests/test_loader.py`
- `tests/test_normalize.py`
- `tests/test_pick.py`
- `tests/test_score.py`
- `tests/test_ui.py`
- `tests/test_weights.py`

Review artifacts:

- `reviews/security-reviewer.md`
- `reviews/architecture-reviewer.md`
- `reviews/test-coverage-reviewer.md`
- `reviews/performance-reviewer.md`
- `reviews/business-logic-reviewer.md`
- `reviews/code-quality-reviewer.md`
- `reviews/dependency-upgrade-reviewer.md`
- `reviews/SUMMARY.md`

## Specialist reports

- [Security reviewer](security-reviewer.md)
- [Architecture reviewer](architecture-reviewer.md)
- [Test-coverage reviewer](test-coverage-reviewer.md)
- [Performance reviewer](performance-reviewer.md)
- [Business-logic reviewer](business-logic-reviewer.md)
- [Code-quality reviewer](code-quality-reviewer.md)
- [Dependency-upgrade reviewer](dependency-upgrade-reviewer.md)
