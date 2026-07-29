# Adaptive diversification caps — design spec

**Date:** 2026-07-29  
**Branch:** `main`  
**Status:** design — awaiting review before implementation plan

## Problem

Fundexpert currently applies fixed limits of two selected funds per strategy and
two per named sector, regardless of requested portfolio size. Those limits work
well for a portfolio of seven or eight funds, but become too restrictive for
larger portfolios. At 12–20 funds they can reject otherwise strong candidates
or prevent the selector from returning the requested number of funds.

The goal is to relax both limits predictably as the requested portfolio grows,
while retaining the existing diversification protection.

## Approaches considered

1. **Automatic stepped caps (selected):** derive the default cap from the
   requested fund count. This is predictable, requires no new UI control, and
   preserves the current behavior for ordinary portfolios.
2. **Percentage-based cap:** calculate a fraction of portfolio size. This scales
   smoothly but produces less obvious rounding boundaries and is harder to
   explain to users.
3. **Diversification strictness control:** add strict, balanced, and relaxed
   modes. This offers more control but adds UI/API choices without a present
   need.

## Selected behavior

When the caller does not explicitly override a cap, Fundexpert will use the
same effective limit for strategy and named sector:

| Requested funds (`n`) | Maximum per strategy | Maximum per named sector |
|---:|---:|---:|
| 1–11 | 2 | 2 |
| 12–15 | 3 | 3 |
| 16–20 | 4 | 4 |

The existing exemptions remain unchanged:

- strategy `other` is not capped;
- sector `diversified` is not capped.

The boundaries are inclusive. Fundexpert already rejects requests above 20
because portfolio weights use 5% increments, so no schedule above 20 is needed.

## Architecture and data flow

Add one pure helper in `fundexpert/config.py` that maps `n` to its automatic
cap. Both strategy and sector defaults use this helper.

Change the default cap values accepted by `PipelineConfig`, the API request
model, and CLI arguments from a concrete integer to `None`, meaning
"automatically derive from `n`." Explicit integer values remain supported for
programmatic and CLI callers that intentionally need a custom cap.

At the start of `run_pipeline`, resolve the two effective caps exactly once:

1. use the explicit value when supplied;
2. otherwise call the automatic-cap helper with `n`;
3. pass the resolved integers to every `pick_top` call, including the
   pre-news comparison used to calculate displaced funds.

This keeps the selection function simple and guarantees that normal selection
and news-adjusted selection use identical constraints.

The React frontend already omits both cap fields, so no new form control is
required. Its existing portfolio-size request will automatically receive the
scaled defaults from the API.

## Compatibility

- Requests for 1–11 funds behave exactly as they do now.
- Explicit `--max-per-type` and `--max-per-sector` CLI values still win over
  automatic defaults.
- API clients may still send explicit integer cap values; omitted or `null`
  values select automatic behavior.
- Existing direct `PipelineConfig` callers that supply integer caps are
  unchanged.
- No persistence or data-bundle schema changes are required.

## Validation and errors

- The automatic-cap helper accepts only portfolio sizes from 1 through 20 and
  raises `ValueError` outside that range.
- API validation continues to reject portfolio sizes outside 1–20 and explicit
  cap values outside 1–20.
- CLI validation must reject invalid explicit caps rather than silently falling
  back to automatic behavior.
- If diversification constraints still exhaust the candidate pool, the
  existing partial-portfolio warning remains unchanged.

## Testing

1. Unit-test every schedule boundary: `1`, `11`, `12`, `15`, `16`, and `20`,
   plus invalid values `0` and `21`.
2. Verify automatic selection limits strategy and named-sector counts to 2, 3,
   and 4 in the three portfolio-size bands.
3. Verify `other` and `diversified` exemptions remain unchanged.
4. Verify explicit caps override the automatic schedule in direct pipeline,
   API, and CLI paths.
5. Verify omitted API caps for `n=12` resolve to 3 and for `n=16` resolve to 4.
6. Verify both news selection passes receive the same resolved caps.
7. Run the full Python and frontend gates, dead-code analysis, documentation
   refresh, and diff hygiene checks required by `AGENTS.md`.

## Documentation

Update the selection documentation and CLI/API descriptions to explain that the
default is automatic and to show the three bands. Refresh generated
documentation with `scripts/refresh-docs.ps1`.

## Non-goals

- Adding a diversification strictness control to the web UI.
- Changing strategy or sector classification rules.
- Relaxing the special exemptions or the 20-fund maximum.
- Changing scoring, ranking, or weight allocation.
