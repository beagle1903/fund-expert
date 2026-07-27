# Fundexpert follow-up ideas

## Data acquisition

- Monitor the undocumented TEFAS web-export transport for schema or access
  changes; never weaken validation to accommodate partial responses.
- Decide whether to add scheduling beyond the current once-per-local-day
  freshness gate.

## Recommendation model

- Backtest horizon averaging, risk calibration, and score-proportional weights
  before changing current recommendation behavior.
- Consider an explainability view for per-signal score contributions.
- Revisit strategy/sector keywords as real fund names expose gaps.

## Product

- Decide whether web-generated portfolios should join CLI run history.
- Add deployment/authentication work only if the local application becomes a
  private or public hosted service.
