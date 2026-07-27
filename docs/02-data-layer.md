# 02 — Data Layer

> Historical design snapshot. See `fundexpert/data/` and generated API
> documentation for current behavior.

Responsible for loading raw TEFAS/BEFAS CSVs, parsing Turkish-localized numbers, and joining the three files per universe into one fund-per-row DataFrame.

## Source Files

Six CSVs total. Both folders share identical schemas.

```
data/tefas/
  buyukluk.csv         # 1006 rows — portfolio size + AUM change
  getiri.csv           # 1006 rows — returns by horizon + Fonun Risk Değeri
  yonetim ucreti.csv   # 1005 rows — management fee
data/befas/
  buyukluk.csv         # 302 rows
  getiri.csv           # 302 rows
  yonetim ucreti.csv   # 302 rows
```

Each CSV has 3 metadata rows (export timestamp, record count, blank) before the header on row 4.

## Schemas (raw column → internal name)

### `getiri.csv` (returns + risk)
| Source column | Internal name |
|---|---|
| `Fon Kodu` | `fon_kodu` |
| `Fon Adı` | `fon_adi` |
| `Şemsiye Fon Türü` | `umbrella_type` |
| `Fonun Risk Değeri` | `risk` (SRRI 1–7 integer) |
| `1 Ay (%)` | `ret_1m` |
| `3 Ay (%)` | `ret_3m` |
| `6 Ay (%)` | `ret_6m` |
| `Yılbaşından İtibaren (%)` | `ret_ytd` |
| `1 Yıl (%)` | `ret_1y` |
| `3 Yıl (%)` | `ret_3y` |
| `5 Yıl (%)` | `ret_5y` |

### `buyukluk.csv` (portfolio size)
| Source column | Internal name |
|---|---|
| `Fon Kodu` | `fon_kodu` |
| `İlk Portföy Büyüklüğü` | `aum_first` |
| `Son Portföy Büyüklüğü` | `aum_last` |
| `Portföy Büyüklüğü Değişimi (%)` | `aum_change_pct` |
| `Tedavüldeki İlk Pay Adedi` | `units_first` |
| `Tedavüldeki Son Pay Adedi` | `units_last` |
| `Pay Adedi Değişimi (%)` | `units_change_pct` |
| `Getiri Oranı (%)` | (dropped — redundant with `getiri.csv`) |

### `yonetim ucreti.csv` (fees)
| Source column | Internal name |
|---|---|
| `Fon Kodu` | `fon_kodu` |
| `Uygulanan Yönetim Ücreti Yıllık (%)` | `applied_management_fee_pct` |
| `Fon İç Tüzüğünde Yer Alan Yönetim Ücreti Yıllık (%)` | `bylaw_management_fee_pct` |
| `Yıllık Getiri Oranı (%)` | (dropped — redundant) |
| `Yıllık Azami Fon Toplam Gider Oranı (%)` | `max_total_expense_pct` |

The internal-name mapping lives in one constants module. If a future TEFAS/BEFAS export changes column names, only that module changes.

## Loader (`data/loader.py`)

```python
pd.read_csv(
    path,
    skiprows=3,             # metadata rows 0-2; header on row 3
    encoding='utf-8',
    decimal=',',            # Turkish decimal comma
    thousands=None,         # observed rows have no thousands grouping
)
```

**Caveat — thousands separator:** Sample rows show `36093030,50` with no thousands grouping, so `thousands=None` is correct for the data we've seen. A unit test asserts numeric parsing on a known row. If real-world exports later contain `36.093.030,50`-style values, `thousands='.'` should be added and the test must catch it.

After loading, columns are renamed via the mapping above. Returns `dict[str, pd.DataFrame]`: `{"getiri": ..., "buyukluk": ..., "yonetim_ucreti": ...}`.

## Merger (`data/merge.py`)

- Inner-joins all three frames on `fon_kodu` → one row per fund with the union of columns.
- Drops the redundant `Getiri Oranı (%)` from `buyukluk` and `Yıllık Getiri Oranı (%)` from `yonetim_ucreti`. The authoritative return source is `getiri.csv`.
- Adds a `universe` column (`"tefas"` or `"befas"`) so downstream code can filter or group.
- For the `"both"` universe, each frame is loaded and merged independently, then `pd.concat`-ed. Fund codes are disjoint between TEFAS and BEFAS (verified empirically: 1006 ∩ 302 = 0), so no collision risk.
- Logs (not errors) any `fon_kodu` present in only some files: the join is inner, so partial rows are dropped — but the log surfaces data-quality issues for the user when they refresh CSVs.

## Missing-Value Policy

| Field | Policy |
|---|---|
| `ret_5y`, `ret_3y` NaN (newer funds) | If horizon=Long and **both** are NaN, fund is excluded. Excluded count is reported. |
| Some return columns NaN within the chosen bucket | Bucket value = mean of available columns. |
| `aum_change_pct` NaN | Volume term contributes 0 (neutral). A flag is printed listing affected funds. |
| `applied_management_fee_pct` NaN | Fund excluded — fee is a primary criterion; missing it is unsafe. |

## Locale / Encoding

Source CSVs are UTF-8 without BOM. Turkish characters render directly. Decimal-comma handling is the only locale concern.
