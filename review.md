# Code Review Findings

This is a full-repository review (mixed lens: correctness, reliability, architecture, and maintainability).

## Findings

### [P1] Interactive cancellation path can crash with traceback

- **Location:** `fundexpert/cli.py` (`_prompt()`, `main()`)
- **Why it matters:** If prompt flow is cancelled (`questionary.ask()` returns `None`), `n` is cast with `int(n_raw)` and can raise `TypeError`, producing an ungraceful failure in a user-facing CLI.
- **Evidence:** `_prompt()` assumes all answers are present and does `int(n_raw)` directly.
- **Suggested direction:** Treat any `None` answer as user cancellation and exit cleanly with a short message and non-zero exit code.

### [P2] Installed CLI depends on source-tree-relative `data/` path

- **Location:** `fundexpert/cli.py` (`DATA_ROOT`), `pyproject.toml`
- **Why it matters:** `DATA_ROOT = Path(__file__).resolve().parent.parent / "data"` is brittle for non-editable installs and layouts where raw CSVs are not next to installed package files.
- **Evidence:** runtime path is hard-wired to repo-like structure; data files are operational inputs, not packaged assets.
- **Suggested direction:** add explicit data path resolution strategy (CLI flag/env var/config + clear fallback/error message).

### [P2] Weighting fallback violates stated 100% invariant for impossible N

- **Location:** `fundexpert/select/weights.py` (`compute_weights()`)
- **Why it matters:** For `n > 20`, defensive fallback can return total display weights above 100 (e.g. 21 x 5% = 105), conflicting with documented/expected invariant.
- **Evidence:** branch guarded by `if n * _STEP > 100` still allocates at least one 5% unit to each fund.
- **Suggested direction:** fail fast for impossible input (`n > 20`) or redefine contract for non-CLI callers.

### [P2] Public docs are materially out of sync with implemented behavior

- **Location:** `README.md`, `docs/01-architecture.md`, `docs/04-selection-and-weighting.md`, `docs/05-cli-interaction.md`, `docs/06-news-pass.md`, `docs/07-output-and-testing.md`
- **Why it matters:** Current docs say implementation is pending, describe umbrella-type cap, and describe active RSS/news pass; code uses strategy-based cap and `--news` is currently a no-op notice in v1.
- **Evidence:** `fundexpert/cli.py` prints reserved-message for `--news`; `fundexpert/select/pick.py` uses `strategy`; docs still describe umbrella/news runtime behavior.
- **Suggested direction:** either update docs to match shipped behavior, or clearly mark them as historical design docs and link to current runtime contract.

### [P3] Header metrics blur filtering stages

- **Location:** `fundexpert/cli.py` (`header` construction), `fundexpert/render/table.py`
- **Why it matters:** Reported counts are useful for auditability, but current `candidate_kept` is horizon-kept count after prior fee NaN filtering; wording can mislead interpretation.
- **Evidence:** fee NaN filtering happens before `apply_horizon()`, then `candidate_kept = len(horizoned)`.
- **Suggested direction:** report per-stage counts explicitly (total, fee-dropped, horizon-dropped, final kept).

## Architecture context (for the pointers above)

- Core flow is centralized in `fundexpert/cli.py`: prompt -> load/merge -> horizon -> score -> strategy bucket -> capped pick -> weights -> render.
- Most policy behavior is spread across `fundexpert/scoring/*` and `fundexpert/select/*`, while the CLI file currently handles orchestration plus UX/persistence concerns.
- This shape makes behavior easy to trace but increases coupling: prompt UX, argument policy, data-path policy, and pipeline policy are all changed from one place.

## Suggested follow-up tests

1. Add CLI tests for cancelled prompts (`ask() -> None`) to verify graceful exit behavior.
2. Add boundary tests for pipeline inputs (`n > 20`, invalid priorities/horizon) with explicit error expectations.
3. Add tests for data-root resolution/error UX when CSV files are not at source-relative path.
4. Add contract tests for `--news` current behavior (reserved/no-op message) so docs and runtime stay aligned.
5. Add assertions for staged candidate funnel counts if header metrics are expanded.

## Open assumptions

- `--news` appears intentionally deferred to v2 (current no-op). If this is intentional, docs should clearly say "planned/not active" in one canonical place.
- If non-interactive API usage is supported, validation should be enforced in `run_pipeline()` rather than relying on prompt constraints.
