# Business Logic Review

## Review status

- Reviewer: `business-logic-reviewer`
- Revision reviewed: `afb02eae4da6ceded239610fcab32af4820d4780`
- Comparison base: `8bbb62d3c1301dfebf90b456f91b8548bd3c3738`
- Scope: the complete Python recommendation pipeline, active local TEFAS/BEFAS data, API/CLI behavior, scoring and horizon math, eligibility, founder semantics, diversification, fees, weights, news penalties, bundle alignment, and reproducibility.
- Result: **0 P0, 4 P1, 7 P2 findings**.
- P0 statement: **No P0 findings were identified.**
- P1 statement: P1 findings are present; this report therefore does not claim that there are no P0/P1 findings.
- Source changes: none. This reviewer only replaced this report.
- Shared automation baseline: `332 passed` at the reviewed commit. Because this was a read-only review and no behavior changed, this reviewer did not rerun the complete suite.

## Methods and evidence collected

The review used only local repository state and local active bundles; it made no external calls.

Commands and checks included:

- `git status --short`, `git log --oneline --decorate -12`, `git diff --name-status 8bbb62d3..HEAD`, and targeted full-context diffs for the changed pipeline, API, founder, rule, bundle, and selection modules.
- Line-numbered inspection with `rg -n` across `fundexpert/`, `frontend/src/`, `tests/`, `README.md`, and `docs/`.
- Local scripts through `.venv\Scripts\python.exe -` using `resolve_active_bundle`, `load_candidates_for_universe`, `clean_candidates`, `run_pipeline`, `bucket_from_names`, and `sector_from_names`.
- Cross-view identity comparison of the three active CSV frames without refreshing or publishing data.
- Inspection of scoring, horizon, selection, weight, founder, API, history, bundle, export, and news tests.

Active-data observations used below:

| Universe | Active bundle | Rows | Notable observations |
|---|---:|---:|---|
| TEFAS | `20260802T211420-e012d490f9c5` | 1,044 | 376 Serbest funds; 119 missing SRRI; 261 `other` strategies; 931 `diversified` sectors |
| BEFAS | `20260728T191343-315747f64263` | 310 raw / 220 after exclusions | Complete SRRI; 29 `other` strategies |

The current default medium-risk, medium-horizon, 8-fund TEFAS run selected `DIP, TP2, MBR, KVS, RBR, PKV, PRU, BMU`; six of those eight rows have `Serbest Şemsiye Fonu` as their umbrella. The current low-risk, 20-fund BEFAS run included an SRRI-5 fund. These are deterministic local reproductions, not hypothetical examples.

## P0 — Critical

No P0 findings.

## P1 — High

### BL-01 — Serbest-fund purchase eligibility is not represented and dominates the default TEFAS recommendation

- **Severity:** P1
- **Evidence:** `fundexpert/rules.json:44` excludes only `OKS`. `fundexpert/data/merge.py:36-49` removes missing-fee rows and configured text exclusions but has no eligibility rule. `fundexpert/pipeline.py:87-99` applies only founder, cleaning, and horizon filters before scoring. The active TEFAS bundle contains 376 Serbest rows out of 1,044, and six of the eight default picks (`DIP`, `KVS`, `RBR`, `PKV`, `PRU`, `BMU`) are Serbest funds.
- **Affected code:** `fundexpert/rules.json:44`; `fundexpert/data/merge.py:36-49`; `fundexpert/pipeline.py:87-99`; API request contract at `fundexpert/api.py:46-63`; CLI prompt contract at `fundexpert/ui.py:37-127`.
- **Impact:** A retail user can receive a portfolio mostly composed of funds they may not be eligible to purchase. Even when the user is eligible, the recommendation cannot distinguish that fact, so the same output is shown to materially different investor profiles. This is a suitability and execution failure, not merely a display issue.
- **Concrete remediation:** Add an explicit investor-eligibility field such as `qualified_investor: bool`, defaulting to the safe retail value. Before scoring, exclude rows whose canonical product classification requires qualified-investor eligibility unless the user opted in. Surface the excluded count and eligibility assumption in the header/API response, and add real-data/fixture tests proving that a retail-default run contains no restricted products while an opted-in run can include them. Do not implement this as an editable keyword alone; keep a controlled eligibility policy separate from user-editable diversification rules.

### BL-02 — “Low” risk is only a score preference, not a suitability guardrail

- **Severity:** P1
- **Evidence:** `fundexpert/scoring/score.py:54-64` only subtracts `lambda * ((risk - 1) / 6)^2`; it never filters or caps SRRI. `fundexpert/config.py:26-30` changes only the penalty coefficient. Both clients label the input as a risk level (`fundexpert/ui.py:75-78`, `frontend/src/components/ControlPanel.jsx:67-72`), which reads as a suitability choice rather than a ranking nudge. A local run on the active BEFAS snapshot with `risk_level='low'` and `n=20` selected an SRRI-5 fund.
- **Affected code:** `fundexpert/config.py:26-30`; `fundexpert/scoring/score.py:54-64`; `fundexpert/pipeline.py:96-109`; `fundexpert/ui.py:75-78`; `frontend/src/components/ControlPanel.jsx:67-72`.
- **Impact:** A user identifying as low risk can still be allocated to materially high-volatility products when other features compensate for the penalty. The UI does not disclose that “risk level” is soft, so the result can violate the user’s reasonable suitability expectation.
- **Concrete remediation:** Make a product decision explicit: either (a) introduce policy-backed SRRI ceilings per risk band and apply them before normalization/scoring, with a visible warning when the requested portfolio cannot be filled, or (b) rename the control everywhere to “risk penalty preference” and clearly state that no maximum SRRI is enforced. For a recommendation product, option (a) is safer. Add invariants asserting that selected SRRI never exceeds the configured ceiling and that missing SRRI follows a documented conservative policy.

### BL-03 — The “volume change” control actually rewards absolute fund size

- **Severity:** P1
- **Evidence:** The loader exposes both `aum_last` and `aum_change_pct` (`fundexpert/data/loader.py:24-35`), but `fundexpert/scoring/score.py:33` defines `V_hat` from `log1p(aum_last)`. The resulting contribution is controlled by `volume_priority` at `fundexpert/scoring/score.py:39,49`. The CLI asks for `Hacim değişimi önceliği` at `fundexpert/ui.py:89-92`; the web says `Volume Priority` at `frontend/src/components/ControlPanel.jsx:85-90`. `aum_change_pct` is never used by the scoring pipeline.
- **Affected code:** `fundexpert/data/loader.py:24-35`; `fundexpert/scoring/score.py:24-52`; `fundexpert/ui.py:89-92`; `frontend/src/components/ControlPanel.jsx:85-90`; `docs/03-scoring-engine.md:23-29`.
- **Impact:** Increasing the advertised flow/volume-change preference favors already-large funds rather than funds with stronger AUM growth. A user can make the opposite decision from the one the label implies. It also duplicates part of the liquidity/scale concept while `units_change_pct` separately models investor flow momentum.
- **Concrete remediation:** Choose one explicit feature contract. If scale/liquidity is intended, rename the field and labels to `fund_size_priority`, keep `log1p(aum_last)`, migrate saved settings, and update API/docs/tests. If growth is intended, calculate the contribution from a robustly clipped `aum_change_pct`. Keep `units_change_pct` as a separately named fund-flow signal. Add a two-fund test where absolute AUM and AUM change point in opposite directions so the intended semantic cannot regress silently.

### BL-04 — Horizon scores average non-comparable cumulative returns and compare incomplete histories on a different basis

- **Severity:** P1
- **Evidence:** `fundexpert/config.py:31-35` maps short/medium/long to 1m+3m, 6m+1y, and 3y+5y. `fundexpert/scoring/horizon.py:8-15` takes a plain arithmetic mean of the raw cumulative percentages and requires only the shorter column. In the active TEFAS bundle, 355 funds have both 3y and 5y values, while 213 have 3y but no 5y. Among complete rows, median 3y return is 165.96% and median 5y return is 618.28%, so the 5y number dominates the mean; incomplete funds are ranked on 3y alone. `tests/test_horizon.py:34-44` explicitly locks in the single-column behavior.
- **Affected code:** `fundexpert/config.py:31-35`; `fundexpert/scoring/horizon.py:8-15`; `tests/test_horizon.py:23-64`.
- **Impact:** “Long horizon” does not compare like with like. Older funds get a mixed 3y/5y cumulative statistic on a much larger scale, while newer funds get a standalone 3y statistic. Similar scale mixing affects short and medium buckets. Rank changes may reflect period length and data availability rather than superior annualized performance.
- **Concrete remediation:** Convert each cumulative return to a comparable periodic measure, preferably CAGR/annualized return for multi-year columns and a clearly specified annualized or per-month measure for shorter columns, then combine them. Decide whether long-horizon eligibility requires 5y history or uses an explicit missing-period penalty; do not silently use a different formula per row. Validate impossible inputs (for example cumulative returns below -100%) and add tests for complete versus incomplete histories plus active-data ranking comparisons before changing production behavior.

## P2 — Medium

### BL-05 — “Fee priority” ignores the available total-expense field

- **Severity:** P2
- **Evidence:** The web exporter requests and writes `Yıllık Azami Fon Toplam Gider Oranı (%)` (`fundexpert/data/tefas_export.py:49-62`), but `YONETIM_RENAME` does not include that column (`fundexpert/data/loader.py:37-43`), and `_read_one` limits `usecols` to the rename keys (`fundexpert/data/loader.py:58-66`). Scoring uses only `applied_management_fee_pct` at `fundexpert/scoring/score.py:34,50`.
- **Affected code:** `fundexpert/data/tefas_export.py:49-62`; `fundexpert/data/loader.py:37-43,58-66`; `fundexpert/scoring/score.py:34,50`; `frontend/src/components/ControlPanel.jsx:92-97`.
- **Impact:** The “Fee Priority” control ranks one cost component rather than the broadest available expense measure. Two funds can be ordered as “cheaper” even when their total expense limits point the other way. Users are not told about the narrower definition.
- **Concrete remediation:** Ingest a canonical `max_total_expense_pct`, validate it, and define a documented cost feature: prefer actual/total expense when available, with an explicit fallback to applied management fee. Return the cost metric and value used for each pick in explainability output. If management fee must remain the product choice, rename the control to “Management Fee Priority” and stop documenting it as generic fee/cost.

### BL-06 — A large unclassified strategy bucket bypasses the advertised diversification cap

- **Severity:** P2
- **Evidence:** `fundexpert/select/strategy.py:18-28` maps names that miss the ordered rules to `other`; the current rules cover only the keywords at `fundexpert/rules.json:2-16`. `fundexpert/select/pick.py:37-47` explicitly exempts `other` from the strategy cap. In the active TEFAS snapshot, 261 of 1,044 candidates are `other`, and four of eight default picks (`KVS`, `RBR`, `PKV`, `PRU`) bypass the strategy cap through that value. The UI nevertheless states a maximum per strategy at `frontend/src/components/ControlPanel.jsx:127-130`.
- **Affected code:** `fundexpert/rules.json:2-16`; `fundexpert/select/strategy.py:18-28`; `fundexpert/select/pick.py:37-47`; `frontend/src/components/ControlPanel.jsx:120-130`.
- **Impact:** The cap is mathematically correct for classified rows but does not guarantee the diversification the control promises. A portfolio can contain many economically similar unclassified funds, especially Serbest variants, without tripping the limit.
- **Concrete remediation:** Add classification-coverage telemetry and fail/warn when `other` exceeds a reviewed threshold in either the candidate pool or selected portfolio. Expand deterministic rules or use a reviewed umbrella/type fallback for uncovered products; preserve a distinct `unknown` status rather than asserting that unknown means diversified. Add an active-bundle regression test for maximum unclassified share and show the selected `other` count in the UI.

### BL-07 — Run output and history do not capture enough state to reproduce a recommendation

- **Severity:** P2
- **Evidence:** Pipeline configuration includes momentum, diversification mode, resolved/override caps, founder, news configuration, and tunable config objects (`fundexpert/pipeline.py:30-49`), but the header records only a subset and omits diversification/caps and rules identity (`fundexpert/pipeline.py:166-181`). CLI history drops even more: no momentum, founder, diversification, cap, news, active bundle, or rules hash (`fundexpert/history/store.py:22-42`). The API returns a snapshot only in the immediate response (`fundexpert/api.py:518-523`) and does not call `save_run`; the CLI receives a manifest during loading/refresh but does not attach it to the run at `fundexpert/cli.py:110-139`.
- **Affected code:** `fundexpert/pipeline.py:30-49,166-181`; `fundexpert/history/store.py:22-42`; `fundexpert/cli.py:110-139`; `fundexpert/api.py:449-523`.
- **Impact:** Two runs with different rules, adaptive caps, snapshot contents, momentum preference, or news mode can have records that look equivalent. Drift analysis cannot distinguish model/configuration change from market-data change, and web-generated recommendations have no durable audit record.
- **Concrete remediation:** Introduce a versioned run-record schema containing all request fields, resolved caps, scoring/selection tunables or a model-version hash, rules-file hash/content version, active `bundle_id` and file hashes, news status, warnings, and picks. Make CLI and API call the same persistence seam, or explicitly disable history in both and label web output ephemeral. Add round-trip tests that reconstruct configuration and prove distinct records for distinct rules/snapshots.

### BL-08 — Bounded TEFAS alignment silently removes funds without recording which ones were omitted

- **Severity:** P2
- **Evidence:** `_align_code_sets` computes the non-common codes and removes them from all three views when five or fewer differ (`fundexpert/data/tefas_export.py:211-242`). `download_web_export_bundle` writes only the aligned rows (`fundexpert/data/tefas_export.py:278-298`). `DataBundleManifest` records only bundle identity, timestamps, row count, and file metadata (`fundexpert/data/bundle.py:73-104`); it has no excluded-code provenance.
- **Affected code:** `fundexpert/data/tefas_export.py:211-242,278-298`; `fundexpert/data/bundle.py:45-118,269-277`.
- **Impact:** Up to five funds can disappear from the investable universe on an otherwise successful refresh, potentially including a top candidate, with no way for the portfolio report or later audit to identify the omission. The code correctly fails closed above the tolerance, but successful bounded loss remains opaque.
- **Concrete remediation:** Return structured alignment metadata (`excluded_codes`, missing views, original row counts) from acquisition, persist it in the immutable manifest, and surface an explicit data-quality warning in status/generation responses. Add tests that a five-code alignment records all omissions and that published provenance is immutable and hash-checked.

### BL-09 — CLI founder choices are static while the API correctly limits choices to the active snapshot

- **Severity:** P2
- **Evidence:** The CLI builds founder menus from the full hard-coded platform list via `founder_choices` (`fundexpert/ui.py:48-74`, `fundexpert/founders.py:192-194`). The API loads the active candidates and returns only present founders with counts (`fundexpert/api.py:397-415`), and rejects a founder absent from the current data (`fundexpert/api.py:466-480`). Pipeline execution later raises if the static CLI choice leaves zero rows (`fundexpert/pipeline.py:87-94`).
- **Affected code:** `fundexpert/ui.py:48-74`; `fundexpert/founders.py:159-194`; `fundexpert/api.py:397-415,466-480`; `fundexpert/pipeline.py:87-94`.
- **Impact:** The CLI can offer a selection that the active bundle cannot fulfill and then fail after all prompts, while the web prevents the same invalid choice. That is a user-visible API/CLI parity gap and becomes more likely when founder lists drift.
- **Concrete remediation:** Resolve and validate each selected active bundle before presenting founder prompts, then build CLI choices from `available_founders(candidates)` exactly as the API does. Show counts, reset a cached founder that is no longer available, and add a test where a canonical founder exists in the registry but not in the active bundle.

### BL-10 — BEFAS news queries use truncated fallback names even though canonical founders are available

- **Severity:** P2
- **Evidence:** News grouping derives a prefix only from `fon_adi` (`fundexpert/news/penalty.py:65-76`). `extract_company_prefix` searches for `PORTFÖY`, then falls back to the first three words (`fundexpert/news/match.py:28-49`). Real BEFAS names generally start with a pension-company legal name and do not contain `PORTFÖY`; for example the active name `ALLİANZ YAŞAM VE EMEKLİLİK A.Ş. ...` becomes `ALLİANZ YAŞAM VE`. The merged candidate already has exact canonical `kurucu` attribution at `fundexpert/data/merge.py:26-30`.
- **Affected code:** `fundexpert/news/match.py:16-49`; `fundexpert/news/penalty.py:65-107`; `fundexpert/data/merge.py:26-30`; tests at `tests/test_news_match.py:6-35` do not cover real BEFAS legal-name prefixes.
- **Impact:** BEFAS negative-news searches can be incomplete or ambiguous, creating false negatives or false positives that directly subtract 0.20 from scores and can displace selected funds. This makes the optional news pass less trustworthy for one of the two supported universes.
- **Concrete remediation:** Pass the canonical `kurucu` into news-query grouping and use a normalized legal entity name as the primary key; retain name parsing only as a fallback. Add representative real-format TEFAS and BEFAS tests and ensure all funds for one canonical founder share one query/result set.

### BL-11 — Historical scoring documentation contradicts the current runtime contract in financially meaningful ways

- **Severity:** P2
- **Evidence:** Although marked “Historical design,” `docs/03-scoring-engine.md:23-29` says volume uses `aum_change_pct`, while runtime uses `aum_last`. `docs/03-scoring-engine.md:47-63` omits the momentum term now present at `fundexpert/scoring/score.py:35,41,46,51`. `docs/03-scoring-engine.md:68-74` describes Low as risk-tolerant and High as risk-averse, the reverse of `fundexpert/config.py:26-30` and the CLI wording at `fundexpert/ui.py:75-78`. `docs/02-data-layer.md:74-77` documents a total-expense field the loader does not ingest.
- **Affected code/docs:** `docs/03-scoring-engine.md:23-74`; `docs/02-data-layer.md:74-77`; `fundexpert/scoring/score.py:32-64`; `fundexpert/config.py:26-30`; `fundexpert/ui.py:75-105`.
- **Impact:** A maintainer or reviewer can calibrate, test, or explain the opposite risk semantics and the wrong financial features. The “historical” banner reduces but does not remove the risk because these pages remain detailed model documentation and are linked from the generated docs set.
- **Concrete remediation:** Move superseded design documents under an unmistakable archive path or add a prominent per-section runtime-difference table. Generate a current scoring-contract page directly from named config/schema definitions where practical. Add a docs assertion/check that current horizon columns, risk-band meanings, and feature names match the runtime constants.

## Verified strengths and non-findings

- Cross-file code-set equality, duplicate-code rejection, numeric parsing, row counts, risk range 1–7, timestamp skew, immutable publication, and pointer activation are guarded in `fundexpert/data/bundle.py:168-277,291-415`.
- TEFAS and BEFAS are processed as separate universes; `run_pipeline` rejects `both`, leaving dual execution to the CLI (`fundexpert/pipeline.py:74-78`).
- Active founder attribution was complete for both local bundles, consistent with `tests/test_founders.py:47-52`.
- Strategy/sector rule priority is now consistently first-match through `np.select` (`fundexpert/select/strategy.py:18-28`, `fundexpert/select/sector.py:27-38`), resolving the prior scalar/vector priority inconsistency.
- Selection ordering is deterministic by score then fund code (`fundexpert/select/pick.py:26-29`), as is top-K news selection (`fundexpert/news/penalty.py:59-60`).
- The largest-remainder allocation enforces 5% units, a 5% floor for supported `N <= 20`, and an exact 100% sum (`fundexpert/select/weights.py:15-50`). No arithmetic defect was found in the supported API/CLI range.
- Adaptive cap resolution is consistent between pipeline and API/CLI inputs and is reused for the news counterfactual (`fundexpert/config.py:51-83`, `fundexpert/pipeline.py:79-84,133-164`).

## Suggested remediation order

1. Add eligibility policy for Serbest/restricted products (BL-01).
2. Decide and enforce the risk-level contract (BL-02).
3. Correct or rename the volume feature (BL-03).
4. Redesign horizon return comparability with explicit migration tests (BL-04).
5. Add run/data/rules provenance before further model tuning (BL-07, BL-08).
6. Improve total-cost semantics and diversification coverage (BL-05, BL-06).
7. Close CLI/API founder and BEFAS news parity gaps (BL-09, BL-10).
8. Refresh current model documentation (BL-11).
