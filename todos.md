Hey! Welcome back. Recap of where we left things:

- ✅ Strategy-based diversity cap shipped (`8d7c54d`)
- ✅ Weight balance fix shipped (`bece1f3`)
- ✅ Weights rounded to 5% multiples (`eb7496b`)
- ✅ CLAUDE.md added (`dc8e373`)
- ✅ CLI cancellation crash fix (`59f9f87`, May 3)
- ✅ `both` universe → two portfolios (`7c5f7cc`, May 3)
- ✅ Per-sector cap (`d364c49`, May 4)
- ✅ Risk semantics flipped: `risk_priority` → `risk_level` (`4398f2e`, May 4)

All on main, pushed.

Some directions we could go:

1. **News footer (`--news`)** — currently a v2 placeholder no-op. Brainstormed v1 design — see "News pass v1" section below.
2. **Score breakdown view** — `_breakdown` dict per fund is computed but never rendered. Add a `--explain` flag that shows R/V/F contributions and risk penalty per pick.
3. **Backtest mode** — given a `--asof` date, score against historical CSVs and report what the portfolio's actual N-month return would have been.
4. **Strategy bucket tuning** — the "other" bucket caught short-term hedge funds (KISA VADELİ SERBEST). Could add a `short_term_hedge` bucket so the cap distinguishes them.
5. **Web UI** — Flask/FastAPI wrapping `run_pipeline`, served on localhost. The earlier session notes mentioned an "app on localhost:3000" goal.
6. **Fee/AUM filtering** — hard filters before scoring (e.g. exclude funds with fee > 3%, or AUM < threshold).

---

## News pass v1 — chosen design (May 4 brainstorm)

Chosen path through the design forks:

- **Effect on scoring:** sentiment is a *signal*, folded into the score so picks change (not just decoration).
- **Detector:** negative-keyword heuristic (regex over Turkish bad-news vocabulary). No external API, no model dependency.
- **Penalty shape:** hard binary — any keyword hit on a fund subtracts a fixed amount (~`−0.20`) from the score. One match or ten, same penalty.
- **Source:** start with one RSS feed (`bigpara.hurriyet.com.tr`). Last 30 days, 1h disk cache.
- **Trigger:** `--news` flag is opt-in. Default runs stay offline and apply no penalty.
- **Match scope:** **title only**, conservative keyword set (`iflas`, `dolandırıcılık`, `soruşturma`, `dava`, `ceza`, `fesih`, `suspansiyon`, `kapatma`, `şikayet`).
- **Article-to-fund linking:** case-insensitive substring match of the company prefix (`ATA PORTFÖY`, `İŞ PORTFÖY`, …) in the article title.

## News pass — possible enhancements (future)

Rejected/deferred options from the same brainstorm — keep in pocket for v2+:

- **Better detector**
  - Claude API per fund: batch headlines, ask for sentiment in `[−1, +1]`. Best Turkish-financial quality. Costs pennies, needs `ANTHROPIC_API_KEY`. Cache verdicts so re-runs are free.
  - Local Turkish sentiment model (`savasy/bert-base-turkish-sentiment`): free at runtime, ~700MB torch dep, mediocre on financial text.
  - Hybrid: heuristic does first pass, Claude is called only for ambiguous cases. Lower cost than pure Claude.
- **Richer penalty shape**
  - Hit-count proportional (`−0.05` per hit, capped at `−0.30`) — distinguishes a fund with one mild hit from one with six.
  - 4th additive term: normalize negative-news count to `N̂ ∈ [0,1]`, fold in as `−w_news · N̂` alongside R̂/V̂/(1−F̂). Could even get its own user-facing priority knob.
  - Hard exclusion (kill switch): any negative-news hit drops the fund regardless of score. Treats news as a guardrail, not a signal.
- **Broader sources**
  - Add `bloomberght.com` and `dunya.com` once we see if `bigpara` alone is too sparse (one-line `config.RSS_FEEDS` change).
  - KAP (Kamuyu Aydınlatma Platformu) — official regulator bulletins, more authoritative for suspensions/fines/fraud, harder to parse.
  - Manual `data/known_bad_funds.txt` seed — zero HTTP, fully deterministic, complementary to RSS.
- **Always-on mode** — fetch+penalize on every run (with `--no-news` escape hatch for offline/CI). Removes the "scores depend on flag" surprise but adds a network dep to default runs.
- **Broader keyword set** — soft-negative words (`zarar`, `düşüş`, `kriz`, `uyarı`, `kaybetti`, `çöküş`, `iptal`, `el konuldu`, `incelemeye alındı`). Risk: false positives on market-wide bad days. Better revisited after we see what the conservative list actually catches.
- **Match scope: title + description** — currently title-only to avoid "rakiplerin yaşadığı iflas..." false positives. Worth revisiting once true positives are well-understood.

## Other deferred items from review.md / today's discussion

- **P1 cancellation crash** — ✅ shipped May 3 (`59f9f87`).
- **P2 weights fallback for `n > 20`** — still open. Decide between hard-fail (`raise ValueError`), silent cap at 20, or document-the-contract. CLI side already constrains `n ≤ 20` via the prompt; only matters for non-CLI `run_pipeline` callers.
- **P2 data path resolution** — `DATA_ROOT = repo/data` is brittle for non-editable installs. Add a `--data-root` flag or `FUNDEXPERT_DATA` env var with a clear "not found" error. Only relevant if we ever `pip install` outside the dev tree.
- **P2 docs out of sync** — `docs/01-architecture.md` through `docs/07-output-and-testing.md` describe behavior that's drifted (umbrella-type cap, active news pass, etc.). Two paths: rewrite to match, or banner them as historical and lean on README + CLAUDE.md as the live contract.
- **P3 staged candidate funnel counts** — current `candidate_kept` blurs fee-NaN drop and horizon-NaN drop into one number. Split into per-stage counts in the header.
- **Architecture: extract orchestration into `fundexpert/pipeline.py`** — `cli.py` now does prompts, argparse, last-run cache, two-universe loop, news (soon), error handling. If we add `--explain`, backtest mode, or a web UI, that file balloons. Worth pulling orchestration out before the next round of flags.
- **Sector classifier growth** — `select/sector.py` keyword set is intentionally minimal. Add new sectors as real picks reveal what's missing.
- **Strategy classifier: short-term hedge bucket** — KISA VADELİ SERBEST funds currently fall to `"other"`. Their scores are competitive enough to surface; deserves its own bucket so the per-strategy cap binds.

Or something totally different. What's calling to you?