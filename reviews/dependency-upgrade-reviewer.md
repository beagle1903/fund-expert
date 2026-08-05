# Dependency Upgrade Review — 2026-08-04

## Scope and isolation

- Reviewed detached commit `afb02eae4da6ceded239610fcab32af4820d4780` in isolated worktree `C:\Users\burha\.codex\worktrees\weekly-fundexpert-dependencies-20260804`.
- Used only that worktree's private `.venv` and `frontend/node_modules`.
- No staging, commits, pushes, PRs, or edits to the main checkout were performed.
- Starting Python environment passed `pip check`; repository baseline supplied by the coordinator was `332 passed`, 94.55% coverage.

## Initial Python inventory

`python -m pip list --outdated --format=json` returned, in deterministic case-insensitive package-name order:

| Package | Installed | Latest | Declaration before |
|---|---:|---:|---|
| annotated-doc | 0.0.4 | 0.0.5 | `requirements.txt==0.0.4` (via FastAPI) |
| annotated-types | 0.7.0 | 0.8.0 | `requirements.txt==0.7.0` (via Pydantic) |
| coverage | 7.15.2 | 7.15.3 | `requirements.txt==7.15.2` (via pytest-cov) |
| fastapi | 0.139.2 | 0.141.1 | `pyproject.toml>=0.139,<1`; `requirements.txt==0.139.2` |
| hypothesis | 6.156.6 | 6.165.0 | `pyproject.toml[pandas]>=6.0`; `requirements.txt==6.156.6` |
| pandas | 3.0.3 | 3.0.5 | `pyproject.toml>=3.0.3`; `requirements.txt==3.0.3` |
| pip | 26.1.2 | 26.2 | environment tool; intentionally absent from compiled safe requirements |
| prompt-toolkit | 3.0.52 | 3.0.53 | `requirements.txt==3.0.52` (via Questionary) |
| pydantic-core | 2.46.4 | 2.47.0 | `requirements.txt==2.46.4` (exactly required by Pydantic 2.13.4) |
| typeguard | 4.5.2 | 4.6.0 | `requirements.txt==4.5.2` (via Pandera) |
| uvicorn | 0.51.0 | 0.52.1 | `pyproject.toml>=0.51,<1`; `requirements.txt==0.51.0` |

## Deterministic Python attempts and results

Each retained candidate was compiled in isolation with `pip-compile --upgrade-package`, installed without pulling unrelated dependencies, checked with `pip check`, and validated with the complete `python -m pytest tests/` suite.

| Order | Package | Result | Installed/declaration after | Complete-suite evidence |
|---:|---|---|---|---|
| 1 | annotated-doc 0.0.5 | kept | lock `0.0.5` | 332 passed, 94.55%, 27.26s |
| 2 | annotated-types 0.8.0 | kept | lock `0.8.0` | 332 passed, 94.55%, 26.09s |
| 3 | coverage 7.15.3 | kept | lock `7.15.3` | 332 passed, 94.55%, 42.04s |
| 4 | fastapi 0.141.1 | kept | declaration `>=0.141.1,<1`; lock `0.141.1` | 332 passed, 94.55%, 42.27s |
| 5 | hypothesis 6.165.0 | kept | declaration `[pandas]>=6.165.0`; lock `6.165.0` | 332 passed, 94.55%, 29.30s |
| 6 | pandas 3.0.5 | kept | declaration `>=3.0.5`; lock `3.0.5` | 332 passed, 94.55%, 31.58s |
| 7 | pip 26.2 | rolled back | restored installed `26.1.2` | App suite initially passed (332, 20.63s), but pip-tools 7.6 then failed importing removed `pip._internal.utils.compat.stdlib_pkgs`; rollback restored `pip-compile`, `pip check`, and 332 passing tests (20.45s) |
| 8 | prompt-toolkit 3.0.53 | kept | lock `3.0.53` | 332 passed, 94.55%, 34.82s |
| 9 | pydantic-core 2.47.0 | incompatible, unchanged | installed/lock remain `2.46.4` | Resolver rejected 2.47.0 because Pydantic 2.13.4 requires exactly 2.46.4; requirements SHA-256 was unchanged; rollback-state suite: 332 passed, 43.31s |
| 10 | typeguard 4.6.0 | kept | lock `4.6.0` | 332 passed, 94.55%, 23.01s |
| 11 | uvicorn 0.52.1 | kept | declaration `>=0.52.1,<1`; lock `0.52.1` | 332 passed, 94.55%, 35.19s |

Final Python state has only the two deliberately retained outdated entries: pip 26.1.2 and pydantic-core 2.46.4. Final `pip check`: **No broken requirements found.**

## Frontend inventory, attempts, and advisory remediation

The initial lock-only `npm outdated --json` exposed four direct candidates: lucide-react 1.25.0→1.28.0, React 19.2.7→19.2.8, react-dom 19.2.7→19.2.8, and Recharts 3.9.2→3.10.1. Initial `npm audit --json` reported one moderate transitive PostCSS advisory (`GHSA-fxqj-rqcc-2cmp`, affected `<=8.5.22`; installed 8.5.19). After `npm ci`, baseline frontend validation passed: 3 files / 15 tests, lint clean, build successful.

| Candidate | Result | Validation |
|---|---|---|
| lucide-react 1.28.0 | kept; package and lock declarations updated | 15 tests passed; lint clean; build passed; Python 332 passed (27.49s) |
| React 19.2.8 | rolled back to 19.2.7 | Independent attempt failed 2 frontend suites because React and react-dom must be exact matches. Rollback: 15 tests, lint, build, and Python 332 passed (27.18s). |
| react-dom 19.2.8 | rolled back to 19.2.7 | npm necessarily changed React too, so the attempt was not independent and was rejected despite 15 passing tests. Exact rollback: 15 tests, lint, build, and Python 332 passed (43.81s). |
| Recharts 3.10.1 | kept; package and lock declarations updated | 15 tests passed; lint clean; build passed; Python 332 passed (38.90s) |
| PostCSS 8.5.25 | kept as an isolated transitive lock update | `npm audit fix` changed one package; 15 tests, lint, build, and Python 332 passed (55.55s); final audit has 0 vulnerabilities |
| @testing-library/user-event 14.6.3 | kept; package and lock declarations updated | 15 tests passed; lint clean; build passed; Python 332 passed (42.97s) |

Materializing `node_modules` surfaced additional non-security updates not visible in the initial lock-only inventory. They were not attempted in this bounded pass: @testing-library/jest-dom 7.0.0 (unsupported major), @types/react 19.2.18, @types/react-dom 19.2.4, @vitejs/plugin-react 6.0.5, oxlint 1.77.0, and Vite 8.2.0. React/react-dom 19.2.8 should be handled as one explicitly coordinated pair in a future task because independent updates are invalid.

Final frontend validation on the retained dependency set:

- `npm test`: **3 files, 15 tests passed**.
- `npm run lint`: **passed with no findings**.
- `npm run build`: **passed**.
- `npm audit --json`: **0 vulnerabilities** (moderate PostCSS advisory resolved).
- Final cross-stack Python validation after the last retained frontend update: **332 passed**, coverage **94.55%**, 42.97s.

## Changed files

- `pyproject.toml` — raised tested direct Python minimums for pandas, FastAPI, Hypothesis, and Uvicorn.
- `requirements.txt` — updated nine compatible resolved Python pins.
- `frontend/package.json` — raised Lucide, Recharts, and user-event declarations; React pair remains unchanged.
- `frontend/package-lock.json` — consistent resolved versions plus PostCSS 8.5.25 advisory remediation.
- `reviews/dependency-upgrade-reviewer.md` — this report.

`git diff --check` passed. No architecture or public-behavior change was made, so the post-feature documentation routine was not applicable.
