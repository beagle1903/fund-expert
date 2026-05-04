# News Pass v1 — Design Spec

**Date:** 2026-05-04
**Status:** Approved, ready for implementation plan
**Supersedes:** `docs/06-news-pass.md` (older display-only design)

## 1. Goal

Make recent Turkish financial news influence fund picks. A fund whose
portfolio-management company appears in a negative-news headline gets a
fixed score penalty before selection, so the picker prefers funds without
recent bad press. Opt-in via `--news`; default runs stay fast and offline.

This is sentiment-as-a-signal (option B from the brainstorm), implemented
with a deliberately simple negative-keyword heuristic (option C). The
brittle parts are intentional — we'd rather miss subtle negative news than
falsely penalise healthy funds.

## 2. User-facing behaviour

### 2.1 Default run (no flag)

Unchanged. No network. No news penalty. The "Not: --news özelliği v2 için
planlandı, henüz aktif değil." stderr notice goes away.

### 2.2 With `--news`

1. Fetch the configured RSS feed (cached) before scoring.
2. Apply negative-news penalty to every candidate (not just picks) so
   selection actually shifts.
3. Render normally; for each pick that was hit, add a "⚠️ Olumsuz haber"
   footer line with the matched headline so the penalty is auditable.

### 2.3 Failure modes

| Condition | Behaviour |
|---|---|
| Feed times out / 404 / malformed XML | Log a warning to stderr, skip the penalty entirely, print picks as if `--news` was off |
| Zero matched articles across all candidates | No penalties applied; picks unchanged; no warning needed |
| Cache write fails | Log at INFO; proceed with the in-memory result |

The news pass *never* fails the whole run. The table is always printed.

## 3. Pipeline insertion

Current pipeline (after today's changes):

```
load → merge → fee-NaN drop → horizon → score_candidates
  → assign strategy + sector → pick_top → compute_weights → render
```

New pipeline (additions in **bold**):

```
load → merge → fee-NaN drop → horizon → score_candidates
  → **(if --news) fetch articles + apply_negative_news_penalty**
  → assign strategy + sector → pick_top → compute_weights
  → **(if --news) build matched-article dict for picks**
  → render
```

Penalty is applied **before** `pick_top`, so funds with negative news
typically lose their slot to the next-best alternative. The matched-article
dict for the rendered footer is built **after** `pick_top` so we only carry
display data for the N picks, not for all 1000+ candidates.

## 4. Module layout

New top-level package: `fundexpert/news/`.

### 4.1 `fundexpert/news/feed.py`

Pure I/O. Fetches the configured RSS feeds with disk caching and returns a
flat list of articles.

```python
@dataclass(frozen=True)
class Article:
    title: str
    url: str
    published: datetime  # UTC
    source: str          # short label, e.g. "bigpara"

def fetch_articles(feeds: list[str], cache_dir: Path,
                   ttl_seconds: int = 3600,
                   max_age_days: int = 30,
                   timeout_seconds: int = 5) -> list[Article]:
    """Fetch + parse all configured feeds; aggregate items newer than
    max_age_days. Returns [] on total failure (with a logged warning)."""
```

Cache: `cache_dir/<sha256(url)>.xml` plus `<sha256(url)>.meta.json`
(timestamp). One sequential request per feed. UA: `fundexpert/0.1 (+local)`.

### 4.2 `fundexpert/news/match.py`

Pure functions. No I/O.

```python
def extract_company_prefix(fon_adi: str) -> str:
    """ATA PORTFÖY ÇOKLU VARLIK FON → 'ATA PORTFÖY'.
    Falls back to the first 3 whitespace-separated words if 'PORTFÖY'
    is absent. Empty/None → ''."""

def is_negative_title(title: str, keywords: tuple[str, ...]) -> bool:
    """Case-insensitive substring match against the keyword tuple.
    Uses the Turkish-i fix (i↔İ, ı↔I) before .upper()."""

def match_negative_articles(prefix: str,
                            articles: list[Article],
                            keywords: tuple[str, ...]) -> list[Article]:
    """Articles whose title contains both the prefix (case-insensitive)
    AND at least one keyword. Empty prefix → []."""
```

### 4.3 `fundexpert/news/penalty.py`

The pipeline-facing entry point.

```python
def apply_negative_news_penalty(
    scored: pd.DataFrame,
    articles: list[Article],
    keywords: tuple[str, ...],
    penalty: float,
) -> tuple[pd.DataFrame, dict[str, list[Article]]]:
    """For each fund, find matching negative articles. If any, subtract
    `penalty` from `score`. Returns (adjusted_df, fund_code → matched articles).
    The dict is keyed by fon_kodu and only contains entries for hit funds."""
```

Penalty is **binary**: any number of matches deducts the same fixed amount.

### 4.4 Config additions (`fundexpert/config.py`)

```python
RSS_FEEDS: tuple[str, ...] = (
    "https://bigpara.hurriyet.com.tr/rss/borsa-haberleri.xml",
)

NEGATIVE_NEWS_KEYWORDS: tuple[str, ...] = (
    "İFLAS", "DOLANDIRICILIK", "SORUŞTURMA", "DAVA",
    "CEZA", "FESİH", "SUSPANSİYON", "KAPATMA", "ŞİKAYET",
)

NEGATIVE_NEWS_PENALTY: float = 0.20
NEWS_CACHE_DIR: Path = Path.home() / ".fundexpert" / "news_cache"
NEWS_CACHE_TTL_SECONDS: int = 3600
NEWS_MAX_AGE_DAYS: int = 30
NEWS_FETCH_TIMEOUT_SECONDS: int = 5
```

Keywords are stored uppercase to skip a `.upper()` on every comparison.

### 4.5 `cli.py` changes

```python
parser.add_argument("--news", action="store_true", ...)  # already exists
# remove the "v2 için planlandı" stderr notice

# inside run_pipeline (after score_candidates, before assign):
if news_enabled:
    articles = fetch_articles(RSS_FEEDS, NEWS_CACHE_DIR, ...)
    scored, hits_by_code = apply_negative_news_penalty(
        scored, articles, NEGATIVE_NEWS_KEYWORDS, NEGATIVE_NEWS_PENALTY,
    )
else:
    hits_by_code = {}

# after pick_top:
news_for_render = {code: hits_by_code[code]
                   for code in selected["fon_kodu"]
                   if code in hits_by_code}
```

`run_pipeline` gains a new keyword-only argument `news_enabled: bool = False`.
`hits_by_code` is threaded into `render_portfolio` via the existing `news`
parameter (which already accepts `dict[str, list[dict]]`).

### 4.6 Render changes (`fundexpert/render/table.py`)

The render layer already accepts a `news` dict and prints a "Haberler:"
section. v1 of this feature uses that exact mechanism — but the items it
prints are *only* the matched negative articles, and the section header is
re-labelled to "⚠️ Olumsuz haber:" so the user knows what they're seeing.

`Article` instances are converted to the existing `{title, url, source,
published}` dict shape at the boundary.

## 5. Determinism, idempotence, and the cache

A run with `--news` is deterministic given the same RSS cache contents.
This means the test suite can stub the cache directory with a fixture XML
file and get reproducible behaviour with no network calls.

A run *without* `--news` is identical to today's behaviour — same picks,
same order, same scores.

## 6. Test plan

| Layer | Test | What it locks in |
|---|---|---|
| `match.py` | `extract_company_prefix` over a parametrized list of real Turkish fund names (with/without PORTFÖY, lowercase, dotted-i) | Prefix extraction behaviour |
| `match.py` | `is_negative_title` over (positive Turkish title, negative title with `şikayet`, mixed-case, lowercase-i, no match) | Keyword detector |
| `match.py` | `match_negative_articles` returns articles where prefix AND keyword both hit; empty prefix → `[]` | Combined matcher |
| `feed.py` | `fetch_articles` parses a fixture XML file from the cache directory and returns articles | Parser |
| `feed.py` | `fetch_articles` returns `[]` when feed URL unreachable (HTTP layer mocked to raise; specific library chosen at implementation time) | Fail-soft |
| `feed.py` | Cache hit (recent meta.json) skips the HTTP call | TTL |
| `penalty.py` | A fund matched by a negative article gets `score -= 0.20`; non-matched fund unchanged | Penalty application |
| `penalty.py` | The returned hits dict only contains matched fund codes | Hit reporting |
| `cli.py` | `run_pipeline(news_enabled=True)` with stub feed produces a different selected set than `news_enabled=False` for a fund seeded with negative news | End-to-end shift |
| `cli.py` | `run_pipeline(news_enabled=True)` with feed fetch failing prints a warning, returns same picks as `news_enabled=False` | Failure isolation |
| `render` | When the news dict has entries, the rendered output contains "Olumsuz haber" and the matched fund's code + the headline | Rendering |

All tests use offline fixtures. No real RSS calls.

## 7. Out of scope (explicit)

These were considered and intentionally deferred — they live in
[todos.md](../../../todos.md) under "News pass — possible enhancements":

- Sentiment beyond binary keyword detection (Claude API, local model, hybrid)
- Penalty shapes beyond binary (count-proportional, additive 4th term, hard exclusion)
- More than one feed (`bloomberght`, `dunya`, KAP, manual seed file)
- Always-on mode with `--no-news` escape
- Broader keyword set (soft-negative words like `zarar`, `düşüş`)
- Title + description matching (currently title-only to avoid false positives)
- Sentiment-priority user knob (analogous to risk/volume/fee)

## 8. Verification before implementation

Per the original v1 spec's "verify before coding" rule, the implementer
must, as the first task:

1. `curl` the bigpara RSS URL and confirm it returns parseable XML.
2. Confirm items have `<pubDate>` (or `<published>` / `<updated>`) timestamps.
3. Spot-check that fund-relevant content surfaces — search for
   `"ATA PORTFÖY"`, `"İŞ PORTFÖY"`, `"ZİRAAT PORTFÖY"` across recent items.

If the feed fails verification, surface alternatives (`mynet.com/finans`,
`finansgundem.com`, `paraanaliz.com`) before writing code. Don't silently
substitute.

## 9. Naming choices worth flagging

- The new package is `fundexpert.news` (not `fundexpert.sentiment` or
  `fundexpert.signals`) — accurate to what it does today and leaves room
  to grow if v2 introduces real sentiment.
- The CLI flag is `--news` (kept from the existing argparse stub).
- The header label is "⚠️ Olumsuz haber:" not "Haberler:" — the v1 design
  is specifically about negative news, not general annotation.
