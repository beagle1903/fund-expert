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
while retaining the existing diversification protection and giving web users a
simple way to choose stricter or looser diversification.

## Approaches considered

1. **Automatic stepped caps:** derive the default cap from the requested fund
   count. This is predictable and preserves the current behavior for ordinary
   portfolios.
2. **Percentage-based cap:** calculate a fraction of portfolio size. This scales
   smoothly but produces less obvious rounding boundaries and is harder to
   explain to users.
3. **Diversification modes (selected):** expose strict, balanced, and relaxed
   policies. Balanced uses the approved automatic schedule; strict preserves
   the old cap, while relaxed scales one step higher. This remains easy to
   explain while giving web users meaningful control.

## Selected behavior

When the caller does not explicitly override a cap, Fundexpert will use the
same effective limit for strategy and named sector:

| Mode | 1–11 funds | 12–15 funds | 16–20 funds |
|---|---:|---:|---:|
| Strict | 2 | 2 | 2 |
| Balanced (default) | 2 | 3 | 4 |
| Relaxed | 3 | 4 | 5 |

Each value is both the maximum per strategy and the maximum per named sector.

The existing exemptions remain unchanged:

- strategy `other` is not capped;
- sector `diversified` is not capped.

The boundaries are inclusive. Fundexpert already rejects requests above 20
because portfolio weights use 5% increments, so no schedule above 20 is needed.

## Architecture and data flow

Add one pure helper in `fundexpert/config.py` that maps `n` plus a
diversification mode to its effective cap. Both strategy and sector defaults
use this helper.

Change the default cap values accepted by `PipelineConfig`, the API request
model, and CLI arguments from a concrete integer to `None`, meaning
"derive from `n` and the selected mode." Add `diversification_mode` with the
allowed values `strict`, `balanced`, and `relaxed`; its default is `balanced`.
Explicit integer values remain supported for programmatic, API, and CLI callers
that intentionally need a custom cap.

At the start of `run_pipeline`, resolve the two effective caps exactly once:

1. use the explicit value when supplied;
2. otherwise call the cap helper with `n` and `diversification_mode`;
3. pass the resolved integers to every `pick_top` call, including the
   pre-news comparison used to calculate displaced funds.

This keeps the selection function simple and guarantees that normal selection
and news-adjusted selection use identical constraints.

### Web UI control

Add a `Diversification` select immediately after the existing portfolio-size
slider in `ControlPanel`. Reusing the panel's existing select pattern keeps the
sidebar compact and keyboard-accessible.

The options are `Strict`, `Balanced`, and `Relaxed`, with `Balanced` selected by
default. Beneath the control, show short helper text with the effective limit
for the current fund count, for example:

`Maximum 3 funds per strategy or named sector.`

Changing either portfolio size or mode updates this helper immediately. The
frontend sends `diversification_mode` with the existing generate request; it
continues to omit the numeric cap fields.

### CLI and API

Add `--diversification {strict,balanced,relaxed}` to the CLI with `balanced` as
the default. The existing `--max-per-type` and `--max-per-sector` flags remain
available and override the selected mode independently.

Add `diversification_mode` to the API request model with the same three values
and default. Optional explicit numeric cap fields take precedence independently:
an explicit strategy cap does not disable automatic sector-cap resolution, and
vice versa.

## Compatibility

- Default Balanced requests for 1–11 funds behave exactly as they do now.
- Existing web behavior remains unchanged because `Balanced` gives portfolios
  of up to 11 funds the current cap of two.
- Explicit `--max-per-type` and `--max-per-sector` CLI values still win over
  mode-derived defaults.
- API clients may still send explicit integer cap values; omitted or `null`
  values select mode-derived behavior.
- Existing direct `PipelineConfig` callers that supply integer caps are
  unchanged.
- No persistence or data-bundle schema changes are required.

## Validation and errors

- The cap helper accepts only portfolio sizes from 1 through 20 and one of the
  three supported modes, and raises `ValueError` for invalid input.
- API validation continues to reject portfolio sizes outside 1–20 and explicit
  cap values outside 1–20, plus unknown diversification modes.
- CLI validation must reject invalid explicit caps rather than silently falling
  back to automatic behavior.
- If diversification constraints still exhaust the candidate pool, the
  existing partial-portfolio warning remains unchanged.

## Testing

1. Unit-test every schedule boundary for all three modes: `1`, `11`, `12`,
   `15`, `16`, and `20`, plus invalid sizes `0` and `21` and an invalid mode.
2. Verify selection observes strict `2/2/2`, balanced `2/3/4`, and relaxed
   `3/4/5` strategy and named-sector limits.
3. Verify `other` and `diversified` exemptions remain unchanged.
4. Verify explicit caps override the mode-derived schedule in direct pipeline,
   API, and CLI paths.
5. Verify omitted API caps for `n=12` resolve to 3 and for `n=16` resolve to 4.
6. Verify both news selection passes receive the same resolved caps.
7. Verify the web control defaults to Balanced, submits the selected mode, and
   updates its effective-cap helper when mode or portfolio size changes.
8. Run the full Python and frontend gates, dead-code analysis, documentation
   refresh, and diff hygiene checks required by `AGENTS.md`.

## Documentation

Update the selection documentation and CLI/API descriptions to explain all
three modes and their schedules. Refresh generated documentation with
`scripts/refresh-docs.ps1`.

## Non-goals

- Changing strategy or sector classification rules.
- Relaxing the special exemptions or the 20-fund maximum.
- Changing scoring, ranking, or weight allocation.
