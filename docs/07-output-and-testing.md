# 07 — Output & Testing

## Renderer (`render/table.py`)

Uses the `rich` library. One table on stdout, with a header block above and an optional footer block below.

### Header Block

```
Fund Expert — 2026-05-02 11:42
Evren: tefas+befas (1308 fon)  •  Vade: Long  •  Risk önc.: High
Hacim önc.: Medium  •  Ücret önc.: High  •  N=5
Aday havuzu: 1308 → 1107 (NaN filtreleri sonrası)
```

This makes any single screenshot reproducible.

### Table

| Fon Kodu | Fon Adı | Şemsiye | Risk | Ağırlık % | Skor |
|---|---|---|---|---|---|
| AAK | ATA PORTFÖY ÇOKLU VARLIK DEĞİŞKEN FON | Değişken | 4 | 28.4 | 0.71 |
| ... | ... | ... | ... | ... | ... |
| | | | **Toplam** | **100.0** | |

A `Toplam` summary row anchors the eye and confirms weights sum to 100.

### Footer Block (only if `--news`)

```
Haberler:
  AAK — "Ata Portföy yeni fon ihraç etti"  (bigpara, 2026-04-28)
        https://...
  ...
```

Funds with zero news hits are simply absent from the footer — no empty bullets.

### No File Output in v1

JSON / CSV / Markdown persistence is not part of v1 per the locked decision. If added later, the render layer is the only file that grows; selection logic stays untouched.

---

## Testing Strategy

Pure modules get unit tests. IO modules get integration tests against tiny fixtures. One end-to-end smoke test exercises the live CSVs.

| Module | Test type | Fixtures |
|---|---|---|
| `data/loader.py` | unit | small synthetic CSV (5 rows) with Turkish decimals + metadata header, plus one malformed row |
| `data/merge.py` | unit | three small frames with overlapping & non-overlapping codes |
| `scoring/horizon.py` | unit | rows with NaN in some return columns |
| `scoring/normalize.py` | unit | constant-value column (degenerate min-max) |
| `scoring/score.py` | unit | known inputs → hand-computed expected scores |
| `select/pick.py` | unit | umbrella-type cap edge case (cap blocks N) |
| `select/weights.py` | unit | negative-score edge case → ε-shift behavior |
| `news/rss.py` | integration | recorded RSS XML fixtures (no network in CI) |
| End-to-end | smoke | run CLI against the real CSVs in `data/`, assert non-empty output, valid weight sum |

### Tooling

- `pytest` runner. No mocking framework needed — pure functions take DataFrames in, return DataFrames out.
- The smoke test is the safety net that proves live CSVs still parse correctly after future refreshes.

---

## Dependencies

Pinned in `requirements.txt` and declared in `pyproject.toml`.

| Package | Purpose | Loaded |
|---|---|---|
| `pandas` | CSV + DataFrame ops | always |
| `rich` | table render | always |
| `questionary` | interactive TTY prompts | always |
| `feedparser` | RSS parsing | only when `--news` is set |
| `pytest` | tests | dev only |

Total runtime deps: 4. No solvers, no API keys, no Claude/MCP coupling at runtime.

## Project Bootstrap

```
fund expert/
├── data/                       # source CSVs (already exists)
├── docs/                       # design docs (this folder)
├── fundexpert/                 # Python package (to be created)
├── tests/                      # pytest suite (to be created)
├── pyproject.toml
└── requirements.txt
```

After cloning and `pip install -e .`:

```bash
fundexpert            # interactive prompts
fundexpert --news     # interactive prompts + RSS annotation
python -m fundexpert  # equivalent for development
```
