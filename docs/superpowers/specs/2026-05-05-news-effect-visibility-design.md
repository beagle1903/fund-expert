# News-effect visibility — design spec

**Date:** 2026-05-05
**Branch:** `claude/funny-easley-5605b3`
**Status:** design — awaiting review before plan
**Depends on:** [2026-05-04-news-pass-v1-design.md](./2026-05-04-news-pass-v1-design.md) (already shipped)

## Problem

The shipped `--news` flag silently rebalances picks: a `−0.20` penalty on funds with negative-news hits is applied before `pick_top`, but the rendered output gives the user almost no signal about what happened.

Concretely, today's output:
- Header has no indicator that `--news` was even on for this run.
- Score column shows the post-penalty number with no marker — a penalized survivor at 0.41 looks identical to a clean fund at 0.41.
- The "⚠️ Olumsuz haber" footer only lists picks that *survived* with hits. Funds that got pushed out of the portfolio entirely by the penalty are invisible.
- Missing-key fail-soft only writes to stderr, which scrolls off above the table.

The user cannot answer "did news change my portfolio, and how?" from the output alone.

## Goal

Make the news pass's effect on the portfolio fully legible from a single `--news` run, without adding noise on runs where news is off or nothing changed.

## Non-goals

- Changing the penalty formula, top-K bound, or any selection logic.
- Persisting news effects across runs (no diff vs. previous run).
- Showing news for the full universe — we keep the top-K bound.
- JSON / machine-readable output.

## Design

Three additive changes to the renderer plus a small plumbing change to `run_pipeline`.

### 1. Header line

When `news_enabled=True`, append exactly one line to the existing 4-line header block (after `Aday havuzu: …`).

| State | Header line |
|---|---|
| Key missing | `Haber taraması: atlandı (TAVILY_API_KEY tanımsız)` |
| Key OK, 0 hits across top-K | `Haber taraması: aktif  •  top-K=24  •  0 fonda olumsuz haber` |
| Key OK, hits exist, picks unchanged | `Haber taraması: aktif  •  top-K=24  •  3 fonda olumsuz haber  •  portföy değişmedi` |
| Key OK, hits exist, picks changed | `Haber taraması: aktif  •  top-K=24  •  3 fonda olumsuz haber  •  1 pick değişti` |

`top-K` is the value computed in `cli.py` (`NEWS_QUERY_TOP_K_MULTIPLIER * n`). `picks değişti` count is the size of the displaced set (see §3).

When `news_enabled=False`, no header line is added — output is byte-identical to today.

The current stderr warning for missing key stays (it's still useful for scripts), but the header line ensures the signal isn't lost above the table.

### 2. Table row markers on penalized picks

For each row in the rendered table whose `fon_kodu` is in `hits_by_code`:

- Append ` 📰` to the **Fon Kodu** cell (e.g. `BBB 📰`).
- Replace the **Skor** cell with `<post-penalty> (−0.20)` — e.g. `0.41 (−0.20)`.

Clean rows render exactly as today. The −0.20 magnitude is read from `NEGATIVE_NEWS_PENALTY` rather than hardcoded in the renderer (so future tuning to the penalty doesn't require a renderer edit).

### 3. Two footer sections

Replace the current single "⚠️ Olumsuz haber" footer with two clearly-distinguished sections, only emitted when news is enabled and there's something to show.

**Footer A — penalized survivors** (renamed from current footer):

```
📰 Olumsuz haberle penalize edilen fonlar (portföyde kaldı):
  BBB — "headline"  (source, 2026-04-29)
        url
```

Same data shape as today's footer. Only the heading changes — explicitly says "portföyde kaldı" so it doesn't read identically to footer B.

**Footer B — displaced funds (NEW)**:

```
⛔ Habere takılıp portföyden düşen fonlar:
  XXX — habersiz skor 0.55 → penalize edince 0.35
        ↳ "headline"  (source, 2026-04-29)
        ↳ url
```

For each displaced fund:
- Header line: `<fon_kodu> — habersiz skor <pre> → penalize edince <post>` (both rounded to 2 dp).
- One bullet per Tavily hit (title + source + date), under it the URL.
- Multiple displaced funds → repeat the block, blank line between.

### 4. Pipeline plumbing

`run_pipeline` returns one new value alongside the existing tuple. New signature:

```python
def run_pipeline(...) -> tuple[pd.DataFrame, dict[str, Any], dict[str, list], dict[str, Any]]:
    # returns (selected, header, hits_for_render, news_meta)
```

`news_meta` shape:
```python
{
    "enabled": bool,                    # was --news passed?
    "key_present": bool,                # was the API key resolved?
    "top_k": int,                       # NEWS_QUERY_TOP_K_MULTIPLIER * n
    "total_hits": int,                  # count of funds in top-K with ≥1 hit
    "displaced": [                      # funds in would_be_picks but not in selected
        {
            "fon_kodu": str,
            "fon_adi": str,
            "score_pre":  float,        # original quant score (pre-penalty)
            "score_post": float,        # adjusted score (pre-penalty − NEGATIVE_NEWS_PENALTY)
            "hits": list[dict],         # same shape as hits_for_render values
        },
        ...
    ],
}
```

When `news_enabled=False`, `news_meta = {"enabled": False}` — renderer treats this as "render nothing news-related" (current behavior).

To compute `displaced`, `run_pipeline` calls `pick_top` twice when news is enabled and `hits_by_code` is non-empty:

```python
# inside run_pipeline, after apply_negative_news_penalty:
selected, warning = pick_top(scored_post, n=n, max_per_type=..., max_per_sector=...)
would_be_picks, _ = pick_top(scored_pre, n=n, max_per_type=..., max_per_sector=...)
picked_codes = set(selected["fon_kodu"].astype(str))
would_be_codes = set(would_be_picks["fon_kodu"].astype(str))
displaced_codes = would_be_codes - picked_codes
```

`scored_pre` is the DataFrame snapshot taken *before* `apply_negative_news_penalty` mutates scores. `apply_negative_news_penalty` already returns a copy (`adjusted = scored.copy()`), so we can preserve `scored` directly without an extra copy.

The second `pick_top` call is bounded the same as the first (same DataFrame size, same caps) so cost is ~constant.

### 5. Renderer signature

```python
def render_portfolio(
    selected: pd.DataFrame,
    header: dict[str, Any],
    news: dict[str, list[dict[str, Any]]] | None,
    news_meta: dict[str, Any] | None = None,   # NEW, default None
) -> None
```

Behavior:
- `news_meta=None` → no header news line, no displaced footer (footer B). The penalized-survivor footer (footer A) still renders if `news` is truthy, using the new heading text. Row markers (§2) require `news_meta` to be present (so we know `NEGATIVE_NEWS_PENALTY` is the live value), and degrade gracefully to no markers when `news_meta` is None.
- `news_meta` provided → full §1–3 rendering.

This keeps the in-process programmatic-call snippet in `CLAUDE.md` working: it currently passes `news=hits or None` and no `news_meta`, so it gets footer A with the new heading and no markers/header line. The snippet doesn't need editing.

## Edge cases

| Scenario | Output |
|---|---|
| `--news` not passed | No header line, no markers, no footers. Identical to today. |
| `--news` passed, no API key | Header: `Haber taraması: atlandı (...)`. No markers, no footers. (stderr warning still fires.) |
| `--news` passed, key OK, 0 hits | Header: `… 0 fonda olumsuz haber`. No markers, no footers. |
| Hits exist, all penalized funds still picked | Header: `… N fonda olumsuz haber • portföy değişmedi`. Markers on penalized rows. Footer A only. |
| Hits exist, some displaced | Full output: header (`X pick değişti`), markers, both footers. |
| Displaced fund has multiple hits | Footer B lists all hits as bullets under one block. |
| `both` universes run | Each universe's `render_portfolio` call is independent. Two separate header lines, two separate footer sets — same as the existing dual-render pattern. |

## Testing plan

Tests live in `tests/test_render.py` (new) and `tests/test_pipeline_news_meta.py` (new).

Library-agnostic: capture rendered output via `Console(file=io.StringIO(), force_terminal=False)` (rich's standard test pattern, already used by `test_render.py` if present). No regex on Tavily payload shape — synthesize hits as in-memory dicts.

**Renderer tests:**
1. `news_meta=None` → output identical to current `render_portfolio` baseline (golden string match on a fixed 3-fund portfolio).
2. `news_meta` with `enabled=True, key_present=False` → header includes `atlandı (...)`, no markers/footers.
3. `news_meta` with hits but `displaced=[]` → header says `portföy değişmedi`, footer A present, footer B absent.
4. `news_meta` with hits and 1 displaced → both footers render in correct order.
5. Penalized survivor row has `📰` in fon_kodu cell and `(−0.20)` in score cell.

**Pipeline tests** (use a stub for `apply_negative_news_penalty` so we don't hit the network):
1. `news_enabled=False` → `news_meta == {"enabled": False}`, second `pick_top` call is *not* made.
2. `news_enabled=True`, stub returns 0 hits → `news_meta.total_hits == 0`, `displaced == []`, second `pick_top` call is *not* made (optimization gate).
3. Stub returns hits but penalty doesn't change rank order → `displaced == []`.
4. Stub returns hits that drop a top fund out of picks → `displaced` contains exactly that fund with correct `score_pre`/`score_post`/`hits`.
5. With `max_per_sector` cap active and a sector-themed displaced fund: verify the displaced field is populated even when the replacement is a sector-cap-driven shuffle (regression for cap interactions).

## Migration / back-compat

- `run_pipeline`'s return tuple grows from 3 to 4 elements. `cli.main` is updated to unpack 4. The non-interactive snippet in `CLAUDE.md` calls `run_pipeline` directly — that snippet currently unpacks 3 values, so the snippet needs the trailing `, _` (one-line tweak in `CLAUDE.md`).
- `render_portfolio` adds a kwarg with a default — existing callers (the snippet, tests) keep working.
- No config changes. No new env vars. No new dependencies.

## Out of scope (deferred)

- Showing news effects on the table itself for displaced funds (e.g. ghost rows). Footer B is enough; ghost rows would clutter the primary table.
- Timestamping the cache hit/miss per fund.
- Surfacing the *full* top-K hits set (only picks + displaced are interesting to the user; the rest is noise).
