# Business Logic Review — 2026-06-12

## Executive Summary
The business logic in `fundexpert` is generally robust, making excellent use of pandas vectorized operations and implementing intelligent selection algorithms (like largest-remainder for weights). The Tavily news-pass implementation is especially well-designed, ensuring that network operations fail softly and only target top candidates. 

However, a critical P0 bug exists where missing data in TEFAS CSV exports can trigger mathematical errors (`NaN` values) that crash the application during weight allocation and rendering. Additionally, the strategy and sector mapping logic leaves a loophole for over-concentration in gold/precious metals, and a subtle Python-specific encoding edge case exists in the Turkish string matching logic.

## Findings

### [P0] Missing `risk` values cause pipeline crash
- **File(s)**: `fundexpert/scoring/score.py`, `fundexpert/select/weights.py`, `fundexpert/render/table.py`
- **Issue**: Some funds (notably "Serbest" funds like `EUN`) have empty values for `Fonun Risk Değeri` in TEFAS exports. `loader.py` handles this by loading them as strings or `NaN`. In `score.py`, `out["risk"].astype(float)` evaluates to `NaN` for these funds, causing `risk_norm`, `risk_penalty`, and ultimately `score` to become `NaN`. If a fund with a `NaN` score is picked (e.g., due to a small pool or large `N`), `weights.py` passes the `NaN` remaining proportion into `.astype(int)`, which raises a fatal `ValueError: Cannot convert non-finite values (NA or inf) to integer`, crashing the entire pipeline. Additionally, `render/table.py` calls `int(r["risk"])` which will also crash if `NaN`.
- **Impact**: Unhandled pipeline crash when processing current TEFAS exports.
- **Recommendation**: Impute missing risk values with a safe, conservative default (e.g., maximum risk level `7.0`) before calculating the risk penalty, ensuring `score` is always finite. Update the renderer to display missing risk safely.
- **Agent Prompt**: In `fundexpert/scoring/score.py`, impute missing risk with `7.0` using `out["risk"].astype(float).fillna(7.0)` before computing the risk penalty. In `fundexpert/render/table.py`, use `str(int(r["risk"])) if pd.notna(r["risk"]) else "-"` for safe rendering.

### [P1] Incomplete sector definition allows gold concentration
- **File(s)**: `fundexpert/select/sector.py`
- **Issue**: `sector_from_name` does not explicitly check for `"ALTIN"` or `"KIYMETLİ MADEN"`. While `strategy.py` correctly buckets these as `precious_metals`, the strategy cap and sector cap are applied independently. Because they don't match any sector rule, they fall back to the `"diversified"` sector bucket, which is completely exempt from the sector cap. Consequently, a user could end up with an un-diversified portfolio filled with gold funds if those funds span different umbrellas (e.g., "Altın Değişken Fon", "Altın Hisse Fonu", "Altın Fon Sepeti") satisfying the `max_per_type` strategy limit but silently bypassing the `max_per_sector` limit.
- **Impact**: Portfolio recommendations can become highly concentrated in a single commodity, directly violating the intended diversification logic.
- **Recommendation**: Add `"ALTIN"` and `"KIYMETLİ MADEN"` to `_SECTOR_RULES` mapping to a `precious_metals` sector bucket so that the sector cap properly catches cross-strategy gold funds.
- **Agent Prompt**: In `fundexpert/select/sector.py`, add `("ALTIN", "precious_metals")` and `("KIYMETLİ MADEN", "precious_metals")` to the `_SECTOR_RULES` tuple (place them before the `"METAL"` rule).

### [P2] Fragile Turkish keyword matching due to Python `lower()` behavior
- **File(s)**: `fundexpert/news/tavily.py`
- **Issue**: The client-side news validation tries to match Turkish characters gracefully by using `text_to_check = (title + " " + content).replace("I", "ı").replace("İ", "i").lower()`. However, the keyword strings from the config are matched using just `k.lower()`. In Python, calling `.lower()` on uppercase `"İ"` evaluates to `"i\u0307"` (an `i` with a combining dot), not a plain `"i"`. If a developer ever adds an uppercase keyword containing `"İ"` or `"I"` to `NEGATIVE_NEWS_KEYWORDS` (e.g., `"İPTAL"`), `k.lower()` will produce a string that can never mathematically match the normalized `text_to_check` string, causing valid negative news hits to be silently dropped.
- **Impact**: Adding uppercase Turkish keywords to the config will silently fail to match hits client-side, causing negative news to be ignored.
- **Recommendation**: Apply the exact same character replacements to the keyword string `k` before checking if it exists in `text_to_check`.
- **Agent Prompt**: In `fundexpert/news/tavily.py`, update the client-side validation loop to safely normalize `k` the same way as the text: `k_clean = k.replace("I", "ı").replace("İ", "i").lower()` and then check `if not any(k_clean in text_to_check for k in keywords)`.

### [P2] `max_total_expense_pct` is loaded but dead code
- **File(s)**: `fundexpert/data/loader.py`, `fundexpert/data/merge.py`, `fundexpert/scoring/score.py`
- **Issue**: The column `"Yıllık Azami Fon Toplam Gider Oranı (%)"` is explicitly parsed and renamed to `max_total_expense_pct` in `loader.py` and merged into the main dataframe. However, `score.py` only uses `applied_management_fee_pct` (`F_hat`). The `max_total_expense_pct` column is completely ignored downstream.
- **Impact**: Unused data bloats memory slightly and clutters the data model.
- **Recommendation**: Remove the dead code and drop the column at the parsing stage.
- **Agent Prompt**: Remove the `"Yıllık Azami Fon Toplam Gider Oranı (%)": "max_total_expense_pct"` mapping from `YONETIM_RENAME` in `fundexpert/data/loader.py`. Run a dead-code check (`vulture`) to ensure no other components are expecting it.
