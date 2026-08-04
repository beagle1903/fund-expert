# Code Quality Review

Review date: 2026-08-04 (Europe/Istanbul)
Isolated worktree: `C:\Users\burha\.codex\worktrees\weekly-fundexpert-code-quality-20260804`
Starting commit: `afb02eae4da6ceded239610fcab32af4820d4780` (detached HEAD)
Scope: Python dead code and lint, frontend lint, high-confidence behavior-preserving cleanup, and full Python regression validation.

## Result

- Ruff: **pass** after 13 mechanical test-only fixes.
- Oxlint: **pass** with the locked frontend dependency tree.
- Vulture: **no confirmed dead production code**. Its 32 findings at 60% confidence are framework/configuration references described below.
- Full test suite: **pass — 332 passed in 55.01s; 94.55% coverage** (required threshold: 90%).
- `git diff --check`: **pass**. Git emitted only the repository's LF-to-CRLF checkout warnings.
- No source architecture or public behavior changed, so the post-feature documentation routine was not required.

## Applied fixes

### P2 — Test lint debt obscured clean static-analysis results

**Evidence:** the initial `.venv/Scripts/ruff.exe check .` reported 13 violations: eight `F401` unused imports, four `E402` late module imports, and one `E701` one-line conditional.

**Affected code:**

- `tests/test_cli.py:1-15,489,502,524` — moved pipeline/UI and `Path` imports to module scope; removed two unused local `sys` imports.
- `tests/test_history_store.py:5` — removed unused `Path`.
- `tests/test_loader.py:1` — removed unused `math`.
- `tests/test_normalize.py:2` — removed unused `pytest`.
- `tests/test_pick.py:1,177` — moved `math` to module scope.
- `tests/test_score.py:1,174,194` — moved NumPy to module scope and expanded the one-line equality guard.
- `tests/test_ui.py:1-2` — removed unused `json` and `pytest`.
- `tests/test_weights.py:2` — removed unused `pytest`.

**Impact:** lint output now has zero violations, so future regressions are visible; runtime behavior is unchanged because only unused imports, import placement, and statement layout changed.

**Remediation applied:** nine insertions and sixteen deletions across eight test files. No production code was changed.

## Dead-code analysis and skipped risks

Command: `.venv/Scripts/python.exe -m vulture fundexpert/`

Vulture exited with findings, but all 32 were classified as dynamic or intentionally public references rather than safe deletion candidates:

- `fundexpert/api.py:49-217` — Pydantic `model_config` values and response/request model fields are consumed dynamically during validation and serialization.
- `fundexpert/api.py:134-169` — Pydantic field/model validators are registered by decorators and are exercised by API tests.
- `fundexpert/api.py:379-450` — FastAPI route functions are registered through `@app.get`, `@app.put`, and `@app.post` decorators and are exercised by endpoint tests.
- `fundexpert/config.py:45,48` — `DEFAULT_MAX_PER_TYPE` and `DEFAULT_MAX_PER_SECTOR` are compatibility exports; the former is explicitly covered by `tests/test_config.py:25`, and repository documentation records both as preserved compatibility constants.

Removing any of these based solely on Vulture would risk breaking API contracts or compatibility. No unreachable branch or high-confidence orphaned production function was found, so no production deletion was made.

Frontend installation emitted one moderate transitive dependency advisory:

- `postcss <=8.5.22`, advisory `GHSA-fxqj-rqcc-2cmp`, fix available.

This was not auto-fixed because dependency changes belong to the isolated dependency-upgrade review and require declaration/lock reconciliation plus full regression testing. `npm audit fix` was not run.

## Commands and validation

| Command | Result |
|---|---|
| `.venv/Scripts/python.exe -m vulture fundexpert/` | 32 framework/configuration false positives at 60% confidence; no safe deletion |
| Initial `.venv/Scripts/ruff.exe check .` | 13 violations found |
| Final `.venv/Scripts/ruff.exe check .` | Pass: `All checks passed!` |
| `npm ci` in `frontend/` | Pass: 125 packages installed from lockfile |
| `npm run lint` in `frontend/` | Pass: Oxlint produced no diagnostics |
| `npm audit --json` in `frontend/` | One moderate transitive `postcss` advisory; deferred |
| `.venv/Scripts/python.exe -m pytest tests/ -q` | Pass: 332 passed in 55.01s; total coverage 94.55% |
| `git diff --check` | Pass (line-ending warnings only) |

## Changed files

- `tests/test_cli.py`
- `tests/test_history_store.py`
- `tests/test_loader.py`
- `tests/test_normalize.py`
- `tests/test_pick.py`
- `tests/test_score.py`
- `tests/test_ui.py`
- `tests/test_weights.py`
- `reviews/code-quality-reviewer.md`

No files were staged, committed, pushed, or modified outside this isolated worktree.
