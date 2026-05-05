# News Pass v1 — Design Spec

**Date:** 2026-05-04
**Status:** Approved (pivoted to Tavily after RSS verification failed), ready for implementation
**Supersedes:** `docs/06-news-pass.md` (older display-only RSS design)

## 0. Pivot note

The first draft of this spec used Turkish RSS feeds (`bigpara`, `bloomberght`,
`dunya`, `paraanaliz`) with company-prefix substring matching. Verification
showed:

- The originally-specified bigpara URL (`/rss/borsa-haberleri.xml`) returns 404.
- Working alternatives carry general macro/political news; **none** of them
  mention any PORTFÖY company in their current items.
- KAP / SPK / TEFAS expose no usable RSS endpoint.

Bad news about a specific portfolio-management company is too rare for
general financial RSS to surface on any given day. The architecture had no
data behind it, so we pivoted to **Tavily search API** — per-fund queries
get an actual fund-specific signal at the cost of needing an API key.

## 1. Goal

Make recent Turkish financial news influence fund picks. For the top-K
quant-scored candidates, query Tavily for the fund's portfolio-management
company alongside negative-news keywords; any returned hit subtracts a
fixed amount from that fund's score before final selection. Opt-in via
`--news`; default runs stay fast and offline.

This is sentiment-as-a-signal (option B from the original brainstorm) with
a search API as the source (option A from Q2, replacing the rejected
keyword-only heuristic).

## 2. User-facing behaviour

### 2.1 Default run (no flag)

Unchanged. No network. No news penalty. The current
"Not: --news özelliği v2 için planlandı, henüz aktif değil." stderr notice
goes away.

### 2.2 With `--news`

1. Score all candidates (existing pipeline).
2. Take the top-K candidates by quant score (K = `3 * N`, configurable).
3. For each, issue a Tavily search query:
   `"<COMPANY PREFIX>" (soruşturma OR dolandırıcılık OR iflas OR dava OR ceza OR fesih OR suspansiyon OR kapatma OR şikayet)`
   restricted to the last 30 days, max 3 results.
4. Apply a fixed `−0.20` penalty to each candidate that returned ≥1 result.
   Binary: one match or ten, same penalty.
5. Re-sort the K candidates and run the existing `pick_top` over them.
6. Render normally; for each pick that was hit, add a "⚠️ Olumsuz haber"
   footer with the matched titles + URLs so the penalty is auditable.

### 2.3 Failure modes

| Condition | Behaviour |
|---|---|
| `TAVILY_API_KEY` env var missing | stderr warning ("Haber taraması atlandı: TAVILY_API_KEY tanımlı değil"), skip steps 3–6, picks fall back to pure quant ranking |
| Tavily HTTP error / timeout / 5xx | stderr warning, skip penalty for this fund, continue with others; if *all* queries fail, behave as if the key was missing |
| Tavily returns malformed JSON | Same as HTTP error |
| Zero candidates have any negative-news hit | No penalties applied; picks unchanged; no warning needed |
| Cache write fails | Log at INFO; proceed with the in-memory result |

The news pass *never* fails the whole run. The table is always printed.

## 3. Pipeline insertion

Current pipeline (post May-4 changes):

```
load → merge → fee-NaN drop → horizon → score_candidates
  → assign strategy + sector → pick_top → compute_weights → render
```

New pipeline (additions in **bold**):

```
load → merge → fee-NaN drop → horizon → score_candidates
  → **(if --news) take top-K by score → tavily_query each
      → apply_negative_news_penalty → resort**
  → assign strategy + sector → pick_top → compute_weights
  → **(if --news) build hits-by-pick dict for render**
  → render
```

The penalty applies to the **top-K candidate set**, not all 1000+ funds.
That keeps query cost bounded (`3 * N`) while still letting news shape
which N funds get picked.

## 4. Module layout

New top-level package: `fundexpert/news/`.

### 4.1 `fundexpert/news/tavily.py`

Pure I/O. Issues Tavily search queries with disk caching and returns hits
per fund.

```python
@dataclass(frozen=True)
class NewsHit:
    title: str
    url: str
    published: datetime | None  # Tavily's published_date if available
    source: str                  # domain extracted from URL

def query_negative_news(
    company_prefix: str,
    keywords: tuple[str, ...],
    api_key: str,
    cache_dir: Path,
    ttl_seconds: int = 3600,
    max_age_days: int = 30,
    max_results: int = 3,
    timeout_seconds: int = 10,
) -> list[NewsHit]:
    """Search Tavily for the company prefix joined with the keyword OR-list,
    restricted to the last `max_age_days` days. Returns hits, [] on any
    error (with a logged warning). Empty prefix → []."""
```

Cache key: `sha256(company_prefix + "|" + sorted(keywords))`. Cache file:
`<cache_dir>/<key>.json` containing `{"queried_at": ISO8601, "hits": [...]}`.
A cache hit < TTL skips the network call entirely.

HTTP layer is `urllib.request` to avoid pulling in `requests` for one call —
Tavily's REST API is simple JSON-over-POST.

### 4.2 `fundexpert/news/match.py`

Pure functions. No I/O.

```python
def extract_company_prefix(fon_adi: str) -> str:
    """ATA PORTFÖY ÇOKLU VARLIK FON → 'ATA PORTFÖY'.
    Falls back to the first 3 whitespace-separated words if 'PORTFÖY'
    is absent. Empty/None → ''."""
```

Note: the keyword detection that lived here in the prior draft is gone —
Tavily's query syntax handles keyword matching server-side.

### 4.3 `fundexpert/news/penalty.py`

The pipeline-facing entry point.

```python
def apply_negative_news_penalty(
    scored: pd.DataFrame,
    top_k: int,
    keywords: tuple[str, ...],
    penalty: float,
    api_key: str | None,
    cache_dir: Path,
) -> tuple[pd.DataFrame, dict[str, list[NewsHit]]]:
    """Take the top_k rows of `scored` (by score, descending). For each,
    query Tavily; if any negative news returns, subtract `penalty` from
    that row's `score`. Returns (full_df_with_adjusted_scores, hits_by_code).

    api_key=None → skip everything, return scored unchanged + empty dict.
    Logs a warning explaining why if skipped.

    The hits_by_code dict only contains entries for funds that had matches.
    Funds outside the top_k are never queried (their scores are untouched).
    """
```

### 4.4 Config additions (`fundexpert/config.py`)

```python
# Tavily search API for the optional negative-news pass.
NEWS_API_KEY_ENV: str = "TAVILY_API_KEY"
NEWS_QUERY_TOP_K_MULTIPLIER: int = 3   # query 3*N candidates by default
NEWS_MAX_AGE_DAYS: int = 30
NEWS_MAX_RESULTS_PER_FUND: int = 3
NEWS_QUERY_TIMEOUT_SECONDS: int = 10

NEGATIVE_NEWS_KEYWORDS: tuple[str, ...] = (
    "soruşturma", "dolandırıcılık", "iflas", "dava",
    "ceza", "fesih", "suspansiyon", "kapatma", "şikayet",
)

NEGATIVE_NEWS_PENALTY: float = 0.20

NEWS_CACHE_DIR: Path = Path.home() / ".fundexpert" / "news_cache"
NEWS_CACHE_TTL_SECONDS: int = 3600
```

Keywords stored lowercase — Tavily search is case-insensitive and we
literally interpolate them into the query string.

### 4.5 `cli.py` changes

```python
# argparse already has --news
# remove the "v2 için planlandı" stderr notice

# inside main(), before run_pipeline:
api_key = os.environ.get(NEWS_API_KEY_ENV) if args.news else None

# pass news_enabled + api_key into run_pipeline:
selected, header = run_pipeline(
    ..., news_enabled=args.news, news_api_key=api_key, ...
)
```

`run_pipeline` gains two new keyword-only arguments: `news_enabled: bool = False`
and `news_api_key: str | None = None`. Inside `run_pipeline`, after
`score_candidates`:

```python
hits_by_code: dict[str, list[NewsHit]] = {}
if news_enabled:
    top_k = NEWS_QUERY_TOP_K_MULTIPLIER * n
    scored, hits_by_code = apply_negative_news_penalty(
        scored, top_k=top_k,
        keywords=NEGATIVE_NEWS_KEYWORDS,
        penalty=NEGATIVE_NEWS_PENALTY,
        api_key=news_api_key,
        cache_dir=NEWS_CACHE_DIR,
    )
```

After `pick_top`, project the hits dict down to just the picked funds
and pass into `render_portfolio` via the existing `news` parameter.

### 4.6 Render changes (`fundexpert/render/table.py`)

The render layer already accepts a `news` dict and prints a "Haberler:"
section. We re-use the same mechanism but the section header becomes
"⚠️ Olumsuz haber:" so the user knows what they're seeing. `NewsHit`
instances convert to the existing `{title, url, source, published}` dict
shape at the boundary.

### 4.7 `.gitignore`

Add (if not already present):

```
.env
.env.local
~/.fundexpert/news_cache/
```

The cache lives outside the repo (`~/.fundexpert/`) so the second entry
is precautionary only.

## 5. Determinism, idempotence, and the cache

A run with `--news` is deterministic given the same Tavily cache contents.
Tests stub `query_negative_news` directly to bypass the network entirely.

A run *without* `--news` is byte-identical to today's behaviour.

## 6. Test plan

| Layer | Test | What it locks in |
|---|---|---|
| `match.py` | `extract_company_prefix` over a parametrized list of real Turkish fund names (with/without PORTFÖY, lowercase, dotted-i) | Prefix extraction behaviour |
| `tavily.py` | `query_negative_news` builds the expected query string from prefix + keywords (assert via mocked HTTP) | Query construction |
| `tavily.py` | Returns `[]` and logs a warning when HTTP layer raises | Fail-soft |
| `tavily.py` | Returns `[]` and logs a warning when response is malformed JSON | Fail-soft |
| `tavily.py` | Cache hit (recent JSON file in cache_dir) skips the HTTP call | TTL |
| `penalty.py` | Top-K funds queried; rows beyond top-K are not touched | Bounded querying |
| `penalty.py` | A fund matched by Tavily gets `score -= 0.20`; non-matched fund unchanged | Penalty application |
| `penalty.py` | The returned hits dict only contains matched fund codes | Hit reporting |
| `penalty.py` | `api_key=None` → returns scored unchanged, empty dict, prints warning | Missing-key path |
| `cli.py` | `run_pipeline(news_enabled=True)` with `query_negative_news` stubbed to return hits for one fund produces a different selected set than `news_enabled=False` | End-to-end shift |
| `cli.py` | `run_pipeline(news_enabled=True, news_api_key=None)` returns same picks as `news_enabled=False` | Failure isolation |
| `render` | When the news dict has entries, the rendered output contains "Olumsuz haber" and the matched fund's code + the headline | Rendering |

All tests use offline fixtures or mock `urllib.request.urlopen`. No real
Tavily calls.

## 7. Out of scope (explicit)

These were considered and intentionally deferred — they live in
[todos.md](../../../todos.md) under "News pass — possible enhancements":

- Sentiment beyond binary hit/no-hit (Claude API for headline scoring,
  count-proportional penalty, additive 4th term)
- Hard exclusion (kill switch instead of soft penalty)
- RSS feeds as a complementary source (revived if Tavily costs become a
  concern; the rejected RSS architecture is documented in §0)
- Always-on mode with `--no-news` escape
- Broader keyword set (`zarar`, `düşüş`, `kriz`, `uyarı` …)
- Sentiment-priority user knob (analogous to risk/volume/fee)
- Backtest mode integration (news data isn't time-travellable cheaply)

## 8. Verification before implementation

The implementer must, as the first coding task:

1. Confirm `TAVILY_API_KEY` is set in the local environment.
2. Issue one manual query (e.g. for `"AK PORTFÖY"`) to confirm the
   API responds, the JSON shape matches what `tavily.py` will parse,
   and the `published_date` field is present on hits when available.
3. If Tavily's free tier denies the call (rate-limited, key revoked,
   API moved), surface this back to the user before writing more code.

## 9. Naming choices worth flagging

- The package is `fundexpert.news` — accurate to what it does, room to
  grow if v2 introduces a real sentiment scorer alongside the search hit.
- The CLI flag is `--news` (kept from the existing argparse stub).
- The header label is "⚠️ Olumsuz haber:" — the feature is specifically
  about negative news, not general annotation.
- The env var is `TAVILY_API_KEY` (Tavily's standard name), referenced
  via the `NEWS_API_KEY_ENV` config constant for indirection.

## 10. Security

- Key only ever read from `os.environ[NEWS_API_KEY_ENV]`. Never accepted
  as a CLI argument (would persist in shell history). Never written to
  disk by fundexpert.
- The cache file stores Tavily's response payloads. These are publicly
  searchable URLs/titles, not secrets — but the cache directory lives at
  `~/.fundexpert/` (outside the repo) regardless.
- `.gitignore` updated to exclude `.env` / `.env.local` so an accidental
  `echo TAVILY_API_KEY=... > .env` never gets committed.
