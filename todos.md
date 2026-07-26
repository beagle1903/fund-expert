# Fundexpert follow-up ideas

## Data acquisition

- Design the browser workflow that downloads all three TEFAS/BEFAS exports.
- Download into a staging directory, then call `validate_bundle` and
  `publish_bundle`; never write directly into the active bundle.
- Define CAPTCHA/manual-handoff behavior and an explicit scheduling policy.

## Recommendation model

- Backtest horizon averaging, risk calibration, and score-proportional weights
  before changing current recommendation behavior.
- Consider an explainability view for per-signal score contributions.
- Revisit strategy/sector keywords as real fund names expose gaps.

## Product

- Decide whether web-generated portfolios should join CLI run history.
- Add deployment/authentication work only if the local application becomes a
  private or public hosted service.
