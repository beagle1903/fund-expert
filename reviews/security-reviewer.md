# Security Review - fundexpert

**Review date:** 2026-08-04

**Reviewed revision:** `afb02eae4da6` (detached checkout; `origin/main` and `main` point to the same commit)

**Prior reviewed revision:** `8bbb62d3c1301dfebf90b456f91b8548bd3c3738`

**Product-code changes made by this reviewer:** none

## Executive summary

The review found no P0 issue, one P1 issue, and six P2 issues. The most important new risk is the local FastAPI service: it accepts arbitrary `Host` values and has no authentication, origin/CSRF control, or other trust check around endpoints that rewrite selection rules, publish refreshed data, and spend the process's Tavily credential. Binding Uvicorn to loopback does not by itself stop browser DNS-rebinding attacks.

The new TEFAS acquisition and bundle publication paths otherwise have meaningful safeguards: fixed HTTPS destinations, strict universe values, fixed filenames, per-file size checks before pandas parsing, schema/numeric/code-set checks, content-derived immutable IDs, validation before activation, and atomic `current.json` replacement. The Tavily credential remains environment-only and is not persisted. No command execution, `eval`, pickle, unsafe YAML loading, upload handling, or user-controlled outbound URL was found.

The prior review's path-traversal concern in `load_candidates_for_universe()` is closed: it now delegates to `resolve_active_bundle()`, which validates the universe before constructing any path (`fundexpert/data/loader.py:81-87`, `fundexpert/data/bundle.py:291-294`). The prior Tavily allowlist, query-construction, and malformed-response findings remain open at current line numbers.

## Findings

### P0

None.

### P1-1 - Local API is vulnerable to DNS rebinding and has no authorization boundary

**Severity:** P1 (high)

**Status:** Confirmed on the current application

**Evidence**

- `fundexpert/api.py:43` creates the FastAPI application without `TrustedHostMiddleware`, authentication, a session-bound capability, or an origin check.
- `fundexpert/api.py:384-394` exposes a data-refresh operation that performs outbound network acquisition and publishes files.
- `fundexpert/api.py:433-446` exposes a persistent rewrite of `fundexpert/rules.json`.
- `fundexpert/api.py:449-452,482-500` lets a request trigger refresh and optional Tavily queries using the process's `TAVILY_API_KEY`.
- `README.md:94` and `AGENTS.md:17` use Uvicorn's loopback default, but loopback binding is not a DNS-rebinding defense.
- A `TestClient` request with `Host: attacker.example:8000` returned `200` for both `/openapi.json` and `/api/data-status`. There are no tests asserting rejection of an untrusted host or origin.

**Impact**

A hostile web page can be served from an attacker-controlled host and then rebind that hostname to `127.0.0.1`. Because the browser still considers the requests same-origin and the API accepts the attacker's `Host`, the page can reach local endpoints without a CORS bypass. It can persist attacker-chosen classification/exclusion rules and influence future recommendations, repeatedly refresh local data, or launch Tavily work using the user's credential. Direct non-browser access is also unrestricted if the service is ever bound beyond loopback.

**Concrete remediation**

Add `TrustedHostMiddleware` with an explicit loopback allowlist (`localhost`, `127.0.0.1`, and `[::1]`) and tests that reject arbitrary and suffix-confusion hostnames. Require a randomly generated, session-bound capability/CSRF token for every state-changing or credential-consuming endpoint and validate `Origin`/`Sec-Fetch-Site` as defense in depth. Keep Uvicorn loopback-only by default; if remote access is supported later, require real authentication and TLS rather than widening the host list. Do not add wildcard CORS.

### P2-1 - API body size and exclusion-keyword length are unbounded

**Severity:** P2 (medium)

**Status:** Confirmed

**Evidence**

- `fundexpert/api.py:143-148` caps the number of rules but declares exclusions as plain `list[str]`; unlike classification keywords at `fundexpert/api.py:131`, each exclusion string has no length bound.
- `fundexpert/api.py:433-437` serializes accepted values and atomically writes them to the package rules file.
- No application or documented server configuration sets a maximum request-body size.
- `SelectionRules.model_validate()` accepted a single exclusion string of 1,000,000 characters during this review.

**Impact**

Any caller that reaches the service can force Starlette/Pydantic to buffer and parse a very large JSON body, then persist a very large rules file. Repetition can exhaust memory, CPU, or disk and make all later rule loads and portfolio generation expensive. Field validation alone is too late to protect JSON parsing from an oversized request.

**Concrete remediation**

Enforce a small request-body limit before `request.json()`/Pydantic parsing, at the ASGI server or an early middleware that correctly handles chunked bodies. Give every exclusion string a bounded constrained type (for example 120 characters, aligned with classification keywords), and consider a total serialized-rule budget. Add tests for oversized `Content-Length`, chunked/streamed overflow, a maximum-size valid request, and an overlong exclusion.

### P2-2 - TEFAS responses are read and parsed without a byte or row ceiling

**Severity:** P2 (medium)

**Status:** Confirmed in the new web-export adapter

**Evidence**

- `fundexpert/data/tefas_export.py:157-180` calls `response.read()` with no size and then decodes/parses the complete remote JSON into memory.
- A fake response used during the review observed `read(size=-1)`, confirming the unbounded read.
- `fundexpert/data/tefas_export.py:270-275,284-290` enforces only minimum row counts; there is no maximum response size, row count, or per-field length.
- The 50 MiB check in `fundexpert/data/bundle.py:204-214` happens only after the response has already been read, parsed, retained as Python objects, and written as CSV.
- `tests/test_tefas_export.py:216-235` covers malformed JSON and shape, but not oversized responses or excessive rows/fields.

**Impact**

A malfunctioning or compromised upstream can return an arbitrarily large body. One `/api/data-refresh` request can exhaust process memory before bundle validation has an opportunity to fail closed. TLS authenticates the current endpoint but does not make response size trustworthy.

**Concrete remediation**

Define a conservative maximum compressed and decompressed response size plus a maximum row count. Reject an excessive `Content-Length`, read at most `limit + 1` bytes, and fail before JSON parsing if the limit is crossed. After parsing, bound row count and the size/type of every selected field. Add tests for missing/misleading `Content-Length`, chunked overflow, exact-boundary input, too many rows, and an oversized string field.

### P2-3 - Tavily's domain allowlist is not enforced on returned or cached hits

**Severity:** P2 (medium)

**Status:** Confirmed; inherited from the prior review

**Evidence**

- `fundexpert/config.py:98-115` defines a curated source allowlist and defense-in-depth issuer denylist.
- `fundexpert/news/tavily.py:162-164` only asks Tavily to apply `include_domains` server-side.
- `fundexpert/news/tavily.py:193-215` accepts returned URLs without checking their scheme or hostname against `allowed_domains`; `fundexpert/news/tavily.py:267` applies only the substring denylist.
- `fundexpert/news/tavily.py:103-123,248-251` returns fresh cache entries without revalidating their URLs against the current security policy.
- A mocked response for `https://evil.example/phish` was returned as a hit even when `allowed_domains=("dunya.com",)`.
- `frontend/src/components/NewsResults.jsx:3-12` renders every accepted remote URL as a clickable external link.

**Impact**

An unexpected, compromised, or schema-drifted search response can penalize a fund and alter a financial recommendation using a source outside the configured trust set. It also presents an off-policy link to the user. This finding does not assert that Tavily currently violates `include_domains`; it removes a single-provider trust assumption at a decision-changing boundary.

**Concrete remediation**

Before keyword matching, require an `https` URL whose normalized hostname is either exactly an allowed domain or a true subdomain (`host == allowed` or `host.endswith("." + allowed)`). Reject embedded credentials, invalid ports, and malformed hosts. Reapply the same validator when reading cache entries. Add exact-host, subdomain, suffix-confusion, IDNA, userinfo, non-HTTPS, malformed, off-list, and poisoned-cache tests.

### P2-4 - Tavily and cache schemas can escape the documented fail-soft boundary

**Severity:** P2 (medium)

**Status:** Confirmed; inherited from the prior review

**Evidence**

- `fundexpert/news/tavily.py:103-123` assumes the cache root, hit list, hit mappings, and required field types without validation.
- `fundexpert/news/tavily.py:185,193-213` assumes a mapping response with a list of mapping results and string `title`, `url`, and `content` fields.
- `fundexpert/news/tavily.py:262-265` catches transport/timeout/JSON-decode errors, but not `KeyError`, `TypeError`, or `AttributeError` caused by a valid-JSON schema violation.
- A fresh cache entry containing `{"hits":[{}]}` caused `query_negative_news()` to raise `KeyError: 'title'` during this review.
- `tests/test_news_tavily.py:121-131,187-202` covers malformed JSON and read errors, but not valid JSON with invalid field shapes/types.

**Impact**

Corrupt local cache data or upstream schema drift can break the advertised fail-soft behavior. Worker-level handling in `fundexpert/news/penalty.py:94-103` avoids a whole-process crash in the normal pipeline, but it silently fails open for the affected issuer; direct library callers receive an exception, and malformed cached types can fail later during API projection or rendering.

**Concrete remediation**

Introduce one bounded decoder for network and cache payloads. Require mapping roots, bounded lists, mapping items, bounded strings, and valid allowed HTTPS URLs. Skip invalid siblings while retaining valid results, translate structural failures into a dedicated parse exception, and catch that exception at `query_negative_news()`. Add malformed-root, missing-field, wrong-type, oversized-field, corrupt-cache, and mixed-valid/invalid tests.

### P2-5 - Fund names can alter Tavily query syntax

**Severity:** P2 (medium)

**Status:** Confirmed; inherited from the prior review and now reachable from automated TEFAS data

**Evidence**

- `fundexpert/news/match.py:35-49` derives a company prefix from the fund name without bounding length or restricting query operators/control characters.
- `fundexpert/news/tavily.py:53-58` interpolates the prefix inside quotes and appends an `OR` expression without escaping quotes, backslashes, parentheses, or line breaks.
- The input path now includes remotely acquired TEFAS strings: `fundexpert/data/tefas_export.py:183-208` converts selected upstream values to CSV verbatim, and `fundexpert/data/loader.py:58-66` loads fund names.
- A prefix of `ACME" OR "VICTIM PORTFOLIO` produced a query structurally equivalent to `"ACME" OR "VICTIM PORTFOLIO" (ceza)`.

**Impact**

A corrupted or unexpected upstream fund name can broaden or redirect the negative-news search and therefore manipulate which fund receives the fixed score penalty. JSON encoding prevents HTTP-header injection, and the upstream source is normally official TEFAS, so this remains a medium trust-boundary issue rather than arbitrary code execution.

**Concrete remediation**

Prefer a Tavily request mode that treats the issuer as data without query-language interpolation. If query syntax is unavoidable, normalize and tightly bound the prefix, reject control characters, and escape every Tavily query metacharacter according to the provider's documented grammar. Add quote, backslash, parenthesis, `OR`, CR/LF, excessive-length, and Unicode tests.

### P2-6 - Integrity locks are process-local and permit lost updates under multi-worker deployment

**Severity:** P2 (medium)

**Status:** Confirmed design limitation

**Evidence**

- `fundexpert/data/refresh.py:37,71-98` protects acquisition/publication with `threading.Lock`, which coordinates threads in only one Python process.
- `fundexpert/utils/rules.py:14,48-75` likewise serializes read-modify-replace rule updates only within one process.
- `fundexpert/data/bundle.py:334-400` atomically publishes a bundle and pointer but has no cross-process transaction/lock covering duplicate destination creation and pointer activation.
- The API can be launched by any valid Uvicorn topology; the repository does not reject or document multi-worker use.

**Impact**

With multiple workers or separate CLI/API processes, simultaneous rule updates can each read the same old file and silently discard one caller's changes. Simultaneous forced refreshes can race destination creation or produce nondeterministic last-writer activation. Atomic replacement protects file syntax, but not the higher-level read-modify-write transaction or intended ordering.

**Concrete remediation**

Either enforce and document a single-worker process model or use an OS-visible lock scoped to the data/rules directory. Hold the rules lock across read, validation, temporary write, replace, cache invalidation, and reread. Hold a refresh/publication lock across freshness recheck, acquisition, destination creation, and pointer activation. Add multiprocess tests proving that one update is rejected with `409` or serialized and that concurrent publication never loses an acknowledged update.

## Checks performed

- Recorded and reviewed `git status`, revision `afb02eae4da6`, recent history, and `git diff 8bbb62d3..HEAD`. The security-relevant delta is primarily the FastAPI/Vite UI, versioned bundle publication, web-export refresh, founder attribution, and editable rules.
- Read all product Python modules and the frontend's API/data rendering paths; searched for secrets, unsafe deserialization, command execution, dangerous browser sinks, arbitrary outbound URLs, path construction, file mutation, and synchronization.
- Ran `.venv/Scripts/python.exe -m bandit -r fundexpert -f txt`. Bandit reported one medium B310 at `fundexpert/news/tavily.py:181`; it was triaged as a scheme-selection false positive because the request target is the constant HTTPS endpoint at line 29, the request is explicitly checked at lines 173-174, and the platform validating TLS context is used. The response URL/source findings above remain independently valid.
- Ran `npm audit --omit=dev --json` in `frontend`: zero production dependency advisories were reported. `pip-audit` is not installed; Python dependency upgrade/advisory work belongs to the parallel dependency reviewer.
- Ran secret and private-key filename/pattern scans across tracked source and recent history. Only documented environment-variable names and explicit test keys were found; no tracked credential or key file was identified.
- Exercised the arbitrary-Host acceptance, million-character exclusion validation, TEFAS unbounded `read()`, off-allowlist Tavily result, query construction, and malformed cache behavior with in-memory or temporary-directory probes. No product or data file was modified.
- A focused 92-test security subset passed every collected test, but the command exited nonzero because running only that subset produced 70.73% aggregate coverage below the repository-wide 90% gate. In accordance with the test-first protocol, the complete suite was run immediately afterward: **332 passed**, **94.55% coverage**, exit code 0.

## Positive controls verified

- Strict Pydantic request models reject unknown fields and bound most public scalar controls (`fundexpert/api.py:46-63,105-109,128-169`).
- Unexpected generation and rule-write exceptions are logged server-side but returned with generic messages (`fundexpert/api.py:438-446,508-516`); the tests verify that sensitive exception strings do not reach responses.
- Universe values are fixed before data path construction (`fundexpert/data/bundle.py:131-133,291-294`; `fundexpert/data/refresh.py:61-64`). Bundle filenames are constants, not request values.
- Bundle validation checks file presence/size, required schemas, numeric values, duplicate/non-empty codes, exact cross-file code coverage, reported row counts, and export-time skew before activation (`fundexpert/data/bundle.py:192-278`). Published data is revalidated after copying and addressed by a content-derived ID before `current.json` is atomically replaced (`fundexpert/data/bundle.py:334-400`).
- The Tavily and TEFAS request endpoints are constants using HTTPS and validating platform TLS (`fundexpert/news/tavily.py:29,165-181`; `fundexpert/data/tefas_export.py:17,147-168`). There is no user-controlled SSRF destination.
- `TAVILY_API_KEY` is loaded from the environment only when news is enabled and is sent only in the Tavily POST body; it is not written to history, caches, rules, snapshots, or frontend responses (`fundexpert/api.py:482-497`; `fundexpert/news/tavily.py:150-172`).
- Editable user keywords use literal substring matching (`regex=False`) rather than regex evaluation (`fundexpert/select/strategy.py:18-28`; `fundexpert/select/sector.py:27-38`). React renders remote text through normal escaped JSX, with no `dangerouslySetInnerHTML` sink.
- Cache, UI-state, history, rules, bundle, and active-pointer writes use same-directory temporary files/directories plus atomic replacement. No product-code `eval`, `exec`, pickle, unsafe YAML load, shell execution, subprocess call, or uploaded filename handling was found.

## Priority

Fix P1-1 before treating the web service as safely reachable from a browser. P2-1 is the natural companion hardening change. Then address the two remote-data bounds/validation gaps (P2-2 through P2-5), followed by cross-process locking if multi-worker or concurrent CLI/API operation is supported.
