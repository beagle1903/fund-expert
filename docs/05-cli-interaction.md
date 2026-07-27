# 05 — CLI Interaction

> **Historical design:** This predates the implemented web API and dashboard. See the repository README for current run instructions and interfaces.

Single command `fundexpert`. Interactive Turkish prompts collect the criteria; flags handle non-prompted modes.

## Entry Point

- Console script registered in `pyproject.toml`: `fundexpert = fundexpert.cli:main`
- Also runnable as `python -m fundexpert`

## Flags

| Flag | Purpose |
|---|---|
| `--news` | Enable RSS news annotation pass after selection (see [06-news-pass](06-news-pass.md)) |
| `--max-per-type N` | Override the default umbrella-type cap (`2`) for this run |
| `--seed N` | Reserved for v2; v1 has no randomness |

`--help` prints all flags and a short usage example.

## Prompt Flow (using `questionary`)

```
? Fon evreni                               (tefas / befas / both)
? Kurucu                                   (universe-specific list / Tümü)
? Risk önceliği (yüksek = riskten kaçınma) (Low / Medium / High)
? Yatırım vadesi                           (Short ≤3 ay / Medium 3 ay – 1 yıl / Long 1 yıl+)
? Hacim değişimi önceliği                  (Low / Medium / High)
? Yönetim ücreti önceliği                  (Low / Medium / High)
? Kaç fon istiyorsun (1-20)?               5
```

All choice prompts are arrow-key driven. The integer prompt uses `min=1, max=20, default=5`.

## Last-Run Memory

Each prompt's last answer is cached in `~/.fundexpert/last.json` and offered as the default on the next run. Pure quality-of-life. No PII; never sent over the network.

If the file is missing or corrupt, defaults silently fall back to the hard-coded ones below.

## Hard-Coded Defaults (First Run Only)

| Prompt | Default |
|---|---|
| Universe | tefas |
| Kurucu | Tümü |
| Risk priority | Medium |
| Horizon | Medium |
| Volume priority | Medium |
| Fee priority | Medium |
| N | 5 |

## Validation

- Universe must be one of the three options (enforced by the picker).
- N must be an integer in `[1, 20]`. Out-of-range input re-prompts.
- Bucket prompts can only return Low/Med/High — no free text.

## Error UX

| Condition | Behavior |
|---|---|
| CSV file missing | Print `Hata: data/<universe>/<file> bulunamadı`, exit code 1 |
| CSV malformed | Print file + line number, exit 1 |
| Empty candidate pool after filters | Print funnel (`1308 → 0`) and a "no portfolio could be built" message; exit 0 |
| `--news` set but no internet | Skip news pass with a one-line warning, still print the table |
| Any unhandled exception | Short message in normal mode; full traceback when `FUNDEXPERT_DEBUG=1` is set |

## Language

Prompts and table headers are **Turkish**. Fund names, umbrella types, and other data values are already Turkish in the source CSVs.

If an English mode is ever added, it goes via a `--lang en` flag. Out of scope for v1.
