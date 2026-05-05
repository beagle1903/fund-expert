# News-effect visibility — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the news pass's effect on the portfolio fully legible from a single `--news` run — header line, row markers on penalized picks, and a footer listing funds that got displaced from the portfolio.

**Architecture:** Two-layer change. (1) `run_pipeline` returns a 4th value, `news_meta`, capturing what the pass did (top-K size, total hits, displaced funds with pre/post scores and their hits). Computing `displaced` requires running `pick_top` a second time on pre-penalty scores. (2) `render_portfolio` gains a `news_meta` kwarg and uses it to emit the header line, row markers, and the new "displaced" footer.

**Tech Stack:** Python, pandas, rich (table rendering), pytest.

**Spec:** [docs/superpowers/specs/2026-05-05-news-effect-visibility-design.md](../specs/2026-05-05-news-effect-visibility-design.md)

---

## File map

- **Modify** `fundexpert/cli.py` — `run_pipeline` returns `(selected, header, hits, news_meta)` (4-tuple); `main()` unpacks 4; news_meta computed from pre/post `pick_top` runs.
- **Modify** `fundexpert/render/table.py` — new `news_meta` kwarg, header news line, 📰 markers + score deltas on penalized rows, footer A heading change, new footer B.
- **Modify** `tests/test_cli.py` — every existing test that unpacks `run_pipeline` updated to 4-tuple.
- **Modify** `tests/test_render.py` — extend with cases for `news_meta` rendering.
- **Modify** `CLAUDE.md` — non-interactive snippet updated to unpack 4 values from `run_pipeline`.

No new files. No new config constants (penalty/top-K already in `fundexpert/config.py`).

---

## Task 1: Extend `run_pipeline` to return `news_meta` (no displaced yet)

**Files:**
- Modify: `fundexpert/cli.py:52-141`
- Modify: `tests/test_cli.py:48-232` (all `run_pipeline` callers)

This task does pure plumbing: adds a 4th return value with the always-present fields (`enabled`, `key_present`, `top_k`, `total_hits`). The `displaced` field is added in Task 2. We split it this way so test signatures stabilize before behavior is layered on.

- [ ] **Step 1: Write failing test for `news_meta` shape when news disabled**

Add to `tests/test_cli.py` near `test_run_pipeline_returns_selected_with_weights`:

```python
def test_run_pipeline_returns_news_meta_with_enabled_false_when_news_off(fake_universe_loader):
    selected, header, hits, news_meta = run_pipeline(
        universe="tefas", risk_level="medium", horizon="medium",
        volume_priority="medium", fee_priority="medium",
        n=2, max_per_type=2, now=datetime(2026, 5, 2, 11, 42),
    )
    assert news_meta == {"enabled": False}
```

- [ ] **Step 2: Run test, confirm it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_cli.py::test_run_pipeline_returns_news_meta_with_enabled_false_when_news_off -v`
Expected: FAIL with `ValueError: not enough values to unpack (expected 4, got 3)`.

- [ ] **Step 3: Update `run_pipeline` to return 4-tuple**

In `fundexpert/cli.py`, change the signature and return:

```python
def run_pipeline(
    universe: str,
    risk_level: str,
    horizon: str,
    volume_priority: str,
    fee_priority: str,
    n: int,
    max_per_type: int,
    now: datetime,
    max_per_sector: int = DEFAULT_MAX_PER_SECTOR,
    news_enabled: bool = False,
    news_api_key: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, list], dict[str, Any]]:
```

And replace the existing `return weighted, header, hits_for_render` at the bottom with:

```python
    if not news_enabled:
        news_meta: dict[str, Any] = {"enabled": False}
    else:
        news_meta = {
            "enabled": True,
            "key_present": bool(news_api_key),
            "top_k": NEWS_QUERY_TOP_K_MULTIPLIER * n,
            "total_hits": len(hits_by_code),
            "displaced": [],  # filled in Task 2
        }

    return weighted, header, hits_for_render, news_meta
```

Update the docstring's return description to mention the 4th value.

- [ ] **Step 4: Update existing `run_pipeline` callers in `cli.py`**

In `cli.py`'s `main()`, update the unpacking inside the `for u in universes_to_run` loop:

```python
        selected, header, hits_for_render, news_meta = run_pipeline(
            universe=u,
            risk_level=answers["risk_level"],
            ...
        )
```

(Renderer still ignores `news_meta` — it gets wired in Task 3.)

- [ ] **Step 5: Update existing 3-tuple test unpacks to 4-tuple**

Edit `tests/test_cli.py` — every `run_pipeline(...)` call. Replace:

| Line range | Old (3-tuple) | New (4-tuple) |
|---|---|---|
| `test_run_pipeline_returns_selected_with_weights` | `selected, header, hits = run_pipeline(...)` | `selected, header, hits, _ = run_pipeline(...)` |
| `test_run_pipeline_with_news_shifts_picks_when_top_fund_has_negative_news` (both calls) | `sel_no_news, _, hits_no_news = ...` and `sel_with_news, _, _ = ...` | `sel_no_news, _, hits_no_news, _ = ...` and `sel_with_news, _, _, _ = ...` |
| `test_run_pipeline_news_enabled_without_api_key_falls_back_to_quant` (both calls) | `sel_no_news, _, _ = ...` and `sel_news_no_key, _, hits = ...` | `sel_no_news, _, _, _ = ...` and `sel_news_no_key, _, hits, _ = ...` |

Also update the two `MagicMock` `return_value` tuples used by `patch("fundexpert.cli.run_pipeline", return_value=...)`:

- `test_main_renders_two_portfolios_when_universe_is_both`: change `return_value=(fake_selected, fake_header, fake_hits)` → `return_value=(fake_selected, fake_header, fake_hits, {"enabled": False})`.
- `test_main_passes_news_api_key_when_news_flag_set`: change `return_value=(fake_selected, fake_header, {})` → `return_value=(fake_selected, fake_header, {}, {"enabled": True, "key_present": True, "top_k": 9, "total_hits": 0, "displaced": []})`.
- `test_main_default_run_does_not_pass_news_key`: change `return_value=(fake_selected, {"warning": None}, {})` → `return_value=(fake_selected, {"warning": None}, {}, {"enabled": False})`.

- [ ] **Step 6: Run all tests, verify green**

Run: `.venv/Scripts/python.exe -m pytest tests/ -v`
Expected: all tests pass (existing count + 1 new). The new test asserts `news_meta == {"enabled": False}`.

- [ ] **Step 7: Commit**

```bash
git add fundexpert/cli.py tests/test_cli.py
git commit -m "feat(news): run_pipeline returns news_meta as 4th tuple value"
```

---

## Task 2: Compute `displaced` funds in `run_pipeline`

**Files:**
- Modify: `fundexpert/cli.py:96-126` (after `apply_negative_news_penalty`, before final return)
- Test: `tests/test_cli.py` (new test below)

When news is enabled and at least one fund got hits, run `pick_top` a second time on pre-penalty scores to compute "what would have been picked." `displaced = would_be − actual`.

- [ ] **Step 1: Write failing test for displaced computation with stub**

Add to `tests/test_cli.py`:

```python
def test_run_pipeline_news_meta_populates_displaced_when_top_fund_dropped(
    fake_universe_loader,
):
    """A Tavily hit on the top quant fund should land it in news_meta['displaced']."""
    from fundexpert.news.tavily import NewsHit

    sel_no_news, _, _, _ = run_pipeline(
        universe="tefas", risk_level="medium", horizon="medium",
        volume_priority="medium", fee_priority="medium",
        n=1, max_per_type=2, now=datetime(2026, 5, 2),
        news_enabled=False, news_api_key=None,
    )
    leader_code = sel_no_news.iloc[0]["fon_kodu"]
    leader_prefix = sel_no_news.iloc[0]["fon_adi"].split()[0] + " FON"

    def fake_query(company_prefix, **_kw):
        if company_prefix == leader_prefix:
            return [NewsHit(title="dava açıldı", url="https://x.com/p",
                            published=None, source="x.com")]
        return []

    with patch("fundexpert.news.penalty.query_negative_news", side_effect=fake_query):
        sel_news, _, _, news_meta = run_pipeline(
            universe="tefas", risk_level="medium", horizon="medium",
            volume_priority="medium", fee_priority="medium",
            n=1, max_per_type=2, now=datetime(2026, 5, 2),
            news_enabled=True, news_api_key="tvly-test",
        )

    assert sel_news.iloc[0]["fon_kodu"] != leader_code
    assert news_meta["enabled"] is True
    assert news_meta["total_hits"] == 1
    assert len(news_meta["displaced"]) == 1
    d = news_meta["displaced"][0]
    assert d["fon_kodu"] == leader_code
    assert d["score_pre"] > d["score_post"]
    assert d["score_pre"] - d["score_post"] == pytest.approx(0.20)
    assert len(d["hits"]) == 1
    assert d["hits"][0]["title"] == "dava açıldı"
```

Also add a test that `displaced` stays empty when news is enabled but produces no hits:

```python
def test_run_pipeline_news_meta_displaced_empty_when_no_hits(fake_universe_loader):
    with patch("fundexpert.news.penalty.query_negative_news", return_value=[]):
        _, _, _, news_meta = run_pipeline(
            universe="tefas", risk_level="medium", horizon="medium",
            volume_priority="medium", fee_priority="medium",
            n=2, max_per_type=2, now=datetime(2026, 5, 2),
            news_enabled=True, news_api_key="tvly-test",
        )
    assert news_meta["total_hits"] == 0
    assert news_meta["displaced"] == []
```

- [ ] **Step 2: Run tests, confirm they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_cli.py::test_run_pipeline_news_meta_populates_displaced_when_top_fund_dropped tests/test_cli.py::test_run_pipeline_news_meta_displaced_empty_when_no_hits -v`
Expected: First test FAILS with `assert len([]) == 1` (displaced is still empty). Second test PASSES (Task 1 already returns `displaced: []`).

- [ ] **Step 3: Implement displaced computation**

In `fundexpert/cli.py`, edit the body of `run_pipeline` so the news block snapshots pre-penalty scores, then computes the counterfactual after `pick_top` runs:

Replace the current block (lines ~96–126):

```python
    # Optional news pass: query Tavily for top-K candidates by quant score,
    # subtract a fixed penalty for any with negative-news hits. Penalty is
    # applied *before* pick_top so picks actually shift.
    hits_by_code: dict[str, list] = {}
    if news_enabled:
        scored, hits_by_code = apply_negative_news_penalty(
            scored,
            top_k=NEWS_QUERY_TOP_K_MULTIPLIER * n,
            keywords=NEGATIVE_NEWS_KEYWORDS,
            penalty=NEGATIVE_NEWS_PENALTY,
            api_key=news_api_key,
            cache_dir=NEWS_CACHE_DIR,
            ttl_seconds=NEWS_CACHE_TTL_SECONDS,
            max_age_days=NEWS_MAX_AGE_DAYS,
            max_results=NEWS_MAX_RESULTS_PER_FUND,
            timeout_seconds=NEWS_QUERY_TIMEOUT_SECONDS,
        )

    selected, warning = pick_top(
        scored, n=n, max_per_type=max_per_type, max_per_sector=max_per_sector,
    )
    weighted = compute_weights(selected)

    # Project hits down to just the picked funds for the renderer.
    picked_codes = set(weighted["fon_kodu"].astype(str))
    hits_for_render = {
        code: [hit.to_render_dict() for hit in hits]
        for code, hits in hits_by_code.items()
        if code in picked_codes
    }
```

with:

```python
    # Optional news pass: query Tavily for top-K candidates by quant score,
    # subtract a fixed penalty for any with negative-news hits. Penalty is
    # applied *before* pick_top so picks actually shift.
    hits_by_code: dict[str, list] = {}
    scored_pre = scored  # snapshot for counterfactual pick_top
    if news_enabled:
        scored, hits_by_code = apply_negative_news_penalty(
            scored,
            top_k=NEWS_QUERY_TOP_K_MULTIPLIER * n,
            keywords=NEGATIVE_NEWS_KEYWORDS,
            penalty=NEGATIVE_NEWS_PENALTY,
            api_key=news_api_key,
            cache_dir=NEWS_CACHE_DIR,
            ttl_seconds=NEWS_CACHE_TTL_SECONDS,
            max_age_days=NEWS_MAX_AGE_DAYS,
            max_results=NEWS_MAX_RESULTS_PER_FUND,
            timeout_seconds=NEWS_QUERY_TIMEOUT_SECONDS,
        )

    selected, warning = pick_top(
        scored, n=n, max_per_type=max_per_type, max_per_sector=max_per_sector,
    )
    weighted = compute_weights(selected)

    # Project hits down to just the picked funds for the renderer.
    picked_codes = set(weighted["fon_kodu"].astype(str))
    hits_for_render = {
        code: [hit.to_render_dict() for hit in hits]
        for code, hits in hits_by_code.items()
        if code in picked_codes
    }

    # Compute "displaced" funds: those that would have been picked without the
    # news penalty but got pushed out by it. Only meaningful when news is on
    # and at least one fund got hits — otherwise pre/post pick_top runs are
    # identical by construction.
    displaced: list[dict[str, Any]] = []
    if news_enabled and hits_by_code:
        would_be, _ = pick_top(
            scored_pre, n=n, max_per_type=max_per_type, max_per_sector=max_per_sector,
        )
        would_be_codes = set(would_be["fon_kodu"].astype(str))
        displaced_codes = would_be_codes - picked_codes
        scored_pre_indexed = scored_pre.set_index(scored_pre["fon_kodu"].astype(str))
        for code in displaced_codes:
            row = scored_pre_indexed.loc[code]
            hits = hits_by_code.get(code, [])
            displaced.append({
                "fon_kodu": code,
                "fon_adi": str(row["fon_adi"]),
                "score_pre":  float(row["score"]),
                "score_post": float(row["score"]) - NEGATIVE_NEWS_PENALTY,
                "hits": [hit.to_render_dict() for hit in hits],
            })
```

Then update the `news_meta` construction at the bottom to include `displaced`:

```python
    if not news_enabled:
        news_meta: dict[str, Any] = {"enabled": False}
    else:
        news_meta = {
            "enabled": True,
            "key_present": bool(news_api_key),
            "top_k": NEWS_QUERY_TOP_K_MULTIPLIER * n,
            "total_hits": len(hits_by_code),
            "displaced": displaced,
        }
```

- [ ] **Step 4: Run tests, confirm they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_cli.py -v`
Expected: all `test_cli.py` tests pass, including the two new ones.

- [ ] **Step 5: Run full suite**

Run: `.venv/Scripts/python.exe -m pytest tests/ -v`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add fundexpert/cli.py tests/test_cli.py
git commit -m "feat(news): populate displaced funds in news_meta

Run pick_top a second time on pre-penalty scores when news is enabled and
at least one fund got hits. Diff against the actual picks gives the set of
funds that lost their slot to the −0.20 penalty; we surface their pre/post
scores and Tavily hits so the renderer can show them."
```

---

## Task 3: Renderer accepts `news_meta` kwarg (no behavior change yet)

**Files:**
- Modify: `fundexpert/render/table.py:10-19` (signature)
- Modify: `fundexpert/cli.py:286` (call site)

Add the kwarg with a `None` default so the existing programmatic snippet in `CLAUDE.md` keeps working without an edit. The renderer doesn't *do* anything with it yet — that's Tasks 4–6.

- [ ] **Step 1: Write failing test asserting renderer accepts kwarg**

Add to `tests/test_render.py`:

```python
def test_render_accepts_news_meta_kwarg_without_error(capsys):
    news_meta = {"enabled": False}
    render_portfolio(_selected(), _header(), news=None, news_meta=news_meta)
    captured = capsys.readouterr()
    assert "AAA" in captured.out  # baseline output still renders
```

- [ ] **Step 2: Run test, confirm it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render.py::test_render_accepts_news_meta_kwarg_without_error -v`
Expected: FAIL with `TypeError: render_portfolio() got an unexpected keyword argument 'news_meta'`.

- [ ] **Step 3: Add the kwarg to `render_portfolio`**

In `fundexpert/render/table.py`, change the signature:

```python
def render_portfolio(
    selected: pd.DataFrame,
    header: dict[str, Any],
    news: dict[str, list[dict[str, Any]]] | None,
    news_meta: dict[str, Any] | None = None,
) -> None:
    """Print header block + table + (optional) news footer to stdout.

    `news` maps fon_kodu → list of {title, url, source, published?}. If empty
    or None, the news footer is omitted.

    `news_meta` carries info about the news pass (enabled flag, top-K size,
    total hits, displaced funds). When None, news-pass-specific output (header
    line, row markers, displaced footer) is suppressed — used by the
    programmatic snippet that doesn't compute news_meta.
    """
```

(Body unchanged — wiring happens in Tasks 4–6.)

- [ ] **Step 4: Update the `cli.py` call site to pass `news_meta`**

Change `render_portfolio(selected, header, news=hits_for_render or None)` to:

```python
        render_portfolio(selected, header, news=hits_for_render or None, news_meta=news_meta)
```

- [ ] **Step 5: Run tests, confirm green**

Run: `.venv/Scripts/python.exe -m pytest tests/ -v`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add fundexpert/render/table.py fundexpert/cli.py tests/test_render.py
git commit -m "feat(render): add news_meta kwarg to render_portfolio (no-op for now)"
```

---

## Task 4: Render the header news line

**Files:**
- Modify: `fundexpert/render/table.py` (add 4-state header line)
- Modify: `tests/test_render.py` (add 4 cases)

Implements the header table from the spec. Done as one task because all 4 states share the same one-block-of-code branch.

- [ ] **Step 1: Write 4 failing tests, one per header state**

Add to `tests/test_render.py`:

```python
def test_render_header_news_line_disabled_omits_line(capsys):
    """news_meta=None → no 'Haber taraması' line at all."""
    render_portfolio(_selected(), _header(), news=None, news_meta=None)
    assert "Haber taraması" not in capsys.readouterr().out


def test_render_header_news_line_key_missing(capsys):
    news_meta = {"enabled": True, "key_present": False, "top_k": 9,
                 "total_hits": 0, "displaced": []}
    render_portfolio(_selected(), _header(), news=None, news_meta=news_meta)
    out = capsys.readouterr().out
    assert "Haber taraması: atlandı (TAVILY_API_KEY tanımsız)" in out


def test_render_header_news_line_zero_hits(capsys):
    news_meta = {"enabled": True, "key_present": True, "top_k": 24,
                 "total_hits": 0, "displaced": []}
    render_portfolio(_selected(), _header(), news=None, news_meta=news_meta)
    out = capsys.readouterr().out
    assert "Haber taraması: aktif" in out
    assert "top-K=24" in out
    assert "0 fonda olumsuz haber" in out
    assert "pick değişti" not in out
    assert "portföy değişmedi" not in out


def test_render_header_news_line_hits_but_picks_unchanged(capsys):
    news_meta = {"enabled": True, "key_present": True, "top_k": 24,
                 "total_hits": 3, "displaced": []}
    render_portfolio(_selected(), _header(), news=None, news_meta=news_meta)
    out = capsys.readouterr().out
    assert "3 fonda olumsuz haber" in out
    assert "portföy değişmedi" in out


def test_render_header_news_line_picks_changed(capsys):
    news_meta = {"enabled": True, "key_present": True, "top_k": 24,
                 "total_hits": 3,
                 "displaced": [{"fon_kodu": "ZZZ", "fon_adi": "Z FON",
                                "score_pre": 0.55, "score_post": 0.35, "hits": []}]}
    render_portfolio(_selected(), _header(), news=None, news_meta=news_meta)
    out = capsys.readouterr().out
    assert "3 fonda olumsuz haber" in out
    assert "1 pick değişti" in out
```

- [ ] **Step 2: Run tests, confirm 4 fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render.py -v -k "header_news_line"`
Expected: 1 PASS (disabled — already works), 4 FAIL.

- [ ] **Step 3: Implement the header news line**

In `fundexpert/render/table.py`, after the existing `console.print(f"Aday havuzu: ...")` block (around line 35) and before `show_sector = (...)`, add:

```python
    if news_meta and news_meta.get("enabled"):
        if not news_meta.get("key_present"):
            console.print("Haber taraması: atlandı (TAVILY_API_KEY tanımsız)")
        else:
            parts = [
                "Haber taraması: aktif",
                f"top-K={news_meta['top_k']}",
                f"{news_meta['total_hits']} fonda olumsuz haber",
            ]
            displaced_count = len(news_meta.get("displaced", []))
            if news_meta["total_hits"] > 0:
                if displaced_count == 0:
                    parts.append("portföy değişmedi")
                else:
                    parts.append(f"{displaced_count} pick değişti")
            console.print("  •  ".join(parts))
```

- [ ] **Step 4: Run tests, confirm all green**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render.py -v`
Expected: all `test_render.py` tests pass.

- [ ] **Step 5: Commit**

```bash
git add fundexpert/render/table.py tests/test_render.py
git commit -m "feat(render): add 4-state news header line above table"
```

---

## Task 5: Render row markers (📰 + score delta) on penalized picks

**Files:**
- Modify: `fundexpert/render/table.py` (row construction loop)
- Modify: `tests/test_render.py` (add 2 cases)

A row is marked penalized when `news_meta` is provided AND its `fon_kodu` is in the `news` dict (which already projects to picks only). The penalty magnitude is read from `NEGATIVE_NEWS_PENALTY` so a future tuning doesn't require a renderer edit.

- [ ] **Step 1: Write failing tests for marker rendering**

Add to `tests/test_render.py`:

```python
def test_render_marks_penalized_pick_in_fon_kodu_and_score(capsys):
    news = {"BBB": [{"title": "BBB hakkında soruşturma", "url": "https://x",
                     "source": "x.com"}]}
    news_meta = {"enabled": True, "key_present": True, "top_k": 9,
                 "total_hits": 1, "displaced": []}
    render_portfolio(_selected(), _header(), news=news, news_meta=news_meta)
    out = capsys.readouterr().out
    # Penalized row's fon_kodu cell carries the marker
    assert "BBB 📰" in out
    # Penalized row's score cell shows the delta (penalty value comes from config)
    assert "(−0.20)" in out
    # Clean row's score cell does NOT carry the delta
    assert "0.71 (−0.20)" not in out


def test_render_does_not_mark_rows_when_news_meta_absent(capsys):
    """Without news_meta, row markers are suppressed even if `news` is given."""
    news = {"BBB": [{"title": "x", "url": "https://x", "source": "x.com"}]}
    render_portfolio(_selected(), _header(), news=news, news_meta=None)
    out = capsys.readouterr().out
    assert "📰" not in out
    assert "(−0.20)" not in out
```

- [ ] **Step 2: Run tests, confirm fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render.py::test_render_marks_penalized_pick_in_fon_kodu_and_score tests/test_render.py::test_render_does_not_mark_rows_when_news_meta_absent -v`
Expected: first FAIL (no marker), second PASS (currently nothing renders markers).

- [ ] **Step 3: Implement row markers**

In `fundexpert/render/table.py`, add this import near the top:

```python
from fundexpert.config import NEGATIVE_NEWS_PENALTY
```

Then replace the row-building loop:

```python
    for _, r in selected.iterrows():
        row = [
            str(r["fon_kodu"]),
            str(r["fon_adi"]),
            str(r["umbrella_type"]),
        ]
        if show_sector:
            row.append(str(r["sector"]))
        row.extend([
            str(int(r["risk"])),
            f"{int(r['display_weight_pct'])}",
            f"{r['score']:.2f}",
        ])
        table.add_row(*row)
```

with:

```python
    show_news_marker = news_meta is not None and bool(news)
    for _, r in selected.iterrows():
        is_penalized = show_news_marker and str(r["fon_kodu"]) in (news or {})
        fon_kodu_cell = f"{r['fon_kodu']} 📰" if is_penalized else str(r["fon_kodu"])
        score_cell = (
            f"{r['score']:.2f} (−{NEGATIVE_NEWS_PENALTY:.2f})"
            if is_penalized
            else f"{r['score']:.2f}"
        )
        row = [
            fon_kodu_cell,
            str(r["fon_adi"]),
            str(r["umbrella_type"]),
        ]
        if show_sector:
            row.append(str(r["sector"]))
        row.extend([
            str(int(r["risk"])),
            f"{int(r['display_weight_pct'])}",
            score_cell,
        ])
        table.add_row(*row)
```

- [ ] **Step 4: Run tests, confirm green**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render.py -v`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add fundexpert/render/table.py tests/test_render.py
git commit -m "feat(render): mark penalized picks with 📰 and score delta"
```

---

## Task 6: Footer A heading change + new footer B (displaced)

**Files:**
- Modify: `fundexpert/render/table.py` (footer block at the end)
- Modify: `tests/test_render.py` (add 3 cases, update 1)

Footer A (existing) gets a clearer heading. Footer B is new and only renders when `news_meta` carries displaced entries.

- [ ] **Step 1: Update existing test for renamed footer A heading**

Modify `tests/test_render.py::test_render_includes_news_footer_when_provided` so it asserts the new heading wording. Replace the test body:

```python
def test_render_includes_news_footer_when_provided(capsys):
    news = {"AAA": [{"title": "AAA hakkında soruşturma", "url": "https://x",
                     "source": "dunya.com"}]}
    render_portfolio(_selected(), _header(), news=news)
    captured = capsys.readouterr()
    assert "Olumsuz haberle penalize edilen fonlar (portföyde kaldı)" in captured.out
    assert "soruşturma" in captured.out
    assert "AAA" in captured.out
```

- [ ] **Step 2: Write failing tests for footer B and footer-A/footer-B interaction**

Add to `tests/test_render.py`:

```python
def test_render_displaced_footer_renders_when_news_meta_has_displaced(capsys):
    news = {}  # no surviving penalized picks for this case
    news_meta = {
        "enabled": True, "key_present": True, "top_k": 9, "total_hits": 1,
        "displaced": [{
            "fon_kodu": "ZZZ", "fon_adi": "Z PORTFÖY HİSSE FON",
            "score_pre": 0.55, "score_post": 0.35,
            "hits": [{"title": "Z hakkında dava açıldı",
                      "url": "https://news.example/z",
                      "source": "news.example"}],
        }],
    }
    render_portfolio(_selected(), _header(), news=news, news_meta=news_meta)
    out = capsys.readouterr().out
    assert "Habere takılıp portföyden düşen fonlar" in out
    assert "ZZZ" in out
    assert "habersiz skor 0.55" in out
    assert "0.35" in out
    assert "dava açıldı" in out
    assert "https://news.example/z" in out


def test_render_displaced_footer_omitted_when_no_displaced(capsys):
    news_meta = {"enabled": True, "key_present": True, "top_k": 9,
                 "total_hits": 0, "displaced": []}
    render_portfolio(_selected(), _header(), news={}, news_meta=news_meta)
    out = capsys.readouterr().out
    assert "Habere takılıp portföyden düşen fonlar" not in out


def test_render_both_footers_when_survivors_and_displaced(capsys):
    news = {"BBB": [{"title": "BBB ceza", "url": "https://b", "source": "b.com"}]}
    news_meta = {
        "enabled": True, "key_present": True, "top_k": 9, "total_hits": 2,
        "displaced": [{
            "fon_kodu": "ZZZ", "fon_adi": "Z FON",
            "score_pre": 0.55, "score_post": 0.35,
            "hits": [{"title": "Z dava", "url": "https://z", "source": "z.com"}],
        }],
    }
    render_portfolio(_selected(), _header(), news=news, news_meta=news_meta)
    out = capsys.readouterr().out
    assert "Olumsuz haberle penalize edilen fonlar (portföyde kaldı)" in out
    assert "Habere takılıp portföyden düşen fonlar" in out
    # Order: A precedes B
    assert out.index("portföyde kaldı") < out.index("portföyden düşen")
```

- [ ] **Step 3: Run tests, confirm fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render.py -v`
Expected: 4 tests fail (1 updated heading, 3 new). Others pass.

- [ ] **Step 4: Implement footer A heading change + footer B**

In `fundexpert/render/table.py`, replace the existing footer block at the bottom of `render_portfolio`:

```python
    if news:
        console.print("\n[bold red]⚠️ Olumsuz haber:[/bold red]")
        for code, items in news.items():
            for item in items:
                published = f", {item['published']:%Y-%m-%d}" if item.get("published") else ""
                console.print(f"  {code} — \"{item['title']}\"  ({item['source']}{published})")
                console.print(f"        {item['url']}")
```

with:

```python
    if news:
        console.print(
            "\n[bold red]📰 Olumsuz haberle penalize edilen fonlar "
            "(portföyde kaldı):[/bold red]"
        )
        for code, items in news.items():
            for item in items:
                published = f", {item['published']:%Y-%m-%d}" if item.get("published") else ""
                console.print(f"  {code} — \"{item['title']}\"  ({item['source']}{published})")
                console.print(f"        {item['url']}")

    if news_meta and news_meta.get("displaced"):
        console.print(
            "\n[bold red]⛔ Habere takılıp portföyden düşen fonlar:[/bold red]"
        )
        for entry in news_meta["displaced"]:
            console.print(
                f"  {entry['fon_kodu']} — habersiz skor {entry['score_pre']:.2f} "
                f"→ penalize edince {entry['score_post']:.2f}"
            )
            for hit in entry["hits"]:
                published = f", {hit['published']:%Y-%m-%d}" if hit.get("published") else ""
                console.print(f"        ↳ \"{hit['title']}\"  ({hit['source']}{published})")
                console.print(f"        ↳ {hit['url']}")
```

- [ ] **Step 5: Run tests, confirm green**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render.py -v`
Expected: all tests pass.

- [ ] **Step 6: Run full suite for regression check**

Run: `.venv/Scripts/python.exe -m pytest tests/ -v`
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add fundexpert/render/table.py tests/test_render.py
git commit -m "feat(render): rename penalized-picks footer + add displaced footer

Footer A heading now reads 'Olumsuz haberle penalize edilen fonlar
(portföyde kaldı)' so it doesn't read identically to footer B. Footer B
is new: lists funds that would have been picked without --news but got
displaced by the −0.20 penalty, with their pre/post scores and Tavily
hits."
```

---

## Task 7: Update `CLAUDE.md` snippet to unpack 4 values

**Files:**
- Modify: `CLAUDE.md` (the non-interactive snippet under "Running")

The snippet calls `run_pipeline` directly. Without an update, anyone copy-pasting it gets `ValueError: too many values to unpack`.

- [ ] **Step 1: Edit the snippet**

In `CLAUDE.md`, find:

```python
selected, header, hits = run_pipeline(
```

Change to:

```python
selected, header, hits, _ = run_pipeline(
```

(`render_portfolio` has `news_meta=None` as default, so the snippet's `render_portfolio(selected, header, news=hits or None)` call still works — it just doesn't get the new header line / displaced footer, which is correct for a programmatic call without the news pass.)

- [ ] **Step 2: Verify the snippet still parses by running it**

Run (from project root, with the data junction in place):

```bash
.venv/Scripts/python.exe -c "
from datetime import datetime
from fundexpert.cli import run_pipeline, _ensure_utf8_stdio
from fundexpert.render.table import render_portfolio
from fundexpert.config import DEFAULT_MAX_PER_TYPE
_ensure_utf8_stdio()
selected, header, hits, _ = run_pipeline(
    universe='tefas', risk_level='medium', horizon='medium',
    volume_priority='medium', fee_priority='medium',
    n=5, max_per_type=DEFAULT_MAX_PER_TYPE, now=datetime.now())
render_portfolio(selected, header, news=hits or None)
"
```

Expected: portfolio table prints without errors.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude.md): unpack 4-tuple from run_pipeline in snippet"
```

---

## Final verification

- [ ] **Step 1: Full test suite green**

Run: `.venv/Scripts/python.exe -m pytest tests/ -v`
Expected: all tests pass (existing count + ~10 new render/cli tests).

- [ ] **Step 2: Live `--news` smoke test**

Pre-condition: `TAVILY_API_KEY` env var set. Run:

```bash
.venv/Scripts/python.exe -m fundexpert.cli --news
```

Pick `tefas`, `medium`, `medium`, `medium`, `medium`, `5`. Verify:
- Header shows `Haber taraması: aktif • top-K=15 • <N> fonda olumsuz haber • ...`
- If any pick has hits, its row shows `📰` and `(−0.20)`
- Footer A "Olumsuz haberle penalize edilen fonlar (portföyde kaldı)" appears for surviving penalized picks
- Footer B "Habere takılıp portföyden düşen fonlar" appears if any fund got displaced

- [ ] **Step 3: Live no-`--news` smoke test (regression)**

Run: `.venv/Scripts/python.exe -m fundexpert.cli` and verify output is byte-identical to current main behavior — no header news line, no markers, no footers.

- [ ] **Step 4: Live `--news` with no key smoke test**

Run with `TAVILY_API_KEY` unset:

```bash
.venv/Scripts/python.exe -m fundexpert.cli --news
```

Expected: header shows `Haber taraması: atlandı (TAVILY_API_KEY tanımsız)`. Stderr also shows the existing skip warning. No footers. Picks identical to no-news run.
