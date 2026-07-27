# Codebase Review Remediation Summary: `fundexpert`

All P1 and P2 findings from the five specialist reviews are resolved.

## P0

None were reported.

## P1 — Resolved

1. **Keyword priority:** strategy and sector vectorized classifiers use ordered
   `np.select` masks, so `rules.json` priority wins over textual position.
2. **Hardcoded rules:** exclusions and issuer cleanup substitutions live in
   `rules.json`. `SERBEST` remains intentionally eligible per the later product
   decision; `OKS` is the configured exclusion.
3. **Duplicate rule loading:** `fundexpert/utils/rules.py` is the centralized,
   cached rules loader.
4. **Missing invariants:** Hypothesis coverage now checks sector-count
   exhaustiveness and news-penalty rank inversion.
5. **Redundant scans:** candidate exclusions share one escaped, compiled regex;
   missing-risk handling uses one summed mask.

## P2 — Resolved

- `DATA_ROOT` is centralized in `config.py`.
- Turkish casing helpers live in `utils/text.py`.
- `HorizonCandidatesSchema` is enforced inside `score_candidates` before
  scoring whenever pipeline schema validation is enabled.
- Duplicate/dynamic imports were removed.
- CSV identity strings use PyArrow storage and umbrella type uses `category`.
- AUM clamping uses `np.maximum`; risk NA conversion is explicit.
- The `python -m fundexpert` entry point, Tavily timeout path, all-NaN scoring,
  and zero-valid-candidate pipeline path have regression coverage.
- News top-K selection is deterministic on score ties.
- The fallback `other` strategy is intentionally exempt from the strategy cap,
  matching the `diversified` sector treatment.

## Validation

- Full suite: 220 passed.
- Coverage: 97.20% (required minimum: 90%).
- Dead-code scan: `vulture fundexpert/` reported no findings.
- API documentation regenerated from the local `./fundexpert` package.
