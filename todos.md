# Fundexpert follow-up ideas

## Data acquisition

- Monitor the undocumented TEFAS web-export transport for schema or access
  changes; keep the TEFAS-only bounded five-code alignment policy and fail
  closed if the difference grows or the aligned bundle misses any other
  validation rule.
- Decide whether to add scheduling beyond the current once-per-local-day
  freshness gate.

## Recommendation model

- Backtest horizon averaging, risk calibration, and score-proportional weights
  before changing current recommendation behavior.
- Consider an explainability view for per-signal score contributions.
- Use the selection-rule editor to revisit strategy/sector keywords as real
  fund names expose gaps; keep first-match ordering deliberate.

## Product

- Decide whether web-generated portfolios should join CLI run history.
- Add deployment/authentication work only if the local application becomes a
  private or public hosted service.
