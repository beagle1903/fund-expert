# 06 — News Pass (`--news`)

> **Historical design:** The implemented news pass uses Tavily, strict domain filtering, and a score penalty. See `AGENTS.md`, source, and tests for current behavior.

Optional, on-demand. v1 scope: **annotate** each picked fund with up to 3 recent Turkish financial-news headlines. **Zero scoring impact.**

## Goal in v1

The news pass is informational. After selection finishes, it attaches a small list of headlines per picked fund so you can see if any recent reporting is worth reading before committing real money.

The user explicitly chose "on-demand via a flag" — default runs are fast, deterministic, and need no network.

## Flow

1. Selection completes → we have N picked funds.
2. If `--news` is **not** set, skip everything below and go straight to render.
3. For each picked fund, build a search query from:
   - The portfolio company prefix from `Fon Adı` — the words before `PORTFÖY` (e.g., `ATA PORTFÖY ÇOKLU VARLIK DEĞİŞKEN FON` → `ATA PORTFÖY`).
   - Falls back to the first 3 words if `PORTFÖY` is absent.
4. Fetch a small set of RSS feeds via `feedparser`. Default list (see *Verification* below):
   - `https://bigpara.hurriyet.com.tr/rss/borsa-haberleri.xml`
   - `https://www.bloomberght.com/rss`
   - `https://www.dunya.com/rss?dunya=fon`
5. Match feed items by case-insensitive substring of the company prefix in the title or description. Keep up to **3 most-recent matches per fund**, restricted to the **last 30 days**.
6. Annotate each result record with:
   ```python
   news = [
       {"title": str, "url": str, "published": datetime, "source": str},
       ...
   ]
   ```
7. The render layer prints them as a footnote section under the table.

## Caching & Politeness

- All fetches go through a disk cache at `~/.fundexpert/news_cache/`, keyed by feed URL, with a **1-hour TTL**.
- Re-running with `--news` within an hour reuses the cache — no extra HTTP traffic.
- One sequential request per feed, **5-second timeout** each. No concurrency in v1.
- User-Agent identifies the tool: `fundexpert/0.1 (+local)`

## Failure Handling

| Condition | Behavior |
|---|---|
| Feed times out / 404 / malformed XML | Log at INFO level, skip this feed, continue with the rest |
| All feeds fail | Print a one-line warning, render table without news footnotes |
| Zero matches across all feeds | Print `Eşleşen son haber bulunamadı` and skip the footnote section |

The news pass **never** fails the whole run. The table is always printed.

## Out of Scope (v1)

- NLP / sentiment scoring on headlines
- Effect on score or weights
- Full-article body scraping
- KAP / SPK regulator-bulletin scraping (`kap.org.tr`) — possible v2 add
- Search-API providers (Tavily, Brave) — possible v2 add when the user is OK adding API keys

## Verification Required Before Implementation

The 3 RSS URLs above are based on common Turkish finance sites but **not yet fetched in this design phase**. Before coding the news module, the implementer must:

1. Fetch each feed and confirm it is a parseable RSS/Atom document.
2. Confirm items have `published` (or `updated`) timestamps.
3. Spot-check that fund-relevant content appears (search for known portfolio companies like "ATA PORTFÖY", "İŞ PORTFÖY", "ZİRAAT PORTFÖY").

If any feed fails verification, do not silently substitute — bring alternatives back to the user. Acceptable alternative sources to evaluate include `mynet.com/finans`, `finansgundem.com`, `paraanaliz.com`.

The chosen feed list lives in `config.RSS_FEEDS` so swapping is a one-file change.
