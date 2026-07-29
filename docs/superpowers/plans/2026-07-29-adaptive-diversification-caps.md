# Adaptive Diversification Caps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scale strategy and named-sector caps with portfolio size, expose Strict/Balanced/Relaxed policies in the web UI and CLI, and preserve explicit numeric overrides.

**Architecture:** A pure policy helper in `fundexpert/config.py` owns the three cap schedules and explicit-override precedence. `run_pipeline` resolves concrete strategy and sector caps once and passes them to every selection pass. The API, CLI, and React form carry a `diversification_mode`; the frontend mirrors the small schedule only to preview the effective cap before submission.

**Tech Stack:** Python 3.13, dataclasses, FastAPI/Pydantic, pandas/pytest, React 19, Vite/Vitest, Testing Library, PowerShell.

## Global Constraints

- Supported modes are exactly `strict`, `balanced`, and `relaxed`; the default is `balanced`.
- Strict uses `2/2/2`, Balanced uses `2/3/4`, and Relaxed uses `3/4/5` across the inclusive size bands `1–11`, `12–15`, and `16–20`.
- The resolved number is applied independently to both strategy and named-sector limits.
- Strategy `other` and sector `diversified` remain exempt.
- Explicit strategy and sector caps override their mode-derived values independently.
- Portfolio size remains limited to 1–20; the web slider remains limited to 3–20.
- No scoring, classification, weighting, persistence, or data-bundle behavior changes.
- Every failing test stops feature work until it is fixed, per `AGENTS.md`.
- After implementation, run dead-code analysis and `scripts/refresh-docs.ps1`, then the complete `scripts/check.ps1` gate.

---

### Task 1: Diversification policy helper

**Files:**
- Modify: `fundexpert/config.py`
- Modify: `tests/test_config.py`

**Interfaces:**
- Produces: `DiversificationMode = Literal["strict", "balanced", "relaxed"]`
- Produces: `resolve_diversification_caps(n: int, mode: DiversificationMode = "balanced", *, max_per_type: int | None = None, max_per_sector: int | None = None) -> tuple[int, int]`
- Preserves: `DEFAULT_MAX_PER_TYPE == 2` and `DEFAULT_MAX_PER_SECTOR == 2` for compatibility with existing imports.

- [ ] **Step 1: Add failing schedule and override tests**

Add imports for `pytest` and parameterize all boundaries in
`tests/test_config.py`:

```python
import pytest


@pytest.mark.parametrize(
    ("mode", "n", "expected"),
    [
        ("strict", 1, 2),
        ("strict", 11, 2),
        ("strict", 12, 2),
        ("strict", 15, 2),
        ("strict", 16, 2),
        ("strict", 20, 2),
        ("balanced", 1, 2),
        ("balanced", 11, 2),
        ("balanced", 12, 3),
        ("balanced", 15, 3),
        ("balanced", 16, 4),
        ("balanced", 20, 4),
        ("relaxed", 1, 3),
        ("relaxed", 11, 3),
        ("relaxed", 12, 4),
        ("relaxed", 15, 4),
        ("relaxed", 16, 5),
        ("relaxed", 20, 5),
    ],
)
def test_resolve_diversification_caps_schedule(mode, n, expected):
    assert config.resolve_diversification_caps(n, mode) == (expected, expected)


def test_resolve_diversification_caps_applies_independent_overrides():
    assert config.resolve_diversification_caps(
        16,
        "balanced",
        max_per_type=7,
    ) == (7, 4)
    assert config.resolve_diversification_caps(
        12,
        "relaxed",
        max_per_sector=6,
    ) == (4, 6)


@pytest.mark.parametrize(
    ("n", "mode", "max_per_type", "max_per_sector"),
    [
        (0, "balanced", None, None),
        (21, "balanced", None, None),
        (8, "unknown", None, None),
        (8, "balanced", 0, None),
        (8, "balanced", None, 21),
    ],
)
def test_resolve_diversification_caps_rejects_invalid_inputs(
    n, mode, max_per_type, max_per_sector
):
    with pytest.raises(ValueError):
        config.resolve_diversification_caps(
            n,
            mode,
            max_per_type=max_per_type,
            max_per_sector=max_per_sector,
        )
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_config.py -v
```

Expected: the new cases fail because `resolve_diversification_caps` does not
exist.

- [ ] **Step 3: Implement the pure policy**

In `fundexpert/config.py`, import `Literal`, define the type alias and immutable
schedule, then implement:

```python
from typing import Literal

DiversificationMode = Literal["strict", "balanced", "relaxed"]

_DIVERSIFICATION_CAPS: dict[DiversificationMode, tuple[int, int, int]] = {
    "strict": (2, 2, 2),
    "balanced": (2, 3, 4),
    "relaxed": (3, 4, 5),
}


def resolve_diversification_caps(
    n: int,
    mode: DiversificationMode = "balanced",
    *,
    max_per_type: int | None = None,
    max_per_sector: int | None = None,
) -> tuple[int, int]:
    if not 1 <= n <= 20:
        raise ValueError("Portfolio size must be between 1 and 20.")
    if mode not in _DIVERSIFICATION_CAPS:
        raise ValueError(f"Unsupported diversification mode: {mode!r}.")
    for name, value in (
        ("max_per_type", max_per_type),
        ("max_per_sector", max_per_sector),
    ):
        if value is not None and not 1 <= value <= 20:
            raise ValueError(f"{name} must be between 1 and 20.")

    band = 0 if n <= 11 else 1 if n <= 15 else 2
    derived = _DIVERSIFICATION_CAPS[mode][band]
    return (
        derived if max_per_type is None else max_per_type,
        derived if max_per_sector is None else max_per_sector,
    )
```

- [ ] **Step 4: Run focused tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_config.py -v
```

Expected: all configuration tests pass.

- [ ] **Step 5: Commit the policy seam**

```powershell
git add -- fundexpert/config.py tests/test_config.py
git commit -m "feat: add adaptive diversification policy"
```

---

### Task 2: Resolve caps once in the selection pipeline

**Files:**
- Modify: `fundexpert/pipeline.py`
- Create: `tests/test_pipeline_diversification.py`

**Interfaces:**
- Consumes: `DiversificationMode` and `resolve_diversification_caps` from Task 1.
- Changes: `PipelineConfig.max_per_type` and `max_per_sector` become optional
  overrides with `None` defaults.
- Adds: `PipelineConfig.diversification_mode: DiversificationMode = "balanced"`.
- Guarantees: the same resolved integers reach primary selection and the
  news-displacement counterfactual.

- [ ] **Step 1: Confirm all `PipelineConfig` construction is keyword-based**

Run:

```powershell
rg -n "PipelineConfig\(" fundexpert tests AGENTS.md README.md docs --glob "!docs/fundexpert/**" --glob "!docs/search.js"
```

Expected: callers use named arguments. If a positional caller appears, convert
it to named arguments in the same task before reordering dataclass fields.

- [ ] **Step 2: Add failing pipeline-resolution tests**

Create `tests/test_pipeline_diversification.py`. Reuse the existing
`fixtures_dir` CSV fixture through `load_universe`, and monkeypatch pipeline
selection seams to capture the resolved integers without changing scoring:

```python
from datetime import datetime

import fundexpert.pipeline as pipeline
from fundexpert.data.loader import load_universe
from fundexpert.data.merge import merge_universe
from fundexpert.pipeline import PipelineConfig, run_pipeline


def _config(**overrides):
    values = {
        "universe": "tefas",
        "risk_level": "medium",
        "horizon": "medium",
        "volume_priority": "medium",
        "fee_priority": "medium",
        "momentum_priority": "medium",
        "n": 12,
        "now": datetime(2026, 7, 29),
    }
    values.update(overrides)
    return PipelineConfig(**values)


def test_pipeline_passes_balanced_caps_to_selection(fixtures_dir, monkeypatch):
    candidates = merge_universe(
        load_universe(
            fixtures_dir / "getiri_small.csv",
            fixtures_dir / "buyukluk_small.csv",
            fixtures_dir / "yonetim_small.csv",
        ),
        universe="tefas",
    )
    calls = []
    real_pick_top = pipeline.pick_top

    def capture(scored, n, max_per_type, max_per_sector, **kwargs):
        calls.append((max_per_type, max_per_sector))
        return real_pick_top(
            scored,
            n=n,
            max_per_type=max_per_type,
            max_per_sector=max_per_sector,
            **kwargs,
        )

    monkeypatch.setattr(pipeline, "pick_top", capture)
    run_pipeline(candidates, _config())

    assert calls == [(3, 3)]


def test_pipeline_preserves_independent_explicit_override(
    fixtures_dir, monkeypatch
):
    candidates = merge_universe(
        load_universe(
            fixtures_dir / "getiri_small.csv",
            fixtures_dir / "buyukluk_small.csv",
            fixtures_dir / "yonetim_small.csv",
        ),
        universe="tefas",
    )
    calls = []
    real_pick_top = pipeline.pick_top

    def capture(scored, n, max_per_type, max_per_sector, **kwargs):
        calls.append((max_per_type, max_per_sector))
        return real_pick_top(
            scored,
            n=n,
            max_per_type=max_per_type,
            max_per_sector=max_per_sector,
            **kwargs,
        )

    monkeypatch.setattr(pipeline, "pick_top", capture)
    run_pipeline(
        candidates,
        _config(
            n=16,
            diversification_mode="relaxed",
            max_per_type=7,
        ),
    )

    assert calls == [(7, 5)]
```

Add a news case that stubs `apply_negative_news_penalty` and
`compute_displaced_funds`, asserting both receive the same resolved
`max_per_type` and `max_per_sector` values for `n=12`, Relaxed:

```python
def test_news_counterfactual_uses_resolved_relaxed_caps(
    fixtures_dir, monkeypatch
):
    candidates = merge_universe(
        load_universe(
            fixtures_dir / "getiri_small.csv",
            fixtures_dir / "buyukluk_small.csv",
            fixtures_dir / "yonetim_small.csv",
        ),
        universe="tefas",
    )
    captured = {}

    def fake_penalty(scored, **kwargs):
        hit = type("Hit", (), {"to_render_dict": lambda self: {}})()
        return scored, {str(scored.iloc[0]["fon_kodu"]): [hit]}

    def fake_displaced(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(pipeline, "apply_negative_news_penalty", fake_penalty)
    monkeypatch.setattr(pipeline, "compute_displaced_funds", fake_displaced)

    run_pipeline(
        candidates,
        _config(
            diversification_mode="relaxed",
            news_enabled=True,
            news_api_key="test-key",
        ),
    )

    assert captured["max_per_type"] == 4
    assert captured["max_per_sector"] == 4
```

- [ ] **Step 3: Run the focused tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_pipeline_diversification.py -v
```

Expected: construction fails because the new mode/default behavior is absent.

- [ ] **Step 4: Implement one-time pipeline resolution**

Reorder keyword-oriented `PipelineConfig` fields so `now` remains before
default-valued fields:

```python
n: int
now: datetime
diversification_mode: DiversificationMode = "balanced"
max_per_type: int | None = None
max_per_sector: int | None = None
```

At the beginning of `run_pipeline`, after universe validation, resolve:

```python
max_per_type, max_per_sector = resolve_diversification_caps(
    config.n,
    config.diversification_mode,
    max_per_type=config.max_per_type,
    max_per_sector=config.max_per_sector,
)
```

Pass these local integers—not the optional config fields—to `pick_top` and
`compute_displaced_funds`.

- [ ] **Step 5: Run pipeline and existing selection/news tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_pipeline_diversification.py tests/test_pick.py tests/test_cli.py -v
```

Expected: all tests pass. Per repository protocol, stop and fix any failure
before continuing.

- [ ] **Step 6: Commit pipeline integration**

```powershell
git add -- fundexpert/pipeline.py tests/test_pipeline_diversification.py
git commit -m "feat: apply adaptive caps in pipeline"
```

---

### Task 3: API and CLI mode contracts

**Files:**
- Modify: `fundexpert/api.py`
- Modify: `fundexpert/cli.py`
- Modify: `tests/test_api.py`
- Modify: `tests/test_cli.py`

**Interfaces:**
- Consumes: `DiversificationMode` and optional cap overrides in
  `PipelineConfig`.
- API request: `diversification_mode` defaults to `"balanced"`;
  `max_per_type` and `max_per_sector` accept `null` or integers 1–20.
- CLI: `--diversification` choices are `strict`, `balanced`, and `relaxed`;
  numeric flags default to `None` and override the selected policy.

- [ ] **Step 1: Add failing API contract tests**

In `tests/test_api.py`, extend invalid-field parameterization with:

```python
("diversification_mode", "unlimited"),
("max_per_type", "3"),
("max_per_sector", True),
```

Add a capture test around `run_pipeline`:

```python
def test_generate_passes_mode_and_optional_caps_to_pipeline(
    client, monkeypatch
):
    captured = {}
    real_run_pipeline = api.run_pipeline

    def capture(candidates, config):
        captured["config"] = config
        return real_run_pipeline(candidates, config)

    monkeypatch.setattr(api, "run_pipeline", capture)
    response = client.post(
        "/api/generate",
        json={
            "universe": "tefas",
            "n": 12,
            "diversification_mode": "relaxed",
            "max_per_type": 6,
        },
    )

    assert response.status_code == 200
    assert captured["config"].diversification_mode == "relaxed"
    assert captured["config"].max_per_type == 6
    assert captured["config"].max_per_sector is None
```

- [ ] **Step 2: Add failing CLI contract tests**

In `tests/test_cli.py`, add a test that monkeypatches `sys.argv`,
`prompt_user`, and `run_pipeline`, then captures the passed config:

```python
def test_main_passes_diversification_mode_and_optional_overrides(monkeypatch):
    captured = []
    answers = {
        "universe": "tefas",
        "risk_level": "medium",
        "horizon": "medium",
        "volume_priority": "medium",
        "fee_priority": "medium",
        "momentum_priority": "medium",
        "n": 12,
    }

    monkeypatch.setattr(
        "sys.argv",
        [
            "fundexpert",
            "--diversification",
            "relaxed",
            "--max-per-sector",
            "6",
        ],
    )
    monkeypatch.setattr("fundexpert.cli.prompt_user", lambda _: answers)
    monkeypatch.setattr("fundexpert.cli.save_last_run_state", lambda _: None)
    monkeypatch.setattr(
        "fundexpert.cli.load_candidates_for_universe",
        lambda *args: object(),
    )

    def fake_run_pipeline(candidates, config):
        captured.append(config)
        return PipelineResult(
            weighted=pd.DataFrame(
                {
                    "fon_kodu": ["AAA"],
                    "fon_adi": ["ALPHA FON"],
                    "display_weight_pct": [100],
                    "score": [0.7],
                    "risk": [3],
                }
            ),
            header={"warning": None},
            hits_for_render={},
            news_meta={"enabled": False},
        )

    monkeypatch.setattr("fundexpert.cli.run_pipeline", fake_run_pipeline)
    monkeypatch.setattr("fundexpert.cli.save_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "fundexpert.cli.render_portfolio", lambda *args, **kwargs: None
    )

    assert main() == 0
    assert captured[0].diversification_mode == "relaxed"
    assert captured[0].max_per_type is None
    assert captured[0].max_per_sector == 6
```

Add `PipelineResult` to the existing pipeline import in `tests/test_cli.py`;
`pandas as pd` is already imported by that module.

- [ ] **Step 3: Add failing CLI cap-validation tests**

Add:

```python
@pytest.mark.parametrize(
    ("flag", "value"),
    [
        ("--max-per-type", "0"),
        ("--max-per-type", "21"),
        ("--max-per-sector", "0"),
        ("--max-per-sector", "21"),
    ],
)
def test_main_rejects_invalid_explicit_cap(monkeypatch, flag, value):
    monkeypatch.setattr("sys.argv", ["fundexpert", flag, value])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 2
```

- [ ] **Step 4: Run focused tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_api.py tests/test_cli.py -v
```

Expected: new API validation/config propagation and CLI arguments fail.

- [ ] **Step 5: Implement API request fields**

In `fundexpert/api.py`, add:

```python
diversification_mode: DiversificationMode = "balanced"
max_per_type: int | None = Field(default=None, ge=1, le=20)
max_per_sector: int | None = Field(default=None, ge=1, le=20)
```

Pass `diversification_mode=req.diversification_mode` to `PipelineConfig`.
Pydantic's existing strict model configuration must continue rejecting numeric
strings and booleans.

- [ ] **Step 6: Implement CLI options and precedence**

In `fundexpert/cli.py`, remove unused imports of the fixed default cap
constants. Add a bounded argparse type:

```python
def _cap_value(value: str) -> int:
    parsed = int(value)
    if not 1 <= parsed <= 20:
        raise argparse.ArgumentTypeError("cap must be between 1 and 20")
    return parsed
```

Then add:

```python
parser.add_argument(
    "--diversification",
    choices=("strict", "balanced", "relaxed"),
    default="balanced",
    help="Çeşitlendirme: strict, balanced veya relaxed",
)
```

Set both numeric cap argument defaults to `None`, update their help text to say
they override the selected mode, set their `type` to `_cap_value`, and pass
`diversification_mode=args.diversification` to `PipelineConfig`.

- [ ] **Step 7: Run API and CLI tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_api.py tests/test_cli.py -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit public contracts**

```powershell
git add -- fundexpert/api.py fundexpert/cli.py tests/test_api.py tests/test_cli.py
git commit -m "feat: expose diversification modes"
```

---

### Task 4: Web UI control and live cap explanation

**Files:**
- Modify: `frontend/src/config.js`
- Modify: `frontend/src/components/ControlPanel.jsx`
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/App.test.jsx`

**Interfaces:**
- Produces: `DIVERSIFICATION_OPTIONS`, containing the three select options.
- Produces: `getDiversificationCap(n, mode) -> number` for display only.
- Adds: `DEFAULT_CONFIG.diversification_mode = "balanced"`.
- Sends: `diversification_mode` in every existing `/api/generate` request.

- [ ] **Step 1: Add failing frontend policy and interaction tests**

In `frontend/src/App.test.jsx`, add:

```jsx
it('defaults to balanced diversification and submits it', async () => {
  render(<App />);
  await screen.findByText('AAA');

  expect(screen.getByLabelText('Diversification')).toHaveValue('balanced');
  const firstGenerate = fetch.mock.calls.find(
    ([url]) => url === '/api/generate',
  );
  expect(
    JSON.parse(firstGenerate[1].body).diversification_mode,
  ).toBe('balanced');
});

it('shows and submits the relaxed cap for a 12-fund portfolio', async () => {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByText('AAA');

  fireEvent.change(screen.getByLabelText(/Portfolio Size/), {
    target: { value: '12' },
  });
  await user.selectOptions(
    screen.getByLabelText('Diversification'),
    'relaxed',
  );

  expect(
    screen.getByText('Maximum 4 funds per strategy or named sector.'),
  ).toBeInTheDocument();

  await user.click(screen.getByRole('button', { name: 'Generate Portfolio' }));
  const generateCalls = () =>
    fetch.mock.calls.filter(([url]) => url === '/api/generate');
  await waitFor(() => expect(generateCalls()).toHaveLength(2));
  expect(
    JSON.parse(generateCalls()[1][1].body).diversification_mode,
  ).toBe('relaxed');
});
```

- [ ] **Step 2: Run frontend tests and verify failure**

Run:

```powershell
npm.cmd --prefix frontend test
```

Expected: the Diversification control and helper text are absent.

- [ ] **Step 3: Add frontend policy metadata**

In `frontend/src/config.js`, add:

```javascript
export const DIVERSIFICATION_OPTIONS = [
  { value: 'strict', label: 'Strict' },
  { value: 'balanced', label: 'Balanced' },
  { value: 'relaxed', label: 'Relaxed' },
];

const DIVERSIFICATION_CAPS = {
  strict: [2, 2, 2],
  balanced: [2, 3, 4],
  relaxed: [3, 4, 5],
};

export function getDiversificationCap(n, mode) {
  const band = n <= 11 ? 0 : n <= 15 ? 1 : 2;
  return DIVERSIFICATION_CAPS[mode][band];
}
```

Add `diversification_mode: 'balanced'` to `DEFAULT_CONFIG`.

- [ ] **Step 4: Render the accessible select and helper**

Import the new exports in `ControlPanel.jsx`. Immediately after the portfolio
size control, reuse `SelectControl`:

```jsx
<SelectControl
  label="Diversification"
  name="diversification_mode"
  value={config.diversification_mode}
  onChange={onChange}
  options={DIVERSIFICATION_OPTIONS}
/>
<p className="control-help" aria-live="polite">
  Maximum {getDiversificationCap(config.n, config.diversification_mode)} funds
  per strategy or named sector.
</p>
```

Keep the helper semantically associated with this area and ensure it updates
without submission.

- [ ] **Step 5: Style helper text consistently**

In `frontend/src/index.css`, add:

```css
.control-help {
  color: var(--text-secondary);
  font-size: 0.8rem;
  line-height: 1.4;
  margin: -12px 0 20px;
}
```

- [ ] **Step 6: Run frontend tests, lint, and build**

Run:

```powershell
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
```

Expected: all commands pass.

- [ ] **Step 7: Commit the web control**

```powershell
git add -- frontend/src/config.js frontend/src/components/ControlPanel.jsx frontend/src/index.css frontend/src/App.test.jsx
git commit -m "feat: add diversification mode control"
```

---

### Task 5: Documentation, post-feature routine, and full verification

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/04-selection-and-weighting.md`
- Modify: generated files under `docs/fundexpert/` and `docs/search.js`
- Modify: `todos.md` only if it currently tracks diversification work or the
  implementation introduces an architectural follow-up.

**Interfaces:**
- Documents the same mode names, schedules, exceptions, and override
  precedence exposed by code.
- Produces no runtime behavior.

- [ ] **Step 1: Update maintained documentation**

In `AGENTS.md`, replace the fixed-cap pipeline wording with:

```text
select.pick.pick_top (N picks, capped independently per strategy and named
sector; default Balanced caps scale 2/3/4 for N=1–11/12–15/16–20, Strict stays
at 2, Relaxed scales 3/4/5; "other" strategy and "diversified" sector are
exempt; explicit numeric overrides win)
```

Update `docs/04-selection-and-weighting.md` to:

- describe `strategy`, not the stale `umbrella_type`, as the strategy cap key;
- document the separate named-sector cap;
- include the Strict/Balanced/Relaxed schedule table;
- document exemptions and independent explicit overrides;
- state that Balanced is the API, CLI, and web default.

Inspect `todos.md` with:

```powershell
if (Test-Path todos.md) { rg -n -i "divers|cap|strategy|sector" todos.md }
```

Only edit it if a matching item must be completed or revised.

- [ ] **Step 2: Run dead-code analysis and clean findings**

Run:

```powershell
.\.venv\Scripts\python.exe -m vulture fundexpert --min-confidence 80
```

Expected: exit 0. If the new feature leaves an unused import/helper, remove it,
rerun the focused tests for that file, and rerun vulture before continuing.

- [ ] **Step 3: Refresh generated documentation**

Run:

```powershell
.\scripts\refresh-docs.ps1
```

Expected: exit 0 and generated API documentation reflects the optional cap
types plus diversification mode.

- [ ] **Step 4: Run the repository's complete verification gate**

Run:

```powershell
.\scripts\check.ps1
```

Expected: Python tests, frontend tests, frontend lint, production build,
vulture, dependency check, and whitespace check all pass. If any test fails,
stop feature work and fix it immediately before rerunning this gate.

- [ ] **Step 5: Inspect final behavior and diff hygiene**

Run:

```powershell
git diff --check
git status --short
git diff --stat
```

Start the app using the documented backend and frontend commands and verify in
the web UI:

1. Balanced is selected on load and an 8-fund portfolio displays cap 2.
2. Changing size to 12 updates Balanced to cap 3.
3. Changing to Relaxed at size 12 updates the helper to cap 4.
4. Generating submits successfully and returns 12 funds when the eligible data
   can satisfy the request.
5. Strict at size 12 displays cap 2 and preserves the existing partial-result
   warning if constraints exhaust eligible candidates.

Stop both servers after the browser check.

- [ ] **Step 6: Commit documentation and generated output**

Stage only files belonging to this feature:

```powershell
git add -- AGENTS.md docs/04-selection-and-weighting.md docs/fundexpert docs/search.js
git add -- todos.md
git commit -m "docs: explain adaptive diversification modes"
```

Omit the `todos.md` staging command when that file was not changed.

- [ ] **Step 7: Confirm clean completion state**

Run:

```powershell
git status --short
git log -6 --oneline
```

Expected: no uncommitted feature files remain; the task commits are visible in
order and all verification evidence is current.
